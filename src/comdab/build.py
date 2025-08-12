from collections.abc import Iterator
from typing import Any

from sqlalchemy import schema, types
from sqlalchemy.sql import ClauseElement

from comdab.exceptions import ComdabInternalError, UnhandledTypeError
from comdab.models.column import ComdabColumn
from comdab.models.constraint import (
    ComdabCheckConstraint,
    ComdabConstraint,
    ComdabForeignKeyConstraint,
    ComdabPrimaryKeyConstraint,
    ComdabUniqueConstraint,
)
from comdab.models.custom_type import ComdabCustomType
from comdab.models.function import ComdabFunction
from comdab.models.index import ComdabIndex
from comdab.models.schema import ComdabSchema
from comdab.models.sequence import ComdabSequence
from comdab.models.table import ComdabTable
from comdab.models.trigger import ComdabTrigger
from comdab.models.type import ComdabType, ComdabTypes
from comdab.models.view import ComdabView
from comdab.source import ComdabSource
from comdab.utils import dict_by_name

strict = False


class ComdabBuilder:
    """Build a database schema describing an existing database.

    Built on :meth:`sqlalchemy.Metadata.reflect` machinery, with custom extensions.
    """

    def __init__(
        self,
        source: ComdabSource,
        allow_unknown_types: bool = False,
    ) -> None:
        self.source = source
        self.allow_unknown_types = allow_unknown_types

    # Level 0

    def build_schema(self) -> ComdabSchema:
        sa_metadata = schema.MetaData()
        sa_metadata.reflect(
            bind=self.source.connection,
            views=False,
            schema=self.source.schema_name,
            resolve_fks=False,
        )

        return ComdabSchema(
            tables=dict_by_name(self.generate_tables(sa_metadata)),
            views=dict_by_name(self.generate_views(sa_metadata)),
            sequences=dict_by_name(self.generate_sequences(sa_metadata)),
            functions=dict_by_name(self.generate_functions(sa_metadata)),
            custom_types=dict_by_name(self.generate_custom_types(sa_metadata)),
            extra={str(key): val for key, val in sa_metadata.info.items()},
        )

    # Level 1

    def generate_tables(self, sa_metadata: schema.MetaData) -> Iterator[ComdabTable]:
        for sa_table in sa_metadata.tables.values():
            yield self.build_table(sa_table)

    def build_table(self, sa_table: schema.Table) -> ComdabTable:
        return ComdabTable(
            name=sa_table.name,
            columns=dict_by_name(self.generate_columns(sa_table)),
            constraints=dict_by_name(self.generate_constraints(sa_table)),
            indexes=dict_by_name(self.generate_indexes(sa_table)),
            triggers=dict_by_name(self.generate_triggers(sa_table)),
            extra=dict(sa_table.dialect_kwargs),
        )

    def generate_views(self, sa_metadata: schema.MetaData) -> Iterator[ComdabView]:
        yield from ()  # No database-agnostic implementation

    def generate_sequences(self, sa_metadata: schema.MetaData) -> Iterator[ComdabSequence]:
        yield from ()  # No database-agnostic implementation

    def generate_functions(self, sa_metadata: schema.MetaData) -> Iterator[ComdabFunction]:
        yield from ()  # No database-agnostic implementation

    def generate_custom_types(self, sa_metadata: schema.MetaData) -> Iterator[ComdabCustomType]:
        yield from ()  # No database-agnostic implementation

    # Level 2

    def generate_columns(self, sa_table: schema.Table) -> Iterator[ComdabColumn]:
        for sa_column in sa_table.columns:
            yield self.build_column(sa_column)

    def generate_constraints(self, sa_table: schema.Table) -> Iterator[ComdabConstraint]:
        for sa_constraint in sa_table.constraints:
            if isinstance(sa_constraint, schema.PrimaryKeyConstraint) and not sa_constraint.columns:
                # Non-existing constraint created because SQLAlchemy needs a primary key per table: ignore
                continue
            yield self.build_constraint(sa_constraint)

    def generate_indexes(self, sa_table: schema.Table) -> Iterator[ComdabIndex]:
        for sa_index in sa_table.indexes:
            yield self.build_index(sa_index)

    def generate_triggers(self, sa_table: schema.Table) -> Iterator[ComdabTrigger]:
        yield from ()  # No database-agnostic implementation

    def build_column(self, sa_column: schema.Column[Any]) -> ComdabColumn:
        if sa_column.nullable is None:
            raise ComdabInternalError("Reflected columns should always have nullability defined")
        match sa_column.server_default:
            case None:
                default = generation_expression = None
            case schema.DefaultClause():
                default = _compile(sa_column.server_default.arg)
                generation_expression = None
            case schema.Computed():
                default = None
                generation_expression = _compile(sa_column.server_default.sqltext)
            case _:
                raise ComdabInternalError(f"Unexpected value in Column.server_default: {sa_column.server_default}")

        return ComdabColumn(
            name=sa_column.name,
            type=self.build_type(sa_column.type),
            nullable=sa_column.nullable,
            default=default,
            generation_expression=generation_expression,
            extra=dict(sa_column.dialect_kwargs),
        )

    def build_constraint(self, sa_constraint: schema.Constraint) -> ComdabConstraint:
        name = sa_constraint.name
        if not isinstance(name, str):
            raise ComdabInternalError("Reflected constraints should always have a name defined")
        extra = dict[str, Any](sa_constraint.dialect_kwargs)

        match sa_constraint:
            case schema.UniqueConstraint():
                return ComdabUniqueConstraint(
                    name=name,
                    columns={col.name for col in sa_constraint.columns},
                    deferrable=sa_constraint.deferrable,
                    initially=sa_constraint.initially,
                    extra=extra,
                )
            case schema.PrimaryKeyConstraint():
                return ComdabPrimaryKeyConstraint(
                    name=name,
                    columns={col.name for col in sa_constraint.columns},
                    deferrable=sa_constraint.deferrable,
                    initially=sa_constraint.initially,
                    extra=extra,
                )
            case schema.ForeignKeyConstraint():
                return ComdabForeignKeyConstraint(
                    name=name,
                    columns_mapping={elt.parent.name: elt.target_fullname for elt in sa_constraint.elements},
                    on_update=sa_constraint.onupdate,
                    on_delete=sa_constraint.ondelete,
                    deferrable=sa_constraint.deferrable,
                    initially=sa_constraint.initially,
                    extra=extra,
                )
            case schema.CheckConstraint():
                return ComdabCheckConstraint(
                    name=name,
                    sql_text=_compile(sa_constraint.sqltext),
                    deferrable=sa_constraint.deferrable,
                    initially=sa_constraint.initially,
                    extra=extra,
                )
            case _:
                raise ComdabInternalError(f"Unexpected SQLAlchemy Constraint type: {type(sa_constraint)}")

    def build_index(self, sa_index: schema.Index) -> ComdabIndex:
        if not sa_index.name:
            raise ComdabInternalError("Reflected indexes should always have a name defined")
        return ComdabIndex(
            name=sa_index.name,
            expressions=[_compile(expr) for expr in sa_index.expressions],
            unique=sa_index.unique,
            extra=dict(sa_index.dialect_kwargs),
        )

    # Level 3

    def build_type(self, sa_type: types.TypeEngine[Any]) -> ComdabType:
        implem_name = type(sa_type).__name__
        match sa_type:
            case types.Enum():  # Subclass of String -> must appear first
                return ComdabTypes.Enum(
                    implem_name=implem_name,
                    values=set(sa_type.enums),
                    type_name=f"{sa_type.schema}.{sa_type.name}" if sa_type.schema else sa_type.name,
                    collation=sa_type.collation,
                )
            case types.String():
                return ComdabTypes.String(implem_name=implem_name, length=sa_type.length, collation=sa_type.collation)
            case types.Integer():
                return ComdabTypes.Integer(implem_name=implem_name)
            case types.Float():  # Subclass of Numeric -> must appear first
                return ComdabTypes.Float(implem_name=implem_name)
            case types.Numeric():
                return ComdabTypes.Numeric(implem_name=implem_name, precision=sa_type.precision, scale=sa_type.scale)
            case types.Boolean():
                return ComdabTypes.Boolean(implem_name=implem_name)
            case types.DateTime():
                return ComdabTypes.DateTime(implem_name=implem_name, with_timezone=sa_type.timezone)
            case types.Date():
                return ComdabTypes.Date(implem_name=implem_name)
            case types.Time():
                return ComdabTypes.Time(implem_name=implem_name)
            case types.Interval():
                return ComdabTypes.Interval(
                    implem_name=implem_name,
                    second_precision=sa_type.second_precision,
                    day_precision=sa_type.day_precision,
                )
            case types.JSON():
                return ComdabTypes.JSON(implem_name=implem_name)
            case types.BINARY():
                return ComdabTypes.Binary(implem_name=implem_name, length=sa_type.length)
            case types.UUID():
                return ComdabTypes.UUID(implem_name=implem_name)
            case types.ARRAY():
                return ComdabTypes.Array(
                    implem_name=implem_name,
                    item_type=self.build_type(sa_type.item_type),
                    dimensions=sa_type.dimensions or 1,
                )
            case _ if self.allow_unknown_types:
                return ComdabTypes.Unknown(implem_name=implem_name)
            case _:
                raise UnhandledTypeError(f"Unhandled SQL type: {type(sa_type)} ({implem_name})")


def _compile(sql_text: str | ClauseElement) -> str:
    if isinstance(sql_text, str):
        return sql_text
    return str(sql_text.compile(compile_kwargs={"literal_binds": True}))

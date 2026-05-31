from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from comdab.exceptions import ComdabInternalError
from comdab.models.base import ComdabModel
from comdab.models.column import ComdabColumn
from comdab.models.constraint import (
    ComdabCheckConstraint,
    ComdabConstraint,
    ComdabConstraintType,
    ComdabExcludeConstraint,
    ComdabForeignKeyConstraint,
    ComdabPrimaryKeyConstraint,
    ComdabUniqueConstraint,
)
from comdab.models.custom_type import ComdabCustomType
from comdab.models.function import ComdabFunction
from comdab.models.index import ComdabIndex
from comdab.models.schema import ROOT, ComdabSchema
from comdab.models.sequence import ComdabSequence
from comdab.models.table import ComdabTable
from comdab.models.trigger import ComdabTrigger
from comdab.models.type import ComdabType
from comdab.models.view import ComdabView
from comdab.path import ComdabPath
from comdab.report import ComdabReport

type _ReportGetter = Callable[[ComdabReport], object]
_path_to_migration_func_spec = dict[ComdabPath, tuple[str, dict[str, _ReportGetter]]]()


def _register[MF: Callable[..., None]](path: ComdabPath, **kwargs: _ReportGetter) -> Callable[[MF], MF]:
    def _decorator(func: MF) -> MF:
        if path in _path_to_migration_func_spec:
            raise ValueError(f"Migration already registered for {path}: {_path_to_migration_func_spec[path]}")

        _path_to_migration_func_spec[path] = (func.__name__, kwargs)
        func._registered_path = path  # pyright: ignore[reportFunctionMemberAccess]  # used for tests only
        func._registered_kwargs = kwargs  # pyright: ignore[reportFunctionMemberAccess]  # used for tests only
        return func

    return _decorator


def _get_only_value(obj: object) -> object:
    if not isinstance(obj, dict) or len(obj) != 1:
        raise ComdabInternalError(f"Expected a left_only/right_only dictionary, got {obj}")
    return next(iter(obj.values()))  # pyright: ignore[reportUnknownVariableType]


def _right_only_value(report: ComdabReport) -> object:
    return _get_only_value(report.right)


def _left_only_value(report: ComdabReport) -> object:
    return _get_only_value(report.left)


def _right(report: ComdabReport) -> object:
    return report.right


def _left(report: ComdabReport) -> object:
    return report.left


class MigrationGeneratorPort(ABC):
    """Abstract base class to generate migrations based on *comdab* reports.

    Inherit this class and implement every method with your migration
    generation backend, then pass it to :func:`generate_migrations`.
    """

    def __init_subclass__(cls, *, strict: bool = True, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.__strict = strict

    def __default_impl(self) -> None:
        if self.__strict:
            raise NotImplementedError(f"{type(self).__name__} doesn't implement this migration!")

    # Level 1

    @abstractmethod
    @_register(ROOT.tables.right_only, table=_right_only_value)
    def create_table(self, *, table: ComdabTable) -> None:
        """Create a new table."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables.left_only, table=_left_only_value)
    def drop_table(self, *, table: ComdabTable) -> None:
        """Drop a table."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.views.right_only, view=_right_only_value)
    def create_view(self, *, view: ComdabView) -> None:
        """Create a new view."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.views.left_only, view=_left_only_value)
    def drop_view(self, *, view: ComdabView) -> None:
        """Drop a view."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences.right_only, sequence=_right_only_value)
    def create_sequence(self, *, sequence: ComdabSequence) -> None:
        """Create a new sequence."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences.left_only, sequence=_left_only_value)
    def drop_sequence(self, *, sequence: ComdabSequence) -> None:
        """Drop a sequence."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.functions.right_only, function=_right_only_value)
    def create_function(self, *, function: ComdabFunction) -> None:
        """Create a new function."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.functions.left_only, function=_left_only_value)
    def drop_function(self, *, function: ComdabFunction) -> None:
        """Drop a function."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.custom_types.right_only, custom_type=_right_only_value)
    def create_custom_type(self, *, custom_type: ComdabCustomType) -> None:
        """Create a new custom type."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.custom_types.left_only, custom_type=_left_only_value)
    def drop_custom_type(self, *, custom_type: ComdabCustomType) -> None:
        """Drop a custom type."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.extra, old_extra=_left, new_extra=_right)
    def alter_schema_extra(self, *, old_extra: dict[str, Any], new_extra: dict[str, Any]) -> None:
        """Change some dialect-specific schema options."""
        self.__default_impl()

    # Level 2

    @abstractmethod
    @_register(ROOT.tables[...].columns.right_only, column=_right_only_value)
    def create_column(self, *, table: ComdabTable, column: ComdabColumn) -> None:
        """Create a new column."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].columns.left_only, column=_left_only_value)
    def drop_column(self, *, table: ComdabTable, column: ComdabColumn) -> None:
        """Drop a column."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints.right_only, constraint=_right_only_value)
    def create_constraint(self, *, table: ComdabTable, constraint: ComdabConstraint) -> None:
        """Create a new constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints.left_only, constraint=_left_only_value)
    def drop_constraint(self, *, table: ComdabTable, constraint: ComdabConstraint) -> None:
        """Drop a constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].indexes.right_only, index=_right_only_value)
    def create_index(self, *, table: ComdabTable, index: ComdabIndex) -> None:
        """Create a new index."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].indexes.left_only, index=_left_only_value)
    def drop_index(self, *, table: ComdabTable, index: ComdabIndex) -> None:
        """Drop a index."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].triggers.right_only, trigger=_right_only_value)
    def create_trigger(self, *, table: ComdabTable, trigger: ComdabTrigger) -> None:
        """Create a new trigger."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].triggers.left_only, trigger=_left_only_value)
    def drop_trigger(self, *, table: ComdabTable, trigger: ComdabTrigger) -> None:
        """Drop a trigger."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].extra, old_extra=_left, new_extra=_right)
    def alter_table_extra(self, *, table: ComdabTable, old_extra: dict[str, Any], new_extra: dict[str, Any]) -> None:
        """Change some dialect-specific table options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.views[...].definition, old_definition=_left, new_definition=_right)
    def alter_view_definition(self, *, view: ComdabView, old_definition: str, new_definition: str) -> None:
        """Change a view definition."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.views[...].materialized, old_materialized=_left, new_materialized=_right)
    def alter_view_materialized(self, *, view: ComdabView, old_materialized: bool, new_materialized: bool) -> None:
        """Change whether a view is materialized."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.views[...].extra, old_extra=_left, new_extra=_right)
    def alter_view_extra(self, *, view: ComdabView, old_extra: dict[str, Any], new_extra: dict[str, Any]) -> None:
        """Change some dialect-specific view options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].type_name, old_type_name=_left, new_type_name=_right)
    def alter_sequence_type_name(self, *, sequence: ComdabSequence, old_type_name: str, new_type_name: str) -> None:
        """Change a sequence type."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].start, old_start=_left, new_start=_right)
    def alter_sequence_start(self, *, sequence: ComdabSequence, old_start: int, new_start: int) -> None:
        """Change a sequence start point."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].increment, old_increment=_left, new_increment=_right)
    def alter_sequence_increment(self, *, sequence: ComdabSequence, old_increment: int, new_increment: int) -> None:
        """Change a sequence increment."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].min, old_min=_left, new_min=_right)
    def alter_sequence_min(self, *, sequence: ComdabSequence, old_min: int, new_min: int) -> None:
        """Change a sequence minimal value."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].max, old_max=_left, new_max=_right)
    def alter_sequence_max(self, *, sequence: ComdabSequence, old_max: int, new_max: int) -> None:
        """Change a sequence maximal value."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].cycle, old_cycle=_left, new_cycle=_right)
    def alter_sequence_cycle(self, *, sequence: ComdabSequence, old_cycle: bool, new_cycle: bool) -> None:
        """Change whether a sequence cycles."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.sequences[...].extra, old_extra=_left, new_extra=_right)
    def alter_sequence_extra(
        self, *, sequence: ComdabSequence, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific sequence options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.functions[...].definition, old_definition=_left, new_definition=_right)
    def alter_function_definition(self, *, function: ComdabFunction, old_definition: str, new_definition: str) -> None:
        """Change a function definition."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.functions[...].extra, old_extra=_left, new_extra=_right)
    def alter_function_extra(
        self, *, function: ComdabFunction, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific function options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.custom_types[...].values, old_values=_left, new_values=_right)
    def alter_custom_type_values(
        self, *, custom_type: ComdabCustomType, old_values: list[str], new_values: list[str]
    ) -> None:
        """Change the values of a custom type."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.custom_types[...].extra, old_extra=_left, new_extra=_right)
    def alter_custom_type_extra(
        self, *, custom_type: ComdabCustomType, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific custom type options."""
        self.__default_impl()

    # Level 3

    @abstractmethod
    @_register(ROOT.tables[...].columns[...].type, old_type=_left, new_type=_right)
    def alter_column_type(
        self, *, table: ComdabTable, column: ComdabColumn, old_type: ComdabType, new_type: ComdabType
    ) -> None:
        """Change a column type."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].columns[...].nullable, old_nullable=_left, new_nullable=_right)
    def alter_column_nullable(
        self, *, table: ComdabTable, column: ComdabColumn, old_nullable: bool, new_nullable: bool
    ) -> None:
        """Change the nullability of a column."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].columns[...].default, old_type=_left, new_type=_right)
    def alter_column_default(
        self, *, table: ComdabTable, column: ComdabColumn, old_type: str | None, new_type: str | None
    ) -> None:
        """Change the default value of a column."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].columns[...].generation_expression, old_expr=_left, new_expr=_right)
    def alter_column_generation_expression(
        self, *, table: ComdabTable, column: ComdabColumn, old_expr: str | None, new_expr: str | None
    ) -> None:
        """Change the generation expression of a column."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].columns[...].extra, old_extra=_left, new_extra=_right)
    def alter_column_extra(
        self, *, table: ComdabTable, column: ComdabColumn, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific column options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].type, old_type=_left, new_type=_right)
    def alter_constraint_type(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabConstraint,
        old_type: ComdabConstraintType,
        new_type: ComdabConstraintType,
    ) -> None:
        """Change a constraint type."""  # TODO: should it be considered a delete + create instead?
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].deferrable, old_deferrable=_left, new_deferrable=_right)
    def alter_constraint_deferrable(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabConstraint,
        old_deferrable: bool | None,
        new_deferrable: bool | None,
    ) -> None:
        """Change whether a constraint can be deferred."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].initially, old_initially=_left, new_initially=_right)
    def alter_constraint_initially(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabConstraint,
        old_initially: str | None,
        new_initially: str | None,
    ) -> None:
        """Change a constraint initial state."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].extra, old_extra=_left, new_extra=_right)
    def alter_constraint_extra(
        self, *, table: ComdabTable, constraint: ComdabConstraint, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific constraint options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].columns, old_columns=_left, new_columns=_right)
    def alter_constraint_columns(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabPrimaryKeyConstraint | ComdabUniqueConstraint,
        old_columns: set[str],
        new_columns: set[str],
    ) -> None:
        """Change a PK / unique constraint columns."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].columns_mapping, old_columns_mapping=_left, new_columns_mapping=_right)
    def alter_constraint_columns_mapping(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabForeignKeyConstraint,
        old_columns_mapping: dict[str, str],
        new_columns_mapping: dict[str, str],
    ) -> None:
        """Change the columns mapping of a foreign key constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].on_update, old_on_update=_left, new_on_update=_right)
    def alter_constraint_on_update(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabForeignKeyConstraint,
        old_on_update: str | None,
        new_on_update: str | None,
    ) -> None:
        """Change the ON UPDATE clause of a foreign key constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].on_delete, old_on_delete=_left, new_on_delete=_right)
    def alter_constraint_on_delete(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabForeignKeyConstraint,
        old_on_delete: str | None,
        new_on_delete: str | None,
    ) -> None:
        """Change the ON DELETE clause of a foreign key constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].constraints[...].sql_text, old_sql_text=_left, new_sql_text=_right)
    def alter_constraint_sql_text(
        self, *, table: ComdabTable, constraint: ComdabCheckConstraint, old_sql_text: str, new_sql_text: str
    ) -> None:
        """Change the clause of a check constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(
        ROOT.tables[...].constraints[...].attributes_and_operators,
        old_attributes_and_operators=_left,
        new_attributes_and_operators=_right,
    )
    def alter_constraint_attributes_and_operators(
        self,
        *,
        table: ComdabTable,
        constraint: ComdabExcludeConstraint,
        old_attributes_and_operators: list[tuple[str, str]],
        new_attributes_and_operators: list[tuple[str, str]],
    ) -> None:
        """Change the attributes and operators of a exclusion constraint."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].indexes[...].expressions, old_expressions=_left, new_expressions=_right)
    def alter_index_expressions(
        self, *, table: ComdabTable, index: ComdabIndex, old_expressions: list[str], new_expressions: list[str]
    ) -> None:
        """Change the expressions of an index."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].indexes[...].unique, old_unique=_left, new_unique=_right)
    def alter_index_unique(self, *, table: ComdabTable, index: ComdabIndex, old_unique: bool, new_unique: bool) -> None:
        """Change if an index is unique."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].indexes[...].extra, old_extra=_left, new_extra=_right)
    def alter_index_extra(
        self, *, table: ComdabTable, index: ComdabIndex, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific index options."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].triggers[...].definition, old_definition=_left, new_definition=_right)
    def alter_trigger_definition(
        self, *, table: ComdabTable, trigger: ComdabTrigger, old_definition: str, new_definition: str
    ) -> None:
        """Change a trigger definition."""
        self.__default_impl()

    @abstractmethod
    @_register(ROOT.tables[...].triggers[...].extra, old_extra=_left, new_extra=_right)
    def alter_trigger_extra(
        self, *, table: ComdabTable, trigger: ComdabTrigger, old_extra: dict[str, Any], new_extra: dict[str, Any]
    ) -> None:
        """Change some dialect-specific trigger options."""
        self.__default_impl()


PartialMigrationGeneratorPort = type(
    "PartialMigrationGeneratorPort",
    (MigrationGeneratorPort,),
    {
        method: lambda self, *a, _m=method, **kw: getattr(super(PartialMigrationGeneratorPort, self), _m)(*a, **kw)  # pyright: ignore[reportUnknownLambdaType]
        for method, _ in _path_to_migration_func_spec.values()
    },
)


_path_dict_to_migration_function_kwarg = {
    "tables": "table",
    "views": "view",
    "sequences": "sequence",
    "functions": "function",
    "custom_types": "custom_type",
    "columns": "column",
    "constraints": "constraint",
    "indexes": "index",
    "triggers": "trigger",
}


def generate_migration(target_schema: ComdabSchema, report: ComdabReport, generator: MigrationGeneratorPort) -> None:
    # Get the migration function corresponding to this report
    path_template, keys = report.path.to_template()
    try:
        func_name, kwargs_getters = _path_to_migration_func_spec[path_template]
    except KeyError:
        raise ComdabInternalError(f"Comdab report not handed by the migration system: {report}") from None

    # Retrieve table/column/... object from the target schema, to pass them to the migration function
    object_kwargs = dict[str, ComdabModel]()
    table: ComdabTable | None = None
    for dict_attr, dict_key in keys.items():
        try:
            match dict_attr:
                case "tables":
                    object_kwargs["table"] = table = target_schema.tables[dict_key]
                case "views" | "sequences" | "functions" | "custom_types":
                    key = _path_dict_to_migration_function_kwarg[dict_attr]
                    object_kwargs[key] = getattr(target_schema, dict_attr)[dict_key]
                case "columns" | "constraints" | "indexes" | "triggers":
                    key = _path_dict_to_migration_function_kwarg[dict_attr]
                    if not table:
                        raise ComdabInternalError(f"Malformed path (cannot have a {key} not in a table): {report.path}")
                    object_kwargs[key] = getattr(table, dict_attr)[dict_key]
                case _:
                    raise ComdabInternalError(f"Unhandled path dictionary: {dict_attr}")
        except KeyError:
            raise ComdabInternalError(
                f"Object referenced in report not in target_schema {dict_attr}: {report.path}"
            ) from None

    # Call the migration function
    migration_func = getattr(generator, func_name)
    migration_func(**object_kwargs, **{key: getter(report) for key, getter in kwargs_getters.items()})

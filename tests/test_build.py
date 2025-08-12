from datetime import datetime
from typing import cast
from unittest import mock

import pytest
import sqlalchemy.schema
from sqlalchemy import (
    ARRAY,
    BIGINT,
    BINARY,
    BOOLEAN,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    JSON,
    SMALLINT,
    UUID,
    VARCHAR,
    CheckConstraint,
    Computed,
    Connection,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Interval,
    MetaData,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from comdab.build import ComdabBuilder
from comdab.exceptions import UnhandledTypeError
from comdab.models import (
    ComdabCheckConstraint,
    ComdabColumn,
    ComdabForeignKeyConstraint,
    ComdabIndex,
    ComdabPrimaryKeyConstraint,
    ComdabSchema,
    ComdabTable,
    ComdabTypes,
    ComdabUniqueConstraint,
)
from comdab.models.type import ComdabType
from comdab.source import ComdabSource


def _build_offline(test_meta: MetaData, *, allow_unknown_types: bool = False) -> ComdabSchema:
    # To avoid the need of a real DB for testing, we mock MetaData.reflect
    # Some end-to-end test without this would be great too
    with mock.patch.object(sqlalchemy.schema, "MetaData") as metadata_mock:
        metadata_mock.return_value = test_meta
        with mock.patch.object(test_meta, "reflect") as reflect_mock:
            builder = ComdabBuilder(
                source=ComdabSource(connection=cast(Connection, "fake_connection"), schema_name="foo"),
                allow_unknown_types=allow_unknown_types,
            )
            schema = builder.build_schema()

    metadata_mock.assert_called_once_with()
    reflect_mock.assert_called_once_with(
        bind="fake_connection",
        views=False,
        schema="foo",
        resolve_fks=False,
    )
    return schema


def test_empty_metadata(meta: MetaData) -> None:
    assert _build_offline(meta) == ComdabSchema(
        tables={},
        views={},
        sequences={},
        functions={},
        custom_types={},
    )


def test_basic(meta: MetaData) -> None:
    meta.info = {"hello": 3, "bye": 2}

    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"
        __table_args__ = {"mydialect_hello": 4, "mydialect_bye": 5}

        id: Mapped[int] = mapped_column(primary_key=True)

    assert _build_offline(meta) == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1", deferrable=None, initially=None, columns={"id"}
                    ),
                },
                indexes={},
                triggers={},
                extra={"mydialect_hello": 4, "mydialect_bye": 5},
            )
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
        extra={"hello": 3, "bye": 2},
    )


def test_column_attributes(meta: MetaData) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str | None] = mapped_column(md_xtra1=6, md_xtra2=7)
        cool: Mapped[bool] = mapped_column(server_default=true())
        when: Mapped[datetime] = mapped_column(Computed(func.current_timestamp()))

    assert _build_offline(meta) == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(length=None, collation=None, implem_name="String"),
                        nullable=True,
                        default=None,
                        generation_expression=None,
                        extra={"md_xtra1": 6, "md_xtra2": 7},
                    ),
                    "cool": ComdabColumn(
                        name="cool",
                        type=ComdabTypes.Boolean(implem_name="Boolean"),
                        nullable=False,
                        default="true",
                        generation_expression=None,
                    ),
                    "when": ComdabColumn(
                        name="when",
                        type=ComdabTypes.DateTime(with_timezone=False, implem_name="DateTime"),
                        nullable=False,
                        default=None,
                        generation_expression="CURRENT_TIMESTAMP",
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1", deferrable=None, initially=None, columns={"id"}
                    ),
                },
                indexes={},
                triggers={},
            )
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
    )


def test_constraints(meta: MetaData) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str | None] = mapped_column(unique=True)

    class _Table2(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_2"

        id: Mapped[int] = mapped_column(primary_key=True)
        id_too: Mapped[bool] = mapped_column(primary_key=True)
        t1_id: Mapped[int] = mapped_column(Integer(), ForeignKey("table_1.id"))
        t1_name: Mapped[str | None] = mapped_column()

        __table_args__ = (
            ForeignKeyConstraint(
                (t1_id, t1_name),
                ("table_1.id", "table_1.name"),
                onupdate="DELETE",
                ondelete="RESTRICT",
                deferrable=True,
                initially="DEFERRED",
                my_xtra1=8,
                my_xtra2=9,
            ),
            UniqueConstraint(
                id,
                t1_id,
                name="custom_unique_constraint",
                deferrable=True,
                initially="DEFERRED",
                my_xtra1=10,
                my_xtra2=11,
            ),
            CheckConstraint(
                func.char_length(t1_name),
                name="custom_ckc",
                deferrable=True,
                initially="DEFERRED",
                my_xtra1=12,
                my_xtra2=13,
            ),
        )

    assert _build_offline(meta) == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(length=None, collation=None, implem_name="String"),
                        nullable=True,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1", deferrable=None, initially=None, columns={"id"}
                    ),
                    "uq_table_1_name": ComdabUniqueConstraint(
                        name="uq_table_1_name", deferrable=None, initially=None, columns={"name"}
                    ),
                },
                indexes={},
                triggers={},
                extra={},
            ),
            "table_2": ComdabTable(
                name="table_2",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "id_too": ComdabColumn(
                        name="id_too",
                        type=ComdabTypes.Boolean(implem_name="Boolean"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "t1_id": ComdabColumn(
                        name="t1_id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "t1_name": ComdabColumn(
                        name="t1_name",
                        type=ComdabTypes.String(length=None, collation=None, implem_name="String"),
                        nullable=True,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "pk_table_2": ComdabPrimaryKeyConstraint(
                        name="pk_table_2", deferrable=None, initially=None, columns={"id", "id_too"}
                    ),
                    "fk_table_2_t1_id": ComdabForeignKeyConstraint(
                        name="fk_table_2_t1_id",
                        deferrable=None,
                        initially=None,
                        columns_mapping={"t1_id": "table_1.id"},
                        on_update=None,
                        on_delete=None,
                    ),
                    "fk_table_2_t1_idt1_name": ComdabForeignKeyConstraint(
                        name="fk_table_2_t1_idt1_name",
                        deferrable=True,
                        initially="DEFERRED",
                        columns_mapping={"t1_id": "table_1.id", "t1_name": "table_1.name"},
                        on_update="DELETE",
                        on_delete="RESTRICT",
                        extra={"my_xtra1": 8, "my_xtra2": 9},
                    ),
                    "custom_unique_constraint": ComdabUniqueConstraint(
                        name="custom_unique_constraint",
                        deferrable=True,
                        initially="DEFERRED",
                        columns={"id", "t1_id"},
                        extra={"my_xtra1": 10, "my_xtra2": 11},
                    ),
                    "ck_table_2_custom_ckc": ComdabCheckConstraint(
                        name="ck_table_2_custom_ckc",
                        deferrable=True,
                        initially="DEFERRED",
                        sql_text="char_length(table_2.t1_name)",
                        extra={"my_xtra1": 12, "my_xtra2": 13},
                    ),
                },
                indexes={},
                triggers={},
            ),
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
    )


def test_indexes(meta: MetaData) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(index=True)

        __table_args__ = (Index("my_custom_index", id, func.char_length(name), unique=True, my_xtra1=14, my_xtra2=15),)

    assert _build_offline(meta) == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(length=None, collation=None, implem_name="String"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1", deferrable=None, initially=None, columns={"id"}
                    ),
                },
                indexes={
                    "ix_table_1_name": ComdabIndex(name="ix_table_1_name", expressions=["table_1.name"], unique=False),
                    "my_custom_index": ComdabIndex(
                        name="my_custom_index",
                        expressions=["table_1.id", "char_length(table_1.name)"],
                        unique=True,
                        extra={"my_xtra1": 14, "my_xtra2": 15},
                    ),
                },
                triggers={},
            )
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
    )


def test_types(meta: MetaData) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id = mapped_column(BIGINT(), primary_key=True)
        name = mapped_column(VARCHAR(length=12, collation="fr-FR"))
        skill = mapped_column(FLOAT())
        money = mapped_column(DECIMAL(precision=3, scale=5))
        cool = mapped_column(BOOLEAN())
        when = mapped_column(DATETIME(timezone=True))
        day = mapped_column(DATE())
        interval_default = mapped_column(Interval())
        interval_custom = mapped_column(Interval(second_precision=3, day_precision=12))
        extra = mapped_column(JSON())
        picture = mapped_column(BINARY(length=256))
        server_id = mapped_column(UUID())
        nums = mapped_column(ARRAY(SMALLINT()))
        bosonic_time = mapped_column(ARRAY(DATETIME(timezone=True), dimensions=26))
        status = mapped_column(Enum("one", "two", name="my_cool_enum"))
        external_status = mapped_column(
            Enum("foo", "BAR", "baz", name="other_cool_enum", schema="other", collation="de-DE")
        )

    def _column(name: str, type: ComdabType) -> dict[str, ComdabColumn]:
        return {
            name: ComdabColumn(name=name, type=type, nullable=name != "id", default=None, generation_expression=None)
        }

    assert _build_offline(meta) == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    **_column("id", ComdabTypes.Integer(implem_name="BIGINT")),
                    **_column("name", ComdabTypes.String(implem_name="VARCHAR", length=12, collation="fr-FR")),
                    **_column("skill", ComdabTypes.Float(implem_name="FLOAT")),
                    **_column("money", ComdabTypes.Numeric(implem_name="DECIMAL", precision=3, scale=5)),
                    **_column("cool", ComdabTypes.Boolean(implem_name="BOOLEAN")),
                    **_column("when", ComdabTypes.DateTime(implem_name="DATETIME", with_timezone=True)),
                    **_column("day", ComdabTypes.Date(implem_name="DATE")),
                    **_column(
                        "interval_default",
                        ComdabTypes.Interval(implem_name="Interval", day_precision=None, second_precision=None),
                    ),
                    **_column(
                        "interval_custom",
                        ComdabTypes.Interval(implem_name="Interval", day_precision=12, second_precision=3),
                    ),
                    **_column("extra", ComdabTypes.JSON(implem_name="JSON")),
                    **_column("picture", ComdabTypes.Binary(implem_name="BINARY", length=256)),
                    **_column("server_id", ComdabTypes.UUID(implem_name="UUID")),
                    **_column(
                        "nums",
                        ComdabTypes.Array(
                            implem_name="ARRAY", item_type=ComdabTypes.Integer(implem_name="SMALLINT"), dimensions=1
                        ),
                    ),
                    **_column(
                        "bosonic_time",
                        ComdabTypes.Array(
                            implem_name="ARRAY",
                            item_type=ComdabTypes.DateTime(implem_name="DATETIME", with_timezone=True),
                            dimensions=26,
                        ),
                    ),
                    **_column(
                        "status",
                        ComdabTypes.Enum(
                            implem_name="Enum",
                            values={"one", "two"},
                            type_name="my_cool_enum",
                            collation=None,
                        ),
                    ),
                    **_column(
                        "external_status",
                        ComdabTypes.Enum(
                            implem_name="Enum",
                            values={"foo", "BAR", "baz"},
                            type_name="other.other_cool_enum",
                            collation=None,  # collation="de-DE",  -- TODO: doesn't work, investigate?
                        ),
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1", deferrable=None, initially=None, columns={"id"}
                    ),
                },
                indexes={},
                triggers={},
            )
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
    )


def test_unknown_types(meta: MetaData) -> None:
    class CustomDateTime(TypeDecorator[datetime]):
        impl = DateTime

    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        when: Mapped[datetime] = mapped_column(CustomDateTime(timezone=True))

    with pytest.raises(UnhandledTypeError):
        _build_offline(meta)

    assert _build_offline(meta, allow_unknown_types=True) == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="Integer"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "when": ComdabColumn(
                        name="when",
                        type=ComdabTypes.Unknown(implem_name="CustomDateTime"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1", deferrable=None, initially=None, columns={"id"}
                    ),
                },
                indexes={},
                triggers={},
            )
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
    )

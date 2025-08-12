import os
import shutil
import subprocess
from collections.abc import Iterator
from importlib.util import find_spec
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import (
    ARRAY,
    URL,
    Connection,
    Engine,
    Enum,
    MetaData,
    Sequence,
    create_engine,
)
from sqlalchemy.dialects.postgresql import DATERANGE, HSTORE, ExcludeConstraint, ranges
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.ddl import CreateSequence

from comdab.models.column import ComdabColumn
from comdab.models.constraint import ComdabExcludeConstraint, ComdabPrimaryKeyConstraint
from comdab.models.custom_type import ComdabCustomType
from comdab.models.function import ComdabFunction
from comdab.models.schema import ComdabSchema
from comdab.models.sequence import ComdabSequence
from comdab.models.table import ComdabTable
from comdab.models.trigger import ComdabTrigger
from comdab.models.type import ComdabType, ComdabTypes
from comdab.models.view import ComdabView
from comdab.source import ComdabSource
from comdab.specific.postgresql.build import ComdabPostgreSQLBuilder

TEST_DB_PORT = int(os.environ.get("COMDAB_TEST_DB_PORT", 5439))


@pytest.fixture(scope="session")
def pg_ctl() -> str:
    pg_ctl = shutil.which("pg_ctl")
    if not pg_ctl:
        pytest.skip(reason="PostgreSQL binaries not available!")
    return pg_ctl


@pytest.fixture(scope="session")
def psql_db(pg_ctl: str) -> Iterator[Engine]:
    if not find_spec("psycopg2"):  # Needed by SQLAlchemy to connect to a PostgreSQL database
        pytest.skip("psycopg2 module not installed!")

    server_url = URL.create(
        drivername="postgresql",
        username="test_user",
        host="localhost",
        port=TEST_DB_PORT,
    )

    with TemporaryDirectory() as data_dir:
        subprocess.run([pg_ctl, "initdb", "-D", data_dir, "-o", f"-U {server_url.username}"], check=True)
        subprocess.run([pg_ctl, "start", "-D", data_dir, "-o", f"-F -p {server_url.port}"], check=True)
        try:
            with create_engine(server_url, isolation_level="AUTOCOMMIT").connect() as conn:
                conn.exec_driver_sql("CREATE DATABASE test_db;")
            yield create_engine(server_url._replace(database="test_db"))
        finally:
            subprocess.run([pg_ctl, "stop", "-D", data_dir], check=True)


@pytest.fixture(scope="function")
def connection(psql_db: Engine) -> Iterator[Connection]:
    with psql_db.connect() as conn:
        yield conn


def test_psql_views(meta: MetaData, connection: Connection) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

    meta.create_all(connection)
    connection.exec_driver_sql(
        "CREATE VIEW public._view_1 (id, name_and_id) AS SELECT id, name || id FROM public.table_1;"
    )
    connection.exec_driver_sql(
        "CREATE VIEW public._view_2 (id, id_and_name) AS SELECT id, (id * 2) || name FROM public.table_1;"
    )
    connection.exec_driver_sql(
        "CREATE MATERIALIZED VIEW public._view_3 (id, name_and_id) AS SELECT id, name || (id * 3) FROM public.table_1;"
    )
    connection.exec_driver_sql(
        "CREATE MATERIALIZED VIEW public._view_4 (id, id_and_name) AS SELECT id, (id * 4) || name FROM public.table_1;"
    )
    connection.exec_driver_sql("CREATE SCHEMA other;")
    connection.exec_driver_sql("CREATE VIEW other._view_1 (x) AS SELECT 42;")

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema().views == {
        "_view_1": ComdabView(
            name="_view_1",
            definition="SELECT table_1.id,\n    ((table_1.name)::text || table_1.id) AS name_and_id\n   FROM table_1;",
            materialized=False,
        ),
        "_view_2": ComdabView(
            name="_view_2",
            definition="SELECT table_1.id,\n    ((table_1.id * 2) || (table_1.name)::text) AS id_and_name\n   FROM table_1;",
            materialized=False,
        ),
        "_view_3": ComdabView(
            name="_view_3",
            definition="SELECT table_1.id,\n    ((table_1.name)::text || (table_1.id * 3)) AS name_and_id\n   FROM table_1;",
            materialized=True,
        ),
        "_view_4": ComdabView(
            name="_view_4",
            definition="SELECT table_1.id,\n    ((table_1.id * 4) || (table_1.name)::text) AS id_and_name\n   FROM table_1;",
            materialized=True,
        ),
    }

    other_builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="other"))
    assert other_builder.build_schema().views == {
        "_view_1": ComdabView(name="_view_1", definition="SELECT 42 AS x;", materialized=False)
    }


def test_psql_sequences(meta: MetaData, connection: Connection) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        user_id: Mapped[int] = mapped_column(
            Sequence(name="my_seq", start=3, increment=2, minvalue=3, maxvalue=7, cycle=True)
        )

    meta.create_all(connection)
    connection.exec_driver_sql("CREATE SCHEMA other;")
    connection.execute(CreateSequence(Sequence(name="my_seq", schema="other", maxvalue=20)))

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema().sequences == {
        "table_1_id_seq": ComdabSequence(
            name="table_1_id_seq", type_name="int4", start=1, increment=1, min=1, max=2147483647, cycle=False
        ),
        "my_seq": ComdabSequence(name="my_seq", type_name="int8", start=3, increment=2, min=3, max=7, cycle=True),
    }

    other_builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="other"))
    assert other_builder.build_schema().sequences == {
        "my_seq": ComdabSequence(name="my_seq", type_name="int8", start=1, increment=1, min=1, max=20, cycle=False),
    }


def test_psql_functions(meta: MetaData, connection: Connection) -> None:
    connection.exec_driver_sql("""
        CREATE OR REPLACE FUNCTION public.day_range(start_date date, end_date date) RETURNS SETOF date
        AS
        $fbd$
            SELECT day::date
            FROM generate_series(start_date, end_date, '1 day'::interval) day
        $fbd$ LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE;
    """)
    connection.exec_driver_sql(
        "CREATE OR REPLACE FUNCTION public._huh() RETURNS integer AS $fbd$ SELECT 42;$fbd$ LANGUAGE sql;"
    )
    connection.exec_driver_sql("CREATE SCHEMA other;")
    connection.exec_driver_sql(
        "CREATE OR REPLACE FUNCTION other._huh() RETURNS integer AS $fbd$ SELECT 43;$fbd$ LANGUAGE sql;"
    )

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema().functions == {
        "day_range": ComdabFunction(
            name="day_range",
            definition="CREATE OR REPLACE FUNCTION public.day_range(start_date date, end_date date)\n RETURNS SETOF date\n LANGUAGE sql\n IMMUTABLE PARALLEL SAFE\nAS $function$\n            SELECT day::date\n            FROM generate_series(start_date, end_date, '1 day'::interval) day\n        $function$\n",
        ),
        "_huh": ComdabFunction(
            name="_huh",
            definition="CREATE OR REPLACE FUNCTION public._huh()\n RETURNS integer\n LANGUAGE sql\nAS $function$ SELECT 42;$function$\n",
        ),
    }

    other_builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="other"))
    assert other_builder.build_schema().functions == {
        "_huh": ComdabFunction(
            name="_huh",
            definition="CREATE OR REPLACE FUNCTION other._huh()\n RETURNS integer\n LANGUAGE sql\nAS $function$ SELECT 43;$function$\n",
        ),
    }


def test_psql_exclude_constraints(meta: MetaData, meta_other: MetaData, connection: Connection) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        currency_code: Mapped[str] = mapped_column(primary_key=True)
        range = mapped_column(DATERANGE(), primary_key=True)
        exchange_rate: Mapped[float] = mapped_column()

        __table_args__ = (
            ExcludeConstraint(
                ("currency_code", "="),
                ("range", "&&"),
                name="my_constr",
                using="GIST",
                deferrable=True,
                initially="DEFERRED",
            ),
            ExcludeConstraint(
                ("currency_code", "="),
                ("exchange_rate", "="),
                name="my_constr_2",
                where=currency_code == "EUR",
            ),
        )

    class _Table2(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_2"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

        __table_args__ = (
            ExcludeConstraint(
                ("id", "="),
                ("name", "="),
                name="my_constr_3",
                deferrable=True,
            ),
        )

    class _OtherBaseModel(DeclarativeBase):
        metadata = meta_other

    class _OtherTable(_OtherBaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "other_table"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

        __table_args__ = (
            ExcludeConstraint(
                ("id", "="),
                ("name", "="),
                name="my_constr",
                deferrable=True,
            ),
        )

    connection.exec_driver_sql("CREATE EXTENSION btree_gist;")  # Needed for GIST exclude constraints
    meta.create_all(connection)
    connection.exec_driver_sql("CREATE SCHEMA other;")
    meta_other.create_all(connection)

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema() == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "currency_code": ComdabColumn(
                        name="currency_code",
                        type=ComdabTypes.String(type="String", implem_name="VARCHAR", length=None, collation=None),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "exchange_rate": ComdabColumn(
                        name="exchange_rate",
                        type=ComdabTypes.Float(type="Float", implem_name="DOUBLE_PRECISION"),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                    "range": ComdabColumn(
                        name="range",
                        type=ComdabTypes.Range(
                            type="Range",
                            implem_name="DATERANGE",
                            item_type=ComdabTypes.Date(type="Date", implem_name="DATE"),
                        ),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "my_constr": ComdabExcludeConstraint(
                        type="exclude",
                        name="my_constr",
                        deferrable=True,
                        initially="DEFERRED",
                        attributes_and_operators=[("currency_code", "="), ("range", "&&")],
                        extra={"postgresql_using": "gist"},
                    ),
                    "my_constr_2": ComdabExcludeConstraint(
                        type="exclude",
                        name="my_constr_2",
                        deferrable=False,
                        initially=None,
                        attributes_and_operators=[("currency_code", "="), ("exchange_rate", "=")],
                        extra={"postgresql_using": "gist", "postgresql_where": "((currency_code)::text = 'EUR'::text)"},
                    ),
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_table_1",
                        deferrable=None,
                        initially=None,
                        columns={"range", "currency_code"},
                        extra={"postgresql_include": []},
                    ),
                },
                indexes={},
                triggers={},
            ),
            "table_2": ComdabTable(
                name="table_2",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(type="Integer", implem_name="INTEGER"),
                        nullable=False,
                        default="nextval('\"public\".table_2_id_seq'::regclass)",
                        generation_expression=None,
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(type="String", implem_name="VARCHAR", length=None, collation=None),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "my_constr_3": ComdabExcludeConstraint(
                        type="exclude",
                        name="my_constr_3",
                        deferrable=True,
                        initially=None,
                        extra={"postgresql_using": "gist"},
                        attributes_and_operators=[("id", "="), ("name", "=")],
                    ),
                    "pk_table_2": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_table_2",
                        deferrable=None,
                        initially=None,
                        extra={"postgresql_include": []},
                        columns={"id"},
                    ),
                },
                indexes={},
                triggers={},
            ),
        },
        views={},
        sequences={
            "table_2_id_seq": ComdabSequence(
                name="table_2_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
            )
        },
        functions={},
        custom_types={},
    )

    other_builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="other"))
    assert other_builder.build_schema() == ComdabSchema(
        tables={
            "other_table": ComdabTable(
                name="other_table",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(type="Integer", implem_name="INTEGER"),
                        nullable=False,
                        default="nextval('other.other_table_id_seq'::regclass)",
                        generation_expression=None,
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(type="String", implem_name="VARCHAR", length=None, collation=None),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={
                    "my_constr": ComdabExcludeConstraint(
                        type="exclude",
                        name="my_constr",
                        deferrable=True,
                        initially=None,
                        extra={"postgresql_using": "gist"},
                        attributes_and_operators=[("id", "="), ("name", "=")],
                    ),
                    "pk_other_table": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_other_table",
                        deferrable=None,
                        initially=None,
                        extra={"postgresql_include": []},
                        columns={"id"},
                    ),
                },
                indexes={},
                triggers={},
            )
        },
        views={},
        sequences={
            "other_table_id_seq": ComdabSequence(
                name="other_table_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
            )
        },
        functions={},
        custom_types={},
    )


def test_psql_triggers(meta: MetaData, meta_other: MetaData, connection: Connection) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

    class _Table2(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_2"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

    class _OtherBaseModel(DeclarativeBase):
        metadata = meta_other

    class _OtherTable(_OtherBaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "other_table"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

    meta.create_all(connection)
    connection.exec_driver_sql(
        """CREATE OR REPLACE FUNCTION _update_name() RETURNS trigger
        AS $fbd$
        BEGIN
            NEW.name := NEW.name || '!';
            RETURN NEW;
        END;
        $fbd$ LANGUAGE plpgsql;
        """
    )
    connection.exec_driver_sql(
        """CREATE TRIGGER _on_table_1_update
        BEFORE UPDATE ON public.table_1
        FOR EACH ROW EXECUTE FUNCTION _update_name();
        """
    )
    connection.exec_driver_sql(
        """CREATE TRIGGER _on_table_1_create
        BEFORE INSERT ON public.table_1
        FOR EACH ROW EXECUTE FUNCTION _update_name();
        """
    )
    connection.exec_driver_sql(
        """CREATE TRIGGER _on_table_2_create_or_update
        BEFORE INSERT OR UPDATE ON public.table_2
        FOR EACH ROW EXECUTE FUNCTION _update_name();
        """
    )

    connection.exec_driver_sql("CREATE SCHEMA other;")
    meta_other.create_all(connection)
    connection.exec_driver_sql(
        """CREATE TRIGGER _on_table_1_create
        BEFORE INSERT ON other.other_table
        FOR EACH ROW EXECUTE FUNCTION public._update_name();
        """
    )

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema() == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(type="Integer", implem_name="INTEGER", extra={}),
                        nullable=False,
                        default="nextval('\"public\".table_1_id_seq'::regclass)",
                        generation_expression=None,
                        extra={},
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(
                            type="String", implem_name="VARCHAR", extra={}, length=None, collation=None
                        ),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                        extra={},
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_table_1",
                        deferrable=None,
                        initially=None,
                        extra={"postgresql_include": []},
                        columns={"id"},
                    )
                },
                indexes={},
                triggers={
                    "_on_table_1_create": ComdabTrigger(
                        name="_on_table_1_create",
                        definition="CREATE TRIGGER _on_table_1_create BEFORE INSERT ON public.table_1 FOR EACH ROW EXECUTE FUNCTION _update_name()",
                        extra={},
                    ),
                    "_on_table_1_update": ComdabTrigger(
                        name="_on_table_1_update",
                        definition="CREATE TRIGGER _on_table_1_update BEFORE UPDATE ON public.table_1 FOR EACH ROW EXECUTE FUNCTION _update_name()",
                        extra={},
                    ),
                },
                extra={},
            ),
            "table_2": ComdabTable(
                name="table_2",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(type="Integer", implem_name="INTEGER", extra={}),
                        nullable=False,
                        default="nextval('\"public\".table_2_id_seq'::regclass)",
                        generation_expression=None,
                        extra={},
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(
                            type="String", implem_name="VARCHAR", extra={}, length=None, collation=None
                        ),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                        extra={},
                    ),
                },
                constraints={
                    "pk_table_2": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_table_2",
                        deferrable=None,
                        initially=None,
                        extra={"postgresql_include": []},
                        columns={"id"},
                    )
                },
                indexes={},
                triggers={
                    "_on_table_2_create_or_update": ComdabTrigger(
                        name="_on_table_2_create_or_update",
                        definition="CREATE TRIGGER _on_table_2_create_or_update BEFORE INSERT OR UPDATE ON public.table_2 FOR EACH ROW EXECUTE FUNCTION _update_name()",
                        extra={},
                    )
                },
                extra={},
            ),
        },
        views={},
        sequences={
            "table_1_id_seq": ComdabSequence(
                name="table_1_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
                extra={},
            ),
            "table_2_id_seq": ComdabSequence(
                name="table_2_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
                extra={},
            ),
        },
        functions={
            "_update_name": ComdabFunction(
                name="_update_name",
                definition="CREATE OR REPLACE FUNCTION public._update_name()\n RETURNS trigger\n LANGUAGE plpgsql\nAS $function$\n        BEGIN\n            NEW.name := NEW.name || '!';\n            RETURN NEW;\n        END;\n        $function$\n",
                extra={},
            )
        },
        custom_types={},
        extra={},
    )

    other_builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="other"))
    assert other_builder.build_schema() == ComdabSchema(
        tables={
            "other_table": ComdabTable(
                name="other_table",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(type="Integer", implem_name="INTEGER", extra={}),
                        nullable=False,
                        default="nextval('other.other_table_id_seq'::regclass)",
                        generation_expression=None,
                        extra={},
                    ),
                    "name": ComdabColumn(
                        name="name",
                        type=ComdabTypes.String(
                            type="String", implem_name="VARCHAR", extra={}, length=None, collation=None
                        ),
                        nullable=False,
                        default=None,
                        generation_expression=None,
                        extra={},
                    ),
                },
                constraints={
                    "pk_other_table": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_other_table",
                        deferrable=None,
                        initially=None,
                        extra={"postgresql_include": []},
                        columns={"id"},
                    )
                },
                indexes={},
                triggers={
                    "_on_table_1_create": ComdabTrigger(
                        name="_on_table_1_create",
                        definition="CREATE TRIGGER _on_table_1_create BEFORE INSERT ON other.other_table FOR EACH ROW EXECUTE FUNCTION _update_name()",
                        extra={},
                    )
                },
                extra={},
            )
        },
        views={},
        sequences={
            "other_table_id_seq": ComdabSequence(
                name="other_table_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
                extra={},
            )
        },
        functions={},
        custom_types={},
        extra={},
    )


def test_psql_custom_types(meta: MetaData, connection: Connection) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        status = mapped_column(Enum("one", "two", name="my_cool_enum"))

    meta.create_all(connection)
    Enum("Three (3)", "FOUR", name="my_cool_enum_NEXT").create(connection)  # Unused type

    connection.exec_driver_sql("CREATE SCHEMA other;")
    Enum("five", "6", name="my_cool_enum_other", schema="other").create(connection)

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema() == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(type="Integer", implem_name="INTEGER", extra={}),
                        nullable=False,
                        default="nextval('\"public\".table_1_id_seq'::regclass)",
                        generation_expression=None,
                        extra={},
                    ),
                    "status": ComdabColumn(
                        name="status",
                        type=ComdabTypes.Enum(
                            implem_name="ENUM", values={"one", "two"}, type_name="my_cool_enum", collation=None
                        ),
                        nullable=True,
                        default=None,
                        generation_expression=None,
                        extra={},
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        type="primary_key",
                        name="pk_table_1",
                        deferrable=None,
                        initially=None,
                        extra={"postgresql_include": []},
                        columns={"id"},
                    )
                },
                indexes={},
                triggers={},
                extra={},
            ),
        },
        views={},
        sequences={
            "table_1_id_seq": ComdabSequence(
                name="table_1_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
                extra={},
            ),
        },
        functions={},
        custom_types={
            "my_cool_enum": ComdabCustomType(name="my_cool_enum", values=["one", "two"]),
            "my_cool_enum_NEXT": ComdabCustomType(name="my_cool_enum_NEXT", values=["Three (3)", "FOUR"]),
        },
        extra={},
    )

    other_builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="other"))
    assert other_builder.build_schema() == ComdabSchema(
        tables={},
        views={},
        sequences={},
        functions={},
        custom_types={
            "my_cool_enum_other": ComdabCustomType(name="my_cool_enum_other", values=["five", "6"]),
        },
        extra={},
    )


def test_psql_types(connection: Connection, meta: MetaData) -> None:
    class _BaseModel(DeclarativeBase):
        metadata = meta

    class _Table1(_BaseModel):  # pyright: ignore[reportUnusedClass]
        __tablename__ = "table_1"

        id: Mapped[int] = mapped_column(primary_key=True)
        names = mapped_column(HSTORE())

        int4_range = mapped_column(ranges.INT4RANGE())
        int8_range = mapped_column(ranges.INT8RANGE())
        num_range = mapped_column(ranges.NUMRANGE())
        ts_range = mapped_column(ranges.TSRANGE())
        tstz_range = mapped_column(ranges.TSTZRANGE())
        date_range = mapped_column(ranges.DATERANGE())

        int4_multirange = mapped_column(ranges.INT4MULTIRANGE())
        int8_multirange = mapped_column(ranges.INT8MULTIRANGE())
        num_multirange = mapped_column(ranges.NUMMULTIRANGE())
        ts_multirange = mapped_column(ranges.TSMULTIRANGE())
        tstz_multirange = mapped_column(ranges.TSTZMULTIRANGE())
        date_multirange = mapped_column(ranges.DATEMULTIRANGE())

        array_of_names = mapped_column(ARRAY(HSTORE()))

    connection.exec_driver_sql("CREATE EXTENSION hstore;")
    meta.create_all(connection)

    def _column(name: str, type: ComdabType) -> dict[str, ComdabColumn]:
        return {name: ComdabColumn(name=name, type=type, nullable=True, default=None, generation_expression=None)}

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema() == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="INTEGER"),
                        nullable=False,
                        default="""nextval('"public".table_1_id_seq'::regclass)""",
                        generation_expression=None,
                    ),
                    **_column("names", ComdabTypes.HSTORE(implem_name="HSTORE")),
                    **_column(
                        "int4_range",
                        ComdabTypes.Range(implem_name="INT4RANGE", item_type=ComdabTypes.Integer(implem_name="INT4")),
                    ),
                    **_column(
                        "int8_range",
                        ComdabTypes.Range(implem_name="INT8RANGE", item_type=ComdabTypes.Integer(implem_name="INT8")),
                    ),
                    **_column(
                        "num_range",
                        ComdabTypes.Range(
                            implem_name="NUMRANGE",
                            item_type=ComdabTypes.Numeric(implem_name="NUM", precision=None, scale=None),
                        ),
                    ),
                    **_column(
                        "ts_range",
                        ComdabTypes.Range(
                            implem_name="TSRANGE", item_type=ComdabTypes.DateTime(implem_name="TS", with_timezone=False)
                        ),
                    ),
                    **_column(
                        "tstz_range",
                        ComdabTypes.Range(
                            implem_name="TSTZRANGE",
                            item_type=ComdabTypes.DateTime(implem_name="TSTZ", with_timezone=True),
                        ),
                    ),
                    **_column(
                        "date_range",
                        ComdabTypes.Range(implem_name="DATERANGE", item_type=ComdabTypes.Date(implem_name="DATE")),
                    ),
                    **_column(
                        "int4_multirange",
                        ComdabTypes.MultiRange(
                            implem_name="INT4MULTIRANGE", item_type=ComdabTypes.Integer(implem_name="INT4")
                        ),
                    ),
                    **_column(
                        "int8_multirange",
                        ComdabTypes.MultiRange(
                            implem_name="INT8MULTIRANGE", item_type=ComdabTypes.Integer(implem_name="INT8")
                        ),
                    ),
                    **_column(
                        "num_multirange",
                        ComdabTypes.MultiRange(
                            implem_name="NUMMULTIRANGE",
                            item_type=ComdabTypes.Numeric(implem_name="NUM", precision=None, scale=None),
                        ),
                    ),
                    **_column(
                        "ts_multirange",
                        ComdabTypes.MultiRange(
                            implem_name="TSMULTIRANGE",
                            item_type=ComdabTypes.DateTime(implem_name="TS", with_timezone=False),
                        ),
                    ),
                    **_column(
                        "tstz_multirange",
                        ComdabTypes.MultiRange(
                            implem_name="TSTZMULTIRANGE",
                            item_type=ComdabTypes.DateTime(implem_name="TSTZ", with_timezone=True),
                        ),
                    ),
                    **_column(
                        "date_multirange",
                        ComdabTypes.MultiRange(
                            implem_name="DATEMULTIRANGE", item_type=ComdabTypes.Date(implem_name="DATE")
                        ),
                    ),
                    **_column(
                        "array_of_names",
                        ComdabTypes.Array(
                            implem_name="ARRAY", item_type=ComdabTypes.HSTORE(implem_name="HSTORE"), dimensions=1
                        ),
                    ),
                },
                constraints={
                    "pk_table_1": ComdabPrimaryKeyConstraint(
                        name="pk_table_1",
                        deferrable=None,
                        initially=None,
                        columns={"id"},
                        extra={"postgresql_include": []},
                    ),
                },
                indexes={},
                triggers={},
            )
        },
        views={},
        sequences={
            "table_1_id_seq": ComdabSequence(
                name="table_1_id_seq",
                type_name="int4",
                start=1,
                increment=1,
                min=1,
                max=2147483647,
                cycle=False,
                extra={},
            )
        },
        functions={},
        custom_types={},
    )


def test_no_primary_key_ignore_fake_constraint(connection: Connection) -> None:
    # Not really psql-specific, but needs a DB

    connection.exec_driver_sql("CREATE TABLE table_1 (id INTEGER);")  # no primary key

    builder = ComdabPostgreSQLBuilder(ComdabSource(connection=connection, schema_name="public"))
    assert builder.build_schema() == ComdabSchema(
        tables={
            "table_1": ComdabTable(
                name="table_1",
                columns={
                    "id": ComdabColumn(
                        name="id",
                        type=ComdabTypes.Integer(implem_name="INTEGER"),
                        nullable=True,
                        default=None,
                        generation_expression=None,
                    ),
                },
                constraints={},
                indexes={},
                triggers={},
                extra={},
            ),
        },
        views={},
        sequences={},
        functions={},
        custom_types={},
    )

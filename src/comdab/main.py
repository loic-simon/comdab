from collections.abc import Iterable

from sqlalchemy import Connection
from sqlalchemy.dialects import postgresql

from comdab.build import ComdabBuilder
from comdab.compare import ComdabComparer, ComdabStrategy
from comdab.migrate import MigrationGeneratorPort, generate_migration
from comdab.models.schema import ComdabSchema
from comdab.path import ComdabPath
from comdab.report import ComdabReport
from comdab.source import ComdabSource


def generate_migrations(
    source_connection: Connection,
    target_connection: Connection,
    generator: MigrationGeneratorPort,
    *,
    source_schema: str = "public",
    target_schema: str = "public",
    rules: dict[ComdabPath, ComdabStrategy] | None = None,
    allow_unknown_types: bool = False,
) -> None:
    """Generate migrations from a source schema to a target schema.

    This is the highest-level, all-in-one *comdab* function.

    Args:
        source_connection: A SQLAlchemy :class:`connection <sqlalchemy.engine.Connection>` established
            to the database we want to migrate.
        target_connection: A SQLAlchemy :class:`connection <sqlalchemy.engine.Connection>` established
            to a database with the desired state to reach.
        generator: The :class:`MigrationGeneratorPort` to use to generate migrations after the differences are found.
        source_schema: The name of the database schema to compare for the ``source_connection``.
        target_schema: The name of the database schema to compare for the ``target_connection``.
        rules: An optional set of rules to allow some differences between the schemas,
            or report them as warnings. See :ref:`Ignore rules <ignorerules>` for more details.
        allow_unknown_types: If ``True``, SQL data types not handed (yet) by comdab will be
            modeled as "unknown" and compared based on their name only.  If ``False`` (the default),
            encountering an unknown name will raise an :exc:`UnhandledTypeError`.
    """
    source = build_comdab_schema(
        source_connection,
        schema=source_schema,
        allow_unknown_types=allow_unknown_types,
    )
    target = build_comdab_schema(
        target_connection,
        schema=target_schema,
        allow_unknown_types=allow_unknown_types,
    )
    reports = compare_comdab_schemas(source, target, rules=rules)
    generate_migrations_from_reports(target, reports, generator)


def compare_databases(
    left_connection: Connection,
    right_connection: Connection,
    *,
    left_schema: str = "public",
    right_schema: str = "public",
    rules: dict[ComdabPath, ComdabStrategy] | None = None,
    allow_unknown_types: bool = False,
) -> list[ComdabReport]:
    """Build and compare two database schemas, from their SQLAlchemy connection.

    Args:
        left_connection: A SQLAlchemy :class:`~sqlalchemy.Connection<connection>` established
            to the first database to compare.
        right_connection: A SQLAlchemy :class:`~sqlalchemy.Connection<connection>` established
            to the second database to compare.
        left_schema: The name of the database schema to compare for the ``left_connection``.
        right_schema: The name of the database schema to compare for the ``right_connection``.
        rules: An optional set of rules to allow some differences between the schemas,
            or report them as warnings. See :ref:`Ignore rules <ignorerules>` for more details.
        allow_unknown_types: If ``True``, SQL data types not handed (yet) by comdab will be
            modeled as "unknown" and compared based on their name only.  If ``False`` (the default),
            encountering an unknown name will raise an :exc:`UnhandledTypeError`.
    """
    left = build_comdab_schema(
        left_connection,
        schema=left_schema,
        allow_unknown_types=allow_unknown_types,
    )
    right = build_comdab_schema(
        right_connection,
        schema=right_schema,
        allow_unknown_types=allow_unknown_types,
    )
    return compare_comdab_schemas(left, right, rules=rules)


def build_comdab_schema(
    connection: Connection,
    *,
    schema: str = "public",
    allow_unknown_types: bool = False,
) -> ComdabSchema:
    """Build a database-agnostic, SQLAlchemy-independent representation of a database schema.

    This is the internal representation used for comparison by *comdab*.

    Args:
        connection: A SQLAlchemy :class:`~sqlalchemy.Connection<connection>` established
            to the database to reflect.
        schema: The name of the database schema to reflect.
        allow_unknown_types: If ``True``, SQL data types not handed (yet) by comdab will be
            modeled as "unknown" and compared based on their name only.  If ``False`` (the default),
            encountering an unknown name will raise an :exc:`UnhandledTypeError`.
    """
    source = ComdabSource(connection=connection, schema_name=schema)
    match connection.dialect:
        case postgresql.dialect():
            from comdab.specific.postgresql.build import ComdabPostgreSQLBuilder

            builder = ComdabPostgreSQLBuilder(source, allow_unknown_types=allow_unknown_types)

        case _:
            builder = ComdabBuilder(source, allow_unknown_types=allow_unknown_types)

    return builder.build_schema()


def compare_comdab_schemas(
    left: ComdabSchema,
    right: ComdabSchema,
    *,
    rules: dict[ComdabPath, ComdabStrategy] | None = None,
) -> list[ComdabReport]:
    """Compare two already built database schemas.

    This is a pure function, needing no connection to a database.

    Args:
        left: The first schema to compare, as produced by :func:`build_comdab_schema`.
        right: The second schema to compare, as produced by :func:`build_comdab_schema`.
        rules: An optional set of rules to allow some differences between the schemas,
            or report them as warnings. See :ref:`Ignore rules <ignorerules>` for more details.
    """
    comparer = ComdabComparer(rules=rules)
    return comparer.compare(left, right)


def generate_migrations_from_reports(
    target_schema: ComdabSchema,
    reports: Iterable[ComdabReport],
    generator: MigrationGeneratorPort,
) -> None:
    """Generate migrations from already build *comdab* reports.

    This is the highest-level, all-in-one *comdab* function.

    Args:
        target_schema: The *comdab*-built schema to reach after migrations.
        reports: The *comdab*-built reports of differences between the source and target schemas.
        generator: The :class:`MigrationGeneratorPort` to use to generate migrations from reports.
    """
    for report in reports:  # TODO: ordering...
        generate_migration(target_schema, report, generator)

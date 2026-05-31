from unittest import mock

from sqlalchemy.dialects import mysql, postgresql

from comdab.main import (
    build_comdab_schema,
    compare_comdab_schemas,
    compare_databases,
    generate_migrations,
    generate_migrations_from_reports,
)
from comdab.source import ComdabSource
from tests import _mock_module


def test_generate_migrations() -> None:
    source_connection = mock.Mock()
    target_connection = mock.Mock()
    generator = mock.Mock()
    rules = mock.Mock()

    source = mock.Mock()
    target = mock.Mock()
    reports = [mock.Mock(), mock.Mock(), mock.Mock()]
    generator = mock.Mock()

    with (
        mock.patch("comdab.main.build_comdab_schema", side_effect=[source, target]) as build_mock,
        mock.patch("comdab.main.compare_comdab_schemas", return_value=reports) as compare_mock,
        mock.patch("comdab.main.generate_migrations_from_reports") as generate_mock,
    ):
        generate_migrations(source_connection, target_connection, generator)
        assert build_mock.call_args_list == [
            mock.call(source_connection, schema="public", allow_unknown_types=False),
            mock.call(target_connection, schema="public", allow_unknown_types=False),
        ]
        assert compare_mock.call_args_list == [mock.call(source, target, rules=None)]
        assert generate_mock.call_args_list == [mock.call(target, reports, generator)]

    with (
        mock.patch("comdab.main.build_comdab_schema", side_effect=[source, target]) as build_mock,
        mock.patch("comdab.main.compare_comdab_schemas", return_value=reports) as compare_mock,
        mock.patch("comdab.main.generate_migrations_from_reports") as generate_mock,
    ):
        generate_migrations(
            source_connection,
            target_connection,
            generator,
            source_schema="foo",
            target_schema="bar",
            rules=rules,
            allow_unknown_types=True,
        )
        assert build_mock.call_args_list == [
            mock.call(source_connection, schema="foo", allow_unknown_types=True),
            mock.call(target_connection, schema="bar", allow_unknown_types=True),
        ]
        assert compare_mock.call_args_list == [mock.call(source, target, rules=rules)]
        assert generate_mock.call_args_list == [mock.call(target, reports, generator)]


def test_compare_databases() -> None:
    left_connection = mock.Mock()
    right_connection = mock.Mock()
    rules = mock.Mock()

    left = mock.Mock()
    right = mock.Mock()

    with (
        mock.patch("comdab.main.build_comdab_schema", side_effect=[left, right]) as build_mock,
        mock.patch("comdab.main.compare_comdab_schemas") as compare_mock,
    ):
        reports = compare_databases(left_connection, right_connection)
        assert build_mock.call_args_list == [
            mock.call(left_connection, schema="public", allow_unknown_types=False),
            mock.call(right_connection, schema="public", allow_unknown_types=False),
        ]
        assert compare_mock.call_args_list == [mock.call(left, right, rules=None)]
        assert reports is compare_mock.return_value

    with (
        mock.patch("comdab.main.build_comdab_schema", side_effect=[left, right]) as build_mock,
        mock.patch("comdab.main.compare_comdab_schemas") as compare_mock,
    ):
        reports = compare_databases(
            left_connection,
            right_connection,
            left_schema="foo",
            right_schema="bar",
            rules=rules,
            allow_unknown_types=True,
        )
        assert build_mock.call_args_list == [
            mock.call(left_connection, schema="foo", allow_unknown_types=True),
            mock.call(right_connection, schema="bar", allow_unknown_types=True),
        ]
        assert compare_mock.call_args_list == [mock.call(left, right, rules=rules)]
        assert reports is compare_mock.return_value


def test_build_comdab_schema() -> None:
    with (
        mock.patch("comdab.main.ComdabBuilder") as generic_builder_mock,
        mock.patch.dict(
            "sys.modules",
            {
                "comdab.specific.postgresql.build": _mock_module,
            },
        ) as sys_modules_mock,
    ):
        psql_builder_mock: mock.Mock = sys_modules_mock["comdab.specific.postgresql.build"].ComdabPostgreSQLBuilder

        connection = mock.Mock(dialect=mysql.dialect())
        result = build_comdab_schema(connection)
        generic_builder_mock.assert_called_once_with(
            ComdabSource(connection=connection, schema_name="public"), allow_unknown_types=False
        )
        generic_builder_mock.return_value.build_schema.assert_called_once_with()
        assert result is generic_builder_mock.return_value.build_schema.return_value

        generic_builder_mock.reset_mock()
        result = build_comdab_schema(connection, schema="other", allow_unknown_types=True)
        generic_builder_mock.assert_called_once_with(
            ComdabSource(connection=connection, schema_name="other"), allow_unknown_types=True
        )
        generic_builder_mock.return_value.build_schema.assert_called_once_with()
        assert result is generic_builder_mock.return_value.build_schema.return_value

        generic_builder_mock.reset_mock()
        psql_builder_mock.assert_not_called()

        connection = mock.Mock(dialect=postgresql.dialect())
        result = build_comdab_schema(connection, schema="other", allow_unknown_types=True)
        generic_builder_mock.assert_not_called()
        psql_builder_mock.assert_called_once_with(
            ComdabSource(connection=connection, schema_name="other"), allow_unknown_types=True
        )
        psql_builder_mock.return_value.build_schema.assert_called_once_with()
        assert result is psql_builder_mock.return_value.build_schema.return_value


def test_compare_comdab_schemas() -> None:
    left = mock.Mock()
    right = mock.Mock()
    rules = mock.Mock()

    with mock.patch("comdab.main.ComdabComparer") as comparer_mock:
        result = compare_comdab_schemas(left, right)
        comparer_mock.assert_called_once_with(rules=None)
        comparer_mock.return_value.compare.assert_called_once_with(left, right)
        assert result is comparer_mock.return_value.compare.return_value

        comparer_mock.reset_mock()

        result = compare_comdab_schemas(left, right, rules=rules)
        comparer_mock.assert_called_once_with(rules=rules)
        comparer_mock.return_value.compare.assert_called_once_with(left, right)
        assert result is comparer_mock.return_value.compare.return_value


def test_generate_migrations_from_reports() -> None:
    target_schema = mock.Mock()
    reports = [mock.Mock(), mock.Mock(), mock.Mock()]
    generator = mock.Mock()

    with mock.patch("comdab.main.generate_migration") as generate_mock:
        generate_migrations_from_reports(target_schema, reports, generator)
        assert generate_mock.call_args_list == [mock.call(target_schema, report, generator) for report in reports]

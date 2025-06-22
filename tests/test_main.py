from unittest import mock

from sqlalchemy.dialects import mysql, postgresql

from comdab.main import build_comdab_schema, compare_comdab_schemas
from comdab.source import ComdabSource
from tests import _mock_module


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

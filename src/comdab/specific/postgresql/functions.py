from typing import NamedTuple

from comdab.models.function import ComdabFunction
from comdab.source import ComdabSource
from comdab.utils import typed_sql


class _FunctionsQuery(NamedTuple):
    proname: str
    functiondef: str


_FUNCTIONS_QUERY = typed_sql[_FunctionsQuery](
    """--sql
    SELECT
        pro.proname,
        pg_get_functiondef(pro.oid) AS functiondef
    FROM pg_catalog.pg_proc pro                                         -- Function
    JOIN pg_catalog.pg_namespace nsp ON nsp.oid = pro.pronamespace      -- Function schema
    JOIN pg_catalog.pg_language lan ON lan.oid = pro.prolang            -- Function implementation language
    WHERE nsp.nspname = :schema_name
    AND pro.prokind = 'f'  -- TODO: handle procedure/aggregate/window functions?
    AND lan.lanname != 'c';
    """,
)


def get_postgresql_functions(source: ComdabSource) -> list[ComdabFunction]:
    result = source.connection.execute(
        _FUNCTIONS_QUERY,
        {"schema_name": source.schema_name},
    )
    return [
        ComdabFunction(
            name=row.proname,
            definition=row.functiondef,
        )
        for row in result.t
    ]

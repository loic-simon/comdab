from typing import NamedTuple

from comdab.models.view import ComdabView
from comdab.source import ComdabSource
from comdab.utils import typed_sql


class _ViewsQuery(NamedTuple):
    relname: str
    relkind: str
    viewdef: str


_VIEWS_QUERY = typed_sql[_ViewsQuery](
    """--sql
    SELECT
        rel.relname,
        rel.relkind,
        pg_get_viewdef(rel.oid) AS viewdef
    FROM pg_catalog.pg_class rel                                        -- View
    JOIN pg_catalog.pg_namespace nsp ON nsp.oid = rel.relnamespace      -- View schema
    WHERE nsp.nspname = :schema_name
    AND rel.relkind IN ('v', 'm');
    """,
)


def get_postgresql_views(source: ComdabSource) -> list[ComdabView]:
    result = source.connection.execute(
        _VIEWS_QUERY,
        {"schema_name": source.schema_name},
    )
    return [
        ComdabView(
            name=row.relname,
            definition=row.viewdef.strip(),
            materialized=row.relkind == "m",
        )
        for row in result.t
    ]

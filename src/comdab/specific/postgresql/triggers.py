from itertools import groupby
from typing import NamedTuple

from comdab.models.trigger import ComdabTrigger
from comdab.source import ComdabSource
from comdab.utils import typed_sql


class _TriggersQuery(NamedTuple):
    relname: str
    tgname: str
    triggerdef: str


_TRIGGERS_QUERY = typed_sql[_TriggersQuery](
    """--sql
    SELECT
        rel.relname,
        tg.tgname,
        pg_get_triggerdef(tg.oid) AS triggerdef
    FROM pg_catalog.pg_trigger tg                                       -- Trigger
    JOIN pg_catalog.pg_class rel ON rel.oid = tg.tgrelid                -- Trigger table
    JOIN pg_catalog.pg_namespace nsp ON nsp.oid = rel.relnamespace      -- Trigger schema
    WHERE nsp.nspname = :schema_name
    AND NOT tg.tgisinternal
    ORDER BY rel.relname;
    """,
)


def get_postgresql_triggers_by_table(source: ComdabSource) -> dict[str, list[ComdabTrigger]]:
    result = source.connection.execute(
        _TRIGGERS_QUERY,
        {"schema_name": source.schema_name},
    )
    return {
        table_name: [
            ComdabTrigger(
                name=row.tgname,
                definition=row.triggerdef,
            )
            for row in rows
        ]
        for table_name, rows in groupby(result.t, lambda row: row.relname)
    }

from typing import NamedTuple

from comdab.models.custom_type import ComdabCustomType
from comdab.source import ComdabSource
from comdab.utils import typed_sql


class _CustomTypesQuery(NamedTuple):
    typname: str
    values: list[str]


_CUSTOM_TYPES_QUERY = typed_sql[_CustomTypesQuery](
    """--sql

    SELECT
        typ.typname,
        ARRAY_AGG(enum.enumlabel ORDER BY enum.enumsortorder) AS values
    FROM pg_catalog.pg_type typ                                             -- Type
    JOIN pg_catalog.pg_namespace nsp ON typ.typnamespace = nsp.oid          -- Type schema
    LEFT OUTER JOIN pg_catalog.pg_enum enum ON enum.enumtypid = typ.oid     -- Enum values
    WHERE nsp.nspname = :schema_name
    AND typ.typtype = 'e'  -- TODO: handle other kind of custom types?
    GROUP BY typ.oid;
    """,
)


def get_postgresql_custom_types(source: ComdabSource) -> list[ComdabCustomType]:
    result = source.connection.execute(
        _CUSTOM_TYPES_QUERY,
        {"schema_name": source.schema_name},
    )
    return [
        ComdabCustomType(
            name=row.typname,
            values=row.values,
        )
        for row in result.t
    ]

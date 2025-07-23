from itertools import groupby
from typing import NamedTuple

from comdab.models.constraint import ComdabExcludeConstraint
from comdab.source import ComdabSource
from comdab.utils import typed_sql


class _ExcludeConstraintsQuery(NamedTuple):
    relname: str
    conname: str
    condeferrable: bool
    condeferred: bool
    ix_typ: str
    attributes: list[str]
    operators: list[str]
    where_expr: str | None


_EXCLUDE_CONSTRAINTS_QUERY = typed_sql[_ExcludeConstraintsQuery](
    """--sql
    SELECT
        rel.relname,
        con.conname,
        con.condeferrable,
        con.condeferred,
        ix_info.ix_typ,
        ix_info.attributes,
        op_info.operators,
        pg_get_expr(ix_info.indpred, rel.oid) AS where_expr
    FROM pg_catalog.pg_constraint con                                   -- Constraint
    JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid              -- Constraint table
    JOIN pg_catalog.pg_namespace nsp ON nsp.oid = con.connamespace      -- Constraint schema
    JOIN (
        SELECT con2.oid, am.amname AS ix_typ, ARRAY_AGG(att.attname ORDER BY att.attnum ASC) AS attributes, ind.indpred
        FROM pg_catalog.pg_constraint con2
        JOIN pg_catalog.pg_class ix ON ix.oid = con2.conindid           -- Index backing the constraint
        JOIN pg_catalog.pg_index ind on ind.indexrelid = ix.oid         -- Same but other view
        JOIN pg_catalog.pg_am am ON am.oid = ix.relam                   -- Index access method (eg. type)
        JOIN pg_catalog.pg_attribute att ON att.attrelid = ix.oid       -- Attribute referenced in the index
        GROUP BY con2.oid, ind.indexrelid, am.oid
    ) ix_info ON ix_info.oid = con.oid
    JOIN (
        SELECT con3.oid, ARRAY_AGG(opr.oprname ORDER BY opnum ASC) AS operators
        FROM pg_catalog.pg_constraint con3
        JOIN unnest(con3.conexclop) WITH ORDINALITY AS t(opid, opnum) ON true  -- Constraint operators for each column
        JOIN pg_operator opr ON opr.oid = opid                          -- Operator info
        GROUP BY con3.oid
    ) op_info ON op_info.oid = con.oid
    WHERE nsp.nspname = :schema_name
    AND con.contype = 'x'
    ORDER BY rel.relname;
    """,
)


def get_postgresql_exclude_constraints_by_table(
    source: ComdabSource,
) -> dict[str, list[ComdabExcludeConstraint]]:
    result = source.connection.execute(
        _EXCLUDE_CONSTRAINTS_QUERY,
        {"schema_name": source.schema_name},
    )
    return {
        table_name: [
            ComdabExcludeConstraint(
                name=row.conname,
                attributes_and_operators=list(zip(row.attributes, row.operators, strict=True)),
                deferrable=row.condeferrable,
                initially="DEFERRED" if row.condeferred else None,
                extra={
                    **({"postgresql_using": row.ix_typ}),
                    **({"postgresql_where": row.where_expr} if row.where_expr else {}),
                },
            )
            for row in rows
        ]
        for table_name, rows in groupby(result.t, lambda row: row.relname)
    }

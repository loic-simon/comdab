from typing import NamedTuple

from comdab.models.sequence import ComdabSequence
from comdab.source import ComdabSource
from comdab.utils import typed_sql


class _SequencesQuery(NamedTuple):
    relname: str
    typname: str
    seqstart: int
    seqincrement: int
    seqmin: int
    seqmax: int
    seqcycle: bool


_SEQUENCES_QUERY = typed_sql[_SequencesQuery](
    """--sql
    SELECT
        rel.relname,
        typ.typname,
        seq.seqstart,
        seq.seqincrement,
        seq.seqmin,
        seq.seqmax,
        seq.seqcycle
    FROM pg_catalog.pg_sequence seq                                     -- Sequence
    JOIN pg_catalog.pg_class rel ON rel.oid = seq.seqrelid              -- Sequence, as a class
    JOIN pg_catalog.pg_namespace nsp ON nsp.oid = rel.relnamespace      -- Sequence schema
    JOIN pg_catalog.pg_type typ ON typ.oid = seq.seqtypid               -- Sequence type
    WHERE nsp.nspname = :schema_name;
    """,
)


def get_postgresql_sequences(source: ComdabSource) -> list[ComdabSequence]:
    result = source.connection.execute(
        _SEQUENCES_QUERY,
        {"schema_name": source.schema_name},
    )
    return [
        ComdabSequence(
            name=row.relname,
            type_name=row.typname,
            start=row.seqstart,
            increment=row.seqincrement,
            min=row.seqmin,
            max=row.seqmax,
            cycle=row.seqcycle,
        )
        for row in result.t
    ]

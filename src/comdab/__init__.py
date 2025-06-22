"""comdab - Compare Database Schemas

Loïc Simon 2025, MIT License
"""

from comdab.main import build_comdab_schema, compare_comdab_schemas, compare_databases
from comdab.models import ROOT

#: The top-level *comdab* path, pointing to a whole :class:`ComdabSchema`.
#:
#: It's attributes are, recursively, the corresponding schema attributes:
#: ``ROOT.tables['foo'].columns`` refer to all columns of the table named ``foo``,
#: eg. the dictionary ``some_schema.tables['foo'].columns``.
#:
#: Dictionary keys can be :mod:`regular expressions <re>` (or ``...``, equivalent to ``'.*'``), so that
#: ``ROOT.tables['_.*'].columns`` refer to all columns of all tables beginning with an underscore.
ROOT = ROOT  # pyright: ignore[reportConstantRedefinition]  # Only here for Sphinx


__all__ = [
    "compare_databases",
    "build_comdab_schema",
    "compare_comdab_schemas",
    "ROOT",
]

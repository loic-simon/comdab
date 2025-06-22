"""Internal helpers used by comdab."""

import textwrap
from collections.abc import Iterable
from typing import LiteralString, NamedTuple, Protocol, cast

from sqlalchemy import text
from sqlalchemy.sql.selectable import TypedReturnsRows

from comdab.exceptions import ComdabInternalError


class _HasName(Protocol):
    @property
    def name(self) -> str: ...


def dict_by_name[T: _HasName](iterable: Iterable[T]) -> dict[str, T]:
    """Transform an iterable into a mapping of items by their "name" property.

    * Order items by name alphabetically
    * Ensure names are unique
    """
    items = sorted(((item.name, item) for item in iterable), key=lambda it: it[0])
    dic = dict(items)
    if len(dic) < len(items):
        _seen = set[str]()
        _duplicate_keys = {x for x, _ in items if x in _seen or _seen.add(x)}
        raise ComdabInternalError(f"dict_by_name: duplicate keys: {_duplicate_keys}")
    return dic


class typed_sql[T: NamedTuple]:  # Use a class rather than a function to allow subscription, waiting for PEP 718
    """Clean & type a SQL textual query multiline string.

    * Make the string an executable :cls:`sqlalchemy.TextClause`
    * Remove "--sql" comment needed by https://marketplace.visualstudio.com/items?itemName=ptweir.python-string-sql
    * Remove indentation-caused leading whitespace
    * Type is as a SQLAlchemy selectable producing rows typed as the NamedTuple passed as generic argument
    """

    def __new__(cls, sql: LiteralString) -> TypedReturnsRows[T]:
        return cast(TypedReturnsRows[T], text(textwrap.dedent(sql.removeprefix("--sql\n"))))

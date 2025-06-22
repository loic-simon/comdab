from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class ComdabIndex(ComdabModel, frozen=True):
    """A database index.

    Equivalent to a :class:`sqlalchemy.Index` object.
    """

    name: str
    expressions: list[str]
    unique: bool
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        name = terminal_path()
        expressions = terminal_path()
        unique = terminal_path()
        extra = dict_of_paths(ComdabPath)

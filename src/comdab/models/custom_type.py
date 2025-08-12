from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class ComdabCustomType(ComdabModel, frozen=True):
    """A database custom type (only Enums supported).

    Even types not used in any column are listed here.
    """

    name: str
    values: list[str]
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        name = terminal_path()
        values = terminal_path()
        extra = dict_of_paths(ComdabPath)

from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class ComdabView(ComdabModel, frozen=True):
    """A database view.

    Equivalent to a :class:`sqlalchemy.Table` object.
    """

    name: str
    definition: str
    materialized: bool
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        name = terminal_path()
        definition = terminal_path()
        materialized = terminal_path()
        extra = dict_of_paths(ComdabPath)

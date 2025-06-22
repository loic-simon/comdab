from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class ComdabSequence(ComdabModel, frozen=True):
    """A database sequence.

    Not natively handled by SQLAlchemy.
    """

    name: str
    type_name: str
    start: int
    increment: int
    min: int
    max: int
    cycle: bool
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        name = terminal_path()
        type_name = terminal_path()
        start = terminal_path()
        increment = terminal_path()
        min = terminal_path()
        max = terminal_path()
        cycle = terminal_path()
        extra = dict_of_paths(ComdabPath)

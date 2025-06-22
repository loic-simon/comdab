from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class ComdabTrigger(ComdabModel, frozen=True):
    """A database trigger.

    Not natively handled by SQLAlchemy.
    """

    name: str
    definition: str
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        name = terminal_path()
        definition = terminal_path()
        extra = dict_of_paths(ComdabPath)

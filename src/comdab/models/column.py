from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.models.type import ComdabType, ComdabType_Path
from comdab.path import ComdabPath, dict_of_paths, sub_path, terminal_path


class ComdabColumn(ComdabModel, frozen=True):
    """A database column.

    Equivalent to a :class:`sqlalchemy.Column` object.
    """

    name: str
    type: ComdabType
    nullable: bool
    default: str | None
    generation_expression: str | None
    extra: dict[str, Any] = Field(default_factory=dict)

    # PostgreSQL parameters not reflected here: storage, compression, collation, comments

    class Path(ComdabPath):
        name = terminal_path()
        type = sub_path(ComdabType_Path)
        nullable = terminal_path()
        default = terminal_path()
        generation_expression = terminal_path()
        extra = dict_of_paths(ComdabPath)

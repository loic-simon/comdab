from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.models.column import ComdabColumn
from comdab.models.constraint import ComdabConstraint, ComdabConstraint_Path
from comdab.models.index import ComdabIndex
from comdab.models.trigger import ComdabTrigger
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class ComdabTable(ComdabModel, frozen=True):
    """A database table.

    Equivalent to a :class:`sqlalchemy.Table` object.
    """

    name: str
    columns: dict[str, ComdabColumn]
    constraints: dict[str, ComdabConstraint]
    indexes: dict[str, ComdabIndex]
    triggers: dict[str, ComdabTrigger]
    # TODO: custom types?
    extra: dict[str, Any] = Field(default_factory=dict)

    # PostgreSQL parameters not reflected here: global/local, logged/unlogged, inheritance, partitioning,
    # storage parameters (fillfactor, vacuum options...), on-commit behavior, tablespace, rules,
    # row-level security, access method, replica identity, owner, comments

    class Path(ComdabPath):
        name = terminal_path()
        columns = dict_of_paths(ComdabColumn.Path)
        constraints = dict_of_paths(ComdabConstraint_Path)
        indexes = dict_of_paths(ComdabIndex.Path)
        triggers = dict_of_paths(ComdabTrigger.Path)
        extra = dict_of_paths(ComdabPath)

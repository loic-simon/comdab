from typing import Any

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.models.function import ComdabFunction
from comdab.models.sequence import ComdabSequence
from comdab.models.table import ComdabTable
from comdab.models.view import ComdabView
from comdab.path import ComdabPath, dict_of_paths


class ComdabSchema(ComdabModel, frozen=True):
    """A database schema, the top-level comdab model.

    Equivalent to a :class:`sqlalchemy.Metadata` object.
    """

    tables: dict[str, ComdabTable]
    views: dict[str, ComdabView]
    sequences: dict[str, ComdabSequence]
    functions: dict[str, ComdabFunction]
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        tables = dict_of_paths(ComdabTable.Path)
        views = dict_of_paths(ComdabView.Path)
        sequences = dict_of_paths(ComdabSequence.Path)
        functions = dict_of_paths(ComdabFunction.Path)
        extra = dict_of_paths(ComdabPath)


ROOT = ComdabSchema.Path([], _ok=True)

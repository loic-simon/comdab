from typing import Any, get_args

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path


class _BaseComdabConstraint(ComdabModel, frozen=True):
    """Root class representing a database constraint.

    Equivalent to a :class:`sqlalchemy.Constraint` object.
    """

    type: str
    name: str
    deferrable: bool | None
    initially: str | None
    extra: dict[str, Any] = Field(default_factory=dict)

    class Path(ComdabPath):
        type = terminal_path()
        name = terminal_path()
        deferrable = terminal_path()
        initially = terminal_path()
        extra = dict_of_paths(ComdabPath)

        # Union of fields of all constraint types
        columns = terminal_path()
        columns_mapping = dict_of_paths(ComdabPath)
        on_update = terminal_path()
        on_delete = terminal_path()
        sql_text = terminal_path()
        attributes_and_operators = terminal_path()


class ComdabUniqueConstraint(_BaseComdabConstraint, frozen=True):
    """A database unique constraint.

    Equivalent to a :class:`sqlalchemy.UniqueConstraint` object.
    """

    type: str = "unique"
    columns: set[str]


class ComdabPrimaryKeyConstraint(_BaseComdabConstraint, frozen=True):
    """A database primary key constraint.

    Equivalent to a :class:`sqlalchemy.PrimaryKeyConstraint` object.
    """

    type: str = "primary_key"
    columns: set[str]


class ComdabForeignKeyConstraint(_BaseComdabConstraint, frozen=True):
    """A database foreign key constraint.

    Equivalent to a :class:`sqlalchemy.ForeignKeyConstraint` object.
    """

    type: str = "foreign_key"
    columns_mapping: dict[str, str]
    on_update: str | None
    on_delete: str | None


class ComdabCheckConstraint(_BaseComdabConstraint, frozen=True):
    """A database check constraint.

    Equivalent to a :class:`sqlalchemy.CheckConstraint` object.
    """

    type: str = "check"
    sql_text: str


class ComdabExcludeConstraint(_BaseComdabConstraint, frozen=True):
    """A database constraint.

    Not natively handled by SQLAlchemy.
    """

    type: str = "exclude"
    attributes_and_operators: list[tuple[str, str]]


type ComdabConstraint = (
    ComdabUniqueConstraint
    | ComdabPrimaryKeyConstraint
    | ComdabForeignKeyConstraint
    | ComdabCheckConstraint
    | ComdabExcludeConstraint
)
ComdabConstraint_Path = _BaseComdabConstraint.Path


assert set(get_args(ComdabConstraint.__value__)) == set(_BaseComdabConstraint.__subclasses__()), (
    "Mismatch between ComdabConstraint members and _BaseComdabConstraint subclasses!"
)

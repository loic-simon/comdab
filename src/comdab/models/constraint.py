from typing import Any, Literal, get_args

from pydantic import Field

from comdab.models.base import ComdabModel
from comdab.path import ComdabPath, dict_of_paths, terminal_path

type ComdabConstraintType = Literal[
    "unique",
    "primary_key",
    "foreign_key",
    "check",
    "exclude",
]


class _BaseComdabConstraint(ComdabModel, frozen=True):
    """Root class representing a database constraint.

    Equivalent to a :class:`sqlalchemy.sql.schema.Constraint` object.
    """

    type: ComdabConstraintType
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

    Equivalent to a :class:`sqlalchemy.sql.schema.UniqueConstraint` object.
    """

    type: Literal["unique"] = "unique"
    columns: set[str]


class ComdabPrimaryKeyConstraint(_BaseComdabConstraint, frozen=True):
    """A database primary key constraint.

    Equivalent to a :class:`sqlalchemy.sql.schema.PrimaryKeyConstraint` object.
    """

    type: Literal["primary_key"] = "primary_key"
    columns: set[str]


class ComdabForeignKeyConstraint(_BaseComdabConstraint, frozen=True):
    """A database foreign key constraint.

    Equivalent to a :class:`sqlalchemy.sql.schema.ForeignKeyConstraint` object.
    """

    type: Literal["foreign_key"] = "foreign_key"
    columns_mapping: dict[str, str]
    on_update: str | None
    on_delete: str | None


class ComdabCheckConstraint(_BaseComdabConstraint, frozen=True):
    """A database check constraint.

    Equivalent to a :class:`sqlalchemy.sql.schema.CheckConstraint` object.
    """

    type: Literal["check"] = "check"
    sql_text: str


class ComdabExcludeConstraint(_BaseComdabConstraint, frozen=True):
    """A database constraint.

    Not natively handled by SQLAlchemy.
    """

    type: Literal["exclude"] = "exclude"
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

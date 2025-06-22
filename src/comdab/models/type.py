from typing import Any, get_args

from pydantic import ConfigDict, Field
from typing_extensions import Unpack

from comdab.models.base import ComdabModel
from comdab.path import (
    ComdabPath,
    _PathDescriptor,  # pyright: ignore[reportPrivateUsage]  # typing usage only
    dict_of_paths,
    sub_path,
    terminal_path,
)


class _BaseComdabType(ComdabModel, frozen=True):
    """Root class representing a database type.

    Equivalent to a :class:`sqlalchemy.types.TypeEngine` object.
    """

    type: str = ""  # Model field, but defined in __init_subclass__
    implem_name: str
    extra: dict[str, Any] = Field(default_factory=dict)

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        super().__init_subclass__(**kwargs)
        cls.type = cls.__name__

    class Path(ComdabPath):
        type = terminal_path()
        implem_name = terminal_path()
        extra = dict_of_paths(ComdabPath)

        # Union of fields of all types
        length = terminal_path()
        collation = terminal_path()
        precision = terminal_path()
        scale = terminal_path()
        with_timezone = terminal_path()
        second_precision = terminal_path()
        day_precision = terminal_path()
        length = terminal_path()
        item_type: _PathDescriptor["_BaseComdabType.Path"]  # Defined below (references itself)
        dimensions = terminal_path()
        values = terminal_path()
        type_name = terminal_path()


_item_type_descr = sub_path(_BaseComdabType.Path)
_item_type_descr.__set_name__(_BaseComdabType.Path, "item_type")
_BaseComdabType.Path.item_type = _item_type_descr


class ComdabTypes:
    """Registry of all data types handled by comdab.

    Each class member represent a database type, equivalent to a :class:`sqlalchemy.types.TypeEngine` class.
    """

    class String(_BaseComdabType, frozen=True):
        length: int | None
        collation: str | None

    class Integer(_BaseComdabType, frozen=True):
        pass

    class Float(_BaseComdabType, frozen=True):
        pass

    class Numeric(_BaseComdabType, frozen=True):
        precision: int | None
        scale: int | None

    class Boolean(_BaseComdabType, frozen=True):
        pass

    class DateTime(_BaseComdabType, frozen=True):
        with_timezone: bool

    class Date(_BaseComdabType, frozen=True):
        pass

    class Time(_BaseComdabType, frozen=True):
        pass

    class Interval(_BaseComdabType, frozen=True):
        second_precision: int | None
        day_precision: int | None

    class JSON(_BaseComdabType, frozen=True):
        pass

    class Binary(_BaseComdabType, frozen=True):
        length: int | None

    class UUID(_BaseComdabType, frozen=True):
        pass

    class Array(_BaseComdabType, frozen=True):
        item_type: "ComdabType"
        dimensions: int

    class Enum(_BaseComdabType, frozen=True):
        values: set[str]
        type_name: str | None
        collation: str | None

    # === PostgreSQL-specific types ===

    class HSTORE(_BaseComdabType, frozen=True):
        pass

    class Range(_BaseComdabType, frozen=True):
        item_type: "ComdabType"

    class MultiRange(_BaseComdabType, frozen=True):
        item_type: "ComdabType"

    # === Unknown type ===

    class Unknown(_BaseComdabType, frozen=True):
        """A type not handled (yet) by comdab, when run with ``allow_unknown_types=True``."""


type ComdabType = (  # Union of all TYPES members
    ComdabTypes.String
    | ComdabTypes.Integer
    | ComdabTypes.Float
    | ComdabTypes.Numeric
    | ComdabTypes.Boolean
    | ComdabTypes.DateTime
    | ComdabTypes.Date
    | ComdabTypes.Time
    | ComdabTypes.Interval
    | ComdabTypes.JSON
    | ComdabTypes.Binary
    | ComdabTypes.UUID
    | ComdabTypes.Array
    | ComdabTypes.Enum
    | ComdabTypes.HSTORE
    | ComdabTypes.Range
    | ComdabTypes.MultiRange
    | ComdabTypes.Unknown
)
ComdabType_Path = _BaseComdabType.Path

assert set(get_args(ComdabType.__value__)) == {
    t for t in ComdabTypes.__dict__.values() if isinstance(t, type) and issubclass(t, _BaseComdabType)
}, "Mismatch between ComdabType and ComdabTypes members!"

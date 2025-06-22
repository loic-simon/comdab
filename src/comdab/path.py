from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import EllipsisType, GenericAlias
from typing import Any, Self, get_args

from comdab.exceptions import ComdabInternalError


@dataclass(frozen=True, slots=True)
class PathAttr:
    """An attribute component of a :class:`ComdabPath`, ie. to access a field of a model."""

    attr: str

    def __repr__(self) -> str:
        return f".{self.attr}"


@dataclass(frozen=True, slots=True)
class PathItem:
    """An item component of a :class:`ComdabPath`, ie. to access a key of a model dictionary field."""

    key: str

    def __repr__(self) -> str:
        return f"[{self.key!r}]"


class ComdabPath[GenericType: Any = Any]:
    """Represent the path of a data in a ComdabModel.

    Should never in instantiated manually, but build from :attr:`~comdab.path.ROOT` attributes
    (eg. ``ROOT.tables['foo'].columns``).
    """

    __slots__ = ("_components", "_generic_type")

    _components: list[PathAttr | PathItem]
    _generic_type: type[GenericType] | None

    def __new__(
        cls, _components: list[PathAttr | PathItem], *, generic_type: type[GenericType] | None = None, _ok: bool = False
    ) -> Self:
        if not _ok:
            raise TypeError(
                f"{cls.__qualname__} should not be instantiated!\n\n"
                "To build a path, start from `comdab.ROOT`, eg. ``ROOT.tables['foo'].columns``."
            )
        inst = super().__new__(cls)
        inst._components = _components
        inst._generic_type = generic_type
        return inst

    def __repr__(self) -> str:
        return f"ROOT{''.join(repr(comp) for comp in self._components)}"

    def __hash__(self) -> int:
        return hash(tuple(self._components))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._components == other._components


def get_path_component(path: ComdabPath, index: int) -> PathAttr | PathItem | None:
    try:
        return path._components[index]  # pyright: ignore[reportPrivateUsage]
    except IndexError:
        return None


def get_path_depth(path: ComdabPath) -> int:
    return len(path._components)  # pyright: ignore[reportPrivateUsage]


class _PathDescriptor[PathType: ComdabPath]:
    def __init__(self, path_type: type[PathType] = ComdabPath) -> None:
        self._path_type = path_type
        self._name: str | None = None
        self._cache: dict[ComdabPath, PathType] = {}

    def __get__(self, obj: ComdabPath, objtype: type[Any] | None = None) -> PathType:
        if not self._name:
            raise ComdabInternalError(f"{type(self).__name__}.__set_name__ was not called!")
        try:
            return self._cache[obj]
        except KeyError:
            res = self._cache[obj] = self._path_type(
                [*obj._components, PathAttr(self._name)],  # pyright: ignore[reportPrivateUsage]
                generic_type=self._path_type,
                _ok=True,
            )
            return res

    def __set_name__(self, owner: type[Any], name: str) -> None:
        if self._name:
            raise ComdabInternalError(f"A same {type(self).__name__} cannot be re-used!")
        if not issubclass(owner, ComdabPath):
            raise ComdabInternalError(
                f"{type(self).__name__} must only be used on {ComdabPath.__name__} instances, got {owner}!"
            )
        self._name = name


def terminal_path() -> _PathDescriptor[ComdabPath]:
    """Use in the class body of a :class:`ComdabPath` subclass to build a path leaf, without children."""
    return _PathDescriptor()


def sub_path[PathType: ComdabPath](path_type: type[PathType]) -> _PathDescriptor[PathType]:
    """Use in the class body of a :class:`ComdabPath` subclass to build a path branch of the given path type."""
    return _PathDescriptor(path_type)


class ComdabPathDict[PathType: ComdabPath](ComdabPath[PathType], Mapping[str | EllipsisType, PathType]):
    """Represent a ComdabPath referring to a dict[str, <some ComdabModel>] attribute.

    Holds paths as items, and special ``.left_only`` / ``.right_only`` path attributes.

    Should never in instantiated manually, but build from :attr:`~comdab.path.ROOT` attributes
    (eg. ``ROOT.tables['foo']``).
    """

    __slots__ = ("_dict",)

    _dict: dict[str | EllipsisType, PathType]
    right_only = terminal_path()
    left_only = terminal_path()

    def __class_getitem__(cls, item: Any) -> GenericAlias:  # TODO[PEP 747]: type item as TypeForm?
        return GenericAlias(cls, item)

    def __new__(
        cls, _components: list[PathAttr | PathItem], *, generic_type: type["ComdabPath"], _ok: bool = False
    ) -> Self:
        inst = super().__new__(cls, _components, generic_type=get_args(generic_type)[0], _ok=_ok)
        inst._dict = {}
        return inst

    def __getitem__(self, key: str | EllipsisType) -> PathType:
        if self._generic_type is None:
            raise ComdabInternalError(f"Non-generic {type(self).__name__} cannot be subscripted!")

        key = ".*" if key is ... else key
        try:
            return self._dict[key]
        except KeyError:
            res = self._dict[key] = self._generic_type([*self._components, PathItem(key)], _ok=True)
            return res

    def __iter__(self) -> Iterator[str | EllipsisType]:
        yield from self._dict

    def __len__(self) -> int:
        return len(self._dict)


def dict_of_paths[PathType: ComdabPath](values_type: type[PathType]) -> _PathDescriptor[ComdabPathDict[PathType]]:
    """Use in the class body of a :class:`ComdabPath` subclass to build a path branch of a dictionary of paths."""
    return _PathDescriptor(ComdabPathDict[values_type])

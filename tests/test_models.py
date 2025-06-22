from inspect import getmembers
from types import GenericAlias, UnionType
from typing import Any, TypeAliasType, TypeIs, cast, get_args, get_origin, get_type_hints

from comdab.models.base import ComdabModel
from comdab.models.schema import ComdabSchema
from comdab.path import ComdabPath, ComdabPathDict, _PathDescriptor  # pyright: ignore[reportPrivateUsage]  # test file


class TestPathsConsistency:
    """Ensure path attributes are in sync with the paren model."""

    def _get_base_schema(self, model: Any) -> tuple[Any, Any]:
        if isinstance(model, TypeAliasType):
            model = model.__value__
        if isinstance(model, UnionType) and any(
            isinstance(x, type) and issubclass(x, ComdabModel) for x in model.__args__
        ):
            assert all(isinstance(x, type) and issubclass(x, ComdabModel) for x in model.__args__), (
                "Union of schema with non-schema not supported! Update test machinery if needed."
            )
            return model, next(x for x in model.__args__[0].mro() if all(x in y.mro() for y in model.__args__))
        return model, model

    def _validate_path_class(self, path_class: Any) -> TypeIs[type[ComdabPath]]:
        return isinstance(path_class, type) and issubclass(path_class, ComdabPath)

    def _validate_schema(
        self, model: type[ComdabModel] | UnionType, _validated_schemas: set[type[ComdabModel] | UnionType]
    ) -> None:
        if model in _validated_schemas:
            return
        _validated_schemas.add(model)

        # If the schema is an union (ComdabType, ComdabConstraint), extract the base schema (where Path is defined)
        model, base_model = self._get_base_schema(model)

        # Check that the schema has a valid Path attribute
        path_class = getattr(base_model, "Path", "<nothing>")
        assert self._validate_path_class(path_class), (
            f"{base_model.__name__}.Path must be a subclass of ComdabPath[{base_model.__qualname__}], got {path_class}!"
        )

        # Extract schema fields and
        if isinstance(model, UnionType):
            union_models: tuple[type[ComdabModel], ...] = get_args(model)
            hints = {typ: get_type_hints(typ) for typ in union_models}
            schema_fields = {name: hints[typ][name] for typ in union_models for name in typ.model_fields}
        else:
            hints = get_type_hints(model)
            schema_fields = {name: hints[name] for name in model.model_fields}

        # Extract path fields
        path_fields = {
            name: member for name, member in getmembers(path_class) if not name.startswith("_") and name != "path"
        }

        # Check schema and path fields match
        if missing_fields := (schema_fields.keys() - path_fields.keys()):
            raise AssertionError(
                f"Fields in {base_model.__name__} missing in {base_model.__name__}.Path: {missing_fields}"
            )
        if unexpected_fields := (path_fields.keys() - schema_fields.keys()):
            raise AssertionError(
                f"Fields not in {base_model.__name__} but declared in {base_model.__name__}.Path: {unexpected_fields}"
            )

        for name, schema_field in schema_fields.items():
            # Check each Path field in detail
            path_field = path_fields[name]
            assert isinstance(path_field, _PathDescriptor), (
                f"{base_model.__name__}.Path.{name} is not a Path descriptor!"
            )
            path_field = cast(_PathDescriptor[Any], path_field)

            schema_field, base_schema_field = self._get_base_schema(schema_field)
            path_type = path_field._path_type  # pyright: ignore[reportPrivateUsage]

            match base_schema_field:
                case type() if issubclass(base_schema_field, ComdabModel):
                    # Schema field is another schema: check the path field is <schema>.Path
                    try:
                        Path = cast(type[ComdabPath], base_schema_field.Path)  # pyright: ignore
                    except AttributeError:
                        raise AssertionError(f"Missing Path attribute for ComdabModel: {base_schema_field}")
                    assert path_type is Path, (
                        f"{base_model.__name__}.Path.{name} describes a {path_type}, expected {base_schema_field}.Path!"
                    )

                    # Then validate child schema
                    print(f"VALIDATE {base_model.__name__}.{name}", schema_field)
                    self._validate_schema(schema_field, _validated_schemas)

                case GenericAlias() if get_origin(base_schema_field) is dict:
                    # Schema field is a dict: extract dict arguments
                    key_ann, value_ann = get_args(base_schema_field)
                    assert key_ann is str
                    value_ann, base_value_ann = self._get_base_schema(value_ann)

                    if isinstance(base_value_ann, type) and issubclass(base_value_ann, ComdabModel):
                        # Schema field is a dict of other schemas: check the path field is a dict of <schema>.Path
                        try:
                            Path = cast(type[ComdabPath], base_value_ann.Path)  # pyright: ignore
                        except AttributeError:
                            raise AssertionError(f"Missing Path attribute for ComdabModel: {base_value_ann}")
                        assert get_origin(path_type) is ComdabPathDict, (
                            f"{base_model.__name__}.Path.{name} describes a {path_type}, expected a dictionary of {base_schema_field}.Path!"
                        )
                        assert get_args(path_type)[0] is Path, (
                            f"{base_model.__name__}.Path.{name} describes a {path_type}, expected a dictionary of {base_schema_field}.Path!"
                        )

                        # Then validate child schema
                        print(f"VALIDATE {base_model.__name__}.{name}[...]", base_value_ann)
                        self._validate_schema(value_ann, _validated_schemas)

                    else:
                        # Schema field is a dict of non-schemas: check the path field is a dict of terminal ComdabPaths
                        assert get_origin(path_type) is ComdabPathDict, (
                            f"{base_model.__name__}.Path.{name} describes a {path_type}, expected a dictionary of ComdabPath!"
                        )
                        assert get_args(path_type)[0] is ComdabPath, (
                            f"{base_model.__name__}.Path.{name} describes a {path_type}, expected a dictionary of ComdabPath!"
                        )

                case _:
                    # Schema field is any other value: check the path field is a terminal ComdabPath
                    assert path_type is ComdabPath, (
                        f"{base_model.__name__}.Path.{name} describes a {path_type}, expected ComdabPath!"
                    )

    def test_all_models(self) -> None:
        """Tests all models recursively, starting from the root schema."""
        self._validate_schema(ComdabSchema, set())

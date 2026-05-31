import inspect
from collections.abc import Iterator
from functools import partial
from types import FunctionType
from typing import TYPE_CHECKING, Any, TypeAliasType, TypeGuard, cast, get_args, get_origin
from unittest import mock

import pytest

from comdab.migrate import (
    MigrationGeneratorPort,
    PartialMigrationGeneratorPort,
    _path_dict_to_migration_function_kwarg,  # pyright: ignore[reportPrivateUsage]
    generate_migration,
)
from comdab.models.base import ComdabModel
from comdab.models.column import ComdabColumn
from comdab.models.constraint import ComdabPrimaryKeyConstraint
from comdab.models.custom_type import ComdabCustomType
from comdab.models.function import ComdabFunction
from comdab.models.index import ComdabIndex
from comdab.models.schema import ROOT, ComdabSchema
from comdab.models.sequence import ComdabSequence
from comdab.models.table import ComdabTable
from comdab.models.trigger import ComdabTrigger
from comdab.models.type import ComdabTypes
from comdab.models.view import ComdabView
from comdab.path import ComdabPath, ComdabPathDict, PathItem
from comdab.report import ComdabReport

if TYPE_CHECKING:

    class _RegisteredMethod(FunctionType):  # pyright: ignore[reportGeneralTypeIssues]
        _registered_path: ComdabPath
        _registered_kwargs: dict[str, Any]


def _is_registered_method(obj: object) -> TypeGuard["_RegisteredMethod"]:
    return inspect.isfunction(obj) and hasattr(obj, "_registered_path")


@pytest.mark.parametrize(["name", "method"], inspect.getmembers(MigrationGeneratorPort, _is_registered_method))
def test_register_signature_consistency(name: str, method: "_RegisteredMethod") -> None:
    self, *func_parameters = list(inspect.signature(method).parameters.values())
    assert self.name == "self"
    assert all(param.kind.name == "KEYWORD_ONLY" for param in func_parameters)
    declared_kwargs = {param.name: param.annotation for param in func_parameters}

    template, keys = method._registered_path.to_template()  # pyright: ignore[reportPrivateUsage]
    registered_kwargs_path = {_path_dict_to_migration_function_kwarg[key] for key in keys}
    registered_kwargs_report = method._registered_kwargs.keys()  # pyright: ignore[reportPrivateUsage]

    assert not registered_kwargs_path & registered_kwargs_report
    assert declared_kwargs.keys() == registered_kwargs_path | registered_kwargs_report

    # Find type of the value corresponding to the registered path
    ann = ComdabSchema
    for comp in template._components:  # pyright: ignore[reportPrivateUsage]
        if isinstance(comp, PathItem):
            assert comp.key == ".*"
            assert get_origin(ann) is dict, ann
            ann = get_args(ann)[1]
        elif comp.attr in ("right_only", "left_only"):
            assert get_origin(ann) is dict, ann
            ann = get_args(ann)[1]
        else:
            if isinstance(ann, type) and issubclass(ann, ComdabModel):
                ann = ann.model_fields[comp.attr].annotation
            elif isinstance(ann, TypeAliasType):
                union_models: tuple[type[ComdabModel], ...] = get_args(ann.__value__)
                # Union: check if the field is defined on a base class
                common_elt: type[ComdabModel] = union_models[0].mro()[1]
                if comp.attr in common_elt.model_fields:
                    ann = common_elt.model_fields[comp.attr].annotation
                else:
                    # Else, look for the first model that defines this field
                    ann = next(
                        cls.model_fields[comp.attr].annotation for cls in union_models if comp.attr in cls.model_fields
                    )
            else:
                raise AssertionError(ann)

    # Ensure it's the same type as the function kwarg annotation
    for kwarg in registered_kwargs_report:
        assert declared_kwargs[kwarg] == ann


sch = ComdabSchema(
    tables={
        "foo": ComdabTable(
            name="foo",
            columns={
                "bar": ComdabColumn(
                    name="bar",
                    type=ComdabTypes.Integer(implem_name="Integer"),
                    nullable=False,
                    default=None,
                    generation_expression=None,
                ),
            },
            constraints={
                "con": ComdabPrimaryKeyConstraint(name="con", deferrable=None, initially=None, columns={"id"})
            },
            indexes={"ix": ComdabIndex(name="ix", expressions=["bar"], unique=False)},
            triggers={"tri": ComdabTrigger(name="tri", definition="...")},
        )
    },
    views={"vue": ComdabView(name="vue", definition="...", materialized=False)},
    sequences={"sek": ComdabSequence(name="sek", type_name="INT", start=0, increment=1, min=0, max=2, cycle=True)},
    functions={"fn": ComdabFunction(name="fn", definition="...")},
    custom_types={"mt": ComdabCustomType(name="ft", values=["a", "b"])},
)

report = partial(ComdabReport, level="error")
generator = cast(MigrationGeneratorPort, mock.call)


@pytest.mark.parametrize(
    ["report", "expected_calls"],
    [
        (
            report(path=ROOT.tables.right_only, left=None, right={"foo": sch.tables["foo"]}),
            [generator.create_table(table=sch.tables["foo"])],
        ),
        (
            report(path=ROOT.tables.left_only, left={"foo": sch.tables["foo"]}, right=None),
            [generator.drop_table(table=sch.tables["foo"])],
        ),
        (
            report(path=ROOT.views.right_only, left=None, right={"vue": sch.views["vue"]}),
            [generator.create_view(view=sch.views["vue"])],
        ),
        (
            report(path=ROOT.views.left_only, left={"vue": sch.views["vue"]}, right=None),
            [generator.drop_view(view=sch.views["vue"])],
        ),
        (
            report(path=ROOT.sequences.right_only, left=None, right={"sek": sch.sequences["sek"]}),
            [generator.create_sequence(sequence=sch.sequences["sek"])],
        ),
        (
            report(path=ROOT.sequences.left_only, left={"sek": sch.sequences["sek"]}, right=None),
            [generator.drop_sequence(sequence=sch.sequences["sek"])],
        ),
        (
            report(path=ROOT.functions.right_only, left=None, right={"fn": sch.functions["fn"]}),
            [generator.create_function(function=sch.functions["fn"])],
        ),
        (
            report(path=ROOT.functions.left_only, left={"fn": sch.functions["fn"]}, right=None),
            [generator.drop_function(function=sch.functions["fn"])],
        ),
        (
            ComdabReport(
                level="error", path=ROOT.custom_types.right_only, left=None, right={"mt": sch.custom_types["mt"]}
            ),
            [generator.create_custom_type(custom_type=sch.custom_types["mt"])],
        ),
        (
            ComdabReport(
                level="error", path=ROOT.custom_types.left_only, left={"mt": sch.custom_types["mt"]}, right=None
            ),
            [generator.drop_custom_type(custom_type=sch.custom_types["mt"])],
        ),
        (
            report(path=ROOT.extra, left={"goo": "goo"}, right={"ga": "gack"}),
            [generator.alter_schema_extra(old_extra={"goo": "goo"}, new_extra={"ga": "gack"})],
        ),
        # Level 2
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].columns.right_only,
                left=None,
                right={"xx": sch.tables["foo"].columns["bar"]},
            ),
            [generator.create_column(table=sch.tables["foo"], column=sch.tables["foo"].columns["bar"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].columns.left_only,
                left={"xx": sch.tables["foo"].columns["bar"]},
                right=None,
            ),
            [generator.drop_column(table=sch.tables["foo"], column=sch.tables["foo"].columns["bar"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].constraints.right_only,
                left=None,
                right={"xx": sch.tables["foo"].constraints["con"]},
            ),
            [generator.create_constraint(table=sch.tables["foo"], constraint=sch.tables["foo"].constraints["con"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].constraints.left_only,
                left={"xx": sch.tables["foo"].constraints["con"]},
                right=None,
            ),
            [generator.drop_constraint(table=sch.tables["foo"], constraint=sch.tables["foo"].constraints["con"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].indexes.right_only,
                left=None,
                right={"xx": sch.tables["foo"].indexes["ix"]},
            ),
            [generator.create_index(table=sch.tables["foo"], index=sch.tables["foo"].indexes["ix"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].indexes.left_only,
                left={"xx": sch.tables["foo"].indexes["ix"]},
                right=None,
            ),
            [generator.drop_index(table=sch.tables["foo"], index=sch.tables["foo"].indexes["ix"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].triggers.right_only,
                left=None,
                right={"xx": sch.tables["foo"].triggers["tri"]},
            ),
            [generator.create_trigger(table=sch.tables["foo"], trigger=sch.tables["foo"].triggers["tri"])],
        ),
        (
            ComdabReport(
                level="error",
                path=ROOT.tables["foo"].triggers.left_only,
                left={"xx": sch.tables["foo"].triggers["tri"]},
                right=None,
            ),
            [generator.drop_trigger(table=sch.tables["foo"], trigger=sch.tables["foo"].triggers["tri"])],
        ),
        (
            report(path=ROOT.tables["foo"].extra, left={"a": 2}, right={"a": 3}),
            [generator.alter_table_extra(table=sch.tables["foo"], old_extra={"a": 2}, new_extra={"a": 3})],
        ),
        (
            report(path=ROOT.views["vue"].definition, left="left", right="right"),
            [generator.alter_view_definition(view=sch.views["vue"], old_definition="left", new_definition="right")],
        ),
        (
            report(path=ROOT.views["vue"].materialized, left=False, right=True),
            [generator.alter_view_materialized(view=sch.views["vue"], old_materialized=False, new_materialized=True)],
        ),
        (
            report(path=ROOT.views["vue"].extra, left={"?": "left"}, right={"?": "right"}),
            [generator.alter_view_extra(view=sch.views["vue"], old_extra={"?": "left"}, new_extra={"?": "right"})],
        ),
        (
            report(path=ROOT.sequences["sek"].type_name, left="left", right="right"),
            [
                generator.alter_sequence_type_name(
                    sequence=sch.sequences["sek"], old_type_name="left", new_type_name="right"
                )
            ],
        ),
        (
            report(path=ROOT.sequences["sek"].start, left=False, right=True),
            [generator.alter_sequence_start(sequence=sch.sequences["sek"], old_start=False, new_start=True)],
        ),
        (
            report(path=ROOT.sequences["sek"].increment, left=2, right=3),
            [generator.alter_sequence_increment(sequence=sch.sequences["sek"], old_increment=2, new_increment=3)],
        ),
        (
            report(path=ROOT.sequences["sek"].min, left=0, right=1),
            [generator.alter_sequence_min(sequence=sch.sequences["sek"], old_min=0, new_min=1)],
        ),
        (
            report(path=ROOT.sequences["sek"].max, left=12345, right=2**16),
            [generator.alter_sequence_max(sequence=sch.sequences["sek"], old_max=12345, new_max=2**16)],
        ),
        (
            report(path=ROOT.sequences["sek"].cycle, left=False, right=True),
            [generator.alter_sequence_cycle(sequence=sch.sequences["sek"], old_cycle=False, new_cycle=True)],
        ),
        (
            report(path=ROOT.sequences["sek"].extra, left={"a": 1}, right={"a": 2}),
            [generator.alter_sequence_extra(sequence=sch.sequences["sek"], old_extra={"a": 1}, new_extra={"a": 2})],
        ),
        (
            report(path=ROOT.functions["fn"].definition, left="left", right="right"),
            [
                generator.alter_function_definition(
                    function=sch.functions["fn"], old_definition="left", new_definition="right"
                )
            ],
        ),
        (
            report(path=ROOT.functions["fn"].extra, left={"a": 1}, right={"a": 2}),
            [generator.alter_function_extra(function=sch.functions["fn"], old_extra={"a": 1}, new_extra={"a": 2})],
        ),
        (
            report(path=ROOT.custom_types["mt"].values, left=["a", "b"], right=["a", "c"]),
            [
                generator.alter_custom_type_values(
                    custom_type=sch.custom_types["mt"], old_values=["a", "b"], new_values=["a", "c"]
                )
            ],
        ),
        (
            report(path=ROOT.custom_types["mt"].extra, left={"a": 1}, right={"a": 2}),
            [
                generator.alter_custom_type_extra(
                    custom_type=sch.custom_types["mt"], old_extra={"a": 1}, new_extra={"a": 2}
                )
            ],
        ),
        # Level 3
        (
            report(
                path=ROOT.tables["foo"].columns["bar"].type,
                left=ComdabTypes.Integer(implem_name="BIGING"),
                right=ComdabTypes.Integer(implem_name="SMALLINT"),
            ),
            [
                generator.alter_column_type(
                    table=sch.tables["foo"],
                    column=sch.tables["foo"].columns["bar"],
                    old_type=ComdabTypes.Integer(implem_name="BIGING"),
                    new_type=ComdabTypes.Integer(implem_name="SMALLINT"),
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].columns["bar"].nullable, left=False, right=True),
            [
                generator.alter_column_nullable(
                    table=sch.tables["foo"],
                    column=sch.tables["foo"].columns["bar"],
                    old_nullable=False,
                    new_nullable=True,
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].columns["bar"].default, left="o", right=None),
            [
                generator.alter_column_default(
                    table=sch.tables["foo"], column=sch.tables["foo"].columns["bar"], old_type="o", new_type=None
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].columns["bar"].generation_expression, left=None, right="eee"),
            [
                generator.alter_column_generation_expression(
                    table=sch.tables["foo"], column=sch.tables["foo"].columns["bar"], old_expr=None, new_expr="eee"
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].columns["bar"].extra, left={"a": 1}, right={"a": 2}),
            [
                generator.alter_column_extra(
                    table=sch.tables["foo"],
                    column=sch.tables["foo"].columns["bar"],
                    old_extra={"a": 1},
                    new_extra={"a": 2},
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].type, left="unique", right="check"),
            [
                generator.alter_constraint_type(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],
                    old_type="unique",
                    new_type="check",
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].deferrable, left=False, right=None),
            [
                generator.alter_constraint_deferrable(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],
                    old_deferrable=False,
                    new_deferrable=None,
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].initially, left=None, right="fooo"),
            [
                generator.alter_constraint_initially(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],
                    old_initially=None,
                    new_initially="fooo",
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].extra, left={"a": 1}, right={"a": 2}),
            [
                generator.alter_constraint_extra(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],
                    old_extra={"a": 1},
                    new_extra={"a": 2},
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].columns, left={"a", "b"}, right={"a", "c"}),
            [
                generator.alter_constraint_columns(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],  # pyright: ignore[reportArgumentType]
                    old_columns={"a", "b"},
                    new_columns={"a", "c"},
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].columns_mapping, left={"a": "b"}, right={"a": "c"}),
            [
                generator.alter_constraint_columns_mapping(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],  # pyright: ignore[reportArgumentType]
                    old_columns_mapping={"a": "b"},
                    new_columns_mapping={"a": "c"},
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].on_update, left="huh", right=None),
            [
                generator.alter_constraint_on_update(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],  # pyright: ignore[reportArgumentType]
                    old_on_update="huh",
                    new_on_update=None,
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].on_delete, left="1", right="2"),
            [
                generator.alter_constraint_on_delete(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],  # pyright: ignore[reportArgumentType]
                    old_on_delete="1",
                    new_on_delete="2",
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].constraints["con"].sql_text, left="left", right="right"),
            [
                generator.alter_constraint_sql_text(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],  # pyright: ignore[reportArgumentType]
                    old_sql_text="left",
                    new_sql_text="right",
                )
            ],
        ),
        (
            report(
                path=ROOT.tables["foo"].constraints["con"].attributes_and_operators,
                left=[("zou", "=")],
                right=[("zou", "!=")],
            ),
            [
                generator.alter_constraint_attributes_and_operators(
                    table=sch.tables["foo"],
                    constraint=sch.tables["foo"].constraints["con"],  # pyright: ignore[reportArgumentType]
                    old_attributes_and_operators=[("zou", "=")],
                    new_attributes_and_operators=[("zou", "!=")],
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].indexes["ix"].expressions, left=["left"], right=["right"]),
            [
                generator.alter_index_expressions(
                    table=sch.tables["foo"],
                    index=sch.tables["foo"].indexes["ix"],
                    old_expressions=["left"],
                    new_expressions=["right"],
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].indexes["ix"].unique, left=True, right=False),
            [
                generator.alter_index_unique(
                    table=sch.tables["foo"], index=sch.tables["foo"].indexes["ix"], old_unique=True, new_unique=False
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].indexes["ix"].extra, left={"a": 1}, right={"a": 2}),
            [
                generator.alter_index_extra(
                    table=sch.tables["foo"],
                    index=sch.tables["foo"].indexes["ix"],
                    old_extra={"a": 1},
                    new_extra={"a": 2},
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].triggers["tri"].definition, left="left", right="right"),
            [
                generator.alter_trigger_definition(
                    table=sch.tables["foo"],
                    trigger=sch.tables["foo"].triggers["tri"],
                    old_definition="left",
                    new_definition="right",
                )
            ],
        ),
        (
            report(path=ROOT.tables["foo"].triggers["tri"].extra, left={"a": 1}, right={"a": 2}),
            [
                generator.alter_trigger_extra(
                    table=sch.tables["foo"],
                    trigger=sch.tables["foo"].triggers["tri"],
                    old_extra={"a": 1},
                    new_extra={"a": 2},
                )
            ],
        ),
    ],
    ids=lambda obj: (
        str(obj.path)
        if isinstance(obj, ComdabReport)
        else str(obj[0]).split("(", maxsplit=1)[0].removeprefix("generator.")
    ),
)
def test_generate_migration_calls(report: ComdabReport, expected_calls: mock._Call) -> None:  # pyright: ignore[reportPrivateUsage]
    generator = mock.Mock(MigrationGeneratorPort)
    generate_migration(sch, report, generator)
    assert generator.mock_calls == expected_calls


def _generate_all_possible_paths(root: ComdabPath) -> Iterator[ComdabPath]:
    for name, attr in inspect.getmembers(root, lambda x: isinstance(x, ComdabPath)):
        if name == "name":  # cannot change
            continue
        if isinstance(attr, ComdabPathDict) and attr._generic_type is not ComdabPath:  # pyright: ignore[reportPrivateUsage]
            yield attr.left_only
            yield attr.right_only
            yield from _generate_all_possible_paths(attr[...])
        else:
            yield attr


@pytest.mark.parametrize(["path"], [(x,) for x in _generate_all_possible_paths(ROOT)], ids=str)
def test_migration_generator_full_coverage(path: ComdabPath) -> None:
    generator = mock.Mock(MigrationGeneratorPort)
    generate_migration(mock.MagicMock(), report(path=path, left={"a": ...}, right={"a": ...}), generator)
    assert len(generator.mock_calls) == 1


def test_migration_generator_port_subclassing() -> None:
    class TestFull(MigrationGeneratorPort):
        def create_table(self, *, table: ComdabTable) -> None:
            pass

    class TestFullNotStrict(MigrationGeneratorPort, strict=False):
        def create_table(self, *, table: ComdabTable) -> None:
            pass

    class TestPartial(PartialMigrationGeneratorPort):
        called = 0

        def create_table(self, *, table: ComdabTable) -> None:
            self.called += 1

    class TestPartialNotStrict(PartialMigrationGeneratorPort, strict=False):
        called = 0

        def create_table(self, *, table: ComdabTable) -> None:
            self.called += 1

    with pytest.raises(TypeError):
        TestFull()  # pyright: ignore[reportAbstractUsage]
    with pytest.raises(TypeError):
        TestFullNotStrict()  # pyright: ignore[reportAbstractUsage]

    generator = TestPartial()
    generator.create_table(table=sch.tables["foo"])
    assert generator.called == 1
    with pytest.raises(NotImplementedError):
        generator.drop_table(table=sch.tables["foo"])
    assert generator.called == 1

    generator = TestPartialNotStrict()
    generator.create_table(table=sch.tables["foo"])
    assert generator.called == 1
    generator.drop_table(table=sch.tables["foo"])
    assert generator.called == 1

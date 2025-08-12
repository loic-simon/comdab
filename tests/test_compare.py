from copy import replace
from typing import cast

import pytest

from comdab.compare import ComdabComparer, ComdabStrategy
from comdab.models import (
    ROOT,
    ComdabColumn,
    ComdabFunction,
    ComdabIndex,
    ComdabPrimaryKeyConstraint,
    ComdabSchema,
    ComdabSequence,
    ComdabTable,
    ComdabTrigger,
    ComdabTypes,
    ComdabUniqueConstraint,
    ComdabView,
)
from comdab.models.custom_type import ComdabCustomType
from comdab.path import ComdabPath
from comdab.report import ComdabReport

EMPTY_SCHEMA = ComdabSchema(
    tables={},
    views={},
    sequences={},
    functions={},
    custom_types={},
)

FULL_SCHEMA = ComdabSchema(
    tables={
        "table1": ComdabTable(
            name="table1",
            columns={
                "col1": ComdabColumn(
                    name="col1",
                    type=ComdabTypes.Array(
                        implem_name="ARRAY_IMPL",
                        item_type=ComdabTypes.DateTime(implem_name="BIGINT", with_timezone=True, extra={"sal": 5}),
                        dimensions=2,
                        extra={"sal": 5},
                    ),
                    nullable=True,
                    default="generate_timestamp()",
                    generation_expression=None,
                    extra={"hey": 4},
                ),
                "col2": ComdabColumn(
                    name="col2",
                    type=ComdabTypes.Integer(implem_name="BIGINT"),
                    nullable=False,
                    default=None,
                    generation_expression="array_length(col1)",
                ),
            },
            constraints={
                "col1_pk": ComdabPrimaryKeyConstraint(
                    name="col1_pk", deferrable=False, initially=None, columns={"col1"}, extra={"no": [37]}
                ),
                "col1_col2_uq": ComdabUniqueConstraint(
                    name="col1_col2_uq", deferrable=True, initially="DEFERRED", columns={"col1", "col2"}
                ),
            },
            indexes={
                "ix_col1": ComdabIndex(
                    name="ix_col1", expressions=["col2", "my_func(col1)"], unique=True, extra={"jsp": {}}
                ),
                "ix2": ComdabIndex(name="ix2", expressions=["other_func(col1)"], unique=False),
            },
            triggers={
                "on_create_delete": ComdabTrigger(
                    name="on_create_delete", definition="CREATE TRIGGER...", extra={"type": "on_statement"}
                ),
                "other_trigger": ComdabTrigger(name="other_trigger", definition="CREATE OTHER TRIGGER..."),
            },
            extra={"hello": 3},
        ),
        "table2": ComdabTable(
            name="table2",
            columns={
                "col3": ComdabColumn(
                    name="col3",
                    type=ComdabTypes.String(length=None, collation=None, implem_name="BIGINT"),
                    nullable=False,
                    default=None,
                    generation_expression=None,
                ),
            },
            constraints={
                "col3_pk": ComdabPrimaryKeyConstraint(
                    name="col3_pk", deferrable=False, initially=None, columns={"col1"}, extra={"no": [37]}
                ),
            },
            indexes={},
            triggers={},
        ),
    },
    views={
        "_table1": ComdabView(
            name="_table1", definition="SELECT * FROM table1;", materialized=False, extra={"useful": False}
        ),
        "_table1_mat": ComdabView(
            name="_table1_mat", definition="SELECT * FROM table1 WHERE false;", materialized=True
        ),
    },
    sequences={
        "seq1": ComdabSequence(
            name="seq1",
            type_name="int4",
            start=2,
            increment=3,
            min=2,
            max=312,
            cycle=True,
            extra={"wtf": "yes"},
        ),
        "seq2": ComdabSequence(name="seq2", type_name="int4", start=1, increment=1, min=1, max=1000, cycle=False),
    },
    functions={
        "my_func": ComdabFunction(
            name="my_func",
            definition="CREATE OR REPLACE FUNCTION...",
            extra={"lang": "fr"},
        ),
        "other_func": ComdabFunction(name="other_func", definition="CREATE OR REPLACE OTHER FUNCTION..."),
    },
    custom_types={
        "my_enum": ComdabCustomType(name="my_enum", values=["one", "two"]),
        "my_enum_2": ComdabCustomType(name="my_enum_2", values=["Three (3)", "FOUR"]),
    },
    extra={
        "extra1": "foo",
        "extra2": {"key1": True, "key2": False},
    },
)


def test_same_schemas() -> None:
    comparer = ComdabComparer()
    assert comparer.compare(EMPTY_SCHEMA, EMPTY_SCHEMA) == []
    assert comparer.compare(FULL_SCHEMA, FULL_SCHEMA) == []


def test_empty_vs_full() -> None:
    comparer = ComdabComparer()
    assert comparer.compare(EMPTY_SCHEMA, FULL_SCHEMA) == [
        ComdabReport("error", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("error", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
        ComdabReport("error", ROOT.views.right_only, {}, {"_table1": FULL_SCHEMA.views["_table1"]}),
        ComdabReport("error", ROOT.views.right_only, {}, {"_table1_mat": FULL_SCHEMA.views["_table1_mat"]}),
        ComdabReport("error", ROOT.sequences.right_only, {}, {"seq1": FULL_SCHEMA.sequences["seq1"]}),
        ComdabReport("error", ROOT.sequences.right_only, {}, {"seq2": FULL_SCHEMA.sequences["seq2"]}),
        ComdabReport("error", ROOT.functions.right_only, {}, {"my_func": FULL_SCHEMA.functions["my_func"]}),
        ComdabReport("error", ROOT.functions.right_only, {}, {"other_func": FULL_SCHEMA.functions["other_func"]}),
        ComdabReport("error", ROOT.custom_types.right_only, {}, {"my_enum": FULL_SCHEMA.custom_types["my_enum"]}),
        ComdabReport("error", ROOT.custom_types.right_only, {}, {"my_enum_2": FULL_SCHEMA.custom_types["my_enum_2"]}),
        ComdabReport("error", ROOT.extra.right_only, {}, {"extra1": FULL_SCHEMA.extra["extra1"]}),
        ComdabReport("error", ROOT.extra.right_only, {}, {"extra2": FULL_SCHEMA.extra["extra2"]}),
    ]
    assert comparer.compare(FULL_SCHEMA, EMPTY_SCHEMA) == [
        ComdabReport("error", ROOT.tables.left_only, {"table1": FULL_SCHEMA.tables["table1"]}, {}),
        ComdabReport("error", ROOT.tables.left_only, {"table2": FULL_SCHEMA.tables["table2"]}, {}),
        ComdabReport("error", ROOT.views.left_only, {"_table1": FULL_SCHEMA.views["_table1"]}, {}),
        ComdabReport("error", ROOT.views.left_only, {"_table1_mat": FULL_SCHEMA.views["_table1_mat"]}, {}),
        ComdabReport("error", ROOT.sequences.left_only, {"seq1": FULL_SCHEMA.sequences["seq1"]}, {}),
        ComdabReport("error", ROOT.sequences.left_only, {"seq2": FULL_SCHEMA.sequences["seq2"]}, {}),
        ComdabReport("error", ROOT.functions.left_only, {"my_func": FULL_SCHEMA.functions["my_func"]}, {}),
        ComdabReport("error", ROOT.functions.left_only, {"other_func": FULL_SCHEMA.functions["other_func"]}, {}),
        ComdabReport("error", ROOT.custom_types.left_only, {"my_enum": FULL_SCHEMA.custom_types["my_enum"]}, {}),
        ComdabReport("error", ROOT.custom_types.left_only, {"my_enum_2": FULL_SCHEMA.custom_types["my_enum_2"]}, {}),
        ComdabReport("error", ROOT.extra.left_only, {"extra1": FULL_SCHEMA.extra["extra1"]}, {}),
        ComdabReport("error", ROOT.extra.left_only, {"extra2": FULL_SCHEMA.extra["extra2"]}, {}),
    ]


@pytest.mark.parametrize(
    ("updated", "expected_path", "expected_left", "expected_right"),
    [
        (
            replace(
                (s := FULL_SCHEMA),
                tables={
                    **s.tables,
                    "table1": replace((t := s.tables["table1"]), columns={"col1": t.columns["col1"]}),
                },
            ),
            ROOT.tables["table1"].columns.right_only,
            {},
            {"col2": t.columns["col2"]},
        ),
        (
            replace(
                (s := FULL_SCHEMA),
                tables={
                    **s.tables,
                    "table1": replace(
                        (t := s.tables["table1"]),
                        columns={
                            **t.columns,
                            "col1": replace(t.columns["col1"], nullable=False),
                        },
                    ),
                },
            ),
            ROOT.tables["table1"].columns["col1"].nullable,
            False,
            True,
        ),
        (
            replace(
                (s := FULL_SCHEMA),
                tables={
                    **s.tables,
                    "table1": replace(
                        (t := s.tables["table1"]),
                        columns={
                            **t.columns,
                            "col1": replace(
                                (c := t.columns["col1"]),
                                type=replace(
                                    (tp := cast(ComdabTypes.Array, c.type)),
                                    item_type=replace(tp.item_type, with_timezone=False),
                                ),
                            ),
                        },
                    ),
                },
            ),
            ROOT.tables["table1"].columns["col1"].type.item_type.with_timezone,
            False,
            True,
        ),
        (
            replace(FULL_SCHEMA, extra={**FULL_SCHEMA.extra, "extra2": {"key1": True}}),
            ROOT.extra["extra2"],  # No deep comparison of dict extras
            {"key1": True},
            {"key1": True, "key2": False},
        ),
    ],
)
def test_subtil_differences(
    updated: ComdabSchema, expected_path: ComdabPath, expected_left: object, expected_right: object
) -> None:
    comparer = ComdabComparer()
    assert comparer.compare(updated, FULL_SCHEMA) == [
        ComdabReport("error", expected_path, expected_left, expected_right)
    ]


def test_rules_empty_vs_full() -> None:
    def _test(rules: dict[ComdabPath, ComdabStrategy]) -> list[ComdabReport]:
        comparer = ComdabComparer(rules=rules)
        return comparer.compare(EMPTY_SCHEMA, FULL_SCHEMA)

    assert _test({}) == [
        ComdabReport("error", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("error", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
        ComdabReport("error", ROOT.views.right_only, {}, {"_table1": FULL_SCHEMA.views["_table1"]}),
        ComdabReport("error", ROOT.views.right_only, {}, {"_table1_mat": FULL_SCHEMA.views["_table1_mat"]}),
        ComdabReport("error", ROOT.sequences.right_only, {}, {"seq1": FULL_SCHEMA.sequences["seq1"]}),
        ComdabReport("error", ROOT.sequences.right_only, {}, {"seq2": FULL_SCHEMA.sequences["seq2"]}),
        ComdabReport("error", ROOT.functions.right_only, {}, {"my_func": FULL_SCHEMA.functions["my_func"]}),
        ComdabReport("error", ROOT.functions.right_only, {}, {"other_func": FULL_SCHEMA.functions["other_func"]}),
        ComdabReport("error", ROOT.custom_types.right_only, {}, {"my_enum": FULL_SCHEMA.custom_types["my_enum"]}),
        ComdabReport("error", ROOT.custom_types.right_only, {}, {"my_enum_2": FULL_SCHEMA.custom_types["my_enum_2"]}),
        ComdabReport("error", ROOT.extra.right_only, {}, {"extra1": FULL_SCHEMA.extra["extra1"]}),
        ComdabReport("error", ROOT.extra.right_only, {}, {"extra2": FULL_SCHEMA.extra["extra2"]}),
    ]
    assert _test({ROOT: "warning"}) == [
        ComdabReport("warning", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("warning", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
        ComdabReport("warning", ROOT.views.right_only, {}, {"_table1": FULL_SCHEMA.views["_table1"]}),
        ComdabReport("warning", ROOT.views.right_only, {}, {"_table1_mat": FULL_SCHEMA.views["_table1_mat"]}),
        ComdabReport("warning", ROOT.sequences.right_only, {}, {"seq1": FULL_SCHEMA.sequences["seq1"]}),
        ComdabReport("warning", ROOT.sequences.right_only, {}, {"seq2": FULL_SCHEMA.sequences["seq2"]}),
        ComdabReport("warning", ROOT.functions.right_only, {}, {"my_func": FULL_SCHEMA.functions["my_func"]}),
        ComdabReport("warning", ROOT.functions.right_only, {}, {"other_func": FULL_SCHEMA.functions["other_func"]}),
        ComdabReport("warning", ROOT.custom_types.right_only, {}, {"my_enum": FULL_SCHEMA.custom_types["my_enum"]}),
        ComdabReport("warning", ROOT.custom_types.right_only, {}, {"my_enum_2": FULL_SCHEMA.custom_types["my_enum_2"]}),
        ComdabReport("warning", ROOT.extra.right_only, {}, {"extra1": FULL_SCHEMA.extra["extra1"]}),
        ComdabReport("warning", ROOT.extra.right_only, {}, {"extra2": FULL_SCHEMA.extra["extra2"]}),
    ]
    assert _test({ROOT: "ignore"}) == []

    assert _test({ROOT.views: "warning", ROOT.sequences: "ignore"}) == [
        ComdabReport("error", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("error", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
        ComdabReport("warning", ROOT.views.right_only, {}, {"_table1": FULL_SCHEMA.views["_table1"]}),
        ComdabReport("warning", ROOT.views.right_only, {}, {"_table1_mat": FULL_SCHEMA.views["_table1_mat"]}),
        ComdabReport("error", ROOT.functions.right_only, {}, {"my_func": FULL_SCHEMA.functions["my_func"]}),
        ComdabReport("error", ROOT.functions.right_only, {}, {"other_func": FULL_SCHEMA.functions["other_func"]}),
        ComdabReport("error", ROOT.custom_types.right_only, {}, {"my_enum": FULL_SCHEMA.custom_types["my_enum"]}),
        ComdabReport("error", ROOT.custom_types.right_only, {}, {"my_enum_2": FULL_SCHEMA.custom_types["my_enum_2"]}),
        ComdabReport("error", ROOT.extra.right_only, {}, {"extra1": FULL_SCHEMA.extra["extra1"]}),
        ComdabReport("error", ROOT.extra.right_only, {}, {"extra2": FULL_SCHEMA.extra["extra2"]}),
    ]

    assert _test({ROOT.tables.right_only: "warning", ROOT.views.left_only: "warning"})[:4] == [
        ComdabReport("warning", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("warning", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
        ComdabReport("error", ROOT.views.right_only, {}, {"_table1": FULL_SCHEMA.views["_table1"]}),
        ComdabReport("error", ROOT.views.right_only, {}, {"_table1_mat": FULL_SCHEMA.views["_table1_mat"]}),
    ]
    assert _test({ROOT.tables["table1"]: "warning"})[:2] == [
        ComdabReport("warning", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("error", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
    ]
    assert _test({ROOT.tables[".+2"]: "warning"})[:2] == [
        ComdabReport("error", ROOT.tables.right_only, {}, {"table1": FULL_SCHEMA.tables["table1"]}),
        ComdabReport("warning", ROOT.tables.right_only, {}, {"table2": FULL_SCHEMA.tables["table2"]}),
    ]

    # just to test left_only too
    assert ComdabComparer(rules={ROOT.tables.left_only: "warning"}).compare(FULL_SCHEMA, EMPTY_SCHEMA)[:2] == [
        ComdabReport("warning", ROOT.tables.left_only, {"table1": FULL_SCHEMA.tables["table1"]}, {}),
        ComdabReport("warning", ROOT.tables.left_only, {"table2": FULL_SCHEMA.tables["table2"]}, {}),
    ]


def test_rules_subtil_difference() -> None:
    updated = replace(
        (s := FULL_SCHEMA),
        tables={
            **s.tables,
            "table1": replace(
                (t := s.tables["table1"]),
                columns={
                    **t.columns,
                    "col1": replace(
                        (c := t.columns["col1"]),
                        type=replace(
                            (tp := cast(ComdabTypes.Array, c.type)),
                            item_type=replace(tp.item_type, with_timezone=False),
                        ),
                    ),
                },
            ),
        },
    )
    difference_path = ROOT.tables["table1"].columns["col1"].type.item_type.with_timezone

    def _test(rules: dict[ComdabPath, ComdabStrategy]) -> ComdabStrategy:
        comparer = ComdabComparer(rules=rules)
        match comparer.compare(updated, FULL_SCHEMA):
            case []:
                return "ignore"
            case [ComdabReport() as report]:
                assert report.path is difference_path
                assert report.left is False
                assert report.right is True
                return report.level
            case _ as reports:
                raise AssertionError(reports)

    assert _test({}) == "error"

    assert _test({ROOT: "warning"}) == "warning"
    assert _test({ROOT: "ignore"}) == "ignore"

    assert _test({ROOT: "warning", ROOT.tables: "error"}) == "error"
    assert _test({ROOT: "ignore", ROOT.tables: "error"}) == "error"
    assert _test({ROOT: "ignore", ROOT.tables: "warning"}) == "warning"

    assert _test({ROOT: "warning", ROOT.tables["table1"]: "error"}) == "error"
    assert _test({ROOT: "warning", ROOT.tables["table2"]: "error"}) == "warning"
    assert _test({ROOT: "warning", ROOT.tables["bzbzbz"]: "error"}) == "warning"
    assert _test({ROOT: "warning", ROOT.tables[...]: "error"}) == "error"
    assert _test({ROOT: "warning", ROOT.tables[r"\w*1"]: "error"}) == "error"
    assert _test({ROOT: "warning", ROOT.tables[r"\w*2"]: "error"}) == "warning"

    assert _test({ROOT.tables[r"\w*1"]: "warning", ROOT.tables[...].columns: "error"}) == "error"
    assert _test({ROOT.tables[r"\w*1"]: "warning", ROOT.tables[...].columns[...]: "error"}) == "error"
    assert _test({ROOT.tables[r"\w*1"]: "warning", ROOT.tables[...].columns.left_only: "error"}) == "warning"
    assert _test({ROOT.tables[r"\w*1"]: "warning", ROOT.tables[...].columns[r"\w*1"]: "error"}) == "error"
    assert _test({ROOT.tables[r"\w*1"]: "warning", ROOT.tables[...].columns[r"\w*2"]: "error"}) == "warning"

    _cols = ROOT.tables[r"\w*1"].columns[r"\w*1"]
    assert _test({_cols: "warning", ROOT.tables[...].columns[...].nullable: "error"}) == "warning"
    assert _test({_cols: "warning", ROOT.tables[...].columns[...].type: "error"}) == "error"
    assert _test({_cols: "warning", ROOT.tables[...].columns[...].type.item_type: "error"}) == "error"
    assert _test({_cols: "warning", ROOT.tables[...].columns[...].type.item_type.length: "error"}) == "warning"
    assert _test({_cols: "warning", ROOT.tables[...].columns[...].type.item_type.with_timezone: "error"}) == "error"

    assert _test({_cols: "warning", ROOT.tables[...].columns[...].type.with_timezone: "error"}) == "warning"

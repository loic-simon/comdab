from dataclasses import dataclass

import pytest
from sqlalchemy import TextClause

from comdab.exceptions import ComdabInternalError
from comdab.utils import dict_by_name, typed_sql


def test_dict_by_name() -> None:
    @dataclass
    class _Test:
        name: str

    assert dict_by_name(()) == {}
    assert list(dict_by_name((_Test("a"), _Test("c"), _Test("b"))).items()) == [  # Use .items() to test dict order
        ("a", _Test("a")),
        ("b", _Test("b")),
        ("c", _Test("c")),
    ]
    with pytest.raises(ComdabInternalError, match="duplicate keys"):
        dict_by_name((_Test("a"), _Test("c"), _Test("a")))


def test_typed_sql() -> None:
    assert isinstance(typed_sql(""), TextClause)
    assert str(typed_sql("").compile()) == ""
    STRING = """--sql
                INDENTED
                MULTI-LINE
                STRING;
                """
    assert str(typed_sql(STRING).compile()) == "INDENTED\nMULTI-LINE\nSTRING;\n"

from itertools import chain

import pytest
from sqlalchemy import MetaData

from comdab.compare import ComdabComparer
from comdab.models import ComdabSchema


def pytest_assertrepr_compare(op: str, left: object, right: object) -> list[str] | None:
    """Custom pytest hook for readable display of ComdabSchema differences in tests.

    See https://docs.pytest.org/en/stable/how-to/assert.html#defining-your-own-explanation-for-failed-assertions
    """
    if op == "==" and isinstance(left, ComdabSchema) and isinstance(right, ComdabSchema):
        reports = ComdabComparer().compare(left, right)
        if not reports:
            return ["!!!!! pytest compared models unequal, but ComdabComparer found nothing !!!!!"]
        return [
            "schemas differ (ComdabComparer reports):",
            *chain(
                *((f"* {report.path}:", f"   left : {report.left}", f"   right: {report.right}") for report in reports)
            ),
        ]


_NAMING_CONVENTION = {  # Needed so auto-generated constraints/indexes have a name
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0N_name)s",
    "uq": "uq_%(table_name)s_%(column_0N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(column_0N_label)s",
}


@pytest.fixture(scope="function")
def meta() -> MetaData:
    return MetaData(naming_convention=_NAMING_CONVENTION)


@pytest.fixture(scope="function")
def meta_other() -> MetaData:
    return MetaData(schema="other", naming_convention=_NAMING_CONVENTION)

from dataclasses import dataclass
from typing import Literal

from comdab.path import ComdabPath


@dataclass(frozen=True, slots=True)
class ComdabReport:
    """A difference between two database schemas, reported by comdab.

    Should not be instantiated manually.

    Args:
        level: Whether the report is for an error (default) or a warning (caused by a custom rule).
        path: The path to the difference between the two schemas.
        left: The value in the left schema.
        right: The value in the right schema.

    Examples:
        * A column is nullable in the left schema, not in the right::

            ComdabReport(level="error", path=ROOT.tables['foo'].columns['bar'].nullable, left=True, right=False)

        * A table is present only in the left schema::

            ComdabReport(level="error", path=ROOT.tables.left_only, left={'foo': ComdabTable(...)}, right={})

        * Two columns are present only in the right schema::

            ComdabReport(level="error", path=ROOT.tables['foo'].right_only, left={}, right={'bar': ComdabColumn(...)})
            ComdabReport(level="error", path=ROOT.tables['foo'].right_only, left={}, right={'baz': ComdabColumn(...)})
    """

    level: Literal["warning", "error"]
    path: ComdabPath
    left: object
    right: object

from dataclasses import dataclass

from sqlalchemy import Connection


@dataclass(kw_only=True, frozen=True)
class ComdabSource:
    """A database source to use for SQL model creation."""

    connection: Connection
    schema_name: str = "public"

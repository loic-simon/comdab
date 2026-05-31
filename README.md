# comdab — Compare Database Schemas

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/comdab)](https://pypi.org/p/comdab)
[![PyPI - Version](https://img.shields.io/pypi/v/comdab)](https://pypi.org/p/comdab)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/loic-simon/comdab/test.yml?label=tests)](https://github.com/loic-simon/comdab/actions/workflows/test.yml)
[![Read the Docs](https://img.shields.io/readthedocs/comdab)](https://comdab.readthedocs.io)
![PyPI - Types](https://img.shields.io/pypi/types/comdab)

_comdab_ allows you to compare in depth two database schemas to find
all differences: missing columns, different nullabilities or defaults,
slight changes in function or triggers definitions...

> [!WARNING]
>
> _comdab_ is still in development, only tested with PostgreSQL 14 — 18 to date.
>
> All feedback and contributions are welcome!

## Installation

Use [pip](https://pip.pypa.io) to install comdab:

```bash
pip install comdab
```

### Requirements

- Python `>= 3.13`
- [sqlalchemy](https://pypi.org/project/sqlalchemy) `>= 2.0`
- [pydantic](https://pypi.org/project/pydantic) `>= 2.0`

## Goals

_comdab_ allows you to compare in depth two database schemas to find
all differences (missing columns, different nullabilities or defaults,
slight changes in function or triggers definitions...) and turn these
reports into model migrations.

_comdab_ migration generation supercharges migration tools like
[Alembic](https://alembic.sqlalchemy.org) to create migrations that,
when applied to an existing database, produce **the exact same schema**
than a new database created from scratch.

Indeed, while migration tools can auto-detect model changes and write
automatically the migrations to apply to pre-existing databases, it does not
cover the whole schema complexity, and does not prevent human errors (like
modifying the model without re-generating migrations, or manually editing
migrations in a slightly wrong way...)

This may cause dangerous and hard to spot bugs, especially if your unit tests
and CI run on a fresh database created from the Python-written model, and not
on pre-existing databases with the new migration applied.

By running _comdab_, you can ensure the two are the nearly-exact same.

_comdab_ is based on the wonderful [SQLAlchemy](https://sqlalchemy.org) library
to connect to the database, and for most of schema introspection.

## Usage

### Comparing database schemas

_comdab_ main reporting function is
[`.compare_databases`](https://comdab.readthedocs.io/en/latest/reference.html#comdab.compare_databases),
which needs already established SQLAlchemy connections to the two databases to compare:

```py
from comdab import compare_databases
from sqlalchemy import create_engine

engine_1 = create_engine("postgresql://user:pass@host/foo")
engine_2 = create_engine("postgresql://user:pass@host/bar")

with engine_1.connect() as left_conn, engine_2.connect() as right_conn:
    reports = compare_databases(left_conn, right_conn)

if reports:
    print("❌ Database schemas are different:", reports)
else:
    print("✅ Database schemas are the same!")
```

### Generating migrations

To generate migrations, a user-defined
[`MigrationGeneratorPort`](https://comdab.readthedocs.io/en/latest/reference.html#comdab.MigrationGeneratorPort) /
[`PartialMigrationGeneratorPort`](https://comdab.readthedocs.io/en/latest/reference.html#comdab.MigrationGeneratorPort)
subclass is additionally needed:

```py
from comdab import generate_migrations, PartialMigrationGeneratorPort
from comdab.models import ComdabTable
from sqlalchemy import create_engine

class MyMigrationGenerator(PartialMigrationGeneratorPort):
    def __init__(self) -> None:
        self.sql_text = ""

    def create_table(self, *, table: ComdabTable) -> None:
        self.sql_text += f"CREATE TABLE {table.name} [...];\n"

    def drop_table(self, *, table: ComdabTable) -> None:
        self.sql_text += f"DROP TABLE {table.name};\n"

    ...

generator = MyMigrationGenerator()
engine_1 = create_engine("postgresql://user:pass@host/source")
engine_2 = create_engine("postgresql://user:pass@host/target")

with engine_1.connect() as source_conn, engine_2.connect() as target_conn:
    generate_migrations(source_conn, target_conn, generator)

print(generator.sql_text)
```

### Advanced usage

See [documentation](https://comdab.readthedocs.io) for configuration and other details.

## Contributing

Issues and pull requests are welcome!

## License

This work is shared under [the MIT license](LICENSE).

@ 2025 Loïc Simon ([loic.simon@espci.org](mailto:loic.simon@espci.org))

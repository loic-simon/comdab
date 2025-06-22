# comdab — Compare Database Schemas

_comdab_ allows you to compare in depth two database schemas to find
all differences: missing columns, different nullabilities or defaults,
slight changes in function or triggers definitions...

> [!WARNING]
>
> _comdab_ is still in development, only tested with PostgreSQL 14 to date.
>
> All feedback and contributions are welcome!

## Installation

Use [pip](https://pip.pypa.io) to install comdab:

```bash
pip install comdab
```

### Requirements

- Python `>= 3.12`
- [sqlalchemy](https://pypi.org/project/sqlalchemy) `>= 2.0`
- [pydantic](https://pypi.org/project/pydantic) `>= 2.0`

## Goals

_comdab_ is especially useful in combination with a migration tool like
[Alembic](https://alembic.sqlalchemy.org), to make sure that applying a
migration to an existing database
and creating a new database from scratch produce **the exact same schema**.

Indeed, while migration tools can auto-detect model changes and write
automatically the migrations to apply to pre-existing databases, it does not
cover the whole schema complexity, and does not prevent human errors (like
modifying the model without re-generating migrations, or manually editing
migrations in a slightly wrong way...)

This may cause dangerous and hard to spot bugs, especially if your unit tests
and CI run on a fresh database created from the Python-written model, and not
on pre-existing databases with the new migration applied.

By running _comdab_, you can ensure the two are the nearly-exact same.

_comdab_ stands on the shoulders of the [SQLAlchemy](https://sqlalchemy.org)
library, used to connect to the database and for most of schema introspection.

## Usage

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

See documentation for configuration and other details.

## Contributing

Issues and pull requests are welcome!

## License

This work is shared under [the MIT license](LICENSE);

@ 2025 Loïc Simon ([loic.simon@espci.org](mailto:loic.simon@espci.org))

comdab -- Compare Database Schemas
==================================

.. toctree::
   :hidden:

   reference


*comdab* allows you to compare in depth two database schemas to find
all differences: missing columns, different nullabilities or defaults,
slight changes in function or triggers definitions...

It is especially useful in combination with a migration tool like
`Alembic`_, to make sure that applying a migration to an existing database
and creating a new database from scratch produce **the exact same schema**.

Indeed, while migration tools can auto-detect model changes and write
automatically the migrations to apply to pre-existing databases, it does not
cover the whole schema complexity, and does not prevent human errors (like
modifying the model without re-generating migrations, or manually editing
migrations in a slightly wrong way...)

This may cause dangerous and hard to spot bugs, especially if your unit tests
and CI run on a fresh database created from the Python-written model, and not
on pre-existing databases with the new migration applied.

By running *comdab*, you can ensure the two are the nearly-exact same.

*comdab* is based on the wonderful `SQLAlchemy <sqla_>`_ library to connect to
the database, and for most of schema introspection.

.. warning::

   *comdab* is still in development, only tested with PostgreSQL 14 to date.

   All feedback and contributions are welcome!


Requirements
------------

* Python >= 3.11
* `sqlalchemy <https://pypi.org/project/sqlalchemy>`_ >= 2.0
* `pydantic <https://pypi.org/project/pydantic>`_ >= 2.0


Installation
------------

.. code-block::bash

   pip install comdab


Usage
-----

*comdab* highest-level function is :func:`.compare_databases`, which needs
already established `SQLAlchemy connections`_ to the two databases to compare:

.. code-block:: python

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

These connections will, of course, only be used for read-only database
introspection.

To compare an existing database with a Python-defined schema, the latter
has to be created first in a fresh database:

.. code-block:: python

   from comdab import compare_databases
   from sqlalchemy import create_engine

   from my_app import BaseModel

   engine_1 = create_engine("postgresql://user:password@host/foo")
   engine_2 = create_engine("postgresql://user:password@host/tmp_db_just_created")

   with engine_1.connect() as left_connection, engine_2.connect() as right_connection:
      BaseModel.metadata.create_all(bind=right_connection)
      reports = compare_databases(left_connection, right_connection)


Supported database features
***************************

*comdab* heavily relies on SQLAlchemy `schema reflection`_ capabilities to
build its internal schema representation, but extends it (using custom queries)
to retrieve objects not natively handled by SQLALchemy.

Top-level schema fields

===========  ==========  ====================================================
Object       Support     Notes
===========  ==========  ====================================================
Tables       Yes
Views        Partial     PostgreSQL only (temporary + materialized)
Sequences    Partial     PostgreSQL only
Functions    Partial     PostgreSQL only (compares reconstructed definitions)
-----------  ----------  ----------------------------------------------------
Columns      Yes
Constraints  Partial     All databases: PK, FK, unique & check constraints;
                         PostgreSQL only: exclude constraints
Indexes      Yes
Triggers     Partial     PostgreSQL only (compares reconstructed definitions)
-----------  ----------  ----------------------------------------------------
Column type  Partial     All SQLALchemy common types;
                         PostgreSQL only: HSTORE, ranges, multiranges
Owners       No          No notion of users/roles/permissions...
Comments     No
===========  ==========  ====================================================

Each object can hold non-standard / dialect-specific data in a ``extra``
dictionary, that will be compared too (unless specifically ignored, see below).


Ignore rules
************

.. _ignorerules:

*comdab* comes with a powerful system to allow some specific differences
between the two schemas. :func:`.build_comdab_schema` and
:func:`.compare_databases` functions take a ``rules`` argument, where you
can specifies *paths* to be ignored or reported as warnings.

These are a mapping of model path (build from :attr:`comdab.ROOT`) to
directives (either ``"ignore"``, ``warning`` or ``error``), where a path
may override a more general exclusion:

.. code-block:: python

   rules={
      # Do not compare functions
      ROOT.functions: "ignore",
      # Report differences as warnings for all tables starting with "_"
      ROOT.tables["_.*"]: "warning",
      # Except for triggers, that are really importants
      ROOT.tables["_.*"].triggers: "error",
      # Allow all left tables to have extra columns
      ROOT.tables[...].columns.left_only: "ignore",  # [...] means [".*"]
      # But warn the other way around
      ROOT.tables[...].columns.right_only: "warning",
   }

Rules can use regular expressions, but two rules *cannot* match the same tables:
if you want to say "every tables but ``foo``", use ``(?!foo$).*``.


.. links

.. _Alembic: https://alembic.sqlalchemy.org
.. _sqla: https://sqlalchemy.org
.. _SQLAlchemy connections: https://docs.sqlalchemy.org/en/stable/code/connections.html
.. _schema reflection: https://docs.sqlalchemy.org/en/stable/code/reflecion.html

:tocdepth: 3

API Reference
=============

Entry points
------------

.. automodule:: comdab
   :members:
   :exclude-members: PartialMigrationGeneratorPort

.. class:: comdab.PartialMigrationGeneratorPort

   Like :class:`.MigrationGeneratorPort`, but does not require all migration methods to be implemented.

   By default, :exc:`NotImplementedError` will be raised if a missing method is called;
   to silently do nothing instead, use ``class MyGenerator(PartialMigrationGeneratorPort, strict=False)``.


Reports
-------

.. automodule:: comdab.report
   :members:


Models
------

.. automodule:: comdab.models
   :members:


Exceptions
----------

.. automodule:: comdab.exceptions
   :members:

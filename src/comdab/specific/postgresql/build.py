from collections.abc import Iterator
from functools import cached_property
from typing import Any

from sqlalchemy import MetaData, Table, types
from sqlalchemy.dialects.postgresql import HSTORE, ranges

from comdab.build import ComdabBuilder
from comdab.exceptions import UnhandledTypeError
from comdab.models.constraint import ComdabConstraint, ComdabExcludeConstraint
from comdab.models.custom_type import ComdabCustomType
from comdab.models.function import ComdabFunction
from comdab.models.sequence import ComdabSequence
from comdab.models.trigger import ComdabTrigger
from comdab.models.type import ComdabType, ComdabTypes
from comdab.models.view import ComdabView
from comdab.specific.postgresql.custom_types import get_postgresql_custom_types
from comdab.specific.postgresql.exclude_constraints import get_postgresql_exclude_constraints_by_table
from comdab.specific.postgresql.functions import get_postgresql_functions
from comdab.specific.postgresql.sequences import get_postgresql_sequences
from comdab.specific.postgresql.triggers import get_postgresql_triggers_by_table
from comdab.specific.postgresql.views import get_postgresql_views


class ComdabPostgreSQLBuilder(ComdabBuilder):
    # Level 1

    def generate_views(self, sa_metadata: MetaData) -> Iterator[ComdabView]:
        yield from super().generate_views(sa_metadata)
        yield from get_postgresql_views(self.source)

    def generate_sequences(self, sa_metadata: MetaData) -> Iterator[ComdabSequence]:
        yield from super().generate_sequences(sa_metadata)
        yield from get_postgresql_sequences(self.source)

    def generate_functions(self, sa_metadata: MetaData) -> Iterator[ComdabFunction]:
        yield from super().generate_functions(sa_metadata)
        yield from get_postgresql_functions(self.source)

    def generate_custom_types(self, sa_metadata: MetaData) -> Iterator[ComdabCustomType]:
        yield from super().generate_custom_types(sa_metadata)
        yield from get_postgresql_custom_types(self.source)

    # Level 2

    @cached_property
    def _exclude_constraints_by_table(self) -> dict[str, list[ComdabExcludeConstraint]]:
        return get_postgresql_exclude_constraints_by_table(self.source)

    def generate_constraints(self, sa_table: Table) -> Iterator[ComdabConstraint]:
        yield from super().generate_constraints(sa_table)
        yield from self._exclude_constraints_by_table.get(sa_table.name, ())

    @cached_property
    def _triggers_by_table(self) -> dict[str, list[ComdabTrigger]]:
        return get_postgresql_triggers_by_table(self.source)

    def generate_triggers(self, sa_table: Table) -> Iterator[ComdabTrigger]:
        yield from super().generate_triggers(sa_table)
        yield from self._triggers_by_table.get(sa_table.name, ())

    # Level 3

    def build_type(self, sa_type: types.TypeEngine[Any]) -> ComdabType:
        implem_name = sa_type.__visit_name__
        match sa_type:
            case HSTORE():
                return ComdabTypes.HSTORE(implem_name=implem_name)
            case ranges.AbstractMultiRange():
                return ComdabTypes.MultiRange(implem_name=implem_name, item_type=self._get_multirange_type(sa_type))
            case ranges.AbstractRange():
                return ComdabTypes.Range(implem_name=implem_name, item_type=self._get_range_type(sa_type))
            case _:
                return super().build_type(sa_type)

    def _get_range_type(self, sa_type: ranges.AbstractRange[Any]) -> ComdabType:
        sub_implem_name = sa_type.__visit_name__.removesuffix("RANGE")
        match sa_type:
            case ranges.INT4RANGE() | ranges.INT8RANGE():
                return ComdabTypes.Integer(implem_name=sub_implem_name)
            case ranges.NUMRANGE():
                return ComdabTypes.Numeric(implem_name=sub_implem_name, precision=None, scale=None)
            case ranges.TSRANGE():
                return ComdabTypes.DateTime(implem_name=sub_implem_name, with_timezone=False)
            case ranges.TSTZRANGE():
                return ComdabTypes.DateTime(implem_name=sub_implem_name, with_timezone=True)
            case ranges.DATERANGE():
                return ComdabTypes.Date(implem_name=sub_implem_name)
            case _:
                raise UnhandledTypeError(f"Unhandled PostgreSQL RANGE type: {sa_type}")

    def _get_multirange_type(self, sa_type: ranges.AbstractMultiRange[Any]) -> ComdabType:
        sub_implem_name = sa_type.__visit_name__.removesuffix("MULTIRANGE")
        match sa_type:
            case ranges.INT4MULTIRANGE() | ranges.INT8MULTIRANGE():
                return ComdabTypes.Integer(implem_name=sub_implem_name)
            case ranges.NUMMULTIRANGE():
                return ComdabTypes.Numeric(implem_name=sub_implem_name, precision=None, scale=None)
            case ranges.TSMULTIRANGE():
                return ComdabTypes.DateTime(implem_name=sub_implem_name, with_timezone=False)
            case ranges.TSTZMULTIRANGE():
                return ComdabTypes.DateTime(implem_name=sub_implem_name, with_timezone=True)
            case ranges.DATEMULTIRANGE():
                return ComdabTypes.Date(implem_name=sub_implem_name)
            case _:
                raise UnhandledTypeError(f"Unhandled PostgreSQL MULTIRANGE type: {sa_type}")

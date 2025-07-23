import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal, cast

from comdab.exceptions import OverlappingPathsError
from comdab.models.base import ComdabModel
from comdab.models.schema import ROOT, ComdabSchema
from comdab.path import (
    ComdabPath,
    ComdabPathDict,
    PathAttr,
    PathItem,
    get_path_component,
    get_path_depth,
)
from comdab.report import ComdabReport

type ComdabStrategy = Literal["error", "warning", "ignore"]


@dataclass(frozen=True, slots=True)
class _Rule:
    path: ComdabPath
    strategy: ComdabStrategy

    def get_attr_component(self, depth: int) -> str | None:
        comp = get_path_component(self.path, depth - 1)
        return comp.attr if isinstance(comp, PathAttr) else None

    def get_item_component(self, depth: int) -> str | None:
        comp = get_path_component(self.path, depth - 1)
        return comp.key if isinstance(comp, PathItem) else None

    def applies_to(self, depth: int) -> bool:
        return get_path_depth(self.path) == depth


class ComdabComparer:
    """Compare two comdab schemas to reveal their differences.

    Specific differences can be ignored or reported as warnings using custom rules.
    """

    def __init__(
        self,
        *,
        rules: dict[ComdabPath, ComdabStrategy] | None = None,
    ) -> None:
        self._rules = rules or {}
        self._default_rule = _Rule(path=ROOT, strategy="error")

    # SEMANTIC: we name
    #  * "crule" (Current Rule) -> a rule applying to the current level
    #  * "prule" (Potential Rule) -> a rule *maybe* applying the current level, or to a more precise attribute/item

    def compare(self, left: ComdabSchema, right: ComdabSchema) -> list[ComdabReport]:
        prules = [_Rule(path=path, strategy=strategy) for path, strategy in self._rules.items()]
        crule = next((rule for rule in prules if rule.applies_to(0)), self._default_rule)
        return list(
            self._compare(left, right, path=ROOT, crule=crule, prules=prules),
        )

    def _compare(
        self,
        left: object,
        right: object,
        *,
        path: ComdabPath,
        crule: _Rule,
        prules: list[_Rule],
    ) -> Iterator[ComdabReport]:
        depth = get_path_depth(path)

        if crule.strategy == "ignore" and not prules:
            # Don't report errors for this path, and no way to change later: we can abort here
            return

        if type(left) is not type(right) or not isinstance(left, ComdabModel):
            # Direct comparison
            if left != right and crule.strategy != "ignore":
                yield ComdabReport(level=crule.strategy, path=path, left=left, right=right)
            return

        # Deep model comparison
        fields = type(left).model_fields.keys()
        field_depth = depth + 1

        # Get the rules specific to each field
        prules_by_field = defaultdict[str, list[_Rule]](list)
        for rule in prules:
            if attr := rule.get_attr_component(field_depth):
                prules_by_field[attr].append(rule)

        # Compare field by field
        for field in fields:
            left_attr = getattr(left, field)
            right_attr = getattr(right, field)
            field_path = getattr(path, field)  # Exists if path is consistent with model (enforced by tests)

            field_prules = prules_by_field[field]
            field_crule = next((rule for rule in field_prules if rule.applies_to(field_depth)), crule)

            if not isinstance(field_path, ComdabPathDict):
                # Scalars: compare attributes directly
                yield from self._compare(
                    left_attr,
                    right_attr,
                    path=field_path,
                    crule=field_crule,
                    prules=field_prules,
                )
                continue

            # Mappings: compare key by key
            left_dict = cast(dict[str, Any], left_attr)
            right_dict = cast(dict[str, Any], right_attr)

            all_keys = sorted(left_dict | right_dict)
            key_depth = field_depth + 1

            left_only_crule = next(
                (rule for rule in field_prules if rule.get_attr_component(key_depth) == "left_only"), None
            )
            right_only_crule = next(
                (rule for rule in field_prules if rule.get_attr_component(key_depth) == "right_only"), None
            )

            for key in all_keys:
                # Key in both dicts: compare, using the matching rule, else field rule
                key_prules = [rule for rule in field_prules if _regex_applies(rule.get_item_component(key_depth), key)]
                key_crules = [rule for rule in key_prules if rule.applies_to(key_depth)]
                if len(key_crules) > 1:
                    raise OverlappingPathsError(
                        f"The key {key!r} matches more than one regex: "
                        f"{', '.join(r.get_item_component(key_depth) or '?' for r in key_crules)}"
                    )
                key_crule = key_crules[0] if key_crules else None

                if key not in right_dict:
                    # Keys only in left dict: apply special rule, else the rule matching the key, else field rule
                    key_crule = left_only_crule or key_crule or field_crule
                    if key_crule.strategy != "ignore":
                        yield ComdabReport(
                            level=key_crule.strategy,
                            path=field_path.left_only,
                            left={key: left_dict[key]},
                            right={},
                        )

                elif key not in left_dict:
                    # Keys only in right dict: apply special rule, else the rule matching the key, else field rule
                    key_crule = right_only_crule or key_crule or field_crule
                    if key_crule.strategy != "ignore":
                        yield ComdabReport(
                            level=key_crule.strategy,
                            path=field_path.right_only,
                            left={},
                            right={key: right_dict[key]},
                        )

                else:
                    # Key in both dicts: compare, using the matching rule, else field rule
                    yield from self._compare(
                        left_dict[key],
                        right_dict[key],
                        path=field_path[key],
                        crule=key_crule or field_crule,
                        prules=key_prules,
                    )


def _regex_applies(pattern: str | None, key: str) -> bool:
    if not pattern:
        return False
    return re.fullmatch(pattern, key) is not None

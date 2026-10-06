from collections.abc import Callable
from typing import cast

from sqlalchemy import ColumnElement, and_, func, not_, or_, select

from vexicon import orm
from vexicon.client.errors import InvalidFilterError
from vexicon.models.base import Filter

type Scalar = str | int | float | bool
type ValueTest = Callable[[ColumnElement[object]], ColumnElement[bool]]


def json_type_names(sample: Scalar) -> list[str]:
    """Returns the json_each type names that a value of sample's type is stored under."""
    if isinstance(sample, bool):
        return ["true", "false"]
    if isinstance(sample, int | float):
        return ["integer", "real"]
    return ["text"]


def fits_sixty_four_bits(value: Scalar) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return True
    return -(2**63) <= value < 2**63


def scalar(key: str, operator: str, value: object) -> Scalar:
    if not isinstance(value, str | int | float | bool):
        raise InvalidFilterError(f"{operator} on {key!r} needs a scalar")
    if not fits_sixty_four_bits(value):
        raise InvalidFilterError(f"{operator} on {key!r} needs a 64-bit integer")
    return value


def scalar_list(key: str, operator: str, value: object) -> list[Scalar]:
    if not isinstance(value, list) or not value:
        raise InvalidFilterError(f"{operator} on {key!r} needs a non-empty list")
    values = [scalar(key, operator, item) for item in cast("list[object]", value)]
    if len({tuple(json_type_names(item)) for item in values}) != 1:
        raise InvalidFilterError(f"{operator} on {key!r} needs values of one type")
    return values


def has_entry(key: str, sample: Scalar, test: ValueTest) -> ColumnElement[bool]:
    """Condition that the metadata has key with a value of sample's type that passes test."""
    entry = func.json_each(orm.Document.meta).table_valued("key", "value", "type")
    return (
        select(entry.c.value)
        .where(
            entry.c.key == key,
            entry.c.type.in_(json_type_names(sample)),
            test(entry.c.value),
        )
        .correlate(orm.Document)
        .exists()
    )


def metadata_condition(key: str, operator: str, value: object) -> ColumnElement[bool]:
    if operator in {"$in", "$nin"}:
        values = scalar_list(key, operator, value)
        member = has_entry(key, values[0], lambda stored: stored.in_(values))
        return member if operator == "$in" else not_(member)
    operand = scalar(key, operator, value)
    if operator in {"$gt", "$gte", "$lt", "$lte"} and isinstance(operand, bool | str):
        raise InvalidFilterError(f"{operator} on {key!r} needs a number")
    match operator:
        case "$eq":
            return has_entry(key, operand, lambda stored: stored == operand)
        case "$ne":
            return not_(has_entry(key, operand, lambda stored: stored == operand))
        case "$gt":
            return has_entry(key, operand, lambda stored: stored > operand)
        case "$gte":
            return has_entry(key, operand, lambda stored: stored >= operand)
        case "$lt":
            return has_entry(key, operand, lambda stored: stored < operand)
        case "$lte":
            return has_entry(key, operand, lambda stored: stored <= operand)
        case _:
            raise InvalidFilterError(f"Unsupported metadata operator {operator!r}")


def logical_branches(key: str, value: object) -> list[object]:
    if not isinstance(value, list):
        raise InvalidFilterError(f"{key} needs a list of filters")
    branches = cast("list[object]", value)
    if len(branches) < 2:
        raise InvalidFilterError(f"{key} needs at least two filters")
    return branches


def where_condition(where: Filter) -> ColumnElement[bool]:
    """Translates a Chroma where filter into a condition over the metadata column."""
    if len(where) != 1:
        raise InvalidFilterError("A where filter holds exactly one key")
    key, value = next(iter(where.items()))
    if key in {"$and", "$or"}:
        branches = [
            where_condition(cast("Filter", branch))
            for branch in logical_branches(key, value)
        ]
        return and_(*branches) if key == "$and" else or_(*branches)
    match value:
        case dict():
            operators = cast("Filter", value)
            if len(operators) != 1:
                raise InvalidFilterError(
                    f"Operator dict on {key!r} holds exactly one operator"
                )
            operator, operand = next(iter(operators.items()))
            return metadata_condition(key, operator, operand)
        case _:
            return metadata_condition(key, "$eq", value)


def where_document_condition(where_document: Filter) -> ColumnElement[bool]:
    """Translates a Chroma where_document filter into a condition over the document column."""
    if len(where_document) != 1:
        raise InvalidFilterError("A where_document filter holds exactly one key")
    key, value = next(iter(where_document.items()))
    if key in {"$and", "$or"}:
        branches = [
            where_document_condition(cast("Filter", branch))
            for branch in logical_branches(key, value)
        ]
        return and_(*branches) if key == "$and" else or_(*branches)
    if not isinstance(value, str) or not value:
        raise InvalidFilterError(f"{key} needs a non-empty string")
    contains = func.instr(orm.Document.document, value) > 0
    match key:
        case "$contains":
            return contains
        case "$not_contains":
            return not_(contains)
        case _:
            raise InvalidFilterError(f"Unsupported document operator {key!r}")

# Builder functions for creating filter expressions
from typing import Any, List, Optional

from dynafield.expressions.types import ColumnFilter, FilterExpression, FilterOperator, LogicalFilter, LogicalOperator


def exp_col(column: str) -> "ColumnFilterBuilder":
    """Start building a column filter"""
    return ColumnFilterBuilder(column)


def exp_and_(*conditions: FilterExpression) -> LogicalFilter:
    """Create AND filter"""
    return LogicalFilter(operator=LogicalOperator.AND, conditions=List(conditions))


def exp_or_(*conditions: FilterExpression) -> LogicalFilter:
    """Create OR filter"""
    return LogicalFilter(operator=LogicalOperator.OR, conditions=List(conditions))


class ColumnFilterBuilder:
    """Fluid interface for building column filters"""

    def __init__(self, column: str):
        self.column = column
        self.json_path: Optional[str] = None

    def json(self, path: str) -> "ColumnFilterBuilder":
        """Specify JSON path for JSONB columns (supports nested paths)"""
        self.json_path = path
        return self

    def eq(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.EQ, value=value, json_path=self.json_path)

    def ne(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.NE, value=value, json_path=self.json_path)

    def gt(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.GT, value=value, json_path=self.json_path)

    def lt(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.LT, value=value, json_path=self.json_path)

    def ge(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.GE, value=value, json_path=self.json_path)

    def le(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.LE, value=value, json_path=self.json_path)

    def contains(self, value: Any) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.CONTAINS, value=value, json_path=self.json_path)

    def in_(self, values: List[Any]) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.IN, value=values, json_path=self.json_path)

    def is_null(self) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.IS_NULL, value=None, json_path=self.json_path)

    def is_not_null(self) -> ColumnFilter:
        return ColumnFilter(column=self.column, operator=FilterOperator.IS_NOT_NULL, value=None, json_path=self.json_path)

    # List operations
    def any_in(self, values: List[Any]) -> ColumnFilter:
        """Any value in the query list exists in the database list"""
        return ColumnFilter(column=self.column, operator=FilterOperator.ANY_IN, value=values, json_path=self.json_path)

    def all_in(self, values: List[Any]) -> ColumnFilter:
        """All values in the query list exist in the database list"""
        return ColumnFilter(column=self.column, operator=FilterOperator.ALL_IN, value=values, json_path=self.json_path)

    def none_in(self, values: List[Any]) -> ColumnFilter:
        """No values in the query list exist in the database list"""
        return ColumnFilter(column=self.column, operator=FilterOperator.NONE_IN, value=values, json_path=self.json_path)

    def list_overlap(self, values: List[Any]) -> ColumnFilter:
        """Database list has any overlap with query list (same as ANY_IN)"""
        return ColumnFilter(column=self.column, operator=FilterOperator.LIST_OVERLAP, value=values, json_path=self.json_path)

    def list_contains(self, values: List[Any]) -> ColumnFilter:
        """Database list contains all query values"""
        return ColumnFilter(column=self.column, operator=FilterOperator.LIST_CONTAINS, value=values, json_path=self.json_path)

    def has_key(self, key: str) -> ColumnFilter:
        """JSONB column has the specified key"""
        return ColumnFilter(column=self.column, operator=FilterOperator.HAS_KEY, value=key, json_path=self.json_path)

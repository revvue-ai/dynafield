# polars_filter_builder.py
from datetime import date, datetime
from typing import Any

import polars as pl

from dynafield.expressions.types import ColumnFilter, FilterOperator, LogicalFilter, LogicalOperator


class PolarsFilterBuilder:
    """Converts filter expressions to Polars expressions"""

    def build_column_filter(self, filter: ColumnFilter) -> pl.Expr:
        """Build Polars expression for a single column filter"""
        if filter.json_path:
            # For JSON columns, we'd need to extract the field
            col_ref = self._build_json_col_reference(filter)
        else:
            col_ref = pl.col(filter.column)

        # Handle list operations
        if filter.operator in [FilterOperator.ANY_IN, FilterOperator.LIST_OVERLAP]:
            return self._build_list_operation(col_ref, filter.value, "any")
        elif filter.operator == FilterOperator.ALL_IN:
            return self._build_list_operation(col_ref, filter.value, "all")
        elif filter.operator == FilterOperator.NONE_IN:
            return ~self._build_list_operation(col_ref, filter.value, "any")
        elif filter.operator == FilterOperator.LIST_CONTAINS:
            return self._build_list_contains(filter.value, col_ref)

        return self._get_polars_expression(col_ref, filter.operator, filter.value)

    def build_logical_filter(self, filter: LogicalFilter) -> pl.Expr:
        """Build Polars expression for logical AND/OR filters"""
        expressions = [condition.to_polars() for condition in filter.conditions]

        if filter.operator == LogicalOperator.AND:
            # Combine all expressions with AND
            result = expressions[0]
            for expr in expressions[1:]:
                result = result & expr
            return result
        else:  # OR
            result = expressions[0]
            for expr in expressions[1:]:
                result = result | expr
            return result

    def _build_json_col_reference(self, filter: ColumnFilter) -> pl.Expr:
        """Build Polars reference for JSON columns"""
        if not filter.json_path:
            return pl.col(filter.column)

        # This assumes your JSON columns are properly structured as structs
        path_parts = filter.json_path.split(".")
        col_ref = pl.col(filter.column)

        for part in path_parts:
            col_ref = col_ref.struct.field(part)

        return col_ref

    def _build_list_operation(self, col_ref: pl.Expr, value: Any, operation: str) -> pl.Expr:
        """Build list operations with proper type handling"""
        if value is None:
            raise ValueError("Cannot perform list operation with None value")

        # Convert value to proper collection type for Polars
        processed_value = self._process_value_for_polars(value)

        if operation == "any":
            return col_ref.list.eval(pl.element().is_in(processed_value)).list.any()
        else:  # "all"
            return col_ref.list.eval(pl.element().is_in(processed_value)).list.all()

    def _build_list_contains(self, value: Any, col_ref: pl.Expr) -> pl.Expr:
        """Build LIST_CONTAINS operation"""
        if value is None:
            raise ValueError("Cannot perform LIST_CONTAINS with None value")

        processed_value = self._process_value_for_polars(value)
        return pl.lit(processed_value).list.eval(pl.element().is_in(col_ref)).list.all()

    def _process_value_for_polars(self, value: Any) -> Any:
        """Convert value to Polars-compatible type"""
        if value is None:
            return None
        elif isinstance(value, (list, tuple)):
            return value
        elif isinstance(value, (str, int, float, bool, date, datetime)):
            return [value]
        else:
            # For other types, try to convert to list
            try:
                return list(value) if hasattr(value, "__iter__") and not isinstance(value, (str, dict)) else [value]
            except TypeError:
                return [value]

    def _get_polars_expression(self, col_ref: pl.Expr, operator: FilterOperator, value: Any) -> pl.Expr:
        """Map FilterOperator to Polars expression"""
        # Process value for Polars compatibility
        processed_value = self._process_value_for_operator(operator, value)

        mapping = {
            FilterOperator.EQ: col_ref.eq(processed_value),
            FilterOperator.NE: col_ref.ne(processed_value),
            FilterOperator.GT: col_ref.gt(processed_value),
            FilterOperator.LT: col_ref.lt(processed_value),
            FilterOperator.GE: col_ref.ge(processed_value),
            FilterOperator.LE: col_ref.le(processed_value),
            FilterOperator.CONTAINS: col_ref.str.contains(str(processed_value)),
            FilterOperator.NOT_CONTAINS: ~col_ref.str.contains(str(processed_value)),
            FilterOperator.STARTS_WITH: col_ref.str.starts_with(str(processed_value)),
            FilterOperator.ENDS_WITH: col_ref.str.ends_with(str(processed_value)),
            FilterOperator.IN: col_ref.is_in(processed_value),
            FilterOperator.NOT_IN: ~col_ref.is_in(processed_value),
            FilterOperator.IS_NULL: col_ref.is_null(),
            FilterOperator.IS_NOT_NULL: col_ref.is_not_null(),
            FilterOperator.HAS_KEY: col_ref.struct.field(str(processed_value)).is_not_null(),  # Approximation
        }

        if operator in mapping:
            return mapping[operator]

        raise ValueError(f"Unsupported operator for Polars: {operator}")

    def _process_value_for_operator(self, operator: FilterOperator, value: Any) -> Any:
        """Process value based on the operator requirements"""
        if value is None:
            return None

        if operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
            return self._process_value_for_polars(value)
        elif operator in [
            FilterOperator.CONTAINS,
            FilterOperator.NOT_CONTAINS,
            FilterOperator.STARTS_WITH,
            FilterOperator.ENDS_WITH,
        ]:
            return str(value)
        else:
            return value

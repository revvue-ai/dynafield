# sql_filter_builder.py
from typing import Any, List, Tuple

from dynafield.expressions.types import ColumnFilter, FilterExpression, FilterOperator, LogicalFilter, LogicalOperator


class SQLFilterBuilder:
    """Converts filter expressions to SQL with enhanced JSONB and list support"""

    def build(self, expression: FilterExpression) -> Tuple[str, List[Any]]:
        """
        Main entry point to build SQL from any filter expression.
        Returns a tuple of (SQL_where_clause, parameters_list)
        """
        if isinstance(expression, ColumnFilter):
            return self.build_column_filter(expression)
        elif isinstance(expression, LogicalFilter):
            return self.build_logical_filter(expression)
        else:
            raise ValueError(f"Unsupported expression type: {type(expression)}")

    def build_column_filter(self, filter: ColumnFilter) -> Tuple[str, List[Any]]:
        """Build SQL for a single column filter with enhanced JSONB support"""
        params: List[Any] = []

        # Build column reference (regular column or JSONB path)
        column_ref = self._build_column_reference(filter)

        # Handle special list operations
        if filter.operator in [
            FilterOperator.ANY_IN,
            FilterOperator.ALL_IN,
            FilterOperator.NONE_IN,
            FilterOperator.LIST_OVERLAP,
            FilterOperator.LIST_CONTAINS,
        ]:
            sql, param_value = self._build_list_operation(filter, column_ref)
        else:
            sql, param_value = self._get_sql_operator(filter.operator, filter.value, column_ref)

        if param_value is not None:
            if isinstance(param_value, (list, tuple)):
                params.extend(param_value)
            else:
                params.append(param_value)

        return sql, params

    def build_logical_filter(self, filter: LogicalFilter) -> Tuple[str, List[Any]]:
        """Build SQL for logical AND/OR filters"""
        all_params: List[Any] = []
        condition_sqls: List[str] = []

        for condition in filter.conditions:
            sql, params = self.build(condition)  # Recursively build each condition
            condition_sqls.append(f"({sql})")
            all_params.extend(params)

        operator = " AND " if filter.operator == LogicalOperator.AND else " OR "
        sql = operator.join(condition_sqls)

        return sql, all_params

    def _build_column_reference(self, filter: ColumnFilter) -> str:
        """Build the appropriate column reference for SQL"""
        if not filter.json_path:
            return filter.column

        # Handle nested JSON paths like 'user.address.city'
        path_parts = filter.json_path.split(".")

        if len(path_parts) == 1:
            # Simple path: column->>'field'
            return f"{filter.column} ->> '{path_parts[0]}'"
        else:
            # Nested path: use #> operator for path navigation
            json_path = ",".join(path_parts)
            return f"{filter.column} #> '{{{json_path}}}'"

    def _build_list_operation(self, filter: ColumnFilter, column_ref: str) -> Tuple[str, Any]:
        """Build SQL for list-to-list operations"""
        if not isinstance(filter.value, list):
            raise ValueError(f"List operations require list value, got {type(filter.value)}")

        mapping = {
            FilterOperator.ANY_IN: (f"{column_ref} && %s::text[]", filter.value),
            FilterOperator.ALL_IN: (f"{column_ref} @> %s::text[]", filter.value),
            FilterOperator.NONE_IN: (f"NOT ({column_ref} && %s::text[])", filter.value),
            FilterOperator.LIST_OVERLAP: (f"{column_ref} && %s::text[]", filter.value),
            FilterOperator.LIST_CONTAINS: (f"{column_ref} @> %s::text[]", filter.value),
        }

        if filter.operator not in mapping:
            raise ValueError(f"Unsupported list operator: {filter.operator}")

        return mapping[filter.operator]

    def _get_sql_operator(self, operator: FilterOperator, value: Any, column_ref: str) -> Tuple[str, Any]:
        """Map FilterOperator to SQL operator with enhanced JSON support"""
        mapping = {
            FilterOperator.EQ: (f"{column_ref} = %s", value),
            FilterOperator.NE: (f"{column_ref} != %s", value),
            FilterOperator.GT: (f"{column_ref} > %s", value),
            FilterOperator.LT: (f"{column_ref} < %s", value),
            FilterOperator.GE: (f"{column_ref} >= %s", value),
            FilterOperator.LE: (f"{column_ref} <= %s", value),
            FilterOperator.CONTAINS: (f"{column_ref} LIKE %s", f"%{value}%" if value else None),
            FilterOperator.NOT_CONTAINS: (f"{column_ref} NOT LIKE %s", f"%{value}%" if value else None),
            FilterOperator.STARTS_WITH: (f"{column_ref} LIKE %s", f"{value}%" if value else None),
            FilterOperator.ENDS_WITH: (f"{column_ref} LIKE %s", f"%{value}" if value else None),
            FilterOperator.ILIKE: (f"{column_ref} ILIKE %s", value),
            FilterOperator.NOT_ILIKE: (f"{column_ref} NOT ILIKE %s", value),
            FilterOperator.IN: (f"{column_ref} IN %s", tuple(value) if value else None),
            FilterOperator.NOT_IN: (f"{column_ref} NOT IN %s", tuple(value) if value else None),
            FilterOperator.IS_NULL: (f"{column_ref} IS NULL", None),
            FilterOperator.IS_NOT_NULL: (f"{column_ref} IS NOT NULL", None),
            FilterOperator.HAS_KEY: (f"{column_ref} ? %s", value),
        }

        if operator in mapping:
            return mapping[operator]

        raise ValueError(f"Unsupported operator for SQL: {operator}")

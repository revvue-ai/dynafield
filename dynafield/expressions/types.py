from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import polars as pl
from pydantic import BaseModel, Field


class FilterOperator(Enum):
    EQ = "EQ"
    NE = "NE"
    GT = "GT"
    LT = "LT"
    GE = "GE"
    LE = "LE"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    ILIKE = "ILIKE"
    NOT_ILIKE = "NOT_ILIKE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"
    HAS_KEY = "HAS_KEY"
    # List-specific operators
    ANY_IN = "ANY_IN"
    ALL_IN = "ALL_IN"
    NONE_IN = "NONE_IN"
    LIST_CONTAINS = "LIST_CONTAINS"
    LIST_OVERLAP = "LIST_OVERLAP"


class LogicalOperator(Enum):
    AND = "AND"
    OR = "OR"


class BaseFilterExpression(BaseModel):
    """Base class for all filter expressions"""

    def to_sql(self) -> Tuple[str, List[Any]]:
        raise NotImplementedError("Subclasses must implement to_sql()")

    def to_polars(self) -> pl.Expr:
        raise NotImplementedError("Subclasses must implement to_polars()")

    class Config:
        use_enum_values = False


class ColumnFilter(BaseFilterExpression):
    """Represents a single column filter condition"""

    column: str
    operator: FilterOperator
    value: Optional[Union[str, int, float, bool, Dict[str, Any], List[Any], date, datetime]] = None
    json_path: Optional[str] = Field(None, description="For JSONB columns - supports nested paths like 'user.address.city'")

    def to_sql(self) -> Tuple[str, List[Any]]:
        """Convert to SQL expression"""
        from dynafield.expressions.sql_filter_builder import SQLFilterBuilder

        builder = SQLFilterBuilder()
        result = builder.build_column_filter(self)
        return result

    def to_polars(self) -> pl.Expr:
        """Convert to Polars expression"""
        from dynafield.expressions.polars_filter_builder import PolarsFilterBuilder

        builder = PolarsFilterBuilder()
        result = builder.build_column_filter(self)
        return result


class LogicalFilter(BaseFilterExpression):
    """Represents a logical combination of filters (AND/OR)"""

    operator: LogicalOperator
    conditions: List["FilterExpression"]

    def to_sql(self) -> Tuple[str, List[Any]]:
        from dynafield.expressions.sql_filter_builder import SQLFilterBuilder

        builder = SQLFilterBuilder()
        result = builder.build_logical_filter(self)
        return result

    def to_polars(self) -> pl.Expr:
        from dynafield.expressions.polars_filter_builder import PolarsFilterBuilder

        builder = PolarsFilterBuilder()
        result = builder.build_logical_filter(self)
        return result


FilterExpression = Union[ColumnFilter, LogicalFilter]

LogicalFilter.model_rebuild()

from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select, func

from ..expressions.types import FilterExpression
from ..logger.logger_config import get_logger

log = get_logger(__name__)

T = TypeVar("T")


async def search_models(
    session: AsyncSession,
    model: Type[T],
    filters: Optional[FilterExpression] = None,
    count_only: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    get_first: bool = False,
) -> Tuple[List[T], int]:
    """
    Search for models in the database using the new filter system.
    """
    from app.utils.expressions.sql_filter_builder import SQLFilterBuilder

    stmt: Select[Any] = select(model)
    execution_params: Dict[str, Any] = {}

    if filters is not None:
        sql_builder = SQLFilterBuilder()
        where_clause, params = sql_builder.build(filters)

        if where_clause:
            validate_parameters(where_clause, params)

            # FIX FOR IN CLAUSE: Convert single-value IN to equality
            if " IN %s" in where_clause and params:
                in_value = params[0]

                if isinstance(in_value, (list, tuple)):
                    if len(in_value) == 0:
                        log.debug("Empty IN list - returning empty results")
                        return [], 0
                    elif len(in_value) == 1:
                        formatted_where = where_clause.replace(" IN %s", " = :param_0")
                        execution_params["param_0"] = in_value[0]
                        log.debug(f"Converted single-value IN to equality: {formatted_where}")
                    else:
                        placeholders = ", ".join([f":param_{i}" for i in range(len(in_value))])
                        formatted_where = where_clause.replace(" IN %s", f" IN ({placeholders})")
                        for i, value in enumerate(in_value):
                            execution_params[f"param_{i}"] = value
                        log.debug(f"Multi-value IN clause: {formatted_where}")
                else:
                    formatted_where = where_clause.replace(" IN %s", " = :param_0")
                    execution_params["param_0"] = in_value
                    log.debug(f"Converted single-value IN to equality: {formatted_where}")

            else:
                formatted_where = where_clause
                for i, param in enumerate(params):
                    formatted_where = formatted_where.replace("%s", f":param_{i}", 1)
                    execution_params[f"param_{i}"] = param

            stmt = stmt.where(text(formatted_where))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await session.execute(count_stmt, execution_params)
    count = count_result.scalar() or 0

    if count_only:
        return [], count

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    if get_first:
        stmt = stmt.limit(1)

    result = await session.scalars(stmt, execution_params)
    models = list(result.all())
    return models, count


def validate_parameters(where_clause: str, params: List[Any]) -> None:
    """Validate that parameters make sense for the SQL"""
    placeholder_count = where_clause.count("%s")

    if placeholder_count != len(params):
        log.debug(f"Parameter count mismatch: {placeholder_count} placeholders, {len(params)} parameters")

    if any(pattern in where_clause.upper() for pattern in ["DROP ", "DELETE ", "UPDATE ", "INSERT "]):
        raise ValueError("Potential SQL injection detected")

    if (" IS NULL" in where_clause.upper() or " IS NOT NULL" in where_clause.upper()) and params:
        log.debug("NULL operations should not have parameters")

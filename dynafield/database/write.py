from typing import List, Optional, Tuple, Type

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel

from dynafield.logger.logger_config import get_logger
from dynafield.tracing import get_tracer

log = get_logger(__name__)
tracer = get_tracer(__name__)


async def get_data_to_add_and_update[T: SQLModel](
    session: AsyncSession, tenant_id: str, data: List[T], primary_key: str = "id"
) -> Tuple[List[T], List[T], List[T]]:
    """Get lists of items to add, update, and existing items.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        data: List of items to process
        primary_key: Name of the primary key attribute

    Returns:
        Tuple of (items_to_add, items_to_update, existing_items)
    """
    if not data:
        log.debug("No data provided for processing.")
        return [], [], []
    model_name = data[0].__class__.__name__ if data else "Unknown"
    with tracer.start_as_current_span(f"Add{model_name}"):
        log.debug(f"Adding or updating {model_name} on tenant {tenant_id}.")

        data_ids = [getattr(doc, primary_key) for doc in data]
        stmt = select(data[0].__class__).where(getattr(data[0].__class__, primary_key).in_(data_ids))

        # Execute query and extract model instances from rows
        execution = await session.execute(stmt)
        existing_data = [row[0] for row in execution.all()]

        existing_ids = {getattr(doc, primary_key) for doc in existing_data}

        to_add = [doc for doc in data if getattr(doc, primary_key) not in existing_ids]
        to_update = [doc for doc in data if getattr(doc, primary_key) in existing_ids]

        return to_add, to_update, existing_data


async def add_table_data[T: SQLModel](session: AsyncSession, tableData: List[T] | None) -> None:
    if not tableData:
        return
    session.add_all(tableData)


async def update_table_data[T: SQLModel](
    session: AsyncSession,
    table: Type[T],
    table_data: Optional[List[T]] = None,
    primary_key: str = "id",  # Default to 'id', can be overridden
) -> None:
    """
    Batch updates table data using SQLAlchemy Core for maximum performance.

    Args:
        primary_key: Explicitly specify the primary key column name
        session: Database session
        table: SQLModel table class
        table_data: List of data to update
    """
    if not table_data:
        return

    update_dicts = []
    for item in table_data:
        if isinstance(item, SQLModel):
            data = item.model_dump(exclude_unset=True)
        else:
            data = dict(item)

        if primary_key not in data:
            raise ValueError(f"Primary key '{primary_key}' missing in update data: {data}")
        update_dicts.append(data)

    stmt = update(table)
    await session.execute(stmt, update_dicts)

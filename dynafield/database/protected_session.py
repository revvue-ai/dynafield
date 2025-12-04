import asyncio
import re
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from dynafield import config, tracing
from dynafield.base_model import custom_json_deserializer, custom_json_serializer
from dynafield.database.connection import conn_string
from dynafield.logger.logger_config import get_logger

log = get_logger(__name__)


_engines: dict[str, AsyncEngine] = {}
_session_makers: dict[str, async_sessionmaker[AsyncSession]] = {}
_engine_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _validate_identifier(identifier: str, identifier_type: str) -> str:
    """Validate and sanitize identifiers for use in SQL"""
    if not identifier:
        raise ValueError(f"{identifier_type} cannot be empty")

    # Allow alphanumeric, underscores, and hyphens (common in UUIDs and slugs)
    if not re.match(r"^[a-zA-Z0-9_\-]+$", identifier):
        raise ValueError(f"Invalid {identifier_type}: {identifier}. Only alphanumeric, underscore, and hyphen characters are allowed.")

    # Additional length checks if needed
    if len(identifier) > 128:
        raise ValueError(f"{identifier_type} too long: {identifier}")

    return identifier


async def get_engine_for_tenant(tenant_db_id: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Get or create engine and session maker for specific tenant database with connection pooling"""

    if tenant_db_id not in _engines:
        async with _engine_locks[tenant_db_id]:
            if tenant_db_id not in _engines:
                engine = create_async_engine(
                    conn_string(role="crud", db=tenant_db_id, mode="async"),
                    poolclass=NullPool,
                    json_serializer=custom_json_serializer,
                    json_deserializer=custom_json_deserializer,
                    **{
                        "echo": False,
                        "future": True,
                        "connect_args": {
                            "command_timeout": 60,
                            "statement_cache_size": 0,
                            "server_settings": {"application_name": "my_app"},
                        },
                    },
                )

                session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

                _engines[tenant_db_id] = engine
                _session_makers[tenant_db_id] = session_maker

    return _engines[tenant_db_id], _session_makers[tenant_db_id]


async def a_create_session(tenant_db_id: str, tenant_id: str) -> AsyncSession:
    """Create a new async session with RLS context set"""
    engine, session_maker = await get_engine_for_tenant(tenant_db_id)
    session = session_maker()
    await _set_rls_context(session, tenant_id)
    return session


async def _set_rls_context(session: AsyncSession, tenant_id: str, user_id: str | None = None) -> None:
    """Set RLS context using properly formatted SQL for SET commands"""
    try:
        sanitized_tenant_id = _validate_identifier(tenant_id, "tenant_id")
        await session.execute(text(f"SET LOCAL app.tenant_id = '{sanitized_tenant_id}'"))
        log.debug("Set RLS context", extra={"tenant_id": tenant_id})

    except Exception as e:
        log.error("Failed to set RLS context", extra={"error": str(e), "tenant_id": tenant_id, "user_id": user_id})
        raise


@asynccontextmanager
async def a_session_scope(
    tenant_id: str,
    tenant_db_id: str,
    mode: Literal["read", "write"] = "read",
) -> AsyncGenerator[AsyncSession, None]:
    if mode not in ("read", "write"):
        raise ValueError("mode must be 'read' or 'write'")

    # TODO: Maybe validation/sanitization shall be done when building the "usermodel" in assert.
    _validate_identifier(tenant_id, "tenant_id")
    _validate_identifier(tenant_db_id, "tenant_db_id")

    with tracing.get_tracer().start_as_current_span(f"Session{mode.capitalize()}"):
        session = await a_create_session(tenant_db_id=tenant_db_id, tenant_id=tenant_id)
        try:
            if mode == "read":
                await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session
            if mode == "write":
                with tracing.get_tracer().start_as_current_span("SessionCommit"):
                    await session.commit()
        except Exception:
            if getattr(session, "get_transaction", None) and session.get_transaction():
                with tracing.get_tracer().start_as_current_span("SessionRollback"):
                    await session.rollback()
            log.exception(
                "DB error",
                extra={"tenant_id": tenant_id, "tenant_db_id": tenant_db_id, "mode": mode},
            )
            raise
        finally:
            with tracing.get_tracer().start_as_current_span("SessionClose"):
                await session.close()


async def check_database_health(tenant_db_id: str | None = None) -> dict[str, bool]:
    """Check health of one or all databases"""
    health_status: dict[str, bool] = {}

    databases_to_check = [tenant_db_id] if tenant_db_id else list(_engines.keys())

    for db_id in databases_to_check:
        if db_id not in _engines:
            health_status[db_id] = False
            continue

        try:
            engine = _engines[db_id]
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            health_status[db_id] = True
        except Exception as e:
            log.error(f"Health check failed for {db_id}: {e}")
            health_status[db_id] = False

    return health_status


async def close_all_connections() -> None:
    """Close all database connections - use during application shutdown"""
    for db_id, engine in _engines.items():
        try:
            await engine.dispose()
            log.info(f"Closed connections for database: {db_id}")
        except Exception as e:
            log.error(f"Error closing connections for {db_id}: {e}")

    _engines.clear()
    _session_makers.clear()


async def db_readiness() -> bool:
    try:
        async with a_session_scope(tenant_id=config.DEFAULT_TENANT_ID, tenant_db_id=config.DEFAULT_TENANT_DATABASE_ID) as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            return row.test == 1 if row and row.test else False
    except Exception as e:
        log.error("Failed database readiness", extra={"error": str(e)})
        return False

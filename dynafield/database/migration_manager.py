import os
from pathlib import Path
from typing import Optional

import sqlalchemy
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

from dynafield.logger.logger_config import get_logger

log = get_logger(__name__)


class MigrationManager:
    def __init__(self, db_url: str, schema: str, alembic_dir: str) -> None:
        self.db_url = db_url
        self.schema = schema
        self.alembic_dir = alembic_dir

        base_dir = Path(__file__).parent.parent.parent.parent
        if alembic_dir is not None:
            alembic_dir_path = Path(alembic_dir).resolve()
        else:
            alembic_dir_path = base_dir / "alembic"
        log.debug(f"Using alembic directory: {alembic_dir_path}")

        # Setup Alembic
        self.alembic_cfg = Config()
        self.alembic_cfg.set_main_option("script_location", str(alembic_dir_path))
        self.alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        self.alembic_cfg.set_main_option("version_locations", str(alembic_dir_path / "versions"))
        self.alembic_cfg.set_main_option("database.schema", schema)

        os.environ["ALEMBIC_BASE_PATH"] = str(base_dir)

        log.debug(f"MigrationManager initialized with DB URL: {db_url} and schema: {schema}")

    def _get_db_name(self) -> str:
        """Extract database name from URL"""
        try:
            return self.db_url.split("/")[-1]
        except Exception:
            return "unknown"

    def ensure_database(self) -> None:
        """Create database if it doesn't exist"""
        try:
            db_name = self._get_db_name()

            # Connect to postgres database to create our target DB
            admin_url = self.db_url.rsplit("/", 1)[0] + "/postgres"
            engine = sqlalchemy.create_engine(admin_url, isolation_level="AUTOCOMMIT")

            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name})

                if not result.fetchone():
                    log.debug(f"Creating database: {db_name}")
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    log.debug(f"Database '{db_name}' created")

        except Exception as e:
            log.warning(f"Database creation skipped: {e}")

    def ensure_schema(self) -> None:
        """Create schema if it doesn't exist"""
        try:
            engine = sqlalchemy.create_engine(self.db_url)
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"'))
                log.debug(f"Schema '{self.schema}' ready")
        except Exception as e:
            log.warning(f"Schema creation skipped: {e}")

    def run_migrations(self) -> None:
        """Run all migrations safely"""
        log.info("Starting database migrations...")
        engine: Optional[Engine] = None
        try:
            engine = sqlalchemy.create_engine(
                self.db_url,
                isolation_level="AUTOCOMMIT",
                connect_args={"connect_timeout": 10, "application_name": "migration_manager"},
                pool_recycle=300,
                pool_pre_ping=True,
            )
            with engine.connect() as _conn:
                log.debug("✓ Connected to PostgreSQL!")
            # Explicitly dispose the engine
            if engine:
                engine.dispose()
            log.debug("✓ Connection closed properly")
        except Exception as e:
            log.error(f"✗ Connection to database failed: {e}")
            if engine:
                engine.dispose()
            raise

        # Ensure database and schema exist
        self.ensure_database()
        self.ensure_schema()

        # Apply migrations
        try:
            command.upgrade(self.alembic_cfg, "head")
            log.info("✓ Migrations completed successfully")
        except Exception as e:
            log.error(f"Migration failed: {e}")
            raise

    def is_schema_initialized(self) -> bool:
        """Check if migrations have been run"""
        try:
            engine = sqlalchemy.create_engine(self.db_url)
            with engine.connect() as conn:
                # Check if alembic_version table exists
                result = conn.execute(
                    text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = :schema 
                        AND table_name = 'alembic_version'
                    )
                """),
                    {"schema": self.schema},
                )
                return bool(result.scalar())
        except Exception:
            return False

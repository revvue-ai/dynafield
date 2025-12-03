from dataclasses import dataclass
from typing import Literal

from dynafield import config

DBUserRole = Literal["migration", "crud"]
DBConnMode = Literal["sync", "async"]
DBDriver = Literal["asyncpg", "psycopg"]


@dataclass
class DBUserCredentials:
    user: str
    password: str


def get_db_credentials(role: DBUserRole) -> DBUserCredentials:
    creds: dict[DBUserRole, DBUserCredentials] = {
        "migration": DBUserCredentials(user=config.DATABASE_TABLE_OWNER_USER, password=config.DATABASE_TABLE_OWNER_PASSWORD),
        "crud": DBUserCredentials(user=config.DATABASE_SCHEMA_USER, password=config.DATABASE_SCHEMA_USER_PASSWORD),
    }
    return creds[role]


def conn_string(*, role: DBUserRole = "crud", db: str = config.DEFAULT_TENANT_DATABASE_ID, mode: DBConnMode = "sync") -> str:
    host = config.DATABASE_HOST
    port = config.DATABASE_PORT
    creds = get_db_credentials(role)

    match mode:
        case "async":
            return f"postgresql+asyncpg://{creds.user}:{creds.password}@{host}:{port}/{db}"
        case "sync":
            return f"postgresql+psycopg://{creds.user}:{creds.password}@{host}:{port}/{db}"
        case _:
            raise ValueError("Unknown mode")

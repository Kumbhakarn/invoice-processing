"""Async SQLAlchemy engine and session management."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True)
class DatabaseResources:
    """Engine and request-safe factory for independent async sessions."""

    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def create_database(database_url: str) -> DatabaseResources:
    """Create database resources without opening a connection immediately."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return DatabaseResources(
        engine=engine,
        sessions=async_sessionmaker(engine, expire_on_commit=False),
    )


async def check_database_connection(engine: AsyncEngine) -> None:
    """Raise a SQLAlchemy error if PostgreSQL cannot answer a simple query."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

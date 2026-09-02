"""Async SQLAlchemy setup for the application database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import Settings
from infrastructure.persistence.models import Base


def get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Create a session factory for the configured SQLite database."""
    engine = create_async_engine(settings.database_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create the initial schema if it does not exist yet.

    The schema is intentionally created at application startup so a fresh local
    checkout is immediately usable. A future production deployment can replace
    this with Alembic migrations without changing repositories.
    """
    bind = session_factory.kw.get("bind")
    if bind is None:
        raise RuntimeError("Database session factory has no engine bind")

    database_url = str(bind.url)
    if database_url.startswith("sqlite") and "///" in database_url:
        Path(database_url.split("///", 1)[1].split("?", 1)[0]).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    async with bind.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Dispose the underlying engine during application shutdown."""
    bind = session_factory.kw.get("bind")
    if bind is not None:
        await bind.dispose()


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session and commit/rollback it as a unit of work."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

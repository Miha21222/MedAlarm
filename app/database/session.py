from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import load_settings
from app.database.migrations import ensure_sqlite_compatibility
from app.database.models import Base

settings = load_settings()
_is_sqlite = settings.database_url.startswith("sqlite+") or settings.database_url.startswith("sqlite:")
engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,
    connect_args={"timeout": 30} if _is_sqlite else {},
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _configure_sqlite(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        if conn.dialect.name == "sqlite":
            # WAL lets the API and bot/scheduler processes read while the other
            # process is writing, substantially reducing transient lock errors.
            await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)
        await ensure_sqlite_compatibility(conn)


@asynccontextmanager
async def session_scope() -> AsyncSession:
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from engine.config import get_settings
from engine.models_sqlalchemy import Base


class DatabaseManager:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def initialize(self, force_sqlite: bool = False) -> None:
        settings = get_settings()
        db_url = settings.database_url
        if force_sqlite or "localhost:5432" in db_url or not db_url:
            db_url = "sqlite+aiosqlite:///./algorise_prod.db"

        if db_url.startswith("sqlite"):
            self._engine = create_async_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
        else:
            self._engine = create_async_engine(
                db_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_timeout=settings.database_pool_timeout,
                pool_pre_ping=True,
                echo=False,
            )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self.initialize()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self.initialize()
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception:
            # If external DATABASE_URL on Render is unreachable, fall back to local SQLite
            self.initialize(force_sqlite=True)
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session() as session:
        yield session


# --- sync engine for analytics and audit recording ---------------------------
#
# The primary session factory is async, and AsyncSession has no .query().
# Analytics reads and audit writes do not belong on the request path, so a
# separate synchronous engine is created against the same database rather
# than forcing async through code that is purely analytical.
#
# This exists because two modules previously did `from engine.database
# import SessionLocal`, which does not exist here. Both wrapped the import
# and the call in try/except, so the failure was silent: the Meta proxy
# appeared to record every operation and recorded nothing at all.

_sync_engine = None


ASYNC_TO_SYNC_DRIVERS = {
    "sqlite+aiosqlite": "sqlite",
    "postgresql+asyncpg": "postgresql+psycopg",
    "mysql+aiomysql": "mysql+pymysql",
}


def _database_url() -> str:
    """The synchronous equivalent of the configured database URL.

    The app is configured with async drivers (sqlite+aiosqlite,
    postgresql+asyncpg) because the request path is async. Passing one of
    those to create_engine() produces an engine that raises MissingGreenlet
    on first connect, so the driver is swapped here rather than at each call
    site.
    """
    from engine.config import get_settings

    url = getattr(get_settings(), "database_url", "") or ""
    if not url or "localhost:5432" in url:
        url = "sqlite+aiosqlite:///./algorise_prod.db"

    for async_drv, sync_drv in ASYNC_TO_SYNC_DRIVERS.items():
        if url.startswith(async_drv + "://"):
            return url.replace(async_drv + "://", sync_drv + "://", 1)
    return url


def sync_engine():
    global _sync_engine
    if _sync_engine is None:
        from sqlalchemy import create_engine

        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _sync_engine = create_engine(url, connect_args=connect_args)
    return _sync_engine


def sync_session():
    """A synchronous Session bound to the same database.

    expire_on_commit is disabled: the default expires every instance on
    commit, and reading an attribute afterwards triggers a lazy refresh,
    which under this engine's async-configured metadata raises
    MissingGreenlet. Analytics code holds rows across a commit.
    """
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=sync_engine(), expire_on_commit=False)()
"""SupplyChain IQ - Database Connection & Session Management."""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings
from backend.app.models.base import Base

# Sync Engine & Session (used for Alembic, scripts, and bulk processing)
engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async Engine & Session (used for FastAPI endpoints)
# Handle sqlite vs postgres dialect for tests vs prod
if "sqlite" in settings.sync_database_url:
    async_engine = None
    AsyncSessionLocal = None
else:
    async_engine = create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Async engine not configured for SQLite.")
    async with AsyncSessionLocal() as session:
        yield session


def init_db(target_engine=None):
    """Create all database tables on target engine."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

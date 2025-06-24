"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from .models.base import Base

# Import all models to ensure they're registered with Base
from .models import User, Project, Execution, ExecutionMessage, ExecutionArtifact

# Create sync engine for Alembic migrations
sync_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Create async engine for application use
async_engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Create SessionLocal class for sync operations (migrations)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    class_=Session
)

# Create AsyncSessionLocal for async operations
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def get_db():
    """
    Dependency to get sync database session.
    Used primarily for migrations.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """
    Dependency to get async database session.
    This is the primary way to interact with the database in the app.
    
    Yields:
        AsyncSession: Async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

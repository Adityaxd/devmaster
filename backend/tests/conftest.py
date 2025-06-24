"""Pytest configuration and fixtures."""

import os
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import uuid

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://devmaster:devmaster@localhost:5433/devmaster_test"
os.environ["DATABASE_SYNC_URL"] = "postgresql://devmaster:devmaster@localhost:5433/devmaster_test"

from app.database import Base
from app.models import User, Project, Execution
from app.config import settings


# Test database URL (using test database)
TEST_DATABASE_URL = "postgresql+asyncpg://devmaster:devmaster@localhost:5433/devmaster_test"
TEST_ASYNC_DATABASE_URL = "postgresql+asyncpg://devmaster:devmaster@localhost:5433/devmaster_test"


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test function."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        poolclass=NullPool,  # Disable pooling for tests
        echo=False
    )
    
    async with engine.begin() as conn:
        # Drop all tables and recreate
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    # Use UUID to ensure unique email and username for each test
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        email=f"test_{unique_id}@example.com",
        username=f"testuser_{unique_id}",
        hashed_password="hashed_password_123",
        full_name="Test User",
        is_active=True
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest.fixture
async def test_project(async_session: AsyncSession, test_user: User) -> Project:
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="A project for testing",
        owner_id=test_user.id,
        technology_stack={
            "backend": "FastAPI",
            "frontend": "React",
            "database": "PostgreSQL"
        }
    )
    
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)
    
    return project


@pytest.fixture
async def test_execution(async_session: AsyncSession, test_project: Project) -> Execution:
    """Create a test execution."""
    from app.models.execution import TaskType, ExecutionStatus
    
    execution = Execution(
        project_id=test_project.id,
        user_request="Test request",
        task_type=TaskType.FULLSTACK_DEVELOPMENT,
        status=ExecutionStatus.INITIALIZING
    )
    
    async_session.add(execution)
    await async_session.commit()
    await async_session.refresh(execution)
    
    return execution


# Markers for different test types
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "asyncio: Async tests")

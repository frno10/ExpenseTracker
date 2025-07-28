"""
Pytest configuration and shared fixtures.
"""
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, CategoryTable, PaymentMethodTable, PaymentType


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.
    
    This fixture creates a fresh database for each test function.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession) -> CategoryTable:
    """Create a sample category for testing."""
    category = CategoryTable(
        id=uuid4(),
        name="Food",
        color="#FF5733",
        icon="utensils",
        is_custom=False
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def sample_payment_method(db_session: AsyncSession) -> PaymentMethodTable:
    """Create a sample payment method for testing."""
    payment_method = PaymentMethodTable(
        id=uuid4(),
        name="Test Credit Card",
        type=PaymentType.CREDIT_CARD,
        account_number="1234",
        institution="Test Bank",
        is_active=True
    )
    db_session.add(payment_method)
    await db_session.commit()
    await db_session.refresh(payment_method)
    return payment_method


@pytest_asyncio.fixture
async def sample_categories(db_session: AsyncSession) -> list[CategoryTable]:
    """Create multiple sample categories for testing."""
    categories = [
        CategoryTable(
            id=uuid4(),
            name="Food",
            color="#FF5733",
            is_custom=False
        ),
        CategoryTable(
            id=uuid4(),
            name="Transportation",
            color="#33FF57",
            is_custom=False
        ),
        CategoryTable(
            id=uuid4(),
            name="Custom Category",
            color="#3357FF",
            is_custom=True
        )
    ]
    
    for category in categories:
        db_session.add(category)
    
    await db_session.commit()
    
    for category in categories:
        await db_session.refresh(category)
    
    return categories


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
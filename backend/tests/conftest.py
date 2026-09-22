import pytest_asyncio
from sqlalchemy import text
from app.database import engine, Base, init_db, AsyncSessionLocal

@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Ensure clean isolated database tables before each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def db_session():
    """Provide an isolated database session for tests."""
    async with AsyncSessionLocal() as session:
        yield session



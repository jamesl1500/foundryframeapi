# DB Core
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.core.config import get_api_settings

# API Settings
settings = get_api_settings()

# Create the async engine
engine = create_async_engine(
    str(settings.database_url),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Create the async session maker
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped async DB session."""
    async with async_session() as session:
        yield session
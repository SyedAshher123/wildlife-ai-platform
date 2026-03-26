"""
Async database session factory and dependency injection.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.config import settings


def _resolved_database_url() -> str:
    """Resolve SQLite relative paths to project-root absolute paths."""
    url = settings.DATABASE_URL
    prefix = "sqlite+aiosqlite:///./"
    if url.startswith(prefix):
        db_name = url[len(prefix):]
        db_path = (settings.PROJECT_ROOT / db_name).resolve()
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"
    return url


# Create async engine
engine = create_async_engine(
    _resolved_database_url(),
    echo=False,
    future=True,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

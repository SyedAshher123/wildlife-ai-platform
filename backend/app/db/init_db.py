"""
Database initialization script.
Creates all tables from ORM models.

Usage:
    python -m backend.app.db.init_db
"""
import asyncio
from backend.app.db.base import Base
from backend.app.db.session import engine

# Import all models so Base.metadata knows about them
from backend.app.models import camera, collection, image, detection, annotation, individual, sighting, missed_correction  # noqa: F401
from backend.app.models import user, job  # noqa: F401


async def init_database():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")


async def drop_database():
    """Drop all tables (use with caution)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("All database tables dropped.")


if __name__ == "__main__":
    asyncio.run(init_database())

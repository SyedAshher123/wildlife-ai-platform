"""Shared fixtures for the pytest suite.

Uses an in-memory SQLite database and overrides FastAPI's get_db dependency.
"""
import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app

# All models must be imported so Base.metadata knows about them
from backend.app.models import camera, collection, image, detection, annotation, individual, sighting  # noqa: F401
from backend.app.models import user, job  # noqa: F401
from backend.app.models.camera import Camera
from backend.app.models.collection import Collection
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.user import User
from backend.app.utils.auth_utils import hash_password, create_access_token


TEST_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSession = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSession() as session:
        yield session


async def _override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---- Factory helpers -------------------------------------------------------

@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a test reviewer user."""
    u = User(email="test@example.com", full_name="Test User", hashed_password=hash_password("password123"), role="reviewer")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """Create a test admin user."""
    u = User(email="admin@example.com", full_name="Admin", hashed_password=hash_password("adminpass123"), role="admin")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


def auth_header(user: User) -> dict:
    """Build Authorization header for a user."""
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_data(db: AsyncSession) -> dict:
    """Seed a camera, collection, images, and detections for testing."""
    cam = Camera(name="1A", camera_number=1, side="A", latitude=-35.0, longitude=150.0)
    db.add(cam)
    await db.flush()

    coll = Collection(name="Collection-1_11-10-2023", collection_number=1)
    db.add(coll)
    await db.flush()

    imgs = []
    for i in range(5):
        img = Image(
            filename=f"RCNX000{i}.JPG",
            file_path=f"MORTON NP PHOTOS/Collection-1_11-10-2023/1A_11-10-23/RCNX000{i}.JPG",
            camera_id=cam.id,
            collection_id=coll.id,
            processed=True,
            has_animal=(i < 3),
            captured_at=datetime(2023, 10, 11, 8 + i, 0, tzinfo=timezone.utc),
        )
        db.add(img)
        await db.flush()
        imgs.append(img)

    dets = []
    for i in range(3):
        d = Detection(
            image_id=imgs[i].id,
            bbox_x=0.1, bbox_y=0.2, bbox_w=0.3, bbox_h=0.4,
            detection_confidence=0.9,
            category="animal",
            species="Dasyurus sp | Quoll sp" if i == 0 else "Notamacropus agilis | Agile Wallaby",
            classification_confidence=0.85 if i == 0 else 0.72,
            model_version="MDv5a+AWC135",
        )
        db.add(d)
        await db.flush()
        dets.append(d)

    await db.commit()
    return {"camera": cam, "collection": coll, "images": imgs, "detections": dets}

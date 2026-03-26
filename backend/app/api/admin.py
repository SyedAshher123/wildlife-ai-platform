"""Admin-only endpoints for user management and system metrics."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.job import ProcessingJob
from backend.app.schemas.schemas import UserOut
from backend.app.utils.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def change_user_role(
    user_id: int,
    role: str,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role (admin only)."""
    if role not in ("admin", "researcher", "reviewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    await db.flush()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/system-metrics")
async def system_metrics(
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """System health metrics (admin only)."""
    total_images = (await db.execute(select(func.count(Image.id)))).scalar() or 0
    processed = (await db.execute(select(func.count(Image.id)).where(Image.processed == True))).scalar() or 0  # noqa: E712
    total_detections = (await db.execute(select(func.count(Detection.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    pending_jobs = (await db.execute(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.status.in_(["queued", "processing"]))
    )).scalar() or 0

    db_path = Path("wildlife.db")
    db_size_mb = round(db_path.stat().st_size / 1024 / 1024, 2) if db_path.exists() else 0

    storage_size_mb = 0
    if settings.STORAGE_ROOT.exists():
        total = sum(f.stat().st_size for f in settings.STORAGE_ROOT.rglob("*") if f.is_file())
        storage_size_mb = round(total / 1024 / 1024, 2)

    return {
        "total_images": total_images,
        "processed_images": processed,
        "unprocessed_images": total_images - processed,
        "total_detections": total_detections,
        "total_users": total_users,
        "pending_jobs": pending_jobs,
        "db_size_mb": db_size_mb,
        "storage_size_mb": storage_size_mb,
    }

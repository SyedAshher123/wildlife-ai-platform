"""Dashboard statistics API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.annotation import Annotation
from backend.app.models.camera import Camera
from backend.app.models.collection import Collection
from backend.app.models.individual import Individual
from backend.app.schemas.schemas import DashboardStats

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get overview statistics for the dashboard."""
    total_images = (await db.execute(select(func.count(Image.id)))).scalar() or 0
    processed = (await db.execute(
        select(func.count(Image.id)).where(Image.processed == True)  # noqa: E712
    )).scalar() or 0
    total_detections = (await db.execute(select(func.count(Detection.id)))).scalar() or 0
    animal_detections = (await db.execute(
        select(func.count(Detection.id)).where(Detection.category == "animal")
    )).scalar() or 0
    quoll_detections = (await db.execute(
        select(func.count(Detection.id)).where(Detection.species.ilike("%quoll%"))
    )).scalar() or 0
    total_individuals = (await db.execute(select(func.count(Individual.id)))).scalar() or 0
    total_cameras = (await db.execute(select(func.count(Camera.id)))).scalar() or 0
    total_collections = (await db.execute(select(func.count(Collection.id)))).scalar() or 0

    # Detections that have no annotation yet
    annotated_ids = select(Annotation.detection_id).distinct()
    pending_review = (await db.execute(
        select(func.count(Detection.id)).where(
            and_(Detection.category == "animal", Detection.id.notin_(annotated_ids))
        )
    )).scalar() or 0

    return DashboardStats(
        total_images=total_images,
        processed_images=processed,
        unprocessed_images=total_images - processed,
        total_detections=total_detections,
        total_animals=animal_detections,
        quoll_detections=quoll_detections,
        total_individuals=total_individuals,
        total_cameras=total_cameras,
        total_collections=total_collections,
        processing_percent=round((processed / total_images * 100), 2) if total_images > 0 else 0.0,
        pending_review=pending_review,
    )


@router.get("/cameras")
async def camera_stats(db: AsyncSession = Depends(get_db)):
    """Camera locations with image/detection counts and last upload time."""
    query = (
        select(
            Camera.id, Camera.name, Camera.latitude, Camera.longitude,
            func.count(Image.id).label("image_count"),
            func.max(Image.captured_at).label("last_upload"),
        )
        .outerjoin(Image, Image.camera_id == Camera.id)
        .group_by(Camera.id, Camera.name, Camera.latitude, Camera.longitude)
        .order_by(Camera.name)
    )
    rows = (await db.execute(query)).all()

    result = []
    for r in rows:
        cam_id, name, lat, lon, img_count, last_upload = r
        det_count_q = (
            select(func.count(Detection.id))
            .join(Image, Image.id == Detection.image_id)
            .where(Image.camera_id == cam_id)
        )
        det_count = (await db.execute(det_count_q)).scalar() or 0
        result.append({
            "id": cam_id, "name": name, "latitude": lat, "longitude": lon,
            "image_count": img_count, "detection_count": det_count,
            "last_upload": str(last_upload) if last_upload else None,
        })
    return result


@router.get("/collections")
async def collection_stats(db: AsyncSession = Depends(get_db)):
    """Image count per collection."""
    query = (
        select(Collection.name, func.count(Image.id).label("image_count"))
        .outerjoin(Image, Image.collection_id == Collection.id)
        .group_by(Collection.id, Collection.name)
        .order_by(Collection.name)
    )
    rows = (await db.execute(query)).all()
    return [{"name": r[0], "image_count": r[1]} for r in rows]


@router.get("/individuals")
async def individual_stats(db: AsyncSession = Depends(get_db)):
    """List all identified individuals with sighting counts."""
    result = await db.execute(select(Individual).order_by(Individual.individual_id))
    return [
        {
            "individual_id": ind.individual_id,
            "species": ind.species,
            "first_seen": ind.first_seen,
            "last_seen": ind.last_seen,
            "total_sightings": ind.total_sightings,
        }
        for ind in result.scalars().all()
    ]

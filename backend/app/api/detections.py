"""Detection querying API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.session import get_db
from backend.app.models.detection import Detection
from backend.app.models.image import Image
from backend.app.schemas.schemas import DetectionOut, DetectionDetail, PaginatedResponse, CameraOut, ImageOut, AnnotationOut

router = APIRouter(prefix="/detections", tags=["Detections"])


@router.get("/", response_model=PaginatedResponse)
async def list_detections(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    species: str | None = None,
    min_confidence: float | None = None,
    image_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List detections with optional filters."""
    query = select(Detection)
    if species is not None:
        query = query.where(Detection.species.ilike(f"%{species}%"))
    if min_confidence is not None:
        query = query.where(Detection.classification_confidence >= min_confidence)
    if image_id is not None:
        query = query.where(Detection.image_id == image_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    detections = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[DetectionOut.model_validate(d) for d in detections],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/species-counts")
async def species_counts(db: AsyncSession = Depends(get_db)):
    """Get count of detections per species."""
    query = (
        select(Detection.species, func.count(Detection.id).label("count"))
        .where(Detection.species.isnot(None))
        .group_by(Detection.species)
        .order_by(func.count(Detection.id).desc())
    )
    rows = (await db.execute(query)).all()
    return [{"species": row[0], "count": row[1]} for row in rows]


@router.get("/{detection_id}", response_model=DetectionDetail)
async def get_detection(detection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single detection with image, camera, and annotations."""
    query = (
        select(Detection)
        .where(Detection.id == detection_id)
        .options(
            selectinload(Detection.image).selectinload(Image.camera),
            selectinload(Detection.annotations),
        )
    )
    det = (await db.execute(query)).scalar_one_or_none()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")

    return DetectionDetail(
        **DetectionOut.model_validate(det).model_dump(),
        image=ImageOut.model_validate(det.image) if det.image else None,
        camera=CameraOut.model_validate(det.image.camera) if det.image and det.image.camera else None,
        annotations=[AnnotationOut.model_validate(a) for a in det.annotations],
    )

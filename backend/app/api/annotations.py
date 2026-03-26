"""Annotation CRUD endpoints for ecologist review workflow."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.annotation import Annotation
from backend.app.models.detection import Detection
from backend.app.models.user import User
from backend.app.schemas.schemas import AnnotationCreate, AnnotationUpdate, AnnotationOut
from backend.app.utils.dependencies import get_current_user

router = APIRouter(prefix="/annotations", tags=["Annotations"])


@router.post("/", response_model=AnnotationOut, status_code=status.HTTP_201_CREATED)
async def create_annotation(
    payload: AnnotationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an annotation (species correction, individual ID, retraining flag)."""
    det = (await db.execute(select(Detection).where(Detection.id == payload.detection_id))).scalar_one_or_none()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")

    ann = Annotation(
        detection_id=payload.detection_id,
        annotator=user.email,
        corrected_species=payload.corrected_species,
        is_correct=payload.is_correct,
        notes=payload.notes,
        individual_id=payload.individual_id,
        flag_for_retraining=payload.flag_for_retraining,
    )
    db.add(ann)
    await db.flush()
    await db.refresh(ann)
    return AnnotationOut.model_validate(ann)


@router.get("/by-detection/{detection_id}", response_model=list[AnnotationOut])
async def get_annotations_for_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all annotations for a specific detection."""
    result = await db.execute(
        select(Annotation).where(Annotation.detection_id == detection_id).order_by(Annotation.created_at.desc())
    )
    return [AnnotationOut.model_validate(a) for a in result.scalars().all()]


@router.put("/{annotation_id}", response_model=AnnotationOut)
async def update_annotation(
    annotation_id: int,
    payload: AnnotationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing annotation."""
    ann = (await db.execute(select(Annotation).where(Annotation.id == annotation_id))).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ann, field, value)
    ann.annotator = user.email

    await db.flush()
    await db.refresh(ann)
    return AnnotationOut.model_validate(ann)

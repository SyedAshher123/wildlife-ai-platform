"""Dataset export endpoints for researchers."""
import csv
import io
import json
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.config import settings
from backend.app.db.session import get_db
from backend.app.models.detection import Detection
from backend.app.models.image import Image
from backend.app.models.annotation import Annotation
from backend.app.models.camera import Camera
from backend.app.utils.dependencies import get_current_user

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/quoll-detections")
async def export_quoll_detections(
    min_confidence: float = 0.0,
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export all quoll detections as CSV or JSON."""
    query = (
        select(Detection)
        .where(Detection.species.ilike("%quoll%"))
        .options(selectinload(Detection.image).selectinload(Image.camera))
        .order_by(Detection.classification_confidence.desc())
    )
    if min_confidence > 0:
        query = query.where(Detection.classification_confidence >= min_confidence)

    dets = (await db.execute(query)).scalars().all()

    rows = []
    for d in dets:
        rows.append({
            "detection_id": d.id,
            "image_id": d.image_id,
            "filename": d.image.filename if d.image else None,
            "camera": d.image.camera.name if d.image and d.image.camera else None,
            "species": d.species,
            "classification_confidence": d.classification_confidence,
            "detection_confidence": d.detection_confidence,
            "bbox_x": d.bbox_x, "bbox_y": d.bbox_y,
            "bbox_w": d.bbox_w, "bbox_h": d.bbox_h,
            "model_version": d.model_version,
            "crop_path": d.crop_path,
            "created_at": str(d.created_at) if d.created_at else None,
        })

    if format == "json":
        return Response(
            content=json.dumps(rows, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=quoll_detections.json"},
        )

    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quoll_detections.csv"},
    )


@router.get("/metadata")
async def export_metadata(
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export full metadata: images + detections + annotations."""
    query = (
        select(Detection)
        .options(
            selectinload(Detection.image).selectinload(Image.camera),
            selectinload(Detection.annotations),
        )
        .order_by(Detection.id)
    )
    dets = (await db.execute(query)).scalars().all()

    rows = []
    for d in dets:
        ann = d.annotations[0] if d.annotations else None
        rows.append({
            "detection_id": d.id,
            "image_id": d.image_id,
            "filename": d.image.filename if d.image else None,
            "file_path": d.image.file_path if d.image else None,
            "camera": d.image.camera.name if d.image and d.image.camera else None,
            "captured_at": str(d.image.captured_at) if d.image and d.image.captured_at else None,
            "species": d.species,
            "classification_confidence": d.classification_confidence,
            "detection_confidence": d.detection_confidence,
            "bbox_x": d.bbox_x, "bbox_y": d.bbox_y,
            "bbox_w": d.bbox_w, "bbox_h": d.bbox_h,
            "model_version": d.model_version,
            "crop_path": d.crop_path,
            "annotation_correct": ann.is_correct if ann else None,
            "annotation_species": ann.corrected_species if ann else None,
            "annotation_individual": ann.individual_id if ann else None,
            "annotation_notes": ann.notes if ann else None,
            "flagged_retraining": ann.flag_for_retraining if ann else None,
        })

    if format == "json":
        return Response(
            content=json.dumps(rows, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=wildlife_metadata.json"},
        )

    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wildlife_metadata.csv"},
    )


@router.get("/crops")
async def export_crops_zip(
    species: str = Query("quoll", description="Species filter"),
    min_confidence: float = 0.0,
    db: AsyncSession = Depends(get_db),
):
    """Export a ZIP of cropped detection images for a given species."""
    query = (
        select(Detection)
        .where(Detection.species.ilike(f"%{species}%"), Detection.crop_path.isnot(None))
        .order_by(Detection.id)
    )
    if min_confidence > 0:
        query = query.where(Detection.classification_confidence >= min_confidence)

    dets = (await db.execute(query)).scalars().all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in dets:
            crop_full = settings.STORAGE_ROOT / d.crop_path
            if crop_full.exists():
                arcname = f"{d.species or 'unknown'}/{Path(d.crop_path).name}"
                zf.write(crop_full, arcname)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={species}_crops.zip"},
    )

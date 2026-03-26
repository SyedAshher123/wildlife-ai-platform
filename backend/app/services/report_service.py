"""Report generation service — aggregates DB data into report dicts."""
import csv
import io
import json
from datetime import datetime

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.annotation import Annotation
from backend.app.models.camera import Camera
from backend.app.models.job import ProcessingJob


async def generate_summary_report(
    db: AsyncSession,
    species_filter: str | None = None,
    camera_ids: list[int] | None = None,
    collection_ids: list[int] | None = None,
) -> dict:
    """Generate a full platform summary report."""
    img_filter = select(Image.id)
    if camera_ids:
        img_filter = img_filter.where(Image.camera_id.in_(camera_ids))
    if collection_ids:
        img_filter = img_filter.where(Image.collection_id.in_(collection_ids))

    total_images = (await db.execute(select(func.count()).select_from(img_filter.subquery()))).scalar() or 0
    processed_images = (await db.execute(
        select(func.count()).select_from(img_filter.where(Image.processed == True).subquery())  # noqa: E712
    )).scalar() or 0
    empty_images = (await db.execute(
        select(func.count()).select_from(img_filter.where(Image.has_animal == False).subquery())  # noqa: E712
    )).scalar() or 0

    det_query = select(Detection)
    if camera_ids or collection_ids:
        det_query = det_query.join(Image, Image.id == Detection.image_id)
        if camera_ids:
            det_query = det_query.where(Image.camera_id.in_(camera_ids))
        if collection_ids:
            det_query = det_query.where(Image.collection_id.in_(collection_ids))
    if species_filter:
        det_query = det_query.where(Detection.species.ilike(f"%{species_filter}%"))

    det_count_q = select(func.count()).select_from(det_query.subquery())
    total_detections = (await db.execute(det_count_q)).scalar() or 0

    # Species distribution
    sp_q = (
        select(Detection.species, func.count(Detection.id).label("count"))
        .where(Detection.species.isnot(None))
        .group_by(Detection.species)
        .order_by(func.count(Detection.id).desc())
    )
    species_rows = (await db.execute(sp_q)).all()
    species_distribution = [{"species": r[0], "count": r[1]} for r in species_rows]
    total_species = len(species_distribution)

    quoll_detections = sum(r["count"] for r in species_distribution if "quoll" in (r["species"] or "").lower())

    # Confidence stats
    mean_det_conf = (await db.execute(select(func.avg(Detection.detection_confidence)))).scalar()
    mean_cls_conf = (await db.execute(
        select(func.avg(Detection.classification_confidence)).where(Detection.classification_confidence.isnot(None))
    )).scalar()

    # Camera counts
    cam_q = (
        select(Camera.name, func.count(Detection.id).label("count"))
        .join(Image, Image.camera_id == Camera.id)
        .join(Detection, Detection.image_id == Image.id)
        .group_by(Camera.name)
        .order_by(func.count(Detection.id).desc())
    )
    cam_rows = (await db.execute(cam_q)).all()
    camera_counts = [{"camera": r[0], "detections": r[1]} for r in cam_rows]

    # Hourly activity (from captured_at)
    hourly_q = (
        select(extract("hour", Image.captured_at).label("hour"), func.count(Detection.id).label("count"))
        .join(Detection, Detection.image_id == Image.id)
        .where(Image.captured_at.isnot(None))
        .group_by("hour")
        .order_by("hour")
    )
    hourly_rows = (await db.execute(hourly_q)).all()
    hourly_activity = [{"hour": int(r[0]), "detections": r[1]} for r in hourly_rows]

    return {
        "total_images": total_images,
        "processed_images": processed_images,
        "empty_images": empty_images,
        "total_detections": total_detections,
        "total_species": total_species,
        "quoll_detections": quoll_detections,
        "mean_detection_confidence": round(mean_det_conf, 4) if mean_det_conf else None,
        "mean_classification_confidence": round(mean_cls_conf, 4) if mean_cls_conf else None,
        "species_distribution": species_distribution,
        "camera_counts": camera_counts,
        "hourly_activity": hourly_activity,
    }


async def generate_batch_report(db: AsyncSession, job_id: int) -> dict | None:
    """Report for a specific batch processing job."""
    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
    if not job:
        return None

    elapsed = None
    if job.started_at and job.completed_at:
        elapsed = (job.completed_at - job.started_at).total_seconds()

    base_report = await generate_summary_report(db)
    base_report["job_id"] = job.id
    base_report["job_status"] = job.status
    base_report["processing_time_seconds"] = elapsed
    base_report["total_images"] = job.total_images
    base_report["processed_images"] = job.processed_images
    base_report["failed_images"] = job.failed_images
    return base_report


def export_report_csv(report: dict) -> str:
    """Convert report dict to CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["Metric", "Value"])
    for key in ["total_images", "processed_images", "empty_images", "total_detections",
                 "total_species", "quoll_detections", "mean_detection_confidence",
                 "mean_classification_confidence", "processing_time_seconds"]:
        writer.writerow([key, report.get(key, "")])

    writer.writerow([])
    writer.writerow(["Species", "Count"])
    for sp in report.get("species_distribution", []):
        writer.writerow([sp["species"], sp["count"]])

    writer.writerow([])
    writer.writerow(["Camera", "Detections"])
    for cam in report.get("camera_counts", []):
        writer.writerow([cam["camera"], cam["detections"]])

    writer.writerow([])
    writer.writerow(["Hour", "Detections"])
    for hr in report.get("hourly_activity", []):
        writer.writerow([hr["hour"], hr["detections"]])

    return buf.getvalue()


def export_report_json(report: dict) -> str:
    """Convert report dict to formatted JSON string."""
    return json.dumps(report, indent=2, default=str)

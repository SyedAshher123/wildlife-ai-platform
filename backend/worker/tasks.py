"""Celery tasks that wrap the existing ML pipelines.

Start the worker:
    celery -A backend.worker.celery_app worker -l info -Q ml -c 1

Using concurrency=1 because the GPU should not be shared across threads.
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.worker.celery_app import celery_app
from backend.app.config import settings
from backend.app.db.session import async_session_factory, engine
from backend.app.db.base import Base
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.job import ProcessingJob


def _get_pipelines():
    """Lazy-load ML pipelines (heavy imports, GPU init)."""
    from backend.worker.pipelines.megadetector_pipeline import MegaDetectorPipeline
    from backend.worker.pipelines.awc135_pipeline import AWC135Pipeline
    md = MegaDetectorPipeline()
    awc = AWC135Pipeline()
    md.load_model()
    awc.load_model()
    return md, awc


_md_pipeline = None
_awc_pipeline = None


def _ensure_pipelines():
    global _md_pipeline, _awc_pipeline
    if _md_pipeline is None:
        _md_pipeline, _awc_pipeline = _get_pipelines()
    return _md_pipeline, _awc_pipeline


async def _process_single_image(db: AsyncSession, image: Image, md, awc):
    """Process one image: MegaDetector -> crop -> AWC135 -> save detections."""
    img_path = settings.DATASET_ROOT / image.file_path
    if not img_path.exists():
        img_path = settings.STORAGE_ROOT / image.file_path
    if not img_path.exists():
        image.processed = True
        image.has_animal = False
        return

    detections = md.detect_single(img_path)
    animal_dets = [d for d in detections if d["category"] == "animal"]

    if not animal_dets:
        image.processed = True
        image.has_animal = False
        return

    image.has_animal = True
    for i, det in enumerate(animal_dets):
        bbox = det["bbox"]
        classification = awc.classify_single(img_path, bbox=bbox, bbox_conf=det["confidence"])

        crop_filename = f"{image.id}_{i}.jpg"
        crop_dir = settings.STORAGE_ROOT / "crops" / str(image.camera_id or "upload")
        crop_path = crop_dir / crop_filename
        try:
            md.crop_detection(img_path, bbox, crop_path)
        except Exception:
            crop_path = None

        detection = Detection(
            image_id=image.id,
            bbox_x=bbox[0], bbox_y=bbox[1], bbox_w=bbox[2], bbox_h=bbox[3],
            detection_confidence=det["confidence"],
            category=det["category"],
            species=classification.get("species"),
            classification_confidence=classification.get("confidence"),
            model_version="MDv5a+AWC135",
            crop_path=str(crop_path.relative_to(settings.STORAGE_ROOT)) if crop_path and crop_path.exists() else None,
        )
        db.add(detection)

    image.processed = True


async def _run_process_image(image_id: int):
    md, awc = _ensure_pipelines()
    async with async_session_factory() as db:
        image = (await db.execute(select(Image).where(Image.id == image_id))).scalar_one_or_none()
        if image and not image.processed:
            await _process_single_image(db, image, md, awc)
            await db.commit()


async def _run_process_batch(job_id: int, image_ids: list[int]):
    md, awc = _ensure_pipelines()

    async with async_session_factory() as db:
        job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
        if job:
            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

    for img_id in image_ids:
        try:
            async with async_session_factory() as db:
                image = (await db.execute(select(Image).where(Image.id == img_id))).scalar_one_or_none()
                if image and not image.processed:
                    await _process_single_image(db, image, md, awc)
                    await db.commit()

                job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
                if job:
                    job.processed_images += 1
                    await db.commit()
        except Exception:
            async with async_session_factory() as db:
                job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
                if job:
                    job.failed_images += 1
                    await db.commit()

    async with async_session_factory() as db:
        job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
        if job:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()


@celery_app.task(name="backend.worker.tasks.process_image_task", bind=True)
def process_image_task(self, image_id: int):
    asyncio.run(_run_process_image(image_id))
    return {"image_id": image_id, "status": "done"}


@celery_app.task(name="backend.worker.tasks.process_batch_task", bind=True)
def process_batch_task(self, job_id: int, image_ids: list[int]):
    asyncio.run(_run_process_batch(job_id, image_ids))
    return {"job_id": job_id, "processed": len(image_ids)}

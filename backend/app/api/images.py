"""Image browsing, upload, and batch processing API endpoints."""
import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import json

from backend.app.config import settings
from backend.app.db.session import get_db, async_session_factory
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.missed_correction import MissedDetectionCorrection
from backend.app.models.camera import Camera
from backend.app.models.collection import Collection
from backend.app.models.job import ProcessingJob
from backend.app.models.user import User
from backend.app.schemas.schemas import (
    ImageOut, ImageDetail, PaginatedResponse, BatchUploadResponse, JobStatus,
    MissedDetectionCreate, MissedDetectionOut,
)
from backend.app.utils.dependencies import get_current_user, get_optional_user

router = APIRouter(prefix="/images", tags=["Images"])

UPLOAD_DIR = settings.STORAGE_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_local_batch_queues: dict[int, list[int]] = {}
_local_batch_tasks: dict[int, asyncio.Task] = {}


def _sanitize_upload_path(raw_name: str | None) -> Path:
    """Normalize client-provided upload name to a safe relative path."""
    src = Path(raw_name or "unknown.jpg")
    parts = [p for p in src.parts if p not in ("", ".", "..")]
    if not parts:
        return Path("unknown.jpg")
    return Path(*parts)


async def _reserve_unique_upload_path(
    db: AsyncSession,
    raw_name: str | None,
    reserved_rel_paths: set[str],
) -> tuple[Path, str, str]:
    """Return a unique destination path and DB file_path for an upload."""
    cleaned = _sanitize_upload_path(raw_name)
    parent = cleaned.parent
    stem = cleaned.stem or "image"
    suffix = cleaned.suffix or ".jpg"

    i = 0
    while True:
        name = f"{stem}{suffix}" if i == 0 else f"{stem}_{i}{suffix}"
        rel_path = (Path("uploads") / parent / name).as_posix()

        if rel_path in reserved_rel_paths:
            i += 1
            continue

        exists_query = select(Image.id).where(Image.file_path == rel_path).limit(1)
        exists = (await db.execute(exists_query)).scalar_one_or_none()
        if exists is None:
            reserved_rel_paths.add(rel_path)
            return UPLOAD_DIR / parent / name, rel_path, name

        i += 1


async def _run_batch_locally(job_id: int, image_ids: list[int]) -> None:
    """Fallback path when Celery is unavailable: process in API process."""
    try:
        from backend.worker.tasks import _run_process_batch
        await _run_process_batch(job_id, image_ids)
    except Exception as exc:
        async with async_session_factory() as db:
            job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                await db.commit()


async def _run_single_locally(image_id: int) -> None:
    """Fallback path when Celery is unavailable for single-image uploads."""
    try:
        from backend.worker.tasks import _run_process_image
        await _run_process_image(image_id)
    except Exception:
        # Leave image as unprocessed if local fallback also fails.
        return


async def _drain_local_batch_queue(job_id: int) -> None:
    """Run queued local batch chunks sequentially for one job."""
    try:
        while True:
            pending = _local_batch_queues.get(job_id, [])
            if not pending:
                break
            current = pending[:]
            _local_batch_queues[job_id] = []
            await _run_batch_locally(job_id, current)
    finally:
        _local_batch_tasks.pop(job_id, None)
        if not _local_batch_queues.get(job_id):
            _local_batch_queues.pop(job_id, None)


def _enqueue_local_batch(job_id: int, image_ids: list[int]) -> None:
    """Append chunk image IDs to the local queue and ensure one worker."""
    if not image_ids:
        return
    queue = _local_batch_queues.setdefault(job_id, [])
    queue.extend(image_ids)
    task = _local_batch_tasks.get(job_id)
    if task is None or task.done():
        _local_batch_tasks[job_id] = asyncio.create_task(_drain_local_batch_queue(job_id))


# ---- Read endpoints -------------------------------------------------------

@router.get("/", response_model=PaginatedResponse)
async def list_images(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    camera_id: int | None = None,
    collection_id: int | None = None,
    processed: bool | None = None,
    has_animal: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List images with optional filters and pagination."""
    query = select(Image)
    if camera_id is not None:
        query = query.where(Image.camera_id == camera_id)
    if collection_id is not None:
        query = query.where(Image.collection_id == collection_id)
    if processed is not None:
        query = query.where(Image.processed == processed)
    if has_animal is not None:
        query = query.where(Image.has_animal == has_animal)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    images = result.scalars().all()

    return PaginatedResponse(
        items=[ImageOut.model_validate(img) for img in images],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    """Poll processing job progress."""
    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    pct = (job.processed_images / job.total_images * 100) if job.total_images > 0 else 0.0
    resp = JobStatus.model_validate(job)
    resp.percent = round(pct, 2)
    return resp


@router.get("/{image_id:int}", response_model=ImageDetail)
async def get_image(image_id: int, db: AsyncSession = Depends(get_db)):
    """Get image details including camera, collection, and detections."""
    query = (
        select(Image)
        .where(Image.id == image_id)
        .options(selectinload(Image.camera), selectinload(Image.collection), selectinload(Image.detections))
    )
    image = (await db.execute(query)).scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageDetail.model_validate(image)


@router.post("/{image_id:int}/missed-detection", response_model=MissedDetectionOut, status_code=201)
async def create_missed_detection(
    image_id: int,
    payload: MissedDetectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User reports a missed animal: draw bbox on image and label species (feedback for model refinement)."""
    image = (await db.execute(select(Image).where(Image.id == image_id))).scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    correction = MissedDetectionCorrection(
        image_id=image_id,
        bbox_x=payload.bbox_x,
        bbox_y=payload.bbox_y,
        bbox_w=payload.bbox_w,
        bbox_h=payload.bbox_h,
        species=payload.species,
        annotator=user.email,
        flag_for_retraining=payload.flag_for_retraining,
    )
    db.add(correction)
    await db.flush()
    await db.refresh(correction)
    return MissedDetectionOut.model_validate(correction)


@router.get("/by-species/{species}", response_model=PaginatedResponse)
async def images_by_species(
    species: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Find images that contain detections of a specific species."""
    query = (
        select(Image)
        .join(Detection, Detection.image_id == Image.id)
        .where(Detection.species.ilike(f"%{species}%"))
        .distinct()
    )
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    images = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[ImageOut.model_validate(img) for img in images],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


# ---- Upload endpoints -----------------------------------------------------

@router.post("/upload", response_model=ImageOut)
async def upload_image(
    file: UploadFile = File(...),
    camera_id: int | None = None,
    collection_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single image, save to storage, create DB record, queue ML processing."""
    ext = Path(file.filename or "unknown.jpg").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(status_code=400, detail="Unsupported image format")

    dest, rel_path, saved_name = await _reserve_unique_upload_path(db, file.filename, set())
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    image = Image(
        filename=saved_name,
        file_path=rel_path,
        camera_id=camera_id,
        collection_id=collection_id,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)

    try:
        from backend.worker.tasks import process_image_task
        process_image_task.delay(image.id)
    except Exception:
        asyncio.create_task(_run_single_locally(image.id))

    return ImageOut.model_validate(image)


def _extract_camera_name(relative_path: str) -> str | None:
    """Extract the camera subfolder name from a relative path like 'Collection/CAM01/IMG.jpg'."""
    parts = Path(relative_path).parts
    if len(parts) >= 3:
        return parts[1]
    if len(parts) == 2:
        return None
    return None


def _extract_collection_name(relative_path: str) -> str | None:
    """Extract the root collection folder from a relative path like 'Collection/CAM01/IMG.jpg'."""
    parts = Path(relative_path).parts
    if len(parts) >= 2:
        return parts[0]
    return None


async def _get_or_create_camera(db: AsyncSession, name: str, cache: dict[str, int]) -> int:
    """Find or create a Camera by name, using a local cache to avoid repeated queries."""
    if name in cache:
        return cache[name]
    row = (await db.execute(select(Camera).where(Camera.name == name))).scalar_one_or_none()
    if row:
        cache[name] = row.id
        return row.id
    cam = Camera(name=name)
    db.add(cam)
    await db.flush()
    cache[name] = cam.id
    return cam.id


async def _get_or_create_collection(db: AsyncSession, name: str, cache: dict[str, int]) -> int:
    """Find or create a Collection by name, using a local cache."""
    if name in cache:
        return cache[name]
    row = (await db.execute(select(Collection).where(Collection.name == name))).scalar_one_or_none()
    if row:
        cache[name] = row.id
        return row.id
    col = Collection(name=name, folder_path=name)
    db.add(col)
    await db.flush()
    cache[name] = col.id
    return col.id


@router.post("/upload-batch", response_model=BatchUploadResponse)
async def upload_batch(
    files: list[UploadFile] = File(...),
    relative_paths: str | None = Form(None),
    collection_name: str | None = Form(None),
    camera_id: int | None = None,
    collection_id: int | None = None,
    job_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple images and queue a batch processing job.

    When `relative_paths` is provided (JSON array of browser webkitRelativePath strings),
    the endpoint auto-creates Collection and Camera records from the folder structure.
    """
    paths_list: list[str] = []
    if relative_paths:
        try:
            paths_list = json.loads(relative_paths)
        except (json.JSONDecodeError, TypeError):
            paths_list = []

    camera_cache: dict[str, int] = {}
    collection_cache: dict[str, int] = {}

    image_ids = []
    reserved_rel_paths: set[str] = set()

    for idx, f in enumerate(files):
        ext = Path(f.filename or "unknown.jpg").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            continue

        rel_path_from_browser = paths_list[idx] if idx < len(paths_list) else None
        use_path = rel_path_from_browser or f.filename

        file_camera_id = camera_id
        file_collection_id = collection_id

        if rel_path_from_browser:
            col_name = collection_name or _extract_collection_name(rel_path_from_browser)
            cam_name = _extract_camera_name(rel_path_from_browser)

            if col_name and file_collection_id is None:
                file_collection_id = await _get_or_create_collection(db, col_name, collection_cache)
            if cam_name and file_camera_id is None:
                file_camera_id = await _get_or_create_camera(db, cam_name, camera_cache)

        dest, rel_path, saved_name = await _reserve_unique_upload_path(db, use_path, reserved_rel_paths)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)

        image = Image(
            filename=saved_name,
            file_path=rel_path,
            camera_id=file_camera_id,
            collection_id=file_collection_id,
        )
        db.add(image)
        await db.flush()
        image_ids.append(image.id)

    if job_id is not None:
        job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.created_by is not None and job.created_by != user.id:
            raise HTTPException(status_code=403, detail="Not allowed to append to this job")
        job.total_images += len(image_ids)
        if job.status in ("completed", "failed"):
            job.status = "queued"
            job.error_message = None
            job.failed_images = 0
    else:
        batch_label = collection_name or (list(collection_cache.keys())[0] if collection_cache else f"batch-{len(image_ids)}-files")
        job = ProcessingJob(
            batch_name=batch_label,
            status="queued",
            total_images=len(image_ids),
            created_by=user.id,
        )
        db.add(job)
        await db.flush()

    try:
        from backend.worker.tasks import process_batch_task
        task = process_batch_task.delay(job.id, image_ids)
        job.celery_task_id = task.id
    except Exception:
        job.celery_task_id = "local-fallback"
        _enqueue_local_batch(job.id, image_ids)

    return BatchUploadResponse(job_id=job.id, files_received=len(image_ids), status="queued")

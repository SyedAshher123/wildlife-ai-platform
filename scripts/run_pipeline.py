"""
ML Processing Pipeline — Standalone Script
============================================
Runs MegaDetector → crop → AWC135 on unprocessed images from the database.
Does NOT require Celery or Redis — runs directly on your GPU.

Usage:
    python -m scripts.run_pipeline
    python -m scripts.run_pipeline --limit 100 --verbose
    python -m scripts.run_pipeline --batch-size 4  # lower for less VRAM
"""
import asyncio
import argparse
import time
from pathlib import Path

from tqdm import tqdm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import engine, async_session_factory
from backend.app.db.base import Base

# Import models
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models import camera, collection, annotation, individual, sighting, user, job  # noqa: F401

# Import pipelines
from backend.worker.pipelines.megadetector_pipeline import MegaDetectorPipeline
from backend.worker.pipelines.awc135_pipeline import AWC135Pipeline


async def get_unprocessed_images(db: AsyncSession, limit: int | None = None) -> list[Image]:
    """Get images that haven't been processed yet."""
    query = select(Image).where(Image.processed == False).order_by(Image.id)
    if limit:
        query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def process_batch(
    db: AsyncSession,
    images: list[Image],
    md_pipeline: MegaDetectorPipeline,
    awc_pipeline: AWC135Pipeline,
    verbose: bool = False,
):
    """Process a batch of images through MegaDetector → crop → AWC135."""
    dataset_root = settings.DATASET_ROOT

    for img in images:
        img_path = dataset_root / img.file_path
        if not img_path.exists():
            if verbose:
                print(f"  ⚠️ File not found: {img.file_path}")
            img.processed = True
            img.has_animal = False
            continue

        try:
            # Step 1: MegaDetector detection
            detections = md_pipeline.detect_single(img_path)

            if not detections:
                # No animals detected
                img.processed = True
                img.has_animal = False
                if verbose:
                    print(f"  🔲 {img.filename}: empty")
                continue

            # Filter for animal detections only
            animal_detections = [d for d in detections if d["category"] == "animal"]

            if not animal_detections:
                img.processed = True
                img.has_animal = False
                if verbose:
                    print(f"  👤 {img.filename}: person/vehicle only")
                continue

            img.has_animal = True

            # Step 2: For each animal detection, classify + save crop for UI
            for i, det in enumerate(animal_detections):
                bbox = det["bbox"]
                bbox_conf = det["confidence"]

                # Classify using original image + bbox (AWC135 crops internally)
                classification = awc_pipeline.classify_single(
                    img_path,
                    bbox=bbox,
                    bbox_conf=bbox_conf,
                )

                # Save crop for annotation UI
                crop_filename = f"{img.id}_{i}.jpg"
                crop_dir = settings.STORAGE_ROOT / "crops" / str(img.camera_id or "unknown")
                crop_path = crop_dir / crop_filename
                try:
                    md_pipeline.crop_detection(img_path, bbox, crop_path)
                except Exception:
                    crop_path = None

                # Save detection to DB
                detection = Detection(
                    image_id=img.id,
                    bbox_x=bbox[0],
                    bbox_y=bbox[1],
                    bbox_w=bbox[2],
                    bbox_h=bbox[3],
                    detection_confidence=bbox_conf,
                    category=det["category"],
                    species=classification.get("species"),
                    classification_confidence=classification.get("confidence"),
                    model_version="MDv5a+AWC135",
                    crop_path=str(crop_path.relative_to(settings.STORAGE_ROOT)) if crop_path and crop_path.exists() else None,
                )
                db.add(detection)

                if verbose:
                    species = classification.get("species", "unknown")
                    conf = classification.get("confidence", 0)
                    is_quoll = "🐾" if awc_pipeline.is_target_species(classification) else "  "
                    print(f"  {is_quoll} {img.filename} box{i}: {species} ({conf:.2f})")

            img.processed = True

        except Exception as e:
            if verbose:
                print(f"  ❌ {img.filename}: {e}")
            img.processed = True
            img.has_animal = None  # Unknown due to error


async def run_pipeline(
    limit: int | None = None,
    batch_size: int | None = None,
    verbose: bool = False,
):
    """Main pipeline execution."""
    batch_size = batch_size or settings.BATCH_SIZE

    print("=" * 60)
    print("Wildlife AI Platform — ML Processing Pipeline")
    print("=" * 60)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize pipelines
    print("\n🔧 Initializing ML models...")
    md_pipeline = MegaDetectorPipeline()
    awc_pipeline = AWC135Pipeline()

    # Pre-load models (so we can measure load time separately)
    start = time.time()
    md_pipeline.load_model()
    print(f"  MegaDetector loaded in {time.time() - start:.1f}s")

    start = time.time()
    awc_pipeline.load_model()
    print(f"  AWC135 loaded in {time.time() - start:.1f}s")

    # Get unprocessed images
    async with async_session_factory() as db:
        total_unprocessed_query = select(func.count(Image.id)).where(Image.processed == False)
        total_unprocessed = (await db.execute(total_unprocessed_query)).scalar() or 0
        total_images = (await db.execute(select(func.count(Image.id)))).scalar() or 0

    print(f"\n📊 Status: {total_images} total images, {total_unprocessed} unprocessed")

    if total_unprocessed == 0:
        print("✅ All images already processed!")
        return

    target = min(limit or total_unprocessed, total_unprocessed)
    print(f"🎯 Processing {target} images in batches of {batch_size}")
    print()

    processed_count = 0
    start_time = time.time()

    with tqdm(total=target, desc="Processing", unit="img") as pbar:
        while processed_count < target:
            async with async_session_factory() as db:
                remaining = target - processed_count
                batch_limit = min(batch_size, remaining)

                images = await get_unprocessed_images(db, limit=batch_limit)
                if not images:
                    break

                await process_batch(db, images, md_pipeline, awc_pipeline, verbose=verbose)
                await db.commit()

                processed_count += len(images)
                pbar.update(len(images))

                # ETA calculation
                elapsed = time.time() - start_time
                if processed_count > 0:
                    rate = processed_count / elapsed
                    remaining_time = (target - processed_count) / rate
                    pbar.set_postfix({
                        "rate": f"{rate:.1f} img/s",
                        "ETA": f"{remaining_time / 60:.0f}m",
                    })

    # Final stats
    elapsed = time.time() - start_time
    rate = processed_count / elapsed if elapsed > 0 else 0

    print("\n" + "=" * 60)
    print(f"✅ Processing complete!")
    print(f"   Images processed: {processed_count}")
    print(f"   Time elapsed: {elapsed / 60:.1f} minutes")
    print(f"   Average rate: {rate:.1f} images/second")
    print("=" * 60)

    # Print detection summary
    async with async_session_factory() as db:
        total_dets = (await db.execute(select(func.count(Detection.id)))).scalar() or 0
        quoll_dets = (await db.execute(
            select(func.count(Detection.id)).where(Detection.species.ilike("%quoll%"))
        )).scalar() or 0
        empty = (await db.execute(
            select(func.count(Image.id)).where(Image.has_animal == False)
        )).scalar() or 0

    print(f"\n📊 Detection Summary:")
    print(f"   Total detections: {total_dets}")
    print(f"   Quoll detections: {quoll_dets}")
    print(f"   Empty images: {empty}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ML detection pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Max images to process")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size (default: 8)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-image results")
    args = parser.parse_args()

    asyncio.run(run_pipeline(
        limit=args.limit,
        batch_size=args.batch_size,
        verbose=args.verbose,
    ))

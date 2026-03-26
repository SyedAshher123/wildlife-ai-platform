"""
Pipeline Verification & Diagnostics
====================================
Checks database consistency and validates ML pipeline outputs.
Does NOT run the ML models — only inspects what's already in the DB.

Usage:
    python -m scripts.verify_pipeline
    python -m scripts.verify_pipeline --verbose
"""
import asyncio
import argparse
from pathlib import Path
from collections import Counter

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import async_session_factory, engine
from backend.app.db.base import Base
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.camera import Camera


class VerificationResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.details: list[str] = []

    def ok(self, msg: str = ""):
        self.passed += 1
        if msg:
            self.details.append(f"  [OK] {msg}")

    def fail(self, msg: str):
        self.failed += 1
        self.details.append(f"  [FAIL] {msg}")

    def warn(self, msg: str):
        self.warnings += 1
        self.details.append(f"  [WARN] {msg}")


async def check_database_basics(db: AsyncSession) -> VerificationResult:
    """Verify basic DB state."""
    r = VerificationResult("Database basics")

    total_images = (await db.execute(select(func.count(Image.id)))).scalar() or 0
    processed = (await db.execute(select(func.count(Image.id)).where(Image.processed == True))).scalar() or 0  # noqa: E712
    total_dets = (await db.execute(select(func.count(Detection.id)))).scalar() or 0
    total_cams = (await db.execute(select(func.count(Camera.id)))).scalar() or 0

    if total_images > 0:
        r.ok(f"Images in DB: {total_images}")
    else:
        r.fail("No images in DB — run bulk_import first")

    if total_cams > 0:
        r.ok(f"Cameras in DB: {total_cams}")
    else:
        r.warn("No cameras in DB")

    if processed > 0:
        r.ok(f"Processed images: {processed}/{total_images} ({processed/total_images*100:.1f}%)")
    else:
        r.warn("No images processed yet — run run_pipeline first")

    if total_dets > 0:
        r.ok(f"Total detections: {total_dets}")
    else:
        r.warn("No detections yet")

    return r


async def check_bbox_validity(db: AsyncSession, verbose: bool = False) -> VerificationResult:
    """Verify all bounding boxes are in valid 0-1 range with positive dimensions."""
    r = VerificationResult("Bounding box validation")

    dets = (await db.execute(select(Detection))).scalars().all()
    if not dets:
        r.warn("No detections to validate")
        return r

    invalid_range = 0
    zero_size = 0
    for d in dets:
        for val, name in [(d.bbox_x, "x"), (d.bbox_y, "y"), (d.bbox_w, "w"), (d.bbox_h, "h")]:
            if val is None or val < 0 or val > 1:
                invalid_range += 1
                if verbose:
                    r.fail(f"Detection {d.id}: {name}={val} out of [0,1] range")
                break
        if d.bbox_w is not None and d.bbox_h is not None:
            if d.bbox_w <= 0 or d.bbox_h <= 0:
                zero_size += 1
                if verbose:
                    r.fail(f"Detection {d.id}: zero/negative size w={d.bbox_w}, h={d.bbox_h}")

    if invalid_range == 0:
        r.ok(f"All {len(dets)} bboxes in valid [0,1] range")
    else:
        r.fail(f"{invalid_range} bboxes have values outside [0,1]")

    if zero_size == 0:
        r.ok(f"All {len(dets)} bboxes have positive dimensions")
    else:
        r.fail(f"{zero_size} bboxes have zero/negative width or height")

    return r


async def check_species_labels(db: AsyncSession) -> VerificationResult:
    """Verify species labels match known AWC135 labels file."""
    r = VerificationResult("Species label validation")

    labels_path = settings.AWC135_LABELS_PATH
    known_labels: set[str] = set()
    if labels_path.exists():
        with open(labels_path, "r", encoding="utf-8-sig") as f:
            known_labels = {line.strip() for line in f if line.strip() and not line.startswith("#")}
        r.ok(f"Loaded {len(known_labels)} known labels from {labels_path.name}")
    else:
        r.warn(f"Labels file not found at {labels_path}")
        return r

    query = select(Detection.species).where(Detection.species.isnot(None)).distinct()
    db_species = [row[0] for row in (await db.execute(query)).all()]

    unknown = [s for s in db_species if s not in known_labels]
    if unknown:
        r.warn(f"{len(unknown)} species in DB not in labels.txt: {unknown[:5]}")
    else:
        r.ok(f"All {len(db_species)} species in DB match labels.txt")

    return r


async def check_empty_images(db: AsyncSession) -> VerificationResult:
    """Verify empty images are correctly marked."""
    r = VerificationResult("Empty image consistency")

    marked_empty = (await db.execute(
        select(func.count(Image.id)).where(Image.has_animal == False)  # noqa: E712
    )).scalar() or 0
    marked_animal = (await db.execute(
        select(func.count(Image.id)).where(Image.has_animal == True)  # noqa: E712
    )).scalar() or 0

    # Images marked has_animal=True should have at least one detection
    animal_no_det = (await db.execute(
        select(func.count(Image.id))
        .where(Image.has_animal == True)  # noqa: E712
        .where(~Image.id.in_(select(Detection.image_id).distinct()))
    )).scalar() or 0

    r.ok(f"Empty images: {marked_empty}, Images with animal: {marked_animal}")
    if animal_no_det == 0:
        r.ok("All animal-flagged images have at least one detection")
    else:
        r.fail(f"{animal_no_det} images marked has_animal=True but have no detections")

    return r


async def check_crop_files(db: AsyncSession) -> VerificationResult:
    """Verify crop files referenced in DB actually exist on disk."""
    r = VerificationResult("Crop file existence")

    dets_with_crop = (await db.execute(
        select(Detection).where(Detection.crop_path.isnot(None))
    )).scalars().all()

    if not dets_with_crop:
        r.warn("No detections have crop paths")
        return r

    missing = 0
    for d in dets_with_crop:
        full_path = settings.STORAGE_ROOT / d.crop_path
        if not full_path.exists():
            missing += 1

    if missing == 0:
        r.ok(f"All {len(dets_with_crop)} crop files exist on disk")
    else:
        r.fail(f"{missing}/{len(dets_with_crop)} crop files missing from disk")

    return r


async def check_confidence_distribution(db: AsyncSession) -> VerificationResult:
    """Report detection and classification confidence statistics."""
    r = VerificationResult("Confidence statistics")

    det_avg = (await db.execute(select(func.avg(Detection.detection_confidence)))).scalar()
    cls_avg = (await db.execute(
        select(func.avg(Detection.classification_confidence)).where(Detection.classification_confidence.isnot(None))
    )).scalar()

    det_min = (await db.execute(select(func.min(Detection.detection_confidence)))).scalar()
    det_max = (await db.execute(select(func.max(Detection.detection_confidence)))).scalar()

    if det_avg is not None:
        r.ok(f"Detection confidence: avg={det_avg:.3f}, min={det_min:.3f}, max={det_max:.3f}")
    else:
        r.warn("No detection confidence data")

    if cls_avg is not None:
        r.ok(f"Classification confidence: avg={cls_avg:.3f}")
    else:
        r.warn("No classification confidence data")

    # Species distribution
    query = (
        select(Detection.species, func.count(Detection.id))
        .where(Detection.species.isnot(None))
        .group_by(Detection.species)
        .order_by(func.count(Detection.id).desc())
        .limit(10)
    )
    rows = (await db.execute(query)).all()
    if rows:
        r.ok("Top species by detection count:")
        for species, count in rows:
            r.details.append(f"    {count:>6}  {species}")

    return r


async def run_verification(verbose: bool = False):
    """Run all verification checks."""
    print("=" * 60)
    print("Wildlife AI Platform — Pipeline Verification")
    print("=" * 60)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    checks = []
    async with async_session_factory() as db:
        checks.append(await check_database_basics(db))
        checks.append(await check_bbox_validity(db, verbose))
        checks.append(await check_species_labels(db))
        checks.append(await check_empty_images(db))
        checks.append(await check_crop_files(db))
        checks.append(await check_confidence_distribution(db))

    total_pass = sum(c.passed for c in checks)
    total_fail = sum(c.failed for c in checks)
    total_warn = sum(c.warnings for c in checks)

    for c in checks:
        status = "PASS" if c.failed == 0 else "FAIL"
        print(f"\n[{status}] {c.name} ({c.passed} ok, {c.failed} fail, {c.warnings} warn)")
        for detail in c.details:
            print(detail)

    print("\n" + "=" * 60)
    print(f"Totals: {total_pass} passed, {total_fail} failed, {total_warn} warnings")
    if total_fail == 0:
        print("Pipeline verification PASSED")
    else:
        print("Pipeline verification FAILED — see details above")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify ML pipeline outputs")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_verification(verbose=args.verbose))

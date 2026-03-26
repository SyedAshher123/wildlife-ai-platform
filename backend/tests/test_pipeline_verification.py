"""Tests for pipeline data consistency — verifies DB invariants hold."""
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.image import Image
from backend.app.models.detection import Detection


@pytest.mark.asyncio
async def test_bbox_values_in_range(db: AsyncSession, sample_data):
    """All bounding box values should be in [0, 1]."""
    dets = (await db.execute(select(Detection))).scalars().all()
    for d in dets:
        assert 0 <= d.bbox_x <= 1, f"bbox_x out of range: {d.bbox_x}"
        assert 0 <= d.bbox_y <= 1, f"bbox_y out of range: {d.bbox_y}"
        assert 0 < d.bbox_w <= 1, f"bbox_w out of range: {d.bbox_w}"
        assert 0 < d.bbox_h <= 1, f"bbox_h out of range: {d.bbox_h}"


@pytest.mark.asyncio
async def test_animal_images_have_detections(db: AsyncSession, sample_data):
    """Every image with has_animal=True should have at least one detection."""
    animal_imgs = (await db.execute(
        select(Image).where(Image.has_animal == True)  # noqa: E712
    )).scalars().all()

    for img in animal_imgs:
        det_count = (await db.execute(
            select(func.count(Detection.id)).where(Detection.image_id == img.id)
        )).scalar() or 0
        assert det_count > 0, f"Image {img.id} marked has_animal=True but has 0 detections"


@pytest.mark.asyncio
async def test_empty_images_have_no_detections(db: AsyncSession, sample_data):
    """Images with has_animal=False should have no detections."""
    empty_imgs = (await db.execute(
        select(Image).where(Image.has_animal == False)  # noqa: E712
    )).scalars().all()

    for img in empty_imgs:
        det_count = (await db.execute(
            select(func.count(Detection.id)).where(Detection.image_id == img.id)
        )).scalar() or 0
        assert det_count == 0, f"Image {img.id} marked has_animal=False but has {det_count} detections"


@pytest.mark.asyncio
async def test_detection_confidence_positive(db: AsyncSession, sample_data):
    """Detection and classification confidence should be positive."""
    dets = (await db.execute(select(Detection))).scalars().all()
    for d in dets:
        assert d.detection_confidence > 0, f"Detection {d.id} has non-positive detection_confidence"
        if d.classification_confidence is not None:
            assert d.classification_confidence >= 0, f"Detection {d.id} has negative classification_confidence"


@pytest.mark.asyncio
async def test_species_populated_for_animal_detections(db: AsyncSession, sample_data):
    """Animal detections should have a species label."""
    dets = (await db.execute(
        select(Detection).where(Detection.category == "animal")
    )).scalars().all()
    for d in dets:
        assert d.species is not None, f"Detection {d.id} is 'animal' but has no species"
        assert len(d.species) > 0, f"Detection {d.id} has empty species string"


@pytest.mark.asyncio
async def test_processed_images_have_has_animal_set(db: AsyncSession, sample_data):
    """Processed images must have has_animal set to True or False (not None)."""
    imgs = (await db.execute(
        select(Image).where(Image.processed == True)  # noqa: E712
    )).scalars().all()
    for img in imgs:
        assert img.has_animal is not None, f"Image {img.id} is processed but has_animal is None"

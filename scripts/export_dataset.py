"""
Dataset Export CLI Tool
=======================
Export detections, crops, and metadata to files for researcher use.

Usage:
    python -m scripts.export_dataset --species quoll --format csv --output exports/
    python -m scripts.export_dataset --all --format json --output exports/
"""
import asyncio
import argparse
import csv
import json
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.config import settings
from backend.app.db.session import async_session_factory, engine
from backend.app.db.base import Base
from backend.app.models.image import Image
from backend.app.models.detection import Detection
from backend.app.models.annotation import Annotation
from backend.app.models.camera import Camera


async def export_detections(
    output_dir: Path,
    species_filter: str | None = None,
    min_confidence: float = 0.0,
    fmt: str = "csv",
    copy_crops: bool = False,
):
    """Export detection records and optionally copy crop files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_session_factory() as db:
        query = (
            select(Detection)
            .options(
                selectinload(Detection.image).selectinload(Image.camera),
                selectinload(Detection.annotations),
            )
            .order_by(Detection.id)
        )
        if species_filter:
            query = query.where(Detection.species.ilike(f"%{species_filter}%"))
        if min_confidence > 0:
            query = query.where(Detection.classification_confidence >= min_confidence)

        dets = (await db.execute(query)).scalars().all()
        print(f"Found {len(dets)} detections")

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
                "bbox": f"{d.bbox_x},{d.bbox_y},{d.bbox_w},{d.bbox_h}",
                "model_version": d.model_version,
                "crop_path": d.crop_path,
                "annotation_correct": ann.is_correct if ann else None,
                "annotation_species": ann.corrected_species if ann else None,
                "annotation_individual": ann.individual_id if ann else None,
                "flagged_retraining": ann.flag_for_retraining if ann else None,
            })

        if fmt == "csv":
            out_file = output_dir / "detections.csv"
            if rows:
                with open(out_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            print(f"Wrote {out_file} ({len(rows)} rows)")
        else:
            out_file = output_dir / "detections.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, default=str)
            print(f"Wrote {out_file} ({len(rows)} records)")

        if copy_crops:
            crops_dir = output_dir / "crops"
            crops_dir.mkdir(exist_ok=True)
            copied = 0
            for d in dets:
                if d.crop_path:
                    src = settings.STORAGE_ROOT / d.crop_path
                    if src.exists():
                        dest = crops_dir / Path(d.crop_path).name
                        shutil.copy2(src, dest)
                        copied += 1
            print(f"Copied {copied} crop files to {crops_dir}")


async def main(args):
    print("=" * 60)
    print("Wildlife AI Platform — Dataset Export")
    print("=" * 60)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await export_detections(
        output_dir=Path(args.output),
        species_filter=args.species if not args.all else None,
        min_confidence=args.min_confidence,
        fmt=args.format,
        copy_crops=args.crops,
    )

    print("\nExport complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export wildlife detection dataset")
    parser.add_argument("--species", type=str, default="quoll", help="Species filter (default: quoll)")
    parser.add_argument("--all", action="store_true", help="Export all species (ignore --species)")
    parser.add_argument("--min-confidence", type=float, default=0.0, help="Minimum classification confidence")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    parser.add_argument("--output", type=str, default="exports", help="Output directory")
    parser.add_argument("--crops", action="store_true", help="Also copy crop image files")
    args = parser.parse_args()

    asyncio.run(main(args))

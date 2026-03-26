"""
Bulk Import Script
==================
Scans the dataset folder structure, registers cameras/collections/images in the DB,
and loads ground-truth quoll sightings from the CSV file.

Usage:
    python -m scripts.bulk_import
    python -m scripts.bulk_import --dry-run --limit 100
"""
import asyncio
import argparse
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import engine, async_session_factory
from backend.app.db.base import Base

# Import models
from backend.app.models.camera import Camera
from backend.app.models.collection import Collection
from backend.app.models.image import Image
from backend.app.models.individual import Individual
from backend.app.models.sighting import Sighting


def parse_camera_folder_name(folder_name: str) -> dict:
    """
    Parse camera folder names like '1A_11-10-23', '4A-12-10-23', '23A_12-10-23'.
    Returns dict with camera_number, side, date.
    """
    # Match patterns: NUM + SIDE + separator + DATE
    pattern = r"^(\d+)([AB])[-_](\d{2}-\d{2}-\d{2,4})$"
    match = re.match(pattern, folder_name)
    if match:
        cam_num = int(match.group(1))
        side = match.group(2)
        date_str = match.group(3)
        try:
            if len(date_str) == 8:  # dd-mm-yy
                date = datetime.strptime(date_str, "%d-%m-%y").date()
            else:
                date = datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            date = None
        return {"camera_number": cam_num, "side": side, "date": date, "name": f"{cam_num}{side}"}
    return None


def parse_collection_folder_name(folder_name: str) -> dict:
    """
    Parse collection folder names like 'Collection-1_11-10-2023'.
    Returns dict with collection_number, date.
    """
    pattern = r"^Collection-(\d+)_(\d{2}-\d{2}-\d{4})$"
    match = re.match(pattern, folder_name)
    if match:
        num = int(match.group(1))
        date_str = match.group(2)
        try:
            date = datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            date = None
        return {"collection_number": num, "date": date}
    return None


async def scan_dataset(
    db: AsyncSession,
    dataset_root: Path,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """Walk the dataset folder structure and register everything in the DB."""
    stats = {
        "cameras_created": 0,
        "collections_created": 0,
        "images_registered": 0,
        "errors": [],
    }

    camera_cache = {}  # name -> Camera object
    collection_cache = {}  # name -> Collection object

    photos_dir = dataset_root / "MORTON NP PHOTOS"
    if not photos_dir.exists():
        stats["errors"].append(f"Photos directory not found: {photos_dir}")
        return stats

    # Get all collection folders
    collection_folders = sorted([
        f for f in photos_dir.iterdir()
        if f.is_dir() and f.name.startswith("Collection-")
    ])

    total_images = 0

    for coll_folder in collection_folders:
        coll_info = parse_collection_folder_name(coll_folder.name)
        if not coll_info:
            stats["errors"].append(f"Could not parse collection folder: {coll_folder.name}")
            continue

        # Create or get collection
        if coll_folder.name not in collection_cache:
            existing = (await db.execute(
                select(Collection).where(Collection.name == coll_folder.name)
            )).scalar_one_or_none()

            if existing:
                collection_cache[coll_folder.name] = existing
            elif not dry_run:
                coll = Collection(
                    name=coll_folder.name,
                    collection_number=coll_info["collection_number"],
                    date_collected=coll_info["date"],
                    folder_path=str(coll_folder.relative_to(dataset_root)),
                )
                db.add(coll)
                await db.flush()
                collection_cache[coll_folder.name] = coll
                stats["collections_created"] += 1

        # Get all camera folders in this collection
        camera_folders = sorted([
            f for f in coll_folder.iterdir() if f.is_dir()
        ])

        for cam_folder in camera_folders:
            cam_info = parse_camera_folder_name(cam_folder.name)
            if not cam_info:
                stats["errors"].append(f"Could not parse camera folder: {cam_folder.name}")
                continue

            cam_name = cam_info["name"]

            # Create or get camera
            if cam_name not in camera_cache:
                existing = (await db.execute(
                    select(Camera).where(Camera.name == cam_name)
                )).scalar_one_or_none()

                if existing:
                    camera_cache[cam_name] = existing
                elif not dry_run:
                    cam = Camera(
                        name=cam_name,
                        camera_number=cam_info["camera_number"],
                        side=cam_info["side"],
                    )
                    db.add(cam)
                    await db.flush()
                    camera_cache[cam_name] = cam
                    stats["cameras_created"] += 1

            # Walk all image files (including subfolders)
            image_files = []
            for root, dirs, files in os.walk(cam_folder):
                for fname in files:
                    ext = os.path.splitext(fname)[1]
                    if ext.lower() in [".jpg", ".jpeg", ".png"]:
                        image_files.append(Path(root) / fname)

            for img_path in image_files:
                if limit and total_images >= limit:
                    break

                rel_path = str(img_path.relative_to(dataset_root))

                if not dry_run:
                    # Check if already registered
                    existing_img = (await db.execute(
                        select(Image.id).where(Image.file_path == rel_path)
                    )).scalar_one_or_none()

                    if not existing_img:
                        img = Image(
                            filename=img_path.name,
                            file_path=rel_path,
                            camera_id=camera_cache.get(cam_name, None) and camera_cache[cam_name].id,
                            collection_id=collection_cache.get(coll_folder.name, None) and collection_cache[coll_folder.name].id,
                        )
                        db.add(img)
                        stats["images_registered"] += 1

                total_images += 1

                # Commit in batches to avoid memory issues
                if not dry_run and total_images % 5000 == 0:
                    await db.commit()
                    print(f"  Committed {total_images} images...")

            if limit and total_images >= limit:
                break
        if limit and total_images >= limit:
            break

    if not dry_run:
        await db.commit()

    if dry_run:
        stats["images_registered"] = total_images

    return stats


async def load_csv_ground_truth(
    db: AsyncSession,
    csv_path: Path,
    dry_run: bool = False,
) -> dict:
    """Load quoll sighting records from CSV and link to images/individuals."""
    stats = {
        "csv_sightings_loaded": 0,
        "individuals_created": 0,
        "errors": [],
    }

    if not csv_path.exists():
        stats["errors"].append(f"CSV not found: {csv_path}")
        return stats

    df = pd.read_csv(csv_path)
    print(f"  CSV loaded: {len(df)} rows")

    individual_cache = {}  # individual_id string -> Individual object

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Loading CSV"):
        try:
            ind_id = str(row.get("individual_id", "")).strip()
            filename = str(row.get("filename", "")).strip()
            identified_by = str(row.get("identified_by", "")).strip()
            camera_id_csv = str(row.get("camera_id", "")).strip()
            collection_name = str(row.get("collection_id", "")).strip()
            timestamp_str = str(row.get("timestamp", "")).strip()

            if not ind_id or not filename:
                continue

            # Parse timestamp
            captured_at = None
            try:
                captured_at = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M")
            except (ValueError, TypeError):
                pass

            if dry_run:
                stats["csv_sightings_loaded"] += 1
                continue

            # Create or get individual
            if ind_id not in individual_cache:
                existing_ind = (await db.execute(
                    select(Individual).where(Individual.individual_id == ind_id)
                )).scalar_one_or_none()

                if existing_ind:
                    individual_cache[ind_id] = existing_ind
                else:
                    ind = Individual(
                        individual_id=ind_id,
                        species=str(row.get("common_name", "Spotted-tailed Quoll")),
                    )
                    db.add(ind)
                    await db.flush()
                    individual_cache[ind_id] = ind
                    stats["individuals_created"] += 1

            # Find matching image in DB
            image_query = select(Image).where(Image.filename == filename)
            if collection_name:
                image_query = image_query.join(
                    Collection, Collection.id == Image.collection_id
                ).where(Collection.name == collection_name)

            img = (await db.execute(image_query)).scalar_one_or_none()

            if img:
                # Update image captured_at if we have it
                if captured_at and not img.captured_at:
                    img.captured_at = captured_at

                # Create sighting
                existing_sighting = (await db.execute(
                    select(Sighting).where(
                        Sighting.individual_id == individual_cache[ind_id].id,
                        Sighting.image_id == img.id,
                    )
                )).scalar_one_or_none()

                if not existing_sighting:
                    sighting = Sighting(
                        individual_id=individual_cache[ind_id].id,
                        image_id=img.id,
                        identified_by=identified_by,
                        source="csv_import",
                    )
                    db.add(sighting)
                    stats["csv_sightings_loaded"] += 1

                    # Update individual timestamps
                    ind_obj = individual_cache[ind_id]
                    if captured_at:
                        if not ind_obj.first_seen or captured_at < ind_obj.first_seen:
                            ind_obj.first_seen = captured_at
                        if not ind_obj.last_seen or captured_at > ind_obj.last_seen:
                            ind_obj.last_seen = captured_at
                    ind_obj.total_sightings = (ind_obj.total_sightings or 0) + 1

        except Exception as e:
            stats["errors"].append(f"Row error: {e}")

        # Commit in batches
        if not dry_run and stats["csv_sightings_loaded"] % 1000 == 0 and stats["csv_sightings_loaded"] > 0:
            await db.commit()

    if not dry_run:
        await db.commit()

    return stats


async def run_import(dry_run: bool = False, limit: int | None = None):
    """Main import routine."""
    print("=" * 60)
    print("Wildlife AI Platform — Bulk Import")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Step 1: Scan dataset folders
        print("\n📁 Scanning dataset folder structure...")
        scan_stats = await scan_dataset(db, settings.DATASET_ROOT, dry_run=dry_run, limit=limit)
        print(f"  Cameras: {scan_stats['cameras_created']}")
        print(f"  Collections: {scan_stats['collections_created']}")
        print(f"  Images: {scan_stats['images_registered']}")
        if scan_stats["errors"]:
            print(f"  Errors: {len(scan_stats['errors'])}")
            for err in scan_stats["errors"][:5]:
                print(f"    ⚠️ {err}")

        # Step 2: Load CSV ground truth
        csv_path = settings.DATASET_ROOT / "stq-morton-data-cleaned.csv"
        print(f"\n📊 Loading CSV ground truth from {csv_path.name}...")
        csv_stats = await load_csv_ground_truth(db, csv_path, dry_run=dry_run)
        print(f"  Sightings loaded: {csv_stats['csv_sightings_loaded']}")
        print(f"  Individuals created: {csv_stats['individuals_created']}")
        if csv_stats["errors"]:
            print(f"  Errors: {len(csv_stats['errors'])}")
            for err in csv_stats["errors"][:5]:
                print(f"    ⚠️ {err}")

    # Step 3: Update camera GPS from CSV data
    async with async_session_factory() as db:
        csv_path = settings.DATASET_ROOT / "stq-morton-data-cleaned.csv"
        if csv_path.exists() and not dry_run:
            print("\n🌍 Updating camera GPS coordinates from CSV...")
            df = pd.read_csv(csv_path)
            gps_data = df.groupby("camera_id").agg({
                "latitude": "first",
                "longitude": "first",
                "elevation": "first",
            }).reset_index()

            updated = 0
            for _, row in gps_data.iterrows():
                cam_num = int(row["camera_id"])
                # Find cameras with this number (both A and B sides)
                cams = (await db.execute(
                    select(Camera).where(Camera.camera_number == cam_num)
                )).scalars().all()

                for cam in cams:
                    if cam.latitude is None:
                        cam.latitude = row["latitude"]
                        cam.longitude = row["longitude"]
                        cam.elevation = row["elevation"]
                        updated += 1

            await db.commit()
            print(f"  Updated GPS for {updated} cameras")

    print("\n" + "=" * 60)
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}✅ Import complete!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk import camera trap dataset")
    parser.add_argument("--dry-run", action="store_true", help="Scan without writing to DB")
    parser.add_argument("--limit", type=int, default=None, help="Max images to process")
    args = parser.parse_args()

    asyncio.run(run_import(dry_run=args.dry_run, limit=args.limit))

"""
Pipeline Test Script
====================
Tests the MegaDetector → crop → AWC135 pipeline on a small sample of
images from the dataset. Does NOT write to the database.

Usage (from project root, in the 'wildlife' conda env):
    python -m scripts.test_pipeline
    python -m scripts.test_pipeline --n 10 --verbose
    python -m scripts.test_pipeline --image "path/to/single/image.jpg"
"""
import argparse
import time
import random
from pathlib import Path

from backend.app.config import settings
from backend.worker.pipelines.megadetector_pipeline import MegaDetectorPipeline
from backend.worker.pipelines.awc135_pipeline import AWC135Pipeline


def find_sample_images(n: int = 5) -> list[Path]:
    """Pick n random images from the dataset folder."""
    photos_dir = settings.DATASET_ROOT / "MORTON NP PHOTOS"
    if not photos_dir.exists():
        raise FileNotFoundError(f"Dataset not found at: {photos_dir}")

    all_images = list(photos_dir.rglob("*.JPG")) + list(photos_dir.rglob("*.jpg"))
    if not all_images:
        raise FileNotFoundError(f"No images found in {photos_dir}")

    random.shuffle(all_images)
    return all_images[:n]


def run_test(image_paths: list[Path], verbose: bool = False):
    """Run the full pipeline on a list of images and print results."""
    print("=" * 60)
    print("Wildlife AI Platform — Pipeline Test")
    print("=" * 60)
    print(f"Target species: {settings.TARGET_SPECIES}")
    print(f"Detection threshold:     {settings.DETECTION_CONFIDENCE_THRESHOLD}")
    print(f"Classification threshold:{settings.CLASSIFICATION_CONFIDENCE_THRESHOLD}")
    print()

    # Load models
    print("Loading models...")
    md_pipeline = MegaDetectorPipeline()
    awc_pipeline = AWC135Pipeline()

    t0 = time.time()
    md_pipeline.load_model()
    print(f"  MegaDetector ready  ({time.time() - t0:.1f}s)")

    t0 = time.time()
    awc_pipeline.load_model()
    print(f"  AWC135 ready        ({time.time() - t0:.1f}s)")
    print()

    # Process images
    stats = {"total": 0, "animal": 0, "empty": 0, "quoll": 0, "errors": 0}
    quoll_detections = []

    print(f"Processing {len(image_paths)} images...\n")
    pipeline_start = time.time()

    for img_path in image_paths:
        stats["total"] += 1
        short = img_path.name

        try:
            detections = md_pipeline.detect_single(img_path)
            animal_dets = [d for d in detections if d["category"] == "animal"]

            if not animal_dets:
                stats["empty"] += 1
                if verbose:
                    print(f"  [empty] {short}")
                continue

            stats["animal"] += 1

            for i, det in enumerate(animal_dets):
                classification = awc_pipeline.classify_single(
                    img_path,
                    bbox=det["bbox"],
                    bbox_conf=det["confidence"],
                )

                species = classification.get("species", "unknown")
                conf = classification.get("confidence", 0.0)
                is_quoll = awc_pipeline.is_target_species(classification)

                if is_quoll:
                    stats["quoll"] += 1
                    quoll_detections.append({
                        "image": str(img_path),
                        "species": species,
                        "confidence": conf,
                        "bbox": det["bbox"],
                    })

                if verbose or is_quoll:
                    flag = "🐾 QUOLL" if is_quoll else "      "
                    print(f"  {flag} {short} | det{i}: {species} ({conf:.2f})")
                    if classification.get("top5"):
                        for label, prob in classification["top5"][1:3]:
                            print(f"           alt: {label} ({prob:.2f})")

        except Exception as e:
            stats["errors"] += 1
            print(f"  [ERROR] {short}: {e}")

    elapsed = time.time() - pipeline_start

    # Summary
    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    print(f"  Images tested  : {stats['total']}")
    print(f"  With animal    : {stats['animal']}")
    print(f"  Empty (no det) : {stats['empty']}")
    print(f"  Quoll detected : {stats['quoll']}")
    print(f"  Errors         : {stats['errors']}")
    print(f"  Time elapsed   : {elapsed:.1f}s  ({stats['total']/elapsed:.1f} img/s)")

    if quoll_detections:
        print()
        print("Quoll detections:")
        for q in quoll_detections:
            print(f"  {Path(q['image']).name}  conf={q['confidence']:.2f}")

    print()
    if stats["animal"] > 0 or stats["total"] == stats["empty"]:
        print("Pipeline test PASSED — models loaded and ran successfully.")
    else:
        print("WARNING: All images had errors. Check model paths.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the ML detection pipeline")
    parser.add_argument("--n", type=int, default=5, help="Number of random images to test")
    parser.add_argument("--image", type=str, default=None, help="Test a specific image file")
    parser.add_argument("--dir", type=str, default=None, help="Run pipeline on all images in a directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print results for every detection")
    args = parser.parse_args()

    if args.image:
        images = [Path(args.image)]

    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        images = list(dir_path.rglob("*.JPG")) + list(dir_path.rglob("*.jpg"))
        print(f"Found {len(images)} images in {dir_path}")

    else:
        print(f"Picking {args.n} random images from dataset...")
        images = find_sample_images(args.n)
        for img in images:
            print(f"  {img.relative_to(settings.DATASET_ROOT)}")
        print()

    run_test(images, verbose=args.verbose)

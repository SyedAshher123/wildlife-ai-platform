"""
MegaDetector Pipeline
=====================
Wraps MegaDetector v5a for animal detection using the megadetector package.
Returns normalized bounding boxes [x, y, w, h] for detected animals.
"""
import torch
from pathlib import Path
from PIL import Image
from typing import Optional

from backend.app.config import settings


class MegaDetectorPipeline:
    """MegaDetector v5a wrapper for animal detection."""

    CATEGORIES = {"1": "animal", "2": "person", "3": "vehicle"}

    def __init__(self, model_path: Optional[Path] = None, device: Optional[str] = None):
        self.model_path = model_path or settings.MEGADETECTOR_MODEL_PATH
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.confidence_threshold = settings.DETECTION_CONFIDENCE_THRESHOLD

    def load_model(self):
        """Load MegaDetector v5a via the megadetector package."""
        if self.model is not None:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"MegaDetector weights not found at {self.model_path}.\n"
                f"Expected: C:/Users/Admin/ml_models/megadetector/md_v5a.0.0.pt"
            )

        from megadetector.detection.run_detector import load_detector
        print(f"Loading MegaDetector from {self.model_path.name} on {self.device}...")
        self.model = load_detector(str(self.model_path))
        print(f"MegaDetector loaded OK")

    def detect_single(self, image_path: str | Path) -> list[dict]:
        """
        Run MegaDetector on a single image.

        Returns list of animal detections:
        [{"bbox": [x, y, w, h], "confidence": 0.95, "category": "animal"}]
        Bbox values are normalized 0-1.
        """
        self.load_model()
        image_path = Path(image_path)

        with Image.open(image_path) as img:
            img.load()
            result = self.model.generate_detections_one_image(
                img,
                str(image_path),
                detection_threshold=self.confidence_threshold,
            )

        detections = []
        for det in result.get("detections") or []:
            conf = det.get("conf", 0.0)
            if conf < self.confidence_threshold:
                continue
            category = self.CATEGORIES.get(str(det.get("category", "1")), "unknown")
            detections.append({
                "bbox": list(det["bbox"]),  # [x, y, w, h] normalized
                "confidence": float(conf),
                "category": category,
            })

        return detections

    def detect_batch(self, image_paths: list[str | Path]) -> list[list[dict]]:
        """Run MegaDetector on a list of images, returning one result list per image."""
        self.load_model()
        results = []
        for path in image_paths:
            try:
                results.append(self.detect_single(path))
            except Exception as e:
                print(f"  Warning: error processing {path}: {e}")
                results.append([])
        return results

    def crop_detection(
        self,
        image_path: str | Path,
        bbox: list[float],
        output_path: str | Path,
        padding: float = 0.05,
    ) -> Path:
        """
        Crop a bounding box from an image and save it for the annotation UI.

        Args:
            image_path: Source image path
            bbox: [x, y, w, h] normalized 0-1 (MegaDetector format)
            output_path: Where to save the crop
            padding: Extra padding fraction around the bbox

        Returns:
            Path to the saved crop file
        """
        img = Image.open(image_path)
        w_img, h_img = img.size

        x, y, w, h = bbox
        pad_x = w * padding
        pad_y = h * padding

        x1 = max(0, int((x - pad_x) * w_img))
        y1 = max(0, int((y - pad_y) * h_img))
        x2 = min(w_img, int((x + w + pad_x) * w_img))
        y2 = min(h_img, int((y + h + pad_y) * h_img))

        crop = img.crop((x1, y1, x2, y2))

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(str(output_path), quality=95)
        img.close()

        return output_path

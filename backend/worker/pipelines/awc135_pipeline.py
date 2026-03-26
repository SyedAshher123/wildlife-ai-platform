"""
AWC135 Species Classification Pipeline
=======================================
Wraps awc_helpers.SpeciesClasInference to classify animal crops.
The AWC135 model uses tf_efficientnet_b5 trained on 135 Australian species.

Label format in labels.txt: "Scientific name | Common name"
Target species entry: "Dasyurus sp | Quoll sp"
"""
from pathlib import Path
from typing import Optional, Union

from backend.app.config import settings


class AWC135Pipeline:
    """AWC135 species classifier wrapper using awc_helpers.SpeciesClasInference."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        labels_path: Optional[Path] = None,
        device: Optional[str] = None,
    ):
        self.model_path = model_path or settings.AWC135_MODEL_PATH
        self.labels_path = labels_path or settings.AWC135_LABELS_PATH
        self.classifier_base = settings.AWC135_CLASSIFIER_BASE
        self.device = device  # None = auto (cuda if available)
        self.classifier = None  # SpeciesClasInference instance
        self.labels: list[str] = []
        self.confidence_threshold = settings.CLASSIFICATION_CONFIDENCE_THRESHOLD

    def load_model(self):
        """Load AWC135 classifier via awc_helpers.SpeciesClasInference."""
        if self.classifier is not None:
            return

        from awc_helpers import SpeciesClasInference

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"AWC135 weights not found at {self.model_path}.\n"
                f"Expected: C:/Users/Admin/ml_models/awc135/awc-135-v1.pth"
            )

        if not self.labels_path.exists():
            raise FileNotFoundError(
                f"AWC135 labels not found at {self.labels_path}.\n"
                f"Expected: C:/Users/Admin/ml_models/awc135/labels.txt"
            )

        with open(self.labels_path, "r", encoding="utf-8-sig") as f:
            self.labels = [
                line.strip() for line in f
                if line.strip() and not line.startswith("#")
            ]
        print(f"  Loaded {len(self.labels)} species labels")

        force_cpu = (self.device == "cpu")
        self.classifier = SpeciesClasInference(
            classifier_path=str(self.model_path),
            classifier_base=self.classifier_base,
            label_names=self.labels,
            clas_threshold=0.0,   # Return all top-N; we apply threshold ourselves
            force_cpu=force_cpu,
            skip_errors=True,
        )
        print(f"AWC135 loaded: {self.model_path.name}")

    def classify_single(
        self,
        image_path: Union[str, Path],
        bbox: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
        bbox_conf: float = 1.0,
        top_n: int = 5,
    ) -> dict:
        """
        Classify an image (or crop) using AWC135.

        For pre-cropped images, leave bbox as default (full image).
        For original images with a bounding box, pass the bbox from MegaDetector.

        Args:
            image_path: Path to image file
            bbox: [x, y, w, h] normalized 0-1 (default = whole image)
            bbox_conf: MegaDetector detection confidence for this bbox
            top_n: Number of top predictions to return

        Returns:
            {
                "species": "Dasyurus sp | Quoll sp",
                "confidence": 0.87,
                "top5": [("Dasyurus sp | Quoll sp", 0.87), ...]
            }
        """
        self.load_model()

        try:
            results = self.classifier.predict_batch(
                inputs=[(str(image_path), float(bbox_conf), tuple(bbox))],
                pred_topn=top_n,
                batch_size=1,
                show_progress=False,
            )

            if not results:
                return {"species": None, "confidence": 0.0, "top5": []}

            # Result tuple: (identifier, bbox_conf, bbox, label1, prob1, label2, prob2, ...)
            row = results[0]
            top5 = []
            i = 3  # Labels/probs start at index 3
            while i + 1 < len(row):
                top5.append((row[i], float(row[i + 1])))
                i += 2

            if not top5:
                return {"species": None, "confidence": 0.0, "top5": []}

            best_species, best_conf = top5[0]
            return {
                "species": best_species,
                "confidence": best_conf,
                "top5": top5,
            }

        except Exception as e:
            return {
                "species": None,
                "confidence": 0.0,
                "top5": [],
                "error": str(e),
            }

    def classify_batch(
        self,
        inputs: list[tuple],  # [(image_path, bbox_conf, bbox), ...]
        top_n: int = 5,
        batch_size: int = 4,
    ) -> list[dict]:
        """
        Classify a batch of images efficiently.

        Args:
            inputs: List of (image_path, bbox_conf, bbox) tuples
            top_n: Number of top predictions per image
            batch_size: GPU batch size

        Returns:
            List of classification dicts (same format as classify_single)
        """
        self.load_model()

        normalized = [(str(p), float(c), tuple(b)) for p, c, b in inputs]

        try:
            all_results = self.classifier.predict_batch(
                inputs=normalized,
                pred_topn=top_n,
                batch_size=batch_size,
                show_progress=False,
            )
        except Exception as e:
            return [{"species": None, "confidence": 0.0, "top5": [], "error": str(e)}] * len(inputs)

        output = []
        for row in all_results:
            top5 = []
            i = 3
            while i + 1 < len(row):
                top5.append((row[i], float(row[i + 1])))
                i += 2

            if top5:
                output.append({"species": top5[0][0], "confidence": top5[0][1], "top5": top5})
            else:
                output.append({"species": None, "confidence": 0.0, "top5": []})

        return output

    def is_target_species(self, classification: dict) -> bool:
        """Check if the classification matches the target species (quoll)."""
        species = classification.get("species") or ""
        confidence = classification.get("confidence", 0.0)
        target = settings.TARGET_SPECIES.lower()
        return target in species.lower() and confidence >= self.confidence_threshold

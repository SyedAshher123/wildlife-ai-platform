"""
Application configuration using pydantic-settings.
All settings can be overridden via environment variables or .env file.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # --- Project Paths ---
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATASET_ROOT: Path = Path(r"I:/AA-Study/Project321/dataset")
    STORAGE_ROOT: Path = Path(r"I:/AA-Study/Project321/storage")

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./wildlife.db"  # SQLite for dev
    # DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/wildlife"  # Postgres for prod

    # --- ML Models (stored outside project dir, not version-controlled) ---
    MEGADETECTOR_MODEL_PATH: Path = Path(r"C:/Users/Admin/ml_models/megadetector/md_v5a.0.0.pt")
    AWC135_MODEL_PATH: Path = Path(r"C:/Users/Admin/ml_models/awc135/awc-135-v1.pth")
    AWC135_LABELS_PATH: Path = Path(r"C:/Users/Admin/ml_models/awc135/labels.txt")
    AWC135_CLASSIFIER_BASE: str = "tf_efficientnet_b5.ns_jft_in1k"

    # --- Detection Thresholds ---
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.1   # MegaDetector min confidence
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = 0.5  # AWC135 min confidence
    # Matches label format in labels.txt: "Dasyurus sp | Quoll sp"
    TARGET_SPECIES: str = "Quoll"

    # --- Processing ---
    BATCH_SIZE: int = 8  # Images per GPU batch (RTX 3080 10GB safe)
    MAX_WORKERS: int = 4  # CPU workers for I/O
    IMAGE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG"]

    # --- Thumbnails ---
    THUMBNAIL_SIZE: tuple[int, int] = (320, 240)
    THUMBNAIL_QUALITY: int = 85

    # --- API ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ]

    # --- Redis / Celery (for later) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.STORAGE_ROOT / "thumbnails", exist_ok=True)
os.makedirs(settings.STORAGE_ROOT / "crops", exist_ok=True)

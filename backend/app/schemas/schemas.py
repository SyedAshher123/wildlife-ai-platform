"""Pydantic schemas for API request/response models."""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Any


# ---------------------------------------------------------------------------
# Auth / User
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: str = Field(min_length=8)
    role: str = "reviewer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
class CameraBase(BaseModel):
    name: str
    camera_number: Optional[int] = None
    side: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None


class CameraOut(CameraBase):
    id: int
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
class CollectionBase(BaseModel):
    name: str
    collection_number: Optional[int] = None
    date_collected: Optional[datetime] = None


class CollectionOut(CollectionBase):
    id: int
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
class DetectionBase(BaseModel):
    image_id: int
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    detection_confidence: float
    category: Optional[str] = None
    species: Optional[str] = None
    classification_confidence: Optional[float] = None


class DetectionOut(DetectionBase):
    id: int
    model_version: Optional[str] = None
    crop_path: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class DetectionDetail(DetectionOut):
    """Detection with nested image, camera, and annotations."""
    image: Optional["ImageOut"] = None
    camera: Optional[CameraOut] = None
    annotations: list["AnnotationOut"] = []


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------
class AnnotationCreate(BaseModel):
    detection_id: int
    corrected_species: Optional[str] = None
    is_correct: Optional[bool] = None
    notes: Optional[str] = None
    individual_id: Optional[str] = None
    flag_for_retraining: bool = False


class AnnotationUpdate(BaseModel):
    corrected_species: Optional[str] = None
    is_correct: Optional[bool] = None
    notes: Optional[str] = None
    individual_id: Optional[str] = None
    flag_for_retraining: Optional[bool] = None


class AnnotationOut(BaseModel):
    id: int
    detection_id: int
    annotator: Optional[str] = None
    corrected_species: Optional[str] = None
    is_correct: Optional[bool] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------
class ImageBase(BaseModel):
    filename: str
    file_path: str
    camera_id: Optional[int] = None
    collection_id: Optional[int] = None
    captured_at: Optional[datetime] = None


class ImageOut(ImageBase):
    id: int
    width: Optional[int] = None
    height: Optional[int] = None
    processed: bool = False
    has_animal: Optional[bool] = None
    thumbnail_path: Optional[str] = None
    model_config = {"from_attributes": True}


class ImageDetail(ImageOut):
    camera: Optional[CameraOut] = None
    collection: Optional[CollectionOut] = None
    detections: list[DetectionOut] = []


class MissedDetectionCreate(BaseModel):
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    species: str
    flag_for_retraining: bool = True


class MissedDetectionOut(BaseModel):
    id: int
    image_id: int
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    species: str
    annotator: Optional[str] = None
    flag_for_retraining: bool = True
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Individual
# ---------------------------------------------------------------------------
class IndividualBase(BaseModel):
    individual_id: str
    species: str = "Spotted-tailed Quoll"
    name: Optional[str] = None


class IndividualOut(IndividualBase):
    id: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_sightings: int = 0
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Processing Job
# ---------------------------------------------------------------------------
class JobStatus(BaseModel):
    id: int
    batch_name: Optional[str] = None
    status: str
    total_images: int = 0
    processed_images: int = 0
    failed_images: int = 0
    percent: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class BatchUploadResponse(BaseModel):
    job_id: int
    files_received: int
    status: str = "queued"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class ReportOut(BaseModel):
    total_images: int = 0
    processed_images: int = 0
    empty_images: int = 0
    total_detections: int = 0
    total_species: int = 0
    quoll_detections: int = 0
    mean_detection_confidence: Optional[float] = None
    mean_classification_confidence: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    species_distribution: list[dict] = []
    camera_counts: list[dict] = []
    hourly_activity: list[dict] = []


class ExportRequest(BaseModel):
    format: str = "csv"  # csv, json, pdf
    species_filter: Optional[str] = None
    min_confidence: Optional[float] = None
    camera_ids: Optional[list[int]] = None
    collection_ids: Optional[list[int]] = None
    include_annotations: bool = True


# ---------------------------------------------------------------------------
# Dashboard / Stats
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_images: int = 0
    processed_images: int = 0
    unprocessed_images: int = 0
    total_detections: int = 0
    total_animals: int = 0
    quoll_detections: int = 0
    total_individuals: int = 0
    total_cameras: int = 0
    total_collections: int = 0
    processing_percent: float = 0.0
    pending_review: int = 0


# ---------------------------------------------------------------------------
# Import / Pagination
# ---------------------------------------------------------------------------
class ImportResult(BaseModel):
    cameras_created: int = 0
    collections_created: int = 0
    images_registered: int = 0
    csv_sightings_loaded: int = 0
    individuals_created: int = 0
    errors: list[str] = []


class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    per_page: int = 50
    pages: int = 0

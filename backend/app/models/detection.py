"""Detection model — a bounding box + classification from ML pipeline."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.db.base import Base


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (
        Index("idx_detections_species_conf", "species", "classification_confidence"),
    )

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)

    # MegaDetector bounding box (normalized 0-1)
    bbox_x = Column(Float, nullable=False)  # top-left x
    bbox_y = Column(Float, nullable=False)  # top-left y
    bbox_w = Column(Float, nullable=False)  # width
    bbox_h = Column(Float, nullable=False)  # height
    detection_confidence = Column(Float, nullable=False)  # MegaDetector confidence
    category = Column(String, nullable=True)  # "animal", "person", "vehicle"

    # AWC135 classification
    species = Column(String, nullable=True, index=True)
    classification_confidence = Column(Float, nullable=True)

    # Metadata
    model_version = Column(String, nullable=True)  # e.g. "MDv5a+AWC135"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Crop file path
    crop_path = Column(String, nullable=True)

    # Relationships
    image = relationship("Image", back_populates="detections")
    annotations = relationship("Annotation", back_populates="detection", lazy="selectin")
    sightings = relationship("Sighting", back_populates="detection", lazy="selectin")

    def __repr__(self):
        return f"<Detection(id={self.id}, species='{self.species}', conf={self.classification_confidence})>"

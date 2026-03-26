"""Annotation model — human review/correction of a detection."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=False, index=True)
    annotator = Column(String, nullable=True)
    corrected_species = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    notes = Column(String, nullable=True)
    individual_id = Column(String, nullable=True)
    flag_for_retraining = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    detection = relationship("Detection", back_populates="annotations")

    def __repr__(self):
        return f"<Annotation(id={self.id}, detection_id={self.detection_id}, is_correct={self.is_correct})>"

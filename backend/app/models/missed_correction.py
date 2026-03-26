"""User correction when model missed an animal in an image (feedback loop for retraining)."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class MissedDetectionCorrection(Base):
    __tablename__ = "missed_detection_corrections"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)
    bbox_x = Column(Float, nullable=False)  # normalized 0-1 or relative to image
    bbox_y = Column(Float, nullable=False)
    bbox_w = Column(Float, nullable=False)
    bbox_h = Column(Float, nullable=False)
    species = Column(String, nullable=False)
    annotator = Column(String, nullable=True)
    flag_for_retraining = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    image = relationship("Image", backref="missed_corrections")

    def __repr__(self):
        return f"<MissedCorrection(id={self.id}, image_id={self.image_id}, species={self.species})>"

"""Sighting model — links an individual quoll to an image/detection."""
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Sighting(Base):
    __tablename__ = "sightings"

    id = Column(Integer, primary_key=True, index=True)
    individual_id = Column(Integer, ForeignKey("individuals.id"), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=True)
    identified_by = Column(String, nullable=True)  # e.g., "Jordyn Clough"
    source = Column(String, nullable=True)  # "csv_import" or "ml_pipeline"

    # Relationships
    individual = relationship("Individual", back_populates="sightings")
    image = relationship("Image", back_populates="sightings")
    detection = relationship("Detection", back_populates="sightings")

    def __repr__(self):
        return f"<Sighting(individual_id={self.individual_id}, image_id={self.image_id})>"

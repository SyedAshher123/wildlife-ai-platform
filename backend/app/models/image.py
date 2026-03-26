"""Image model — core entity representing a camera trap photo."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (
        Index("idx_images_camera_time", "camera_id", "captured_at"),
        Index("idx_images_processed", "processed", "has_animal"),
    )

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # e.g., "RCNX0001.JPG"
    file_path = Column(String, unique=True, nullable=False)  # full relative path from dataset root
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True, index=True)
    captured_at = Column(DateTime, nullable=True, index=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes
    processed = Column(Boolean, default=False, index=True)
    has_animal = Column(Boolean, nullable=True)  # None = not processed, True/False after MD
    thumbnail_path = Column(String, nullable=True)

    # Relationships
    camera = relationship("Camera", back_populates="images")
    collection = relationship("Collection", back_populates="images")
    detections = relationship("Detection", back_populates="image", lazy="selectin")
    sightings = relationship("Sighting", back_populates="image", lazy="selectin")

    def __repr__(self):
        return f"<Image(id={self.id}, filename='{self.filename}', processed={self.processed})>"

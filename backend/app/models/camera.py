"""Camera trap station model."""
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "1A", "2B"
    camera_number = Column(Integer, nullable=True)  # numeric part, e.g., 1
    side = Column(String(1), nullable=True)  # "A" or "B"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    elevation = Column(Float, nullable=True)

    # Relationships
    images = relationship("Image", back_populates="camera", lazy="selectin")

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}')>"

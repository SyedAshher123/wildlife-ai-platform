"""Collection (field trip) model."""
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "Collection-1_11-10-2023"
    collection_number = Column(Integer, nullable=True)  # e.g., 1
    date_collected = Column(Date, nullable=True)
    folder_path = Column(String, nullable=True)

    # Relationships
    images = relationship("Image", back_populates="collection", lazy="selectin")

    def __repr__(self):
        return f"<Collection(id={self.id}, name='{self.name}')>"

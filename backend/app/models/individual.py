"""Individual quoll model — a specific identified animal."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class Individual(Base):
    __tablename__ = "individuals"

    id = Column(Integer, primary_key=True, index=True)
    individual_id = Column(String, unique=True, nullable=False, index=True)  # e.g., "02Q2", "07Q2"
    species = Column(String, nullable=False, default="Spotted-tailed Quoll")
    name = Column(String, nullable=True)  # optional nickname
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    total_sightings = Column(Integer, default=0)

    # Relationships
    sightings = relationship("Sighting", back_populates="individual", lazy="selectin")

    def __repr__(self):
        return f"<Individual(id={self.id}, individual_id='{self.individual_id}')>"

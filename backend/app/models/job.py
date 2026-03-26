"""ProcessingJob model — tracks async batch processing status."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timezone
from backend.app.db.base import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="queued")  # queued, processing, completed, failed
    total_images = Column(Integer, default=0)
    processed_images = Column(Integer, default=0)
    failed_images = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    celery_task_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, status='{self.status}', {self.processed_images}/{self.total_images})>"

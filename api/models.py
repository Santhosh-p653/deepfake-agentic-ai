from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class ProcessingStatus(enum.Enum):
    pending = "pending"
    temp_stored = "temp_stored"
    processing = "processing"
    processed = "processed"
    completed = "completed"
    failed = "failed"
    deleted = "deleted"

class MediaUpload(Base):
    __tablename__ = "media_uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    size_mb = Column(Float, nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.pending, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    temp_path = Column(String, nullable=True)
    drive_path = Column(String, nullable=True)
    verdict = Column(String, nullable=True)
    verdict_score = Column(Float, nullable=True)
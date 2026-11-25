from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
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

class TestFixture(Base):
    __tablename__ = "test_fixtures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False, unique=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    ground_truth = Column(String, nullable=False)
    predicted_label = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    agent_reasoning = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    verified_result = Column(Boolean, nullable=True)
    evaluation_run_id = Column(String, nullable=True)
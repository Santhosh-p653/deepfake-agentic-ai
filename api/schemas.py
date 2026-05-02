from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    status: str
    id: int
    filename: str
    size_mb: float
    minio_object: str


class ResultResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    size_mb: float
    status: str
    verdict: Optional[str]
    verdict_score: Optional[float]
    uploaded_at: Optional[str]
    processed_at: Optional[str]


class VerdictPayload(BaseModel):
    record_id: int
    verdict: str
    verdict_score: Optional[float]


class HealthResponse(BaseModel):
    status: str
    database: str

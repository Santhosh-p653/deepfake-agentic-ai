from pydantic import BaseModel


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
    verdict: str | None
    verdict_score: float | None
    uploaded_at: str | None
    processed_at: str | None


class VerdictPayload(BaseModel):
    record_id: int
    verdict: str
    verdict_score: float | None


class HealthResponse(BaseModel):
    status: str
    database: str

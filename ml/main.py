import os
import uuid
from pathlib import Path

from fastapi import FastAPI
from minio import Minio

from ml.preprocessing import preprocess
from ml.detection import detect

# ── MinIO configuration ─────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepfakemedia")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

# ── Upload directory (must match preprocessing security rule) ───────
UPLOADS_ROOT = Path("/app/uploads")

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "ml pong"}


@app.post("/process")
def process(payload: dict):
    minio_object = payload.get("minio_object")
    record_id = payload.get("record_id")

    if not minio_object:
        return {"error": "minio_object is required"}

    # Preserve file extension for whitelist validation
    ext = Path(minio_object).suffix.lower() or ".jpg"

    # Generate safe filename inside allowed directory
    filename = f"{uuid.uuid4()}{ext}"
    tmp_path = str(UPLOADS_ROOT / filename)

    try:
        # Download file from MinIO → /app/uploads
        minio_client.fget_object(MINIO_BUCKET, minio_object, tmp_path)

        # Run preprocessing
        preprocessing_signal = preprocess(tmp_path)

        # Run detection using extracted frames
        detection_signal = detect(
            preprocessing_signal.metadata.get("frames", [])
        )

    finally:
        # Cleanup file after processing
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return {
        "record_id": record_id,
        "preprocessing": preprocessing_signal.model_dump(),
        "detection": detection_signal.model_dump(),
    }
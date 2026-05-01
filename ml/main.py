import os
import tempfile
from fastapi import FastAPI
from minio import Minio
from ml.preprocessing import preprocess
from ml.detection import detect

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

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "ml pong"}


@app.post("/process")
def process(payload: dict):
    minio_object = payload.get("minio_object")
    record_id = payload.get("record_id")

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        minio_client.fget_object(MINIO_BUCKET, minio_object, tmp_path)
        preprocessing_signal = preprocess(tmp_path)
        detection_signal = detect(preprocessing_signal.metadata.get("frames", []))
    finally:
        os.unlink(tmp_path)

    return {
        "record_id": record_id,
        "preprocessing": preprocessing_signal.model_dump(),
        "detection": detection_signal.model_dump(),
    }
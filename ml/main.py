import os
import uuid
from pathlib import Path

from fastapi import FastAPI
from minio import Minio

from ml.preprocessing import preprocess
from ml.detection import detect
from shared.logger import get_logger

logger = get_logger("ml.main")

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

UPLOADS_ROOT = Path("/app/uploads")
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".mp4"}

# Fix #4: ensure uploads directory exists at startup
UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI()


@app.get("/ping")
def ping():
    logger.info("Ping received", extra={"status": "success"})
    return {"message": "ml pong"}


@app.post("/process")
def process(payload: dict):
    minio_object = payload.get("minio_object")
    record_id = payload.get("record_id")

    logger.info(
        f"Process request received — record_id={record_id} object={minio_object}",
        extra={"status": "called"}
    )

    if not minio_object:
        logger.warning("Missing minio_object in payload", extra={"status": "error"})
        return {"error": "minio_object is required"}

    # Fix #1: only extract the suffix from user input — never use minio_object
    # as a path component directly, preventing path traversal via object keys
    ext = Path(minio_object).suffix.lower()
    if ext not in ALLOWED_SUFFIXES:
        logger.warning(
            f"Rejected unsupported extension — {ext!r}",
            extra={"status": "error"}
        )
        return {"error": "Unsupported file type"}

    filename = f"{uuid.uuid4()}{ext}"

    # Fix #2: initialise tmp_path before try so finally block never hits NameError
    # Fix #3: keep as Path throughout — only cast to str at call sites that need it
    tmp_path: Path | None = None

    try:
        tmp_path = UPLOADS_ROOT / filename

        logger.info(
            f"Downloading from MinIO — object={minio_object}",
            extra={"status": "called"}
        )
        minio_client.fget_object(MINIO_BUCKET, minio_object, str(tmp_path))
        logger.info("MinIO download complete", extra={"status": "success"})

        logger.info("Preprocessing invoked", extra={"status": "called"})
        frames, preprocessing_signal = preprocess(str(tmp_path))
        logger.info(
            f"Preprocessing complete — quality={preprocessing_signal.score}",
            extra={"status": "success"}
        )

        logger.info("Detection invoked", extra={"status": "called"})
        detection_signal = detect(frames)  # numpy arrays stay inside ML service
        logger.info(
            f"Detection complete — score={detection_signal.score}",
            extra={"status": "success"}
        )

    except ValueError as e:
        logger.error(f"Processing failed — {e}", extra={"status": "error"})
        return {"error": str(e)}
    except Exception:
        logger.exception("Unexpected error during processing", extra={"status": "error"})
        return {"error": "Internal processing error"}
    finally:
        # Fix #2+3: tmp_path is a Path or None — .exists()/.unlink() are safe either way
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
            logger.info("Temp file cleaned up", extra={"status": "success"})

    logger.info(
        f"Process complete — record_id={record_id}",
        extra={"status": "success"}
    )

    return {
        "record_id": record_id,
        "preprocessing": preprocessing_signal.model_dump(),
        "detection": detection_signal.model_dump(),
        }
    

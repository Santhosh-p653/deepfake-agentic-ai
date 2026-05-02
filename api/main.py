import uuid
import threading
import time
import requests
from datetime import datetime
from fastapi import FastAPI, Response, status, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from .db import check_db_connection, get_db, init_db, update_status
from .models import MediaUpload, ProcessingStatus
from .input_validator import validate_input
from .temp_manager import (
    ensure_temp_dir, write_to_temp, delete_from_temp, cleanup_on_startup
)
from .ml_stub import run_ml
from .minio_client import ensure_bucket, upload_to_minio
from shared.logger import get_logger

logger = get_logger("api.main")

app = FastAPI()


def init_db_with_retry(max_retries=10, delay=3):
    for attempt in range(1, max_retries + 1):
        try:
            init_db()
            logger.info("DB initialized successfully", extra={"status": "success"})
            return
        except OperationalError:
            logger.warning(
                f"DB not ready, retrying ({attempt}/{max_retries})",
                extra={"status": "error"}
            )
            time.sleep(delay)

    logger.exception("DB init failed after retries", extra={"status": "error"})
    raise RuntimeError("Database initialization failed")


@app.on_event("startup")
def on_startup():
    init_db_with_retry()
    ensure_temp_dir()
    ensure_bucket()

    from .db import SessionLocal
    if SessionLocal:
        db = SessionLocal()
        try:
            cleanup_on_startup(db)
        finally:
            db.close()

    logger.info("Application startup complete", extra={"status": "success"})


@app.get("/health")
async def health(response: Response):
    db_status = check_db_connection()
    if db_status:
        logger.info("Health check passed", extra={"status": "success"})
        return {"status": "ok", "database": "connected"}
    logger.warning("Health check failed — database disconnected", extra={"status": "error"})
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "error", "database": "disconnected"}


@app.get("/ping")
def ping():
    logger.info("Ping received", extra={"status": "success"})
    return {"message": "pong"}


@app.get("/run-agents")
async def run_agents():
    logger.info("Run agents request received", extra={"status": "called"})
    try:
        response = requests.get("http://agents:8123/ping", timeout=10)
        logger.info(
            f"Agents responded with {response.status_code}",
            extra={"status": "success"}
        )
        return response.json()
    except Exception:
        logger.exception("Failed to reach agents service", extra={"status": "error"})
        return {"error": "Failed to run agents"}


@app.post("/verdict")
def receive_verdict(payload: dict, db: Session = Depends(get_db)):
    record_id = payload.get("record_id")
    verdict = payload.get("verdict")
    verdict_score = payload.get("verdict_score")

    if db and record_id:
        row = db.query(MediaUpload).filter(MediaUpload.id == record_id).first()
        if row:
            row.verdict = verdict
            row.verdict_score = verdict_score
            row.status = ProcessingStatus.completed
            db.commit()

    logger.info(
        f"Verdict received — id={record_id} verdict={verdict} score={verdict_score}",
        extra={"status": "success"}
    )
    return {"status": "ok"}


@app.get("/result/{record_id}")
def get_result(record_id: int, db: Session = Depends(get_db)):
    if not db:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "reason": "Database unavailable"}
        )

    row = db.query(MediaUpload).filter(MediaUpload.id == record_id).first()
    if not row:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "reason": "Record not found"}
        )

    logger.info(
        f"Result fetched — id={record_id} status={row.status.value}",
        extra={"status": "success"}
    )
    return {
        "id": row.id,
        "filename": row.filename,
        "status": row.status.value,
        "verdict": row.verdict,
        "verdict_score": row.verdict_score,
        "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    logger.info(
        f"Upload request received — filename={file.filename}",
        extra={"status": "called"}
    )
    file_bytes = await file.read()

    # Step 1 — validate
    valid, message = validate_input(file.filename, file_bytes)
    if not valid:
        logger.warning(
            f"Upload rejected — filename={file.filename} reason={message}",
            extra={"status": "error"}
        )
        return JSONResponse(status_code=400, content={"status": "rejected", "reason": message})

    size_mb = round(len(file_bytes) / (1024 * 1024), 4)
    ext = file.filename.rsplit(".", 1)[-1].lower()

    # Step 2 — DB insert
    record = MediaUpload(
        filename=file.filename,
        file_type=ext,
        size_mb=size_mb,
        status=ProcessingStatus.pending,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_id = record.id

    logger.info(
        f"DB record created — id={record_id} filename={file.filename}",
        extra={"status": "success"}
    )

    # Step 3 — temp write
    temp_path = write_to_temp(file_bytes, file.filename)
    logger.info(f"Temp file written — path={temp_path}", extra={"status": "success"})

    # Step 4 — ML stub + MinIO
    logger.info("ML stub invoked", extra={"status": "called"})
    ml_result = run_ml(temp_path)
    logger.info("ML stub complete", extra={"status": "success"})

    object_name = f"{uuid.uuid4().hex}.{ext}"
    minio_object = upload_to_minio(temp_path, object_name)
    logger.info(
        f"MinIO upload complete — object={minio_object}",
        extra={"status": "success"}
    )

    update_status(
        db,
        record_id,
        ProcessingStatus.processed,
        processed_at=datetime.utcnow(),
    )

    # Step 5 — delete temp then trigger agents
    delete_from_temp(temp_path)

    def _run_agents():
        try:
            logger.info("Triggering agents pipeline", extra={"status": "called"})
            requests.post(
                "http://agents:8123/run",
                json={"record_id": record_id, "minio_object": minio_object},
                timeout=120,
            )
            logger.info("Agents pipeline triggered", extra={"status": "success"})
        except Exception:
            logger.exception("Failed to trigger agents pipeline", extra={"status": "error"})

    threading.Thread(target=_run_agents, daemon=True).start()

    logger.info(
        f"Upload pipeline complete — id={record_id} filename={file.filename}",
        extra={"status": "success"}
    )

    return {
        "status": "accepted",
        "id": record_id,
        "filename": file.filename,
        "size_mb": size_mb,
        "ml_result": ml_result,
        "minio_object": minio_object,
    }

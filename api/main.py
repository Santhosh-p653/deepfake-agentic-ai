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
from .logger import get_logger

logger = get_logger(__name__)

app = FastAPI()


# ✅ DB RETRY LOGIC
def init_db_with_retry(max_retries=10, delay=3):
    for attempt in range(1, max_retries + 1):
        try:
            init_db()
            logger.info(
                '{"message": "DB initialized successfully", "attempt": %d}',
                attempt
            )
            return
        except OperationalError:
            logger.warning(
                '{"message": "DB not ready, retrying", "attempt": %d, "max": %d}',
                attempt,
                max_retries
            )
            time.sleep(delay)

    logger.exception('{"message": "DB init failed after retries"}')
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

    logger.info('{"message": "Application startup complete"}')


@app.get("/health")
async def health(response: Response):
    db_status = check_db_connection()
    if db_status:
        logger.info('{"message": "Health check passed", "database": "connected"}')
        return {"status": "ok", "database": "connected"}
    logger.warning('{"message": "Health check failed", "database": "disconnected"}')
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "error", "database": "disconnected"}


@app.get("/ping")
def ping():
    logger.info('{"message": "Ping received"}')
    return {"message": "pong"}


@app.get("/run-agents")
async def run_agents():
    logger.info('{"message": "Run agents request received"}')
    try:
        response = requests.get("http://agents:8123/ping", timeout=10)
        logger.info('{"message": "Agents responded", "status_code": %d}', response.status_code)
        return response.json()
    except Exception:
        logger.exception('{"message": "Failed to reach agents service"}')
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
        '{"message": "Verdict received", "id": %s, "verdict": "%s", "score": %s}',
        record_id,
        verdict,
        verdict_score,
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
        '{"message": "Result fetched", "id": %d, "status": "%s"}',
        record_id,
        row.status.value,
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
    logger.info('{"message": "Upload request received", "filename": "%s"}', file.filename)
    file_bytes = await file.read()

    # Step 1 — validate
    valid, message = validate_input(file.filename, file_bytes)
    if not valid:
        logger.warning(
            '{"message": "Upload rejected", "filename": "%s", "reason": "%s"}',
            file.filename,
            message,
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

    # Step 3 — temp write
    temp_path = write_to_temp(file_bytes, file.filename)

    # Step 4 — ML + MinIO
    ml_result = run_ml(temp_path)
    object_name = f"{uuid.uuid4().hex}.{ext}"
    minio_object = upload_to_minio(temp_path, object_name)

    update_status(
        db,
        record_id,
        ProcessingStatus.processed,
        processed_at=datetime.utcnow(),
    )

    # Step 5 — trigger agents FIRST
    def _run_agents():
        try:
            requests.post(
                "http://agents:8123/run",
                json={"record_id": record_id, "file_path": temp_path},
                timeout=120,
            )
        except Exception:
            logger.exception('{"message": "Failed to trigger agents pipeline"}')

    threading.Thread(target=_run_agents, daemon=True).start()

    # ✅ NOW safe to delete temp file
    delete_from_temp(temp_path)

    logger.info(
        '{"message": "Upload pipeline complete", "id": %s, "filename": "%s"}',
        record_id,
        file.filename,
    )

    return {
        "status": "accepted",
        "id": record_id,
        "filename": file.filename,
        "size_mb": size_mb,
        "ml_result": ml_result,
        "minio_object": minio_object,
    }
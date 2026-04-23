
import uuid
import json
import requests
from datetime import datetime
from fastapi import FastAPI, Response, status, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .db import check_db_connection, get_db, init_db, count_active_temp_files, update_status
from .models import MediaUpload, ProcessingStatus
from .input_validator import validate_input
from .temp_manager import (
    ensure_temp_dir, write_to_temp, delete_from_temp, cleanup_on_startup, TEMP_FILE_CAP
)
from .ml_stub import run_ml
from .minio_client import ensure_bucket, upload_to_minio
from .logger import get_logger

logger = get_logger(__name__)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()
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


@app.get("/run-agents")
async def run_agents():
    logger.info('{"message": "Run agents request received"}')
    try:
        response = requests.get("http://agents:8123/run", timeout=10)
        logger.info('{"message": "Agents responded", "status_code": %d}', response.status_code)
        return response.json()
    except Exception:
        logger.exception('{"message": "Failed to reach agents service"}')
        return {"error": "Failed to run agents"}


@app.get("/ping")
def ping():
    logger.info('{"message": "Ping received"}')
    return {"message": "pong"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    logger.info('{"message": "Upload request received", "filename": "%s"}', file.filename)
    file_bytes = await file.read()

    # Step 1 — validate format and encoding
    valid, message = validate_input(file.filename, file_bytes)
    if not valid:
        logger.warning(
            '{"message": "Upload rejected at validation", "filename": "%s", "reason": "%s"}',
            file.filename,
            message,
        )
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": message}
        )

    size_mb = round(len(file_bytes) / (1024 * 1024), 4)
    ext = file.filename.rsplit(".", 1)[-1].lower()

    # Step 2 — cap check + DB insert (atomic)
    record_id = None
    temp_path = None

    if db:
        try:
            active_count = count_active_temp_files(db)
            if active_count >= TEMP_FILE_CAP:
                logger.warning(
                    '{"message": "Upload rejected, temp cap reached",'
                    ' "filename": "%s", "active": %d, "cap": %d}',
                    file.filename,
                    active_count,
                    TEMP_FILE_CAP,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "rejected",
                        "reason": (
                            f"Temp storage at capacity ({TEMP_FILE_CAP} files max). "
                            "Try again shortly."
                        ),
                    },
                )

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
                '{"message": "DB record created", "id": %d, "filename": "%s"}',
                record_id,
                file.filename,
            )

        except Exception:
            logger.exception(
                '{"message": "DB error during cap check", "filename": "%s"}',
                file.filename,
            )
            return JSONResponse(
                status_code=500,
                content={"status": "error", "reason": "Database error"}
            )
    else:
        logger.warning(
            '{"message": "No DB session, proceeding without persistence",'
            ' "filename": "%s"}',
            file.filename,
        )

    # Step 3 — write to temp folder
    try:
        temp_path = write_to_temp(file_bytes, file.filename)
        if db and record_id:
            update_status(db, record_id, ProcessingStatus.temp_stored, temp_path=temp_path)
    except Exception:
        logger.exception(
            '{"message": "Failed to write temp file", "filename": "%s"}',
            file.filename,
        )
        if db and record_id:
            update_status(
                db, record_id, ProcessingStatus.failed, processed_at=datetime.utcnow()
            )
        return JSONResponse(
            status_code=500,
            content={"status": "error", "reason": "Failed to store file"}
        )

    # Step 4 — transition to processing, run ML stub, push to MinIO
    ml_result = None
    minio_object = None
    try:
        if db and record_id:
            update_status(db, record_id, ProcessingStatus.processing)

        ml_result = run_ml(temp_path)

        object_name = f"{uuid.uuid4().hex}.{ext}"
        minio_object = upload_to_minio(temp_path, object_name)

        if db and record_id:
            update_status(
                db,
                record_id,
                ProcessingStatus.processed,
                processed_at=datetime.utcnow(),
            )
            row = db.query(MediaUpload).filter(MediaUpload.id == record_id).first()
            if row:
                row.drive_path = minio_object
                db.commit()

        logger.info(
            '{"message": "ML and MinIO complete", "id": %s, "filename": "%s",'
            ' "object": "%s"}',
            record_id,
            file.filename,
            minio_object,
        )

    except Exception:
        logger.exception(
            '{"message": "ML or MinIO failed", "id": %s, "filename": "%s"}',
            record_id,
            file.filename,
        )
        if db and record_id:
            update_status(
                db, record_id, ProcessingStatus.failed, processed_at=datetime.utcnow()
            )

    finally:
        if temp_path:
            delete_from_temp(temp_path)
            if db and record_id:
                update_status(db, record_id, ProcessingStatus.deleted)

    logger.info(
        '{"message": "Upload pipeline complete", "id": %s, "filename": "%s",'
        ' "size_mb": %f}',
        record_id,
        file.filename,
        size_mb,
    )
    return {
        "status": "accepted",
        "id": record_id,
        "filename": file.filename,
        "size_mb": size_mb,
        "ml_result": ml_result,
        "minio_object": minio_object,
    }

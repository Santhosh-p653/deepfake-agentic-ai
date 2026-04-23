import requests
from datetime import datetime
from fastapi import FastAPI, Response, status, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .db import check_db_connection, get_db, init_db, count_active_temp_files, update_status
from .models import MediaUpload, ProcessingStatus
from .input_validator import validate_input
from .temp_manager import ensure_temp_dir, write_to_temp, delete_from_temp, cleanup_on_startup, TEMP_FILE_CAP
from .ml_stub import run_ml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()
    ensure_temp_dir()
    # Run cleanup inside its own DB session — not a request session
    from .db import SessionLocal
    if SessionLocal:
        db = SessionLocal()
        try:
            cleanup_on_startup(db)
        finally:
            db.close()


@app.get("/health")
async def health(response: Response):
    logger.info("Health endpoint called")
    db_status = check_db_connection()
    if db_status:
        return {"status": "ok", "database": "connected"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "error", "database": "disconnected"}


@app.get("/run-agents")
async def run_agents():
    try:
        response = requests.get("http://agents:8123/run", timeout=10)
        return response.json()
    except Exception:
        logger.exception("Error while calling agents service")
        return {"error": "Failed to run agents"}


@app.get("/ping")
def ping():
    return {"message": "pong"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_bytes = await file.read()

    # Step 1 — validate format and encoding
    valid, message = validate_input(file.filename, file_bytes)
    if not valid:
        logger.warning("Upload rejected: %s | file=%s", message, file.filename)
        return JSONResponse(status_code=400, content={"status": "rejected", "reason": message})

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
                    "Upload rejected: temp cap reached | file=%s active=%d cap=%d",
                    file.filename, active_count, TEMP_FILE_CAP
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "rejected",
                        "reason": f"Temp storage at capacity ({TEMP_FILE_CAP} files max). Try again shortly."
                    }
                )

            # Insert row as pending before touching disk
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

        except Exception:
            logger.exception("DB error during upload cap check: file=%s", file.filename)
            return JSONResponse(status_code=500, content={"status": "error", "reason": "Database error"})
    else:
        logger.warning("No DB session — proceeding without persistence: file=%s", file.filename)

    # Step 3 — write to temp folder
    try:
        temp_path = write_to_temp(file_bytes, file.filename)
        if db and record_id:
            update_status(db, record_id, ProcessingStatus.temp_stored, temp_path=temp_path)
    except Exception:
        logger.exception("Failed to write temp file: file=%s", file.filename)
        if db and record_id:
            update_status(db, record_id, ProcessingStatus.failed, processed_at=datetime.utcnow())
        return JSONResponse(status_code=500, content={"status": "error", "reason": "Failed to store file"})

    # Step 4 — transition to processing, run ML stub
    ml_result = None
    try:
        if db and record_id:
            update_status(db, record_id, ProcessingStatus.processing)

        ml_result = run_ml(temp_path)

        if db and record_id:
            update_status(db, record_id, ProcessingStatus.processed, processed_at=datetime.utcnow())

        logger.info("ML complete: id=%s file=%s result=%s", record_id, file.filename, ml_result)

    except Exception:
        logger.exception("ML failed: id=%s file=%s", record_id, file.filename)
        if db and record_id:
            update_status(db, record_id, ProcessingStatus.failed, processed_at=datetime.utcnow())

    finally:
        # Always clean up — success or failure
        if temp_path:
            delete_from_temp(temp_path)
            if db and record_id:
                update_status(db, record_id, ProcessingStatus.deleted)

    logger.info("Upload complete: id=%s file=%s size_mb=%f", record_id, file.filename, size_mb)
    return {
        "status": "accepted",
        "id": record_id,
        "filename": file.filename,
        "size_mb": size_mb,
        "ml_result": ml_result,
}

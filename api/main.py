<<<<<<< Updated upstream
import requests
from fastapi import FastAPI, Response, status, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .db import check_db_connection, get_db, init_db
from .models import MediaUpload
from .input_validator import validate_input
=======
from fastapi import FastAPI
from db import check_db_connection
>>>>>>> Stashed changes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


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
    valid, message = validate_input(file.filename, file_bytes)

    if not valid:
        logger.warning("Upload rejected: %s | file=%s", message, file.filename)
        return JSONResponse(status_code=400, content={"status": "rejected", "reason": message})

    size_mb = round(len(file_bytes) / (1024 * 1024), 4)
    ext = file.filename.rsplit(".", 1)[-1].lower()

    record = MediaUpload(
        filename=file.filename,
        file_type=ext,
        size_mb=size_mb,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("Upload accepted and recorded: id=%d file=%s size_mb=%f", record.id, record.filename, record.size_mb)
    return {"status": "accepted", "id": record.id, "filename": record.filename, "size_mb": size_mb}

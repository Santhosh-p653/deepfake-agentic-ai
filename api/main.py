import requests
from fastapi import FastAPI, Response, status, UploadFile, File
from fastapi.responses import JSONResponse
from .db import check_db_connection
from .input_validator import validate_input
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


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
async def upload_file(file: UploadFile = File(...)):
    file_bytes = await file.read()
    valid, message = validate_input(file.filename, file_bytes)

    if not valid:
        logger.warning("Upload rejected: %s | file=%s", message, file.filename)
        return JSONResponse(status_code=400, content={"status": "rejected", "reason": message})

    logger.info("Upload accepted: file=%s size_bytes=%d", file.filename, len(file_bytes))
    return {"status": "accepted", "filename": file.filename, "size_bytes": len(file_bytes)}

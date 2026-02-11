<<<<<<< Updated upstream
from fastapi import FastAPI, Response, status
=======
from fastapi import FastAPI
>>>>>>> Stashed changes
from db import check_db_connection
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

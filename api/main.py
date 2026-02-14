import requests
import asyncio
import subprocess
import json
from fastapi import FastAPI, Response, status
from fastapi import FastAPI
from .db import check_db_connection
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
		response=requests.get("http://agents:8123/run",timeout=10)
		return response.json()
	except Exception as e:
		return {"error":str(e)}
@app.get("/ping")
def ping():
	return{"message":"pong"}

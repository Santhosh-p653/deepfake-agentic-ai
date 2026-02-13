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
		result=subprocess.run(["docker","run","--rm","--env-file",".env","deepfake-agentic-ai-agents","python","agents/task_runner.py"],capture_output=True,text=True)
		logger.info(f"Agents output:{result.stdout}")
		try:
			return json.loads(result.stdout)
		except json.JSONDecodeError:
			return{"output":result.stdout}
	except  Exception as e:
		logger.error(f"Failed to run agents:{e}")
		return{"error":str(e)}

from fastapi import FastAPI
fromdb import check_db_connection
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
app=FastAPI()
@app.get("/")
def health():
	logger.info("Health endpoint called")
	db_status=check_db_connection()
	if db_status:
		return {"status":"ok","database":"connected"}
	else:
		return {"status":"error","database":"disconnected"}


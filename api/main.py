from fastapi import FastAPI
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
app=FastAPI()
@app.get("/")
def health():
	logger.info("Health endpoint called")
	return {"status":"ok"}
	

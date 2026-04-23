import time
import logging

logger = logging.getLogger(__name__)

def run_ml(file_path: str) -> dict:
    """
    Stub ML call. Simulates processing delay and returns a dummy result.
    Replace with real inter-service call in step 4+.
    """
    logger.info("ML stub invoked: path=%s", file_path)
    time.sleep(0.5)  # simulate processing time
    result = {
        "deepfake_probability": 0.07,
        "model": "stub",
        "file_path": file_path,
    }
    logger.info("ML stub complete: path=%s result=%s", file_path, result)
    return result

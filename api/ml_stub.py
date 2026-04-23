import time
from .logger import get_logger

logger = get_logger(__name__)


def run_ml(file_path: str) -> dict:
    """
    Stub ML call. Simulates processing delay and returns a dummy result.
    Replace with real inter-service call in step 4+.
    """
    logger.info('{"message": "ML stub invoked", "path": "%s"}', file_path)
    time.sleep(0.5)
    result = {
        "deepfake_probability": 0.07,
        "model": "stub",
        "file_path": file_path,
    }
    logger.info(
        '{"message": "ML stub complete", "path": "%s", "deepfake_probability": %s}',
        file_path,
        result["deepfake_probability"],
    )
    return result

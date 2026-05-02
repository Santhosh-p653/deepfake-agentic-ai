import requests
from shared.logger import get_logger

logger = get_logger("agents.ml_client")

ML_URL = "http://ml:8001"


def call_ml(minio_object: str, record_id: int) -> dict:
    logger.info(
        f"Calling ML service — record_id={record_id} object={minio_object}",
        extra={"status": "called"}
    )
    try:
        response = requests.post(
            f"{ML_URL}/process",
            json={"minio_object": minio_object, "record_id": record_id},
            timeout=60,
        )
        response.raise_for_status()
        logger.info("ML service call complete", extra={"status": "success"})
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("ML service call timed out", extra={"status": "error"})
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"ML service returned error — {e}", extra={"status": "error"})
        raise
    except Exception:
        logger.exception("Unexpected error calling ML service", extra={"status": "error"})
        raise

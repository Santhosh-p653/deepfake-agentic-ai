import requests

ML_URL = "http://ml:8001"


def call_ml(file_path: str, record_id: int) -> dict:
    response = requests.post(
        f"{ML_URL}/process",
        json={"file_path": file_path, "record_id": record_id},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

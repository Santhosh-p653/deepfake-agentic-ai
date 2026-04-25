import requests
from fastapi import FastAPI

from .log_analyser import analyse_logs
from .ml_client import call_ml
from .aggregator import aggregate
from .decider import decide
from shared.signal import Signal

API_URL = "http://api:8000"

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "agents pong"}


@app.get("/analyse")
def analyse():
    signal = analyse_logs()
    return signal.model_dump()


@app.post("/run")
def run(payload: dict):
    record_id = payload.get("record_id")
    file_path = payload.get("file_path")

    if not record_id or not file_path:
        return {"error": "record_id or file_path missing"}

    # 🔹 Step 1 — call ML service
    try:
        ml_result = call_ml(file_path, record_id)
    except Exception as e:
        return {"error": f"ML call failed: {str(e)}"}

    try:
        preprocessing = Signal(**ml_result["preprocessing"])
        detection = Signal(**ml_result["detection"])
    except Exception as e:
        return {"error": f"Invalid ML response: {str(e)}"}

    # 🔹 Step 2 — analyse logs
    log_signal = analyse_logs()

    # 🔹 Step 3 — aggregate signals
    aggregated = aggregate(preprocessing, detection, log_signal)

    # 🔹 Step 4 — decide verdict
    decision = decide(aggregated, record_id)

    # 🔹 Step 5 — send verdict back to API
    try:
        requests.post(
            f"{API_URL}/verdict",
            json={
                "record_id": record_id,
                "verdict": decision.get("verdict"),
                "verdict_score": decision.get("score"),
            },
            timeout=10,
        )
    except Exception:
        # don't crash pipeline if API is temporarily unavailable
        pass

    return {
        "record_id": record_id,
        "aggregated": aggregated,
        "decision": decision,
    }
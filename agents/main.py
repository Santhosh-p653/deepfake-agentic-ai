import requests
from fastapi import FastAPI
from log_analyser import analyse_logs
from ml_client import call_ml
from aggregator import aggregate
from decider import decide
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

    # call ml service
    ml_result = call_ml(file_path, record_id)

    preprocessing = Signal(**ml_result["preprocessing"])
    detection = Signal(**ml_result["detection"])

    # analyse logs
    log_signal = analyse_logs()

    # aggregate all three signals
    aggregated = aggregate(preprocessing, detection, log_signal)

    # decide verdict
    decision = decide(aggregated, record_id)

    # send verdict back to api
    try:
        requests.post(
            f"{API_URL}/verdict",
            json={
                "record_id": record_id,
                "verdict": decision["verdict"],
                "verdict_score": decision["score"],
            },
            timeout=10,
        )
    except Exception:
        pass

    return {
        "record_id": record_id,
        "aggregated": aggregated,
        "decision": decision,
    }

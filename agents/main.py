import requests
from fastapi import FastAPI
from agents.log_analyser import analyse_logs
from agents.ml_client import call_ml
from agents.aggregator import aggregate
from agents.decider import decide
from agents.source_verifier import verify
from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("agents.main")

API_URL = "http://api:8000"

app = FastAPI()


@app.get("/ping")
def ping():
    logger.info("Ping received", extra={"status": "success"})
    return {"message": "agents pong"}


@app.get("/analyse")
def analyse():
    logger.info("Standalone analyse request received", extra={"status": "called"})
    signal = analyse_logs()
    logger.info("Standalone analyse complete", extra={"status": "success"})
    return signal.model_dump()


@app.post("/run")
def run(payload: dict):
    record_id = payload.get("record_id")
    minio_object = payload.get("minio_object")

    logger.info(
        f"Pipeline run invoked — record_id={record_id}",
        extra={"status": "called"}
    )

    # Call ML service
    logger.info("ML client invoked", extra={"status": "called"})
    ml_result = call_ml(minio_object, record_id)
    logger.info("ML client complete", extra={"status": "success"})

    preprocessing = Signal(**ml_result["preprocessing"])
    detection = Signal(**ml_result["detection"])

    # Source verification — reads from preprocessing metadata
    logger.info("Source verifier invoked", extra={"status": "called"})
    source_signal = verify(preprocessing)
    logger.info("Source verifier complete", extra={"status": "success"})

    # Analyse logs
    logger.info("Log analyser invoked", extra={"status": "called"})
    log_signal = analyse_logs()
    logger.info("Log analyser complete", extra={"status": "success"})

    # Aggregate all four signals
    logger.info("Aggregator invoked", extra={"status": "called"})
    aggregated = aggregate(preprocessing, detection, log_signal, source_signal)
    logger.info(
        f"Aggregation complete — score={aggregated['aggregated_score']}",
        extra={"status": "success"}
    )

    # Decide verdict
    logger.info("Decider invoked", extra={"status": "called"})
    decision = decide(aggregated, record_id)
    logger.info(
        f"Decision complete — verdict={decision['verdict']}",
        extra={"status": "success"}
    )

    # Send verdict back to API
    try:
        logger.info("Sending verdict to API", extra={"status": "called"})
        requests.post(
            f"{API_URL}/verdict",
            json={
                "record_id": record_id,
                "verdict": decision["verdict"],
                "verdict_score": decision["score"],
            },
            timeout=10,
        )
        logger.info("Verdict sent to API", extra={"status": "success"})
    except Exception:
        logger.exception("Failed to send verdict to API", extra={"status": "error"})

    logger.info(
        f"Pipeline run complete — record_id={record_id} verdict={decision['verdict']}",
        extra={"status": "success"}
    )

    return {
        "record_id": record_id,
        "aggregated": aggregated,
        "decision": decision,
        "source_flags": source_signal.metadata.get("flags", []),
    }

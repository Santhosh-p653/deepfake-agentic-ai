import requests
from fastapi import FastAPI
from agents.log_analyser import analyse_logs
from agents.ml_client import call_ml
from agents.aggregator import aggregate, compute_path3a_weights
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

    # Source verification
    logger.info("Source verifier invoked", extra={"status": "called"})
    source_signal = verify(preprocessing)
    logger.info("Source verifier complete", extra={"status": "success"})

    # Log analysis
    logger.info("Log analyser invoked", extra={"status": "called"})
    log_signal = analyse_logs()
    logger.info("Log analyser complete", extra={"status": "success"})

    # First aggregation — reliability-weighted
    logger.info("Aggregator invoked", extra={"status": "called"})
    aggregated = aggregate(preprocessing, detection, log_signal, source_signal)
    logger.info(
        f"Aggregation complete — score={aggregated['aggregated_score']}",
        extra={"status": "success"}
    )

    # First decision
    logger.info("Decider invoked", extra={"status": "called"})
    decision = decide(aggregated, record_id)
    logger.info(
        f"Decision complete — verdict={decision['verdict']} "
        f"reanalysis={decision.get('reanalysis')}",
        extra={"status": "success"}
    )

    # Path 3a — middle zone reanalysis with uniform weight boost
    if decision.get("reanalysis") and decision.get("reanalysis_path") == "3a":
        logger.info(
            "Path 3a reanalysis triggered — applying uniform weight boost",
            extra={"status": "called"}
        )
        boosted_weights = compute_path3a_weights(aggregated["weight_breakdown"])
        aggregated = aggregate(
            preprocessing, detection, log_signal, source_signal,
            weight_overrides=boosted_weights,
        )
        logger.info(
            f"Path 3a re-aggregation complete — score={aggregated['aggregated_score']}",
            extra={"status": "success"}
        )
        decision = decide(aggregated, record_id)
        decision["reanalysis_path"] = "3a_complete"
        logger.info(
            f"Path 3a decision complete — verdict={decision['verdict']}",
            extra={"status": "success"}
        )

    # Send verdict to API
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
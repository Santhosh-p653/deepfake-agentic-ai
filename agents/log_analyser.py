import hashlib
import json
import os
import re

from openai import OpenAI

from shared.log_filter import load_filtered_logs
from shared.logger import get_logger
from shared.signal import Signal

logger = get_logger("agents.log_analyser")

client = OpenAI(
    api_key=os.getenv("SAMBANOVA_API_KEY"),
    base_url="https://api.sambanova.ai/v1",
)

_cache: dict[str, dict] = {}


def analyse_logs() -> Signal:
    logger.info("Log analyser invoked", extra={"status": "called"})

    logs = load_filtered_logs()

    if not logs:
        logger.warning("No relevant logs found after filtering", extra={"status": "error"})
        return Signal(
            score=0.0,
            reliability=0.0,
            module="agents.log_analyser",
            metadata={"error": "no logs found after filtering"},
        )

    logger.info(f"Filtered logs ready — lines={len(logs)}", extra={"status": "success"})

    cache_key = hashlib.sha256(json.dumps(logs, sort_keys=True).encode()).hexdigest()

    if cache_key in _cache:
        logger.info("Cache hit — skipping LLM call", extra={"status": "success"})
        analysis = _cache[cache_key]
    else:
        analysis = _call_llm_with_retry(logs)
        _cache[cache_key] = analysis

    score, reliability = _parse_analysis(analysis)

    logger.info(
        f"Log analysis complete — score={score} reliability={reliability}",
        extra={"status": "success"},
    )

    return Signal(
        score=score,
        reliability=reliability,
        module="agents.log_analyser",
        metadata={
            "lines_analysed": len(logs),
            "analysis_summary": analysis.get("summary"),
            "anomalies": analysis.get("anomalies", []),
        },
    )


def _call_llm_raw(logs: list[dict], temperature: float = 0.1) -> str:
    log_text = json.dumps(logs, indent=2)

    prompt = (
        "You are a log analyser for a deepfake detection system.\n"
        "Analyse the following filtered structured JSON logs "
        "(WARNING/ERROR levels and module checkpoints only).\n"
        "Identify anomalies, missing module invocations, or suspicious patterns.\n\n"
        f"Logs:\n{log_text}\n\n"
        "Respond ONLY in JSON with this exact structure, no preamble, no markdown:\n"
        "{\n"
        '  "summary": "one sentence summary of log health",\n'
        '  "anomalies": ["list of specific anomalies found, empty if none"],\n'
        '  "missing_modules": ["list of modules expected but not seen in logs"],\n'
        '  "anomaly_score": 0.0,\n'
        '  "confidence": 0.0\n'
        "}\n\n"
        "anomaly_score: 0.0 means clean, 1.0 means highly suspicious.\n"
        "confidence: how confident you are in this analysis, 0.0 to 1.0."
    )

    response = client.chat.completions.create(
        model="gemma-3-12b-it",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


def _call_llm_with_retry(logs: list[dict]) -> dict:
    logger.info("LLM call invoked", extra={"status": "called"})

    # Attempt 1 — temperature 0.1
    try:
        raw = _call_llm_raw(logs, temperature=0.1)
        result = _extract_json(raw)
        logger.info("LLM call complete", extra={"status": "success"})
        return result
    except Exception:
        logger.warning("LLM attempt 1 failed, retrying at temperature=0.0", extra={"status": "error"})

    # Attempt 2 — temperature 0.0
    try:
        raw = _call_llm_raw(logs, temperature=0.0)
        result = _extract_json(raw)
        logger.info("LLM retry succeeded", extra={"status": "success"})
        return result
    except Exception:
        logger.exception("LLM retry failed, falling back to rule-based", extra={"status": "error"})

    # Fallback
    return _rule_based_fallback(logs)


def _rule_based_fallback(logs: list[dict]) -> dict:
    error_count = sum(1 for e in logs if e.get("level") == "ERROR")
    warning_count = sum(1 for e in logs if e.get("level") == "WARNING")

    anomaly_score = min(1.0, (error_count * 0.2) + (warning_count * 0.05))

    logger.warning(
        f"Rule-based fallback used — errors={error_count} warnings={warning_count}",
        extra={"status": "error"},
    )

    return {
        "summary": f"Rule-based fallback: {error_count} errors, {warning_count} warnings detected.",
        "anomalies": [f"{error_count} ERROR entries found"] if error_count else [],
        "missing_modules": [],
        "anomaly_score": anomaly_score,
        "confidence": 0.3,
    }


def _parse_analysis(analysis: dict) -> tuple[float, float]:
    score = float(analysis.get("anomaly_score", 0.0))
    reliability = float(analysis.get("confidence", 0.2))
    score = max(0.0, min(1.0, score))
    reliability = max(0.0, min(1.0, reliability))
    return score, reliability
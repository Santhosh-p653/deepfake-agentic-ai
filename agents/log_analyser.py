import json
import os
from openai import OpenAI
from shared.signal import Signal
from shared.logger import get_logger
from shared.log_filter import load_filtered_logs

logger = get_logger("agents.log_analyser")

client = OpenAI(
    api_key=os.getenv("SAMBANOVA_API_KEY"),
    base_url="https://api.sambanova.ai/v1",
)


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

    logger.info(
        f"Filtered logs ready — lines={len(logs)}",
        extra={"status": "success"}
    )

    analysis = _call_llm(logs)
    score, reliability = _parse_analysis(analysis)

    logger.info(
        f"Log analysis complete — score={score} reliability={reliability}",
        extra={"status": "success"}
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


def _call_llm(logs: list[dict]) -> dict:
    log_text = json.dumps(logs, indent=2)

    prompt = f"""
You are a log analyser for a deepfake detection system.
Analyse the following filtered structured JSON logs (WARNING/ERROR levels and module checkpoints only).
Identify anomalies, missing module invocations, or suspicious patterns.

Logs:
{log_text}

Respond ONLY in JSON with this exact structure, no preamble, no markdown:
{{
  "summary": "one sentence summary of log health",
  "anomalies": ["list of specific anomalies found, empty if none"],
  "missing_modules": ["list of modules expected but not seen in logs"],
  "anomaly_score": 0.0,
  "confidence": 0.0
}}

anomaly_score: 0.0 means clean, 1.0 means highly suspicious.
confidence: how confident you are in this analysis, 0.0 to 1.0.
"""

    logger.info("LLM call invoked", extra={"status": "called"})

    try:
        response = client.chat.completions.create(
            model="gemma-3-12b-it",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        logger.info("LLM call complete", extra={"status": "success"})
    except Exception:
        logger.exception("LLM call failed", extra={"status": "error"})
        return {
            "summary": "LLM call failed",
            "anomalies": [],
            "missing_modules": [],
            "anomaly_score": 0.0,
            "confidence": 0.0,
        }

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM response could not be parsed as JSON", extra={"status": "error"})
        return {
            "summary": "LLM response could not be parsed",
            "anomalies": [],
            "missing_modules": [],
            "anomaly_score": 0.0,
            "confidence": 0.2,
        }


def _parse_analysis(analysis: dict) -> tuple[float, float]:
    score = float(analysis.get("anomaly_score", 0.0))
    reliability = float(analysis.get("confidence", 0.2))
    score = max(0.0, min(1.0, score))
    reliability = max(0.0, min(1.0, reliability))
    return score, reliability

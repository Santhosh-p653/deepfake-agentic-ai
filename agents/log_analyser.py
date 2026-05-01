import json
import os
from openai import OpenAI
from shared.signal import Signal

LOG_PATH = "/app/logs/app.log"
MAX_LOG_LINES = 100  # cap to avoid hitting token limits

client = OpenAI(
    api_key=os.getenv("SAMBANOVA_API_KEY"),
    base_url="https://api.sambanova.ai/v1",
)


def analyse_logs() -> Signal:
    logs = _read_logs()

    if not logs:
        return Signal(
            score=0.0,
            reliability=0.0,
            module="agents.log_analyser",
            metadata={
                "error": "no logs found",
                "log_path": LOG_PATH,
            },
        )

    analysis = _call_llm(logs)
    score, reliability = _parse_analysis(analysis)

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


def _read_logs() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []

    logs = []
    with open(LOG_PATH, "r") as f:
        lines = f.readlines()[-MAX_LOG_LINES:]
        for line in lines:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return logs


def _call_llm(logs: list[dict]) -> dict:
    log_text = json.dumps(logs, indent=2)

    prompt = f"""
You are a log analyser for a deepfake detection system.
Analyse the following structured JSON logs and identify any anomalies,
inconsistencies, or suspicious patterns.

Logs:
{log_text}

Respond ONLY in JSON with this exact structure, no preamble, no markdown:
{{
  "summary": "one sentence summary of log health",
  "anomalies": ["list of specific anomalies found, empty if none"],
  "anomaly_score": 0.0,
  "confidence": 0.0
}}

anomaly_score: 0.0 means clean, 1.0 means highly suspicious.
confidence: how confident you are in this analysis, 0.0 to 1.0.
"""

    response = client.chat.completions.create(
        model="gemma-3-12b-it",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "summary": "LLM response could not be parsed",
            "anomalies": [],
            "anomaly_score": 0.0,
            "confidence": 0.2,
        }


def _parse_analysis(analysis: dict) -> tuple[float, float]:
    score = float(analysis.get("anomaly_score", 0.0))
    reliability = float(analysis.get("confidence", 0.2))
    score = max(0.0, min(1.0, score))
    reliability = max(0.0, min(1.0, reliability))
    return score, reliability

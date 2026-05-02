import json
import os

LOG_PATH = os.getenv("LOG_PATH", "/app/logs/app.log")
MAX_RAW_LINES = 500  # read last N lines from file
TARGET_STATUSES = {"called", "success", "error"}
TARGET_LEVELS = {"WARNING", "ERROR"}


def load_filtered_logs() -> list[dict]:
    """
    Reads the shared log file and returns only:
    - Lines at WARNING or ERROR level
    - Lines with status in {called, success, error} (module checkpoints)

    Keeps output small — target under 20 lines for LLM context.
    """
    if not os.path.exists(LOG_PATH):
        return []

    raw_lines = []
    with open(LOG_PATH, "r") as f:
        raw_lines = f.readlines()[-MAX_RAW_LINES:]

    filtered = []
    for line in raw_lines:
        try:
            entry = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        level = entry.get("level", "")
        status = entry.get("status")

        if level in TARGET_LEVELS or status in TARGET_STATUSES:
            # Only keep fields useful for LLM — drop noise
            filtered.append({
                "timestamp": entry.get("timestamp"),
                "level": level,
                "module": entry.get("module"),
                "status": status,
                "message": entry.get("message"),
                # include exception summary if present
                **({"exception": entry["exception"][:200]} if "exception" in entry else {}),
            })

    return filtered
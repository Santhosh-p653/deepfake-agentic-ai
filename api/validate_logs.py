
import sys
import json

REQUIRED_FIELDS = {"timestamp", "level", "module", "message"}

REQUIRED_EVENTS = [
    "Upload request received",
    "DB record created",
    "Write temp file",
    "ML stub invoked",
    "Upload to MinIO complete",
    "Upload pipeline complete",
]


def validate(log_path: str):
    errors = []
    events_found = set()

    try:
        with open(log_path, "r") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    except FileNotFoundError:
        print(f"ERROR: Log file not found: {log_path}")
        sys.exit(1)

    if not lines:
        print("ERROR: Log file is empty")
        sys.exit(1)

    for i, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: invalid JSON — {e}\n  Content: {line[:120]}")
            continue

        missing = REQUIRED_FIELDS - entry.keys()
        if missing:
            errors.append(f"Line {i}: missing fields {missing} — {line[:120]}")
            continue

        msg = entry.get("message", "")
        for event in REQUIRED_EVENTS:
            if event in msg:
                events_found.add(event)

    missing_events = set(REQUIRED_EVENTS) - events_found
    if missing_events:
        for event in missing_events:
            errors.append(f"Missing required log event: '{event}'")

    if errors:
        print(f"Log validation FAILED — {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print(
        f"Log validation PASSED — {len(lines)} lines checked, "
        f"all {len(REQUIRED_EVENTS)} required events found."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_logs.py <path_to_log_file>")
        sys.exit(1)
    validate(sys.argv[1])

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
            lines = [l.strip() for l in f.readlines() if l.strip()]
    except FileNotFoundError:
        print(f"ERROR: Log file not found: {log_path}")
        sys.exit(1)

    if not lines:
        print("ERROR: Log file is empty")
        sys.exit(1)

    for i, line in enumerate(lines, 1):
        # Check every line is valid JSON
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: invalid JSON — {e}\n  Content: {line[:120]}")
            continue

        # Check required fields exist
        missing = REQUIRED_FIELDS - entry.keys()
        if missing:
            errors.append(f"Line {i}: missing fields {missing} — {line[:120]}")
            continue

        # Track which required events have been logged
        msg = entry.get("message", "")
        for event in REQUIRED_EVENTS:
            if event in msg:
                events_found.add(event)

    # Check all required events were logged
    missing_events = set(REQUIRED_EVENTS) - events_found
    if missing_events:
        for event in missing_events:
            errors.append(f"Missing required log event: '{event}'")

    if errors:
        print(f"Log validation FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"Log validation PASSED — {len(lines)} lines checked, "
          f"all {len(REQUIRED_EVENTS)} required events found.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_logs.py <path_to_log_file>")
        sys.exit(1)
    validate(sys.argv[1])

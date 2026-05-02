"""
Schema validation for CI — verifies API responses match locked schemas.
Run after the API is live: python api/validate_schema.py
"""
import sys
import json
import requests

BASE = "http://localhost:8000"

UPLOAD_REQUIRED = {"status", "id", "filename", "size_mb", "minio_object"}
RESULT_REQUIRED = {
    "id", "filename", "file_type", "size_mb",
    "status", "verdict", "verdict_score", "uploaded_at", "processed_at"
}
HEALTH_REQUIRED = {"status", "database"}


def check(name: str, data: dict, required: set):
    missing = required - set(data.keys())
    if missing:
        print(f"SCHEMA FAIL [{name}] — missing fields: {missing}")
        return False
    print(f"SCHEMA OK [{name}]")
    return True


def main():
    errors = 0

    # Health
    r = requests.get(f"{BASE}/health")
    errors += 0 if check("health", r.json(), HEALTH_REQUIRED) else 1

    # Upload
    import base64
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    r = requests.post(
        f"{BASE}/upload",
        files={"file": ("test.png", png, "image/png")},
    )
    upload_data = r.json()
    errors += 0 if check("upload", upload_data, UPLOAD_REQUIRED) else 1

    # Result
    record_id = upload_data.get("id")
    if record_id:
        r = requests.get(f"{BASE}/result/{record_id}")
        errors += 0 if check("result", r.json(), RESULT_REQUIRED) else 1
    else:
        print("SCHEMA FAIL [result] — no record_id from upload")
        errors += 1

    if errors:
        print(f"\n{errors} schema violation(s) found.")
        sys.exit(1)

    print("\nAll schemas valid.")


if __name__ == "__main__":
    main()

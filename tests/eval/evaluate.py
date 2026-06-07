import json
import os
import time
import uuid
import requests
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = os.getenv("API_URL", "http://localhost:8000")

engine = create_engine(DATABASE_URL)
run_id = str(uuid.uuid4())

JOB_TIMEOUT = 120   # max wait per file
POLL_INTERVAL = 2   # polling frequency


# ---------------------------
# JOB POLLING (ROBUST)
# ---------------------------
def poll_result(record_id, timeout=JOB_TIMEOUT):
    start = time.time()

    while True:
        try:
            r = requests.get(f"{API_URL}/result/{record_id}", timeout=10)
            r.raise_for_status()
            data = r.json()

            status = (data.get("status") or "").lower()
            verdict = (data.get("verdict") or "").lower()

            if status in ["completed", "done"] or verdict not in ["pending", "processing", "queued"]:
                return data

        except Exception as e:
            print(f"[POLL ERROR] {record_id}: {e}")

        if time.time() - start > timeout:
            return None

        time.sleep(POLL_INTERVAL)


# ---------------------------
# LOAD DATA
# ---------------------------
with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT id, filename, file_path, ground_truth
            FROM test_fixtures
            WHERE predicted_label IS NULL
        """)
    ).fetchall()

    real_count = sum(1 for r in rows if r.ground_truth == "real")
    fake_count = sum(1 for r in rows if r.ground_truth == "fake")

    print(f"\nLoaded {len(rows)} fixtures — Real: {real_count}, Fake: {fake_count}")

    results = []
    timeouts = 0

    # ---------------------------
    # MAIN LOOP (STRICT SEQUENTIAL)
    # ---------------------------
    for i, row in enumerate(rows):
        print(f"\n[{i+1}/{len(rows)}] Processing {row.filename}")

        # -------- SUBMIT JOB --------
        try:
            with open(row.file_path, "rb") as f:
                resp = requests.post(
                    f"{API_URL}/upload",
                    files={"file": f},
                    timeout=60
                )

            if resp.status_code not in [200, 201, 202]:
                raise Exception(f"Bad status: {resp.status_code} - {resp.text}")

            data = resp.json()

            # FIXED: API returns 'id', not 'record_id' or 'job_id'
            record_id = data.get("record_id") or data.get("job_id") or data.get("id")
            if not record_id:
                raise Exception(f"No record_id returned: {data}")

        except Exception as e:
            print(f"[UPLOAD FAILED] {row.filename}: {e}")
            continue

        print(f"Uploaded → record_id: {record_id}")

        # -------- WAIT FOR RESULT --------
        start = time.time()
        result = poll_result(record_id)
        latency = time.time() - start

        if not result:
            print(f"[TIMEOUT] {row.filename}")
            timeouts += 1
            continue

        predicted = (result.get("verdict") or "").lower()
        score = result.get("score")
        signals = result.get("signals", {})

        # -------- GROUND TRUTH CHECK --------
        if predicted == "flag_for_review":
            correct = None
        else:
            correct = predicted == row.ground_truth

        conn.execute(text("""
            UPDATE test_fixtures SET
                predicted_label   = :predicted,
                confidence_score  = :score,
                agent_reasoning   = CAST(:reasoning AS jsonb),
                verified_result   = :correct,
                evaluation_run_id = :run_id
            WHERE id = :id
        """), {
            "predicted": predicted,
            "score": score,
            "reasoning": json.dumps(signals),
            "correct": correct,
            "run_id": run_id,
            "id": row.id,
        })

        results.append({
            "ground_truth": row.ground_truth,
            "predicted": predicted,
            "score": score,
            "correct": correct,
            "latency": latency,
        })

        marker = "~" if predicted == "flag_for_review" else ("✓" if correct else "✗")
        print(f"{row.filename}: {row.ground_truth} → {predicted} {marker} ({latency:.1f}s)")

    conn.commit()


# ---------------------------
# METRICS
# ---------------------------
total = len(results)
review_count = sum(1 for r in results if r["predicted"] == "flag_for_review")
decisive = total - review_count

tp = sum(1 for r in results if r["ground_truth"] == "fake" and r["predicted"] == "fake")
tn = sum(1 for r in results if r["ground_truth"] == "real" and r["predicted"] == "real")
fp = sum(1 for r in results if r["ground_truth"] == "real" and r["predicted"] == "fake")
fn = sum(1 for r in results if r["ground_truth"] == "fake" and r["predicted"] == "real")

precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
accuracy = (tp + tn) / decisive if decisive else 0
coverage = decisive / total if total else 0

latencies = [r["latency"] for r in results]
avg_latency = sum(latencies) / len(latencies) if latencies else 0
p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

print(f"\n--- Evaluation Run: {run_id} ---")
print(f"Total evaluated: {total}")

print(f"\nConfusion Matrix")
print(f"TP: {tp} FN: {fn}")
print(f"FP: {fp} TN: {tn}")

print(f"\nMetrics")
print(f"Accuracy: {accuracy:.2%}")
print(f"Precision: {precision:.2%}")
print(f"Recall: {recall:.2%}")
print(f"F1: {f1:.2%}")
print(f"Coverage: {coverage:.2%}")

print(f"\nTimeouts: {timeouts}")

print(f"\nLatency")
print(f"Avg: {avg_latency:.1f}s")
print(f"P95: {p95_latency:.1f}s")
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


def poll_result(record_id, timeout=60):
    for _ in range(timeout):
        try:
            r = requests.get(f"{API_URL}/result/{record_id}")
            r.raise_for_status()
            data = r.json()
            if data.get("verdict") != "pending":
                return data
        except Exception as e:
            print(f"Poll error for {record_id}: {e}")
        time.sleep(1)
    return None


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

    for row in rows:
        try:
            with open(row.file_path, "rb") as f:
                resp = requests.post(
                    f"{API_URL}/upload",
                    files={"file": f}
                )
            resp.raise_for_status()
            record_id = resp.json()["record_id"]
        except Exception as e:
            print(f"Upload failed: {row.filename}: {e}")
            continue

        print(f"Uploaded {row.filename} → record_id: {record_id}")

        start = time.time()
        result = poll_result(record_id)
        latency = time.time() - start

        if not result:
            print(f"Timeout: {row.filename} — skipping")
            timeouts += 1
            continue

        predicted = result.get("verdict", "").lower()
        score = result.get("score")
        signals = result.get("signals", {})

        # Option B — review is neither correct nor incorrect
        if predicted == "flag_for_review":
            correct = None
        else:
            correct = predicted == row.ground_truth

        conn.execute(text("""
            UPDATE test_fixtures SET
                predicted_label   = :predicted,
                confidence_score  = :score,
                agent_reasoning   = :reasoning::jsonb,
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

# --- Metrics ---
total = len(results)
review_count = sum(1 for r in results if r["predicted"] == "flag_for_review")
decisive = total - review_count

tp = sum(1 for r in results if r["ground_truth"] == "fake" and r["predicted"] == "fake")
tn = sum(1 for r in results if r["ground_truth"] == "real" and r["predicted"] == "real")
fp = sum(1 for r in results if r["ground_truth"] == "real" and r["predicted"] == "fake")
fn = sum(1 for r in results if r["ground_truth"] == "fake" and r["predicted"] == "real")

precision = tp / (tp + fp) if (tp + fp) else 0
recall    = tp / (tp + fn) if (tp + fn) else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
accuracy  = (tp + tn) / decisive if decisive else 0
coverage  = decisive / total if total else 0

real_scores = [r["score"] for r in results if r["ground_truth"] == "real" and r["score"] is not None]
fake_scores = [r["score"] for r in results if r["ground_truth"] == "fake" and r["score"] is not None]
real_mean = sum(real_scores) / len(real_scores) if real_scores else 0
fake_mean = sum(fake_scores) / len(fake_scores) if fake_scores else 0
gap = fake_mean - real_mean

latencies = [r["latency"] for r in results]
avg_latency = sum(latencies) / len(latencies) if latencies else 0
p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

print(f"\n--- Evaluation Run: {run_id} ---")
print(f"Total evaluated: {total} / {len(rows)}")

print(f"\nConfusion Matrix (decisive only)")
print(f"  TP: {tp}  FN: {fn}")
print(f"  FP: {fp}  TN: {tn}")

print(f"\nCore Metrics")
print(f"  Accuracy:  {accuracy:.2%}  (on decisive only)")
print(f"  Precision: {precision:.2%}")
print(f"  Recall:    {recall:.2%}")
print(f"  F1 Score:  {f1:.2%}")
print(f"  Coverage:  {coverage:.2%}  ({decisive}/{total} decisive)")

print(f"\nReview & Availability")
print(f"  FLAG_FOR_REVIEW: {review_count} ({review_count/total:.2%})" if total else "  FLAG_FOR_REVIEW: 0")
print(f"  Timeouts:        {timeouts} ({timeouts/(total+timeouts):.2%})" if (total + timeouts) else "  Timeouts: 0")

print(f"\nScore Distribution")
print(f"  Real mean: {real_mean:.4f}")
print(f"  Fake mean: {fake_mean:.4f}")
print(f"  Gap:       {gap:.4f}")

print(f"\nLatency")
print(f"  Average: {avg_latency:.1f}s")
print(f"  P95:     {p95_latency:.1f}s")
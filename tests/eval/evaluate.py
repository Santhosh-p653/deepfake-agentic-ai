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
        r = requests.get(f"{API_URL}/result/{record_id}")
        data = r.json()
        if data["verdict"] != "pending":
            return data
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

    results = []

    for row in rows:
        with open(row.file_path, "rb") as f:
            resp = requests.post(
                f"{API_URL}/upload",
                files={"file": f}
            )

        record_id = resp.json()["record_id"]
        print(f"Uploaded {row.filename} → record_id: {record_id}")

        result = poll_result(record_id)
        if not result:
            print(f"Timeout: {row.filename} — skipping")
            continue

        predicted = result["verdict"].lower()
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
            "score": result.get("score"),
            "reasoning": str(result.get("signals", {})),
            "correct": correct,
            "run_id": run_id,
            "id": row.id,
        })

        results.append({
            "ground_truth": row.ground_truth,
            "predicted": predicted
        })
        print(f"{row.filename}: {row.ground_truth} → {predicted} {'✓' if correct else '✗'}")

    conn.commit()

# Metrics
tp = sum(1 for r in results if r["ground_truth"] == "fake" and r["predicted"] == "fake")
tn = sum(1 for r in results if r["ground_truth"] == "real" and r["predicted"] == "real")
fp = sum(1 for r in results if r["ground_truth"] == "real" and r["predicted"] == "fake")
fn = sum(1 for r in results if r["ground_truth"] == "fake" and r["predicted"] == "real")

precision = tp / (tp + fp) if (tp + fp) else 0
recall    = tp / (tp + fn) if (tp + fn) else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
accuracy  = (tp + tn) / len(results) if results else 0

print(f"\n--- Evaluation Run: {run_id} ---")
print(f"Accuracy:  {accuracy:.2%}")
print(f"Precision: {precision:.2%}")
print(f"Recall:    {recall:.2%}")
print(f"F1 Score:  {f1:.2%}")
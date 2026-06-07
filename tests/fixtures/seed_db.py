import os
import json
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

DATASET_DIR = "tests/fixtures/deepfake_subset"
LABELS_PATH = os.path.join(DATASET_DIR, "metadata/labels.json")

with open(LABELS_PATH) as f:
    labels = json.load(f)

with engine.connect() as conn:
    for rel_path, meta in labels.items():
        filename = os.path.basename(rel_path)
        file_path = os.path.join(DATASET_DIR, "images", rel_path)
        ground_truth = meta["type"]  # "real" or "fake"
        size = os.path.getsize(file_path)

        exists = conn.execute(
            text("SELECT 1 FROM test_fixtures WHERE filename = :f"),
            {"f": filename}
        ).fetchone()

        if exists:
            print(f"Skipping {filename} — already seeded")
            continue

        conn.execute(text("""
            INSERT INTO test_fixtures
                (filename, file_path, file_type, mime_type,
                 file_size_bytes, ground_truth)
            VALUES
                (:filename, :file_path, :file_type, :mime_type,
                 :size, :ground_truth)
        """), {
            "filename": filename,
            "file_path": file_path,
            "file_type": "image",
            "mime_type": "image/jpeg",
            "size": size,
            "ground_truth": ground_truth,
        })
        print(f"Seeded {filename} as {ground_truth}")

    conn.commit()
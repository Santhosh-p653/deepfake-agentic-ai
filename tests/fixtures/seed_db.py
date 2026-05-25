import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

FIXTURES = {
    "tests/fixtures/fake": "fake",
    "tests/fixtures/real": "real",
}

with engine.connect() as conn:
    for folder, ground_truth in FIXTURES.items():
        for filename in os.listdir(folder):
            if filename.startswith("."):
                continue

            filepath = os.path.join(folder, filename)
            size = os.path.getsize(filepath)

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
                "file_path": filepath,
                "file_type": "image",
                "mime_type": "image/jpeg",
                "size": size,
                "ground_truth": ground_truth,
            })
            print(f"Seeded {filename} as {ground_truth}")

    conn.commit()
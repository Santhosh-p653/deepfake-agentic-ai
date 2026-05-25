CREATE TABLE IF NOT EXISTS test_fixtures (
    id                SERIAL PRIMARY KEY,
    filename          TEXT NOT NULL UNIQUE,
    file_path         TEXT NOT NULL,
    file_type         TEXT,
    mime_type         TEXT,
    file_size_bytes   INTEGER,
    ground_truth      TEXT NOT NULL,
    predicted_label   TEXT,
    confidence_score  FLOAT,
    agent_reasoning   JSONB,
    verified_result   BOOLEAN,
    evaluation_run_id TEXT
);
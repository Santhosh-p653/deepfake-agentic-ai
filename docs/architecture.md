
# 🏗️ System Architecture — Deepfake Agentic AI

This document describes the current architecture of the system. It follows a containerized,
agent-based microservices design with isolated services packaged as independent Docker images
and deployed via Docker Compose. All images are pushed to GHCR on every merge to `main`.

---

## Overview

```
Client
  └── POST /upload
        └── API Service (FastAPI)
              ├── Input Validation (format + encoding)
              ├── PostgreSQL (metadata write)
              ├── /app/tmp (temp file write, max 2)
              ├── ML Service (inference via HTTP) ← stub until wired
              ├── MinIO (file push after ML)
              └── Structured JSON Logging (all stages)
```

Inter-service communication is HTTP over an internal Docker bridge network.
No service accesses another's filesystem or database directly.

---

## Services

### 1. API Service
**Port:** `8000`
**Role:** Entry point for all client requests. Handles validation, orchestration, DB writes,
temp file management, and MinIO uploads.

- FastAPI + SQLAlchemy + psycopg2
- Validates format (`.jpeg`, `.png`, `.mp4`) and encoding on every upload
- Enforces 2-file temp cap via DB-level `FOR UPDATE` lock
- Transitions file through status pipeline: `pending → temp_stored → processing → processed → deleted`
- Emits structured JSON logs to stdout and `logs/app.log`
- Containerized with lightweight Python base image
- Runs independently of ML workloads — no model weights loaded here

---

### 2. ML Service
**Role:** Deepfake detection and inference.

- Receives file path or bytes from API via HTTP
- Runs RetinaFace → Xception → Transformer pipeline
- Returns `deepfake_probability` and model metadata
- Separate Dockerfile optimized for ML dependencies (larger image)
- Keeps model weights and heavy libraries out of the API container
- Prevents memory contention between inference and request handling
- Currently stubbed in `ml_stub.py` — real wiring is next

**Detection pipeline:**
```

RetinaFace        → face localization + landmark alignment
Xception CNN      → forensic feature extraction (texture artifacts)
Transformer       → temporal coherence modeling (frame jitter/blending)
```

---

### 3. Agents Service
**Port:** `8123`
**Role:** Orchestration brain. Receives requests from the API and coordinates
multi-agent workflows using LangGraph.

```
Before: API → docker run agents (job container)
After:  API → HTTP request → agents service (persistent container)
```

- LangGraph + ChromaDB
- Lightweight Python image, minimal dependencies
- Communicates with API via internal bridge network
- Keeps orchestration logic isolated from inference and storage
- ChromaDB stores high-dimensional facial embeddings for similarity search

---

### 4. Database & Storage Services

#### PostgreSQL
**Role:** Primary metadata store. Never stores media bytes.

- Official `postgres:15` image
- Data persisted via Docker named volume (`postgres_data`)
- ORM: SQLAlchemy
- Schema managed via `Base.metadata.create_all()` on startup

**Table: `media_uploads`**

| Column       | Type     | Description                          |
|--------------|----------|--------------------------------------|
| id           | Integer  | Primary key                          |
| user_id      | Integer  | Optional user reference              |
| filename     | String   | Original filename                    |
| file_type    | String   | Extension                            |
| size_mb      | Float    | File size in MB                      |
| status       | Enum     | Pipeline status                      |
| temp_path    | String   | `/app/tmp` path during processing    |
| drive_path   | String   | MinIO object name post-upload        |
| uploaded_at  | DateTime | Upload timestamp (UTC)               |
| processed_at | DateTime | ML completion timestamp (UTC)        |

#### MinIO
**Ports:** `9000` (API), `9001` (UI)
**Role:** Time-based object cache for processed media files.

- Files pushed after ML processing completes
- 30-day auto-delete lifecycle rule on `deepfakemedia` bucket
- Presigned URLs for re-access (24-hour expiry)
- Not a permanent store — treat as cache, not archive

#### ChromaDB
**Role:** Vector store for facial embeddings.
- Managed by the agents service
- Used for similarity search against known manipulation patterns

---

## Network & Container Layout

```

bridge_network (internal Docker network)
  ├── api          :8000
  ├── agents       :8123
  ├── ml           (internal only)
  ├── db           :5432
  ├── minio        :9000 / :9001
  ├── dozzle       :8080  (log viewer)
  └── beszel       :8090  (metrics dashboard)
```

All services communicate over `bridge_network`. No service exposes unnecessary ports externally.

---

## File Lifecycle

```
Upload
  └── Validate (format + encoding)
        └── Write → /app/tmp (max 2 files, DB-enforced cap)
              └── ML inference (stub → real service)
                    └── Push → MinIO (deepfakemedia bucket)
                          └── Delete → /app/tmp
                                └── Auto-delete → MinIO at 30 days
```

| Stage      | DB Status     |
|------------|---------------|
| Received   | `pending`     |
| On disk    | `temp_stored` |
| ML running | `processing`  |
| ML done    | `processed`   |
| Cleaned up | `deleted`     |
| Error      | `failed`      |

---

## Logging

All modules emit structured JSON to stdout and `logs/app.log`.

```json
{
  "timestamp": "2026-04-23T10:45:00.123Z",
  "level": "INFO",
  "module": "api.main",
  "message": "Upload pipeline complete",
  "id": 1,
  "filename": "image.jpg",
  "size_mb": 0.452
}
```

- Live view: Dozzle at `http://localhost:8080`
- File view: `logs/app.log`
- CI validation: `api/validate_logs.py` runs on every push

---

## CI/CD

All images built and pushed to GHCR on merge to `main`.

| Workflow               | Purpose                                         |
|------------------------|-------------------------------------------------|
| `ci-api.yml`           | Lint, format, build + push API image            |
| `ci-agents.yml`        | Lint, format, build + push agents image         |
| `ci-ml.yml`            | Lint, format, build + push ML image             |
| `ci-tests.yml`         | Pytest — API and ML unit tests                  |
| `ci-network-audit.yml` | Network audit, upload test, log validation      |
| `codespaces-prebuild`  | Prebuild images for GitHub Codespaces           |

---

## Implementation Status

### Input Pipeline

| Step | Description                              | Status  |
|------|------------------------------------------|---------|
| 1    | Input validation                         | ✅ Done |
| 2    | PostgreSQL metadata schema               | ✅ Done |
| 3    | Docker temp folder management            | ✅ Done |
| 4    | MinIO integration + 30-day lifecycle     | ✅ Done |
| 5    | Structured JSON logging                  | ✅ Done |
| 6    | CI network audit + logging validation    | ✅ Done |

### ML Integration

| Step | Description                              | Status      |
|------|------------------------------------------|-------------|
| 1    | `/results/{id}` endpoint                 | 🔜 Next     |
| 2    | Wire real ML service — replace stub      | 🔜 Planned  |
| 3    | RetinaFace → Xception → Transformer      | 🔜 Planned  |
| 4    | Store `deepfake_probability` in DB       | 🔜 Planned  |

### Tests

| Task | Description                              | Status      |
|------|------------------------------------------|-------------|
| —    | Parallel upload + race condition test    | 🔜 Planned  |
| —    | Deadlock / lock contention test          | 🔜 Planned  |

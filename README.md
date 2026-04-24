
# 🛡️ Deepfake Agentic AI
**High-performance forensic analysis leveraging Computer Vision and Agentic Workflows.**

Deepfake Agentic AI is a sophisticated, service-oriented system designed to detect spatial and temporal
inconsistencies in digital media. By utilizing a multi-stage pipeline from face alignment to
transformer-based temporal analysis it provides an industry-standard approach to verifying media
authenticity.

---

## 🏗️ System Architecture & Workflow

The system is built as a modular microservices mesh, ensuring that compute-intensive tasks like deep
learning inference do not bottleneck the API responsiveness.

1. **Preprocessing (FFmpeg & OpenCV)**: Handles high-speed frame extraction and isolates audio streams
   for potential multi-modal forensic checks.
2. **Detection Pipeline**:
   - **RetinaFace**: Performs high-accuracy facial localization and landmark alignment to normalize input data.
   - **Xception**: A CNN backbone specialized in forensic feature extraction, detecting artifacts in facial textures.
   - **Transformers**: Models the "temporal coherence" between frames to identify jitter or blending errors common in deepfakes.
3. **Vector Intelligence (ChromaDB)**: Stores high-dimensional facial embeddings to perform similarity
   search and identify known manipulation patterns.
4. **Backend (FastAPI & PostgreSQL)**: Manages high-concurrency API requests, stores metadata, and
   maintains a persistent audit log of all scans.
5. **Object Storage (MinIO)**: Stores processed media files with automatic 30-day expiry after ML
   processing completes.
6. **Structured Logging**: JSON-formatted logs across all modules written to stdout and `logs/app.log`
   for audit and replay.

---

## 🚀 Getting Started

### 📋 Prerequisites

- **Docker & Docker Compose** installed
- **Git** installed and configured

---

### ⚙️ Installation & Deployment

```bash
# 1️⃣ Clone the repository
git clone https://github.com/Santhosh-p653/deepfake-agentic-ai.git
cd deepfake-agentic-ai

# 2️⃣ Copy and configure environment variables
cp .env.example .env
# Edit .env with your actual values

# 3️⃣ Start the full environment
docker compose up -d --build

# 4️⃣ Start only the API service (brings DB and MinIO up with it)
docker compose up --build api

# 5️⃣ Wipe all volumes and restart clean (dev reset)
docker compose down -v && docker compose up --build api
```

---

## 🌐 Services & URLs

| Service    | URL                        | Description                        |
|------------|----------------------------|------------------------------------|
| API        | http://localhost:8000      | FastAPI — main entry point         |
| API Docs   | http://localhost:8000/docs | Auto-generated Swagger UI          |
| MinIO UI   | http://localhost:9001      | Object storage browser             |
| Dozzle     | http://localhost:8080      | Live Docker log viewer             |
| Beszel     | http://localhost:8090      | Container metrics dashboard        |
| Agents     | http://localhost:8123      | LangGraph agent service            |

> MinIO default credentials: `minioadmin / minioadmin` — change in production.

---

## 📡 API Endpoints

### General

| Method | Endpoint      | Description                      |
|--------|---------------|----------------------------------|
| GET    | `/ping`       | Liveness check — returns `pong`  |
| GET    | `/health`     | DB connection status check       |
| GET    | `/run-agents` | Trigger LangGraph agent pipeline |

### Media

| Method | Endpoint         | Description                               |
|--------|------------------|-------------------------------------------|
| POST   | `/upload`        | Upload a media file for deepfake analysis |
| GET    | `/results/{id}`  | Get detection result by record ID *(upcoming)* |

---

### `POST /upload`

**Accepted formats:** `.jpeg`, `.png`, `.mp4`

**Request:** `multipart/form-data` with field `file`

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/image.jpg"
```

**Success response `200`:**
```json
{
  "status": "accepted",
  "id": 1,
  "filename": "image.jpg",
  "size_mb": 0.452,
  "ml_result": {
    "deepfake_probability": 0.07,
    "model": "stub",
    "file_path": "/app/tmp/abc123.jpg"
  },
  "minio_object": "def456.jpg"
}
```

**Rejection responses:**

| Status | Reason                                  |
|--------|-----------------------------------------|
| 400    | Invalid format or encoding mismatch     |
| 429    | Temp storage at capacity (2 files max)  |
| 500    | DB error or failed to write temp file   |

---

## 🗄️ Media Pipeline — File Lifecycle

```
Upload → /app/tmp (max 2 files) → ML processing → MinIO bucket → auto-delete at 30 days
```

| Stage      | DB Status     | Description                              |
|------------|---------------|------------------------------------------|
| Received   | `pending`     | Record created, file not yet on disk     |
| On disk    | `temp_stored` | File written to `/app/tmp`               |
| ML running | `processing`  | ML invoked (stub until real ML wired)    |
| ML done    | `processed`   | Result returned, file pushed to MinIO    |
| Cleaned up | `deleted`     | Temp file removed from `/app/tmp`        |
| Error      | `failed`      | Any stage failure                        |

---

## 🗃️ Database Schema

**Table: `media_uploads`**

| Column       | Type     | Description                             |
|--------------|----------|-----------------------------------------|
| id           | Integer  | Primary key                             |
| user_id      | Integer  | Optional user reference                 |
| filename     | String   | Original uploaded filename              |
| file_type    | String   | Extension (`jpeg`, `png`, `mp4`)        |
| size_mb      | Float    | File size in MB                         |
| status       | Enum     | Current pipeline status (see above)     |
| temp_path    | String   | Path in `/app/tmp` while processing     |
| drive_path   | String   | MinIO object name after upload          |
| uploaded_at  | DateTime | Upload timestamp (UTC)                  |
| processed_at | DateTime | ML completion timestamp (UTC)           |

---

## 📦 Object Storage — MinIO

- **Bucket:** `deepfakemedia`
- **Lifecycle:** Files auto-deleted 30 days after ML processing
- **Re-access:** Presigned URLs generated on demand (24-hour expiry by default)
- **UI:** http://localhost:9001

---

## 📋 Structured Logging

All modules emit structured JSON logs to stdout and `logs/app.log`.

**Log format:**
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

**View live logs:**
- Terminal: `docker compose logs -f api`
- Dozzle UI: http://localhost:8080

---

## 🔧 Environment Variables

Create a `.env` file in the root directory. Never commit real credentials.

```env
# PostgreSQL
DATABASE_URL=postgresql://<user>:<password>@db:5432/<dbname>

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<your-access-key>
MINIO_SECRET_KEY=<your-secret-key>
MINIO_BUCKET=deepfakemedia
```

All secrets are injected via GitHub Secrets in CI — never hardcoded in workflows.

---

## 📁 Project Structure

```
deepfake-agentic-ai/
├── api/
│   ├── main.py             # FastAPI app, endpoints, upload pipeline
│   ├── db.py               # SQLAlchemy engine, session, helpers
│   ├── models.py           # MediaUpload ORM model, ProcessingStatus enum
│   ├── input_validator.py  # Format and encoding validation
│   ├── temp_manager.py     # Temp folder write/delete/cleanup
│   ├── minio_client.py     # MinIO upload, lifecycle, presigned URLs
│   ├── ml_stub.py          # ML placeholder — replaced when ML service wired
│   ├── logger.py           # Central JSON logger
│   └── validate_logs.py    # CI log validation script
├── agents/                 # LangGraph agent service
├── ml/                     # RetinaFace + Xception + Transformers
├── logs/                   # JSON log output (auto-created, gitignored)
├── .github/
│   └── workflows/
│       ├── ci-api.yml              # Lint, format, build API
│       ├── ci-agents.yml           # Lint, format, build agents
│       ├── ci-ml.yml               # Lint, format, build ML
│       ├── ci-tests.yml            # Pytest — API and ML
│       ├── ci-network-audit.yml    # Network audit + log validation
│       └── codespaces-prebuild.yml # Codespaces image prebuild
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.agents
├── Dockerfile.ml
├── .env.example
└── .env                    # Never commit — add to .gitignore
```

---

## 🛠️ Implementation Status

### Input Pipeline & Infrastructure

| Step | Description                                      | Status     |
|------|--------------------------------------------------|------------|
| 1    | Input validation — format + encoding check       | ✅ Done    |
| 2    | PostgreSQL metadata schema                       | ✅ Done    |
| 3    | Docker temp folder management                    | ✅ Done    |
| 4    | MinIO integration — push after ML, 30-day expiry | ✅ Done    |
| 5    | Structured JSON logging across all modules       | ✅ Done    |
| 6    | CI workflow — network audit + logging validation | ✅ Done    |

### ML Integration (Up Next)

| Step | Description                                      | Status     |
|------|--------------------------------------------------|------------|
| 1    | `/results/{id}` endpoint                         | 🔜 Next    |
| 2    | Wire real ML service — replace stub              | 🔜 Planned |
| 3    | RetinaFace → Xception → Transformer pipeline     | 🔜 Planned |
| 4    | Store `deepfake_probability` in PostgreSQL        | 🔜 Planned |

### Tests

| Task | Description                                      | Status     |
|------|--------------------------------------------------|------------|
| —    | Parallel upload + race condition test            | 🔜 Planned |
| —    | Deadlock / lock contention test                  | 🔜 Planned |

---

## 🔬 CI Workflows

| Workflow               | Trigger          | What it does                                      |
|------------------------|------------------|---------------------------------------------------|
| `ci-api.yml`           | push/PR to main  | Black, isort, flake8, build & push API image      |
| `ci-agents.yml`        | push/PR to main  | Black, isort, flake8, build & push agents image   |
| `ci-ml.yml`            | push/PR to main  | Black, isort, flake8, build & push ML image       |
| `ci-tests.yml`         | push/PR to main  | Pytest — API and ML unit tests                    |
| `ci-network-audit.yml` | push/PR to main  | Network audit, upload test, JSON log validation   |
| `codespaces-prebuild`  | push to codespaces/main | Prebuild API, agents, ML images for Codespaces |

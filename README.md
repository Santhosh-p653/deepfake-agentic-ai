
# 🛡️ Deepfake Agentic AI
**High-performance forensic analysis leveraging Computer Vision and Agentic Workflows.**

Deepfake Agentic AI is a sophisticated, service-oriented system designed to detect spatial and temporal
inconsistencies in digital media. By utilizing a multi-signal pipeline — preprocessing quality analysis,
CNN-based face detection, and LLM-powered log analysis — it provides an industry-standard approach to
verifying media authenticity.

---

## 🏗️ System Architecture & Workflow

The system is built as a modular microservices mesh, ensuring that compute-intensive tasks like deep
learning inference do not bottleneck the API responsiveness.

**Flow:** `File Input → API Service → ML Service → Agent Service → Verdict or Human Review`

1. **API Service (FastAPI + PostgreSQL)**: Accepts and validates media, manages the upload pipeline,
   stores metadata, and returns the final verdict to the client.
2. **ML Service (OpenCV + RetinaFace + Xception)**: Preprocesses media and runs deepfake detection.
   Each module produces a **Signal** — a score and a reliability value.
3. **Agent Service (LangGraph + SambaNova LLM)**: Reads structured logs, identifies anomalies,
   aggregates all signals weighted by reliability, and routes the final verdict.
4. **Signal Contract**: Every module outputs `{ score, reliability, module, metadata }`.
   The aggregator weights signals at runtime — adaptive, not fixed constants.
5. **Object Storage (MinIO)**: Stores processed media files with automatic 30-day expiry.
6. **Structured Logging**: JSON-formatted logs across all modules written to stdout and `logs/app.log`.

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
| ML         | http://localhost:8001      | ML service — preprocessing + detection |
| MinIO UI   | http://localhost:9001      | Object storage browser             |
| Dozzle     | http://localhost:8080      | Live Docker log viewer             |
| Beszel     | http://localhost:8090      | Container metrics dashboard        |
| Agents     | http://localhost:8123      | Agent service — log analyser, aggregator, decider |

> MinIO default credentials: `minioadmin / minioadmin` — change in production.

---

## 📡 API Endpoints

### General

| Method | Endpoint      | Description                      |
|--------|---------------|----------------------------------|
| GET    | `/ping`       | Liveness check — returns `pong`  |
| GET    | `/health`     | DB connection status check       |
| GET    | `/run-agents` | Ping agent service               |

### Media

| Method | Endpoint           | Description                               |
|--------|--------------------|-------------------------------------------|
| POST   | `/upload`          | Upload a media file for deepfake analysis |
| GET    | `/result/{id}`     | Poll for detection verdict by record ID   |
| POST   | `/verdict`         | Internal — agents post verdict back to API |

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

### `GET /result/{id}`

Poll this after upload to retrieve the final verdict once the pipeline completes.

```bash
curl http://localhost:8000/result/1
```

**Response:**
```json
{
  "id": 1,
  "filename": "image.jpg",
  "status": "completed",
  "verdict": "REAL",
  "verdict_score": 0.21,
  "uploaded_at": "2026-04-25T10:00:00Z",
  "processed_at": "2026-04-25T10:00:05Z"
}
```

**Verdict values:** `REAL` · `FAKE` · `FLAG_FOR_REVIEW`

---

## 🔁 Full Pipeline Flow

```
POST /upload
  → Validate (format + encoding)
  → Write to /app/tmp
  → Push to MinIO
  → [async] POST agents/run
      → agents calls ml/process
          → ml: preprocess → detect → return Signals
      → agents: log analyser → Signal
      → agents: aggregate all Signals (weighted by reliability)
      → agents: decider → verdict
      → agents POST api/verdict
  → GET /result/{id} returns verdict to client
```

---

## 🗄️ Media Pipeline — File Lifecycle

```
Upload → /app/tmp (max 2 files) → ML processing → MinIO bucket → auto-delete at 30 days
```

| Stage      | DB Status     | Description                              |
|------------|---------------|------------------------------------------|
| Received   | `pending`     | Record created, file not yet on disk     |
| On disk    | `temp_stored` | File written to `/app/tmp`               |
| ML running | `processing`  | ML invoked                               |
| ML done    | `processed`   | Result returned, file pushed to MinIO    |
| Cleaned up | `deleted`     | Temp file removed from `/app/tmp`        |
| Verdict in | `completed`   | Verdict stored, pipeline done            |
| Error      | `failed`      | Any stage failure                        |

---

## 🗃️ Database Schema

**Table: `media_uploads`**

| Column        | Type     | Description                             |
|---------------|----------|-----------------------------------------|
| id            | Integer  | Primary key                             |
| user_id       | Integer  | Optional user reference                 |
| filename      | String   | Original uploaded filename              |
| file_type     | String   | Extension (`jpeg`, `png`, `mp4`)        |
| size_mb       | Float    | File size in MB                         |
| status        | Enum     | Current pipeline status (see above)     |
| temp_path     | String   | Path in `/app/tmp` while processing     |
| drive_path    | String   | MinIO object name after upload          |
| verdict       | String   | Final verdict: REAL / FAKE / FLAG_FOR_REVIEW |
| verdict_score | Float    | Final aggregated score (0.0 – 1.0)      |
| uploaded_at   | DateTime | Upload timestamp (UTC)                  |
| processed_at  | DateTime | ML completion timestamp (UTC)           |

---

## 📦 Object Storage — MinIO

- **Bucket:** `deepfakemedia`
- **Lifecycle:** Files auto-deleted 30 days after ML processing
- **Re-access:** Presigned URLs generated on demand (24-hour expiry by default)
- **UI:** http://localhost:9001

---

## 🧠 Signal Contract

Every module that produces a judgment outputs this schema:

```json
{
  "score": 0.0,
  "reliability": 0.0,
  "module": "ml.preprocessing",
  "metadata": {}
}
```

- `score` — judgment value, 0.0 to 1.0
- `reliability` — trust in that score, 0.0 to 1.0
- `module` — which module produced this
- `metadata` — module-specific context

The aggregator weights signals at runtime using reliability values — not fixed constants.

---

## 🤖 Agent Service — Decision Logic

**Decider paths:**

| Path | Condition | Action |
|------|-----------|--------|
| 1 | High confidence score | Output verdict directly |
| 2 | Low confidence score | Flag for human review |
| 3a | Middle zone (~45–55%) | Reanalyse once, adjust all module weights uniformly |
| 3b | 70/30 module conflict | Reanalyse once, adjust only conflicting modules |

**Governance rules:**
- One reanalysis attempt maximum — hard blocked after one
- Every weight adjustment logged: before, after, reason, affected modules
- All thresholds TBD via experimentation and version-controlled

---

## 📋 Structured Logging

All modules emit structured JSON logs to stdout and `logs/app.log`.

**Log format:**
```json
{
  "timestamp": "2026-04-25T10:45:00.123Z",
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

# SambaNova LLM (agent log analyser)
SAMBANOVA_API_KEY=<your-key>
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
│   ├── ml_stub.py          # ML placeholder (active until Detection unblocked)
│   ├── logger.py           # Central JSON logger
│   └── validate_logs.py    # CI log validation script
├── agents/
│   ├── main.py             # FastAPI app, /run /analyse /ping endpoints
│   ├── log_analyser.py     # SambaNova LLM log anomaly detection
│   ├── aggregator.py       # Runtime reliability-weighted signal aggregation
│   ├── decider.py          # Threshold routing, reanalysis hard block
│   └── ml_client.py        # HTTP client — calls ml /process
├── ml/
│   ├── main.py             # FastAPI app, /process endpoint
│   ├── preprocessing.py    # Frame extraction, quality checks, normalisation
│   └── detection.py        # Detection stub (RetinaFace+Xception — see issue)
├── shared/
│   └── signal.py           # Pydantic Signal model — shared across all services
├── logs/                   # JSON log output (auto-created, gitignored)
├── .github/
│   └── workflows/
│       ├── ci-api.yml              # Lint, format, build & push API image
│       ├── ci-agents.yml           # Lint, format, build & push agents image
│       ├── ci-ml.yml               # Lint, format, build & push ML image
│       ├── ci-tests.yml            # Pytest — API and ML unit tests
│       ├── ci-network-audit.yml    # Network audit + log validation
│       └── codespaces-prebuild.yml # Codespaces image prebuild
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.agents
├── Dockerfile.ml
├── .env.example
└── .env                    # Never commit — gitignored
```

---

## 🛠️ Implementation Status

### Phase 1 — Input Pipeline & Infrastructure

| Step | Description                                      | Status     |
|------|--------------------------------------------------|------------|
| 1    | Input validation — format + encoding check       | ✅ Done    |
| 2    | PostgreSQL metadata schema                       | ✅ Done    |
| 3    | Docker temp folder management                    | ✅ Done    |
| 4    | MinIO integration — push after ML, 30-day expiry | ✅ Done    |
| 5    | Structured JSON logging across all modules       | ✅ Done    |
| 6    | CI workflow — network audit + logging validation | ✅ Done    |

### Phase 2 — Multi-Signal Pipeline

| Step | Description                                      | Status     |
|------|--------------------------------------------------|------------|
| 1    | Signal contract — shared Pydantic model          | ✅ Done    |
| 2    | ML preprocessing — quality checks + normalisation | ✅ Done   |
| 3    | ML detection — RetinaFace + Xception             | ⚠️ Stubbed — [see issue](https://github.com/Santhosh-p653/deepfake-agentic-ai/issues) |
| 4    | Agent log analyser — SambaNova LLM               | ✅ Done    |
| 5    | Aggregator + Decider — full pipeline wired       | ✅ Done    |
| 2C   | GET /result/{id} — client verdict polling        | ✅ Done    |

### Pending

| Task | Description                                      | Status     |
|------|--------------------------------------------------|------------|
| —    | Real RetinaFace + Xception detection             | 🔜 Blocked by bandwidth |
| —    | Threshold experimentation + version control      | 🔜 Needs real data |
| —    | Decider Path 3a/3b full reanalysis logic         | 🔜 Needs real data |
| —    | Authentication + rate limiting                   | 🔜 Planned |
| —    | Frontend UI                                      | 🔜 Planned |

---

## 🔬 CI Workflows

| Workflow               | Trigger                  | What it does                                      |
|------------------------|--------------------------|---------------------------------------------------|
| `ci-api.yml`           | push/PR to main          | Black, isort, flake8, build & push API image      |
| `ci-agents.yml`        | push/PR to main          | Black, isort, flake8, build & push agents image   |
| `ci-ml.yml`            | push/PR to main          | Black, isort, flake8, build & push ML image       |
| `ci-tests.yml`         | push/PR to main          | Pytest — API and ML unit tests                    |
| `ci-network-audit.yml` | push/PR to main          | Network audit, upload test, JSON log validation   |
| `codespaces-prebuild`  | push to codespaces/main  | Prebuild API, agents, ML images for Codespaces    |

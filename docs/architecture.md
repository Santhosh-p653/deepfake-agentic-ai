
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
              ├── ML Service (RetinaFace + SigLIP inference via HTTP)
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
**Role:** Deepfake detection and inference (System 1 Perceptual Layer).

- Receives file path or bytes from API via HTTP (`POST /process`)
- Runs RetinaFace face detection and SiglipForImageClassification (`prithivMLmods/deepfake-detector-model-v1`)
- Runs media preprocessing: Laplacian blur variance, resolution checks, and metadata extraction
- Emits standardized `Signal` contracts `{ score, reliability, module, metadata }`
- Separate Dockerfile optimized for ML dependencies (PyTorch, torchvision, transformers, OpenCV)
- Keeps model weights and heavy libraries out of the API container
- Prevents memory contention between inference and request handling

**Detection pipeline:**
```
Frame / Image 
  ├── OpenCV Preprocessing → Quality & blur analysis → Signal(ml.preprocessing)
  └── RetinaFace (PyTorch) → Crop & score faces via SigLIP → Signal(ml.detection)
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
  ├── ui           :8501  (Streamlit frontend)
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

### Phase 1 — Input Pipeline & Infrastructure ✅

| Step | Description                              | Status  |
|------|------------------------------------------|---------|
| 1    | Input validation (magic bytes & format)  | ✅ Done |
| 2    | PostgreSQL metadata schema               | ✅ Done |
| 3    | Docker temp folder management            | ✅ Done |
| 4    | MinIO integration + 30-day lifecycle     | ✅ Done |
| 5    | Structured JSON logging                  | ✅ Done |
| 6    | CI network audit + logging validation    | ✅ Done |

### Phase 2 — Multi-Signal Pipeline & Agents ✅

| Step | Description                                         | Status  |
|------|-----------------------------------------------------|---------|
| 1    | Signal contract — shared Pydantic model             | ✅ Done |
| 2    | ML preprocessing — blur, resolution, and quality    | ✅ Done |
| 3    | LLM log analyser — Gemma via SambaNova              | ✅ Done |
| 4    | Source verifier — metadata forensics                | ✅ Done |
| 5    | Aggregator + Decider — reliability weighting        | ✅ Done |
| 6    | Streamlit UI — real-time verification dashboard     | ✅ Done |

### Phase 3 — Detection & Evaluation Framework 🔄

| Step | Description                                         | Status         |
|------|-----------------------------------------------------|----------------|
| 1    | RetinaFace + Siglip detection (`prithivMLmods`)     | ✅ Done        |
| 2    | Unit tests with mocked ML in CI                     | ✅ Done        |
| 3    | Evaluation pipeline on Kaggle 140k real/fake faces  | ✅ Done        |
| 4    | Threshold tuning & calibration                      | 🔄 In Progress |

---

## 🔮 Future Architecture Evolution: Dual-Process Cognitive Forensics (System 1 + System 2)

As detailed in [docs/roadmap.md](file:///home/santhosh/deepfake-agentic-ai/docs/roadmap.md), the system is advancing toward an uncertainty-gated **Dual-Process Cognitive Architecture**:

```
                       ┌─────────────────────────────────────────┐
                       │               Media Input               │
                       └────────────────────┬────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │      System 1: Fast Perceptual Reflex         │
                    │   (SigLIP ViT + Frequency SRM/FFT Head)       │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │  Cognitive Gatekeeper │
                                │  (Uncertainty Check)  │
                                └───┬───────────────┬───┘
                                    │               │
            Definitive Verdict      │               │ High Uncertainty /
            (P > 0.85 or P < 0.15)  │               │ Ambiguous (0.30 - 0.70)
                                    ▼               ▼
                      ┌───────────────────┐   ┌───────────────────────────┐
                      │   Fast-Path Exit  │   │  System 2: Agentic Bus    │
                      │   (<100ms bypass) │   │  • Multi-Agent Debate     │
                      └───────────────────┘   │  • Provenance/EXIF Check  │
                                              │  • LLM Judge (SambaNova)  │
                                              └─────────────┬─────────────┘
                                                            │
                                                            ▼
                                              ┌───────────────────────────┐
                                              │ Explainable Forensic Rpt  │
                                              └───────────────────────────┘
```

### Key Architectural Enhancements
1. **System 1 Decision Head & Triage:** Lightweight multi-signal classifier with conformal uncertainty estimation to fast-exit $>75\%$ of clean media in $<100\text{ms}$.
2. **Cognitive Gatekeeper:** Dynamic routing that escalates only ambiguous, anomalous, or conflicting samples to System 2.
3. **System 2 Deliberative Multi-Agent Forensics:** LangGraph-coordinated debate between visual artifact, provenance, and forensic judge agents producing legally defensible, explainable audit logs.
4. **Metacognitive Feedback Loop:** Hard-negative feedback from System 2 deliberative verdicts to continuously fine-tune System 1 decision thresholds.

*For full specification, formulas, and milestones, see [docs/roadmap.md](file:///home/santhosh/deepfake-agentic-ai/docs/roadmap.md).*

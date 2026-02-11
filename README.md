

###Deepfake Agentic AI
A high-performance, agent-based deepfake detection system leveraging Computer Vision (CV), Deep Learning (DL), and Vector Similarity Search. This project provides a robust pipeline for analyzing temporal and spatial inconsistencies in digital media to verify authenticity.

System Architecture
The system is designed with a modular service-oriented architecture to handle compute-intensive inference tasks:

Preprocessing: FFmpeg and OpenCV for precise frame extraction and audio stream isolation.

Detection Pipeline: * RetinaFace: High-accuracy face detection and alignment.

Xception: Feature extraction optimized for forensic facial analysis.

Transformers: Temporal modeling to detect inconsistencies across video frames.

Vector Engine: ChromaDB for high-dimensional vector search and similarity matching.

Backend & Orchestration: * FastAPI: High-concurrency inference APIs.

PostgreSQL: Relational storage for metadata and audit logs.

Docker: Full containerization for reproducible environments.

 Getting Started
Prerequisites
Docker and Docker Compose

Git

Installation
Clone the repository:

Bash
git clone https://github.com/Santhosh-p653/deepfake-agentic-ai
cd deepfake-agentic-ai
Spin up the environment: The entire stack (API, Database, and Vector Store) is orchestrated via Docker:

Bash
docker compose up -d --build
The API will be accessible at http://localhost:8000.

 Development Workflow
System Health
To verify the integrity of the service mesh and database connectivity, visit the automated health check endpoint: http://localhost:8000/health

Modifying the Source
The core logic resides in the /api directory. If you modify the source code or update dependencies:

Add new packages to requirements.txt.

Rebuild and restart the containers:

Bash
docker compose up -d --build
Resource Management
Stop Services: docker compose down

View Logs: docker compose logs -f

 Current Status
[x] Core infrastructure and service orchestration resolved.

[x] Stable environment for database and API interaction.

[ ] Integration of Transformer-based temporal modeling (In Progress).

For a deep dive into the underlying logic, see docs/architecture.md. If you encounter environment-specific issues (WSL, DNS, or Postgres connectivity), refer to the Troubleshooting Guide.


# 🛡️ Deepfake Agentic AI
**High-performance forensic analysis leveraging Computer Vision and Agentic Workflows.**

Deepfake Agentic AI is a sophisticated, service-oriented system designed to detect spatial and temporal inconsistencies in digital media. By utilizing a multi-stage pipeline—from face alignment to transformer-based temporal analysis—it provides an industry-standard approach to verifying media authenticity.

---

## 🏗️ System Architecture & Workflow

The system is built as a modular microservices mesh, ensuring that compute-intensive tasks like deep learning inference do not bottleneck the API responsiveness.

1.  **Preprocessing (FFmpeg & OpenCV)**: Handles high-speed frame extraction and isolates audio streams for potential multi-modal forensic checks.
2.  **Detection Pipeline**:
    * **RetinaFace**: Performs high-accuracy facial localization and landmark alignment to normalize input data.
    * **Xception**: A CNN backbone specialized in forensic feature extraction, detecting artifacts in facial textures.
    * **Transformers**: Models the "temporal coherence" between frames to identify jitter or blending errors common in deepfakes.
3.  **Vector Intelligence (ChromaDB)**: Stores high-dimensional facial embeddings to perform similarity search and identify known manipulation patterns.
4.  **Backend (FastAPI & PostgreSQL)**: Manages high-concurrency API requests, stores metadata, and maintains a persistent audit log of all scans.



---

## 🚀 Getting Started

### 📋 Prerequisites
* **Docker & Docker Compose** installed.
* **Git** installed and configured with SSH.

### ⚙️ Installation & Deployment
Run the following commands to pull the project and spin up the entire environment (API, DB, and Vector Store) automatically:

```bash
# 1. Clone the repository
git clone [https://github.com/Santhosh-p653/deepfake-agentic-ai](https://github.com/Santhosh-p653/deepfake-agentic-ai)
cd deepfake-agentic-ai

# 2. Start the orchestrated environment
docker compose up -d --build

#SYSTEM ARCHITECTURE
This system follows a modular ,agent based pipeline:

1.Media Insertion
2.Frame Extraction
3.Face Detection
4.Feauture Extraction
5.Temporal Modeling
6.Vector indexing &search
7.Decision Aggregation

Each stage can retry or fallback independently.

#UPDATED VERSION
This document describes the architecture of the application based on microservice setup.
The system is divided into three isolated sections to improve stability,maintainability
and fault isolation.
1.API Service
Handles client request,business logics,orchestration between services.
Dockerized details:
1. Containerized using a lightweight python base image.
2. Dependencies installed via requirements.txt
3. Runs independently of ML Workloads.
PORTS: 8000
2.ML Service
Performs Deepfake detection/Ml inference tasks.
Details:
1. Load trained models.
2. Accept inference requests from API service.
3. Returns prediction result using results only.
4. Seperate dokcerfile optimized for Ml Dependency.
5. Larger image due to ml libraries.
6. It don't bloat api container
7. Prevents memory contention.
3.DB Services
Persistent Storage and infrastructure support.
Components: Postgresql,Redis,Chroma-db.
ORM : sqlalchemy.
Details:
1. Uses official Postgresql image.
2. Data persisted via Docker volumes.
4.Agents Service
Acts as the central brain of the system.It receives client requests and orchestrates multiple agents to complete tasks.
Role: Orchestrator,Fallback Strategy,Execution Order.
Details:
1. Light weight Python image.
2. Minimal depenedency.
3. Communicates via agents via internal network.
4. Keeps orchestration logic clean.
5. Easy to scale request handling.
6. Faster iteration and debugging. 
#UPDATED VERSION v2:
This system follows a containerized agent based microservices architecture,with isolated API,Agents,ML and DB services,packaged as independent docker images
 and ready for deployment via GHCR.
#UPDATED VERSION v3:
```
Before: API -> docker run agents(job container)
After: API  -> HTTP request -> agents service
```

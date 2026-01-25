#Deepfake Agentic AI

An agent-based  deepfake detection system using computer vision,DL,and vector similarity search.

##Planned Architecture
-FFmpeg +opencv->frame&audio extraction
-RetineFace->Face Detection
-Xception->Feature Extraction
-Transformer->Temporal modeling
-Chroma-Vector search
-FastAPI-inference APIs
-PostgreSQL->Metadata Storage
-Docker->Containerized deployment

##Status
Most of configs were resolved.
The repo is stable with basic setup to build the system further.


##Setup

### Clone the repository
``` 
git clone https://github.com/Santhosh-p653/deepfake-agentic-ai
cd deepfake-agentic-ai
```

###Start the Project
```
docker compose up -d --build
```
Fastapi will run on http://localhost:8000/

###Stop the project
```
docker compose down
```
###Editing the Code

All code in the api/folder
Make changes locally and rebuild the container if needed

###Adding new Packages

Update requirements.txt with new packages
Rebuild docker image
```
docker compose build
docker compose up -d
```
###Pull latest Updates
```
git pull 
docker compose up -d --build
```

For detailed architecture see the `docs/architecture.md`.
For troubleshooting guide on configuration see `docs/troubleshooting.md` for common issues,including docker in wsl and postgres errors,DNS errors.

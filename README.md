#Deepfake Agentic AI

An agent-based  deepfake detectionsystem using computer vision,DL,and vector similarity search.

##Planned Architecture
-FFmpeg +opencv->frame&audio extraction
-RetineFace->Face Detection
-Xception->Feauture Extraction
-Transformer->Temporal modeling
-Chroma-Vector search
-FastAPI-inference APIs
PostgreSQL->Metadata Storage
-Docker->Containerized deployment

##Status
Initial Setup in progress.

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


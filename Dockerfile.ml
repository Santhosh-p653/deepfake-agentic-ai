FROM python:3.11-slim
RUN apt-get update && apt-get install -y \ffmpeg\libgl1\libgl2.0-0\ &&rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ml/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ml ./ml
CMD ["python","ml/inference.py"]


FROM python:3.11-slim

# Install runtime dependencies (ffmpeg and OpenGL libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ml/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml ./ml

CMD ["python", "ml/inference.py"]

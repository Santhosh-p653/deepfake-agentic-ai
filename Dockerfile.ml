FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by opencv + retinaface
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY ml/requirements.txt .

# CPU-only torch — pinned to 2.4.0 (numpy 2.x compatible, transformers compatible)
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 \
    torch==2.4.0+cpu torchvision==0.19.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Rest of deps
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 \
    -r requirements.txt

COPY ml ./ml
COPY shared/ ./shared/

CMD ["uvicorn", "ml.main:app", "--host", "0.0.0.0", "--port", "8001"]

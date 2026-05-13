FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by opencv + retina-face
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY ml/requirements.txt .

# CPU-only torch first (heaviest, benefits most from layer caching)
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 \
    torch==2.2.2+cpu torchvision==0.17.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Rest of deps
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 \
    -r requirements.txt

COPY ml ./ml
COPY shared/ ./shared/

CMD ["uvicorn", "ml.main:app", "--host", "0.0.0.0", "--port", "8001"]
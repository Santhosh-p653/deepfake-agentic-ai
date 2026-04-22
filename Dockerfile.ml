FROM python:3.11-slim

WORKDIR /app

COPY ml/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ml ./ml

CMD ["python", "ml/inference.py"]

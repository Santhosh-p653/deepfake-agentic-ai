from fastapi import FastAPI
from ml.preprocessing import preprocess
from ml.detection import detect

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "ml pong"}


@app.post("/process")
def process(payload: dict):
    file_path = payload.get("file_path")
    record_id = payload.get("record_id")

    preprocessing_signal = preprocess(file_path)
    detection_signal = detect(preprocessing_signal.metadata.get("frames", []))

    return {
        "record_id": record_id,
        "preprocessing": preprocessing_signal.model_dump(),
        "detection": detection_signal.model_dump(),
    }

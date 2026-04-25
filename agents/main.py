from fastapi import FastAPI
from log_analyser import analyse_logs

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "agents pong"}


@app.get("/analyse")
def analyse():
    signal = analyse_logs()
    return signal.model_dump()
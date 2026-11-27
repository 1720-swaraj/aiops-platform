from fastapi import FastAPI
import os

app = FastAPI(title="AIOps Platform API")

@app.get("/health")
def health():
    return {"status": "ok", "service": "api"}

@app.get("/")
def root():
    return {
        "message": "AIOps Microservices Platform API",
        "env": os.getenv("APP_ENV", "local")
    }

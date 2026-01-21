import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/config")
def config():
    # Never return secrets in real apps.
    return {"has_database_url": bool(os.getenv("DATABASE_URL"))}

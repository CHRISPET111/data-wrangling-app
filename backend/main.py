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

from sqlalchemy import text

@app.get("/levels")
def get_levels():
    """
    Returns all game levels with their badge names.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT level_number, name, description, badge_name
            FROM levels
            ORDER BY level_number
        """))

        return [dict(row) for row in result.mappings()]

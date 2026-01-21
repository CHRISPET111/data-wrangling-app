import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text

# ----------------------
# App setup
# ----------------------
app = FastAPI()

# ----------------------
# Database setup (FORCE psycopg v3)
# ----------------------
DATABASE_URL = os.getenv("DATABASE_URL")

engine = None
if DATABASE_URL:
    # Render sometimes provides "postgres://" or "postgresql://"
    # Force SQLAlchemy to use psycopg (v3) driver:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ----------------------
# Basic endpoints
# ----------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/config")
def config():
    # Never return secrets in real apps.
    return {"has_database_url": bool(os.getenv("DATABASE_URL"))}


@app.get("/db-check")
def db_check():
    """
    Quick sanity check to verify the database is reachable.
    """
    if engine is None:
        return {"db": "not configured"}

    with engine.connect() as conn:
        value = conn.execute(text("SELECT 1")).scalar()
        return {"db": "connected", "result": value}


# ----------------------
# Seed levels into the database (run once)
# ----------------------
@app.post("/seed")
def seed_levels():
    """
    Creates the levels table (if needed) and inserts the 7 fun levels.
    Safe to run multiple times.
    """
    if engine is None:
        raise HTTPException(
            status_code=500,
            detail="Database not configured. Set DATABASE_URL."
        )

    with engine.begin() as conn:
        # Create table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS levels (
                id SERIAL PRIMARY KEY,
                level_number INT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                badge_name TEXT NOT NULL
            )
        """))

        # Insert levels (idempotent)
        conn.execute(text("""
            INSERT INTO levels (level_number, name, description, badge_name)
            VALUES
            (1, 'The Data Detective', 'Inspect and understand messy data', 'Data Detective'),
            (2, 'The Janitor’s Revenge', 'Clean missing values and duplicates', 'Data Janitor'),
            (3, 'The Filter Wizard', 'Filter and index data safely', 'Filter Wizard'),
            (4, 'The String Surgeon', 'Fix strings and dates', 'String Surgeon'),
            (5, 'The Join Assassin', 'Join datasets without explosions', 'Join Assassin'),
            (6, 'The Shape Shifter', 'Reshape data correctly', 'Shape Shifter'),
            (7, 'The Data Alchemist', 'End-to-end wrangling challenge', 'Data Alchemist')
            ON CONFLICT (level_number) DO NOTHING
        """))

    return {"ok": True, "message": "Levels table created and seeded"}


# ----------------------
# Game content endpoint
# ----------------------
@app.get("/levels")
def get_levels():
    """
    Returns all game levels with their badge names.
    """
    if engine is None:
        raise HTTPException(
            status_code=500,
            detail="Database not configured. Set DATABASE_URL."
        )

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT level_number, name, description, badge_name
            FROM levels
            ORDER BY level_number
        """))
        return [dict(row) for row in result.mappings()]

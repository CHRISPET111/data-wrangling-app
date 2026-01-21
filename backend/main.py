import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, text

# ----------------------
# App setup
# ----------------------
app = FastAPI(title="Wrangling Game API", version="1.0.0")

# ----------------------
# CORS (needed if you later add a separate React UI)
# ----------------------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def require_db():
    if engine is None:
        raise HTTPException(
            status_code=500,
            detail="Database not configured. Set DATABASE_URL.",
        )
    return engine


# ----------------------
# Basic endpoints
# ----------------------
@app.get("/")
def root():
    # Render/browsers often hit GET /
    return {"status": "ok", "ui": "/app", "docs": "/docs", "health": "/health"}


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
# Minimal UI (fastest way to "open the app" in a browser)
# ----------------------
@app.get("/app", response_class=HTMLResponse)
def app_ui():
    return """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>Wrangling Game</title>
        <style>
          body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
          button { padding: 10px 14px; border-radius: 10px; border: 1px solid #ccc; cursor: pointer; margin-right: 8px; }
          .card { border: 1px solid #eee; border-radius: 14px; padding: 14px; margin-top: 12px; }
          .muted { color: #666; }
          pre { background:#f6f6f6; padding:12px; border-radius:12px; overflow:auto; }
        </style>
      </head>
      <body>
        <h1>Wrangling Game</h1>
        <p class="muted">Simple UI served by FastAPI</p>

        <div>
          <button onclick="seed()">Seed DB</button>
          <button onclick="loadLevels()">Load Levels</button>
        </div>

        <pre id="status"></pre>
        <div id="out"></div>

        <script>
          const statusEl = document.getElementById('status');
          const outEl = document.getElementById('out');

          function setStatus(msg) {
            statusEl.textContent = msg || '';
          }

          async function seed() {
            try {
              setStatus("Seeding...");
              const res = await fetch('/seed', { method: 'POST' });
              const data = await res.json();
              setStatus(JSON.stringify(data, null, 2));
            } catch (e) {
              setStatus("Seed failed: " + e);
            }
          }

          async function loadLevels() {
            try {
              setStatus("Loading levels...");
              const res = await fetch('/levels');
              const levels = await res.json();

              outEl.innerHTML = "";
              levels.forEach(l => {
                const div = document.createElement('div');
                div.className = 'card';
                div.innerHTML = `
                  <div><b>Level ${l.level_number}: ${l.name}</b></div>
                  <div class="muted">${l.description}</div>
                  <div style="margin-top:8px;">🏅 Badge: <b>${l.badge_name}</b></div>
                `;
                outEl.appendChild(div);
              });

              setStatus("");
            } catch (e) {
              setStatus("Load failed: " + e);
            }
          }
        </script>
      </body>
    </html>
    """


# ----------------------
# Seed levels into the database (run once)
# ----------------------
@app.post("/seed")
def seed_levels():
    """
    Creates the levels table (if needed) and inserts the 7 fun levels.
    Safe to run multiple times.
    """
    db = require_db()

    with db.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS levels (
                    id SERIAL PRIMARY KEY,
                    level_number INT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    badge_name TEXT NOT NULL
                )
                """
            )
        )

        conn.execute(
            text(
                """
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
                """
            )
        )

    return {"ok": True, "message": "Levels table created and seeded"}


# ----------------------
# Game content endpoint
# ----------------------
@app.get("/levels")
def get_levels():
    """
    Returns all game levels with their badge names.
    """
    db = require_db()

    with db.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT level_number, name, description, badge_name
                FROM levels
                ORDER BY level_number
                """
            )
        )
        return [dict(row) for row in result.mappings()]

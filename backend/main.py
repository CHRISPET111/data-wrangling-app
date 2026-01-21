import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
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
# Challenge content (MVP)
# ----------------------
CHALLENGES = {
    1: {
        "title": "The Data Detective",
        "goal": "Inspect and understand messy data.",
        "task": "List 3 things you would check first in a messy dataset.",
        "hint": "Missing values, duplicates, data types, ranges/outliers.",
        "must_have": ["missing", "duplicate", "type|dtype|datetype|range|outlier"],
    },
    2: {
        "title": "The Janitor’s Revenge",
        "goal": "Clean missing values and duplicates.",
        "task": "Identify issues in the data and describe how you would fix missing values and duplicates.",
        "hint": "Drop vs impute; define duplicate keys; keep latest record.",
        "must_have": ["missing|null|nan", "duplicate|dedup", "impute|fill|median|mean|drop"],
    },
    3: {
        "title": "The Filter Wizard",
        "goal": "Filter and index data safely.",
        "task": "Explain how you would filter rows in pandas and avoid SettingWithCopyWarning.",
        "hint": "Use .loc and consider .copy().",
        "must_have": ["loc", "copy|SettingWithCopy"],
    },
    4: {
        "title": "The String Surgeon",
        "goal": "Fix strings and dates.",
        "task": "How would you parse messy date strings into a datetime column in pandas?",
        "hint": "pd.to_datetime(..., errors='coerce')",
        "must_have": ["to_datetime", "errors|coerce"],
    },
    5: {
        "title": "The Join Assassin",
        "goal": "Join datasets without explosions.",
        "task": "Name 2 checks you do before joining tables to avoid row multiplication.",
        "hint": "Check key uniqueness, cardinality, duplicates.",
        "must_have": ["key", "unique|uniqueness", "cardinality|duplicate"],
    },
    6: {
        "title": "The Shape Shifter",
        "goal": "Reshape data correctly.",
        "task": "When would you use pivot vs melt? Give one example each.",
        "hint": "Wide vs long transformations.",
        "must_have": ["pivot", "melt|stack|unstack", "wide|long"],
    },
    7: {
        "title": "The Data Alchemist",
        "goal": "End-to-end wrangling challenge.",
        "task": "Outline an end-to-end data wrangling pipeline (steps + checks).",
        "hint": "Ingest → validate → clean → transform → QA → output.",
        "must_have": ["validate|schema", "clean", "transform", "qa|check|test"],
    },
}


def score_answer(level_number: int, answer: str) -> dict:
    """
    Very simple rubric-based scoring:
    - must contain enough concepts (regex patterns in must_have)
    - must be long enough (to avoid 1-liners)
    """
    challenge = CHALLENGES[level_number]
    patterns = challenge.get("must_have", [])

    hits = 0
    hit_patterns = []
    for p in patterns:
        if re.search(p, answer, flags=re.IGNORECASE):
            hits += 1
            hit_patterns.append(p)

    min_len = 40 if level_number in (2, 7) else 25
    long_enough = len(answer.strip()) >= min_len

    # Pass rule: enough hits + enough length
    required_hits = max(2, (len(patterns) + 1) // 2)
    passed = (hits >= required_hits) and long_enough

    feedback = []
    if not long_enough:
        feedback.append(f"Answer is a bit short. Aim for at least {min_len} characters.")
    if hits < required_hits:
        feedback.append("Mention a few more key concepts from the hint/goal.")

    if passed:
        feedback.append("Nice — you covered the key ideas for this level.")

    return {
        "passed": passed,
        "hits": hits,
        "required_hits": required_hits,
        "matched": hit_patterns,
        "feedback": feedback,
    }


# ----------------------
# Basic endpoints
# ----------------------
@app.get("/")
def root():
    return {"status": "ok", "ui": "/app", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/config")
def config():
    return {"has_database_url": bool(os.getenv("DATABASE_URL"))}


@app.get("/db-check")
def db_check():
    if engine is None:
        return {"db": "not configured"}

    with engine.connect() as conn:
        value = conn.execute(text("SELECT 1")).scalar()
        return {"db": "connected", "result": value}


# ----------------------
# Minimal UI (now clickable + playable)
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
          .row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom: 14px; }
          button { padding: 10px 14px; border-radius: 10px; border: 1px solid #ccc; cursor: pointer; background: white; }
          .card { border: 1px solid #eee; border-radius: 14px; padding: 14px; margin-top: 12px; cursor:pointer; }
          .card:hover { border-color:#ccc; }
          .muted { color: #666; }
          pre { background:#f6f6f6; padding:12px; border-radius:12px; overflow:auto; }
          .modalBack {
            position: fixed; inset:0; background: rgba(0,0,0,0.35);
            display:none; align-items:center; justify-content:center; padding: 18px;
          }
          .modal {
            width: min(820px, 100%); background: white; border-radius: 16px; padding: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
          }
          textarea { width: 100%; min-height: 120px; border-radius: 12px; border:1px solid #ddd; padding: 10px; }
          code, .box { background:#f6f6f6; padding: 10px; border-radius: 12px; display:block; }
        </style>
      </head>
      <body>
        <h1>Wrangling Game</h1>
        <p class="muted">Click a level to play. Submit an answer to get instant feedback.</p>

        <div class="row">
          <button onclick="seed()">Seed DB</button>
          <button onclick="loadLevels()">Reload Levels</button>
          <button onclick="location.href='/docs'">Open /docs</button>
        </div>

        <pre id="status"></pre>
        <div id="out"></div>

        <!-- Modal -->
        <div id="modalBack" class="modalBack" onclick="hideModal()">
          <div class="modal" onclick="event.stopPropagation()">
            <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
              <div>
                <h2 id="mTitle" style="margin:0;"></h2>
                <div id="mGoal" class="muted" style="margin-top:6px;"></div>
              </div>
              <button onclick="hideModal()">Close</button>
            </div>

            <div style="margin-top:12px;">
              <div><b>Task</b></div>
              <div id="mTask" style="margin-top:6px;"></div>
              <div id="mHint" class="muted" style="margin-top:8px;"></div>
            </div>

            <div style="margin-top:12px;">
              <div><b>Example messy data</b></div>
              <div class="box" id="mData" style="margin-top:6px; white-space:pre;"></div>
            </div>

            <div style="margin-top:12px;">
              <div><b>Your answer</b></div>
              <textarea id="answer" placeholder="Type your answer here..."></textarea>
            </div>

            <div class="row" style="margin-top:12px;">
              <button onclick="submitAnswer()">Submit</button>
            </div>

            <pre id="result"></pre>
          </div>
        </div>

        <script>
          const statusEl = document.getElementById('status');
          const outEl = document.getElementById('out');

          let currentLevel = null;

          const EXAMPLE_DATA = `user_id | age | country
-----------------------
1       | 29  | DE
2       |     | DE
2       |     | DE
3       | 41  |
4       | -5  | FR`;

          function setStatus(msg) { statusEl.textContent = msg || ''; }

          function showModal() {
            document.getElementById('modalBack').style.display = "flex";
          }
          function hideModal() {
            document.getElementById('modalBack').style.display = "none";
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
                div.onclick = () => openLevel(l.level_number);
                div.innerHTML = `
                  <div><b>Level ${l.level_number}: ${l.name}</b></div>
                  <div class="muted">${l.description}</div>
                  <div style="margin-top:8px;">🏅 Badge: <b>${l.badge_name}</b></div>
                  <div class="muted" style="margin-top:8px;">Click to play →</div>
                `;
                outEl.appendChild(div);
              });

              setStatus("");
            } catch (e) {
              setStatus("Load failed: " + e);
            }
          }

          async function openLevel(levelNumber) {
            try {
              setStatus("");
              const res = await fetch(`/levels/${levelNumber}`);
              const data = await res.json();

              currentLevel = data;
              document.getElementById('mTitle').textContent = `Level ${data.level_number}: ${data.title}`;
              document.getElementById('mGoal').textContent = data.goal || "";
              document.getElementById('mTask').textContent = data.task || "";
              document.getElementById('mHint').textContent = data.hint ? ("Hint: " + data.hint) : "";
              document.getElementById('mData').textContent = EXAMPLE_DATA;
              document.getElementById('answer').value = "";
              document.getElementById('result').textContent = "";

              showModal();
            } catch (e) {
              setStatus("Open level failed: " + e);
            }
          }

          async function submitAnswer() {
            const txt = document.getElementById('answer').value.trim();
            if (!currentLevel) return;
            if (!txt) {
              document.getElementById('result').textContent = "⚠️ Please type an answer first.";
              return;
            }

            const res = await fetch(`/levels/${currentLevel.level_number}/submit`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ answer: txt })
            });

            const data = await res.json();
            document.getElementById('result').textContent = JSON.stringify(data, null, 2);
          }

          loadLevels();
        </script>
      </body>
    </html>
    """


# ----------------------
# Seed levels into the database (run once)
# ----------------------
@app.post("/seed")
def seed_levels():
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
# List levels (from DB)
# ----------------------
@app.get("/levels")
def get_levels():
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


# ----------------------
# Get a single level (challenge content)
# ----------------------
@app.get("/levels/{level_number}")
def get_level(level_number: int):
    if level_number not in CHALLENGES:
        raise HTTPException(status_code=404, detail="Level not found")

    return {"level_number": level_number, **CHALLENGES[level_number]}


class SubmitAnswer(BaseModel):
    answer: str


# ----------------------
# Submit answer (basic rubric grading)
# ----------------------
@app.post("/levels/{level_number}/submit")
def submit_level(level_number: int, payload: SubmitAnswer):
    if level_number not in CHALLENGES:
        raise HTTPException(status_code=404, detail="Level not found")

    result = score_answer(level_number, payload.answer)
    return {
        "level_number": level_number,
        "passed": result["passed"],
        "hits": result["hits"],
        "required_hits": result["required_hits"],
        "feedback": result["feedback"],
    }


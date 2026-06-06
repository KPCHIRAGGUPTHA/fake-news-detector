from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import os
import sys

# Add parent directory so backend can import predict.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.predict import predict

app = FastAPI(title="Fake News Detector API")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database Setup ────────────────────────────────────────────────────────────
DB_PATH = "backend/history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            text       TEXT,
            label      TEXT,
            confidence REAL,
            reasons    TEXT,
            timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Request Model ─────────────────────────────────────────────────────────────
class NewsInput(BaseModel):
    text: str

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return FileResponse("frontend/index.html")

@app.post("/predict")
def predict_news(input: NewsInput):
    if not input.text.strip():
        return {"error": "Please enter some text."}

    result = predict(input.text)

    # Save to DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO history (text, label, confidence, reasons) VALUES (?, ?, ?, ?)",
        (input.text[:500], result["label"], result["confidence"], " | ".join(result["reasons"]))
    )
    conn.commit()
    conn.close()

    return result

@app.get("/history")
def get_history():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, text, label, confidence, reasons, timestamp FROM history ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()

    return [
        {
            "id":         r[0],
            "text":       r[1],
            "label":      r[2],
            "confidence": r[3],
            "reasons":    r[4],
            "timestamp":  r[5]
        }
        for r in rows
    ]

@app.delete("/history")
def clear_history():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    return {"message": "History cleared."}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.predict import predict
from backend.scraper import scrape_article

app = FastAPI(title="Fake News Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "backend/history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT DEFAULT 'text',
            url        TEXT DEFAULT '',
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

class NewsInput(BaseModel):
    text: str

class UrlInput(BaseModel):
    url: str

@app.get("/")
def root():
    return FileResponse("frontend/index.html")

@app.post("/predict")
def predict_news(input: NewsInput):
    if not input.text.strip():
        return {"error": "Please enter some text."}
    result = predict(input.text)
    _save_history("text", "", input.text, result)
    return result

@app.post("/predict-url")
def predict_url(input: UrlInput):
    if not input.url.strip():
        return {"error": "Please enter a URL."}
    scraped = scrape_article(input.url)
    if "error" in scraped:
        return {"error": scraped["error"]}
    result = predict(scraped["text"])
    result["scraped_title"]  = scraped.get("title", "")
    result["scraped_domain"] = scraped.get("domain", "")
    result["scraped_chars"]  = scraped.get("chars", 0)
    result["domain_trust"]   = scraped.get("trust", {})
    result["scraped_text"]   = scraped["text"]
    _save_history("url", input.url, scraped["text"], result)
    return result

@app.get("/history")
def get_history():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, source, url, text, label, confidence, reasons, timestamp FROM history ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "source": r[1], "url": r[2],
            "text": r[3], "label": r[4],
            "confidence": r[5], "reasons": r[6], "timestamp": r[7]
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

def _save_history(source, url, text, result):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO history (source, url, text, label, confidence, reasons) VALUES (?,?,?,?,?,?)",
        (source, url, text[:500], result["label"], result["confidence"], " | ".join(result["reasons"]))
    )
    conn.commit()
    conn.close()
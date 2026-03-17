"""
Memory System — LTM (Long-Term Memory) + STM (Short-Term Memory)
================================================================
LTM: SQLite database storing run history, errors, quality scores
STM: In-process dict passed through AgentState each run

Used by LangGraph nodes to:
  - Skip re-processing already-done work (STM cache)
  - Learn from past failures (LTM error log)
  - Track quality trends (LTM quality_log)
  - Report provider reliability (LTM provider_stats)
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = "data/memory/ltm.db"


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create LTM tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT NOT NULL,
            title       TEXT,
            timestamp   TEXT DEFAULT (datetime('now')),
            status      TEXT DEFAULT 'running',   -- running | success | failed
            quality_score REAL DEFAULT 0.0,
            video_path  TEXT,
            duration_min REAL DEFAULT 0.0,
            provider_llm  TEXT,
            provider_tts  TEXT
        );

        CREATE TABLE IF NOT EXISTS errors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER REFERENCES runs(id),
            node        TEXT,
            error_type  TEXT,
            message     TEXT,
            timestamp   TEXT DEFAULT (datetime('now')),
            resolved    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS quality_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER REFERENCES runs(id),
            chapter_id  INTEGER,
            chapter_name TEXT,
            has_audio   INTEGER,
            has_animation INTEGER,
            duration_sec  REAL,
            quality_score REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS provider_stats (
            provider      TEXT PRIMARY KEY,
            total_calls   INTEGER DEFAULT 0,
            success_calls INTEGER DEFAULT 0,
            fail_calls    INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0.0,
            last_used     TEXT
        );

        CREATE TABLE IF NOT EXISTS problem_index (
            slug        TEXT PRIMARY KEY,
            title       TEXT,
            difficulty  TEXT,
            tags        TEXT,
            last_run_id INTEGER REFERENCES runs(id),
            run_count   INTEGER DEFAULT 0,
            best_quality REAL DEFAULT 0.0
        );
    """)
    conn.commit()
    conn.close()


# ── Run Management ─────────────────────────────────────────────────────────────

def start_run(slug: str, title: str, provider_llm: str, provider_tts: str) -> int:
    """Start a new run record. Returns run_id."""
    init_db()
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO runs (slug, title, status, provider_llm, provider_tts) VALUES (?,?,?,?,?)",
        (slug, title, "running", provider_llm, provider_tts)
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def finish_run(run_id: int, status: str, quality_score: float,
               video_path: str, duration_min: float):
    """Update a run record on completion."""
    conn = _get_conn()
    conn.execute(
        "UPDATE runs SET status=?, quality_score=?, video_path=?, duration_min=? WHERE id=?",
        (status, quality_score, video_path, duration_min, run_id)
    )
    conn.commit()
    conn.close()


# ── Error Logging ──────────────────────────────────────────────────────────────

def log_error(run_id: int, node: str, error_type: str, message: str):
    """Log an error to LTM."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO errors (run_id, node, error_type, message) VALUES (?,?,?,?)",
        (run_id, node, error_type, str(message)[:1000])
    )
    conn.commit()
    conn.close()
    print(f"  [LTM] Logged error: {node} -> {error_type}")


def get_past_errors(slug: str, node: str) -> list:
    """Retrieve past errors for this slug/node to avoid repeating mistakes."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT e.error_type, e.message, COUNT(*) as freq
           FROM errors e JOIN runs r ON e.run_id = r.id
           WHERE r.slug=? AND e.node=? AND e.resolved=0
           GROUP BY e.error_type ORDER BY freq DESC LIMIT 5""",
        (slug, node)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Quality Logging ───────────────────────────────────────────────────────────

def log_chapter_quality(run_id: int, chapter: dict):
    conn = _get_conn()
    conn.execute(
        """INSERT INTO quality_log
           (run_id, chapter_id, chapter_name, has_audio, has_animation, duration_sec, quality_score)
           VALUES (?,?,?,?,?,?,?)""",
        (run_id,
         chapter.get("segment_id", 0),
         chapter.get("chapter", ""),
         1 if chapter.get("audio_path") else 0,
         1 if chapter.get("animation_path") else 0,
         chapter.get("duration_sec", 0),
         chapter.get("quality_score", 0.0))
    )
    conn.commit()
    conn.close()


# ── Provider Stats ────────────────────────────────────────────────────────────

def record_provider_call(provider: str, success: bool, latency_ms: float):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO provider_stats (provider, total_calls, success_calls, fail_calls, avg_latency_ms, last_used)
        VALUES (?, 1, ?, ?, ?, datetime('now'))
        ON CONFLICT(provider) DO UPDATE SET
            total_calls = total_calls + 1,
            success_calls = success_calls + ?,
            fail_calls = fail_calls + ?,
            avg_latency_ms = (avg_latency_ms * total_calls + ?) / (total_calls + 1),
            last_used = datetime('now')
    """, (provider, int(success), int(not success), int(success), int(not success), latency_ms))
    conn.commit()
    conn.close()


def get_best_provider(provider_type: str) -> Optional[str]:
    """Return the provider with highest success rate for the given type."""
    conn = _get_conn()
    providers = {
        "llm": ["huggingface", "openai", "anthropic", "gemini"],
        "tts": ["edge_tts", "elevenlabs", "openai_tts", "gtts"],
    }
    candidates = providers.get(provider_type, [])
    if not candidates:
        return None
    placeholders = ",".join("?" * len(candidates))
    rows = conn.execute(
        f"""SELECT provider, CAST(success_calls AS REAL)/MAX(total_calls,1) as rate
            FROM provider_stats WHERE provider IN ({placeholders})
            ORDER BY rate DESC LIMIT 1""",
        candidates
    ).fetchall()
    conn.close()
    return rows[0]["provider"] if rows else None


# ── STM Helpers ───────────────────────────────────────────────────────────────

def make_stm() -> dict:
    """Initialize a fresh Short-Term Memory for a run."""
    return {
        "run_id": None,
        "chapters_audio_done": [],
        "chapters_video_done": [],
        "retry_counts": {},
        "provider_fallbacks": {},
        "quality_scores": {},
    }

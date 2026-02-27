"""ZeroTax AI — SQLite persistence layer.

Schema:
  users      — accounts (email + hashed password)
  api_keys   — per-user encrypted API keys
  tax_plans  — full JSON plan blobs
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional


DB_PATH = os.environ.get("ZEROTAX_DB", "zerotax.db")

_conn: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            email        TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name    TEXT DEFAULT '',
            created_at   TEXT NOT NULL,
            last_login   TEXT
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            user_id      TEXT PRIMARY KEY,
            anthropic_key TEXT DEFAULT '',
            openai_key   TEXT DEFAULT '',
            updated_at   TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tax_plans (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            plan_name    TEXT NOT NULL,
            status       TEXT DEFAULT 'pending',
            wizard_data  TEXT DEFAULT '{}',
            ai_result    TEXT DEFAULT '{}',
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS knowledge_meta (
            key          TEXT PRIMARY KEY,
            value        TEXT NOT NULL
        );

        INSERT OR IGNORE INTO knowledge_meta (key, value)
        VALUES ('last_updated', 'Never'), ('chunk_count', '0');
    """)
    conn.commit()


# ─── API Keys ─────────────────────────────────────────────────────────────────

def get_api_keys(user_id: str) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM api_keys WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {"anthropic_key": "", "openai_key": ""}
    return {"anthropic_key": row["anthropic_key"] or "", "openai_key": row["openai_key"] or ""}


def save_api_keys(user_id: str, anthropic_key: str = "", openai_key: str = "") -> None:
    db = get_db()
    db.execute("""
        INSERT INTO api_keys (user_id, anthropic_key, openai_key, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            anthropic_key = excluded.anthropic_key,
            openai_key    = excluded.openai_key,
            updated_at    = excluded.updated_at
    """, (user_id, anthropic_key, openai_key, datetime.utcnow().isoformat()))
    db.commit()


# ─── Tax Plans ────────────────────────────────────────────────────────────────

def create_plan(user_id: str, plan_name: str, wizard_data: dict) -> str:
    import uuid
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db = get_db()
    db.execute(
        "INSERT INTO tax_plans (id, user_id, plan_name, status, wizard_data, ai_result, created_at, updated_at) "
        "VALUES (?, ?, ?, 'pending', ?, '{}', ?, ?)",
        (plan_id, user_id, plan_name, json.dumps(wizard_data), now, now),
    )
    db.commit()
    return plan_id


def update_plan_result(plan_id: str, result: dict, status: str = "complete") -> None:
    db = get_db()
    db.execute(
        "UPDATE tax_plans SET ai_result = ?, status = ?, updated_at = ? WHERE id = ?",
        (json.dumps(result), status, datetime.utcnow().isoformat(), plan_id),
    )
    db.commit()


def get_plan(plan_id: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM tax_plans WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "plan_name": row["plan_name"],
        "status": row["status"],
        "wizard_data": json.loads(row["wizard_data"] or "{}"),
        "ai_result": json.loads(row["ai_result"] or "{}"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_user_plans(user_id: str) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM tax_plans WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    plans = []
    for row in rows:
        ai = json.loads(row["ai_result"] or "{}")
        plans.append({
            "id": row["id"],
            "plan_name": row["plan_name"],
            "status": row["status"],
            "created_at": row["created_at"],
            "projected_annual_savings": ai.get("projected_annual_savings", 0),
            "strategies_count": len(ai.get("strategies", [])),
        })
    return plans


def delete_plan(plan_id: str, user_id: str) -> None:
    db = get_db()
    db.execute("DELETE FROM tax_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
    db.commit()


# ─── Knowledge Meta ───────────────────────────────────────────────────────────

def get_knowledge_meta() -> dict:
    db = get_db()
    rows = db.execute("SELECT key, value FROM knowledge_meta").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_knowledge_meta(key: str, value: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO knowledge_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    db.commit()

"""
SQLite3 helpers for logging and retrieving analysis run history.
Database is auto-created at ./data/runs.db on first call to init_db().
"""

import os
import sqlite3
from datetime import datetime


DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "runs.db")


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the runs table if it does not exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                query       TEXT,
                filename    TEXT,
                status      TEXT,
                retry_count INTEGER,
                final_answer TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def insert_run(
    query: str,
    filename: str,
    status: str,
    retry_count: int,
    final_answer: str,
) -> None:
    """Insert a completed run into the database."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO runs (timestamp, query, filename, status, retry_count, final_answer)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                query,
                filename,
                status,
                retry_count,
                final_answer,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_history(limit: int = 20) -> list[dict]:
    """Return the last `limit` runs as a list of dicts, newest first."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

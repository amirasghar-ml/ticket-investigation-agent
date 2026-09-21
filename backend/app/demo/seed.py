from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import DATA_DIR, ROOT_DIR, settings
from app.demo import APPLICATION_LOGS, USERS


def _db_path() -> Path:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        raw = url.replace("sqlite:///", "", 1)
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path
    return DATA_DIR / "support_agent.db"


def connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def seed() -> None:
    from app.demo import refresh_clock

    refresh_clock()
    conn = connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                last_login_at TEXT,
                session_type TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS application_logs (
                id INTEGER PRIMARY KEY,
                ts TEXT NOT NULL,
                level TEXT NOT NULL,
                service TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                user_email TEXT,
                message TEXT NOT NULL,
                error_signature TEXT,
                stack_trace TEXT,
                request_id TEXT
            );
            """
        )
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM application_logs")
        conn.executemany(
            """
            INSERT INTO users (id, email, name, status, last_login_at, session_type, created_at)
            VALUES (:id, :email, :name, :status, :last_login_at, :session_type, :created_at)
            """,
            USERS,
        )
        conn.executemany(
            """
            INSERT INTO application_logs (
                id, ts, level, service, path, status_code, user_email,
                message, error_signature, stack_trace, request_id
            ) VALUES (
                :id, :ts, :level, :service, :path, :status_code, :user_email,
                :message, :error_signature, :stack_trace, :request_id
            )
            """,
            APPLICATION_LOGS,
        )
        conn.commit()
    finally:
        conn.close()

"""
File: db.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Database connection, path resolution, and business constants.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date


def _load_dotenv() -> None:
    """Load .env from the project root (if it exists)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    dotenv_path = os.path.join(project_dir, ".env")
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# PM_DATA_DIR env var allows separating code from data.
# If set, pm.db / html / thumbnails / backup.sql live under that path.
# If not set, falls back to demo/ inside the project (for OSS contributors).
DATA_DIR = os.environ.get("PM_DATA_DIR", os.path.join(PROJECT_DIR, "demo"))
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "pm.db")
DEFAULT_HTML_DIR = os.path.join(DATA_DIR, "html")
DEFAULT_BACKUP_PATH = os.path.join(DATA_DIR, "backup.sql")

# Business constants
COVER_VALUE_MULTIPLIER = 20          # 封面图单价
FY_START_MONTH = 4                   # 财年起始月 (4月)
FY_END_MONTH = 3                     # 财年结束月 (3月)


def connect(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        backup_path = _resolve_backup_path(db_path)
        if not os.path.exists(backup_path):
            raise FileNotFoundError(
                f"Database '{db_path}' not found and no backup available at '{backup_path}'"
            )
        print(f"Restoring database from backup: {backup_path}")
        conn = sqlite3.connect(db_path)
        with open(backup_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _resolve_backup_path(db_path: str) -> str:
    """Resolve backup.sql path to the same directory as the db file."""
    data_dir = os.path.dirname(os.path.abspath(db_path))
    return os.path.join(data_dir, "backup.sql")


def dump_db(db_path: str, dump_path: str) -> None:
    conn = sqlite3.connect(db_path)
    os.makedirs(os.path.dirname(dump_path), exist_ok=True)
    with open(dump_path, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(line + "\n")
    conn.close()


def scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    return conn.execute(sql, params).fetchone()[0]


def date_expr(prefix: str) -> str:
    return (
        f"date({prefix}_y || '-' || "
        f"printf('%02d', {prefix}_m) || '-' || "
        f"printf('%02d', {prefix}_d))"
    )


def format_date(y: int | None, m: int | None, d: int | None) -> str:
    if y is None or m is None or d is None:
        return ""
    return f"{y:04d}-{m:02d}-{d:02d}"


def row_date(row: sqlite3.Row, prefix: str) -> date:
    return date(row[f"{prefix}_y"], row[f"{prefix}_m"], row[f"{prefix}_d"])

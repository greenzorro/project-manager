"""
File: db.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Database connection, backup, and common database helpers.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date

from config import (
    COVER_VALUE_MULTIPLIER,
    DATA_DIR,
    DEFAULT_BACKUP_PATH,
    DEFAULT_DB_PATH,
    DEFAULT_HTML_DIR,
    DEFAULT_OWNER,
    DEFAULT_PROJECT_NAME,
    FY_END_MONTH,
    FY_START_MONTH,
    PROJECT_DIR,
    SCRIPT_DIR,
)


def connect(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        backup_path = resolve_backup_path(db_path)
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


def resolve_backup_path(db_path: str) -> str:
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


def resolve_project_id(conn: sqlite3.Connection, name: str) -> str | None:
    row = conn.execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()
    return row[0] if row else None


def format_date(y: int | None, m: int | None, d: int | None) -> str:
    if y is None or m is None or d is None:
        return ""
    return f"{y:04d}-{m:02d}-{d:02d}"


def row_date(row: sqlite3.Row, prefix: str) -> date:
    return date(row[f"{prefix}_y"], row[f"{prefix}_m"], row[f"{prefix}_d"])

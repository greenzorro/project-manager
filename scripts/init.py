"""
File: init.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Initialize the project-manager SQLite database.
"""

import argparse
import os
import sqlite3
import sys
import uuid
from datetime import date

from db import DEFAULT_DB_PATH, FY_START_MONTH, PROJECT_DIR

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(PROJECT_DIR, "sql", "schema.sql")


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    _seed_req_types(conn)
    _seed_stat_periods(conn)

    conn.commit()
    conn.close()
    print(f"Database initialized: {db_path}")


def _current_fiscal_year(today: date) -> int:
    """Fiscal year starting month is {FY_START_MONTH}. Named by ending year."""
    return today.year + 1 if today.month >= FY_START_MONTH else today.year


def _seed_req_types(conn: sqlite3.Connection) -> None:
    seed_types = [
        ("__sys__", "__sys__"),
    ]
    for type_id, name in seed_types:
        conn.execute(
            "INSERT OR IGNORE INTO req_types (id, name) VALUES (?, ?)",
            (type_id, name),
        )


def _seed_stat_periods(conn: sqlite3.Connection) -> None:
    month_names = {
        1: "4月", 2: "5月", 3: "6月", 4: "7月",
        5: "8月", 6: "9月", 7: "10月", 8: "11月",
        9: "12月", 10: "1月", 11: "2月", 12: "3月",
    }
    periods = []

    for i in range(1, 13):
        periods.append((f"M{i:02d}-{month_names[i]}", "月"))

    periods.append(("S1", "S"))
    periods.append(("S2", "S"))

    current_fy = _current_fiscal_year(date.today())
    for n in range(current_fy - 2, current_fy + 1):
        periods.append((f"FY-{n % 100}", "财年"))

    existing = {r[0] for r in conn.execute("SELECT name FROM stat_periods")}
    for name, ptype in periods:
        if name not in existing:
            conn.execute(
                "INSERT INTO stat_periods (id, name, type) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), name, ptype),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize project-manager database")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite database path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)
    init_db(args.db_path)

    sys.path.insert(0, SCRIPT_DIR)
    from compute_periods import compute_periods
    compute_periods(args.db_path)
    print("Stat periods dates computed.")


if __name__ == "__main__":
    main()

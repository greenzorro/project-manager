"""
File: doctor.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Database consistency checks.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from db import connect, date_expr, scalar


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def run_doctor(db_path: str) -> list[Check]:
    conn = connect(db_path)
    checks: list[Check] = []

    integrity = scalar(conn, "PRAGMA integrity_check")
    checks.append(Check("sqlite_integrity", integrity == "ok", str(integrity)))

    fk_errors = [tuple(row) for row in conn.execute("PRAGMA foreign_key_check")]
    checks.append(Check("foreign_keys", not fk_errors, str(fk_errors)))

    count_checks = [
        (
            "requirements_have_requesters",
            "SELECT COUNT(*) FROM requirements WHERE requesters IS NULL OR requesters=''",
        ),
        (
            "requirements_have_received_dates",
            "SELECT COUNT(*) FROM requirements "
            "WHERE received_y IS NULL OR received_m IS NULL OR received_d IS NULL",
        ),
        (
            "requirements_have_projects",
            "SELECT COUNT(*) FROM requirements WHERE project_id IS NULL OR project_id=''",
        ),
        (
            "requirements_have_types",
            "SELECT COUNT(*) FROM requirements WHERE type_id IS NULL OR type_id=''",
        ),
        (
            "requirements_project_refs_exist",
            "SELECT COUNT(*) FROM requirements r "
            "LEFT JOIN projects p ON r.project_id=p.id WHERE p.id IS NULL",
        ),
        (
            "requirements_type_refs_exist",
            "SELECT COUNT(*) FROM requirements r "
            "LEFT JOIN req_types t ON r.type_id=t.id WHERE t.id IS NULL",
        ),
        (
            "schedules_requirement_refs_exist",
            "SELECT COUNT(*) FROM schedules s "
            "LEFT JOIN requirements r ON s.requirement_id=r.id WHERE r.id IS NULL",
        ),
        (
            "schedules_have_owner",
            "SELECT COUNT(*) FROM schedules WHERE owner IS NULL OR owner=''",
        ),
        (
            "stat_periods_have_dates",
            "SELECT COUNT(*) FROM stat_periods "
            "WHERE start_y IS NULL OR end_y IS NULL "
            "OR start_before_y IS NULL OR end_after_y IS NULL",
        ),
        (
            "schedules_start_before_end",
            "SELECT COUNT(*) FROM schedules "
            f"WHERE {date_expr('start')} > {date_expr('end')}",
        ),
    ]
    for name, sql in count_checks:
        bad = scalar(conn, sql)
        checks.append(Check(name, bad == 0, f"{bad} bad rows"))

    checks.extend(check_dates(conn))

    for view in ["v_requirements", "v_schedules", "v_stats_by_period"]:
        try:
            count = scalar(conn, f"SELECT COUNT(*) FROM {view}")
            checks.append(Check(f"{view}_queryable", True, f"{count} rows"))
        except sqlite3.Error as exc:
            checks.append(Check(f"{view}_queryable", False, str(exc)))

    schema_sql = scalar(
        conn,
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='requirements'",
    )
    required_fragments = [
        "project_id TEXT NOT NULL",
        "type_id TEXT NOT NULL",
        "requesters TEXT NOT NULL CHECK(requesters != '')",
        "received_y INTEGER NOT NULL",
        "received_m INTEGER NOT NULL",
        "received_d INTEGER NOT NULL",
    ]
    for fragment in required_fragments:
        checks.append(Check(f"schema_has_{fragment.split()[0]}", fragment in schema_sql, fragment))

    conn.close()
    return checks


def print_doctor(checks: list[Check]) -> int:
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "OK" if check.ok else "FAIL"
        print(f"{status:4} {check.name}: {check.detail}")
    print(f"\n{len(checks) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


def check_dates(conn: sqlite3.Connection) -> list[Check]:
    checks: list[Check] = []
    date_targets = [
        ("requirements", "received"),
        ("requirements", "expected"),
        ("requirements", "actual"),
        ("schedules", "start"),
        ("schedules", "end"),
        ("cover_outputs", "date"),
        ("stat_periods", "start"),
        ("stat_periods", "end"),
        ("stat_periods", "start_before"),
        ("stat_periods", "end_after"),
    ]
    for table, prefix in date_targets:
        rows = conn.execute(
            f"SELECT id, {prefix}_y AS y, {prefix}_m AS m, {prefix}_d AS d "
            f"FROM {table} "
            f"WHERE {prefix}_y IS NOT NULL "
            f"OR {prefix}_m IS NOT NULL "
            f"OR {prefix}_d IS NOT NULL"
        ).fetchall()
        bad = []
        for row in rows:
            try:
                if row["y"] is None or row["m"] is None or row["d"] is None:
                    raise ValueError("partial date")
                date(int(row["y"]), int(row["m"]), int(row["d"]))
            except (TypeError, ValueError) as exc:
                bad.append((row["id"], row["y"], row["m"], row["d"], str(exc)))
        checks.append(
            Check(
                f"{table}_{prefix}_dates_valid",
                not bad,
                "0 bad dates" if not bad else str(bad[:5]),
            )
        )
    return checks

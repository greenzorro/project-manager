"""
File: render_queries.py
Project: project-manager
Description: Query and aggregation helpers for static HTML rendering.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from db import COVER_VALUE_MULTIPLIER, FY_START_MONTH, format_date


def query_dashboard_data(conn: sqlite3.Connection) -> dict:
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT period_name, period_type, req_count, ui_pages, reports, courses, cover_count, efficiency
            FROM v_stats_by_period
            ORDER BY
              CASE period_type WHEN '月' THEN 1 WHEN 'S' THEN 2 ELSE 3 END,
              period_name
            """
        )
    ]
    for row in rows:
        row["cover_value"] = (row["cover_count"] or 0) * COVER_VALUE_MULTIPLIER
    months = [row for row in rows if row["period_type"] == "月"]
    fiscal_years = [row for row in rows if row["period_type"] == "财年"]
    current_fy = max(fiscal_years, key=lambda r: r["period_name"])
    fy_stacks = compute_fy_stacks(conn, fiscal_years)
    today = date.today()
    fy_start_year = today.year if today.month >= FY_START_MONTH else today.year - 1
    fy_start = f"{fy_start_year}-04-01"
    fy_end = f"{fy_start_year + 1}-03-31"

    requester_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT requesters AS requester, COUNT(*) AS req_count,
                   SUM(CASE WHEN actual_y IS NOT NULL THEN 1 ELSE 0 END) AS delivered_count,
                   SUM(CASE WHEN actual_y IS NULL THEN 1 ELSE 0 END) AS open_count
            FROM requirements
            WHERE type_id != '__sys__'
              AND date(received_y || '-' || printf('%02d', received_m) || '-' || printf('%02d', received_d)) >= date(?)
              AND date(received_y || '-' || printf('%02d', received_m) || '-' || printf('%02d', received_d)) <= date(?)
            GROUP BY requesters
            ORDER BY req_count DESC, requester
            LIMIT 10
            """,
            (fy_start, fy_end),
        )
    ]
    type_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT rt.name AS type_name, COUNT(*) AS req_count
            FROM requirements r
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.type_id != '__sys__'
              AND date(r.received_y || '-' || printf('%02d', r.received_m) || '-' || printf('%02d', r.received_d)) >= date(?)
              AND date(r.received_y || '-' || printf('%02d', r.received_m) || '-' || printf('%02d', r.received_d)) <= date(?)
            GROUP BY rt.name
            ORDER BY req_count DESC, rt.name
            """,
            (fy_start, fy_end),
        )
    ]
    return {
        "months": months,
        "fiscal_years": fiscal_years,
        "current_fy": current_fy,
        "fy_stacks": fy_stacks,
        "requester_rows": requester_rows,
        "type_rows": type_rows,
    }


def query_calendar_data(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    window_start = add_months_to_month_start(date(today.year, today.month, 1), -3)
    window_end = add_months_to_month_start(date(today.year, today.month, 1), 4) - timedelta(days=1)
    months = [add_months_to_month_start(window_start, index) for index in range(7)]
    schedules = [
        normalize_schedule(row)
        for row in conn.execute(
            """
            SELECT s.id, s.start_y, s.start_m, s.start_d, s.end_y, s.end_m, s.end_d,
                   s.owner, r.name AS requirement_name, p.name AS project_name
            FROM schedules s
            JOIN requirements r ON s.requirement_id = r.id
            LEFT JOIN projects p ON r.project_id = p.id
            WHERE date(s.end_y || '-' || printf('%02d', s.end_m) || '-' || printf('%02d', s.end_d)) >= date(?)
              AND date(s.start_y || '-' || printf('%02d', s.start_m) || '-' || printf('%02d', s.start_d)) <= date(?)
            ORDER BY s.start_y, s.start_m, s.start_d, s.owner, r.name
            """,
            (window_start.isoformat(), window_end.isoformat()),
        )
    ]
    owners = sorted({schedule["owner"] for schedule in schedules})
    return {
        "window_start": window_start,
        "window_end": window_end,
        "months": months,
        "schedules": schedules,
        "owners": owners,
    }


def query_recent_rows(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    recent_start = today - timedelta(days=7)
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT r.id, r.name, p.name AS project_name, rt.name AS type_name, r.requesters,
                   r.received_y, r.received_m, r.received_d,
                   r.expected_y, r.expected_m, r.expected_d,
                   r.actual_y, r.actual_m, r.actual_d,
                   r.ui_pages, r.delivery_url, r.delivery_thumbnail, r.notes
            FROM requirements r
            JOIN projects p ON r.project_id = p.id
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.type_id != '__sys__'
              AND (
                r.actual_y IS NULL
                OR date(r.actual_y || '-' || printf('%02d', r.actual_m) || '-' || printf('%02d', r.actual_d)) >= date(?)
              )
            ORDER BY
              r.actual_y IS NOT NULL,
              r.expected_y IS NULL,
              r.expected_y, r.expected_m, r.expected_d,
              r.actual_y DESC, r.actual_m DESC, r.actual_d DESC,
              r.name
            """,
            (recent_start.isoformat(),),
        )
    ]
    return {
        "today": today,
        "recent_start": recent_start,
        "open_rows": [row for row in rows if row["actual_y"] is None],
        "done_rows": [row for row in rows if row["actual_y"] is not None],
    }


def query_history_rows(conn: sqlite3.Connection) -> list[dict]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT r.id, r.name, p.name AS project_name, rt.name AS type_name, r.requesters,
                   r.received_y, r.received_m, r.received_d,
                   r.actual_y, r.actual_m, r.actual_d,
                   r.ui_pages, r.delivery_url, r.delivery_thumbnail
            FROM requirements r
            JOIN projects p ON r.project_id = p.id
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.type_id != '__sys__'
              AND r.actual_y IS NOT NULL
            ORDER BY r.actual_y DESC, r.actual_m DESC, r.actual_d DESC, r.name
            """
        )
    ]


def normalize_schedule(row: sqlite3.Row) -> dict:
    start = date(row["start_y"], row["start_m"], row["start_d"])
    end = date(row["end_y"], row["end_m"], row["end_d"])
    return {
        "id": row["id"],
        "start": start,
        "end": end,
        "owner": row["owner"],
        "requirement_name": row["requirement_name"],
        "project_name": row["project_name"] or "",
    }


def add_months_to_month_start(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def compute_fy_stacks(conn: sqlite3.Connection, fiscal_years: list[dict]) -> dict:
    req_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT r.actual_y, r.actual_m, r.actual_d, r.ui_pages, rt.name AS type_name
            FROM requirements r
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.actual_y IS NOT NULL AND r.type_id != '__sys__'
            """
        )
    ]
    co_rows = [
        dict(row)
        for row in conn.execute("SELECT date_y, date_m, date_d, count FROM cover_outputs")
    ]
    ranges = fy_semester_ranges(fiscal_years)
    labels = [row[0] for row in ranges]
    metrics = {
        "req_count": _count,
        "ui_pages": _ui_pages,
        "efficiency": _efficiency,
        "cover_value": _cover,
        "reports": _reports,
        "courses": _courses,
    }
    stacks = {}
    for key, func in metrics.items():
        s1 = []
        s2 = []
        for _, s1_start, s1_end, s2_start, s2_end in ranges:
            s1.append(func(req_rows, co_rows, s1_start, s1_end))
            s2.append(func(req_rows, co_rows, s2_start, s2_end))
        stacks[key] = (labels, s1, s2)
    return stacks


def fy_semester_ranges(fiscal_years: list[dict]) -> list[tuple]:
    ranges = []
    for row in fiscal_years:
        fy_suffix = int(row["period_name"].split("-")[1])
        end_year = 2000 + fy_suffix
        start_year = end_year - 1
        s1_start = date(start_year, 4, 1)
        s1_end = date(start_year, 9, 30)
        s2_start = date(start_year, 10, 1)
        s2_end = date(end_year, 3, 31)
        ranges.append((row["period_name"], s1_start, s1_end, s2_start, s2_end))
    return ranges


def _count(req_rows, _co, start, end):
    return sum(1 for row in req_rows if _in_range(row, start, end))


def _ui_pages(req_rows, _co, start, end):
    return sum((row["ui_pages"] or 0) for row in req_rows if row["type_name"] == "UI设计" and _in_range(row, start, end))


def _efficiency(req_rows, _co, start, end):
    return sum(1 for row in req_rows if row["type_name"] == "内部提效" and _in_range(row, start, end))


def _cover(_req_rows, co_rows, start, end):
    total = 0
    for row in co_rows:
        d = date(row["date_y"], row["date_m"], row["date_d"])
        if start <= d <= end:
            total += (row["count"] or 0) * COVER_VALUE_MULTIPLIER
    return total


def _reports(req_rows, _co, start, end):
    return sum(1 for row in req_rows if row["type_name"] == "数据分析" and _in_range(row, start, end))


def _courses(req_rows, _co, start, end):
    return sum(1 for row in req_rows if row["type_name"] == "课程制作" and _in_range(row, start, end))


def _in_range(row, start: date, end: date) -> bool:
    actual = format_date(row["actual_y"], row["actual_m"], row["actual_d"])
    if not actual:
        return False
    return start <= date.fromisoformat(actual) <= end

"""
File: holiday_ops.py
Project: project-manager
Description: Holiday and personal leave write operations.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from db import DEFAULT_OWNER, connect
from schedule_ops import ScheduleMovePlan, apply_schedule_move_on_connection
from schedule_utils import load_non_business_days, move_schedule, split_at_non_business


def add_holiday_and_push(
    db_path: str,
    start: date,
    end: date,
    *,
    holiday: bool = True,
    owner: str = "",
) -> None:
    """Add a public holiday or personal leave, then push all affected schedules.

    Args:
        holiday: True for public holiday (owner='-'), False for personal leave
        owner: required for leave, ignored for holiday
    """
    if end < start:
        raise ValueError("end date must be >= start date")

    if holiday:
        req_name = "__公共假期__"
        sched_owner = "-"
    else:
        req_name = "__请假__"
        if not owner:
            owner = DEFAULT_OWNER
        sched_owner = owner

    conn = connect(db_path)

    owner_clause = ""
    params: list[str] = [start.isoformat()]
    if not holiday:
        owner_clause = "AND s.owner = ?"
        params.append(sched_owner)

    rows = conn.execute(
        f"""
        SELECT s.id, s.requirement_id, s.start_y, s.start_m, s.start_d,
               s.end_y, s.end_m, s.end_d, s.owner, r.name AS requirement_name
        FROM schedules s
        JOIN requirements r ON s.requirement_id = r.id
        WHERE s.owner != '-'
          AND r.name NOT GLOB '__*'
          AND date(s.end_y || '-' || printf('%02d', s.end_m) || '-' || printf('%02d', s.end_d)) >= date(?)
          {owner_clause}
        ORDER BY s.start_y, s.start_m, s.start_d
        """,
        tuple(params),
    ).fetchall()
    owners = sorted({row["owner"] for row in rows})
    old_non_bd_by_owner = {
        row_owner: load_non_business_days(db_path, owner=row_owner)
        for row_owner in owners
    }

    req_id = conn.execute(
        "SELECT id FROM requirements WHERE name=?", (req_name,)
    ).fetchone()
    if req_id is None:
        conn.close()
        raise ValueError(f"System requirement '{req_name}' not found in database")
    req_id = req_id[0]

    plans = []
    holiday_dates = {
        start + timedelta(days=i) for i in range((end - start).days + 1)
    }
    for row in rows:
        row_owner = row["owner"]
        old_non_bd = old_non_bd_by_owner[row_owner]
        new_non_bd = old_non_bd | holiday_dates
        blocked = sum(
            1
            for d in holiday_dates
            if d.weekday() < 5 and d not in old_non_bd
        )
        if blocked == 0:
            continue

        old_start = date(row["start_y"], row["start_m"], row["start_d"])
        old_end = date(row["end_y"], row["end_m"], row["end_d"])
        if old_end < start:
            continue
        new_start, new_end = move_schedule(old_start, old_end, blocked, new_non_bd)
        segments = split_at_non_business(new_start, new_end, new_non_bd)
        plans.append(ScheduleMovePlan(row, old_start, old_end, segments))

    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            INSERT INTO schedules (id, requirement_id,
                start_y, start_m, start_d, end_y, end_m, end_d, owner)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                str(uuid.uuid4()), req_id,
                start.year, start.month, start.day,
                end.year, end.month, end.day,
                sched_owner,
            ),
        )
        apply_schedule_move_on_connection(conn, plans)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

"""
File: schedule_ops.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Database-backed schedule write operations.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date

from db import connect
from schedule_utils import move_schedule, split_cross_weekend


@dataclass
class ScheduleMovePlan:
    row: sqlite3.Row
    old_start: date
    old_end: date
    segments: list[tuple[date, date]]


def plan_schedule_move(db_path: str, owner: str, from_date: date, days: int) -> list[ScheduleMovePlan]:
    conn = connect(db_path)
    rows = conn.execute(
        """
        SELECT s.id, s.requirement_id, s.start_y, s.start_m, s.start_d,
               s.end_y, s.end_m, s.end_d, s.owner,
               r.name AS requirement_name
        FROM schedules s
        JOIN requirements r ON s.requirement_id = r.id
        WHERE s.owner = ?
          AND date(s.start_y || '-' || printf('%02d', s.start_m) || '-' || printf('%02d', s.start_d)) >= date(?)
        ORDER BY s.start_y, s.start_m, s.start_d, r.name
        """,
        (owner, from_date.isoformat()),
    ).fetchall()
    conn.close()

    plans = []
    for row in rows:
        old_start = date(row["start_y"], row["start_m"], row["start_d"])
        old_end = date(row["end_y"], row["end_m"], row["end_d"])
        new_start, new_end = move_schedule(old_start, old_end, days)
        segments = split_cross_weekend(new_start, new_end)
        plans.append(ScheduleMovePlan(row, old_start, old_end, segments))
    return plans


def apply_schedule_move(db_path: str, plans: list[ScheduleMovePlan]) -> None:
    conn = connect(db_path)
    conn.execute("BEGIN")
    try:
        for plan in plans:
            first_start, first_end = plan.segments[0]
            conn.execute(
                """
                UPDATE schedules
                SET start_y=?, start_m=?, start_d=?,
                    end_y=?, end_m=?, end_d=?
                WHERE id=?
                """,
                (
                    first_start.year,
                    first_start.month,
                    first_start.day,
                    first_end.year,
                    first_end.month,
                    first_end.day,
                    plan.row["id"],
                ),
            )
            for seg_start, seg_end in plan.segments[1:]:
                conn.execute(
                    """
                    INSERT INTO schedules (
                        id, requirement_id,
                        start_y, start_m, start_d,
                        end_y, end_m, end_d,
                        owner
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        plan.row["requirement_id"],
                        seg_start.year,
                        seg_start.month,
                        seg_start.day,
                        seg_end.year,
                        seg_end.month,
                        seg_end.day,
                        plan.row["owner"],
                    ),
                )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

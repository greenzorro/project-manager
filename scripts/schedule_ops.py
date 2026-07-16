"""
File: schedule_ops.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Database-backed schedule write operations.
              Holiday + leave aware: loads non-business days from db automatically.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date

from db import DEFAULT_OWNER, connect
from schedule_utils import (
    add_business_days,
    load_non_business_days,
    move_schedule,
    split_at_non_business,
)


@dataclass
class ScheduleMovePlan:
    row: sqlite3.Row
    old_start: date
    old_end: date
    segments: list[tuple[date, date]]


def plan_schedule_move(
    db_path: str, owner: str, from_date: date, days: int
) -> list[ScheduleMovePlan]:
    non_bd = load_non_business_days(db_path, owner=owner)

    conn = connect(db_path)
    rows = conn.execute(
        """
        SELECT s.id, s.requirement_id, s.start_y, s.start_m, s.start_d,
               s.end_y, s.end_m, s.end_d, s.owner,
               r.name AS requirement_name
        FROM schedules s
        JOIN requirements r ON s.requirement_id = r.id
        WHERE s.owner = ?
          AND r.name NOT GLOB '__*'
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
        new_start, new_end = move_schedule(old_start, old_end, days, non_bd)
        segments = split_at_non_business(new_start, new_end, non_bd)
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


def offset_schedule_end(
    db_path: str,
    schedule_id: str,
    days: int,
    owner: str | None = None,
) -> date:
    """Shift a schedule's end by N business days (positive=extend, negative=shorten).

    Returns the new end date. Caller should then use split_at_non_business()
    if the new range crosses non-business days.
    """
    non_bd = load_non_business_days(db_path, owner=owner)
    conn = connect(db_path)
    row = conn.execute(
        "SELECT end_y, end_m, end_d FROM schedules WHERE id=?", (schedule_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"Schedule {schedule_id} not found")

    old_end = date(row["end_y"], row["end_m"], row["end_d"])
    return add_business_days(old_end, days, non_bd)


def adjust_schedule_end(
    db_path: str,
    schedule_id: str,
    days: int,
    owner: str | None = None,
) -> list[tuple[date, date]]:
    """Adjust a schedule's end by N business days (positive=extend, negative=shorten),
    splitting if the adjusted range crosses non-business days."""
    conn = connect(db_path)
    row = conn.execute(
        """
        SELECT id, requirement_id, start_y, start_m, start_d,
               end_y, end_m, end_d, owner
        FROM schedules
        WHERE id=?
        """,
        (schedule_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"Schedule {schedule_id} not found")

    schedule_owner = owner or row["owner"]
    non_bd = load_non_business_days(db_path, owner=schedule_owner)
    old_start = date(row["start_y"], row["start_m"], row["start_d"])
    old_end = date(row["end_y"], row["end_m"], row["end_d"])
    new_end = add_business_days(old_end, days, non_bd)
    if new_end < old_start:
        new_end = old_start
    segments = split_at_non_business(old_start, new_end, non_bd)

    conn = connect(db_path)
    conn.execute("BEGIN")
    try:
        first_start, first_end = segments[0]
        conn.execute(
            """
            UPDATE schedules
            SET start_y=?, start_m=?, start_d=?,
                end_y=?, end_m=?, end_d=?,
                owner=?
            WHERE id=?
            """,
            (
                first_start.year,
                first_start.month,
                first_start.day,
                first_end.year,
                first_end.month,
                first_end.day,
                schedule_owner,
                schedule_id,
            ),
        )
        for seg_start, seg_end in segments[1:]:
            conn.execute(
                """
                INSERT INTO schedules(
                    id, requirement_id,
                    start_y, start_m, start_d,
                    end_y, end_m, end_d,
                    owner
                )
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(uuid.uuid4()),
                    row["requirement_id"],
                    seg_start.year,
                    seg_start.month,
                    seg_start.day,
                    seg_end.year,
                    seg_end.month,
                    seg_end.day,
                    schedule_owner,
                ),
            )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()
    return segments


def add_schedule(
    db_path: str,
    requirement_id: str,
    start: date,
    end: date,
    *,
    owner: str = "",
) -> int:
    """Add a schedule segment, auto-splitting at non-business days.

    Defaults: owner from PM_DEFAULT_OWNER.

    Returns number of segments created.
    """
    if not owner:
        owner = DEFAULT_OWNER

    non_bd = load_non_business_days(db_path, owner=owner)
    segments = split_at_non_business(start, end, non_bd)

    conn = connect(db_path)
    conn.execute("BEGIN")
    try:
        for seg_start, seg_end in segments:
            conn.execute(
                """INSERT INTO schedules
                   (id, requirement_id, start_y, start_m, start_d, end_y, end_m, end_d, owner)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), requirement_id,
                 seg_start.year, seg_start.month, seg_start.day,
                 seg_end.year, seg_end.month, seg_end.day, owner),
            )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    return len(segments)

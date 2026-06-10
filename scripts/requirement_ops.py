"""
File: requirement_ops.py
Project: project-manager
Description: Requirement creation, insertion, and delivery use cases.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date

from db import DEFAULT_OWNER, DEFAULT_PROJECT_NAME, connect, resolve_project_id
from schedule_utils import add_business_days, load_non_business_days, split_at_non_business
from schedule_ops import apply_schedule_move, plan_schedule_move


def insert_and_push(
    db_path: str,
    new_req_name: str,
    type_id: str,
    requester: str,
    *,
    project_id: str = "",
    owner: str = "",
    notes: str | None = None,
    insert_before_req_name: str = "",
    duration_days: int = 1,
    push_days: int = 1,
) -> None:
    """Insert a new requirement + schedule, then push all subsequent tasks.

    Args:
        type_id: req_types UUID, e.g. UI设计 → '023750d9-...'
        requester: 需求方 name
        project_id: defaults to PM_DEFAULT_PROJECT from .env
        owner: schedule owner, defaults to PM_DEFAULT_OWNER from .env
        insert_before_req_name: if set, insert before this requirement and push subsequent tasks
        push_days: how many business days to push subsequent tasks
    """
    non_bd = load_non_business_days(db_path, owner=owner or DEFAULT_OWNER)

    conn = connect(db_path)

    if not project_id and DEFAULT_PROJECT_NAME:
        project_id = resolve_project_id(conn, DEFAULT_PROJECT_NAME) or ""
    if not project_id:
        conn.close()
        raise ValueError("No project_id provided and PM_DEFAULT_PROJECT not found in database")
    if not owner:
        owner = DEFAULT_OWNER

    if insert_before_req_name:
        first_sched = conn.execute(
            """
            SELECT s.start_y, s.start_m, s.start_d
            FROM schedules s
            JOIN requirements r ON s.requirement_id = r.id
            WHERE r.name=? AND s.owner=?
            ORDER BY s.start_y, s.start_m, s.start_d
            LIMIT 1
            """,
            (insert_before_req_name, owner),
        ).fetchone()

        if first_sched is None:
            conn.close()
            raise ValueError(f"Target requirement '{insert_before_req_name}' not found for owner '{owner}'")

        insert_date = date(
            first_sched["start_y"], first_sched["start_m"], first_sched["start_d"]
        )
    else:
        insert_date = date.today()

    new_req_id = str(uuid.uuid4())
    today = date.today()

    new_start = insert_date
    new_end = add_business_days(new_start, duration_days - 1, non_bd)

    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            INSERT INTO requirements (id, name, project_id, type_id,
                received_y, received_m, received_d, requesters, notes)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                new_req_id, new_req_name, project_id, type_id,
                today.year, today.month, today.day,
                requester, notes,
            ),
        )
        segments = split_at_non_business(new_start, new_end, non_bd)
        for seg_start, seg_end in segments:
            conn.execute(
                """
                INSERT INTO schedules (id, requirement_id,
                    start_y, start_m, start_d, end_y, end_m, end_d, owner)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(uuid.uuid4()), new_req_id,
                    seg_start.year, seg_start.month, seg_start.day,
                    seg_end.year, seg_end.month, seg_end.day,
                    owner,
                ),
            )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        conn.close()
        raise
    conn.close()

    if insert_before_req_name:
        plans = plan_schedule_move(db_path, owner, insert_date, push_days)
        plans = [p for p in plans if p.row["requirement_id"] != new_req_id]
        apply_schedule_move(db_path, plans)


def create_requirement(
    db_path: str,
    name: str,
    type_id: str,
    requester: str,
    *,
    project_id: str = "",
    owner: str = "",
    notes: str | None = None,
    duration_days: int = 0,
    start_date: date | None = None,
) -> str:
    """Create a requirement and optionally its schedule.

    Defaults: project_id from PM_DEFAULT_PROJECT, owner from PM_DEFAULT_OWNER,
              received date = today.

    If duration_days > 0, creates schedule starting from start_date (or today),
    auto-split at non-business days.

    Returns the new requirement UUID.
    """
    conn = connect(db_path)

    if not project_id and DEFAULT_PROJECT_NAME:
        project_id = resolve_project_id(conn, DEFAULT_PROJECT_NAME) or ""
    if not project_id:
        conn.close()
        raise ValueError("No project_id provided and PM_DEFAULT_PROJECT not found in database")
    if not owner:
        owner = DEFAULT_OWNER

    req_id = str(uuid.uuid4())
    today = date.today()

    conn.execute("BEGIN")
    try:
        conn.execute(
            """INSERT INTO requirements
               (id, name, project_id, type_id, received_y, received_m, received_d, requesters, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (req_id, name, project_id, type_id,
             today.year, today.month, today.day, requester, notes),
        )
        if duration_days > 0:
            non_bd = load_non_business_days(db_path, owner=owner)
            sched_start = start_date or today
            sched_end = add_business_days(sched_start, duration_days - 1, non_bd)
            segments = split_at_non_business(sched_start, sched_end, non_bd)
            for seg_start, seg_end in segments:
                conn.execute(
                    """INSERT INTO schedules
                       (id, requirement_id, start_y, start_m, start_d, end_y, end_m, end_d, owner)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4()), req_id,
                     seg_start.year, seg_start.month, seg_start.day,
                     seg_end.year, seg_end.month, seg_end.day, owner),
                )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    return req_id


def mark_delivered(
    db_path: str,
    req_id_or_name: str,
    *,
    actual_date: date | None = None,
    delivery_url: str = "",
    delivery_thumbnail: str = "",
) -> date:
    """Mark a requirement as delivered, with rule validation.

    Rules:
    1. If actual_date not given, uses max schedule end date
    2. Refuses if no schedules exist
    3. UI设计 requires ui_pages > 0
    4. Warns (but doesn't block) if delivery_url/thumbnail is empty

    Returns the actual delivery date written.
    """
    conn = connect(db_path)

    row = conn.execute(
        "SELECT id, name, type_id, ui_pages, delivery_url, delivery_thumbnail FROM requirements WHERE id=? OR name=?",
        (req_id_or_name, req_id_or_name),
    ).fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"Requirement '{req_id_or_name}' not found")

    req_id = row["id"]
    req_name = row["name"]

    type_row = conn.execute(
        "SELECT name FROM req_types WHERE id=?", (row["type_id"],)
    ).fetchone()
    type_name = type_row["name"] if type_row else ""

    if actual_date is None:
        sched_row = conn.execute(
            """SELECT end_y, end_m, end_d FROM schedules
               WHERE requirement_id=? AND owner!='-'
               ORDER BY end_y DESC, end_m DESC, end_d DESC LIMIT 1""",
            (req_id,),
        ).fetchone()
        if sched_row is None:
            conn.close()
            raise ValueError(
                f"'{req_name}' has no schedules — cannot auto-resolve delivery date. "
                f"Add a schedule first or specify actual_date explicitly."
            )
        actual_date = date(sched_row["end_y"], sched_row["end_m"], sched_row["end_d"])

    if type_name == "UI设计":
        ui_pages = row["ui_pages"] or 0
        if ui_pages <= 0:
            conn.close()
            raise ValueError(
                f"'{req_name}' is UI设计 but ui_pages={ui_pages}. Set ui_pages > 0 before marking delivered."
            )

    warnings = []
    if not (row["delivery_url"] or "").strip() and not delivery_url:
        warnings.append("delivery_url is empty")
    if not (row["delivery_thumbnail"] or "").strip() and not delivery_thumbnail:
        warnings.append("delivery_thumbnail is empty")
    if warnings:
        print(f"⚠ Warning for '{req_name}': {', '.join(warnings)}")

    conn.execute(
        """UPDATE requirements SET actual_y=?, actual_m=?, actual_d=?,
           delivery_url=CASE WHEN ? != '' THEN ? ELSE delivery_url END,
           delivery_thumbnail=CASE WHEN ? != '' THEN ? ELSE delivery_thumbnail END
           WHERE id=?""",
        (actual_date.year, actual_date.month, actual_date.day,
         delivery_url, delivery_url,
         delivery_thumbnail, delivery_thumbnail,
         req_id),
    )
    conn.commit()
    conn.close()
    return actual_date


def set_delivery_thumbnail(db_path: str, req_id_or_name: str, thumbnail: str) -> None:
    """Set a requirement delivery thumbnail path."""
    conn = connect(db_path)
    row = conn.execute(
        "SELECT id FROM requirements WHERE id=? OR name=?",
        (req_id_or_name, req_id_or_name),
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Requirement '{req_id_or_name}' not found")

    conn.execute(
        "UPDATE requirements SET delivery_thumbnail=? WHERE id=?",
        (thumbnail, row["id"]),
    )
    conn.commit()
    conn.close()

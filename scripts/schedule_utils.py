"""
File: schedule_utils.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Schedule utilities: business day arithmetic and weekend splitting.
             All functions accept an optional non_business_days set (holidays + leave).
"""

from datetime import date, timedelta


def load_non_business_days(db_path: str, owner: str | None = None) -> set[date]:
    """Load public holidays (owner='-') and optionally a person's leave dates.

    Args:
        owner: if provided, also loads this person's __请假__ dates.
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT start_y, start_m, start_d, end_y, end_m, end_d FROM schedules WHERE owner='-'"
    ).fetchall()

    if owner:
        leave_rows = conn.execute(
            """
            SELECT s.start_y, s.start_m, s.start_d, s.end_y, s.end_m, s.end_d
            FROM schedules s
            JOIN requirements r ON s.requirement_id = r.id
            WHERE s.owner=? AND r.name='__请假__'
            """,
            (owner,),
        ).fetchall()
        rows = list(rows) + leave_rows

    conn.close()

    non_bd: set[date] = set()
    for r in rows:
        s = date(r["start_y"], r["start_m"], r["start_d"])
        e = date(r["end_y"], r["end_m"], r["end_d"])
        d = s
        while d <= e:
            non_bd.add(d)
            d += timedelta(days=1)
    return non_bd


def is_business_day(
    d: date, non_business_days: set[date] | None = None
) -> bool:
    if d.weekday() >= 5:
        return False
    if non_business_days is not None and d in non_business_days:
        return False
    return True


def next_business_day(
    d: date, non_business_days: set[date] | None = None
) -> date:
    d = d + timedelta(days=1)
    while not is_business_day(d, non_business_days):
        d = d + timedelta(days=1)
    return d


def prev_business_day(
    d: date, non_business_days: set[date] | None = None
) -> date:
    d = d - timedelta(days=1)
    while not is_business_day(d, non_business_days):
        d = d - timedelta(days=1)
    return d


def add_business_days(
    d: date, days: int, non_business_days: set[date] | None = None
) -> date:
    if days > 0:
        for _ in range(days):
            d = next_business_day(d, non_business_days)
    elif days < 0:
        for _ in range(-days):
            d = prev_business_day(d, non_business_days)
    return d


def split_at_non_business(
    start: date, end: date, non_business_days: set[date] | None = None
) -> list[tuple[date, date]]:
    """Split a date range at non-business days (weekends, holidays, leave) into
    contiguous business-day-only segments."""

    def _has_gap(s: date, e: date) -> bool:
        d = s + timedelta(days=1)
        while d <= e:
            if not is_business_day(d, non_business_days):
                return True
            d += timedelta(days=1)
        return False

    if not _has_gap(start, end):
        return [(start, end)]

    segments: list[tuple[date, date]] = []
    current = start
    while current <= end:
        if not is_business_day(current, non_business_days):
            current = next_business_day(current, non_business_days)
            continue

        seg_end = current
        while seg_end < end:
            seg_end = seg_end + timedelta(days=1)
            if not is_business_day(seg_end, non_business_days):
                seg_end = seg_end - timedelta(days=1)
                break

        segments.append((current, seg_end))
        current = seg_end + timedelta(days=1)
        while current <= end and not is_business_day(current, non_business_days):
            current = current + timedelta(days=1)

    return segments


def move_schedule(
    start: date,
    end: date,
    days: int,
    non_business_days: set[date] | None = None,
) -> tuple[date, date]:
    """Move a schedule by N business days (positive=forward, negative=backward)."""
    new_start = add_business_days(start, days, non_business_days)
    duration = 0
    d = start
    while d <= end:
        if is_business_day(d, non_business_days):
            duration += 1
        d += timedelta(days=1)
    new_end = add_business_days(new_start, max(0, duration - 1), non_business_days)
    return new_start, new_end
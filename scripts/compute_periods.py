"""
File: compute_periods.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Compute stat period dates anchored to the current fiscal year.
"""

import argparse
import calendar
import sqlite3
from datetime import date, timedelta

from db import DEFAULT_DB_PATH, FY_START_MONTH, FY_END_MONTH

MONTH_NUMS = {
    "M01": FY_START_MONTH,
    "M02": FY_START_MONTH + 1,
    "M03": FY_START_MONTH + 2,
    "M04": FY_START_MONTH + 3,
    "M05": FY_START_MONTH + 4,
    "M06": FY_START_MONTH + 5,
    "M07": FY_START_MONTH + 6,
    "M08": FY_START_MONTH + 7,
    "M09": FY_START_MONTH + 8,
    "M10": (FY_START_MONTH + 9) % 12 or 12,
    "M11": (FY_START_MONTH + 10) % 12 or 12,
    "M12": (FY_START_MONTH + 11) % 12 or 12,
}

SEMESTER_RULES = {
    "S1": (FY_START_MONTH, 9),
    "S2": (10, FY_END_MONTH),
}


def _current_fy_start(today: date) -> int:
    return today.year if today.month >= FY_START_MONTH else today.year - 1


def _period_dates(period_name: str, period_type: str, today: date):
    if period_type == "月":
        return _month_dates(period_name, today)
    elif period_type == "S":
        return _semester_dates(period_name, today)
    elif period_type == "财年":
        return _fiscal_dates(period_name)
    raise ValueError(f"Unknown period type: {period_type}")


def _month_dates(name: str, today: date):
    m = MONTH_NUMS[name[:3]]
    fy = _current_fy_start(today)
    year = fy if m >= FY_START_MONTH else fy + 1
    start = date(year, m, 1)
    end = date(year, m, calendar.monthrange(year, m)[1])
    return start, end


def _semester_dates(name: str, today: date):
    sm, em = SEMESTER_RULES[name]
    fy = _current_fy_start(today)
    start_year = fy
    end_year = fy if sm <= em else fy + 1
    start = date(start_year, sm, 1)
    end = date(end_year, em, calendar.monthrange(end_year, em)[1])
    return start, end


def _fiscal_dates(name: str):
    fy_end_year = int(name[3:]) + 2000
    fy_start_year = fy_end_year - 1
    start = date(fy_start_year, FY_START_MONTH, 1)
    end = date(fy_end_year, FY_END_MONTH, calendar.monthrange(fy_end_year, FY_END_MONTH)[1])
    return start, end


def compute_periods(db_path: str) -> None:
    today = date.today()
    from db import connect
    conn = connect(db_path)

    rows = conn.execute(
        "SELECT id, name, type FROM stat_periods"
    ).fetchall()

    for pid, name, ptype in rows:
        start, end = _period_dates(name, ptype, today)
        before = start - timedelta(days=1)
        after = end + timedelta(days=1)

        conn.execute(
            """UPDATE stat_periods SET
               start_y=?, start_m=?, start_d=?,
               end_y=?, end_m=?, end_d=?,
               start_before_y=?, start_before_m=?, start_before_d=?,
               end_after_y=?, end_after_m=?, end_after_d=?
               WHERE id=?""",
            (
                start.year, start.month, start.day,
                end.year, end.month, end.day,
                before.year, before.month, before.day,
                after.year, after.month, after.day,
                pid,
            ),
        )

    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute stat period dates")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite database path")
    args = parser.parse_args()
    compute_periods(args.db_path)
    print(f"Period dates computed for {date.today()}")


if __name__ == "__main__":
    main()
"""
File: schedule_utils.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Schedule utilities: business day arithmetic and weekend splitting.
"""

from datetime import date, timedelta


def is_business_day(d: date) -> bool:
    return d.weekday() < 5


def next_business_day(d: date) -> date:
    d = d + timedelta(days=1)
    while not is_business_day(d):
        d = d + timedelta(days=1)
    return d


def add_business_days(d: date, days: int) -> date:
    for _ in range(days):
        d = next_business_day(d)
    return d


def crosses_weekend(start: date, end: date) -> bool:
    if start >= end:
        return False
    d = start + timedelta(days=1)
    while d <= end:
        if not is_business_day(d):
            return True
        d = d + timedelta(days=1)
    return False


def split_cross_weekend(start: date, end: date) -> list[tuple[date, date]]:
    """Split a date range that crosses Saturday/Sunday into segments without weekends.

    Example: (2026-06-12 Fri, 2026-06-15 Mon) → [(06-12, 06-12), (06-15, 06-15)]
    """
    if not crosses_weekend(start, end):
        return [(start, end)]

    segments = []
    current = start
    while current <= end:
        if not is_business_day(current):
            current = next_business_day(current)
            continue

        seg_end = current
        while seg_end < end:
            seg_end = seg_end + timedelta(days=1)
            if not is_business_day(seg_end):
                seg_end = seg_end - timedelta(days=1)
                break

        segments.append((current, seg_end))
        current = seg_end + timedelta(days=1)
        while current <= end and not is_business_day(current):
            current = current + timedelta(days=1)

    return segments


def move_schedule(start: date, end: date, days: int) -> tuple[date, date]:
    """Move a schedule by N business days forward."""
    new_start = add_business_days(start, days)
    duration = sum(1 for d in _date_range(start, end) if is_business_day(d))
    new_end = add_business_days(new_start, duration - 1)
    return new_start, new_end


def _date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d = d + timedelta(days=1)
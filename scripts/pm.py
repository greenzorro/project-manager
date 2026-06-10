"""
File: pm.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Unified CLI entry point for the project-manager system.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date

from compute_periods import compute_periods
from db import DEFAULT_DB_PATH, DEFAULT_HTML_DIR, connect, resolve_backup_path
from doctor import print_doctor, run_doctor
from holiday_ops import add_holiday_and_push
from output import print_table
from render_html import render_html
from requirement_ops import create_requirement, insert_and_push, mark_delivered, set_delivery_thumbnail
from schedule_ops import add_schedule, adjust_schedule_end, apply_schedule_move, plan_schedule_move
from stats import requester_stats


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def command_doctor(args: argparse.Namespace) -> int:
    return print_doctor(run_doctor(args.db_path))


def command_compute_periods(args: argparse.Namespace) -> int:
    compute_periods(args.db_path)
    print(f"Period dates computed for {date.today()}")
    return 0


def command_render_html(args: argparse.Namespace) -> int:
    dashboard_path, calendar_path, recent_path, history_path = render_html(
        args.db_path,
        os.path.abspath(args.output_dir),
    )
    print(f"Dashboard written: {dashboard_path}")
    print(f"Calendar written: {calendar_path}")
    print(f"Recent tasks written: {recent_path}")
    print(f"History tasks written: {history_path}")
    return 0


def command_stats_requester(args: argparse.Namespace) -> int:
    rows = requester_stats(args.db_path, include_system=args.include_system)
    print_table(
        ["requester", "requests", "delivered", "open"],
        [
            [
                row["requester"],
                str(row["req_count"]),
                str(row["delivered_count"]),
                str(row["open_count"]),
            ]
            for row in rows
        ],
    )
    return 0


def resolve_named_id(db_path: str, table: str, value: str, label: str) -> str:
    conn = connect(db_path)
    try:
        row = conn.execute(
            f"SELECT id FROM {table} WHERE id=? OR name=?",
            (value, value),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"{label} '{value}' not found")
    return row["id"]


def resolve_type_arg(args: argparse.Namespace) -> str:
    value = args.type_id or args.type_name
    if not value:
        raise ValueError("Provide --type-id or --type")
    return resolve_named_id(args.db_path, "req_types", value, "Requirement type")


def resolve_project_arg(args: argparse.Namespace) -> str:
    value = args.project_id or args.project_name
    if not value:
        return ""
    return resolve_named_id(args.db_path, "projects", value, "Project")


def resolve_requirement_arg(db_path: str, value: str) -> str:
    return resolve_named_id(db_path, "requirements", value, "Requirement")


def command_requirement_create(args: argparse.Namespace) -> int:
    req_id = create_requirement(
        args.db_path,
        args.name,
        resolve_type_arg(args),
        args.requester,
        project_id=resolve_project_arg(args),
        owner=args.owner or "",
        notes=args.notes,
        duration_days=args.duration_days,
        start_date=args.start_date,
    )
    print(f"Requirement created: {req_id}")
    return 0


def command_requirement_deliver(args: argparse.Namespace) -> int:
    actual = mark_delivered(
        args.db_path,
        args.requirement,
        actual_date=args.actual_date,
        delivery_url=args.url or "",
        delivery_thumbnail=args.thumbnail or "",
    )
    print(f"Requirement delivered on {actual.isoformat()}")
    return 0


def command_requirement_insert(args: argparse.Namespace) -> int:
    insert_and_push(
        args.db_path,
        args.name,
        resolve_type_arg(args),
        args.requester,
        project_id=resolve_project_arg(args),
        owner=args.owner or "",
        notes=args.notes,
        insert_before_req_name=args.before,
        duration_days=args.duration_days,
        push_days=args.push_days,
    )
    print("Requirement inserted and subsequent schedules pushed.")
    return 0


def command_requirement_thumbnail(args: argparse.Namespace) -> int:
    set_delivery_thumbnail(args.db_path, args.requirement, args.thumbnail)
    print("Requirement thumbnail updated.")
    return 0


def command_schedule_add(args: argparse.Namespace) -> int:
    requirement_id = resolve_requirement_arg(args.db_path, args.requirement)
    count = add_schedule(
        args.db_path,
        requirement_id,
        args.start_date,
        args.end_date,
        owner=args.owner or "",
    )
    print(f"Schedule segments created: {count}")
    return 0


def command_schedule_adjust(args: argparse.Namespace) -> int:
    segments = adjust_schedule_end(
        args.db_path,
        args.schedule_id,
        args.days,
        owner=args.owner,
    )
    rendered = ", ".join(f"{start.isoformat()}..{end.isoformat()}" for start, end in segments)
    print(f"Schedule adjusted: {rendered}")
    return 0


def command_schedule_move(args: argparse.Namespace) -> int:
    plans = plan_schedule_move(args.db_path, args.owner, args.from_date, args.days)
    if not plans:
        print("No matching schedules.")
        return 0

    print_schedule_move_plan(plans)

    if not args.apply:
        print("\nDry run only. Re-run with --apply to write changes.")
        return 0

    apply_schedule_move(args.db_path, plans)
    print("\nApplied local schedule changes.")
    return 0


def command_holiday_add(args: argparse.Namespace) -> int:
    add_holiday_and_push(args.db_path, args.start_date, args.end_date, holiday=True)
    print(f"Public holiday added: {args.start_date.isoformat()}..{args.end_date.isoformat()}")
    return 0


def command_leave_add(args: argparse.Namespace) -> int:
    add_holiday_and_push(
        args.db_path,
        args.start_date,
        args.end_date,
        holiday=False,
        owner=args.owner,
    )
    print(f"Leave added for {args.owner}: {args.start_date.isoformat()}..{args.end_date.isoformat()}")
    return 0


def print_schedule_move_plan(plans) -> None:
    rows = []
    for plan in plans:
        new_range = ", ".join(
            f"{seg_start.isoformat()}..{seg_end.isoformat()}"
            for seg_start, seg_end in plan.segments
        )
        rows.append(
            [
                plan.row["requirement_name"],
                plan.row["owner"],
                f"{plan.old_start.isoformat()}..{plan.old_end.isoformat()}",
                new_range,
            ]
        )
    print_table(["requirement", "owner", "old", "new"], rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project manager local CLI")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="check database and model consistency")
    doctor.set_defaults(func=command_doctor)

    compute = subparsers.add_parser("compute-periods", help="recompute stat period dates")
    compute.set_defaults(func=command_compute_periods)

    render = subparsers.add_parser("render-html", help="render local dashboard and calendar HTML")
    render.add_argument("--output-dir", default=DEFAULT_HTML_DIR, help="output directory")
    render.set_defaults(func=command_render_html)

    stats = subparsers.add_parser("stats", help="show local stats")
    stats_subparsers = stats.add_subparsers(dest="stats_command", required=True)
    requester = stats_subparsers.add_parser("requester", help="count requirements by requester")
    requester.add_argument("--include-system", action="store_true", help="include __sys__ records")
    requester.set_defaults(func=command_stats_requester)

    requirement = subparsers.add_parser("requirement", help="requirement write operations")
    requirement_subparsers = requirement.add_subparsers(dest="requirement_command", required=True)
    create = requirement_subparsers.add_parser("create", help="create a requirement")
    create.add_argument("--name", required=True, help="requirement name")
    create.add_argument("--type", dest="type_name", help="requirement type name or id")
    create.add_argument("--type-id", help="requirement type id")
    create.add_argument("--requester", required=True, help="requester")
    create.add_argument("--project", dest="project_name", help="project name or id")
    create.add_argument("--project-id", help="project id")
    create.add_argument("--owner", help="schedule owner")
    create.add_argument("--notes", help="notes")
    create.add_argument("--duration-days", type=int, default=0, help="business days to schedule")
    create.add_argument("--start", dest="start_date", type=parse_iso_date, help="schedule start YYYY-MM-DD")
    create.set_defaults(func=command_requirement_create)

    deliver = requirement_subparsers.add_parser("deliver", help="mark a requirement delivered")
    deliver.add_argument("requirement", help="requirement id or exact name")
    deliver.add_argument("--actual-date", type=parse_iso_date, help="actual delivery date YYYY-MM-DD")
    deliver.add_argument("--url", help="delivery URL")
    deliver.add_argument("--thumbnail", help="delivery thumbnail path under thumbnails/")
    deliver.set_defaults(func=command_requirement_deliver)

    insert = requirement_subparsers.add_parser("insert", help="insert a requirement before another and push schedules")
    insert.add_argument("--name", required=True, help="new requirement name")
    insert.add_argument("--type", dest="type_name", help="requirement type name or id")
    insert.add_argument("--type-id", help="requirement type id")
    insert.add_argument("--requester", required=True, help="requester")
    insert.add_argument("--before", required=True, help="target requirement name")
    insert.add_argument("--project", dest="project_name", help="project name or id")
    insert.add_argument("--project-id", help="project id")
    insert.add_argument("--owner", help="schedule owner")
    insert.add_argument("--notes", help="notes")
    insert.add_argument("--duration-days", type=int, default=1, help="business days for the inserted task")
    insert.add_argument("--push-days", type=int, default=1, help="business days to push subsequent tasks")
    insert.set_defaults(func=command_requirement_insert)

    thumbnail = requirement_subparsers.add_parser("thumbnail", help="set delivery thumbnail")
    thumbnail.add_argument("requirement", help="requirement id or exact name")
    thumbnail.add_argument("thumbnail", help="thumbnail path under thumbnails/")
    thumbnail.set_defaults(func=command_requirement_thumbnail)

    schedule = subparsers.add_parser("schedule", help="schedule operations")
    schedule_subparsers = schedule.add_subparsers(dest="schedule_command", required=True)
    add = schedule_subparsers.add_parser("add", help="add a schedule to a requirement")
    add.add_argument("requirement", help="requirement id or exact name")
    add.add_argument("--start", dest="start_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    add.add_argument("--end", dest="end_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    add.add_argument("--owner", help="schedule owner")
    add.set_defaults(func=command_schedule_add)

    adjust = schedule_subparsers.add_parser("adjust", help="adjust a schedule end by business days (positive=extend, negative=shorten)")
    adjust.add_argument("schedule_id", help="schedule id")
    adjust.add_argument("--days", required=True, type=int, help="business days to adjust")
    adjust.add_argument("--owner", help="schedule owner override")
    adjust.set_defaults(func=command_schedule_adjust)

    move = schedule_subparsers.add_parser("move", help="move owner schedules by business days")
    move.add_argument("--owner", required=True, help="schedule owner")
    move.add_argument("--from", dest="from_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    move.add_argument("--days", required=True, type=int, help="business days to move (positive=forward, negative=backward)")
    move.add_argument("--apply", action="store_true", help="write changes; default is dry-run")
    move.set_defaults(func=command_schedule_move)

    holiday = subparsers.add_parser("holiday", help="public holiday and personal leave operations")
    holiday_subparsers = holiday.add_subparsers(dest="holiday_command", required=True)
    holiday_add = holiday_subparsers.add_parser("add", help="add a public holiday and push affected schedules")
    holiday_add.add_argument("--start", dest="start_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    holiday_add.add_argument("--end", dest="end_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    holiday_add.set_defaults(func=command_holiday_add)

    leave = holiday_subparsers.add_parser("leave", help="add personal leave and push that owner")
    leave.add_argument("--owner", required=True, help="schedule owner")
    leave.add_argument("--start", dest="start_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    leave.add_argument("--end", dest="end_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    leave.set_defaults(func=command_leave_add)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    if result == 0:
        try:
            from db import dump_db
            dump_db(args.db_path, resolve_backup_path(args.db_path))
        except (OSError, sqlite3.Error) as e:
            print(f"Warning: Database auto-backup failed: {e}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())

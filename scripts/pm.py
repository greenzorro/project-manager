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
from datetime import date

from compute_periods import compute_periods
from db import DEFAULT_BACKUP_PATH, DEFAULT_DB_PATH, DEFAULT_HTML_DIR
from doctor import print_doctor, run_doctor
from output import print_table
from render_html import render_html
from schedule_ops import apply_schedule_move, plan_schedule_move
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


def command_schedule_move(args: argparse.Namespace) -> int:
    if args.days < 0:
        print("days must be >= 0")
        return 2

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

    schedule = subparsers.add_parser("schedule", help="schedule operations")
    schedule_subparsers = schedule.add_subparsers(dest="schedule_command", required=True)
    move = schedule_subparsers.add_parser("move", help="move owner schedules by business days")
    move.add_argument("--owner", required=True, help="schedule owner")
    move.add_argument("--from", dest="from_date", required=True, type=parse_iso_date, help="YYYY-MM-DD")
    move.add_argument("--days", required=True, type=int, help="business days to move forward")
    move.add_argument("--apply", action="store_true", help="write changes; default is dry-run")
    move.set_defaults(func=command_schedule_move)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    if result == 0:
        try:
            from db import dump_db
            dump_db(args.db_path, DEFAULT_BACKUP_PATH)
        except (OSError, sqlite3.Error) as e:
            print(f"Warning: Database auto-backup failed: {e}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())

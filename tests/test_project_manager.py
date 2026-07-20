import io
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from compute_periods import _period_dates, compute_periods
from db import connect, dump_db, resolve_backup_path
from doctor import run_doctor
from holiday_ops import add_holiday_and_push
from init import init_db
from requirement_ops import create_requirement, insert_and_push, mark_delivered, set_delivery_thumbnail
from render_html import render_html
from schedule_ops import add_schedule, adjust_schedule_end
from stats import requester_stats
from thumbnail import generate_thumbnail


class ProjectManagerDryRunTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path.home() / "Downloads" / "temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="project-manager-tests-", dir=temp_root)
        self.work_dir = Path(self.temp_dir.name)
        self.db_path = self.work_dir / "pm.db"
        self.html_dir = self.work_dir / "html"
        shutil.copy2(PROJECT_DIR / "demo" / "pm.db", self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def rows(self, sql, params=()):
        conn = self.connect()
        try:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def scalar(self, sql, params=()):
        conn = self.connect()
        try:
            return conn.execute(sql, params).fetchone()[0]
        finally:
            conn.close()

    def req_type(self, name):
        return self.scalar("SELECT id FROM req_types WHERE name=?", (name,))

    def project(self, name):
        return self.scalar("SELECT id FROM projects WHERE name=?", (name,))

    def run_pm(self, *args, check=True):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "pm.py"),
                "--db-path",
                str(self.db_path),
                *args,
            ],
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"pm.py {' '.join(args)} failed with {result.returncode}\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return result

    def insert_req(self, req_id, name, type_name="数据分析", notes=None, ui_pages=0):
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO requirements(
                    id, name, project_id, type_id, requesters,
                    received_y, received_m, received_d, ui_pages, notes
                )
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    req_id,
                    name,
                    self.project("官方网站"),
                    self.req_type(type_name),
                    "DryRun",
                    2026,
                    6,
                    1,
                    ui_pages,
                    notes,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def insert_sched(self, sched_id, req_id, start, end, owner):
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO schedules(
                    id, requirement_id, start_y, start_m, start_d,
                    end_y, end_m, end_d, owner
                )
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    sched_id,
                    req_id,
                    start.year,
                    start.month,
                    start.day,
                    end.year,
                    end.month,
                    end.day,
                    owner,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def task_rows(self, req_ids):
        placeholders = ",".join("?" for _ in req_ids)
        return self.rows(
            f"""
            SELECT r.name, s.owner,
                   printf('%04d-%02d-%02d', s.start_y, s.start_m, s.start_d) AS start,
                   printf('%04d-%02d-%02d', s.end_y, s.end_m, s.end_d) AS end
            FROM schedules s
            JOIN requirements r ON r.id=s.requirement_id
            WHERE r.id IN ({placeholders})
            ORDER BY s.start_y, s.start_m, s.start_d, s.owner, r.name
            """,
            tuple(req_ids),
        )

    def test_add_schedule_splits_and_skips_non_business_days(self):
        self.insert_req("dry-add", "Dry Add")
        add_holiday_and_push(str(self.db_path), date(2026, 7, 6), date(2026, 7, 6), holiday=True)

        self.assertEqual(
            add_schedule(
                str(self.db_path),
                "dry-add",
                date(2026, 7, 3),
                date(2026, 7, 8),
                owner="Alice",
            ),
            2,
        )
        self.assertEqual(
            self.task_rows(["dry-add"]),
            [
                {"name": "Dry Add", "owner": "Alice", "start": "2026-07-03", "end": "2026-07-03"},
                {"name": "Dry Add", "owner": "Alice", "start": "2026-07-07", "end": "2026-07-08"},
            ],
        )

    def test_add_schedule_weekend_only_creates_no_segments(self):
        self.insert_req("dry-weekend", "Dry Weekend")

        self.assertEqual(
            add_schedule(
                str(self.db_path),
                "dry-weekend",
                date(2026, 7, 4),
                date(2026, 7, 5),
                owner="Alice",
            ),
            0,
        )
        self.assertEqual(self.task_rows(["dry-weekend"]), [])

    def test_mark_delivered_error_and_delivery_fields(self):
        self.insert_req("dry-nosched", "Dry No Schedule")
        with self.assertRaisesRegex(ValueError, "has no schedules"):
            mark_delivered(str(self.db_path), "dry-nosched")

        self.insert_req("dry-deliver", "Dry Deliver")
        self.insert_sched("dry-deliver-s", "dry-deliver", date(2026, 7, 13), date(2026, 7, 14), "Alice")
        self.assertEqual(
            mark_delivered(
                str(self.db_path),
                "dry-deliver",
                delivery_url="https://example.com/one",
                delivery_thumbnail="one.webp",
            ),
            date(2026, 7, 14),
        )
        self.assertEqual(
            self.rows(
                "SELECT delivery_url, delivery_thumbnail FROM requirements WHERE id='dry-deliver'"
            )[0],
            {"delivery_url": "https://example.com/one", "delivery_thumbnail": "one.webp"},
        )

        mark_delivered(str(self.db_path), "dry-deliver", actual_date=date(2026, 7, 15))
        self.assertEqual(
            self.rows(
                """
                SELECT actual_y, actual_m, actual_d, delivery_url, delivery_thumbnail
                FROM requirements WHERE id='dry-deliver'
                """
            )[0],
            {
                "actual_y": 2026,
                "actual_m": 7,
                "actual_d": 15,
                "delivery_url": "https://example.com/one",
                "delivery_thumbnail": "one.webp",
            },
        )
        set_delivery_thumbnail(str(self.db_path), "dry-deliver", "two.webp")
        self.assertEqual(
            self.scalar("SELECT delivery_thumbnail FROM requirements WHERE id='dry-deliver'"),
            "two.webp",
        )

    def test_public_holiday_pushes_each_owner(self):
        self.insert_req("dry-a", "Dry Alice")
        self.insert_sched("dry-sa", "dry-a", date(2026, 7, 1), date(2026, 7, 1), "Alice")
        self.insert_req("dry-b", "Dry Bob")
        self.insert_sched("dry-sb", "dry-b", date(2026, 7, 1), date(2026, 7, 1), "Bob")

        add_holiday_and_push(str(self.db_path), date(2026, 7, 1), date(2026, 7, 1), holiday=True)

        self.assertEqual(
            self.task_rows(["dry-a", "dry-b"]),
            [
                {"name": "Dry Alice", "owner": "Alice", "start": "2026-07-02", "end": "2026-07-02"},
                {"name": "Dry Bob", "owner": "Bob", "start": "2026-07-02", "end": "2026-07-02"},
            ],
        )

    def test_holiday_insert_and_schedule_push_roll_back_together(self):
        self.insert_req("dry-a", "Dry Alice")
        self.insert_sched("dry-sa", "dry-a", date(2026, 7, 1), date(2026, 7, 1), "Alice")
        before_holidays = self.scalar(
            """
            SELECT COUNT(*) FROM schedules s
            JOIN requirements r ON r.id=s.requirement_id
            WHERE r.name='__公共假期__'
            """
        )

        with patch(
            "holiday_ops.apply_schedule_move_on_connection",
            side_effect=sqlite3.OperationalError("schedule update failed"),
        ):
            with self.assertRaises(sqlite3.OperationalError):
                add_holiday_and_push(
                    str(self.db_path), date(2026, 7, 1), date(2026, 7, 1), holiday=True
                )

        self.assertEqual(
            self.scalar(
                """
                SELECT COUNT(*) FROM schedules s
                JOIN requirements r ON r.id=s.requirement_id
                WHERE r.name='__公共假期__'
                """
            ),
            before_holidays,
        )
        self.assertEqual(
            self.task_rows(["dry-a"]),
            [{"name": "Dry Alice", "owner": "Alice", "start": "2026-07-01", "end": "2026-07-01"}],
        )

    def test_personal_leave_pushes_only_that_owner(self):
        self.insert_req("dry-a", "Dry Alice")
        self.insert_sched("dry-sa", "dry-a", date(2026, 7, 6), date(2026, 7, 6), "Alice")
        self.insert_req("dry-b", "Dry Bob")
        self.insert_sched("dry-sb", "dry-b", date(2026, 7, 6), date(2026, 7, 6), "Bob")

        add_holiday_and_push(
            str(self.db_path), date(2026, 7, 6), date(2026, 7, 6), holiday=False, owner="Alice"
        )

        self.assertEqual(
            self.task_rows(["dry-a", "dry-b"]),
            [
                {"name": "Dry Bob", "owner": "Bob", "start": "2026-07-06", "end": "2026-07-06"},
                {"name": "Dry Alice", "owner": "Alice", "start": "2026-07-07", "end": "2026-07-07"},
            ],
        )

    def test_overlapping_leave_and_public_holiday_does_not_double_push(self):
        self.insert_req("dry-a", "Dry Alice")
        self.insert_sched("dry-sa", "dry-a", date(2026, 7, 8), date(2026, 7, 8), "Alice")

        add_holiday_and_push(str(self.db_path), date(2026, 7, 8), date(2026, 7, 8), holiday=True)
        add_holiday_and_push(
            str(self.db_path), date(2026, 7, 8), date(2026, 7, 8), holiday=False, owner="Alice"
        )

        self.assertEqual(
            self.task_rows(["dry-a"]),
            [{"name": "Dry Alice", "owner": "Alice", "start": "2026-07-09", "end": "2026-07-09"}],
        )

    def test_insert_and_push_keeps_inserted_task_in_target_slot(self):
        self.insert_req("dry-target", "Dry Target")
        self.insert_sched(
            "dry-st", "dry-target", date(2026, 8, 3), date(2026, 8, 3), "Alice"
        )
        self.insert_req("dry-later", "Dry Later")
        self.insert_sched("dry-sl", "dry-later", date(2026, 8, 4), date(2026, 8, 4), "Alice")

        insert_and_push(
            str(self.db_path),
            "Dry Inserted",
            self.req_type("数据分析"),
            "DryRun",
            project_id=self.project("官方网站"),
            owner="Alice",
            insert_before_req_name="Dry Target",
            duration_days=1,
            push_days=1,
        )

        rows = self.rows(
            """
            SELECT r.name, printf('%04d-%02d-%02d', s.start_y, s.start_m, s.start_d) AS start
            FROM schedules s
            JOIN requirements r ON r.id=s.requirement_id
            WHERE r.name IN ('Dry Target', 'Dry Later', 'Dry Inserted')
            ORDER BY s.start_y, s.start_m, s.start_d, r.name
            """
        )
        self.assertEqual(
            rows,
            [
                {"name": "Dry Inserted", "start": "2026-08-03"},
                {"name": "Dry Target", "start": "2026-08-04"},
                {"name": "Dry Later", "start": "2026-08-05"},
            ],
        )

    def test_requirement_insert_and_schedule_push_roll_back_together(self):
        self.insert_req("dry-target", "Dry Target")
        self.insert_sched(
            "dry-st", "dry-target", date(2026, 8, 3), date(2026, 8, 3), "Alice"
        )

        with patch(
            "requirement_ops.apply_schedule_move_on_connection",
            side_effect=sqlite3.OperationalError("schedule update failed"),
        ):
            with self.assertRaises(sqlite3.OperationalError):
                insert_and_push(
                    str(self.db_path),
                    "Dry Rolled Back",
                    self.req_type("数据分析"),
                    "DryRun",
                    project_id=self.project("官方网站"),
                    owner="Alice",
                    insert_before_req_name="Dry Target",
                )

        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM requirements WHERE name='Dry Rolled Back'"),
            0,
        )
        self.assertEqual(
            self.task_rows(["dry-target"]),
            [{"name": "Dry Target", "owner": "Alice", "start": "2026-08-03", "end": "2026-08-03"}],
        )

    def test_insert_and_push_splits_inserted_task_over_weekend(self):
        self.insert_req("dry-target", "Dry Target")
        self.insert_sched(
            "dry-st", "dry-target", date(2026, 8, 7), date(2026, 8, 7), "Alice"
        )

        insert_and_push(
            str(self.db_path),
            "Dry Inserted Long",
            self.req_type("数据分析"),
            "DryRun",
            project_id=self.project("官方网站"),
            owner="Alice",
            insert_before_req_name="Dry Target",
            duration_days=3,
            push_days=3,
        )

        rows = self.rows(
            """
            SELECT r.name, printf('%04d-%02d-%02d', s.start_y, s.start_m, s.start_d) AS start,
                   printf('%04d-%02d-%02d', s.end_y, s.end_m, s.end_d) AS end
            FROM schedules s
            JOIN requirements r ON r.id=s.requirement_id
            WHERE r.name IN ('Dry Target', 'Dry Inserted Long')
            ORDER BY s.start_y, s.start_m, s.start_d, r.name
            """
        )
        self.assertEqual(
            rows,
            [
                {"name": "Dry Inserted Long", "start": "2026-08-07", "end": "2026-08-07"},
                {"name": "Dry Inserted Long", "start": "2026-08-10", "end": "2026-08-11"},
                {"name": "Dry Target", "start": "2026-08-12", "end": "2026-08-12"},
            ],
        )

    def test_adjust_schedule_end_splits_over_weekend(self):
        self.insert_req("dry-ext", "Dry Extend")
        self.insert_sched("dry-se", "dry-ext", date(2026, 8, 7), date(2026, 8, 7), "Alice")

        self.assertEqual(
            adjust_schedule_end(str(self.db_path), "dry-se", 2),
            [(date(2026, 8, 7), date(2026, 8, 7)), (date(2026, 8, 10), date(2026, 8, 11))],
        )
        self.assertEqual(
            self.task_rows(["dry-ext"]),
            [
                {"name": "Dry Extend", "owner": "Alice", "start": "2026-08-07", "end": "2026-08-07"},
                {"name": "Dry Extend", "owner": "Alice", "start": "2026-08-10", "end": "2026-08-11"},
            ],
        )

    def test_adjust_schedule_end_shorten(self):
        self.insert_req("dry-shorten", "Dry Shorten")
        self.insert_sched("dry-ss", "dry-shorten", date(2026, 8, 3), date(2026, 8, 7), "Alice")

        self.assertEqual(
            adjust_schedule_end(str(self.db_path), "dry-ss", -2),
            [(date(2026, 8, 3), date(2026, 8, 5))],
        )
        self.assertEqual(
            self.task_rows(["dry-shorten"]),
            [
                {"name": "Dry Shorten", "owner": "Alice", "start": "2026-08-03", "end": "2026-08-05"},
            ],
        )

    def test_adjust_schedule_end_shorten_secondary_segment(self):
        """Shorten one segment of a split schedule; sibling segments stay as-is."""
        self.insert_req("dry-split", "Dry Split")
        self.insert_sched("dry-ss", "dry-split", date(2026, 8, 7), date(2026, 8, 7), "Alice")
        adjust_schedule_end(str(self.db_path), "dry-ss", 2)

        sched_ids = [
            r["id"]
            for r in self.rows(
                """
                SELECT id FROM schedules
                WHERE requirement_id='dry-split'
                AND start_y=2026 AND start_m=8 AND start_d=10
                """
            )
        ]
        self.assertEqual(len(sched_ids), 1)

        self.assertEqual(
            adjust_schedule_end(str(self.db_path), sched_ids[0], -1),
            [(date(2026, 8, 10), date(2026, 8, 10))],
        )
        self.assertEqual(
            self.task_rows(["dry-split"]),
            [
                {"name": "Dry Split", "owner": "Alice", "start": "2026-08-07", "end": "2026-08-07"},
                {"name": "Dry Split", "owner": "Alice", "start": "2026-08-10", "end": "2026-08-10"},
            ],
        )

    def test_add_business_days_negative_skips_non_business(self):
        from schedule_utils import add_business_days

        non_bd = {date(2026, 8, 6)}
        self.assertEqual(
            add_business_days(date(2026, 8, 7), -1, non_bd),
            date(2026, 8, 5),
        )
        self.assertEqual(
            add_business_days(date(2026, 8, 7), -2, non_bd),
            date(2026, 8, 4),
        )

    def test_add_business_days_negative_skips_weekend(self):
        from schedule_utils import add_business_days

        self.assertEqual(
            add_business_days(date(2026, 8, 10), -1),  # Monday -> Friday
            date(2026, 8, 7),
        )
        self.assertEqual(
            add_business_days(date(2026, 8, 10), -3),  # Mon -> Wed
            date(2026, 8, 5),
        )

    def test_move_schedule_backward(self):
        from schedule_utils import move_schedule

        new_start, new_end = move_schedule(
            date(2026, 8, 12), date(2026, 8, 14), -3  # Wed-Fri -> Fri-Tue
        )
        self.assertEqual(new_start, date(2026, 8, 7))
        self.assertEqual(new_end, date(2026, 8, 11))

    def test_create_mark_render_and_doctor_integration(self):
        req_id = create_requirement(
            str(self.db_path),
            "Dry Created UI",
            self.req_type("UI设计"),
            "DryRun",
            project_id=self.project("官方网站"),
            owner="Alice",
            duration_days=2,
            start_date=date(2026, 8, 7),
            notes="dry note",
        )
        with self.assertRaisesRegex(ValueError, "ui_pages=0"):
            mark_delivered(str(self.db_path), req_id)

        conn = self.connect()
        try:
            conn.execute("UPDATE requirements SET ui_pages=2 WHERE id=?", (req_id,))
            conn.commit()
        finally:
            conn.close()
        with redirect_stdout(io.StringIO()):
            actual = mark_delivered(str(self.db_path), req_id, delivery_url="https://example.com/dry")
        self.assertEqual(actual, date(2026, 8, 10))

        self.insert_req("dry-note", "Dry Note Render", notes="<b>escaped note</b>")
        self.insert_sched("dry-sn", "dry-note", date(2026, 9, 1), date(2026, 9, 1), "Alice")
        render_html(str(self.db_path), str(self.html_dir))
        recent = (self.html_dir / "recent.html").read_text(encoding="utf-8")
        self.assertIn("&lt;b&gt;escaped note&lt;/b&gt;", recent)
        self.assertNotIn("<b>escaped note</b>", recent)

        self.assertEqual(sum(1 for check in run_doctor(str(self.db_path)) if not check.ok), 0)

    def test_render_html_outputs_all_pages_with_expected_content(self):
        self.insert_req("dry-render", "Dry Render", notes="visible dry note")
        self.insert_sched("dry-render-s", "dry-render", date(2026, 9, 1), date(2026, 9, 1), "Alice")

        paths = render_html(str(self.db_path), str(self.html_dir))

        self.assertEqual([Path(path).name for path in paths], ["dashboard.html", "calendar.html", "recent.html", "history.html"])
        for name in ["dashboard.html", "calendar.html", "recent.html", "history.html"]:
            self.assertTrue((self.html_dir / name).exists(), name)
        self.assertIn("Dry Render", (self.html_dir / "recent.html").read_text(encoding="utf-8"))
        self.assertIn("visible dry note", (self.html_dir / "recent.html").read_text(encoding="utf-8"))
        self.assertIn("Alice", (self.html_dir / "calendar.html").read_text(encoding="utf-8"))
        self.assertIn("项目统计", (self.html_dir / "dashboard.html").read_text(encoding="utf-8"))

    def test_compute_periods_stats_and_db_restore(self):
        self.assertEqual(
            _period_dates("M01-4月", "月", date(2026, 6, 10)),
            (date(2026, 4, 1), date(2026, 4, 30)),
        )
        self.assertEqual(
            _period_dates("S2", "S", date(2026, 6, 10)),
            (date(2026, 10, 1), date(2027, 3, 31)),
        )
        self.assertEqual(
            _period_dates("FY-27", "财年", date(2026, 6, 10)),
            (date(2026, 4, 1), date(2027, 3, 31)),
        )

        compute_periods(str(self.db_path))
        self.assertEqual(
            self.scalar(
                """
                SELECT COUNT(*) FROM stat_periods
                WHERE start_y IS NULL OR end_y IS NULL
                   OR start_before_y IS NULL OR end_after_y IS NULL
                """
            ),
            0,
        )
        stats = requester_stats(str(self.db_path), include_system=False)
        self.assertTrue(stats)
        self.assertNotIn("__sys__", {row["requester"] for row in stats})
        stats_with_system = requester_stats(str(self.db_path), include_system=True)
        self.assertIn("__sys__", {row["requester"] for row in stats_with_system})

        backup_path = Path(resolve_backup_path(str(self.db_path)))
        dump_db(str(self.db_path), str(backup_path))
        self.db_path.unlink()
        with redirect_stdout(io.StringIO()):
            conn = connect(str(self.db_path))
        try:
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0], 0)
        finally:
            conn.close()

    def test_init_db_creates_valid_empty_database(self):
        init_path = self.work_dir / "init.pm.db"

        with redirect_stdout(io.StringIO()):
            init_db(str(init_path))
        compute_periods(str(init_path))

        conn = sqlite3.connect(init_path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM req_types WHERE id='__sys__'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM projects WHERE id='__sys__'").fetchone()[0], 1)
            sys_names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM requirements WHERE name IN ('__公共假期__', '__请假__')"
                )
            }
            self.assertEqual(sys_names, {"__公共假期__", "__请假__"})
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM stat_periods").fetchone()[0], 17)
            open_status = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT name, status FROM v_requirements WHERE actual_y IS NULL"
                )
            }
            self.assertEqual(open_status["__公共假期__"], "⚠️特殊")
            self.assertEqual(open_status["__请假__"], "⚠️特殊")
        finally:
            conn.close()
        self.assertEqual(sum(1 for check in run_doctor(str(init_path)) if not check.ok), 0)

    def test_requirement_status_distinguishes_open_and_system(self):
        self.insert_req("dry-open", "Dry Open Task")
        rows = {
            row["name"]: row["status"]
            for row in self.rows(
                """
                SELECT name, status FROM v_requirements
                WHERE name IN ('Dry Open Task', '__公共假期__', '__请假__')
                """
            )
        }
        self.assertEqual(rows["Dry Open Task"], "🚀进行中")
        self.assertEqual(rows["__公共假期__"], "⚠️特殊")
        self.assertEqual(rows["__请假__"], "⚠️特殊")
        self.assertEqual(sum(1 for check in run_doctor(str(self.db_path)) if not check.ok), 0)

    def test_cli_requirement_schedule_holiday_stats_and_render(self):
        self.run_pm(
            "requirement",
            "create",
            "--name",
            "CLI Created",
            "--type",
            "数据分析",
            "--requester",
            "DryRun",
            "--project",
            "官方网站",
        )
        self.run_pm(
            "schedule",
            "add",
            "CLI Created",
            "--start",
            "2026-09-02",
            "--end",
            "2026-09-04",
            "--owner",
            "Alice",
        )
        move_dry = self.run_pm(
            "schedule",
            "move",
            "--owner",
            "Alice",
            "--from",
            "2026-09-02",
            "--days",
            "1",
        )
        self.assertIn("Dry run only", move_dry.stdout)
        self.assertEqual(
            self.rows(
                """
                SELECT printf('%04d-%02d-%02d', s.start_y, s.start_m, s.start_d) AS start
                FROM schedules s JOIN requirements r ON r.id=s.requirement_id
                WHERE r.name='CLI Created'
                """
            )[0]["start"],
            "2026-09-02",
        )
        self.run_pm(
            "schedule",
            "move",
            "--owner",
            "Alice",
            "--from",
            "2026-09-02",
            "--days",
            "1",
            "--apply",
        )
        self.assertEqual(
            self.rows(
                """
                SELECT printf('%04d-%02d-%02d', s.start_y, s.start_m, s.start_d) AS start
                FROM schedules s JOIN requirements r ON r.id=s.requirement_id
                WHERE r.name='CLI Created'
                """
            )[0]["start"],
            "2026-09-03",
        )
        schedule_id = self.rows(
            """
            SELECT s.id FROM schedules s
            JOIN requirements r ON r.id=s.requirement_id
            WHERE r.name='CLI Created'
            ORDER BY s.start_y, s.start_m, s.start_d
            LIMIT 1
            """
        )[0]["id"]
        self.run_pm("schedule", "adjust", schedule_id, "--days", "1")
        self.run_pm("requirement", "thumbnail", "CLI Created", "cli.webp")
        self.run_pm("requirement", "deliver", "CLI Created", "--url", "https://example.com/cli")
        self.assertEqual(
            self.rows(
                """
                SELECT actual_y, actual_m, actual_d, delivery_thumbnail
                FROM requirements WHERE name='CLI Created'
                """
            )[0],
            {"actual_y": 2026, "actual_m": 9, "actual_d": 7, "delivery_thumbnail": "cli.webp"},
        )

        self.run_pm("holiday", "leave", "--owner", "Alice", "--start", "2026-09-09", "--end", "2026-09-09")
        stats = self.run_pm("stats", "requester")
        self.assertIn("DryRun", stats.stdout)
        output_dir = self.work_dir / "cli-html"
        self.run_pm("render-html", "--output-dir", str(output_dir))
        self.assertTrue((output_dir / "dashboard.html").exists())
        self.assertTrue((self.work_dir / "backup.sql").exists())

    def test_thumbnail_generate_from_source(self):
        """generate_thumbnail scales, converts, writes and updates DB."""
        from PIL import Image

        self.insert_req("dry-thumb", "Dry Thumb")
        # Build a 2000x1000 source image in temp dir.
        src = self.work_dir / "src.png"
        Image.new("RGB", (2000, 1000), (255, 0, 0)).save(src)

        # generate_thumbnail uses DATA_DIR for output; override env so the
        # thumbnails dir lands inside the temp work dir.
        import thumbnail as thumb_mod
        original_data_dir = thumb_mod.DATA_DIR
        thumb_mod.DATA_DIR = str(self.work_dir)
        try:
            filename = generate_thumbnail(
                str(self.db_path), "dry-thumb", str(src)
            )
        finally:
            thumb_mod.DATA_DIR = original_data_dir

        # Filename is slugified name + .webp.
        self.assertEqual(filename, "DryThumb.webp")
        out_path = self.work_dir / "thumbnails" / filename
        self.assertTrue(out_path.exists())
        # Long edge capped at 800.
        with Image.open(out_path) as im:
            self.assertLessEqual(max(im.size), 800)
        # DB updated.
        self.assertEqual(
            self.scalar(
                "SELECT delivery_thumbnail FROM requirements WHERE id='dry-thumb'"
            ),
            "DryThumb.webp",
        )

    def test_cli_thumbnail_generate_via_source(self):
        """CLI `requirement thumbnail <req> --source <path>` end-to-end."""
        from PIL import Image

        self.insert_req("dry-cli-thumb", "Dry CLI Thumb")
        src = self.work_dir / "cli_src.png"
        Image.new("RGB", (1600, 400), (0, 128, 0)).save(src)

        # Override DATA_DIR for this subprocess run via env. The CLI reads
        # DATA_DIR at import time, so we set PM_DATA_DIR.
        env = os.environ.copy()
        env["PM_DATA_DIR"] = str(self.work_dir)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "pm.py"),
                "--db-path",
                str(self.db_path),
                "requirement",
                "thumbnail",
                "dry-cli-thumb",
                "--source",
                str(src),
            ],
            cwd=PROJECT_DIR,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            result.returncode, 0, msg=f"STDOUT:{result.stdout}\nSTDERR:{result.stderr}"
        )
        out_path = self.work_dir / "thumbnails" / "DryCLIThumb.webp"
        self.assertTrue(out_path.exists())

    def test_cli_errors_are_reported(self):
        result = self.run_pm(
            "requirement",
            "create",
            "--name",
            "Bad Type",
            "--type",
            "不存在的类型",
            "--requester",
            "DryRun",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()

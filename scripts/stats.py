"""
File: stats.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Local statistics queries.
"""

from __future__ import annotations

from db import connect


def requester_stats(db_path: str, include_system: bool = False) -> list[dict]:
    conn = connect(db_path)
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT requesters AS requester,
                   COUNT(*) AS req_count,
                   SUM(CASE WHEN actual_y IS NOT NULL THEN 1 ELSE 0 END) AS delivered_count,
                   SUM(CASE WHEN actual_y IS NULL THEN 1 ELSE 0 END) AS open_count
            FROM requirements
            WHERE (? OR type_id != '__sys__')
            GROUP BY requesters
            ORDER BY req_count DESC, requester
            """,
            (1 if include_system else 0,),
        )
    ]
    conn.close()
    return rows

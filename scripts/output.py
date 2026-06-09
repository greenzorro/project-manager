"""
File: output.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Terminal table output helpers.
"""

from __future__ import annotations


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))

    def fmt(row: list[str]) -> str:
        return "  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))

    print(fmt(headers))
    print(fmt(["-" * width for width in widths]))
    for row in rows:
        print(fmt(row))

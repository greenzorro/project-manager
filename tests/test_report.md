# Test Report

## Scope

The test suite validates the local-first project management workflow across module-level behavior and CLI entry points.

Covered areas:

- Requirement creation, insertion, delivery, and validation rules
- Schedule creation, movement (forward and backward), adjustment (extend and shorten), weekend splitting, and non-business-day handling
- Public holidays and personal leave
- Static HTML rendering for dashboard, calendar, recent tasks, and history
- Fiscal period computation and requester statistics
- Database initialization (including system holiday/leave rows), backup restore, and doctor checks
- Requirement status rules (`🚀进行中` vs `⚠️特殊` via `GLOB '__*'`)
- CLI commands for requirement, schedule, holiday, stats, and render operations
- Sensitive-data hygiene checks for committed history and current project text

## Commands

```bash
python -m unittest discover -s tests
python -m py_compile scripts/*.py tests/*.py
git diff --check
```

## Result

```text
============================= 23 passed in 1.58s ==============================
```

Additional checks:

- Python bytecode compilation passed.
- Patch whitespace check passed.
- Test data is created from a temporary copy of `demo/pm.db`.
- Temporary test directories are created under `~/Downloads/temp` and cleaned up by the test harness.

## Sensitive Data Check

Current verification status:

- No tracked `.env` file.
- No obvious private path, formal project name, formal owner name, or internal company keyword in project text.
- No overlap between formal database sensitive text fields and current project text files.
- No overlap between formal database sensitive text fields and `demo/pm.db`.
- Public GitHub `main` contains the same two commits present in local remote-tracking history; local full-history sensitive-field scan found no matches.

## Notes

The test suite uses only Python standard library modules and does not require external services.

"""
File: config.py
Project: project-manager
Description: Environment, path, and business constant configuration.
"""

from __future__ import annotations

import os


def load_dotenv() -> None:
    """Load .env from the project root without overriding existing environment."""
    dotenv_path = os.path.join(PROJECT_DIR, ".env")
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

load_dotenv()

# PM_DATA_DIR env var allows separating code from data.
# If set, pm.db / html / thumbnails / backup.sql live under that path.
# If not set, falls back to demo/ inside the project (for OSS contributors).
DATA_DIR = os.environ.get("PM_DATA_DIR", os.path.join(PROJECT_DIR, "demo"))
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "pm.db")
DEFAULT_HTML_DIR = os.path.join(DATA_DIR, "html")
DEFAULT_BACKUP_PATH = os.path.join(DATA_DIR, "backup.sql")

# Optional defaults from .env, reducing input when adding requirements.
DEFAULT_PROJECT_NAME = os.environ.get("PM_DEFAULT_PROJECT", "")
DEFAULT_OWNER = os.environ.get("PM_DEFAULT_OWNER", "")

# Business constants.
COVER_VALUE_MULTIPLIER = 20
FY_START_MONTH = 4
FY_END_MONTH = 3

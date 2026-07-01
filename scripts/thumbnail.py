"""
File: thumbnail.py
Project: project-manager
Description: Generate delivery thumbnails from source images.

Scales the source image so its long edge measures at most ``max_size`` pixels,
converts to WebP, writes it under the ``thumbnails/`` directory, and updates
the requirement's ``delivery_thumbnail`` field.
"""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

from PIL import Image

from config import DATA_DIR
from db import connect
from requirement_ops import set_delivery_thumbnail

# Long-edge pixel cap for generated thumbnails, matching the skill spec.
DEFAULT_MAX_SIZE = 800
DEFAULT_QUALITY = 85
DEFAULT_FORMAT = "WEBP"


def _slugify(name: str) -> str:
    """Return a filesystem-safe base name derived from a requirement name.

    Keeps CJK characters (they are valid path characters) but strips
    punctuation, whitespace and reserved symbols.
    """
    # Normalize unicode, then drop punctuation/symbols/spaces.
    cleaned = unicodedata.normalize("NFKC", name)
    out = []
    for ch in cleaned:
        cat = unicodedata.category(ch)
        # Keep letters, numbers, and CJK ideographs.
        if cat.startswith(("L", "N")):
            out.append(ch)
    return "".join(out) or "thumbnail"


def _resolve_requirement_id(db_path: str, req_id_or_name: str) -> str:
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM requirements WHERE id=? OR name=?",
            (req_id_or_name, req_id_or_name),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"Requirement '{req_id_or_name}' not found")
    return row["id"]


def _resolve_requirement_name(db_path: str, req_id: str) -> str:
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM requirements WHERE id=?", (req_id,)
        ).fetchone()
    finally:
        conn.close()
    return row["name"] if row else req_id


def generate_thumbnail(
    db_path: str,
    req_id_or_name: str,
    src_path: str,
    *,
    max_size: int = DEFAULT_MAX_SIZE,
    quality: int = DEFAULT_QUALITY,
    filename: str | None = None,
) -> str:
    """Generate a WebP thumbnail for a requirement from a source image.

    1. Validates the source image can be opened.
    2. Scales it so the long edge is at most ``max_size`` pixels.
    3. Writes the WebP result under ``<DATA_DIR>/thumbnails/``.
    4. Updates the requirement's ``delivery_thumbnail`` field.

    Args:
        db_path: SQLite database path.
        req_id_or_name: Requirement id or exact name.
        src_path: Path to the source image (any PIL-readable format).
        max_size: Maximum long-edge pixel size. Defaults to 800.
        quality: WebP quality (1-100). Defaults to 85.
        filename: Custom thumbnail filename (without path). If omitted,
            uses a slug of the requirement name (falls back to requirement id).

    Returns:
        The relative thumbnail filename (e.g. ``"需求名.webp"``), which is the
        value written into ``delivery_thumbnail``.
    """
    if max_size <= 0:
        raise ValueError(f"max_size must be positive, got {max_size}")
    if not (1 <= quality <= 100):
        raise ValueError(f"quality must be between 1 and 100, got {quality}")

    src = Path(src_path)
    if not src.is_file():
        raise FileNotFoundError(f"Source image not found: {src_path}")

    req_id = _resolve_requirement_id(db_path, req_id_or_name)

    if filename is None:
        req_name = _resolve_requirement_name(db_path, req_id)
        base = _slugify(req_name) or req_id
        filename = f"{base}.{DEFAULT_FORMAT.lower()}"

    # Always end with .webp; normalize any user-supplied extension.
    stem = Path(filename).stem
    filename = f"{stem}.{DEFAULT_FORMAT.lower()}"

    thumbnails_dir = Path(DATA_DIR) / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    dst_path = thumbnails_dir / filename

    with Image.open(src) as im:
        image = im.convert("RGB")
        width, height = image.size
        long_side = max(width, height)
        if long_side > max_size:
            scale = max_size / long_side
            new_size = (max(1, int(round(width * scale))),
                        max(1, int(round(height * scale))))
            image = image.resize(new_size, Image.LANCZOS)
        image.save(dst_path, DEFAULT_FORMAT, quality=quality)

    set_delivery_thumbnail(db_path, req_id, filename)
    return filename

"""Manage legacy OneShot .run session files."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sessions_dir() -> Path:
    home = Path(os.environ.get("HOME", Path.home()))
    preferred = home / ".wipwn" / "sessions"
    if preferred.exists():
        return preferred
    # If a previous root run created ~/.wipwn with restrictive permissions,
    # fall back to the repo-local directory.
    return ROOT / ".wipwn" / "sessions"


def list_sessions() -> list[dict]:
    directory = sessions_dir()
    if not directory.exists():
        return []
    sessions = []
    try:
        paths = sorted(directory.glob("*.run"))
    except PermissionError:
        return []
    for path in paths:
        try:
            mask = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            mask = ""
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        sessions.append({
            "file": str(path),
            "bssid": path.stem,
            "mask": mask,
            "size": size,
        })
    return sessions


def export_sessions(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(list_sessions(), indent=2) + "\n", encoding="utf-8")
    return target


def clear_sessions() -> int:
    count = 0
    for item in list_sessions():
        try:
            Path(item["file"]).unlink()
            count += 1
        except OSError:
            pass
    return count

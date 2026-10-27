"""Router, vulnerable-device and PIN databases."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "database"
VULN_FILE = ROOT / "vulnwsc.txt"
ROUTER_FILE = DB_DIR / "router_models.json"
PINS_FILE = DB_DIR / "pins.csv"

VULN_SOURCES = [
    ("WiFuX", "https://raw.githubusercontent.com/msrofficial/WiFuX/main/vulnwsc.txt"),
    ("OneShot", "https://raw.githubusercontent.com/kimocoder/OneShot/master/vulnwsc.txt"),
    ("OneShot-Extended", "https://raw.githubusercontent.com/chkndrp/OneShot-Extended/master/vulnwsc.txt"),
    ("OneShot-fulvius", "https://raw.githubusercontent.com/fulvius31/OneShot/master/vulnwsc.txt"),
]
PINS_SOURCE = "https://raw.githubusercontent.com/fulvius31/OneShot/master/pins.csv"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _fetch(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "wipwn-v2-db/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def load_router_models() -> dict:
    if not ROUTER_FILE.exists():
        return {"vendors_count": 0, "vuln_confirmed_count": 0, "models": {}, "vuln_confirmed": []}
    return json.loads(ROUTER_FILE.read_text(encoding="utf-8"))


def load_vuln_list() -> list[str]:
    if not VULN_FILE.exists():
        return []
    lines = VULN_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        value = line.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def load_pins() -> dict[str, set[str]]:
    """Return OUI -> set(PIN). File format is PIN,OUI."""
    result: dict[str, set[str]] = {}
    if not PINS_FILE.exists():
        return result
    for line in PINS_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        pin, oui = line.split(",", 1)
        result.setdefault(oui.strip().upper(), set()).add(pin.strip())
    return result


def pins_for_oui(oui: str) -> list[str]:
    oui = oui.strip().upper()
    return sorted(load_pins().get(oui, set()))


def find_router(name: str) -> tuple[str, dict] | tuple[None, None]:
    """Best-effort vendor/model lookup."""
    if not name:
        return None, None
    needle = name.lower()
    db = load_router_models()
    best: tuple[int, str, dict] | None = None
    for vendor, info in db.get("models", {}).items():
        candidates = [vendor, *info.get("models", [])]
        for candidate in candidates:
            c = str(candidate).lower()
            if c == needle:
                return vendor, info
            if c and (c in needle or needle in c):
                score = len(c)
                if best is None or score > best[0]:
                    best = (score, vendor, info)
    if best:
        return best[1], best[2]
    return None, None


def default_pins(name: str) -> list[str]:
    vendor, info = find_router(name)
    if not info:
        return []
    return list(info.get("default_pins", []))


def default_creds(name: str) -> list[tuple[str, str]]:
    vendor, info = find_router(name)
    if not info:
        return []
    return [tuple(x) for x in info.get("default_creds", [])]


def pixie_rating(name: str) -> str:
    vendor, info = find_router(name)
    if not info:
        return "UNKNOWN"
    return str(info.get("pixie_dust_rating", "UNKNOWN"))


def is_vuln_model(name: str) -> bool:
    needle = name.strip().lower()
    if not needle:
        return False
    for entry in load_vuln_list():
        e = entry.lower()
        if e == needle or e in needle or needle in e:
            return True
    return False


def stats() -> dict:
    models = load_router_models()
    pins = load_pins()
    return {
        "vuln_entries": len(load_vuln_list()),
        "vendors": models.get("vendors_count", len(models.get("models", {}))),
        "confirmed_vuln": models.get("vuln_confirmed_count", len(models.get("vuln_confirmed", []))),
        "pin_ouis": len(pins),
        "pin_count": sum(len(v) for v in pins.values()),
    }


def _merge_lines(groups: Iterable[Iterable[str]]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for raw in group:
            value = raw.strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
    result.sort(key=str.lower)
    return result


def update_vuln_list(offline: bool = False, log=print) -> int:
    groups: list[list[str]] = [load_vuln_list()]
    if not offline:
        for name, url in VULN_SOURCES:
            try:
                groups.append(_fetch(url).decode("utf-8", errors="replace").splitlines())
                log(f"[+] {name}: downloaded")
            except Exception as exc:  # noqa: BLE001 - report and keep local data
                log(f"[!] {name}: {exc}")
    db = load_router_models()
    confirmed = db.get("vuln_confirmed", [])
    if isinstance(confirmed, list):
        groups.append([str(x) for x in confirmed])
    entries = _merge_lines(groups)
    _atomic_write(VULN_FILE, ("\n".join(entries) + "\n").encode("utf-8"))
    return len(entries)


def update_pins(offline: bool = False, log=print) -> int:
    if offline:
        return len(load_pins())
    try:
        data = _fetch(PINS_SOURCE)
    except Exception as exc:  # noqa: BLE001
        log(f"[!] pins.csv: {exc}")
        return len(load_pins())
    _atomic_write(PINS_FILE, data)
    return len(load_pins())

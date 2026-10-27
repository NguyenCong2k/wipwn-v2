"""Wi-Fi scanning and WPS metadata parsing."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import database

BSS_RE = re.compile(r"^BSS\s+([0-9a-fA-F:]{17})", re.MULTILINE)


def parse_iw_scan(text: str) -> list[dict]:
    networks: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("BSS "):
            if current:
                networks.append(current)
            bssid = line.split()[1].split("(")[0]
            current = {
                "bssid": bssid.lower(),
                "ssid": "",
                "signal": None,
                "frequency": None,
                "security": "",
                "wps": False,
                "wps_locked": False,
                "model": "",
                "model_number": "",
                "device_name": "",
            }
            continue
        if current is None:
            continue
        stripped = line.strip()
        meta = stripped[2:] if stripped.startswith("* ") else stripped
        if stripped.startswith("freq:"):
            try:
                current["frequency"] = int(float(stripped.split(":", 1)[1].strip()))
            except ValueError:
                pass
        elif stripped.startswith("signal:"):
            match = re.search(r"(-?\d+(?:\.\d+)?)", stripped)
            if match:
                current["signal"] = float(match.group(1))
        elif stripped.startswith("SSID:"):
            current["ssid"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("RSN:"):
            current["security"] = "WPA2"
        elif stripped.startswith("WPA:") and not current["security"]:
            current["security"] = "WPA"
        elif meta.startswith("WPS:"):
            current["wps"] = True
        elif "WPS locked:" in meta or "AP setup locked:" in meta:
            value = meta.split(":", 1)[1].strip().lower()
            try:
                current["wps_locked"] = int(value, 16) != 0
            except ValueError:
                current["wps_locked"] = value not in ("0", "no", "false", "")
        elif meta.startswith("Model:"):
            current["model"] = meta.split(":", 1)[1].strip()
        elif meta.startswith("Model Number:"):
            current["model_number"] = meta.split(":", 1)[1].strip()
        elif meta.startswith("Device name:"):
            current["device_name"] = meta.split(":", 1)[1].strip()
    if current:
        networks.append(current)
    return networks


def scan_termux() -> list[dict]:
    exe = shutil.which("termux-wifi-scaninfo")
    if not exe:
        return []
    result = subprocess.run([exe], capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    networks = []
    for item in data:
        networks.append({
            "bssid": str(item.get("bssid", "")).lower(),
            "ssid": item.get("ssid", ""),
            "signal": item.get("rssi"),
            "frequency": item.get("frequency"),
            "security": item.get("capabilities", ""),
            "wps": bool(item.get("wps", False)),
            "wps_locked": False,
            "model": "",
            "model_number": "",
            "device_name": "",
        })
    return networks


def scan(interface: str = "wlan0", timeout: int = 30) -> list[dict]:
    iw = shutil.which("iw")
    if iw:
        result = subprocess.run(
            [iw, "dev", interface, "scan"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode == 0:
            networks = parse_iw_scan(result.stdout)
            if networks:
                return networks
    return scan_termux()


def annotate(networks: list[dict]) -> list[dict]:
    for net in networks:
        name = " ".join(x for x in (net.get("model"), net.get("model_number"), net.get("device_name")) if x)
        vendor, info = database.find_router(name) if name else (None, None)
        net["vendor"] = vendor or ""
        net["known_vuln"] = database.is_vuln_model(name) if name else False
        net["pixie_rating"] = database.pixie_rating(name) if name else "UNKNOWN"
        if info:
            net["default_pins"] = list(info.get("default_pins", []))
    return networks


def format_table(networks: list[dict]) -> str:
    if not networks:
        return "No networks found."
    headers = ("#", "BSSID", "SSID", "SEC", "SIGNAL", "WPS", "LOCK", "MODEL", "PIXIE")
    rows = []
    for index, net in enumerate(networks, 1):
        signal = net.get("signal")
        signal_text = f"{signal:.0f}" if isinstance(signal, (int, float)) else "-"
        rows.append((
            str(index),
            net.get("bssid", ""),
            (net.get("ssid") or "<hidden>")[:24],
            (net.get("security") or "-")[:8],
            signal_text,
            "yes" if net.get("wps") else "no",
            "yes" if net.get("wps_locked") else "no",
            (net.get("model") or net.get("model_number") or "-")[:24],
            net.get("pixie_rating", "UNKNOWN"),
        ))
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    line = "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    out = [line, "-" * len(line)]
    for row in rows:
        out.append("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(out)


def save_json(networks: list[dict], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(networks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target

"""Credential report generation."""

from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_TXT = ROOT / "store" / "wipwn_crack_data.txt"
REPORTS_DIR = ROOT / "reports"
STORED_CSV = REPORTS_DIR / "stored.csv"


def _clean(value: str | None) -> str:
    return (value or "").strip()


def load_entries() -> list[dict]:
    entries: list[dict] = []
    seen: set[tuple[str, str]] = set()

    if STORED_CSV.exists():
        with STORED_CSV.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            for row in reader:
                if len(row) < 5 or row[0].lower() == "date":
                    continue
                key = (row[1].strip(), row[2].strip())
                if key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "date": _clean(row[0]),
                    "bssid": _clean(row[1]),
                    "ssid": _clean(row[2]),
                    "pin": _clean(row[3]),
                    "psk": _clean(row[4]),
                })

    if STORE_TXT.exists():
        text = STORE_TXT.read_text(encoding="utf-8", errors="replace")
        for block in text.split("----------------------------------------"):
            values = dict(re.findall(r"➠\s*([A-Z]+):\s*(.*)", block))
            if not values:
                continue
            entry = {
                "date": _clean(values.get("TIME")),
                "bssid": _clean(values.get("BSSID")),
                "ssid": _clean(values.get("SSID")),
                "pin": _clean(values.get("PIN")),
                "psk": _clean(values.get("PSK")),
            }
            key = (entry["bssid"], entry["ssid"])
            if key in seen:
                continue
            seen.add(key)
            entries.append(entry)

    entries.sort(key=lambda item: item.get("date", ""))
    return entries


def _html(entries: list[dict]) -> str:
    rows = []
    for entry in entries:
        rows.append(
            "<tr>"
            f"<td>{html.escape(entry.get('bssid', ''))}</td>"
            f"<td>{html.escape(entry.get('ssid', ''))}</td>"
            f"<td class=\"pin\">{html.escape(entry.get('pin', ''))}</td>"
            f"<td class=\"psk\">{html.escape(entry.get('psk', ''))}</td>"
            f"<td>{html.escape(entry.get('date', ''))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>wipwn report</title>
<style>
body {{ font-family: ui-monospace, monospace; background: #0d0d0d; color: #e6e6e6; margin: 0; padding: 24px; }}
h1 {{ color: #00ff88; text-align: center; }}
.sub {{ text-align: center; color: #888; margin-bottom: 24px; }}
.summary {{ text-align: center; margin: 18px 0 28px; }}
.summary span {{ color: #00ff88; font-size: 1.6em; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; background: #171717; }}
th {{ background: #00ff88; color: #000; padding: 10px; text-align: left; }}
td {{ padding: 9px 10px; border-bottom: 1px solid #2a2a2a; }}
.pin {{ color: #ffcc00; }} .psk {{ color: #88aaff; }}
footer {{ color: #555; text-align: center; margin-top: 24px; }}
</style>
</head>
<body>
<h1>wipwn report</h1>
<p class="sub">Generated {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
<div class="summary">Networks cracked: <span>{len(entries)}</span></div>
<table>
<thead><tr><th>BSSID</th><th>ESSID</th><th>WPS PIN</th><th>WPA PSK</th><th>Date</th></tr></thead>
<tbody>{''.join(rows) if rows else '<tr><td colspan="5">No entries</td></tr>'}</tbody>
</table>
<footer>wipwn v2 - authorized testing only</footer>
</body>
</html>
"""


def generate(fmt: str, output: str | Path | None = None) -> Path:
    entries = load_entries()
    fmt = fmt.lower()
    if fmt not in {"html", "csv", "json"}:
        raise ValueError("format must be html, csv or json")
    target = Path(output) if output else REPORTS_DIR / f"wipwn_report.{fmt}"
    target.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "html":
        target.write_text(_html(entries), encoding="utf-8")
    elif fmt == "json":
        target.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "bssid", "ssid", "pin", "psk"])
            writer.writeheader()
            writer.writerows(entries)
    return target

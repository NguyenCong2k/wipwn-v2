#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wipwn v2 - maintenance and scanner layer for the OneShot-based engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from wipwn_tools import __version__, android, database, report, scanner, session
from wipwn_tools.logger import setup_logging


def cmd_doctor(_: argparse.Namespace) -> int:
    checks = android.check_environment()
    android.print_environment(checks)
    failed = [item for item in checks if not item["ok"]]
    return 0 if not failed else 1


def cmd_scan(args: argparse.Namespace) -> int:
    logger = setup_logging(args.verbose, args.log_file)
    interface = args.interface or android.detect_interface() or "wlan0"
    logger.info("Scanning on %s", interface)
    networks = scanner.scan(interface, timeout=args.timeout)
    networks = scanner.annotate(networks)
    print(scanner.format_table(networks))
    if args.json:
        path = scanner.save_json(networks, args.json)
        logger.info("Saved %d networks to %s", len(networks), path)
    return 0 if networks else 1


def cmd_db(args: argparse.Namespace) -> int:
    logger = setup_logging(args.verbose, None)
    if args.action == "stats":
        info = database.stats()
        for key, value in info.items():
            print(f"{key:>16}: {value}")
        return 0
    if args.action == "update":
        count = database.update_vuln_list(offline=args.offline, log=logger.info)
        pins = database.update_pins(offline=args.offline, log=logger.info)
        logger.info("vulnwsc.txt: %d entries; pins.csv: %d OUIs", count, pins)
        return 0
    return 2


def cmd_sessions(args: argparse.Namespace) -> int:
    if args.action == "list":
        items = session.list_sessions()
        if not items:
            print("No saved sessions.")
            return 0
        for item in items:
            print(f"{item['bssid']}  mask={item['mask'] or '-':<7}  {item['file']}")
        return 0
    if args.action == "export":
        path = session.export_sessions(args.output)
        print(f"Exported to {path}")
        return 0
    if args.action == "clear":
        count = session.clear_sessions()
        print(f"Removed {count} session file(s).")
        return 0
    return 2


def cmd_report(args: argparse.Namespace) -> int:
    path = report.generate(args.format, args.output)
    print(f"Report written to {path}")
    return 0


def cmd_attack(args: argparse.Namespace) -> int:
    if not args.authorized:
        print("Refusing to run an attack without --authorized.")
        print("Only use this on a network you own or have written permission to test.")
        return 2
    legacy = ROOT / "legacy_oneshot.py"
    if not legacy.exists():
        print("legacy_oneshot.py is missing.")
        return 2

    import os
    import shlex
    import shutil
    import subprocess

    command = [sys.executable, str(legacy), *args.legacy_args]
    if hasattr(os, "getuid") and os.getuid() == 0:
        return subprocess.call(command, env=android.fix_env_for_root())

    su = shutil.which("su") or shutil.which("tsu")
    if not su:
        print("Root is required. Run this from a root shell (su/tsu).")
        return 2

    # su -c starts a fresh shell; pass Termux HOME/TMPDIR/PATH explicitly.
    env = android.fix_env_for_root()
    exports = " ".join(
        f"export {key}={shlex.quote(env[key])};"
        for key in ("HOME", "TMPDIR", "PATH")
        if key in env
    )
    inner = " ".join(shlex.quote(part) for part in command)
    shell_command = f"{exports} cd {shlex.quote(str(ROOT))} && exec {inner}"
    return subprocess.call([su, "-c", shell_command])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wipwn",
        description="wipwn v2 - scanner, database, session and report tools. "
                    "WPS attacks are only allowed with --authorized.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="check Android/Termux environment")
    doctor.set_defaults(func=cmd_doctor)

    scan = sub.add_parser("scan", help="scan nearby Wi-Fi/WPS networks")
    scan.add_argument("-i", "--interface", default=None)
    scan.add_argument("--timeout", type=int, default=30)
    scan.add_argument("--json", metavar="FILE", default=None)
    scan.add_argument("--log-file", default=None)
    scan.add_argument("-v", "--verbose", action="store_true")
    scan.set_defaults(func=cmd_scan)

    db = sub.add_parser("db", help="database commands")
    db.add_argument("action", choices=["stats", "update"])
    db.add_argument("--offline", action="store_true")
    db.add_argument("-v", "--verbose", action="store_true")
    db.set_defaults(func=cmd_db)

    sessions = sub.add_parser("sessions", help="legacy OneShot session files")
    sessions.add_argument("action", choices=["list", "export", "clear"])
    sessions.add_argument("-o", "--output", default="sessions.json")
    sessions.set_defaults(func=cmd_sessions)

    rep = sub.add_parser("report", help="generate HTML/CSV/JSON report")
    rep.add_argument("--format", choices=["html", "csv", "json"], default="html")
    rep.add_argument("-o", "--output", default=None)
    rep.set_defaults(func=cmd_report)

    attack = sub.add_parser("attack", help="run the legacy OneShot engine (authorized only)")
    attack.add_argument("--authorized", action="store_true",
                        help="confirm you own the network or have written permission")
    attack.add_argument("legacy_args", nargs=argparse.REMAINDER,
                        help="arguments passed to legacy_oneshot.py")
    attack.set_defaults(func=cmd_attack)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    if extra:
        if args.command == "attack":
            args.legacy_args.extend(extra)
        else:
            parser.error("unrecognized arguments: " + " ".join(extra))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

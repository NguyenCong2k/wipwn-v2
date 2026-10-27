"""Android/Termux environment checks and helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

TERMUX_HOME = Path("/data/data/com.termux/files/home")
TERMUX_PREFIX = Path("/data/data/com.termux/files/usr")
REQUIRED_BINARIES = ("python", "wpa_supplicant", "pixiewps", "iw")


def is_android() -> bool:
    return bool(hasattr(__import__("sys"), "getandroidapilevel"))


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or TERMUX_HOME.exists()


def which(name: str) -> str | None:
    return shutil.which(name)


def run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def root_uid() -> str | None:
    try:
        return str(os.getuid())
    except AttributeError:
        return None


def has_root() -> bool:
    uid = root_uid()
    if uid == "0":
        return True
    su = which("su") or which("tsu")
    if not su:
        return False
    try:
        result = run([su, "-c", "id -u"], timeout=5)
        return result.returncode == 0 and result.stdout.strip() == "0"
    except Exception:  # noqa: BLE001 - environment probe
        return False


def detect_interface() -> str | None:
    iw = which("iw")
    if iw:
        try:
            result = run([iw, "dev"], timeout=10)
            for line in result.stdout.splitlines():
                if "Interface" in line:
                    return line.split()[-1]
        except Exception:  # noqa: BLE001
            pass
    try:
        result = run(["ip", "link"], timeout=10)
        for line in result.stdout.splitlines():
            if ": wlan" in line and ":" in line:
                return line.split(":")[1].strip().split("@")[0]
    except Exception:  # noqa: BLE001
        pass
    return None


def _status(name: str, ok: bool, detail: str, fix: str = "") -> dict:
    return {"name": name, "ok": ok, "detail": detail, "fix": fix}


def check_environment() -> list[dict]:
    checks: list[dict] = []
    checks.append(_status("Android", is_android(), "Android runtime" if is_android() else "not Android"))
    checks.append(_status(
        "Termux",
        is_termux(),
        os.environ.get("PREFIX", "PREFIX not set"),
        "Install Termux from F-Droid.",
    ))
    uid = root_uid()
    checks.append(_status(
        "Root",
        has_root(),
        f"uid={uid}" if uid is not None else "unknown",
        "Root with Magisk/KernelSU/APatch is required for WPS attacks.",
    ))
    for binary in REQUIRED_BINARIES:
        path = which(binary)
        checks.append(_status(
            binary,
            bool(path),
            path or "not found in PATH",
            f"pkg install {binary.replace('_', '-')} -y",
        ))
    iface = detect_interface()
    checks.append(_status(
        "interface",
        bool(iface),
        iface or "no wlan interface found",
        "Check 'ip link show' or pass --interface explicitly.",
    ))
    home = Path(os.environ.get("HOME", ""))
    checks.append(_status(
        "HOME",
        home.exists() and str(home) != "/",
        str(home) or "unset",
        "Run through ./wipwn.sh or export HOME=/data/data/com.termux/files/home",
    ))
    tmp = Path(os.environ.get("TMPDIR", "/tmp"))
    checks.append(_status(
        "TMPDIR",
        tmp.exists() and os.access(tmp, os.W_OK),
        str(tmp),
        "export TMPDIR=/data/data/com.termux/files/usr/tmp",
    ))
    return checks


def print_environment(checks: list[dict]) -> None:
    for item in checks:
        mark = "OK" if item["ok"] else "FAIL"
        print(f"[{mark:4}] {item['name']:<16} {item['detail']}")
        if not item["ok"] and item["fix"]:
            print(f"         fix: {item['fix']}")


def fix_env_for_root() -> dict[str, str]:
    """Return environment suitable for a root child process on Termux."""
    env = os.environ.copy()
    if TERMUX_HOME.exists():
        env["HOME"] = str(TERMUX_HOME)
    tmp = TERMUX_PREFIX / "tmp"
    if tmp.exists():
        env["TMPDIR"] = str(tmp)
    if TERMUX_PREFIX.exists():
        env["PATH"] = f"{TERMUX_PREFIX / 'bin'}:{env.get('PATH', '')}"
    return env

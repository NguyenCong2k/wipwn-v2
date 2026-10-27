#!/data/data/com.termux/files/usr/bin/bash
# wipwn v2 wrapper for Termux (scanner/database/report use).
set -u
cd "$(dirname "$0")" || exit 1

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME="${HOME:-/data/data/com.termux/files/home}"
if [ "$HOME" = "/" ] || [ ! -d "$HOME" ]; then
    HOME="/data/data/com.termux/files/home"
fi
TMPDIR="$PREFIX/tmp"
mkdir -p "$TMPDIR" 2>/dev/null || true

export HOME TMPDIR
export PATH="$PREFIX/bin:$PATH"

PY="$PREFIX/bin/python"
if [ ! -x "$PY" ]; then
    PY="$(command -v python3 || command -v python)"
fi
if [ -z "${PY:-}" ]; then
    echo "python not found. Run: pkg install python -y"
    exit 1
fi

exec "$PY" wipwn.py "$@"

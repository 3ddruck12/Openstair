#!/usr/bin/env bash
# OpenStair von Projektverzeichnis aus starten (nutzt .venv, falls vorhanden).
set -e
cd "$(dirname "$0")"
VENV="${VENV:-.venv}"
if [[ -x "$VENV/bin/python" ]]; then
  exec "$VENV/bin/python" main.py "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 main.py "$@"
fi
echo "OpenStair: weder $VENV noch python3 gefunden." >&2
echo "  Bitte: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
exit 1

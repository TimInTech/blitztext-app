#!/usr/bin/env bash
# BlitztextLinux starten — immer mit der .venv (nicht mit dem System-python3)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PYTHON}" ]]; then
    echo "FEHLER: .venv nicht gefunden. Bitte zuerst 'bash scripts/install.sh' ausführen." >&2
    exit 1
fi

exec "${VENV_PYTHON}" "${SCRIPT_DIR}/app/blitztext_linux.py" "$@"

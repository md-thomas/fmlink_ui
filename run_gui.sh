#!/usr/bin/env bash
# Launches the OpenWave OTA Station GUI. Resolves its own location first,
# so it works no matter what directory you run it from or what it's
# symlinked as - handy if tab completion isn't finding the venv's python
# for you.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "error: no venv found at $SCRIPT_DIR/.venv" >&2
    echo "set one up first:" >&2
    echo "  cd $SCRIPT_DIR" >&2
    echo "  python3 -m venv --system-site-packages .venv" >&2
    echo "  .venv/bin/pip install -e ." >&2
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$VENV_PYTHON" -m ota_gui.main "$@"

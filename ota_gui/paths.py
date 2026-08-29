"""Puts the open_wave and ota_sim repos on sys.path so ota_station.py and
its dependencies (openwave_link, openwave_fec, modulate, demodulate, ...)
can be imported directly, the same way ota_station.py itself already
expects to be run (from within its own directory - see its pyproject.toml,
which only lists a handful of its modules under py-modules and isn't
pip-installed today). Must run before any `import ota_station` etc.

Defaults to sibling checkouts (open_wave_ui, open_wave and ota_sim all
under the same parent directory); override with the OPENWAVE_SRC/
OTA_SIM_SRC environment variables if yours live elsewhere.
"""
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

OPENWAVE_SRC = Path(os.environ.get('OPENWAVE_SRC', _REPO_ROOT / 'open_wave'))
OTA_SIM_SRC = Path(os.environ.get('OTA_SIM_SRC', _REPO_ROOT / 'ota_sim'))


def install():
    for src in (OPENWAVE_SRC, OTA_SIM_SRC):
        if not src.is_dir():
            raise RuntimeError(
                f"expected {src} to exist - set OPENWAVE_SRC/OTA_SIM_SRC if your "
                f"open_wave/ota_sim checkouts live somewhere other than as siblings "
                f"of open_wave_ui")
        path_str = str(src)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

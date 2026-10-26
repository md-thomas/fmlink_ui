"""Persists the GUI's own layout/field state (window size, pane split
positions, Station/Settings panel values) across launches - NOT anything
about the FMlink protocol itself (that all lives in ota_station.py/
Station). Saved once, on clean exit (App._on_close), and loaded once, at
startup (App.__init__) - not written continuously, so a crash simply
loses whatever changed since the last clean exit rather than risking a
corrupt file mid-write (see save()'s write-then-rename).

File > Reset UI (see app.py's _reset_ui) deletes this file and puts the
running window back to the same hardcoded defaults a first-ever launch
would use.
"""
import json

CONFIG_PATH = None


def _config_path():
    global CONFIG_PATH
    if CONFIG_PATH is None:
        import pathlib
        CONFIG_PATH = pathlib.Path.home() / '.config' / 'fmlink_ui' / 'ui_state.json'
    return CONFIG_PATH


def load():
    """Returns the saved state dict, or {} if there isn't one yet / it's
    unreadable - callers should treat every key as optional and fall back
    to their own hardcoded default, exactly as if this were a first-ever
    launch."""
    path = _config_path()
    if not path.exists():
        # Saved before the FMlink rename (the GUI was open_wave_ui then);
        # the next save() writes the new location.
        path = path.parent.parent / 'open_wave_ui' / path.name
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data):
    """Write-then-rename so a crash or power loss mid-write can't leave a
    half-written, unparseable file behind - load() would just silently
    fall back to defaults next time either way, but this avoids that
    happening to a previously-good file."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix('.json.tmp')
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(path)


def reset():
    """File > Reset UI - removes the saved state entirely so the next
    launch (and, per app.py's _reset_ui, the current one too) behaves like
    a first-ever run."""
    path = _config_path()
    path.unlink(missing_ok=True)

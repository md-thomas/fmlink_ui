# OpenWave OTA Station GUI

A `customtkinter` front end for `ota_station.py` (in the sibling `open_wave`
repo): send/receive messages, pick a Waveform Mode and FEC preset, and watch
a live I/Q constellation with SNR/EVM readout while talking to a peer
station through an `ota_sim` simulator relay.

It is a thin frontend over `ota_station.py`'s own `Station` class and its
`_handle_command()` dispatcher - every `/`-command the CLI supports
(`/ping`, `/ping survey`, `/renegotiate`, `/mode`, `/fec`, `/bandwidth`,
`/modes`, `/help`, `/quit`) works identically here, just from buttons/
dropdowns instead of typed commands (you can still type them directly into
the chat entry too).

## Setup

Expects `open_wave` and `ota_sim` checked out as sibling directories next to
this one (override with the `OPENWAVE_SRC`/`OTA_SIM_SRC` env vars if not):

```
Projects/
  open_wave/
  ota_sim/
  open_wave_ui/   <- this repo
```

```bash
python3 -m venv --system-site-packages .venv   # --system-site-packages picks up an existing editable ota_sim install
.venv/bin/pip install -e .
```

## Run

Start a simulator (from `open_wave`, or anywhere with `ota_sim` importable):

```bash
python3 -m ota_sim.simulator --distance-km 5 --base-snr-db 15
```

Then, per station:

```bash
.venv/bin/python3 -m ota_gui.main --sim-host 127.0.0.1 --sim-port 9500
```

`--sim-host`/`--sim-port`/`--local-port` are set once here at launch (see
`--help` for defaults) - there's no Simulator panel in the window at all.
The app connects immediately on launch using that address plus whatever's
in the **Station** panel's defaults (Station ID, peer callsign, Bandwidth)
and the **Settings** panel next to it (ACK/Verbose, Auto negotiate,
Mode/FEC) - the same as an unmodified `ota_station.py` with the equivalent
CLI flags, just without an interactive connect step. Once connected, the
Station panel's Station ID/Peer callsign fields and Settings panel's ACK/
Auto-negotiate/Verbose checkboxes lock (they only apply at connect time);
Bandwidth/Mode/FEC stay live and editable - picking a new one there acts
immediately on the session. Two GUI instances (or one GUI + one CLI
`ota_station.py`) pointed at the same simulator can talk to each other.

**File** menu: ota-sim-connect/ota-sim-disconnect (toggles - ends the current session, or
reconnects with whatever's currently in the Station/Settings panels, without
relaunching the app), **Reset UI** (puts the window back to its hardcoded
defaults - size, pane splits, Station/Settings fields - and clears the saved
state below so the next launch starts fresh too; doesn't touch a live
session), and Exit.

**Link** menu: Ping, Ping Survey, Renegotiate, Show Modes Table, and a
**Speed Test** submenu (200 B/1 KB/5 KB/20 KB) - sends a chat message of
the chosen size through the live session and times its confirmed delivery,
reporting the result in the **Status** log - requires ACK (otherwise "sent"
and "delivered" aren't distinguishable, so the timing would be
meaningless). Not an `ota_station.py` command; purely a GUI-side
measurement built on the normal `send_text()` path.

The conversation and the diagnostic noise around it live in two separate
logs, stacked below the Station/Settings panels: **Messages** (sent/
received chat text only, each line shown as `source -> destination:
message`) and **Status** below it (everything else - negotiate/ping/rx/ack
output, connect/disconnect banners, typed-command echoes, errors, `/modes`'
reference table, Speed Test progress/results) - each with its own Clear
button. That column is given noticeably more width than the constellation
plot next to it, which is deliberately smaller.

The **Constellation** panel keeps the last few received bursts overlaid
(not just the latest one) so short messages don't render as a nearly-empty
scatter - its own **Clear** button wipes that accumulated history (and the
SNR/EVM readout) on demand; note the readout itself always reflects only
the single most recent burst regardless, so the accumulated scatter never
affects the numbers, only what's drawn.

Messages/Status/constellation are all resizable by dragging the divider
between them (both the one between Messages and Status, and the one
between that whole column and the constellation) - `customtkinter` has no
splitter widget of its own, so these are plain `tkinter.PanedWindow`s
hosting the CTk panels as panes; the sash is styled to match the panel
background but won't look pixel-identical to a native CTk widget.

Window size, both pane split positions, and every Station/Settings field
are remembered across launches (saved to
`~/.config/open_wave_ui/ui_state.json` on a clean exit, loaded back at the
next startup) - **File > Reset UI** clears that and puts the running window
back to the same hardcoded defaults a first-ever launch would use.

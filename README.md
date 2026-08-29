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
.venv/bin/python3 -m ota_gui.main
```

Fill in the **Simulator** panel (sim host/port, local port) and the
**Station** panel (Station ID, peer callsign, ACK/Auto-negotiate/Verbose),
pick a starting Mode/FEC/Bandwidth in the panel on the right if you want,
then click **Connect** (in the Simulator panel, next to the address/port
fields) - or just start typing a message and hit Send/Enter, which connects
automatically first using whatever's currently in those fields if you
skip the button. Either way it's the same as an unmodified `ota_station.py`
with the equivalent CLI flags. Mode/FEC/Bandwidth stay live afterward too -
picking a new one there acts immediately on the live session (and, like
Send, will connect first if you pick one before clicking Connect). Two GUI
instances (or one GUI + one CLI `ota_station.py`) pointed at the same
simulator can talk to each other. The Connect button becomes Disconnect
once connected, ending the session and re-arming both panels' fields for a
new one.

The **Link** panel (below the constellation) has Ping/Ping Survey/
Renegotiate/Show Modes Table, plus **Speed Test**: sends a chat message of
a chosen size through the live session and times its confirmed delivery -
requires ACK (otherwise "sent" and "delivered" aren't distinguishable, so
the timing would be meaningless). Not an `ota_station.py` command; purely a
GUI-side measurement built on the normal `send_text()` path.

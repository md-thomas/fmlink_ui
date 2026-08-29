"""The one place Mode/FEC/Bandwidth live - both as the starting values used
when App auto-connects on first send, and (once a session is live) as live
controls. Picking a value from any of the three dropdowns/segments below
acts immediately - no separate Set button - synthesized as the exact
command string ota_station.py's own stdin loop would dispatch, then handed
to run_command() (see controller.py) - so mode-switch bandwidth-ceiling
checks, FEC-preset validation, etc. are the CLI's own logic, not
reimplemented here.

Every selection here is live from the moment the window opens, connected
or not - App's run_command() (see app.py's _ensure_connected) auto-connects
first, using whatever's currently set across the settings bar/this panel,
exactly like sending a chat message does. A disabled-until-connected
control that needs an interaction to create the very connection it's
disabled without is a dead end, so nothing here waits for one to already
exist - picking a starting Mode/FEC/Bandwidth before ever connecting is
exactly as valid an action as changing one live.

Ping/Ping Survey/Renegotiate/Show Modes Table live in their own
LinkActionsPanel (link_actions_panel.py) instead, below the constellation
plot. This panel shows no status text of its own - the live Mode/FEC
readout (and the "not connected" hint) live in the bottom status bar
instead (status_bar.py).

The FEC dropdown's "None" entry means "FEC off" - picking it is a pure
local/pending-value change, never sent as a command: _handle_command's
/fec can only ever turn FEC ON with a chosen preset, never back off
mid-session (matching ota_station.py's own CLI) - there's nothing to send
for "None" once a session is already live.
"""
import customtkinter as ctk

import openwave_fec as fec
import openwave_link as link

FEC_NONE = 'None'


class ModePanel(ctk.CTkFrame):
    def __init__(self, master, on_command):
        super().__init__(master)
        self._on_command = on_command
        self._connected = False

        mode_labels = [link.format_mode(m) for m in sorted(link.WAVEFORM_MODES)]
        self._mode_by_label = {link.format_mode(m): m for m in sorted(link.WAVEFORM_MODES)}
        mode_fec_row = ctk.CTkFrame(self, fg_color="transparent")
        mode_fec_row.pack(fill="x", padx=10, pady=(10, 4))

        mode_col = ctk.CTkFrame(mode_fec_row, fg_color="transparent")
        mode_col.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(mode_col, text="Mode", width=40, anchor="w").pack(side="left")
        self.mode_menu = ctk.CTkOptionMenu(mode_col, values=mode_labels, command=self._set_mode)
        self.mode_menu.pack(side="left", fill="x", expand=True)

        fec_col = ctk.CTkFrame(mode_fec_row, fg_color="transparent")
        fec_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(fec_col, text="FEC", width=35, anchor="w").pack(side="left")
        self.fec_menu = ctk.CTkOptionMenu(
            fec_col, values=[FEC_NONE] + sorted(fec.PRESETS), command=self._set_fec)
        self.fec_menu.set(FEC_NONE)
        self.fec_menu.pack(side="left", fill="x", expand=True)

        bw_row = ctk.CTkFrame(self, fg_color="transparent")
        bw_row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(bw_row, text="Bandwidth", width=70, anchor="w").pack(side="left")
        self.bandwidth_menu = ctk.CTkSegmentedButton(
            bw_row, values=["wide", "narrow"], command=self._set_bandwidth)
        self.bandwidth_menu.set("narrow")
        self.bandwidth_menu.pack(side="left", fill="x", expand=True, pady=(0, 10))

    def _set_mode(self, label):
        mode_id = self._mode_by_label[label]
        self._on_command(f'/mode {mode_id}')

    def _set_fec(self, preset):
        if preset == FEC_NONE:
            return  # pure pending-value change - see this file's docstring
        self._on_command(f'/fec {preset}')

    def _set_bandwidth(self, value):
        self._on_command(f'/bandwidth {value}')

    # -- starting values, read by App when auto-connecting -----------------
    def get_initial_mode_id(self):
        return self._mode_by_label[self.mode_menu.get()]

    def get_initial_fec(self):
        preset = self.fec_menu.get()
        if preset == FEC_NONE:
            return False, None
        return True, preset

    def get_initial_bandwidth(self):
        return self.bandwidth_menu.get()

    def refresh(self, station):
        """Resyncs the Bandwidth toggle from the live Station object (or
        lack of one) - called on every poll tick rather than tracked
        separately, so it's always exactly right regardless of what
        triggered a change (a selection here, a typed /command, or the
        peer). Mode/FEC status text itself lives in the status bar, not
        here - see this file's docstring."""
        self._connected = station is not None
        if station is None:
            return
        bandwidth = 'narrow' if station.max_symbol_rate is not None else 'wide'
        if self.bandwidth_menu.get() != bandwidth:
            self.bandwidth_menu.set(bandwidth)

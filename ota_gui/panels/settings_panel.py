"""Everything except who-this-station-is and Bandwidth (those live in
SessionPanel next to this one): ACK/Auto negotiate/Verbose (session-scoped
- no live/mid-session equivalent, so they lock once connected, same as
SessionPanel's Station ID/Peer callsign fields) and Mode/FEC
(live-adjustable - see below).

While Auto negotiate is checked, Mode/FEC are disabled: negotiate() runs on
this station's own first send and picks the mode/FEC itself, so a manual
choice made here beforehand would just get overridden - matches
ota_station.py's own --auto behavior (see Station.send_text()'s
_auto_negotiate_done gating). Uncheck Auto negotiate to pick Mode/FEC by
hand instead.

Mode/FEC act immediately on selection, no separate Set button -
synthesized as the exact command string ota_station.py's own stdin loop
would dispatch, then handed to run_command() (see controller.py) - so
mode-switch bandwidth-ceiling checks, FEC-preset validation, etc. are the
CLI's own logic, not reimplemented here. There's no Connect button anywhere
in the window to wait on, so every selection here just works, connected or
not - if startup's own connect attempt somehow hasn't landed yet,
_ensure_connected() runs again as a fallback, exactly like sending a chat
message does.

Ping/Ping Survey/Renegotiate/Show Modes Table/Speed Test all live in the
Link menu instead (see app.py's _build_menu). This panel shows no live
status text of its own - the live Mode/FEC readout (and the "not
connected" hint) live in the bottom status bar instead (status_bar.py).

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

_SESSION_SCOPED_ATTRS = ('ack_check', 'auto_check', 'verbose_check')


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, on_command):
        super().__init__(master)
        self._on_command = on_command

        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        toggles_row = ctk.CTkFrame(self, fg_color="transparent")
        toggles_row.pack(fill="x", padx=10, pady=(0, 6))
        self.ack_check = ctk.CTkCheckBox(toggles_row, text="ACK")
        self.ack_check.select()
        self.ack_check.pack(side="left")
        self.verbose_check = ctk.CTkCheckBox(toggles_row, text="Verbose")
        self.verbose_check.pack(side="left", padx=(10, 0))
        self.auto_check = ctk.CTkCheckBox(
            toggles_row, text="Auto negotiate", command=self._sync_mode_fec_state)
        self.auto_check.select()
        self.auto_check.pack(side="right")

        mode_labels = [link.format_mode(m) for m in sorted(link.WAVEFORM_MODES)]
        self._mode_by_label = {link.format_mode(m): m for m in sorted(link.WAVEFORM_MODES)}
        mode_fec_row = ctk.CTkFrame(self, fg_color="transparent")
        mode_fec_row.pack(fill="x", padx=10, pady=(4, 10))

        # Explicit (narrower-than-default) widths on the two OptionMenus,
        # PLUS dynamic_resizing=False - otherwise CTkOptionMenu ignores the
        # given width and sizes itself to fit its current label text
        # instead (e.g. "Mode 0 (600 sym/s, bpsk)"), which was the actual
        # reason this panel's row - and so the whole column it shares with
        # ConstellationPanel below (see app.py's shared-grid comment) -
        # stayed wide no matter how the column weights were biased toward
        # the Messages/Status column instead.
        mode_col = ctk.CTkFrame(mode_fec_row, fg_color="transparent")
        mode_col.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(mode_col, text="Mode", width=40, anchor="w").pack(side="left")
        self.mode_menu = ctk.CTkOptionMenu(
            mode_col, values=mode_labels, command=self._set_mode, width=70, dynamic_resizing=False)
        self.mode_menu.pack(side="left", fill="x", expand=True)

        fec_col = ctk.CTkFrame(mode_fec_row, fg_color="transparent")
        fec_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(fec_col, text="FEC", width=35, anchor="w").pack(side="left")
        self.fec_menu = ctk.CTkOptionMenu(
            fec_col, values=[FEC_NONE] + sorted(fec.PRESETS), command=self._set_fec, width=55,
            dynamic_resizing=False)
        self.fec_menu.set(FEC_NONE)
        self.fec_menu.pack(side="left", fill="x", expand=True)

        self._sync_mode_fec_state()

    def _set_mode(self, label):
        mode_id = self._mode_by_label[label]
        self._on_command(f'/mode {mode_id}')

    def _set_fec(self, preset):
        if preset == FEC_NONE:
            return  # pure pending-value change - see this file's docstring
        self._on_command(f'/fec {preset}')

    def _sync_mode_fec_state(self):
        state = "disabled" if self.auto_check.get() else "normal"
        self.mode_menu.configure(state=state)
        self.fec_menu.configure(state=state)

    # -- session settings, read by App on get_settings() ------------------
    def get_session_settings(self):
        return dict(
            use_ack=bool(self.ack_check.get()),
            auto=bool(self.auto_check.get()),
            verbose=bool(self.verbose_check.get()),
        )

    # -- starting values, read by App when auto-connecting -----------------
    def get_initial_mode_id(self):
        return self._mode_by_label[self.mode_menu.get()]

    def get_initial_fec(self):
        preset = self.fec_menu.get()
        if preset == FEC_NONE:
            return False, None
        return True, preset

    # -- ui_config persistence (see app.py's _save_ui_config/_apply_ui_config) --
    def export_state(self):
        return dict(
            use_ack=bool(self.ack_check.get()),
            verbose=bool(self.verbose_check.get()),
            auto=bool(self.auto_check.get()),
            mode_label=self.mode_menu.get(),
            fec_preset=self.fec_menu.get(),
        )

    def import_state(self, data):
        """Widget-state-only, like SessionPanel's import_state - never
        calls _on_command(), so this restores what the panel SHOWS (at
        startup, before any session exists; or via Reset UI), not a live
        change to whatever session might already be running."""
        if 'use_ack' in data:
            (self.ack_check.select() if data['use_ack'] else self.ack_check.deselect())
        if 'verbose' in data:
            (self.verbose_check.select() if data['verbose'] else self.verbose_check.deselect())
        if 'auto' in data:
            (self.auto_check.select() if data['auto'] else self.auto_check.deselect())
        if data.get('mode_label') in self._mode_by_label:
            self.mode_menu.set(data['mode_label'])
        if data.get('fec_preset') in ([FEC_NONE] + sorted(fec.PRESETS)):
            self.fec_menu.set(data['fec_preset'])
        self._sync_mode_fec_state()

    def reset_defaults(self):
        self.import_state(dict(
            use_ack=True, verbose=False, auto=True,
            mode_label=next(iter(self._mode_by_label)), fec_preset=FEC_NONE,
        ))

    def set_connected(self, connected):
        """Only ACK/Auto negotiate/Verbose lock - they're session-scoped,
        same as SessionPanel's Station ID/Peer callsign fields (see this
        file's docstring). Mode/FEC stay live/editable whether connected or
        not."""
        state = "disabled" if connected else "normal"
        for attr in _SESSION_SCOPED_ATTRS:
            getattr(self, attr).configure(state=state)

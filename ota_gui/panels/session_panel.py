"""Who this station is (--station-id, --dst, --bandwidth) - the simulator
address is fixed at launch (see main.py) and has no panel of its own at
all - App connects on startup using whatever's here at that moment (its
own defaults, since nothing's had a chance to type anything yet), so
Station ID/Peer callsign lock (see set_connected()) almost immediately.
Bandwidth is live-adjustable like Mode/FEC (see SettingsPanel, next door,
which has ACK/Auto negotiate/Verbose and Mode/FEC instead) - picking a new
value here acts immediately on the session, synthesized as the exact
'/bandwidth ...' command ota_station.py's own stdin loop would dispatch."""
import customtkinter as ctk

_INPUT_WIDGET_ATTRS = ('station_id_entry', 'dst_entry')

DEFAULTS = {'station_id': 'K0MDT', 'dst_id': 'W1AW', 'bandwidth': 'narrow'}


class SessionPanel(ctk.CTkFrame):
    def __init__(self, master, on_command):
        super().__init__(master)
        self._on_command = on_command

        ctk.CTkLabel(self, text="Station", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8)

        self.station_id_entry = self._field(row, "Station ID", "K0MDT")
        self.dst_entry = self._field(row, "Peer callsign", "W1AW")

        bw_col = ctk.CTkFrame(row, fg_color="transparent")
        bw_col.pack(side="left", padx=6)
        ctk.CTkLabel(bw_col, text="Bandwidth", anchor="w").pack(anchor="w")
        self.bandwidth_menu = ctk.CTkSegmentedButton(
            bw_col, values=["wide", "narrow"], command=self._set_bandwidth, width=220,
            dynamic_resizing=False)
        self.bandwidth_menu.set("narrow")
        self.bandwidth_menu.pack()

        self.error_label = ctk.CTkLabel(self, text="", text_color="#d0453b", anchor="w")
        self.error_label.pack(fill="x", padx=10, pady=(2, 8))

    def _field(self, parent, label, default):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.pack(side="left", padx=6)
        ctk.CTkLabel(col, text=label).pack(anchor="w")
        entry = ctk.CTkEntry(col, width=110)
        entry.insert(0, default)
        entry.pack()
        return entry

    def _set_bandwidth(self, value):
        self._on_command(f'/bandwidth {value}')

    def get_settings(self):
        """Returns {station_id, dst_id}, or raises ValueError with a
        user-facing message for App to show via show_error()."""
        station_id = self.station_id_entry.get().strip()
        if not station_id:
            raise ValueError("Enter a Station ID first")
        return dict(
            station_id=station_id,
            dst_id=self.dst_entry.get().strip() or 'ALL',
        )

    # -- starting value, read by App when auto-connecting -------------------
    def get_initial_bandwidth(self):
        return self.bandwidth_menu.get()

    # -- ui_config persistence (see app.py's _save_ui_config/_apply_ui_config) --
    def export_state(self):
        return dict(
            station_id=self.station_id_entry.get(),
            dst_id=self.dst_entry.get(),
            bandwidth=self.bandwidth_menu.get(),
        )

    def import_state(self, data):
        """Widget-state-only - deliberately never calls _on_command(), even
        for bandwidth: this restores what the panel SHOWS (at startup,
        before any session exists; or via Reset UI), not a live change to
        whatever session might already be running. A live change to
        Bandwidth already goes through _set_bandwidth() via the segmented
        button's own click handler instead."""
        if 'station_id' in data:
            self._set_entry(self.station_id_entry, data['station_id'])
        if 'dst_id' in data:
            self._set_entry(self.dst_entry, data['dst_id'])
        if data.get('bandwidth') in ('wide', 'narrow'):
            self.bandwidth_menu.set(data['bandwidth'])

    def _set_entry(self, entry, value):
        """delete()/insert() are silently no-ops on a disabled CTkEntry
        (same as plain tkinter) - Reset UI/a saved-state restore need to
        take effect even while connected (fields locked, see
        set_connected()), so this unlocks just long enough to write the
        value, then puts the lock back exactly as it was."""
        was_disabled = entry.cget('state') == 'disabled'
        if was_disabled:
            entry.configure(state='normal')
        entry.delete(0, 'end')
        entry.insert(0, value)
        if was_disabled:
            entry.configure(state='disabled')

    def reset_defaults(self):
        self.import_state(DEFAULTS)

    def show_error(self, message):
        self.error_label.configure(text=message)

    def set_connected(self, connected):
        state = "disabled" if connected else "normal"
        for attr in _INPUT_WIDGET_ATTRS:
            getattr(self, attr).configure(state=state)
        if connected:
            self.error_label.configure(text="")

    def refresh(self, station):
        """Resyncs the Bandwidth toggle from the live Station object (or
        lack of one) - called on every poll tick rather than tracked
        separately, so it's always exactly right regardless of what
        triggered a change (a selection here, a typed /command, or the
        peer)."""
        if station is None:
            return
        bandwidth = 'narrow' if station.max_symbol_rate is not None else 'wide'
        if self.bandwidth_menu.get() != bandwidth:
            self.bandwidth_menu.set(bandwidth)

"""The rest of what needs setting up before a session starts: who this
station is (--station-id, --dst) and the three CLI flags with no live/
mid-session equivalent (--ack, --auto, --verbose - _handle_command has no
command that can toggle any of these once a session is running, unlike
mode/FEC/bandwidth, which live in ModePanel instead, or the simulator
address, which lives in SimPanel)."""
import customtkinter as ctk

_INPUT_WIDGET_ATTRS = ('station_id_entry', 'dst_entry', 'ack_check', 'auto_check', 'verbose_check')


class SessionPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(self, text="Station", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8)

        self.station_id_entry = self._field(row, "Station ID", "K0MDT")
        self.dst_entry = self._field(row, "Peer callsign", "W1AW")

        toggles_col = ctk.CTkFrame(row, fg_color="transparent")
        toggles_col.pack(side="left", padx=6)
        self.ack_check = ctk.CTkCheckBox(toggles_col, text="ACK")
        self.ack_check.select()
        self.ack_check.pack(anchor="w")
        self.auto_check = ctk.CTkCheckBox(toggles_col, text="Auto negotiate")
        self.auto_check.select()
        self.auto_check.pack(anchor="w", pady=(4, 0))

        verbose_col = ctk.CTkFrame(row, fg_color="transparent")
        verbose_col.pack(side="left", padx=6)
        self.verbose_check = ctk.CTkCheckBox(verbose_col, text="Verbose")
        self.verbose_check.pack(anchor="w")

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

    def get_settings(self):
        """Returns {station_id, dst_id, use_ack, auto, verbose}, or raises
        ValueError with a user-facing message for App to show via
        show_error()."""
        station_id = self.station_id_entry.get().strip()
        if not station_id:
            raise ValueError("Enter a Station ID first")
        return dict(
            station_id=station_id,
            dst_id=self.dst_entry.get().strip() or 'ALL',
            use_ack=bool(self.ack_check.get()),
            auto=bool(self.auto_check.get()),
            verbose=bool(self.verbose_check.get()),
        )

    def show_error(self, message):
        self.error_label.configure(text=message)

    def set_connected(self, connected):
        state = "disabled" if connected else "normal"
        for attr in _INPUT_WIDGET_ATTRS:
            getattr(self, attr).configure(state=state)
        if connected:
            self.error_label.configure(text="")

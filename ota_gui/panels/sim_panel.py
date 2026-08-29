"""Simulator connection: where to reach the ota_sim relay (--sim-host/
--sim-port, --local-port), plus the Connect/Disconnect action itself - it
lives here because connecting IS reaching the simulator, so the button
belongs right next to the address/port fields it uses.

Send/Ping/etc. still connect on their own first if you skip this button
(see App._ensure_connected) - Connect just makes that step explicit and
gives you an obvious way to end a session with Disconnect, without having
to send something first to get a live one going."""
import customtkinter as ctk

_INPUT_WIDGET_ATTRS = ('sim_host_entry', 'sim_port_entry', 'local_port_entry')


class SimPanel(ctk.CTkFrame):
    def __init__(self, master, on_toggle):
        super().__init__(master)
        self._on_toggle = on_toggle
        self._connected = False

        ctk.CTkLabel(self, text="Simulator", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8)

        self.sim_host_entry = self._field(row, "Sim host", "127.0.0.1")
        self.sim_port_entry = self._field(row, "Sim port", "9500")
        self.local_port_entry = self._field(row, "Local port", "0")

        # A spacer label matching the real field labels' height, so the
        # button lines up with the entries below them exactly - more
        # robust than guessing a pady offset (which drifts with font/
        # theme metrics).
        button_col = ctk.CTkFrame(row, fg_color="transparent")
        button_col.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(button_col, text="").pack(anchor="w")
        self.connect_button = ctk.CTkButton(
            button_col, text="Connect", width=100, command=self._clicked)
        self.connect_button.pack()

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

    def _clicked(self):
        self._on_toggle()

    def get_settings(self):
        """Returns {sim_host, sim_port, local_port}, or raises ValueError
        with a user-facing message for App to show via show_error()."""
        try:
            sim_port = int(self.sim_port_entry.get().strip())
            local_port = int(self.local_port_entry.get().strip() or '0')
        except ValueError:
            raise ValueError("Sim port / local port must be numbers")
        return dict(
            sim_host=self.sim_host_entry.get().strip(),
            sim_port=sim_port,
            local_port=local_port,
        )

    def show_error(self, message):
        self.error_label.configure(text=message)

    def set_connected(self, connected):
        self._connected = connected
        self.connect_button.configure(text="Disconnect" if connected else "Connect")
        state = "disabled" if connected else "normal"
        for attr in _INPUT_WIDGET_ATTRS:
            getattr(self, attr).configure(state=state)
        if connected:
            self.error_label.configure(text="")

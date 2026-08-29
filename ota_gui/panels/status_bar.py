"""Every live status readout lives here: the current Mode/FEC (formerly
shown in ModePanel), and link counters (reuses
ota_station._link_counts_compact, the same compact rendering the CLI's
session summary uses). The Connect/Disconnect action itself lives in
sim_panel.py, next to the address/port fields it connects with."""
import customtkinter as ctk

import openwave_link as link
import ota_station

NOT_CONNECTED_HINT = ("not connected - picking a Mode/FEC/Bandwidth or clicking "
                       "Ping/etc. will connect first, using these settings")


class StatusBar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.label = ctk.CTkLabel(self, text=NOT_CONNECTED_HINT, anchor="w")
        self.label.pack(side="left", fill="x", expand=True, padx=10, pady=6)

    def refresh(self, station):
        if station is None:
            self.label.configure(text=NOT_CONNECTED_HINT)
            return
        fec_note = f"on ({station.fec_preset})" if station.use_fec else "off"
        self.label.configure(
            text=f"{station.station_id} <-> {station.dst_id}    "
                 f"{link.format_mode(station.mode_id)}, FEC {fec_note}    "
                 f"{ota_station._link_counts_compact(station.receiver)}")

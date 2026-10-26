"""Live I/Q constellation scatter + SNR/EVM readout, fed by Station's
on_symbols hook (see controller.py/StationController._connect) - fires
whenever a burst was found/synced, even one that later fails CRC, which is
exactly the case worth looking at."""
import collections

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import fmlink_modem as modem
import ota_station

# Keep a short rolling history of recent bursts (reset whenever the
# modulation changes) so the scatter reads as a populated constellation
# instead of a handful of points per keystroke-sized chat message.
HISTORY_BURSTS = 4

POINT_COLOR = '#3b8ed0'
IDEAL_COLOR = '#d0453b'
AXIS_COLOR = '#888888'


class ConstellationPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._history = collections.deque(maxlen=HISTORY_BURSTS)
        self._last_modulation = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(header, text="Constellation", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(side="left", padx=2)
        # Just calls reset() - the same rolling-history clear a modulation
        # change already triggers automatically (see update_symbols) - this
        # is the manual equivalent, for clearing the accumulated HISTORY_
        # BURSTS scatter on demand without waiting for that.
        ctk.CTkButton(header, text="Clear", width=70, height=28, command=self.reset).pack(side="right")

        self.figure = Figure(figsize=(2.6, 2.6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.12, right=0.96, top=0.96, bottom=0.1)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(4, 0))

        self.readout = ctk.CTkLabel(self, text="SNR: -    EVM: -", font=ctk.CTkFont(size=13))
        self.readout.pack(pady=(4, 10))

        self._draw_axes()

    def _draw_axes(self, limit=1.5):
        self.ax.clear()
        self.ax.axhline(0, color=AXIS_COLOR, linewidth=0.8, zorder=0)
        self.ax.axvline(0, color=AXIS_COLOR, linewidth=0.8, zorder=0)
        self.ax.set_xlabel('I')
        self.ax.set_ylabel('Q')
        self.ax.set_xlim(-limit, limit)
        self.ax.set_ylim(-limit, limit)
        self.ax.set_aspect('equal')

    def reset(self):
        self._history.clear()
        self._last_modulation = None
        self._draw_axes()
        self.canvas.draw_idle()
        self.readout.configure(text="SNR: -    EVM: -")

    def update_symbols(self, symbols, modulation, snr_db):
        if modulation != self._last_modulation:
            self._history.clear()
            self._last_modulation = modulation
        self._history.append(symbols)

        ideal = modem._CONSTELLATIONS.get(modulation, ())
        limit = max(abs(p) for p in ideal) * 1.6 if ideal else 1.5

        self._draw_axes(limit)
        for burst in self._history:
            self.ax.scatter(burst.real, burst.imag, s=10, alpha=0.45,
                             color=POINT_COLOR, zorder=2)
        if ideal:
            self.ax.scatter([p.real for p in ideal], [p.imag for p in ideal],
                             s=90, marker='x', color=IDEAL_COLOR, linewidths=2, zorder=3)
        self.canvas.draw_idle()

        evm_percent = ota_station._snr_db_to_evm_percent(snr_db)
        self.readout.configure(
            text=f"SNR: {snr_db:.1f} dB    EVM: {evm_percent:.1f} %    "
                 f"({modulation}, {len(symbols)} symbols)")

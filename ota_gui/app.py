import tkinter as tk

import customtkinter as ctk

from . import paths

paths.install()

import ota_station  # noqa: E402

from . import ui_config  # noqa: E402
from .controller import StationController  # noqa: E402
from .panels.chat_panel import ChatPanel  # noqa: E402
from .panels.constellation_panel import ConstellationPanel  # noqa: E402
from .panels.session_panel import SessionPanel  # noqa: E402
from .panels.settings_panel import SettingsPanel  # noqa: E402
from .panels.status_bar import StatusBar  # noqa: E402
from .panels.status_panel import StatusPanel  # noqa: E402

POLL_INTERVAL_MS = 80
SPEED_TEST_SIZES = {'200 B': 200, '1 KB': 1000, '5 KB': 5000, '20 KB': 20000}
DEFAULT_WINDOW_SIZE = (1300, 820)


class App(ctk.CTk):
    def __init__(self, sim_host, sim_port, local_port):
        super().__init__()
        self.title("OpenWave OTA Station")

        # Loaded once here, at startup, and applied below (window size
        # immediately; Station/Settings panel fields and pane split
        # positions once those widgets exist) - see ui_config.py and
        # _save_ui_config()/_reset_ui(). {} (first-ever launch, or after
        # File > Reset UI) falls through to this file's own hardcoded
        # defaults everywhere below, same as if this code didn't exist.
        self._ui_config = ui_config.load()
        saved_window = self._ui_config.get('window', {})
        self._center_window(
            saved_window.get('width', DEFAULT_WINDOW_SIZE[0]),
            saved_window.get('height', DEFAULT_WINDOW_SIZE[1]))

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Fixed for the life of the process (see main.py's argparse) - no
        # Simulator panel/Connect button anymore, so these never show up in
        # the GUI at all; _ensure_connected() reads them straight off self.
        self._sim_host = sim_host
        self._sim_port = sim_port
        self._local_port = local_port

        self.controller = StationController()
        self._build_menu()

        self.status_bar = StatusBar(self)
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # One shared grid for the top panel AND the body below, both using
        # the same two columns - packed (not just created) after status_bar
        # claims its bottom strip, so this frame's expand=True only grows
        # into what's left. Sharing one grid (rather than top/body each
        # defining their own columns independently) is what keeps the
        # Station panel's edges lined up with the chat/mode-column boundary
        # below it - two separately-configured grids drift apart the
        # moment their weights or padding aren't identical.
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        self.session_panel = SessionPanel(main, on_command=self._run_command)
        self.session_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.session_panel.import_state(self._ui_config.get('session', {}))

        self.settings_panel = SettingsPanel(main, on_command=self._run_command)
        self.settings_panel.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        self.settings_panel.import_state(self._ui_config.get('settings', {}))

        # Draggable-sash panes for the body row, so Messages/Status/
        # constellation can all be resized by hand - customtkinter has no
        # splitter widget of its own, but it's built on plain tkinter, and
        # tkinter.PanedWindow happily hosts CTkFrame children as panes. The
        # sash itself is necessarily plain-tkinter styled (no CTk splitter
        # exists to match exactly) - _sash_color() at least keeps its
        # background the same gray CTkFrame itself uses in the active
        # light/dark mode, so it doesn't stand out as a foreign widget.
        sash_style = dict(sashwidth=6, sashrelief="raised", bg=self._sash_color(), bd=0)

        self.body = tk.PanedWindow(main, orient="horizontal", **sash_style)
        self.body.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.message_pane = tk.PanedWindow(self.body, orient="vertical", **sash_style)

        self.chat_panel = ChatPanel(
            self.message_pane, on_send_text=self._send_text, on_command=self._run_command)
        self.status_panel = StatusPanel(self.message_pane)
        self.message_pane.add(self.chat_panel, minsize=150, stretch="always")
        self.message_pane.add(self.status_panel, minsize=100, stretch="always")

        self.constellation_panel = ConstellationPanel(self.body)
        self.body.add(self.message_pane, minsize=380, stretch="always", width=950)
        self.body.add(self.constellation_panel, minsize=250, stretch="always")

        # This file's own hardcoded default split, captured from the panes
        # as actually laid out above (rather than re-guessed as fractions
        # by hand) - what File > Reset UI puts the sashes back to.
        self._default_pane_fractions = self._current_pane_fractions()
        self._restore_pane_fractions(self._ui_config.get('panes', {}))

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(POLL_INTERVAL_MS, self._poll)

        # No Connect button in any panel - the simulator address is fixed
        # at launch (see main.py), so there's nothing left to wait on:
        # connect immediately with whatever's in the Station/Mode panels'
        # defaults. File > ota-sim-connect/ota-sim-disconnect (see _build_menu) is still
        # there for ending a session or reconnecting with changed settings
        # without relaunching the whole app.
        self._ensure_connected()

    def _sash_color(self):
        light, dark = ctk.ThemeManager.theme['CTkFrame']['fg_color']
        return dark if ctk.get_appearance_mode() == 'Dark' else light

    def _current_pane_fractions(self):
        """Sash positions as fractions of their pane's current size, not
        raw pixels - so a saved split survives a differently-sized window
        (or a different screen) at the next launch instead of landing at a
        stale/nonsensical pixel offset."""
        self.update_idletasks()
        body_w = self.body.winfo_width() or 1
        message_h = self.message_pane.winfo_height() or 1
        return {
            'body': self.body.sash_coord(0)[0] / body_w,
            'message': self.message_pane.sash_coord(0)[1] / message_h,
        }

    def _restore_pane_fractions(self, fractions):
        self.update_idletasks()
        body_frac = fractions.get('body')
        if body_frac is not None:
            self.body.sash_place(0, int(body_frac * self.body.winfo_width()), 0)
        message_frac = fractions.get('message')
        if message_frac is not None:
            self.message_pane.sash_place(0, 0, int(message_frac * self.message_pane.winfo_height()))

    def _center_window(self, width, height):
        # update_idletasks() first, then measure back the actual (CTk-
        # DPI-scaled) width/height rather than trusting the raw args -
        # tk::PlaceWindow's own centering logic disagreed with
        # winfo_screenwidth/height's coordinate space under CTk's scaling
        # and put the window off-screen, so this does the arithmetic
        # directly instead. The window manager may still nudge the
        # placement to avoid its own reserved screen space (a top panel,
        # say) - that's expected, not a bug.
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_menu(self):
        menubar = tk.Menu(self)
        self._file_menu = tk.Menu(menubar, tearoff=False)
        self._file_menu.add_command(label="ota-sim-connect", command=self._toggle_connection)
        self._file_menu.add_separator()
        self._file_menu.add_command(label="Reset UI", command=self._reset_ui)
        self._file_menu.add_separator()
        self._file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=self._file_menu)

        link_menu = tk.Menu(menubar, tearoff=False)
        link_menu.add_command(label="Ping", command=lambda: self._run_command('/ping'))
        link_menu.add_command(label="Ping Survey", command=lambda: self._run_command('/ping survey'))
        link_menu.add_command(label="Renegotiate", command=lambda: self._run_command('/renegotiate'))
        link_menu.add_separator()
        link_menu.add_command(label="Show Modes Table", command=lambda: self._run_command('/modes'))
        link_menu.add_separator()
        speed_test_menu = tk.Menu(link_menu, tearoff=False)
        for label, size_bytes in SPEED_TEST_SIZES.items():
            speed_test_menu.add_command(
                label=label, command=lambda size_bytes=size_bytes: self._run_speed_test(size_bytes))
        link_menu.add_cascade(label="Speed Test", menu=speed_test_menu)
        menubar.add_cascade(label="Link", menu=link_menu)

        self.configure(menu=menubar)

    # -- actions ------------------------------------------------------
    def _toggle_connection(self):
        """File > ota-sim-connect/ota-sim-disconnect."""
        if self.controller.connected:
            self.controller.disconnect()
        else:
            self._ensure_connected()

    def _ensure_connected(self):
        """Connects using whatever's currently in the Station/Settings
        panels plus the sim address fixed at launch - called once at
        startup, and also by Send/Ping/Set/etc. so those still work even on
        the rare chance startup's own connect attempt failed (see each
        panel's own docstring). Returns True if a session is (now) live,
        False if it couldn't connect (bad/missing settings, or the connect
        attempt itself failed) - callers should bail out without acting in
        that case."""
        if self.controller.connected:
            return True

        try:
            session_settings = self.session_panel.get_settings()
        except ValueError as exc:
            self.session_panel.show_error(str(exc))
            return False

        use_fec, fec_preset = self.settings_panel.get_initial_fec()
        settings = dict(session_settings, sim_host=self._sim_host, sim_port=self._sim_port,
                         local_port=self._local_port)
        settings.update(self.settings_panel.get_session_settings())
        settings.update(
            mode_id=self.settings_panel.get_initial_mode_id(),
            use_fec=use_fec,
            fec_preset=fec_preset,
            bandwidth=self.session_panel.get_initial_bandwidth(),
        )
        try:
            self.controller.connect(**settings)
        except Exception as exc:
            self.session_panel.show_error(f"Connect failed: {exc}")
            return False
        return True

    def _send_text(self, text):
        if not self._ensure_connected():
            return
        station = self.controller.station
        self.chat_panel.append(f"{station.station_id} -> {station.dst_id}: {text}", tag='sent')
        try:
            self.controller.send_text(text)
        except RuntimeError as exc:
            self.status_panel.append(f"[error] {exc}")

    def _run_command(self, line):
        # Pure reference info - openwave_link.WAVEFORM_MODES/openwave_fec.
        # PRESETS - needs no session, so it works before ever connecting.
        if line.strip() == '/modes':
            self.status_panel.append(ota_station._waveform_modes_table())
            return
        if not self._ensure_connected():
            return
        self.status_panel.append(f"> {line}")
        try:
            self.controller.run_command(line)
        except RuntimeError as exc:
            self.status_panel.append(f"[error] {exc}")

    def _run_speed_test(self, size_bytes):
        """Link > Speed Test - not an ota_station.py command, just a normal
        chat message of a chosen size, timed end-to-end (see controller.py's
        run_speed_test). Requires ACK: without it, send_text() returns as
        soon as the local transmit finishes, not when the peer actually has
        it - that would time local processing, not the link, so ACK is
        checked here rather than letting a misleading number come back."""
        if not self._ensure_connected():
            return
        if not self.controller.station.use_ack:
            self.status_panel.append(
                "[error] speed test needs ACK to time actual delivery - check it in the "
                "Settings panel, then File > ota-sim-disconnect and ota-sim-connect again")
            return
        self.status_panel.append(
            f"[speed test] sending {ota_station._human_size(size_bytes, short=True)}...")
        self.controller.run_speed_test('x' * size_bytes)

    def _reset_ui(self):
        """File > Reset UI - puts the running window back to the same
        hardcoded defaults a first-ever launch would use (window size,
        pane splits, Station/Settings panel fields) and deletes the saved
        state file so the NEXT launch starts fresh too - a plain relaunch
        alone wouldn't do that, since _on_close would just save the
        (unwanted) current state right back over it. Deliberately doesn't
        touch a live session (see SessionPanel/SettingsPanel's
        import_state() docstrings) - this resets the UI, not the radio
        link."""
        ui_config.reset()
        self.session_panel.reset_defaults()
        self.settings_panel.reset_defaults()
        self._center_window(*DEFAULT_WINDOW_SIZE)
        self._restore_pane_fractions(self._default_pane_fractions)
        self.status_panel.append("[ui] reset to defaults")

    def _save_ui_config(self):
        ui_config.save(dict(
            window=dict(width=self.winfo_width(), height=self.winfo_height()),
            panes=self._current_pane_fractions(),
            session=self.session_panel.export_state(),
            settings=self.settings_panel.export_state(),
        ))

    def _on_close(self):
        self._save_ui_config()
        self.controller.disconnect()
        self.destroy()

    def _is_received_message(self, text):
        """A received message is logged by Station._handle_message() itself
        as "<dst_id>: <text>" (see ota_station.py) - the same 'log' event
        pipeline carries every other diagnostic line too (negotiate/ping/rx/
        ack/etc.), so this is the one place that tells them apart, purely by
        matching that exact prefix against the live station's own dst_id.
        Used to SKIP this one line in the 'log' handler below - the
        separate 'message' event (Station's on_message hook) delivers the
        same received text without the prefix, which is what ChatPanel
        actually shows (reformatted as "source -> destination: message"),
        so leaving this copy in StatusPanel too would just be a duplicate.
        Not perfect in theory (a status line could coincidentally start the
        same way) but there's no real ambiguity in practice - callsigns
        don't collide with the rest of this file's fixed log wording."""
        station = self.controller.station
        return station is not None and text.startswith(f"{station.dst_id}: ")

    def _format_speed_result(self, data):
        if data['error']:
            return f"Speed test failed: {data['error']}"
        elapsed = data['elapsed']
        text_bps = (data['text_bytes'] * 8 / elapsed) if elapsed > 0 else 0
        # bps computed from text bytes only, matching ota_station.py's own
        # --verbose stats convention - on-air bytes are raw oversampled IQ
        # samples, not an information rate, so a "bps" from those wouldn't
        # mean anything comparable (it'd dwarf the mode's real symbol rate).
        # "sent", not "delivered" - send_text() may have given up on a
        # fragment after retries without raising (logged as "[ack] gave up"
        # in the chat log above, not treated as an error here), so this
        # number alone doesn't guarantee full delivery.
        return (f"{ota_station._human_size(data['text_bytes'], short=True)} sent in "
                f"{elapsed:.2f}s -> {text_bps:.0f} bps text-level "
                f"({ota_station._human_size(data['air_bytes'], short=True)} on-air) - "
                f"see status log above for delivery status")

    # -- draining controller events onto the Tk thread --------------------
    def _poll(self):
        for kind, data in self.controller.poll_events():
            if kind == 'log':
                # Skip the received-message-shaped line here - the
                # 'message' event below already puts it in ChatPanel,
                # reformatted (see _is_received_message's docstring).
                if not self._is_received_message(data['text']):
                    self.status_panel.append(data['text'])
            elif kind == 'message':
                station = self.controller.station
                self.chat_panel.append(
                    f"{station.dst_id} -> {station.station_id}: {data['text']}", tag='received')
            elif kind == 'symbols':
                self.constellation_panel.update_symbols(
                    data['symbols'], data['modulation'], data['snr_db'])
            elif kind == 'connected':
                # No chat_panel.clear() here - the connect that fires this
                # event is often triggered synchronously by something that
                # already appended to the log first (a sent-message echo,
                # a Speed Test's ACK-required warning, ...), and this event
                # is only processed on the NEXT poll tick, after that -
                # clearing here would silently wipe it out from under
                # whatever the user just did.
                self.status_panel.append(f"[connected] local port {data['local_port']}")
                self.session_panel.set_connected(True)
                self.settings_panel.set_connected(True)
                self._file_menu.entryconfigure(0, label="ota-sim-disconnect")
            elif kind == 'disconnected':
                self.status_panel.append(data['summary'])
                self.session_panel.set_connected(False)
                self.settings_panel.set_connected(False)
                self.constellation_panel.reset()
                self._file_menu.entryconfigure(0, label="ota-sim-connect")
            elif kind == 'speed_test_result':
                self.status_panel.append(self._format_speed_result(data))

        self.session_panel.refresh(self.controller.station)
        self.status_bar.refresh(self.controller.station)
        self.after(POLL_INTERVAL_MS, self._poll)

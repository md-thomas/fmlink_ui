import customtkinter as ctk

from . import paths

paths.install()

import ota_station  # noqa: E402

from .controller import StationController  # noqa: E402
from .panels.chat_panel import ChatPanel  # noqa: E402
from .panels.constellation_panel import ConstellationPanel  # noqa: E402
from .panels.link_actions_panel import LinkActionsPanel  # noqa: E402
from .panels.mode_panel import ModePanel  # noqa: E402
from .panels.session_panel import SessionPanel  # noqa: E402
from .panels.sim_panel import SimPanel  # noqa: E402
from .panels.status_bar import StatusBar  # noqa: E402

POLL_INTERVAL_MS = 80


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OpenWave OTA Station")
        self.geometry("1150x760")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.controller = StationController()

        self.status_bar = StatusBar(self)
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # One shared grid for the top panels AND the body below, both using
        # the same two columns - packed (not just created) after status_bar
        # claims its bottom strip, so this frame's expand=True only grows
        # into what's left. Sharing one grid (rather than top/body each
        # defining their own columns independently) is what keeps the
        # Simulator/Station panels' column boundary lined up with the chat/
        # mode-column boundary below them - two separately-configured grids
        # drift apart the moment their weights or padding aren't identical.
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(1, weight=1)

        self.sim_panel = SimPanel(main, on_toggle=self._toggle_connection)
        self.sim_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        self.session_panel = SessionPanel(main)
        self.session_panel.grid(row=0, column=1, sticky="nsew", pady=(0, 10))

        self.chat_panel = ChatPanel(main, on_send_text=self._send_text, on_command=self._run_command)
        self.chat_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self.mode_panel = ModePanel(right, on_command=self._run_command)
        self.mode_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.constellation_panel = ConstellationPanel(right)
        self.constellation_panel.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        self.link_actions_panel = LinkActionsPanel(
            right, on_command=self._run_command, on_speed_test=self._run_speed_test)
        self.link_actions_panel.grid(row=2, column=0, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(POLL_INTERVAL_MS, self._poll)

    # -- actions ------------------------------------------------------
    def _toggle_connection(self):
        """SimPanel's Connect/Disconnect button."""
        if self.controller.connected:
            self.controller.disconnect()
        else:
            self._ensure_connected()

    def _ensure_connected(self):
        """Connects using whatever's currently in the Station/Simulator/
        Mode panels - called explicitly by the Connect button, and also by
        Send/Ping/Set/etc. so those still work even if you skip that button
        (see each panel's own docstring). Returns True if a session is (now)
        live, False if it couldn't connect (bad/missing settings, or the
        connect attempt itself failed) - callers should bail out without
        acting in that case."""
        if self.controller.connected:
            return True

        try:
            session_settings = self.session_panel.get_settings()
        except ValueError as exc:
            self.session_panel.show_error(str(exc))
            return False
        try:
            sim_settings = self.sim_panel.get_settings()
        except ValueError as exc:
            self.sim_panel.show_error(str(exc))
            return False

        use_fec, fec_preset = self.mode_panel.get_initial_fec()
        settings = {**session_settings, **sim_settings}
        settings.update(
            mode_id=self.mode_panel.get_initial_mode_id(),
            use_fec=use_fec,
            fec_preset=fec_preset,
            bandwidth=self.mode_panel.get_initial_bandwidth(),
        )
        try:
            self.controller.connect(**settings)
        except Exception as exc:
            self.sim_panel.show_error(f"Connect failed: {exc}")
            return False
        return True

    def _send_text(self, text):
        if not self._ensure_connected():
            return
        try:
            self.controller.send_text(text)
        except RuntimeError as exc:
            self.chat_panel.append(f"[error] {exc}")

    def _run_command(self, line):
        # Pure reference info - openwave_link.WAVEFORM_MODES/openwave_fec.
        # PRESETS - needs no session, so it works before ever connecting.
        if line.strip() == '/modes':
            self.chat_panel.append(ota_station._waveform_modes_table())
            return
        if not self._ensure_connected():
            return
        self.chat_panel.append(f"> {line}")
        try:
            self.controller.run_command(line)
        except RuntimeError as exc:
            self.chat_panel.append(f"[error] {exc}")

    def _run_speed_test(self, size_bytes):
        """LinkActionsPanel's Speed Test - not an ota_station.py command,
        just a normal chat message of a chosen size, timed end-to-end (see
        controller.py's run_speed_test). Requires ACK: without it,
        send_text() returns as soon as the local transmit finishes, not
        when the peer actually has it - that would time local processing,
        not the link, so ACK is checked here rather than letting a
        misleading number come back."""
        if not self._ensure_connected():
            return
        if not self.controller.station.use_ack:
            self.chat_panel.append(
                "[speed test] needs ACK to time actual delivery - enable it in the "
                "Station panel, then reconnect")
            return
        self.link_actions_panel.set_speed_test_running(True)
        self.controller.run_speed_test('x' * size_bytes)

    def _on_close(self):
        self.controller.disconnect()
        self.destroy()

    def _log_tag(self, text):
        """A received message is logged by Station._handle_message() itself
        as "<dst_id>: <text>" (see ota_station.py) - the same 'log' event
        pipeline carries every other diagnostic line too (negotiate/ping/rx/
        ack/etc.), so this is the one place that tells them apart, purely by
        matching that exact prefix against the live station's own dst_id.
        Not perfect in theory (a status line could coincidentally start the
        same way) but there's no real ambiguity in practice - callsigns
        don't collide with the rest of this file's fixed log wording."""
        station = self.controller.station
        if station is not None and text.startswith(f"{station.dst_id}: "):
            return 'received'
        return 'status'

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
                f"see chat log above for delivery status")

    # -- draining controller events onto the Tk thread --------------------
    def _poll(self):
        for kind, data in self.controller.poll_events():
            if kind == 'log':
                self.chat_panel.append(data['text'], tag=self._log_tag(data['text']))
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
                self.chat_panel.append(f"[connected] local port {data['local_port']}")
                self.sim_panel.set_connected(True)
                self.session_panel.set_connected(True)
            elif kind == 'disconnected':
                self.chat_panel.append(data['summary'])
                self.sim_panel.set_connected(False)
                self.session_panel.set_connected(False)
                self.constellation_panel.reset()
            elif kind == 'speed_test_result':
                self.link_actions_panel.set_speed_test_running(False)
                self.link_actions_panel.show_speed_result(self._format_speed_result(data))
            # 'message' carries the same text Station's own on_log call
            # already renders as "<dst_id>: <text>" - no separate handling
            # needed here (see _log_tag()).

        self.mode_panel.refresh(self.controller.station)
        self.status_bar.refresh(self.controller.station)
        self.after(POLL_INTERVAL_MS, self._poll)

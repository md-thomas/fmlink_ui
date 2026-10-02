"""Bridges a live ota_station.Station (asyncio) to a synchronous, thread-safe
API a Tk GUI can call directly from its main thread.

Station and its coroutines (send_text, ping, ping_survey, negotiate,
_announce_mode, and _handle_command which dispatches all of those) all live
on a dedicated background asyncio event-loop thread. GUI calls hop onto that
thread via asyncio.run_coroutine_threadsafe(); Station's own callbacks
(on_message/on_log/on_symbols), which fire FROM that thread, are never
touched directly by the GUI - they just push (kind, data) tuples onto a
queue.Queue, which the GUI drains on its own thread (e.g. via Tk's
`after()`) at its own pace. This is the standard safe pattern for mixing
asyncio with Tkinter: no widget is ever touched from the asyncio thread.
"""
import asyncio
import queue
import threading
import time

from . import paths

paths.install()

import ota_station  # noqa: E402


class StationController:
    def __init__(self):
        self.events = queue.Queue()
        self.station = None
        self._loop = None
        self._thread = None

    @property
    def connected(self):
        return self.station is not None

    # -- event-loop lifecycle --------------------------------------------
    def _start_loop(self):
        if self._loop is not None:
            return
        ready = threading.Event()

        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        ready.wait()

    # -- connect / disconnect --------------------------------------------
    def connect(self, **station_kwargs):
        """station_kwargs: station_id, dst_id, sim_host, sim_port,
        mode_id, use_fec, fec_preset, use_ack, auto, bandwidth, verbose - the
        GUI-panel equivalents of ota_station.py's CLI flags. Blocks (briefly)
        until the station's TCP connection to the simulator is up and
        registered - mirrors ota_station.run()'s setup."""
        if self.station is not None:
            raise RuntimeError("already connected - disconnect() first")
        self._start_loop()
        fut = asyncio.run_coroutine_threadsafe(self._connect(**station_kwargs), self._loop)
        return fut.result(timeout=10)

    async def _connect(self, station_id, dst_id, sim_host, sim_port,
                        mode_id=0, use_fec=False, fec_preset=None, use_ack=False,
                        auto=False, bandwidth='wide', verbose=False):
        # Same use_fec-implied-by-auto rule as ota_station.run().
        station = ota_station.Station(
            station_id=station_id, dst_id=dst_id, mode_id=mode_id,
            use_fec=use_fec or auto, fec_preset=fec_preset, use_ack=use_ack,
            auto=auto, bandwidth=bandwidth, verbose=verbose,
            on_message=lambda text: self._emit('message', text=text),
            on_log=lambda msg: self._emit('log', text=msg),
            on_symbols=lambda symbols, modulation, snr_db: self._emit(
                'symbols', symbols=symbols, modulation=modulation, snr_db=snr_db),
        )
        await station.connect(sim_host, sim_port)
        self.station = station
        self._emit('connected', sim_address=f"{sim_host}:{sim_port}")
        return station

    def disconnect(self):
        if self.station is None:
            return
        fut = asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
        fut.result(timeout=5)

    async def _disconnect(self):
        summary = self.station.stats_summary()
        self.station.close()
        self.station = None
        self._emit('disconnected', summary=summary)

    # -- actions (fire-and-forget from the GUI's point of view; results/
    # errors surface as queued events, not return values) -----------------
    def send_text(self, text):
        self._call(self.station.send_text(text))

    def run_command(self, line):
        """line: a full '/'-prefixed command string, e.g. '/mode 3' or
        '/ping survey' - reused verbatim through ota_station._handle_command,
        so every command (bandwidth-ceiling checks, FEC validation, ping/
        negotiate retries, ...) behaves identically to the CLI. A '/quit' or
        '/exit' line (the only case _handle_command returns False for)
        triggers the same disconnect() the GUI's own Disconnect button uses."""
        self._call(self._run_command(line))

    async def _run_command(self, line):
        keep_going = await ota_station._handle_command(self.station, line)
        if not keep_going:
            await self._disconnect()

    def run_speed_test(self, payload):
        """payload: a text string of the size to test with - sent exactly
        like a normal chat message (same fragmentation/FEC/current mode),
        just timed end-to-end. Requires --ack: without it, send_text()
        returns as soon as the local transmit finishes, not when the peer
        actually has it, which would time the wrong thing entirely - see
        app.py's caller, which checks use_ack before calling this."""
        self._call(self._run_speed_test(payload))

    async def _run_speed_test(self, payload):
        # Caught (not left to _call's generic error-log path) so the result
        # event always fires either way - that's what re-enables the Speed
        # Test button in the GUI (see app.py); a raised exception here would
        # otherwise leave it stuck showing "Running...".
        text_bytes = len(payload.encode('utf-8'))
        air_before = self.station.stats['sent_air_bytes']
        started = time.monotonic()
        error = None
        try:
            await self.station.send_text(payload)
        except Exception as exc:
            error = repr(exc)
        elapsed = time.monotonic() - started
        air_bytes = self.station.stats['sent_air_bytes'] - air_before
        self._emit('speed_test_result', text_bytes=text_bytes, air_bytes=air_bytes,
                    elapsed=elapsed, error=error)

    def _call(self, coro):
        if self.station is None or self._loop is None:
            raise RuntimeError("not connected")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        fut.add_done_callback(self._report_future_error)

    def _report_future_error(self, fut):
        exc = fut.exception()
        if exc is not None:
            self._emit('log', text=f"[error] {exc!r}")

    # -- event plumbing (asyncio thread -> GUI thread) ---------------------
    def _emit(self, kind, **data):
        self.events.put((kind, data))

    def poll_events(self):
        """Drains every queued event without blocking - call from the GUI's
        own periodic (e.g. Tk after()) tick. Returns a list of (kind, data)
        tuples in arrival order."""
        drained = []
        while True:
            try:
                drained.append(self.events.get_nowait())
            except queue.Empty:
                break
        return drained

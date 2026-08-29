"""OpenWave OTA Station GUI entry point.

    python3 -m ota_gui.main

All connection settings (station ID, peer, simulator address, mode, FEC,
ACK, auto-negotiate, bandwidth, verbose) are set from the Connect bar at
the top of the window - see ota_gui/panels/connect_panel.py - rather than
as command-line flags, since they're meant to be changed between sessions
without restarting the app.
"""
from .app import App


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()

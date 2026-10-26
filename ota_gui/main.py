"""FMlink OTA Station GUI entry point.

    python3 -m ota_gui.main --sim-host 127.0.0.1 --sim-port 9500

The simulator address (--sim-host/--sim-port) is fixed for
the life of the process, set here on the command line - there's no
Simulator panel in the window at all; the app connects immediately on
launch using this address plus whatever's in the Station panel's defaults
(Station ID, peer callsign, Bandwidth) and the Settings panel's defaults
(ACK/Auto negotiate/Verbose, Mode/FEC). Ending a session (or changing
anything that only applies at connect time) doesn't need a relaunch -
File > ota-sim-disconnect, then ota-sim-connect again, does that from
within the running window.
"""
import argparse

from .app import App


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sim-host', default='127.0.0.1',
                         help='ota_sim simulator address (default: 127.0.0.1)')
    parser.add_argument('--sim-port', type=int, default=9500,
                         help='ota_sim simulator port (default: 9500)')
    args = parser.parse_args()

    app = App(sim_host=args.sim_host, sim_port=args.sim_port)
    app.mainloop()


if __name__ == '__main__':
    main()

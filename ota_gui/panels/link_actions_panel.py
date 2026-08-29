"""Ping / Ping Survey / Renegotiate / Show Modes Table / Speed Test - the
diagnostic and reference commands, split out from ModePanel so mode/FEC/
bandwidth selection and these one-shot actions aren't crowded into one
panel.

Ping/Ping Survey/Renegotiate are clickable from the moment the window
opens, connected or not - App's run_command() (see app.py's
_ensure_connected) auto-connects first, using whatever's currently in the
Simulator/Station/Mode panels, exactly like sending a chat message does.
Show Modes Table needs no session at all (it's static reference info -
openwave_link.WAVEFORM_MODES/openwave_fec.PRESETS), so it's never gated on
anything.

Speed Test has no ota_station.py command of its own - it's just a normal
chat message of a chosen size, sent through the live session and timed
end-to-end (see app.py's _run_speed_test/controller.py's run_speed_test).
It needs ACK on to mean anything (otherwise "sent" and "delivered" aren't
distinguishable), so App checks that first rather than this panel - keeps
the same "session-state gating lives in App" pattern as everything else
here."""
import customtkinter as ctk

SPEED_TEST_SIZES = {'200 B': 200, '1 KB': 1000, '5 KB': 5000, '20 KB': 20000}


class LinkActionsPanel(ctk.CTkFrame):
    def __init__(self, master, on_command, on_speed_test):
        super().__init__(master)
        self._on_command = on_command
        self._on_speed_test = on_speed_test

        ctk.CTkLabel(self, text="Link", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=8, pady=4)
        self.ping_button = ctk.CTkButton(
            button_row, text="Ping", command=lambda: self._on_command('/ping'))
        self.ping_button.pack(side="left", expand=True, fill="x", padx=2)
        self.ping_survey_button = ctk.CTkButton(
            button_row, text="Ping Survey", command=lambda: self._on_command('/ping survey'))
        self.ping_survey_button.pack(side="left", expand=True, fill="x", padx=2)
        self.renegotiate_button = ctk.CTkButton(
            button_row, text="Renegotiate", command=lambda: self._on_command('/renegotiate'))
        self.renegotiate_button.pack(side="left", expand=True, fill="x", padx=2)

        ctk.CTkButton(self, text="Show Modes Table",
                      command=lambda: self._on_command('/modes')).pack(
            fill="x", padx=8, pady=4)

        speed_row = ctk.CTkFrame(self, fg_color="transparent")
        speed_row.pack(fill="x", padx=8, pady=(4, 2))
        self.speed_size_menu = ctk.CTkOptionMenu(speed_row, values=list(SPEED_TEST_SIZES), width=90)
        self.speed_size_menu.set('1 KB')
        self.speed_size_menu.pack(side="left", padx=(0, 6))
        self.speed_test_button = ctk.CTkButton(
            speed_row, text="Run Speed Test", command=self._run_speed_test)
        self.speed_test_button.pack(side="left", fill="x", expand=True)

        self.speed_result_label = ctk.CTkLabel(
            self, text="", anchor="w", font=ctk.CTkFont(size=11), text_color="gray60",
            wraplength=280, justify="left")
        self.speed_result_label.pack(fill="x", padx=10, pady=(0, 10))

    def _run_speed_test(self):
        size = SPEED_TEST_SIZES[self.speed_size_menu.get()]
        self._on_speed_test(size)

    def set_speed_test_running(self, running):
        self.speed_test_button.configure(
            state="disabled" if running else "normal",
            text="Running..." if running else "Run Speed Test")
        if running:
            self.speed_result_label.configure(text="")

    def show_speed_result(self, text):
        self.speed_result_label.configure(text=text)

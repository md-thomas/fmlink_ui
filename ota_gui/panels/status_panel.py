"""Status/info/error feed - every diagnostic line Station's on_log hook
produces (negotiate/ping/rx/ack output, connect/disconnect banners, command
echoes, errors, /modes reference text, Speed Test progress/results), split
out from ChatPanel so the actual conversation isn't lost in the diagnostic
noise around it (see chat_panel.py, which now carries only sent/received
messages, matching ota_station.py's CLI - all of this would otherwise print
to stderr - just routed here through Station's on_log hook instead)."""
import customtkinter as ctk

STATUS_COLOR = 'gray55'
ERROR_COLOR = '#d0453b'


class StatusPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(header, text="Status", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(side="left", padx=2)
        ctk.CTkButton(header, text="Clear", width=60, command=self.clear).pack(side="right")

        self.log = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # Same tag_config(font=...) restriction as ChatPanel - color-only.
        self.log.tag_config('status', foreground=STATUS_COLOR)
        self.log.tag_config('error', foreground=ERROR_COLOR)

    def append(self, line):
        tag = 'error' if line.startswith('[error]') else 'status'
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tags=tag)
        self.log.configure(state="disabled")
        self.log.see("end")

    def clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

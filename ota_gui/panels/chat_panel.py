"""Scrolling message view + entry box - the actual conversation only (sent/
received chat text, each shown as "source -> destination: message"). Every
diagnostic line - negotiate/ping/rx/ack output, connect/disconnect banners,
command echoes, errors, /modes reference text, Speed Test progress/results
- lives in the separate StatusPanel instead (status_panel.py), so it
doesn't bury the conversation the way ota_station.py's CLI interleaves
everything on one terminal.

The "source -> destination: message" formatting itself happens in App
(app.py's _send_text/_poll), not here - this panel has no idea what this
station's own station_id/dst_id are, only App/the live Station object
does."""
import customtkinter as ctk

SENT_COLOR = '#3b8ed0'
RECEIVED_COLOR = '#2fa84f'


class ChatPanel(ctk.CTkFrame):
    def __init__(self, master, on_send_text, on_command):
        super().__init__(master)
        self._on_send_text = on_send_text
        self._on_command = on_command

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(header, text="Messages", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(side="left", padx=2)
        ctk.CTkButton(header, text="Clear", width=70, height=28, command=self.clear).pack(side="right")

        self.log = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        # CTkTextbox refuses per-tag fonts outright ("incompatible with
        # scaling" - see its tag_config()), so color is the whole
        # distinction here rather than also varying weight/size.
        self.log.tag_config('sent', foreground=SENT_COLOR)
        self.log.tag_config('received', foreground=RECEIVED_COLOR)

        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(fill="x", padx=8, pady=(0, 8))
        self.entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="Type a message, or a /command (see /help)")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry.bind("<Return>", lambda _event: self._send())
        ctk.CTkButton(entry_row, text="Send", width=70, height=28, command=self._send).pack(side="left")

    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        if text.startswith('/'):
            self._on_command(text)
        else:
            # No local echo here - App's _send_text appends the "source ->
            # destination: message" line itself once it knows a session is
            # actually live (it may still need to auto-connect first).
            self._on_send_text(text)

    def append(self, line, tag='received'):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tags=tag)
        self.log.configure(state="disabled")
        self.log.see("end")

    def clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

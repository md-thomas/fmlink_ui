"""Scrolling message/log view + entry box - the messaging half of the GUI.
Received messages, sent-message echoes, and every diagnostic line Station
would otherwise print to stderr (negotiate/ping/rx-error output, all routed
through Station's on_log hook) share one chronological feed, matching how
ota_station.py's CLI already interleaves them on one terminal - but styled
differently (see the 'sent'/'received'/'status' tags below) so the actual
conversation stands out from the diagnostic noise around it."""
import customtkinter as ctk

SENT_COLOR = '#3b8ed0'
RECEIVED_COLOR = '#2fa84f'
STATUS_COLOR = 'gray55'


class ChatPanel(ctk.CTkFrame):
    def __init__(self, master, on_send_text, on_command):
        super().__init__(master)
        self._on_send_text = on_send_text
        self._on_command = on_command

        self.log = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # CTkTextbox refuses per-tag fonts outright ("incompatible with
        # scaling" - see its tag_config()), so color is the whole
        # distinction here rather than also varying weight/size.
        self.log.tag_config('sent', foreground=SENT_COLOR)
        self.log.tag_config('received', foreground=RECEIVED_COLOR)
        self.log.tag_config('status', foreground=STATUS_COLOR)

        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(fill="x", padx=8, pady=(0, 8))
        self.entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="Type a message and Send to connect, or a /command (see /help)")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry.bind("<Return>", lambda _event: self._send())
        ctk.CTkButton(entry_row, text="Send", width=70, command=self._send).pack(side="left")
        ctk.CTkButton(entry_row, text="Clear", width=60, command=self.clear).pack(side="left", padx=(6, 0))

    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        if text.startswith('/'):
            self._on_command(text)
        else:
            self.append(f"> {text}", tag='sent')
            self._on_send_text(text)

    def append(self, line, tag='status'):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tags=tag)
        self.log.configure(state="disabled")
        self.log.see("end")

    def clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

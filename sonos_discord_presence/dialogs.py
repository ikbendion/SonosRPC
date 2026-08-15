"""Small tkinter dialogs used from the tray menu.

pystray runs its own loop and has no widgets of its own, so anything that
needs user text input or a pick-a-speaker list borrows a hidden Tk root.
Each dialog is created and destroyed per-call so it never fights with the
tray icon's event loop.
"""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import List, Optional

from .sonos_client import SpeakerInfo


def _hidden_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def ask_discord_client_id(initial: str = "") -> Optional[str]:
    root = _hidden_root()
    try:
        value = simpledialog.askstring(
            "Sonos Discord Presence",
            "Discord Application Client ID:\n"
            "(Create one at https://discord.com/developers/applications)",
            initialvalue=initial,
            parent=root,
        )
    finally:
        root.destroy()
    return value.strip() if value else None


def ask_poll_interval(initial: float = 5.0) -> Optional[float]:
    root = _hidden_root()
    try:
        value = simpledialog.askfloat(
            "Sonos Discord Presence",
            "Poll interval (seconds):",
            initialvalue=initial,
            minvalue=2,
            maxvalue=60,
            parent=root,
        )
    finally:
        root.destroy()
    return value


def ask_spotify_credentials(initial_id: str = "", initial_secret: str = ""):
    """Two-step prompt for optional Spotify Developer credentials, used to
    look up real album art. Returns (client_id, secret) -- either may be
    an empty string if the user wants to clear/disable the feature -- or
    None if the user cancelled (leave existing config untouched)."""
    root = _hidden_root()
    try:
        client_id = simpledialog.askstring(
            "Sonos Discord Presence",
            "Spotify Client ID (optional, for real album art):\n"
            "Leave blank to disable. Get one at https://developer.spotify.com/dashboard",
            initialvalue=initial_id,
            parent=root,
        )
    finally:
        root.destroy()
    if client_id is None:
        return None

    root = _hidden_root()
    try:
        client_secret = simpledialog.askstring(
            "Sonos Discord Presence",
            "Spotify Client Secret:",
            initialvalue=initial_secret,
            parent=root,
        )
    finally:
        root.destroy()
    if client_secret is None:
        return None

    return client_id.strip(), client_secret.strip()


def show_message(title: str, message: str) -> None:
    root = _hidden_root()
    try:
        messagebox.showinfo(title, message, parent=root)
    finally:
        root.destroy()


def select_speaker(speakers: List[SpeakerInfo]) -> Optional[SpeakerInfo]:
    """Modal list picker. Returns the chosen SpeakerInfo, or None if
    cancelled / nothing was found."""
    if not speakers:
        show_message("Sonos Discord Presence", "No Sonos speakers were found on the network.")
        return None

    root = _hidden_root()
    root.deiconify()
    root.title("Select Sonos Speaker")
    root.geometry("320x260")
    root.resizable(False, False)

    result = {"speaker": None}

    tk.Label(root, text="Choose the speaker to track:").pack(pady=(10, 4))

    listbox = tk.Listbox(root, height=8)
    for speaker in speakers:
        listbox.insert(tk.END, speaker.name)
    listbox.selection_set(0)
    listbox.pack(fill=tk.BOTH, expand=True, padx=10)

    def on_ok():
        selection = listbox.curselection()
        if selection:
            result["speaker"] = speakers[selection[0]]
        root.destroy()

    def on_cancel():
        root.destroy()

    button_frame = ttk.Frame(root)
    button_frame.pack(pady=10)
    ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    return result["speaker"]

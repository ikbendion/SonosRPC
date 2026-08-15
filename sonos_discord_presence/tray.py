"""System tray icon and menu, built with pystray.

The tray only renders state and forwards clicks; all the actual
speaker/Discord/config logic lives in `app.py` and is wired in through the
`callbacks` dict passed to `TrayApp`.
"""
import logging
import threading
from enum import Enum, auto

import pystray
from PIL import Image

from .resources import asset_path

log = logging.getLogger(__name__)


class TrayState(Enum):
    OK = auto()
    IDLE = auto()
    ERROR = auto()


_ICON_FILES = {
    TrayState.OK: "icon.png",
    TrayState.IDLE: "icon.png",
    TrayState.ERROR: "icon_error.png",
}

_ICON_CACHE: dict = {}


def _load_icon(state: TrayState) -> Image.Image:
    filename = _ICON_FILES[state]
    if filename not in _ICON_CACHE:
        _ICON_CACHE[filename] = Image.open(asset_path(filename))
    return _ICON_CACHE[filename]


class TrayApp:
    def __init__(self, callbacks: dict, start_with_windows_enabled: bool):
        """`callbacks` expects keys: select_speaker, open_settings, quit,
        toggle_start_with_windows -- each a zero/one-arg callable."""
        self._callbacks = callbacks
        self._status_text = "Starting..."
        self._start_with_windows = start_with_windows_enabled
        self._lock = threading.Lock()

        self.icon = pystray.Icon(
            "SonosDiscordPresence",
            icon=_load_icon(TrayState.IDLE),
            title="Sonos Discord Presence — Starting…",
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda item: self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Select Sonos Speaker", self._on_select_speaker),
            pystray.MenuItem("Settings...", self._on_settings),
            pystray.MenuItem(
                "Start with Windows",
                self._on_toggle_start_with_windows,
                checked=lambda item: self._start_with_windows,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _on_select_speaker(self, icon, item):
        self._callbacks["select_speaker"]()

    def _on_settings(self, icon, item):
        self._callbacks["open_settings"]()

    def _on_toggle_start_with_windows(self, icon, item):
        with self._lock:
            self._start_with_windows = not self._start_with_windows
        self._callbacks["toggle_start_with_windows"](self._start_with_windows)
        self.icon.update_menu()

    def _on_quit(self, icon, item):
        self._callbacks["quit"]()
        icon.stop()

    def set_status(self, text: str, state: TrayState = TrayState.OK) -> None:
        with self._lock:
            self._status_text = text
        self.icon.title = f"Sonos Discord Presence — {text}"[:127]
        self.icon.icon = _load_icon(state)
        self.icon.update_menu()

    def set_start_with_windows(self, enabled: bool) -> None:
        with self._lock:
            self._start_with_windows = enabled
        self.icon.update_menu()

    def run(self) -> None:
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()

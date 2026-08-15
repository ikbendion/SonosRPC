"""Orchestrates config, Sonos polling, Discord RPC and the tray icon.

Logging is set up by main.py before this module is even imported (see its
module docstring for why), so this module just gets a logger and assumes
a handler is already attached to the root logger.
"""
import logging
import threading
import time

from . import DISPLAY_NAME
from .config import load_config, save_config
from .dialogs import (
    ask_discord_client_id,
    ask_poll_interval,
    ask_spotify_credentials,
    select_speaker,
    show_message,
)
from .discord_rpc import DiscordRPCManager
from .metadata import normalize
from .sonos_client import SpeakerInfo, discover_speakers
from .sonos_client import SonosPoller
from .spotify_art import SpotifyArtResolver
from .startup import is_enabled as startup_is_enabled
from .startup import set_enabled as startup_set_enabled
from .tray import TrayApp, TrayState

log = logging.getLogger(__name__)

DISCORD_RETRY_SECONDS = 15
PLAYING_STATES = {"PLAYING"}


class App:
    def __init__(self):
        self.cfg = load_config()
        self.discord: DiscordRPCManager | None = None
        self.poller: SonosPoller | None = None
        self.tray: TrayApp | None = None
        self.spotify = SpotifyArtResolver(
            self.cfg.get("spotify_client_id", ""), self.cfg.get("spotify_client_secret", "")
        )

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._idle_since = None

    # ---------------------------------------------------------------- setup
    def _ensure_client_id(self) -> None:
        while not self.cfg.get("discord_client_id"):
            client_id = ask_discord_client_id()
            if not client_id:
                show_message(
                    DISPLAY_NAME,
                    "A Discord Application Client ID is required. "
                    "See the README for how to create one.",
                )
                continue
            self.cfg["discord_client_id"] = client_id
            save_config(self.cfg)

    def _ensure_speaker(self) -> None:
        while not self.cfg.get("speaker_uid"):
            speakers = discover_speakers()
            chosen = select_speaker(speakers)
            if chosen is None:
                # select_speaker() already showed a "no speakers found" message
                # when the list was empty; either way, let the user retry.
                continue
            self.cfg["speaker_uid"] = chosen.uid
            self.cfg["speaker_name"] = chosen.name
            self.cfg["speaker_ip"] = chosen.ip_address
            save_config(self.cfg)

    def _ensure_configured(self) -> None:
        self._ensure_client_id()
        self._ensure_speaker()

    # ------------------------------------------------------------ callbacks
    def _current_speaker(self) -> SpeakerInfo:
        return SpeakerInfo(
            uid=self.cfg["speaker_uid"],
            name=self.cfg["speaker_name"],
            ip_address=self.cfg.get("speaker_ip", ""),
        )

    def _restart_poller(self) -> None:
        if self.poller:
            self.poller.stop()
        self.poller = SonosPoller(
            speaker=self._current_speaker(),
            on_update=self._on_track_update,
            on_error=self._on_poll_error,
            poll_interval=float(self.cfg.get("poll_interval", 5)),
        )
        self.poller.start()

    def _on_select_speaker(self) -> None:
        speakers = discover_speakers()
        chosen = select_speaker(speakers)
        if chosen is None:
            return
        with self._lock:
            self.cfg["speaker_uid"] = chosen.uid
            self.cfg["speaker_name"] = chosen.name
            self.cfg["speaker_ip"] = chosen.ip_address
            save_config(self.cfg)
            self._idle_since = None
        self._restart_poller()
        if self.tray:
            self.tray.set_status(f"Tracking {chosen.name}", TrayState.IDLE)

    def _on_open_settings(self) -> None:
        client_id = ask_discord_client_id(self.cfg.get("discord_client_id", ""))
        if client_id:
            changed = client_id != self.cfg.get("discord_client_id")
            self.cfg["discord_client_id"] = client_id
            if changed and self.discord:
                self.discord.close()
                self.discord = DiscordRPCManager(client_id)

        interval = ask_poll_interval(self.cfg.get("poll_interval", 5))
        if interval:
            self.cfg["poll_interval"] = interval
            if self.poller:
                self.poller.poll_interval = interval

        spotify_creds = ask_spotify_credentials(
            self.cfg.get("spotify_client_id", ""), self.cfg.get("spotify_client_secret", "")
        )
        if spotify_creds is not None:
            spotify_client_id, spotify_client_secret = spotify_creds
            self.cfg["spotify_client_id"] = spotify_client_id
            self.cfg["spotify_client_secret"] = spotify_client_secret
            self.spotify = SpotifyArtResolver(spotify_client_id, spotify_client_secret)

        save_config(self.cfg)

    def _on_toggle_start_with_windows(self, enabled: bool) -> None:
        if startup_set_enabled(enabled):
            self.cfg["start_with_windows"] = enabled
            save_config(self.cfg)
        elif self.tray:
            self.tray.set_start_with_windows(not enabled)

    def _on_quit(self) -> None:
        self._stop_event.set()
        if self.poller:
            self.poller.stop()
        if self.discord:
            self.discord.clear()
            self.discord.close()

    # --------------------------------------------------------- poll events
    def _on_track_update(self, track_info: dict, transport_state: str) -> None:
        track = normalize(track_info)
        with self._lock:
            if transport_state in PLAYING_STATES:
                self._idle_since = None

                if track.is_spotify and self.spotify.configured:
                    spotify_art = self.spotify.lookup_album_art(track.raw_title, track.raw_artist)
                    if spotify_art:
                        track.album_art_url = spotify_art

                if self.discord and not self.discord.connected:
                    self.discord.connect()

                if self.discord and self.discord.connected:
                    self.discord.update(track)
                    if self.tray:
                        self.tray.set_status(f"Playing: {track.details}", TrayState.OK)
                elif self.tray:
                    self.tray.set_status(
                        f"Playing: {track.details} (Discord not connected)", TrayState.ERROR
                    )
            else:
                if self._idle_since is None:
                    self._idle_since = time.time()

                idle_elapsed = time.time() - self._idle_since
                grace = float(self.cfg.get("idle_grace_seconds", 12))
                if idle_elapsed >= grace:
                    if self.discord and self.discord.connected:
                        self.discord.clear()
                    if self.tray:
                        self.tray.set_status("Idle", TrayState.IDLE)
                elif self.tray:
                    self.tray.set_status(f"Paused: {track.details}", TrayState.IDLE)

    def _on_poll_error(self, exc: Exception) -> None:
        if self.tray:
            self.tray.set_status(
                f"Sonos speaker unreachable — retrying ({self.cfg.get('speaker_name', '?')})",
                TrayState.ERROR,
            )

    def _discord_supervisor(self) -> None:
        while not self._stop_event.is_set():
            if self.discord and not self.discord.connected:
                self.discord.connect()
            self._stop_event.wait(DISCORD_RETRY_SECONDS)

    # -------------------------------------------------------------- run
    def run(self) -> None:
        log.info("Starting %s", DISPLAY_NAME)

        self._ensure_configured()

        self.discord = DiscordRPCManager(self.cfg["discord_client_id"])
        self.discord.connect()

        self.tray = TrayApp(
            callbacks={
                "select_speaker": self._on_select_speaker,
                "open_settings": self._on_open_settings,
                "toggle_start_with_windows": self._on_toggle_start_with_windows,
                "quit": self._on_quit,
            },
            start_with_windows_enabled=startup_is_enabled(),
        )
        self.tray.set_status(f"Tracking {self.cfg.get('speaker_name', '?')}", TrayState.IDLE)

        self._restart_poller()

        threading.Thread(target=self._discord_supervisor, name="DiscordSupervisor", daemon=True).start()

        try:
            self.tray.run()
        finally:
            self._on_quit()

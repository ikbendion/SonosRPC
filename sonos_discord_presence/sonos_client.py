"""Sonos discovery and polling.

Only one speaker is actively tracked today, but discovery returns a list
of `SpeakerInfo` and `SonosPoller` is keyed off a single entry from that
list rather than a hardcoded IP, so tracking several speakers later just
means running one `SonosPoller` per `SpeakerInfo` instead of restructuring
this module.
"""
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

import soco
from soco import SoCo
from soco.exceptions import SoCoException

log = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 8


@dataclass
class SpeakerInfo:
    uid: str
    name: str
    ip_address: str


def discover_speakers(timeout: int = DISCOVERY_TIMEOUT) -> List[SpeakerInfo]:
    """Discover Sonos speakers/groups on the LAN.

    Returns one entry per zone (a stereo pair or group is represented by
    its coordinator), which is what a user picks between in the UI.
    """
    try:
        devices = soco.discover(timeout=timeout)
    except Exception:
        log.exception("Sonos discovery failed")
        devices = None

    if not devices:
        return []

    speakers = []
    for device in devices:
        try:
            speakers.append(
                SpeakerInfo(uid=device.uid, name=device.player_name, ip_address=device.ip_address)
            )
        except SoCoException:
            log.warning("Skipping unreachable Sonos device during discovery", exc_info=True)
    speakers.sort(key=lambda s: s.name.lower())
    return speakers


def connect_to_speaker(info: SpeakerInfo) -> Optional[SoCo]:
    """Reconnect directly by last-known IP, falling back to full discovery
    if the speaker's address changed (e.g. DHCP lease renewal)."""
    if info.ip_address:
        try:
            device = SoCo(info.ip_address)
            if device.uid == info.uid:
                return device
        except SoCoException:
            pass

    for speaker in discover_speakers():
        if speaker.uid == info.uid:
            try:
                return SoCo(speaker.ip_address)
            except SoCoException:
                return None
    return None


TrackCallback = Callable[[dict, str], None]
ErrorCallback = Callable[[Exception], None]


class SonosPoller:
    """Background poller for a single Sonos speaker.

    Calls `on_update(track_info, transport_state)` on every successful poll
    and `on_error(exc)` when the speaker can't be reached, so callers can
    surface a disconnected state without the poll loop dying.
    """

    def __init__(
        self,
        speaker: SpeakerInfo,
        on_update: TrackCallback,
        on_error: ErrorCallback,
        poll_interval: float = 5.0,
    ):
        self.speaker = speaker
        self._on_update = on_update
        self._on_error = on_error
        self.poll_interval = poll_interval
        self._device: Optional[SoCo] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="SonosPoller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _ensure_connected(self) -> bool:
        if self._device is not None:
            return True
        self._device = connect_to_speaker(self.speaker)
        return self._device is not None

    def _run(self) -> None:
        backoff = self.poll_interval
        while not self._stop_event.is_set():
            try:
                if not self._ensure_connected():
                    raise SoCoException(f"Speaker '{self.speaker.name}' not reachable")

                track_info = self._device.get_current_track_info()
                transport_state = self._device.get_current_transport_info()["current_transport_state"]
                self._on_update(track_info, transport_state)
                backoff = self.poll_interval
            except Exception as exc:  # noqa: BLE001 - surface everything to caller
                log.warning("Sonos poll failed: %s", exc)
                self._device = None
                self._on_error(exc)
                backoff = min(backoff * 2, 60)

            self._stop_event.wait(backoff if self._device is None else self.poll_interval)

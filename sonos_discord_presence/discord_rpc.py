"""Discord Rich Presence handling via pypresence's local IPC connection.

Discord's RPC client only accepts `large_image` as either a key from the
application's uploaded art assets or a URL Discord's client can fetch
itself -- it can't reach a Sonos speaker's LAN-only art server. We detect
that case and fall back to a pre-uploaded generic asset key.
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

from pypresence import Presence
from pypresence.exceptions import DiscordNotFound, PipeClosed, InvalidID

from .metadata import NormalizedTrack

log = logging.getLogger(__name__)

FALLBACK_IMAGE_KEY = "logo"


def _is_publicly_reachable_url(url: str) -> bool:
    """Best-effort check that `url` isn't pointing at a LAN-only host
    (e.g. a Sonos speaker's own http server serving cached art)."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        addr = ipaddress.ip_address(socket.gethostbyname(host))
    except (socket.gaierror, ValueError):
        # Not a raw IP and couldn't resolve -- treat unresolvable hosts as
        # unreachable rather than risk sending a broken URL to Discord.
        return False
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        return False
    return True


class DiscordRPCManager:
    def __init__(self, client_id: str, fallback_image_key: str = FALLBACK_IMAGE_KEY):
        self.client_id = client_id
        self.fallback_image_key = fallback_image_key
        self._rpc: Presence | None = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        if self._connected:
            return True
        try:
            self._rpc = Presence(self.client_id)
            self._rpc.connect()
            self._connected = True
            log.info("Connected to Discord IPC")
            return True
        except (DiscordNotFound, InvalidID, FileNotFoundError, ConnectionRefusedError) as exc:
            log.info("Discord not available yet: %s", exc)
            self._connected = False
            self._rpc = None
            return False
        except Exception:
            log.exception("Unexpected error connecting to Discord")
            self._connected = False
            self._rpc = None
            return False

    def update(self, track: NormalizedTrack, start_timestamp: int) -> bool:
        if not self._connected:
            return False

        image_key = (
            track.album_art_url
            if _is_publicly_reachable_url(track.album_art_url)
            else self.fallback_image_key
        )

        try:
            self._rpc.update(
                details=track.details,
                state=track.state,
                large_image=image_key,
                large_text="Sonos Discord Presence",
                start=start_timestamp,
            )
            return True
        except PipeClosed:
            log.info("Discord IPC pipe closed; will reconnect")
            self._connected = False
            self._rpc = None
            return False
        except Exception:
            log.exception("Failed to update Discord presence")
            self._connected = False
            self._rpc = None
            return False

    def clear(self) -> None:
        if not self._connected or not self._rpc:
            return
        try:
            self._rpc.clear()
        except PipeClosed:
            self._connected = False
            self._rpc = None
        except Exception:
            log.exception("Failed to clear Discord presence")

    def close(self) -> None:
        if self._rpc:
            try:
                self._rpc.close()
            except Exception:
                pass
        self._connected = False
        self._rpc = None

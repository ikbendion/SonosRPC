"""Source-aware normalization of Sonos track metadata.

Sonos reports wildly different metadata quality depending on where the
audio is coming from. `get_current_track_info()`'s `uri` field carries a
scheme prefix that tells us the source, which we use to branch formatting
logic so Discord never shows a blank field.
"""
import logging
from dataclasses import dataclass
from enum import Enum, auto

log = logging.getLogger(__name__)

UNKNOWN_TITLE = "Unknown Track"
UNKNOWN_ARTIST = "Unknown Artist"
UNKNOWN_ALBUM = "Unknown Album"


class SourceType(Enum):
    STREAMING = auto()      # Spotify, Apple Music, Amazon Music, Deezer, etc.
    RADIO = auto()           # TuneIn / internet radio / satellite radio
    LOCAL_LIBRARY = auto()   # NAS / local music library share
    LINE_IN = auto()         # TV / aux / line-in on the speaker itself
    GROUPED_ROOM = auto()    # Following another Sonos player's queue
    UNKNOWN = auto()


# Ordered so more specific prefixes are checked before generic ones.
_URI_SCHEME_MAP = (
    ("x-sonos-spotify:", SourceType.STREAMING),
    ("x-sonosprog-http:", SourceType.STREAMING),
    ("x-sonos-http:", SourceType.STREAMING),
    ("x-sonosapi-hls-static:", SourceType.RADIO),
    ("x-sonosapi-hls:", SourceType.RADIO),
    ("x-sonosapi-stream:", SourceType.RADIO),
    ("x-sonosapi-radio:", SourceType.RADIO),
    ("x-rincon-mp3radio:", SourceType.RADIO),
    ("x-file-cifs:", SourceType.LOCAL_LIBRARY),
    ("x-sonos-vli:", SourceType.LINE_IN),
    ("x-rincon-stream:", SourceType.LINE_IN),
    ("x-rincon:", SourceType.GROUPED_ROOM),
)


def classify_source(uri: str) -> SourceType:
    if not uri:
        return SourceType.UNKNOWN
    for prefix, source_type in _URI_SCHEME_MAP:
        if uri.startswith(prefix):
            return source_type
    return SourceType.UNKNOWN


@dataclass
class NormalizedTrack:
    source_type: SourceType
    details: str   # Discord "details" (top) line
    state: str      # Discord "state" (bottom) line
    album_art_url: str = ""
    raw_title: str = ""
    raw_artist: str = ""
    is_spotify: bool = False


def _clean(value) -> str:
    if not value:
        return ""
    value = str(value).strip()
    if value in ("", "NOT_IMPLEMENTED", "-1"):
        return ""
    return value


def normalize(track_info: dict) -> NormalizedTrack:
    """Turn a soco `get_current_track_info()` dict into Discord-ready text."""
    uri = _clean(track_info.get("uri"))
    source_type = classify_source(uri)

    title = _clean(track_info.get("title"))
    artist = _clean(track_info.get("artist"))
    album = _clean(track_info.get("album"))
    album_art_url = _clean(track_info.get("album_art"))

    if source_type == SourceType.STREAMING:
        details = title or UNKNOWN_TITLE
        state = artist or UNKNOWN_ARTIST
        if album:
            state = f"{state} — {album}"

    elif source_type == SourceType.RADIO:
        # Radio metadata is often just a station name in `title`, or a
        # single "Artist - Track" string crammed into one field.
        station = title or artist or "Radio Station"
        details = station
        state = "Radio"
        if artist and artist != station:
            state = f"Radio — {artist}"

    elif source_type == SourceType.LOCAL_LIBRARY:
        details = title or UNKNOWN_TITLE
        state = artist or UNKNOWN_ARTIST
        if album:
            state = f"{state} — {album}"

    elif source_type == SourceType.LINE_IN:
        details = "Line-In"
        state = title or "External Input"

    elif source_type == SourceType.GROUPED_ROOM:
        details = title or "Playing from another room"
        state = artist or "Grouped Sonos playback"

    else:
        details = title or UNKNOWN_TITLE
        state = artist or (album or "Sonos")

    return NormalizedTrack(
        source_type=source_type,
        details=details[:128],
        state=state[:128],
        album_art_url=album_art_url,
        raw_title=title,
        raw_artist=artist,
        is_spotify=uri.startswith("x-sonos-spotify:"),
    )

"""Optional SoundCloud lookup for real track/album art.

Same root problem as Spotify: Sonos serves SoundCloud art from its own
LAN-only address too. Unlike Spotify, though, SoundCloud closed public API
registration years ago, so there's no "just sign up for a free app" path
-- this only does anything if the user already holds a client_id for
SoundCloud's `api-v2` endpoint (the one their own web player calls; it's
not an officially documented third-party API, so treat this as
best-effort and liable to break if SoundCloud changes it).

Sonos also doesn't expose a distinct URI scheme for SoundCloud the way it
does for Spotify (`x-sonos-spotify:`) -- it shows up as generic
SourceType.STREAMING, same bucket as Apple Music, Amazon Music, etc. So
this is only tried as a fallback for non-Spotify streaming tracks, and
only trusts a result whose title (and artist, if Sonos gave one) actually
matches what's playing, to avoid attaching the wrong art to some other
service's track that happens to land in the same generic bucket.
"""
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

SEARCH_URL = "https://api-v2.soundcloud.com/search/tracks"
CACHE_SIZE = 50
REQUEST_TIMEOUT = 5
# api-v2 is SoundCloud's own web-client endpoint; a browser-like UA avoids
# being bounced purely for looking like a bare script.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SonosDiscordPresence"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


class SoundCloudArtResolver:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self._cache: dict[tuple[str, str], Optional[str]] = {}

    @property
    def configured(self) -> bool:
        return bool(self.client_id)

    def lookup_album_art(self, title: str, artist: str) -> Optional[str]:
        """Best-effort lookup; returns None (never raises) on failure, a
        miss, or a low-confidence match."""
        if not self.configured or not title:
            return None

        cache_key = (title.lower(), artist.lower())
        if cache_key in self._cache:
            return self._cache[cache_key]

        params = urllib.parse.urlencode(
            {"q": f"{title} {artist}".strip(), "client_id": self.client_id, "limit": 5}
        )
        request = urllib.request.Request(
            f"{SEARCH_URL}?{params}", headers={"User-Agent": USER_AGENT}
        )

        art_url = self._best_match(request, title, artist)
        self._cache[cache_key] = art_url
        if len(self._cache) > CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        return art_url

    def _best_match(self, request, title: str, artist: str) -> Optional[str]:
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError) as exc:
            log.warning("SoundCloud art lookup failed for %r by %r: %s", title, artist, exc)
            return None

        wanted_title = _normalize(title)
        wanted_artist = _normalize(artist)
        for item in payload.get("collection", []):
            candidate_title = _normalize(item.get("title", ""))
            candidate_artist = _normalize((item.get("user") or {}).get("username", ""))
            if wanted_title not in candidate_title:
                continue
            if wanted_artist and wanted_artist not in candidate_artist:
                continue
            artwork = item.get("artwork_url") or (item.get("user") or {}).get("avatar_url")
            if artwork:
                # SoundCloud serves a small thumbnail by default; swap in
                # the largest available crop.
                return artwork.replace("-large.", "-t500x500.")
        return None

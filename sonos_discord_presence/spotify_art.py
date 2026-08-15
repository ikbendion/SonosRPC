"""Optional Spotify Web API lookup for real album art.

Sonos always serves album art from its own speaker
(`http://<speaker-ip>:1400/getaa?...`) regardless of source, including
Spotify -- that URL is LAN-only, so `discord_rpc.py` can never hand it to
Discord and falls back to the generic `logo` asset instead.

If the user configures free Spotify Developer credentials, this looks up
the same track on Spotify's public catalog instead, which gives a real
`i.scdn.co` art URL that Discord's client *can* fetch. Uses the Client
Credentials flow (catalog-search only, no user login) so no OAuth
redirect/login flow is needed. Implemented with stdlib `urllib` to avoid
adding a new dependency.
"""
import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
CACHE_SIZE = 50
REQUEST_TIMEOUT = 5


class SpotifyArtResolver:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._token_expiry = 0.0
        self._cache: dict[tuple[str, str], Optional[str]] = {}

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _ensure_token(self) -> Optional[str]:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        auth_header = base64.b64encode(credentials).decode("ascii")
        data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("ascii")
        request = urllib.request.Request(
            TOKEN_URL,
            data=data,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError) as exc:
            log.warning("Spotify token request failed: %s", exc)
            return None

        self._access_token = payload.get("access_token")
        self._token_expiry = time.time() + max(payload.get("expires_in", 0) - 60, 0)
        return self._access_token

    def lookup_album_art(self, title: str, artist: str) -> Optional[str]:
        """Best-effort lookup; returns None (never raises) on any failure
        so a Spotify hiccup can't take down the poll loop."""
        if not self.configured or not title:
            return None

        cache_key = (title.lower(), artist.lower())
        if cache_key in self._cache:
            return self._cache[cache_key]

        token = self._ensure_token()
        if not token:
            return None

        query = f"track:{title}" + (f" artist:{artist}" if artist else "")
        params = urllib.parse.urlencode({"q": query, "type": "track", "limit": 1})
        request = urllib.request.Request(
            f"{SEARCH_URL}?{params}",
            headers={"Authorization": f"Bearer {token}"},
        )

        art_url = None
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            items = payload.get("tracks", {}).get("items", [])
            if items:
                images = items[0].get("album", {}).get("images", [])
                if images:
                    art_url = images[0]["url"]
        except (urllib.error.URLError, ValueError, KeyError, IndexError) as exc:
            log.warning("Spotify art lookup failed for %r by %r: %s", title, artist, exc)

        self._cache[cache_key] = art_url
        if len(self._cache) > CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        return art_url

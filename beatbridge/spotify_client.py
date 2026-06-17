from __future__ import annotations

import re
import threading
from dataclasses import dataclass

from .config import AppConfig, SPOTIFY_SCOPES

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except Exception:
    spotipy = None
    SpotifyOAuth = None


SPOTIFY_TRACK_URI_RE = re.compile(r"^spotify:track:[A-Za-z0-9]{22}$")


@dataclass(frozen=True)
class TrackInfo:
    title: str = "No track connected"
    artist: str = "Set up .env for playback data"
    is_playing: bool = False
    uri: str = ""


class SpotifyController:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = None
        self.available = False
        self.status_text = "Spotify not configured"
        self.current_track = TrackInfo()
        self._lock = threading.RLock()

    def connect(self) -> bool:
        if not self.config.spotify_configured:
            self.status_text = "Spotify credentials missing"
            return False
        if spotipy is None or SpotifyOAuth is None:
            self.status_text = "spotipy is unavailable"
            return False

        try:
            auth_manager = SpotifyOAuth(
                client_id=self.config.spotify_client_id,
                client_secret=self.config.spotify_client_secret,
                redirect_uri=self.config.spotify_redirect_uri,
                scope=" ".join(SPOTIFY_SCOPES),
                cache_path=self.config.spotify_cache_path,
                open_browser=True,
            )
            with self._lock:
                self.client = spotipy.Spotify(
                    auth_manager=auth_manager,
                    requests_timeout=6,
                    retries=1,
                    status_retries=1,
                )
                self.available = True
                self.status_text = "Spotify connected"
            self.refresh_current_track()
            return True
        except Exception as exc:
            with self._lock:
                self.available = False
                self.status_text = f"Spotify login unavailable: {exc}"
            return False

    def refresh_current_track(self) -> TrackInfo:
        client = self._client()
        if client is None:
            return self.current_track

        try:
            playback = client.current_user_playing_track()
            if not playback or not playback.get("item"):
                self.current_track = TrackInfo(
                    title="Nothing playing",
                    artist="Start playback in your music app",
                    is_playing=False,
                )
                self.status_text = "No active playback"
                return self.current_track

            item = playback["item"]
            artists = ", ".join(artist["name"] for artist in item.get("artists", []))
            self.current_track = TrackInfo(
                title=item.get("name") or "Unknown track",
                artist=artists or "Unknown artist",
                is_playing=bool(playback.get("is_playing")),
                uri=item.get("uri") or "",
            )
            self.status_text = "Playing" if self.current_track.is_playing else "Paused"
            return self.current_track
        except Exception as exc:
            self.status_text = f"Spotify refresh failed: {exc}"
            return self.current_track

    def toggle_playback(self) -> None:
        client = self._client()
        if client is None:
            return
        try:
            if self.current_track.is_playing:
                client.pause_playback()
                self.status_text = "Paused"
            else:
                client.start_playback()
                self.status_text = "Playing"
            self.refresh_current_track()
        except Exception as exc:
            self.status_text = f"Playback control failed: {exc}"

    def next_track(self) -> None:
        client = self._client()
        if client is None:
            return
        try:
            client.next_track()
            self.status_text = "Skipped"
            self.refresh_current_track()
        except Exception as exc:
            self.status_text = f"Next failed: {exc}"

    def previous_track(self) -> None:
        client = self._client()
        if client is None:
            return
        try:
            client.previous_track()
            self.status_text = "Previous"
            self.refresh_current_track()
        except Exception as exc:
            self.status_text = f"Previous failed: {exc}"

    def add_to_queue(self, uri: str) -> tuple[bool, str]:
        client = self._client()
        if client is None:
            return False, "Spotify is not connected"
        if not SPOTIFY_TRACK_URI_RE.match(uri or ""):
            return False, "Recommendation has no valid track URI"

        try:
            client.add_to_queue(uri)
            self.status_text = "Queued recommendation"
            return True, "Queued recommendation"
        except Exception as exc:
            self.status_text = f"Queue failed: {exc}"
            return False, self.status_text

    def _client(self):
        with self._lock:
            if self.client is None or not self.available:
                return None
            return self.client

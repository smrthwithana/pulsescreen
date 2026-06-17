from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


SPOTIFY_SCOPES = (
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
)


@dataclass(frozen=True)
class AppConfig:
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_redirect_uri: str
    spotify_cache_path: str
    database_path: Path

    @property
    def spotify_configured(self) -> bool:
        return bool(
            self.spotify_client_id
            and self.spotify_client_secret
            and self.spotify_redirect_uri
        )


def load_config() -> AppConfig:
    if load_dotenv is not None:
        load_dotenv()

    root = Path.cwd()
    return AppConfig(
        spotify_client_id=os.getenv("SPOTIPY_CLIENT_ID") or None,
        spotify_client_secret=os.getenv("SPOTIPY_CLIENT_SECRET") or None,
        spotify_redirect_uri=os.getenv(
            "SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"
        ),
        spotify_cache_path=os.getenv(
            "SPOTIPY_CACHE_PATH", str(root / ".spotipy-cache")
        ),
        database_path=root / "beatbridge_tracks.sqlite3",
    )

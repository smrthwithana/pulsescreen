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
    app_name: str
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_redirect_uri: str
    spotify_cache_path: str
    database_path: Path
    audio_device: str | None

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
        app_name=os.getenv("PLUSESCREEN_APP_NAME", "plusescreen"),
        spotify_client_id=os.getenv("SPOTIPY_CLIENT_ID") or None,
        spotify_client_secret=os.getenv("SPOTIPY_CLIENT_SECRET") or None,
        spotify_redirect_uri=os.getenv(
            "SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"
        ),
        spotify_cache_path=os.getenv(
            "SPOTIPY_CACHE_PATH", str(root / ".spotipy-cache")
        ),
        database_path=root / "plusescreen_tracks.sqlite3",
        audio_device=(
            os.getenv("PLUSESCREEN_AUDIO_DEVICE")
            or os.getenv("PULSESCREEN_AUDIO_DEVICE")
            or os.getenv("BEATBRIDGE_AUDIO_DEVICE")
            or None
        ),
    )

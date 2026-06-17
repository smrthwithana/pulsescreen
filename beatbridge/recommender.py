from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


SPOTIFY_TRACK_URI_RE = re.compile(r"^spotify:track:[A-Za-z0-9]{22}$")


@dataclass(frozen=True)
class RecommendedTrack:
    title: str
    artist: str
    bpm: float
    energy: float
    mood: str
    spotify_uri: str
    match_score: float

    @property
    def queueable(self) -> bool:
        return bool(SPOTIFY_TRACK_URI_RE.match(self.spotify_uri or ""))


DEMO_TRACKS = [
    ("Neon Drift", "Glass Circuit", 96, 0.44, "dreamy", ""),
    ("Late Metro Bloom", "Astra Lane", 99, 0.48, "chill", ""),
    ("Soft Voltage", "Mira Vale", 102, 0.52, "focus", ""),
    ("Velvet Console", "Night Arcade", 104, 0.57, "retro", ""),
    ("Afterimage Slowdance", "Luma Index", 107, 0.42, "dreamy", ""),
    ("Chrome Tide", "Solar Habit", 110, 0.61, "smooth", ""),
    ("Vapor Keys", "Blue Halogen", 112, 0.55, "chill", ""),
    ("Circuit Garden", "Echo Tangle", 114, 0.63, "focus", ""),
    ("Cassette Skyline", "Moon Router", 116, 0.58, "retro", ""),
    ("Liquid Avenue", "Signal Flower", 118, 0.68, "smooth", ""),
    ("Glass Elevator", "Polar Sequence", 120, 0.51, "cool", ""),
    ("Palmwave Static", "The Soft Pixels", 121, 0.66, "retro", ""),
    ("Prism Runner", "Kilo Hearts", 123, 0.73, "euphoric", ""),
    ("Warm Boot", "Mono Flora", 124, 0.62, "focus", ""),
    ("Lunar Lobby", "Hush Servo", 126, 0.49, "chill", ""),
    ("Sunset Packet", "Amber Relay", 127, 0.74, "euphoric", ""),
    ("Night Bus Mirage", "Velvet Node", 128, 0.70, "smooth", ""),
    ("Blue Firewire", "Dawn Compiler", 130, 0.78, "euphoric", ""),
    ("Memory Foam Bass", "Orbit Runner", 132, 0.64, "cool", ""),
    ("Kinetic Halo", "Ion Garden", 134, 0.82, "euphoric", ""),
    ("Rain on CRT", "Violet Terminal", 136, 0.53, "dark", ""),
    ("Sleepless Driver", "Ghost Frequency", 138, 0.77, "dark", ""),
    ("Magnetic Pool", "Futura Moss", 140, 0.69, "smooth", ""),
    ("Frosted Laser", "Plasma Motel", 142, 0.85, "euphoric", ""),
    ("Deep Render", "Bit Orchid", 144, 0.72, "focus", ""),
    ("Carbon Hearts", "North Neon", 146, 0.79, "dark", ""),
    ("Zero Gravity Club", "Pulse Lantern", 148, 0.88, "euphoric", ""),
    ("Pastel Overdrive", "Halo Syntax", 150, 0.76, "retro", ""),
    ("Fever Buffer", "Arcade Oracle", 154, 0.92, "euphoric", ""),
    ("Blacklight River", "Neon Particulate", 158, 0.86, "dark", ""),
    ("Starlit Debug", "Aural Cache", 162, 0.81, "focus", ""),
    ("Aurora Queue", "Slow Comet", 168, 0.74, "dreamy", ""),
]


class RecommendationEngine:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._ensure_database()

    def recommend(
        self,
        bpm: float,
        energy: float,
        mood: str | None = None,
        limit: int = 5,
    ) -> list[RecommendedTrack]:
        target_bpm = bpm if 55 <= bpm <= 190 else 120.0
        target_energy = max(0.0, min(1.0, energy if energy > 0 else 0.55))

        rows = self._fetch_tracks()
        scored = []
        for title, artist, track_bpm, track_energy, track_mood, spotify_uri in rows:
            bpm_penalty = min(abs(track_bpm - target_bpm) / 55.0, 1.0) * 68.0
            energy_penalty = abs(track_energy - target_energy) * 28.0
            mood_penalty = 0.0 if not mood or mood == track_mood else 4.0
            score = max(0.0, 100.0 - bpm_penalty - energy_penalty - mood_penalty)
            scored.append(
                RecommendedTrack(
                    title=title,
                    artist=artist,
                    bpm=float(track_bpm),
                    energy=float(track_energy),
                    mood=track_mood,
                    spotify_uri=spotify_uri or "",
                    match_score=score,
                )
            )

        scored.sort(key=lambda track: track.match_score, reverse=True)
        return scored[:limit]

    def _ensure_database(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    bpm REAL NOT NULL,
                    energy REAL NOT NULL,
                    mood TEXT NOT NULL,
                    spotify_uri TEXT DEFAULT '',
                    UNIQUE(title, artist)
                )
                """
            )
            conn.executemany(
                """
                INSERT OR IGNORE INTO tracks
                    (title, artist, bpm, energy, mood, spotify_uri)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                DEMO_TRACKS,
            )

    def _fetch_tracks(self) -> list[tuple[str, str, float, float, str, str]]:
        with sqlite3.connect(self.database_path) as conn:
            rows = conn.execute(
                """
                SELECT title, artist, bpm, energy, mood, spotify_uri
                FROM tracks
                """
            ).fetchall()
        return rows

from __future__ import annotations

import threading
import time

import pygame

from .audio_engine import AudioEngine, AudioSnapshot
from .config import load_config
from .recommender import RecommendationEngine, RecommendedTrack
from .spotify_client import SpotifyController, TrackInfo
from .visualizers import VisualizerManager


HINT_TEXT = "SPACE play/pause   N next   B previous   R refresh   Q queue match   1-3 modes   F fullscreen   ESC quit"


def main() -> None:
    config = load_config()
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("BeatBridge")

    fullscreen = True
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    fonts = make_fonts()

    audio = AudioEngine()
    audio.start()

    spotify = SpotifyController(config)
    run_background(spotify.connect)

    recommender = RecommendationEngine(config.database_path)
    visualizers = VisualizerManager(screen.get_size())

    recommendations: list[RecommendedTrack] = []
    next_recommendation_update = 0.0
    next_track_update = 0.0
    toast = {"text": "", "until": 0.0}

    def set_toast(text: str, seconds: float = 2.8) -> None:
        toast["text"] = text
        toast["until"] = time.monotonic() + seconds

    running = True
    try:
        while running:
            dt = clock.tick(60) / 1000.0
            now = time.monotonic()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_1:
                        visualizers.set_mode(0)
                    elif event.key == pygame.K_2:
                        visualizers.set_mode(1)
                    elif event.key == pygame.K_3:
                        visualizers.set_mode(2)
                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
                        size = (0, 0) if fullscreen else (1280, 720)
                        screen = pygame.display.set_mode(size, flags)
                        visualizers.resize(screen.get_size())
                        fonts = make_fonts()
                    elif event.key == pygame.K_SPACE:
                        run_background(spotify.toggle_playback)
                    elif event.key == pygame.K_n:
                        run_background(spotify.next_track)
                    elif event.key == pygame.K_b:
                        run_background(spotify.previous_track)
                    elif event.key == pygame.K_r:
                        run_background(spotify.refresh_current_track)
                    elif event.key == pygame.K_q:
                        queueable = next((track for track in recommendations if track.queueable), None)
                        if queueable is None:
                            set_toast("Demo tracks need real Spotify track URIs before queueing")
                        else:
                            set_toast(f"Queueing {queueable.title}")
                            run_background(
                                lambda uri=queueable.spotify_uri: set_toast(
                                    spotify.add_to_queue(uri)[1]
                                )
                            )
                elif event.type == pygame.VIDEORESIZE and not fullscreen:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    visualizers.resize(screen.get_size())

            snapshot = audio.update(dt)

            if now >= next_recommendation_update:
                recommendations = recommender.recommend(snapshot.bpm, snapshot.energy, limit=5)
                next_recommendation_update = now + 0.5

            if spotify.available and now >= next_track_update:
                run_background(spotify.refresh_current_track)
                next_track_update = now + 7.0

            visualizers.draw(screen, snapshot, dt)
            draw_overlay(
                screen=screen,
                fonts=fonts,
                snapshot=snapshot,
                mode_name=visualizers.current_name,
                track=spotify.current_track,
                spotify_status=spotify.status_text,
                recommendations=recommendations,
                toast_text=toast["text"] if now < toast["until"] else "",
            )
            pygame.display.flip()
    finally:
        audio.stop()
        pygame.quit()


def run_background(fn) -> None:
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()


def make_fonts() -> dict[str, pygame.font.Font]:
    return {
        "brand": pygame.font.SysFont("consolas", 28, bold=True),
        "body": pygame.font.SysFont("consolas", 18),
        "small": pygame.font.SysFont("consolas", 14),
        "tiny": pygame.font.SysFont("consolas", 12),
    }


def draw_overlay(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    snapshot: AudioSnapshot,
    mode_name: str,
    track: TrackInfo,
    spotify_status: str,
    recommendations: list[RecommendedTrack],
    toast_text: str,
) -> None:
    width, height = screen.get_size()
    draw_top_left(screen, fonts, snapshot, mode_name)
    draw_bottom_track(screen, fonts, track, spotify_status)
    draw_center_hint(screen, fonts, HINT_TEXT)
    draw_recommendations(screen, fonts, recommendations)
    if toast_text:
        draw_toast(screen, fonts, toast_text, width, height)


def draw_top_left(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    snapshot: AudioSnapshot,
    mode_name: str,
) -> None:
    panel = pygame.Surface((360, 92), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 92), panel.get_rect(), border_radius=8)
    draw_text(panel, fonts["brand"], "BeatBridge", (16, 12), (240, 255, 255))
    source = "DEMO" if snapshot.demo_mode else "LIVE"
    bpm_text = f"{snapshot.bpm:05.1f} BPM" if snapshot.bpm > 0 else "BPM scanning"
    draw_text(
        panel,
        fonts["small"],
        f"{mode_name}  |  {source}  |  {bpm_text}",
        (17, 48),
        (174, 230, 235),
    )
    levels = f"B {snapshot.bass:.2f}   M {snapshot.mids:.2f}   T {snapshot.treble:.2f}"
    draw_text(panel, fonts["tiny"], levels, (17, 70), (135, 190, 210))
    screen.blit(panel, (18, 18))


def draw_bottom_track(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    track: TrackInfo,
    spotify_status: str,
) -> None:
    width, height = screen.get_size()
    panel_width = min(640, width - 36)
    panel = pygame.Surface((panel_width, 82), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 104), panel.get_rect(), border_radius=8)
    title = ellipsize(fonts["body"], track.title, panel_width - 30)
    artist = ellipsize(fonts["small"], track.artist, panel_width - 30)
    status = ellipsize(fonts["tiny"], spotify_status, panel_width - 30)
    draw_text(panel, fonts["body"], title, (15, 13), (255, 255, 255))
    draw_text(panel, fonts["small"], artist, (15, 40), (178, 238, 240))
    draw_text(panel, fonts["tiny"], status, (15, 61), (155, 164, 184))
    screen.blit(panel, (18, height - 100))


def draw_center_hint(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    hint: str,
) -> None:
    width, height = screen.get_size()
    text = ellipsize(fonts["tiny"], hint, max(280, width - 760))
    rendered = fonts["tiny"].render(text, True, (205, 220, 226))
    pad_x, pad_y = 12, 7
    panel = pygame.Surface((rendered.get_width() + pad_x * 2, rendered.get_height() + pad_y * 2), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 82), panel.get_rect(), border_radius=8)
    panel.blit(rendered, (pad_x, pad_y))
    screen.blit(panel, ((width - panel.get_width()) // 2, height - panel.get_height() - 24))


def draw_recommendations(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    recommendations: list[RecommendedTrack],
) -> None:
    width, height = screen.get_size()
    panel_width = min(390, max(310, int(width * 0.28)))
    panel_height = min(430, height - 90)
    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 96), panel.get_rect(), border_radius=8)
    pygame.draw.rect(panel, (0, 240, 255, 64), panel.get_rect(), width=1, border_radius=8)
    draw_text(panel, fonts["body"], "Smooth Transitions", (18, 16), (245, 255, 255))

    y = 54
    row_gap = 68
    for index, track in enumerate(recommendations[:5], start=1):
        color = (255, 255, 255) if index == 1 else (215, 232, 235)
        title = ellipsize(fonts["small"], f"{index}. {track.title}", panel_width - 34)
        artist = ellipsize(fonts["tiny"], track.artist, panel_width - 34)
        meta = f"{track.bpm:.0f} BPM  E {track.energy:.2f}  {track.match_score:.0f}%"
        queue = "queue-ready" if track.queueable else "local demo"

        draw_text(panel, fonts["small"], title, (18, y), color)
        draw_text(panel, fonts["tiny"], artist, (18, y + 20), (159, 218, 223))
        draw_text(panel, fonts["tiny"], meta, (18, y + 38), (255, 216, 105))
        draw_text(panel, fonts["tiny"], queue, (panel_width - 98, y + 38), (180, 170, 255))
        y += row_gap

    if not recommendations:
        draw_text(panel, fonts["small"], "Listening for a transition...", (18, 58), (210, 230, 235))

    screen.blit(panel, (width - panel_width - 18, 72))


def draw_toast(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    text: str,
    width: int,
    height: int,
) -> None:
    rendered = fonts["small"].render(ellipsize(fonts["small"], text, 520), True, (255, 255, 255))
    panel = pygame.Surface((rendered.get_width() + 26, rendered.get_height() + 20), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 150), panel.get_rect(), border_radius=8)
    pygame.draw.rect(panel, (255, 58, 212, 110), panel.get_rect(), width=1, border_radius=8)
    panel.blit(rendered, (13, 10))
    screen.blit(panel, ((width - panel.get_width()) // 2, height - 150))


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    surface.blit(font.render(text, True, color), position)


def ellipsize(font: pygame.font.Font, text: str, max_width: int) -> str:
    if font.size(text)[0] <= max_width:
        return text
    suffix = "..."
    clipped = text
    while clipped and font.size(clipped + suffix)[0] > max_width:
        clipped = clipped[:-1]
    return clipped + suffix if clipped else suffix

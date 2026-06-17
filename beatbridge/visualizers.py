from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from .audio_engine import AudioSnapshot


PALETTE = [
    (0, 244, 255),
    (255, 58, 212),
    (255, 226, 72),
    (57, 255, 136),
    (132, 96, 255),
    (255, 111, 72),
]


def neon_color(index: int, pulse: float = 0.0, alpha: int = 220) -> tuple[int, int, int, int]:
    base = PALETTE[index % len(PALETTE)]
    boost = min(1.0, max(0.0, pulse)) * 60
    return (
        min(255, int(base[0] + boost)),
        min(255, int(base[1] + boost)),
        min(255, int(base[2] + boost)),
        alpha,
    )


class LiquidFlow:
    name = "Liquid Flow"

    def __init__(self, size: tuple[int, int]) -> None:
        self.resize(size)
        self.phase = 0.0

    def resize(self, size: tuple[int, int]) -> None:
        self.size = size
        self.trails = pygame.Surface(size, pygame.SRCALPHA)

    def draw(self, screen: pygame.Surface, audio: AudioSnapshot, dt: float) -> None:
        width, height = self.size
        self.phase += dt * (0.7 + audio.mids * 2.0)
        self.trails.fill((6, 8, 12, 24), special_flags=pygame.BLEND_RGBA_SUB)

        spacing = max(18, width // 90)
        xs = list(range(-spacing * 2, width + spacing * 2, spacing))
        wave_count = 10

        for wave in range(wave_count):
            center = height * (0.18 + wave / (wave_count - 1) * 0.64)
            amp = height * (0.035 + audio.bass * 0.11 + wave * 0.002)
            speed = self.phase * (0.8 + wave * 0.11)
            points = []
            for x in xs:
                nx = x / max(width, 1)
                ribbon = math.sin(nx * 12.0 + speed + wave * 0.7)
                ribbon += math.sin(nx * 28.0 - speed * 1.25 + wave) * 0.35
                ribbon += math.sin(nx * 6.0 + self.phase * 0.35 + audio.treble * 3.0) * 0.6
                y = center + ribbon * amp + math.sin(self.phase + wave) * audio.volume * 35
                points.append((x, y))

            pulse = audio.volume + (0.5 if audio.beat else 0.0)
            color = neon_color(wave, pulse, 190)
            glow = neon_color(wave + 2, pulse, 54)
            width_glow = max(4, int(5 + audio.bass * 18))
            width_core = max(1, int(1 + audio.treble * 4))
            pygame.draw.lines(self.trails, glow, False, points, width_glow)
            pygame.draw.lines(self.trails, color, False, points, width_core)

        for ring in range(4):
            radius = int((audio.bass + ring * 0.25 + self.phase * 0.08) % 1.3 * height * 0.42)
            alpha = max(0, 72 - ring * 12)
            color = neon_color(ring + 1, audio.energy, alpha)
            pygame.draw.circle(self.trails, color, (width // 2, height // 2), radius, 1)

        screen.fill((1, 3, 8))
        screen.blit(self.trails, (0, 0))


@dataclass
class Particle:
    angle: float
    radius: float
    speed: float
    size: float
    color_index: int


class ParticlePulse:
    name = "Particle Pulse"

    def __init__(self, size: tuple[int, int]) -> None:
        self.seed = random.Random(37)
        self.particles: list[Particle] = []
        self.flash = 0.0
        self.resize(size)

    def resize(self, size: tuple[int, int]) -> None:
        self.size = size
        self.trails = pygame.Surface(size, pygame.SRCALPHA)
        width, height = size
        max_radius = max(80, min(width, height) * 0.46)
        count = 260
        self.particles = [
            Particle(
                angle=self.seed.random() * math.tau,
                radius=self.seed.random() * max_radius,
                speed=0.2 + self.seed.random() * 1.6,
                size=1.0 + self.seed.random() * 3.2,
                color_index=i,
            )
            for i in range(count)
        ]

    def draw(self, screen: pygame.Surface, audio: AudioSnapshot, dt: float) -> None:
        width, height = self.size
        center = (width * 0.5, height * 0.5)
        max_radius = max(80, min(width, height) * 0.5)
        self.trails.fill((7, 5, 12, 34), special_flags=pygame.BLEND_RGBA_SUB)
        self.flash = max(0.0, self.flash - dt * 3.2)
        if audio.beat:
            self.flash = 1.0

        for particle in self.particles:
            particle.angle += dt * particle.speed * (0.7 + audio.treble * 2.4)
            particle.radius += dt * (18 + audio.bass * 85 + self.flash * 180)
            if particle.radius > max_radius:
                particle.radius *= 0.16
                particle.angle = self.seed.random() * math.tau

            wobble = math.sin(particle.angle * 3.0 + particle.radius * 0.018) * audio.mids * 42
            radius = particle.radius + wobble
            x = center[0] + math.cos(particle.angle) * radius
            y = center[1] + math.sin(particle.angle) * radius
            size = int(particle.size + audio.volume * 5 + self.flash * 4)
            color = neon_color(particle.color_index, audio.energy + self.flash, 150)
            pygame.draw.circle(self.trails, color, (int(x), int(y)), max(1, size))

        burst_radius = int(min(width, height) * (0.08 + audio.bass * 0.34 + self.flash * 0.16))
        pygame.draw.circle(
            self.trails,
            neon_color(2, audio.energy + self.flash, 76),
            (int(center[0]), int(center[1])),
            burst_radius,
            max(2, int(2 + audio.bass * 10)),
        )

        screen.fill((3, 1, 9))
        screen.blit(self.trails, (0, 0))


class EqualizerWave:
    name = "Equalizer Wave"

    def __init__(self, size: tuple[int, int]) -> None:
        self.phase = 0.0
        self.resize(size)

    def resize(self, size: tuple[int, int]) -> None:
        self.size = size
        self.trails = pygame.Surface(size, pygame.SRCALPHA)

    def draw(self, screen: pygame.Surface, audio: AudioSnapshot, dt: float) -> None:
        width, height = self.size
        self.phase += dt * (1.3 + audio.energy * 2.0)
        self.trails.fill((3, 6, 10, 42), special_flags=pygame.BLEND_RGBA_SUB)

        bar_count = max(36, width // 20)
        gap = 3
        bar_width = max(3, width // bar_count - gap)
        baseline = int(height * 0.63)

        for i in range(bar_count):
            x = i * (bar_width + gap) + gap
            band_mix = (
                audio.bass * math.sin(i * 0.2 + self.phase) ** 2
                + audio.mids * math.sin(i * 0.37 - self.phase * 0.8) ** 2
                + audio.treble * math.sin(i * 0.73 + self.phase * 1.7) ** 2
            ) / 1.35
            height_value = int(18 + band_mix * height * 0.46 + audio.volume * 44)
            color = neon_color(i, band_mix + audio.volume, 185)
            glow = neon_color(i + 1, band_mix, 48)
            pygame.draw.rect(
                self.trails,
                glow,
                (x - 2, baseline - height_value - 3, bar_width + 4, height_value + 6),
                border_radius=bar_width // 2,
            )
            pygame.draw.rect(
                self.trails,
                color,
                (x, baseline - height_value, bar_width, height_value),
                border_radius=bar_width // 2,
            )
            mirror_h = int(height_value * 0.42)
            pygame.draw.rect(
                self.trails,
                (*color[:3], 70),
                (x, baseline + 8, bar_width, mirror_h),
                border_radius=bar_width // 2,
            )

        upper = []
        lower = []
        step = max(10, width // 120)
        for x in range(0, width + step, step):
            nx = x / max(width, 1)
            wave = math.sin(nx * math.tau * 2 + self.phase) * audio.bass
            wave += math.sin(nx * math.tau * 5 - self.phase * 1.3) * audio.mids * 0.75
            wave += math.sin(nx * math.tau * 13 + self.phase * 2.1) * audio.treble * 0.28
            y = height * 0.32 + wave * height * 0.18
            upper.append((x, y))
            lower.append((x, height - y))

        pygame.draw.lines(self.trails, neon_color(4, audio.energy, 92), False, upper, 8)
        pygame.draw.lines(self.trails, neon_color(0, audio.energy, 235), False, upper, 2)
        pygame.draw.lines(self.trails, neon_color(1, audio.energy, 72), False, lower, 5)

        screen.fill((1, 4, 8))
        screen.blit(self.trails, (0, 0))


class VisualizerManager:
    def __init__(self, size: tuple[int, int]) -> None:
        self.visualizers = [LiquidFlow(size), ParticlePulse(size), EqualizerWave(size)]
        self.mode_index = 0

    @property
    def current_name(self) -> str:
        return self.visualizers[self.mode_index].name

    def set_mode(self, mode_index: int) -> None:
        if 0 <= mode_index < len(self.visualizers):
            self.mode_index = mode_index

    def resize(self, size: tuple[int, int]) -> None:
        for visualizer in self.visualizers:
            visualizer.resize(size)

    def draw(self, screen: pygame.Surface, audio: AudioSnapshot, dt: float) -> None:
        self.visualizers[self.mode_index].draw(screen, audio, dt)

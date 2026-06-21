from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None


@dataclass(frozen=True)
class AudioSnapshot:
    volume: float = 0.0
    bass: float = 0.0
    mids: float = 0.0
    treble: float = 0.0
    energy: float = 0.0
    beat: bool = False
    bpm: float = 0.0
    demo_mode: bool = False
    status: str = ""


class AudioEngine:
    def __init__(
        self,
        sample_rate: int = 44_100,
        block_size: int = 2048,
        device: str | int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.requested_device = device
        self.current_device_index: int | None = None
        self.stream = None
        self.demo_mode = False
        self.status = "Microphone initializing"

        self._lock = threading.Lock()
        self._latest_samples: np.ndarray | None = None
        self._start_time = time.monotonic()
        self._last_beat_time = 0.0
        self._beat_times: deque[float] = deque(maxlen=16)

        self._volume = 0.0
        self._bass = 0.0
        self._mids = 0.0
        self._treble = 0.0
        self._energy = 0.0
        self._bpm = 0.0
        self._noise_floor = 0.04
        self._previous_raw_volume = 0.0

    def start(self) -> None:
        if sd is None:
            self.demo_mode = True
            self.status = "Demo audio: sounddevice is unavailable"
            return

        errors: list[str] = []
        for device_index in self._candidate_input_devices(include_requested=True):
            try:
                info = sd.query_devices(device_index, "input")
                default_rate = int(float(info.get("default_samplerate") or self.sample_rate))
                self.sample_rate = default_rate if default_rate > 0 else self.sample_rate
                self.stream = sd.InputStream(
                    device=device_index,
                    channels=1,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self.stream.start()
                name = self._clean_device_name(info.get("name", device_index))
                self.status = f"Live microphone #{device_index}: {name}"
                self.demo_mode = False
                self.current_device_index = device_index
                return
            except Exception as exc:
                errors.append(f"{device_index}: {exc}")
                self.stream = None

        self.demo_mode = True
        self.current_device_index = None
        detail = errors[-1] if errors else "no input devices found"
        self.status = f"Demo audio: microphone unavailable ({detail})"

    def stop(self) -> None:
        if self.stream is None:
            return
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
        self.stream = None

    def cycle_input_device(self) -> str:
        if sd is None:
            self.demo_mode = True
            self.status = "Demo audio: sounddevice is unavailable"
            return self.status

        try:
            candidates = self._candidate_input_devices(include_requested=False)
        except Exception as exc:
            self.demo_mode = True
            self.status = f"Demo audio: device scan failed ({exc})"
            return self.status

        if not candidates:
            self.demo_mode = True
            self.status = "Demo audio: no input devices found"
            return self.status

        if self.current_device_index in candidates:
            position = candidates.index(self.current_device_index)
            next_device = candidates[(position + 1) % len(candidates)]
        else:
            next_device = candidates[0]

        self.stop()
        self.requested_device = next_device
        self.demo_mode = False
        self.status = "Switching microphone"
        self.start()
        return self.status

    def update(self, dt: float) -> AudioSnapshot:
        if self.demo_mode:
            return self._update_demo()

        with self._lock:
            samples = None if self._latest_samples is None else self._latest_samples.copy()
            self._latest_samples = None

        if samples is None or samples.size == 0:
            self._volume *= 0.94
            self._bass *= 0.94
            self._mids *= 0.94
            self._treble *= 0.94
            self._energy *= 0.94
            return AudioSnapshot(
                volume=self._volume,
                bass=self._bass,
                mids=self._mids,
                treble=self._treble,
                energy=self._energy,
                bpm=self._bpm,
                demo_mode=False,
                status=self.status,
            )

        raw_volume, raw_bass, raw_mids, raw_treble = self._analyze_samples(samples)
        beat = self._detect_beat(raw_volume)

        smooth = 1.0 - math.exp(-max(dt, 1 / 120) * 9.0)
        self._volume += (raw_volume - self._volume) * smooth
        self._bass += (raw_bass - self._bass) * smooth
        self._mids += (raw_mids - self._mids) * smooth
        self._treble += (raw_treble - self._treble) * smooth

        raw_energy = min(
            1.0,
            raw_volume * 0.45 + raw_bass * 0.25 + raw_mids * 0.2 + raw_treble * 0.1,
        )
        self._energy += (raw_energy - self._energy) * smooth

        return AudioSnapshot(
            volume=self._volume,
            bass=self._bass,
            mids=self._mids,
            treble=self._treble,
            energy=self._energy,
            beat=beat,
            bpm=self._bpm,
            demo_mode=False,
            status=self.status,
        )

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            self.status = f"Live microphone ({status})"
        mono = np.asarray(indata[:, 0], dtype=np.float32)
        with self._lock:
            self._latest_samples = mono

    def _candidate_input_devices(self, include_requested: bool = True) -> list[int]:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        indexes = [
            index
            for index, info in enumerate(devices)
            if int(info.get("max_input_channels", 0)) > 0
        ]

        requested = self._match_requested_device(devices, indexes) if include_requested else None
        preferred = sorted(
            indexes,
            key=lambda index: self._device_score(index, devices[index], hostapis),
            reverse=True,
        )

        default_indexes: list[int] = []
        for value in sd.default.device:
            if isinstance(value, int) and value >= 0 and value in indexes:
                default_indexes.append(value)

        ordered: list[int] = []
        for index in [requested, *preferred, *default_indexes, *indexes]:
            if index is not None and index not in ordered:
                ordered.append(index)
        return ordered

    def _match_requested_device(self, devices, indexes: list[int]) -> int | None:
        if self.requested_device is None:
            return None

        request = str(self.requested_device).strip()
        if not request:
            return None
        if request.isdigit():
            index = int(request)
            return index if index in indexes else None

        lowered = request.lower()
        for index in indexes:
            if lowered in str(devices[index].get("name", "")).lower():
                return index
        return None

    def _device_score(self, index: int, info, hostapis) -> int:
        name = self._clean_device_name(info.get("name", "")).lower()
        hostapi_name = ""
        hostapi_index = info.get("hostapi")
        if isinstance(hostapi_index, int) and 0 <= hostapi_index < len(hostapis):
            hostapi_name = str(hostapis[hostapi_index].get("name", "")).lower()

        score = 0
        if "microphone" in name:
            score += 80
        if "mic" in name:
            score += 35
        if "array" in name:
            score += 12
        if "wasapi" in hostapi_name:
            score += 18
        elif "directsound" in hostapi_name:
            score += 10
        elif "mme" in hostapi_name:
            score += 4
        if "stereo mix" in name:
            score -= 70
        if "mapper" in name or "primary sound" in name:
            score -= 30
        return score

    def _clean_device_name(self, name) -> str:
        return " ".join(str(name).split())

    def _analyze_samples(self, samples: np.ndarray) -> tuple[float, float, float, float]:
        samples = np.nan_to_num(samples.astype(np.float32), copy=False)
        rms = float(np.sqrt(np.mean(samples * samples)))
        raw_volume = float(np.clip(rms * 10.0, 0.0, 1.0))

        if samples.size < 64:
            return raw_volume, 0.0, 0.0, 0.0

        windowed = samples * np.hanning(samples.size)
        magnitudes = np.abs(np.fft.rfft(windowed)) / max(samples.size, 1)
        freqs = np.fft.rfftfreq(samples.size, 1.0 / self.sample_rate)

        bass = self._band_value(freqs, magnitudes, 20, 250, 1300, 3.4)
        mids = self._band_value(freqs, magnitudes, 250, 2500, 900, 3.2)
        treble = self._band_value(freqs, magnitudes, 2500, 10_000, 1400, 3.0)
        return raw_volume, bass, mids, treble

    def _band_value(
        self,
        freqs: np.ndarray,
        magnitudes: np.ndarray,
        low: float,
        high: float,
        gain: float,
        divisor: float,
    ) -> float:
        mask = (freqs >= low) & (freqs < high)
        if not np.any(mask):
            return 0.0
        value = float(np.mean(magnitudes[mask]))
        return float(np.clip(math.log1p(value * gain) / divisor, 0.0, 1.0))

    def _detect_beat(self, raw_volume: float) -> bool:
        now = time.monotonic()
        self._noise_floor = self._noise_floor * 0.94 + raw_volume * 0.06
        onset = raw_volume - self._previous_raw_volume
        self._previous_raw_volume = raw_volume

        threshold = max(0.08, self._noise_floor * 1.45)
        beat = raw_volume > threshold and onset > 0.025 and now - self._last_beat_time > 0.26
        if beat:
            self._last_beat_time = now
            self._beat_times.append(now)
            self._update_bpm()
        return beat

    def _update_bpm(self) -> None:
        if len(self._beat_times) < 4:
            return
        intervals = np.diff(np.array(self._beat_times, dtype=np.float64))
        intervals = intervals[(intervals >= 0.3) & (intervals <= 1.4)]
        if intervals.size < 3:
            return

        bpm = 60.0 / float(np.median(intervals))
        while bpm < 70:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        self._bpm = bpm if self._bpm <= 0 else self._bpm * 0.72 + bpm * 0.28

    def _update_demo(self) -> AudioSnapshot:
        now = time.monotonic()
        t = now - self._start_time
        demo_bpm = 118.0 + math.sin(t * 0.09) * 12.0
        beat_period = 60.0 / demo_bpm
        beat_phase = (t % beat_period) / beat_period
        pulse = math.exp(-beat_phase * 12.0)
        beat = pulse > 0.72 and now - self._last_beat_time > beat_period * 0.55
        if beat:
            self._last_beat_time = now

        bass = np.clip(0.2 + pulse * 0.8 + math.sin(t * 1.7) * 0.08, 0.0, 1.0)
        mids = np.clip(0.35 + math.sin(t * 2.3) * 0.18 + pulse * 0.25, 0.0, 1.0)
        treble = np.clip(0.32 + math.sin(t * 4.9) * 0.22 + pulse * 0.15, 0.0, 1.0)
        volume = np.clip(0.28 + pulse * 0.72 + math.sin(t * 1.2) * 0.09, 0.0, 1.0)
        energy = np.clip(volume * 0.45 + bass * 0.25 + mids * 0.2 + treble * 0.1, 0.0, 1.0)

        self._volume = float(volume)
        self._bass = float(bass)
        self._mids = float(mids)
        self._treble = float(treble)
        self._energy = float(energy)
        self._bpm = demo_bpm

        return AudioSnapshot(
            volume=self._volume,
            bass=self._bass,
            mids=self._mids,
            treble=self._treble,
            energy=self._energy,
            beat=beat,
            bpm=self._bpm,
            demo_mode=True,
            status=self.status,
        )

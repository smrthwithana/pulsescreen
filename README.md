# plusescreen

plusescreen is a full-screen old-school MP3 visualizer for live microphone audio. It draws liquid neon lines, beat-reactive particles, and equalizer waves, then overlays the current playback state and smooth transition recommendations.

It is intentionally not a normal dashboard. The visualizer is the screen; controls and metadata sit lightly on top.

## Install

Use Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `sounddevice` cannot find an audio backend or input device, the app still opens in demo audio mode.

## Spotify Setup

1. Go to the Spotify Developer Dashboard.
2. Create an app.
3. Add this redirect URI to the app settings:

```text
http://127.0.0.1:8888/callback
```

4. Copy `.env.example` to `.env`.
5. Fill in your values:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
PLUSESCREEN_AUDIO_DEVICE=auto
```

The app uses these scopes:

```text
user-read-playback-state
user-modify-playback-state
user-read-currently-playing
```

Playback controls require a Spotify Premium account and an active playback device.

## Run

```powershell
python main.py
```

The first Spotify login may open a browser. If credentials are missing or login fails, the visualizer and recommendations still run.

## Keyboard Controls

| Key | Action |
| --- | --- |
| `1` | Liquid Flow visualizer |
| `2` | Particle Pulse visualizer |
| `3` | Equalizer Wave visualizer |
| `F` | Toggle fullscreen |
| `ESC` | Quit |
| `SPACE` | Play/pause |
| `N` | Next track |
| `B` | Previous track |
| `R` | Refresh current song |
| `Q` | Queue the best recommendation if it has a valid Spotify track URI |
| `M` | Cycle microphone/input device |
| `D` | Toggle demo visualizer mode |

## Recommendations

The MVP seeds a local SQLite database with 30 demo tracks. Recommendations score BPM similarity first, energy similarity second, and mood as a small optional adjustment. Demo tracks intentionally use placeholder Spotify URIs, so queueing is disabled until you replace a row with a real `spotify:track:...` URI.

The local database is created at:

```text
plusescreen_tracks.sqlite3
```

It is ignored by git so you can tune the dataset locally.

## Troubleshooting

### Microphone

If the app shows `DEMO`, it could not open a live microphone stream. Check that:

- An input device is connected and enabled.
- Windows privacy settings allow microphone access.
- No exclusive-mode audio app is blocking the device.
- `sounddevice` installed correctly inside the active virtual environment.

The app automatically prefers devices with `Microphone` or `Mic` in the name over `Stereo Mix`. To force a specific input, set `PLUSESCREEN_AUDIO_DEVICE` in `.env` to a device number or part of the device name:

```env
PLUSESCREEN_AUDIO_DEVICE=Microphone Array
```

To list devices:

```powershell
.\.venv\Scripts\python.exe -m sounddevice
```

If the overlay says `Live microphone` but the visualizer is not reacting, press `M` to cycle through the available input devices. Some Windows machines expose `Stereo Mix`, virtual voice changers, Bluetooth headset inputs, and the laptop microphone separately. Press `D` to force demo visualizer mode any time.

The visualizer should still animate in demo mode.

### Spotify Login

If the current song does not appear:

- Confirm `.env` exists and contains the three Spotify variables.
- Confirm the redirect URI in `.env` exactly matches the one in the Spotify Developer Dashboard.
- Start playback in your Spotify client before pressing `R`.
- Premium is required for play, pause, next, previous, and queue actions.

### First Login Cache

Spotipy stores auth tokens in `.spotipy-cache`, which is ignored by git. Delete that file if you need to switch accounts or force a fresh login.

## GitHub

This repository can be pushed to GitHub after you create a remote repository:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/plusescreen.git
git branch -M main
git push -u origin main
```

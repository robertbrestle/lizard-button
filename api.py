#!/usr/bin/env python3
"""
api.py — IoT device API server. Configuration is loaded from device.env,
which should sit alongside this script.
"""
import os
import queue
import subprocess
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent / "device.env")

API_KEY = os.environ["DEVICE_API_KEY"]
AUDIO_DIR = Path(os.environ.get("AUDIO_DIR", "/home/pi/lizard-button/audio"))
QUEUE_MAXSIZE = int(os.environ.get("AUDIO_QUEUE_MAXSIZE", "10"))
AUDIO_EXTENSIONS = {".wav", ".mp3"}

# Track map is built once at startup and cached in memory so /play stays fast.
# Use POST /api/v1/rescan to refresh it after adding files to audio/.
TRACKS = {}

# Single-consumer queue: one worker thread plays one file at a time, waiting
# for each to finish, so overlapping requests play back-to-back instead of
# layering on top of each other via ALSA's dmix.
audio_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
_stop_worker = threading.Event()
_now_playing = None
_state_lock = threading.Lock()


def scan_tracks():
    """Map each audio file's basename (no extension) to its filename.

    e.g. lizard.wav -> {"lizard": "lizard.wav"}
    """
    if not AUDIO_DIR.is_dir():
        return {}
    return {
        f.stem: f.name
        for f in sorted(AUDIO_DIR.iterdir())
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    }


def _play_command(path: Path):
    # aplay only handles WAV; mpg123 handles MP3
    if path.suffix.lower() == ".mp3":
        return ["mpg123", "-q", str(path)]
    return ["aplay", "-q", str(path)]


def _audio_worker():
    """Drain the queue one track at a time, blocking until each finishes."""
    global _now_playing
    while not _stop_worker.is_set():
        try:
            track_id, path = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            with _state_lock:
                _now_playing = track_id
            # subprocess.run blocks until playback completes — this is what
            # serializes the queue.
            subprocess.run(_play_command(path), check=False)
        except Exception as exc:  # keep the worker alive on playback failures
            print(f"Playback failed for '{track_id}': {exc}")
        finally:
            with _state_lock:
                _now_playing = None
            audio_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    global TRACKS
    TRACKS = scan_tracks()
    print(f"Loaded {len(TRACKS)} track(s) from {AUDIO_DIR}: {sorted(TRACKS)}")

    worker = threading.Thread(target=_audio_worker, name="audio-worker", daemon=True)
    worker.start()

    yield

    # --- shutdown ---
    _stop_worker.set()
    worker.join(timeout=2)


app = FastAPI(lifespan=lifespan)


def check_key(x_api_key):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class PlayRequest(BaseModel):
    track_id: str


@app.post("/api/v1/play")
def play_track(req: PlayRequest, x_api_key: str = Header(None)):
    check_key(x_api_key)
    filename = TRACKS.get(req.track_id)
    if not filename:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown track_id '{req.track_id}'. Available: {sorted(TRACKS)}",
        )
    path = AUDIO_DIR / filename
    if not path.is_file():
        raise HTTPException(
            status_code=410,
            detail=f"'{filename}' is no longer on disk. POST /api/v1/rescan to refresh.",
        )
    try:
        audio_queue.put_nowait((req.track_id, path))
    except queue.Full:
        raise HTTPException(
            status_code=503,
            detail=f"Audio queue is full ({QUEUE_MAXSIZE} items). Try again shortly.",
        )
    return {
        "status": "queued",
        "track_id": req.track_id,
        "queue_depth": audio_queue.qsize(),
    }


@app.get("/api/v1/queue")
def queue_state(x_api_key: str = Header(None)):
    check_key(x_api_key)
    with _state_lock:
        playing = _now_playing
    return {
        "now_playing": playing,
        "queue_depth": audio_queue.qsize(),
        "queue_maxsize": QUEUE_MAXSIZE,
    }


@app.post("/api/v1/rescan")
def rescan(x_api_key: str = Header(None)):
    check_key(x_api_key)
    global TRACKS
    previous = set(TRACKS)
    TRACKS = scan_tracks()
    current = set(TRACKS)
    return {
        "status": "rescanned",
        "track_count": len(TRACKS),
        "added": sorted(current - previous),
        "removed": sorted(previous - current),
        "tracks": sorted(TRACKS),
    }


@app.get("/api/v1/info")
def info(x_api_key: str = Header(None)):
    check_key(x_api_key)
    return {
        "device": "lizard-button",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/v1/status",
                "auth_required": False,
                "description": "Health check.",
            },
            {
                "method": "GET",
                "path": "/api/v1/info",
                "auth_required": True,
                "description": "List available endpoints and audio tracks.",
            },
            {
                "method": "POST",
                "path": "/api/v1/play",
                "auth_required": True,
                "description": "Queue a track for playback by track_id.",
                "body": {"track_id": "string"},
            },
            {
                "method": "GET",
                "path": "/api/v1/queue",
                "auth_required": True,
                "description": "Show what is playing and how deep the queue is.",
            },
            {
                "method": "POST",
                "path": "/api/v1/rescan",
                "auth_required": True,
                "description": "Rescan audio/ and refresh the cached track map.",
            },
        ],
        "audio_dir": str(AUDIO_DIR),
        "track_count": len(TRACKS),
        "queue_depth": audio_queue.qsize(),
        "tracks": [
            {"track_id": k, "filename": v} for k, v in sorted(TRACKS.items())
        ],
    }


@app.get("/api/v1/status")
def status():
    return {"status": "online"}

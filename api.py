#!/usr/bin/env python3
"""
api.py — IoT device API server. Configuration is loaded from device.env,
which should sit alongside this script.
"""
import json
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import RPi.GPIO as GPIO

load_dotenv(Path(__file__).resolve().parent / "device.env")

API_KEY = os.environ["DEVICE_API_KEY"]
AUDIO_DIR = os.environ.get("AUDIO_DIR", "/home/pi/audio")
TRACKS = json.loads(os.environ.get(
    "TRACKS_JSON",
    '{"lizard": "lizard.wav"}'
))

app = FastAPI()

def check_key(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

class PlayRequest(BaseModel):
    track_id: str

@app.post("/api/v1/play")
def play_track(req: PlayRequest, x_api_key: str = Header(...)):
    check_key(x_api_key)
    filename = TRACKS.get(req.track_id)
    if not filename:
        raise HTTPException(status_code=404, detail="Unknown track_id")
    subprocess.Popen(["aplay", os.path.join(AUDIO_DIR, filename)])
    return {"status": "playing", "track_id": req.track_id}

@app.get("/api/v1/status")
def status():
    return {"status": "online"}
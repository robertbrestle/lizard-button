#!/usr/bin/env python3
"""
button.py — watches the physical button and plays a fixed audio
track on each press. Configuration is loaded from device.env, which should
sit alongside this script. Runs independently of the API server, so it
still works if WiFi or the API process is down.
"""
import os
import subprocess
from pathlib import Path
from signal import pause

from dotenv import load_dotenv
from gpiozero import Button

load_dotenv(Path(__file__).resolve().parent / "device.env")

BUTTON_PIN = int(os.environ.get("BUTTON_PIN", "17"))
AUDIO_DIR = os.environ.get("AUDIO_DIR", "/home/pi/lizard-button/audio")
TRACK = os.environ.get("BUTTON_TRACK", "lizard.wav")
DEBOUNCE_SECONDS = float(os.environ.get("BUTTON_DEBOUNCE_SECONDS", "0.1"))

# pull_up=True matches the internal pull-up wiring
button = Button(BUTTON_PIN, pull_up=True, bounce_time=DEBOUNCE_SECONDS)

def play_button_track():
    subprocess.Popen(["aplay", os.path.join(AUDIO_DIR, TRACK)])

button.when_pressed = play_button_track

print("Button listener running — waiting for presses (Ctrl+C to exit)")
pause()
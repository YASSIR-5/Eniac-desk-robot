import time
from pathlib import Path

from PIL import Image, ImageSequence

import board
import digitalio
from adafruit_rgb_display import ili9341

# ---- Paths ----
BASE_DIR = Path(__file__).parent
GIF_DIR = BASE_DIR / "faces" / "Gifs"

INTRO = "intro.gif"
LOOP_GIFS = [
    "idle.gif",
    "listening.gif",
    "thinking.gif",
]

# ---- Display setup ----
spi = board.SPI()
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D24)
reset_pin = digitalio.DigitalInOut(board.D25)

cs_pin.direction = digitalio.Direction.OUTPUT
dc_pin.direction = digitalio.Direction.OUTPUT
reset_pin.direction = digitalio.Direction.OUTPUT

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

disp = ili9341.ILI9341(
    spi,
    rotation=90,
    cs=cs_pin,
    dc=dc_pin,          # fixed bug: must be dc_pin
    rst=reset_pin,
    baudrate=40000000,  # your new baudrate
)

# ---- Helpers ----
def load_gif_frames(path: Path):
    """Load all frames as resized RGB images."""
    try:
        im = Image.open(path)
    except FileNotFoundError:
        print(f"GIF not found: {path}")
        return []

    frames = []
    for frame in ImageSequence.Iterator(im):
        rgb = frame.convert("RGB")
        rgb = rgb.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
        frames.append(rgb)

    print(f"{path.name}: loaded {len(frames)} frames")
    return frames

def play_frames(frames, frame_delay_s: float, total_duration_s: float | None = None):
    """
    Play frames at a fixed speed.
    - If total_duration_s is None: play exactly one pass through frames.
    - Else: loop until total_duration_s is reached.
    """
    if not frames:
        return

    n = len(frames)

    # One-shot mode (for intro)
    if total_duration_s is None:
        for frame in frames:
            disp.image(frame)
            time.sleep(frame_delay_s)
        return

    # Looping mode (for idle/listening/thinking)
    start = time.time()
    idx = 0
    while time.time() - start < total_duration_s:
        disp.image(frames[idx])
        time.sleep(frame_delay_s)
        idx = (idx + 1) % n

# ---- Main ----
def main():
    print("GIF test: intro once, then idle/listening/thinking at fixed speed")

    # Load frames
    intro_frames = load_gif_frames(GIF_DIR / INTRO)
    loop_clips = {name: load_gif_frames(GIF_DIR / name) for name in LOOP_GIFS}

    # 1) Play intro ONCE
    print("Playing intro once...")
    play_frames(intro_frames, frame_delay_s=0.01, total_duration_s=None)

    # 2) Loop other GIFs, 5s each, normal speed
    while True:
        for name in LOOP_GIFS:
            print(f"Showing {name}...")
            play_frames(loop_clips[name], frame_delay_s=0.01, total_duration_s=9.0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")

# src/face/display_loop.py
import time
from pathlib import Path
from threading import Event, Thread

from PIL import Image, ImageSequence

import board
import digitalio
from adafruit_rgb_display import ili9341

BASE_DIR = Path(__file__).resolve().parent.parent  # src/
GIF_DIR = BASE_DIR / "faces" / "Gifs"

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

# States
STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_THINKING = "thinking"

class FaceDisplay:
    def __init__(self):
        # ---- Display setup ----
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D24)
        reset_pin = digitalio.DigitalInOut(board.D25)

        cs_pin.direction = digitalio.Direction.OUTPUT
        dc_pin.direction = digitalio.Direction.OUTPUT
        reset_pin.direction = digitalio.Direction.OUTPUT

        self.disp = ili9341.ILI9341(
            spi,
            rotation=90,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=40000000,
        )

        # Preload GIFs
        self.frames = {
            STATE_IDLE:       self._load_gif_frames(GIF_DIR / "idle.gif"),
            STATE_LISTENING:  self._load_gif_frames(GIF_DIR / "listening.gif"),
            STATE_THINKING:   self._load_gif_frames(GIF_DIR / "thinking.gif"),
        }

        self.state = STATE_IDLE
        self._stop = Event()
        self._thread: Thread | None = None

    def _load_gif_frames(self, path: Path):
        from PIL import Image
        try:
            im = Image.open(path)
        except FileNotFoundError:
            print(f"GIF not found: {path}")
            return []

        frames = []
        for frame in ImageSequence.Iterator(im):
            rgb = frame.convert("RGB").resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
            frames.append(rgb)
        print(f"{path.name}: loaded {len(frames)} frames")
        return frames

    def set_state(self, new_state: str):
        self.state = new_state

    def start(self, frame_delay_s: float = 0.05):
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, args=(frame_delay_s,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run(self, frame_delay_s: float):
        idx = 0
        while not self._stop.is_set():
            frames = self.frames.get(self.state) or []
            if not frames:
                time.sleep(0.1)
                continue

            frame = frames[idx % len(frames)]
            self.disp.image(frame)
            idx = (idx + 1) % len(frames)
            time.sleep(frame_delay_s)

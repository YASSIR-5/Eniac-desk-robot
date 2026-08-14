import random
import threading
import time
from pathlib import Path
from threading import Event, Lock, Thread

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import ili9341


FACE_DIR = Path(__file__).resolve().parent / "Faces_States"

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

STATE_LOADING = "loading"
STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_OK_WINK = "ok_wink"
STATE_THINKING = "thinking"
STATE_SPEAKING = "speaking"
STATE_ERROR = "error"
STATE_JUDGE = "judge"
STATE_SLEEPING = "sleeping"
STATE_TURNING_OFF = "turning_off"


BLINK_MIN_S = 2.5
BLINK_MAX_S = 4.5

SLEEP_MIN_S = 30.0
SLEEP_MAX_S = 60.0

SELF_WAKE_MIN_S = 20.0
SELF_WAKE_MAX_S = 60.0

BLINK_DURATION_S = 0.1
OK_WINK_DURATION_S = 1.0
ERROR_DURATION_S = 1.2
THINKING_FRAME_S = 0.45
SPEAKING_FRAME_S = 0.3
LOADING_FRAME_S = 0.25


class FaceDisplay:
    def __init__(self, on_sleep=None, on_boot=None):
        self.spi_lock = Lock()
        self._lock = Lock()

        self.on_sleep = on_sleep
        self.on_boot = on_boot

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
            baudrate=60000000,
        )

        self.frames = {
            STATE_IDLE: self._load_pngs(["Idle.png"]),
            STATE_LISTENING: self._load_pngs(["Listening.png"]),
            STATE_OK_WINK: self._load_pngs(["ok-wink.png"]),
            STATE_THINKING: self._load_pngs(["thinkingA.png", "thinkingB.png"]),
            STATE_SPEAKING: self._load_pngs(["SpeakingA.png", "SpeakingB.png"]),
            STATE_ERROR: self._load_pngs(["Error.png"]),
            STATE_JUDGE: self._load_pngs(["Judge.png"]),
            STATE_SLEEPING: self._load_pngs(["Sleeping.png"]),
            "blink": self._load_pngs(["Blink.png"]),
            STATE_TURNING_OFF: self._load_pngs(["Turn_Off.png"]),
        }

        self.loading_frames = self._build_loading_frames()

        self.state = STATE_LOADING
        self.current_text = None
        self._state_started_at = time.monotonic()
        self._last_activity = time.monotonic()
        self._next_blink_at = self._new_blink_time()
        self._sleep_at = self._new_sleep_time()
        self._self_wake_at = None

        self._frame_index = 0
        self._stop = Event()
        self._thread = None

    def _load_pngs(self, names):
        frames = []

        for name in names:
            path = FACE_DIR / name

            try:
                frame = Image.open(path).convert("RGB")
                frame = frame.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
                frames.append(frame)
                print(f"[Face] Loaded {path.name}")
            except FileNotFoundError:
                print(f"[Face] Missing: {path}")

        return frames

    def _build_loading_frames(self):
        sequence = [
            STATE_IDLE,
            STATE_LISTENING,
            STATE_OK_WINK,
            STATE_THINKING,
            STATE_SPEAKING,
            STATE_ERROR,
            STATE_JUDGE,
            STATE_SLEEPING,
            STATE_IDLE,
        ]

        thumbnails = []

        for state in sequence:
            frames = self.frames.get(state) or []
            if not frames:
                continue

            thumbnail = frames[0].resize((100, 75))
            thumbnails.append(thumbnail)

        if not thumbnails:
            return []

        strip_width = len(thumbnails) * 100
        strip = Image.new("RGB", (strip_width, DISPLAY_HEIGHT), "#2c4a60")

        for index, thumbnail in enumerate(thumbnails):
            strip.paste(thumbnail, (index * 100, 82))

        max_offset = max(0, strip_width - DISPLAY_WIDTH)
        offsets = list(range(0, max_offset + 1, 80))

        if offsets[-1] != max_offset:
            offsets.append(max_offset)

        frames = []

        for offset in offsets:
            canvas = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), "#2c4a60")
            canvas.paste(strip, (-offset, 0))
            frames.append(canvas)

        return frames

    def _new_blink_time(self):
        return time.monotonic() + random.uniform(BLINK_MIN_S, BLINK_MAX_S)

    def _new_sleep_time(self):
        return time.monotonic() + random.uniform(SLEEP_MIN_S, SLEEP_MAX_S)

    def _new_self_wake_time(self):
        return time.monotonic() + random.uniform(
            SELF_WAKE_MIN_S,
            SELF_WAKE_MAX_S,
        )

    def _draw(self, frame):
        with self.spi_lock:
            try:
                self.disp.image(frame)
            except Exception as e:
                print(f"[Display error] {e}")

    def _run_callback(self, callback):
        if callback is None:
            return

        threading.Thread(target=callback, daemon=True).start()

    def set_state(self, new_state, text=None):
        with self._lock:
            state_changed = new_state != self.state

            self.state = new_state
            self.current_text = text
            self._state_started_at = time.monotonic()

            if state_changed:
                self._frame_index = 0

            if new_state == STATE_IDLE:
                self._last_activity = time.monotonic()
                self._next_blink_at = self._new_blink_time()
                self._sleep_at = self._new_sleep_time()
                self._self_wake_at = None

            elif new_state == STATE_SLEEPING:
                self._self_wake_at = self._new_self_wake_time()

    def get_state(self):
        with self._lock:
            return self.state

    def show_text_reply(self, text):
        self.set_state(STATE_SPEAKING, text=text)

    def show_text_only(self, text):
        self.set_state(STATE_IDLE, text=text)

    def clear_text(self):
        with self._lock:
            self.current_text = None

    def show_error(self, text=None):
        self.set_state(STATE_ERROR, text=text)

    def start(self, frame_delay_s=None):
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _play_loading_intro(self):
        self._run_callback(self.on_boot)

        for frame in self.loading_frames:
            if self._stop.is_set():
                return

            self._draw(frame)
            time.sleep(LOADING_FRAME_S)

        self.set_state(STATE_IDLE)

    def _state_delay(self, state):
        if state == STATE_THINKING:
            return THINKING_FRAME_S

        if state == STATE_SPEAKING:
            return SPEAKING_FRAME_S

        return 0.05

    def _run(self):
        self._play_loading_intro()

        while not self._stop.is_set():
            with self._lock:
                state = self.state
                text = self.current_text
                now = time.monotonic()
                state_age = now - self._state_started_at
                next_blink_at = self._next_blink_at
                sleep_at = self._sleep_at
                self_wake_at = self._self_wake_at

            if state == STATE_ERROR and state_age >= ERROR_DURATION_S:
                self.set_state(STATE_IDLE)
                continue

            

            if (
                state == STATE_SLEEPING
                and self_wake_at is not None
                and now >= self_wake_at
            ):
                self.set_state(STATE_IDLE)
                continue

            if (
                state == STATE_IDLE
                and text is None
                and now >= sleep_at
            ):
                self.set_state(STATE_SLEEPING)
                self._run_callback(self.on_sleep)
                continue

            is_blinking = (
                state == STATE_IDLE
                and text is None
                and time.monotonic() >= next_blink_at
            )

            if is_blinking:
                blink_frames = self.frames.get("blink") or []

                if blink_frames:
                    self._draw(blink_frames[0].copy())

                time.sleep(BLINK_DURATION_S)

                with self._lock:
                    self._next_blink_at = self._new_blink_time()

                continue

            frames = self.frames.get(state) or self.frames.get(STATE_IDLE) or []

            if not frames:
                time.sleep(0.1)
                continue

            frame = frames[self._frame_index % len(frames)].copy()
            self._frame_index = (self._frame_index + 1) % len(frames)

            if text:
                frame = self._overlay_text(frame, text)

            self._draw(frame)
            time.sleep(self._state_delay(state))

    def _overlay_text(self, image, text):
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                24,
            )
        except Exception:
            font = ImageFont.load_default()

        margin = 16
        max_width = DISPLAY_WIDTH - (margin * 2)
        text_top = 150

        lines = []
        current_line = ""

        for word in text.split():
            candidate = f"{current_line} {word}".strip()
            bbox = font.getbbox(candidate)
            candidate_width = bbox[2] - bbox[0]

            if candidate_width <= max_width:
                current_line = candidate
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        lines = lines[:3]

        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 4
        y = text_top

        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            x = (DISPLAY_WIDTH - line_width) // 2

            draw.text(
                (x, y),
                line,
                font=font,
                fill="#86b499",
            )

            y += line_height

        return image


if __name__ == "__main__":
    display = FaceDisplay()
    display.start()

    print("Face display test running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        display.stop()
        print("\nStopped.")
import time
from pathlib import Path
from threading import Event, Thread, Lock
from PIL import Image, ImageSequence, ImageDraw, ImageFont
import board
import digitalio
from adafruit_rgb_display import ili9341

BASE_DIR = Path(__file__).resolve().parent.parent
GIF_DIR = BASE_DIR / "faces" / "Gifs"

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_THINKING = "thinking"
STATE_SPEAKING = "speaking"
STATE_ERROR = "error"
STATE_WINK = "wink"

IDLE_TIMEOUT_S = 7.0  # seconds of silence before a wink triggers


class FaceDisplay:
    def __init__(self):
        self.spi_lock = Lock()

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
            STATE_IDLE: self._load_gif_frames(GIF_DIR / "idle.gif", skip=1),
            STATE_LISTENING: self._load_gif_frames(GIF_DIR / "listening.gif"),
            STATE_THINKING: self._load_gif_frames(GIF_DIR / "thinking.gif"),
            STATE_SPEAKING: self._load_speaking_pngs(),
            STATE_ERROR: self._load_error_pngs(),
            STATE_WINK: self._load_gif_frames(GIF_DIR / "wink.gif", skip=2),
        }

        self.state = STATE_IDLE
        self.current_text = None
        self._stop = Event()
        self._thread = None
        self._lock = Lock()
        self._last_activity = time.time()

    def _load_gif_frames(self, path: Path, skip: int = 1):
        try:
            im = Image.open(path)
        except FileNotFoundError:
            print(f"GIF not found: {path}")
            return []
        frames = []
        for i, frame in enumerate(ImageSequence.Iterator(im)):
            if i % skip != 0:
                continue
            rgb = frame.convert("RGB").resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
            frames.append(rgb)
        print(f"{path.name}: loaded {len(frames)} frames (skip={skip})")
        return frames

    def _load_speaking_pngs(self):
        paths = [GIF_DIR / "speaking_a.png", GIF_DIR / "speaking_b.png"]
        return self._load_png_list(paths)

    def _load_error_pngs(self):
        paths = [GIF_DIR / "error.png"]
        return self._load_png_list(paths)

    def _load_png_list(self, paths):
        frames = []
        for p in paths:
            try:
                img = Image.open(p).convert("RGB").resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
                frames.append(img)
                print(f"{p.name}: loaded")
            except FileNotFoundError:
                print(f"PNG not found: {p}")
        return frames

    def set_state(self, new_state: str, text: str = None):
        """Set robot state and optional text to overlay. Thread-safe."""
        with self._lock:
            self.state = new_state
            self.current_text = text
            self._last_activity = time.time()

    def show_text_reply(self, text: str):
        """Call this to show speaking state with reply text on screen."""
        self.set_state(STATE_SPEAKING, text=text)

    def show_error(self, text: str = None):
        """Call this on errors to show the error face."""
        self.set_state(STATE_ERROR, text=text)

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
        wink_idx = 0
        winking = False

        while not self._stop.is_set():
            with self._lock:
                state = self.state
                text = self.current_text
                idle_elapsed = time.time() - self._last_activity

            if winking and state != STATE_IDLE:
                winking = False

            wink_frames = self.frames.get(STATE_WINK) or []

            if state == STATE_IDLE and not winking and idle_elapsed >= IDLE_TIMEOUT_S:
                winking = True
                wink_idx = 0

            if winking:
                if not wink_frames or wink_idx >= len(wink_frames):
                    winking = False
                    with self._lock:
                        self._last_activity = time.time()
                else:
                    state = STATE_WINK

            frames = self.frames.get(state) or self.frames.get(STATE_IDLE) or []
            if not frames:
                time.sleep(0.1)
                continue

            if state == STATE_WINK:
                frame = frames[wink_idx % len(frames)].copy()
                wink_idx += 1
            else:
                frame = frames[idx % len(frames)].copy()
                idx = (idx + 1) % len(frames)

            if text:
                frame = self._overlay_text(frame, text)

            with self.spi_lock:
                try:
                    self.disp.image(frame)
                except Exception as e:
                    print(f"Display error: {e}")

            if state == STATE_SPEAKING:
                delay = 0.3
            elif state == STATE_WINK:
                delay = 0.03
            else:
                delay = frame_delay_s
            time.sleep(delay)

    def _overlay_text(self, img, text):
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        except Exception:
            font = ImageFont.load_default()

        margin = 20
        text_box_width = DISPLAY_WIDTH - 2 * margin
        text_box_top = 160

        lines = []
        words = text.split()
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word).strip()
            bbox = font.getbbox(test_line)
            if (bbox[2] - bbox[0]) <= text_box_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 4
        y = text_box_top
        for line in lines:
            bbox = font.getbbox(line)
            x = (DISPLAY_WIDTH - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, font=font, fill="#86b499")
            y += line_height

        return img
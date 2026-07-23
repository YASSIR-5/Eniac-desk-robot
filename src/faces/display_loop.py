import time
from pathlib import Path
from threading import Event, Thread, Lock
from PIL import Image, ImageSequence, ImageDraw, ImageFont
import board
import digitalio
from adafruit_rgb_display import ili9341

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
GIF_DIR = BASE_DIR / "faces" / "Gifs"

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

# State constants
STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_THINKING = "thinking"
STATE_SPEAKING = "speaking"  # New state for text output

# Reply box colors
FRAME_COLOR = (134, 180, 153)   # custom frame color
INNER_COLOR = (255, 255, 255)   # white inside
TEXT_COLOR = (0, 0, 0)          # black text


class FaceDisplay:
    def __init__(self):
        # ---- SPI Lock to prevent threading collisions ----
        self.spi_lock = Lock()

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
            baudrate=60000000,
        )

        # Preload GIF frames
        self.frames = {
            STATE_IDLE: self._load_gif_frames(GIF_DIR / "idle.gif"),
            STATE_LISTENING: self._load_gif_frames(GIF_DIR / "listening.gif"),
            STATE_THINKING: self._load_gif_frames(GIF_DIR / "thinking.gif"),
        }

        self.state = STATE_IDLE
        self.current_text = None
        self._stop = Event()
        self._thread = None

        # Cache for rendered text box (avoids re-rendering every frame)
        self._cached_text = None
        self._cached_box_img = None

    def _load_gif_frames(self, path: Path):
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

    def set_state(self, new_state: str, text: str = None):
        """Set robot state and optional text to overlay."""
        self.state = new_state
        self.current_text = text
        if text is None:
            self._cached_text = None
            self._cached_box_img = None

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
            frames = self.frames.get(self.state) or self.frames.get(STATE_IDLE) or []
            if not frames:
                time.sleep(0.1)
                continue

            frame = frames[idx % len(frames)].copy()

            if self.current_text:
                if self.current_text != self._cached_text:
                    self._cached_box_img = self._draw_reply_box(frame.copy(), self.current_text)
                    self._cached_text = self.current_text
                frame = self._cached_box_img.copy()

            with self.spi_lock:
                try:
                    self.disp.image(frame)
                except Exception as e:
                    print(f"Display error: {e}")

            idx = (idx + 1) % len(frames)
            time.sleep(frame_delay_s)

    def _draw_reply_box(self, img, text):
        """
        Draws a reply frame that dynamically fits text:
        shrinks font and grows box height as needed, up to screen limits.
        """
        draw = ImageDraw.Draw(img)

        box_margin = 10
        box_left = box_margin
        box_right = DISPLAY_WIDTH - box_margin
        border_thickness = 6
        text_margin = 24
        max_box_top = 40
        min_box_top = 170

        text_box_width = (box_right - border_thickness - text_margin) - (
            box_left + border_thickness + text_margin // 2
        )

        font_sizes = [40, 32, 26, 22, 18]
        chosen_font = None
        chosen_lines = None
        chosen_box_top = None
        font = None
        lines = []
        line_height = 20

        for size in font_sizes:
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
                )
            except Exception:
                font = ImageFont.load_default()

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
            if current_line:
                lines.append(current_line)

            line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 6
            total_h = line_height * len(lines) + 2 * (border_thickness + text_margin // 2)

            box_top = DISPLAY_HEIGHT - box_margin - total_h
            box_top = max(max_box_top, min(box_top, min_box_top))

            available_h = (DISPLAY_HEIGHT - box_margin) - box_top
            if total_h <= available_h:
                chosen_font = font
                chosen_lines = lines
                chosen_box_top = box_top
                break

        if chosen_font is None:
            chosen_font = font
            max_lines = max(1, (DISPLAY_HEIGHT - box_margin - max_box_top) // line_height)
            chosen_lines = lines[:max_lines]
            if chosen_lines:
                chosen_lines[-1] = chosen_lines[-1][:20] + "..."
            chosen_box_top = max_box_top

        box_top = chosen_box_top
        box_bottom = DISPLAY_HEIGHT - box_margin

        draw.rectangle([box_left, box_top, box_right, box_bottom], fill=FRAME_COLOR)

        draw.rectangle(
            [
                box_left + border_thickness,
                box_top + border_thickness,
                box_right - border_thickness,
                box_bottom - border_thickness,
            ],
            fill=INNER_COLOR,
        )

        line_height = chosen_font.getbbox("Ay")[3] - chosen_font.getbbox("Ay")[1] + 6
        y = box_top + border_thickness + 4
        for line in chosen_lines:
            bbox = chosen_font.getbbox(line)
            line_w = bbox[2] - bbox[0]
            x = box_left + border_thickness + text_margin // 2 + max(0, (text_box_width - line_w) // 2)
            draw.text((x, y), line, font=chosen_font, fill=TEXT_COLOR)
            y += line_height

        return img

    def show_text_reply(self, text: str):
        """Public method to update the text being displayed."""
        self.set_state(STATE_IDLE, text=text)
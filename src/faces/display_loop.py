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

        # Lower baudrate slightly for better stability on Pi 3A+ with long wires
        self.disp = ili9341.ILI9341(
            spi,
            rotation=90,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000, # 24MHz is more stable than 40MHz for many displays
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

    def start(self, frame_delay_s: float = 0.05): # Slightly slower FPS for stability
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
            # Get current frames for the state
            frames = self.frames.get(self.state) or self.frames.get(STATE_IDLE) or []
            if not frames:
                time.sleep(0.1)
                continue

            frame = frames[idx % len(frames)].copy()
            
            # If there is text to display, overlay it on the current frame
            if self.current_text:
                frame = self._overlay_text(frame, self.current_text)

            # Use lock to ensure only one thread writes to SPI at a time
            with self.spi_lock:
                try:
                    self.disp.image(frame)
                except Exception as e:
                    print(f"Display error: {e}")

            idx = (idx + 1) % len(frames)
            time.sleep(frame_delay_s)

    def _overlay_text(self, img, text):
        """Draws wrapped text on top of an image frame."""
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        except:
            font = ImageFont.load_default()

        margin = 20
        text_box_width = DISPLAY_WIDTH - 2 * margin
        text_box_top = 160 # Positioned below the eyes

        # Word wrap
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

        # Draw semi-transparent background for readability (Optional)
        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 4
        total_h = line_height * len(lines)
        # draw.rectangle([margin-5, text_box_top-5, DISPLAY_WIDTH-margin+5, text_box_top+total_h+5], fill=(43, 72, 93, 180))

        # Draw text
        y = text_box_top
        for line in lines:
            # Center text horizontally
            bbox = font.getbbox(line)
            x = (DISPLAY_WIDTH - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, font=font, fill="#86b499")
            y += line_height
            
        return img

    def show_text_reply(self, text: str):
        """Public method to update the text being displayed."""
        self.set_state(STATE_IDLE, text=text)

import time
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from PIL import Image

import board
import digitalio
from adafruit_rgb_display import ili9341

import openwakeword
from openwakeword.model import Model

# ---- Paths ----
BASE_DIR = Path(__file__).parent
FACES_DIR = BASE_DIR / "faces"
MODEL_PATH = BASE_DIR / "WakeWord" / "hey_eniac.onnx"

# ---- Wake word model ----
model = Model(
    wakeword_model_paths=[str(MODEL_PATH)]
)

MIC_RATE = 48000
TARGET_RATE = 16000
CHUNK_MIC = 3840  # 80ms at 48kHz, downsamples to 1280 at 16kHz
last_detected = 0
COOLDOWN = 2

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
    dc=dc_pin,
    rst=reset_pin,
    baudrate=24000000,
)

# ---- Load face images ----
def load_face(name):
    img = Image.open(FACES_DIR / name).convert("RGB")
    img = img.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
    return img

idle_img = load_face("idle.png")
blank_img = load_face("blink.png")
listening1_img = load_face("listening.png")
listening2_img = load_face("listening2.png")

# ---- State ----
is_listening = False
stop_flag = False

# ---- Face animation thread ----
def face_loop():
    global is_listening
    listening_start = 0

    while not stop_flag:
        if is_listening:
            disp.image(listening1_img)
            time.sleep(0.7)
            if not is_listening:
                continue
            disp.image(listening2_img)
            time.sleep(0.7)

            if time.time() - listening_start > 10:
                is_listening = False
        else:
            # Idle: hold eyes open, then quick blink
            disp.image(idle_img)
            time.sleep(5.0)          # eyes open for 5s

            disp.image(blank_img)    # closed/blink frame
            time.sleep(0.2)          # blink very fast

            # go back to idle; loop repeats
def trigger_listening():
    global is_listening, listening_start
    is_listening = True
    globals()["listening_start"] = time.time()

# ---- Audio callback ----
def audio_callback(indata, frames, time_info, status):
    global last_detected
    audio_np = np.frombuffer(indata, dtype=np.int16)

    # Downsample 48000 -> 16000
    audio_16k = resample_poly(audio_np, TARGET_RATE, MIC_RATE).astype(np.int16)

    prediction = model.predict(audio_16k)
    for key, value in prediction.items():
        if value > 0.05:
            now = time.time()
            if now - last_detected > COOLDOWN:
                print(f"✅ Wake word detected! (confidence: {value:.2f})")
                last_detected = now
                trigger_listening()

# ---- Audio thread ----
def start_audio():
    with sd.RawInputStream(
        samplerate=MIC_RATE,
        blocksize=CHUNK_MIC,
        dtype='int16',
        channels=1,
        device=None,  # uses default ALSA input; see note below
        callback=audio_callback
    ):
        print("Listening... say 'Hey ENIAC'")
        while not stop_flag:
            sd.sleep(100)

# ---- Run ----
audio_thread = threading.Thread(target=start_audio, daemon=True)
audio_thread.start()

try:
    face_loop()
except KeyboardInterrupt:
    stop_flag = True
    print("\nStopped.")

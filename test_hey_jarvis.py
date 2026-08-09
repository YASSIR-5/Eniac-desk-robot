import queue
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from openwakeword.model import Model

MODEL_PATH = Path.home() / "eniac" / "WakeWord" / "hey_jarvis_v0.1.onnx"

INPUT_RATE = 48000
CHUNK = 3840
THRESHOLD = 0.5
COOLDOWN_S = 2.0

model = Model(
    wakeword_model_paths=[str(MODEL_PATH)],
)

audio_queue = queue.Queue(maxsize=25)
last_detected = 0.0


def callback(indata, frames, time_info, status):
    try:
        audio_queue.put_nowait(bytes(indata))
    except queue.Full:
        pass


print("Listening for: Hey Jarvis")
print("Press Ctrl+C to stop.")

try:
    with sd.RawInputStream(
        samplerate=INPUT_RATE,
        blocksize=CHUNK,
        dtype="int16",
        channels=1,
        device=None,
        latency="high",
        callback=callback,
    ):
        while True:
            raw_audio = audio_queue.get()

            audio_48k = np.frombuffer(raw_audio, dtype=np.int16)
            audio_16k = resample_poly(audio_48k, 1, 3).astype(np.int16)

            scores = model.predict(audio_16k)
            score = max(scores.values(), default=0.0)

            if score >= THRESHOLD and time.time() - last_detected >= COOLDOWN_S:
                last_detected = time.time()
                print(f"\nHEY JARVIS DETECTED — score: {score:.3f}\n")

except KeyboardInterrupt:
    print("\nStopped.")
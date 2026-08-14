import queue
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from openwakeword.model import Model


INPUT_RATE = 48000
WAKE_RATE = 16000
CHUNK = 3840
THRESHOLD = 0.50
COOLDOWN_S = 2.0

DEFAULT_MODEL_PATH = (
    Path.home() / "eniac" / "WakeWord" / "hey_jarvis_v0.1.onnx"
)


class WakeWordListener:
    def __init__(
        self,
        on_detected,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        threshold: float = THRESHOLD,
        cooldown_s: float = COOLDOWN_S,
        device=None,
    ):
        self.on_detected = on_detected
        self.model_path = Path(model_path)
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self.device = device

        self.model = None
        

        self._audio_queue = queue.Queue(maxsize=25)
        self._stop_event = threading.Event()
        self._thread = None
        self._last_detected = 0.0

    def _create_fresh_model(self):
        
        return Model(
            wakeword_model_paths=[str(self.model_path)],
    )
    
    def _callback(self, indata, frames, time_info, status):
        try:
            self._audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            pass

    def _run(self):
        try:
            with sd.RawInputStream(
                samplerate=INPUT_RATE,
                blocksize=CHUNK,
                dtype="int16",
                channels=1,
                device=self.device,
                latency="high",
                callback=self._callback,
            ):
                while not self._stop_event.is_set():
                    try:
                        raw_audio = self._audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    audio_48k = np.frombuffer(raw_audio, dtype=np.int16)
                    audio_16k = resample_poly(
                        audio_48k,
                        WAKE_RATE,
                        INPUT_RATE,
                    ).astype(np.int16)

                    scores = self.model.predict(audio_16k)
                    score = max(scores.values(), default=0.0)

                    now = time.time()
                    if (
                        score >= self.threshold
                        and now - self._last_detected >= self.cooldown_s
                    ):
                        self._last_detected = now
                        self._stop_event.set()

                        threading.Thread(
                            target=self.on_detected,
                            args=(score,),
                            daemon=True,
                        ).start()

        except Exception as e:
            print(f"[Wake word error] {e}")

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        _t0 = time.time()
        print(f"[TIMING] wake_word.start(): about to load model: {_t0:.3f}")
        try:
            self.model = self._create_fresh_model()
        except Exception as e:
            print(f"[Wake word error] Could not load model: {e}")
            return
        _t1 = time.time()
        print(f"[TIMING] wake_word.start(): model loaded in {_t1 - _t0:.3f}s (finished at {_t1:.3f})")

        self._last_detected = 0.0
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[Wake word] Listening for: Hey Jarvis")

    def stop(self):
        self._stop_event.set()

        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)

        self._thread = None

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()


if __name__ == "__main__":
    def detected(score):
        print(f"\nHEY JARVIS DETECTED — score: {score:.3f}\n")

    listener = WakeWordListener(on_detected=detected)
    listener.start()

    print("Press Ctrl+C to stop.")

    try:
        while listener.is_running():
            time.sleep(0.1)
    except KeyboardInterrupt:
        listener.stop()
        print("\nStopped.")
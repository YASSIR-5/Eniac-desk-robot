import threading
import time

import numpy as np
import sounddevice as sd


RATE = 48000
CHUNK = 1024

ENERGY_THRESHOLD = 0.004
MIN_ACTIVE_BLOCKS = 3
MIN_SILENT_BLOCKS = 50
PRE_BUFFER_MAX = 40

NO_SPEECH_TIMEOUT_S = 7.0


class MicVAD:
    """
    Records one request after ENIAC wakes.

    - Waits up to 7 seconds for speech.
    - Starts recording when speech is detected.
    - Stops after MIN_SILENT_BLOCKS.
    - Releases the microphone after one utterance.
    """

    def __init__(
        self,
        on_speech_start=None,
        on_speech_end=None,
        on_utterance=None,
        on_timeout=None,
        device=None,
    ):
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_utterance = on_utterance
        self.on_timeout = on_timeout
        self.device = device

        self._thread = None
        self._stop_event = threading.Event()

        self._speaking = False
        self._finished = False
        self._active_count = 0
        self._silent_count = 0

        self._pre_buffer = []
        self._buffer = []
        self._started_at = 0.0

    def _callback(self, indata, frames, time_info, status):
        if self._finished:
            return

        audio = np.frombuffer(indata, dtype=np.int16).astype(np.float32)
        audio /= 32768.0

        energy = np.sqrt(np.mean(audio ** 2))

        if energy > ENERGY_THRESHOLD:
            self._active_count += 1
            self._silent_count = 0
        else:
            self._silent_count += 1
            self._active_count = 0

        if not self._speaking:
            self._pre_buffer.append(audio.copy())

            if len(self._pre_buffer) > PRE_BUFFER_MAX:
                self._pre_buffer.pop(0)

            if self._active_count >= MIN_ACTIVE_BLOCKS:
                self._speaking = True
                self._silent_count = 0
                self._buffer = list(self._pre_buffer)
                self._pre_buffer = []

                if self.on_speech_start:
                    self.on_speech_start()

            return

        self._buffer.append(audio.copy())

        if self._silent_count < MIN_SILENT_BLOCKS:
            return

        self._finished = True
        self._speaking = False
        self._stop_event.set()

        utterance = np.concatenate(self._buffer) if self._buffer else None
        self._buffer = []

        if self.on_speech_end:
            self.on_speech_end()

        if self.on_utterance and utterance is not None:
            threading.Thread(
                target=self.on_utterance,
                args=(utterance,),
                daemon=True,
            ).start()

    def _run(self):
        try:
            with sd.RawInputStream(
                samplerate=RATE,
                blocksize=CHUNK,
                dtype="int16",
                channels=1,
                device=self.device,
                latency="high",
                callback=self._callback,
            ):
                self._started_at = time.monotonic()

                while not self._stop_event.is_set():
                    no_speech_yet = not self._speaking
                    elapsed = time.monotonic() - self._started_at

                    if no_speech_yet and elapsed >= NO_SPEECH_TIMEOUT_S:
                        self._finished = True
                        self._stop_event.set()

                        if self.on_timeout:
                            threading.Thread(
                                target=self.on_timeout,
                                daemon=True,
                            ).start()

                        break

                    sd.sleep(50)

        except Exception as e:
            print(f"[Mic error] {e}")

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._speaking = False
        self._finished = False
        self._active_count = 0
        self._silent_count = 0
        self._pre_buffer = []
        self._buffer = []

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        print("[Mic] Waiting up to 7 seconds for a request.")

    def stop(self):
        self._stop_event.set()

        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)

        self._thread = None
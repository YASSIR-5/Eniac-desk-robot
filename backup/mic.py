# src/audio/mic.py
import time
# src/audio/mic.py
import threading
import numpy as np
import sounddevice as sd

# Audio settings
RATE = 48000          # Must match SAMPLE_RATE in main.py
CHUNK = 1024          # frames per block

# VAD tuning
ENERGY_THRESHOLD = 0.004   # adjust if needed
MIN_ACTIVE_BLOCKS = 8      # loud blocks before "speech start"
MIN_SILENT_BLOCKS = 25     # quiet blocks before "speech end"


class MicVAD:
    """
    Simple energy-based VAD:
    - on_speech_start(): called when voice activity begins
    - on_speech_end():   called when voice activity ends
    - on_utterance(audio_np): called once per utterance with full audio
    """

    def __init__(self, on_speech_start, on_speech_end, on_utterance=None, device=None):
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_utterance = on_utterance
        self.device = device

        self._thread = None
        self._stop_flag = False

        self._speaking = False
        self._active_count = 0
        self._silent_count = 0

        self._buffer = []  # stores audio blocks for current utterance

    def _callback(self, indata, frames, time_info, status):
        if status:
            # print("Status:", status)  # optional
            pass

        # int16 -> float32 in [-1, 1]
        audio = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768.0

        # append to buffer
        self._buffer.append(audio.copy())

        # RMS energy
        energy = np.sqrt(np.mean(audio ** 2))

        # VAD state tracking
        if energy > ENERGY_THRESHOLD:
            self._active_count += 1
            self._silent_count = 0
        else:
            self._silent_count += 1
            self._active_count = 0

        # START of speech
        if not self._speaking and self._active_count >= MIN_ACTIVE_BLOCKS:
            self._speaking = True
            self._silent_count = 0
            self._buffer = []  # reset buffer at speech start
            if self.on_speech_start:
                self.on_speech_start()

        # END of speech
        elif self._speaking and self._silent_count >= MIN_SILENT_BLOCKS:
            self._speaking = False
            self._active_count = 0

            # concatenate buffered audio
            if self._buffer:
                utterance = np.concatenate(self._buffer)
            else:
                utterance = None
            self._buffer = []

            if self.on_speech_end:
                self.on_speech_end()

            if self.on_utterance and utterance is not None:
                self.on_utterance(utterance)

    def _run(self):
        with sd.RawInputStream(
            samplerate=RATE,
            blocksize=CHUNK,
            dtype="int16",
            channels=1,
            device=self.device,
            callback=self._callback,
        ):
            while not self._stop_flag:
                sd.sleep(50)

    def start(self):
        if self._thread is not None:
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag = True
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None

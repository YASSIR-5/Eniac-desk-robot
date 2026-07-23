# src/audio/mic.py
import threading
import numpy as np
import sounddevice as sd

# Audio settings
RATE = 48000          # Must match SAMPLE_RATE in main.py
CHUNK = 1024          # frames per block

# VAD tuning
ENERGY_THRESHOLD = 0.008   # raised: reduces false triggers from background noise
MIN_ACTIVE_BLOCKS = 5      # lowered: reacts faster to speech start
MIN_SILENT_BLOCKS = 50     # raised: waits longer before cutting off end of sentence

PRE_BUFFER_MAX = 20        # ~0.4s of audio kept before speech starts


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

        self._pre_buffer = []   # rolling window before speech starts (~0.4s)
        self._buffer = []       # active utterance audio

    def _callback(self, indata, frames, time_info, status):
        # int16 -> float32 in [-1, 1]
        audio = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768.0

        # RMS energy
        energy = np.sqrt(np.mean(audio ** 2))

        if energy > ENERGY_THRESHOLD:
            self._active_count += 1
            self._silent_count = 0
        else:
            self._silent_count += 1
            self._active_count = 0

        if not self._speaking:
            # Keep a rolling pre-speech window so first words aren't lost
            self._pre_buffer.append(audio.copy())
            if len(self._pre_buffer) > PRE_BUFFER_MAX:
                self._pre_buffer.pop(0)

            # START of speech
            if self._active_count >= MIN_ACTIVE_BLOCKS:
                self._speaking = True
                self._silent_count = 0
                # Seed buffer with pre-speech audio so first syllable is captured
                self._buffer = list(self._pre_buffer)
                self._pre_buffer = []
                if self.on_speech_start:
                    self.on_speech_start()

        else:
            # Accumulate speech audio
            self._buffer.append(audio.copy())

            # END of speech
            if self._silent_count >= MIN_SILENT_BLOCKS:
                self._speaking = False
                self._active_count = 0

                utterance = np.concatenate(self._buffer) if self._buffer else None
                self._buffer = []

                if self.on_speech_end:
                    self.on_speech_end()

                # Offload to a thread — never block the audio callback
                if self.on_utterance and utterance is not None:
                    threading.Thread(
                        target=self.on_utterance,
                        args=(utterance,),
                        daemon=True,
                    ).start()

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

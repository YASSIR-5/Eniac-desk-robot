import threading
import time
from typing import Optional

import numpy as np

from src.audio.mic import MicVAD, RATE
from src.audio.tts import play_bootup, play_sleep, play_soft, speak
from src.audio.wake_word import WakeWordListener
from src.brain.groq_client import generate_reply, transcribe_audio_numpy
from src.faces.display_loop import (
    FaceDisplay,
    STATE_ERROR,
    STATE_IDLE,
    STATE_JUDGE,
    STATE_LISTENING,
    STATE_OK_WINK,
    STATE_SPEAKING,
    STATE_THINKING,
)


SAMPLE_RATE = RATE

JUDGE_DURATION_S = 2.0
OK_WINK_DURATION_S = 1.0


class ENIACController:
    def __init__(self):
        self.face = FaceDisplay(
            on_boot=play_bootup,
            on_sleep=play_sleep,
        )

        self.wake: Optional[WakeWordListener] = None
        self.vad: Optional[MicVAD] = None

        self.history = []
        self.max_turns = 8

        self._busy = False
        self._lock = threading.Lock()

    def _start_wake_listener(self):
        if self.wake is None:
            self.wake = WakeWordListener(
                on_detected=self._on_wake_detected,
            )

        self.wake.start()

    def _return_to_idle(self):
        self.face.clear_text()
        self.face.set_state(STATE_IDLE)

        with self._lock:
            self._busy = False

        self._start_wake_listener()

    def _on_wake_detected(self, score):
        with self._lock:
            if self._busy:
                return

            self._busy = True

        print(f"[Wake word] Hey Jarvis detected — score: {score:.3f}")

        if self.wake is not None:
            self.wake.stop()

        self.face.set_state(STATE_LISTENING)

        play_soft()

        self.vad = MicVAD(
            on_speech_start=self._on_speech_start,
            on_speech_end=self._on_speech_end,
            on_utterance=self._on_utterance,
            on_timeout=self._on_no_request,
            device=None,
        )

        self.vad.start()

    def _on_speech_start(self):
        print("[VAD] Speech started.")
        self.face.set_state(STATE_LISTENING)

    def _on_speech_end(self):
        print("[VAD] Speech ended.")
        self.face.set_state(STATE_OK_WINK)

    def _on_no_request(self):
        print("[VAD] No speech received. Showing Judge state.")

        self.face.set_state(STATE_JUDGE)
        time.sleep(JUDGE_DURATION_S)

        self._return_to_idle()

    def _on_utterance(self, audio_np: np.ndarray):
        print(f"[VAD] Captured {len(audio_np)} audio samples.")

        time.sleep(OK_WINK_DURATION_S)
        self.face.set_state(STATE_THINKING)

        try:
            text = transcribe_audio_numpy(audio_np, SAMPLE_RATE).strip()
        except Exception as e:
            print("[STT error]", e)
            text = ""

        if not text:
            self.face.show_error()
            time.sleep(1.2)

            self.face.set_state(STATE_SPEAKING)
            speak("I did not catch that.")

            self._return_to_idle()
            return

        print("USER:", text)

        try:
            result = generate_reply(text, history=self.history)
            reply = result["text"]

        except Exception as e:
            print("[LLM error]", e)

            self.face.show_error()
            time.sleep(1.2)

            reply = "My brain glitched. Try again?"

        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply})

        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

        print("ENIAC:", reply)

        self.face.set_state(STATE_SPEAKING)
        speak(reply)

        self._return_to_idle()

    def start(self):
        self.face.start()
        self._start_wake_listener()

        print(
            "\nENIAC is running.\n"
            "Say: Hey Jarvis\n"
            "Wait for Soft.mp3.\n"
            "Then say your request.\n"
            "Press Ctrl+C to stop.\n"
        )

    def stop(self):
        if self.wake is not None:
            self.wake.stop()

        if self.vad is not None:
            self.vad.stop()

        self.face.stop()


def main():
    eniac = ENIACController()
    eniac.start()

    try:
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping ENIAC...")
        eniac.stop()


if __name__ == "__main__":
    main()
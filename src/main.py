import threading
import time
from typing import Optional

import numpy as np
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")

from src.audio.mic import MicVAD, RATE
from src.audio.tts import play_bootup, play_sleep, play_soft, play_random_thinking_phrase, speak
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

THINKING_PROMPT_DELAY_S = 0.8

SHUTDOWN_PHRASES = ("shut down","off" "shutdown", "power off", "turn off")


class ENIACController:
    def __init__(self):
        self.face = FaceDisplay(
            on_boot=play_bootup,
            on_sleep=play_sleep,
        )

        self.wake: Optional[WakeWordListener] = None
        self.vad: Optional[MicVAD] = None

        self._generation = 0
        self._speaking_stop_event = threading.Event()

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

    def _return_to_idle(self, gen):
        with self._lock:
            if gen != self._generation:
             return
        self._busy = False

        self.face.clear_text()
        self.face.set_state(STATE_IDLE)
        self._start_wake_listener()

    def _on_wake_detected(self, score):
        with self._lock:
            was_busy = self._busy
            self._busy = True
            self._generation += 1
            my_gen = self._generation

        if was_busy:
            print(f"[Wake word] Barge-in detected — score: {score:.3f}")
            self._speaking_stop_event.set()
        else:
            print(f"[Wake word] Hey Jarvis detected — score: {score:.3f}")

        if self.wake is not None:
            self.wake.stop()

            self.face.set_state(STATE_LISTENING)
            play_soft()

            self.vad = MicVAD(
                on_speech_start=self._on_speech_start,
                on_speech_end=self._on_speech_end,
                on_utterance=lambda audio, gen=my_gen: self._on_utterance(audio, gen),
                on_timeout=lambda gen=my_gen: self._on_no_request(gen),
                device=None,
    )
            self.vad.start()

    def _on_speech_start(self):
        print("[VAD] Speech started.")
        self.face.set_state(STATE_LISTENING)

    def _on_speech_end(self):
        print("[VAD] Speech ended.")
        self.face.set_state(STATE_OK_WINK)

    def _on_no_request(self, gen):
        with self._lock:
            if gen != self._generation:
                return

        print("[VAD] No speech received. Showing Judge state.")
        self.face.set_state(STATE_JUDGE)
        time.sleep(JUDGE_DURATION_S)
        self._return_to_idle(gen)


    def _on_utterance(self, audio_np: np.ndarray, gen: int):
        print(f"[VAD] Captured {len(audio_np)} audio samples.")

        def voice_started():
            if gen != self._generation:
                return
            print("[TTS] Playback started.")
            self.face.set_state(STATE_SPEAKING)

        time.sleep(OK_WINK_DURATION_S)

        if gen != self._generation:
            return

        self.face.set_state(STATE_THINKING)

        # Mic is free now — re-enable wake word to catch a barge-in
        # during Thinking/Speaking.
        self._speaking_stop_event.clear()
        time.sleep(0.05)
        self._start_wake_listener()

        result_holder = {}
        done_event = threading.Event()

        def worker():
            try:
                result_holder["text"] = transcribe_audio_numpy(
                    audio_np, SAMPLE_RATE
                ).strip()
            except Exception as e:
                print("[STT error]", e)
                result_holder["text"] = ""
            done_event.set()

        threading.Thread(target=worker, daemon=True).start()

        if not done_event.wait(timeout=THINKING_PROMPT_DELAY_S):
            if gen == self._generation:
                play_random_thinking_phrase()
            done_event.wait()

        if gen != self._generation:
            return

        text = result_holder.get("text", "")

        if not text:
            self.face.show_error()
            time.sleep(1.2)

            if gen != self._generation:
                return

            self.face.set_state(STATE_THINKING)
            speak(
                "I did not catch that.",
                on_playback_start=voice_started,
                stop_event=self._speaking_stop_event,
            )

            self._return_to_idle(gen)
            return

        print("USER:", text)

        # --- Local shutdown command, bypasses Groq entirely ---
        if any(phrase in text.lower() for phrase in SHUTDOWN_PHRASES):
            print("[System] Shutdown command received.")

            if gen != self._generation:
                return

            self.face.set_state(STATE_THINKING)
            speak(
                "Shutting down now. See you soon.",
                on_playback_start=voice_started,
                stop_event=self._speaking_stop_event,
            )

            if self.wake is not None:
                self.wake.stop()
            if self.vad is not None:
                self.vad.stop()
            self.face.stop()

            os.system("sudo shutdown -h now")
            return

        llm_result_holder = {}
        llm_done_event = threading.Event()

        def llm_worker():
            try:
                result = generate_reply(text, history=self.history)
                llm_result_holder["reply"] = result["text"]
            except Exception as e:
                print("[LLM error]", e)
                llm_result_holder["reply"] = "My brain glitched. Try again?"
            llm_done_event.set()

        threading.Thread(target=llm_worker, daemon=True).start()

        if not llm_done_event.wait(timeout=THINKING_PROMPT_DELAY_S):
            if gen == self._generation:
                play_random_thinking_phrase()
            llm_done_event.wait()

        if gen != self._generation:
            return

        reply = llm_result_holder.get("reply", "My brain glitched. Try again?")

        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply})

        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

        print("ENIAC:", reply)

        self.face.set_state(STATE_THINKING)

        speak(
            reply,
            on_playback_start=voice_started,
            stop_event=self._speaking_stop_event,
        )

        self._return_to_idle(gen)

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
# src/main.py
# src/main.py
import time
from typing import Optional

import numpy as np

from src.audio.mic import MicVAD
from src.faces.display_loop import (
    FaceDisplay,
    STATE_IDLE,
    STATE_LISTENING,
    STATE_THINKING,
)
from src.brain.groq_client import transcribe_audio_numpy, generate_reply

SAMPLE_RATE = 48000  # must match RATE in MicVAD


class ENIACController:
    """
    High-level orchestrator for ENIAC's behavior:
    - controls face states
    - triggers STT + LLM on utterances
    """

    def __init__(self):
        self.face = FaceDisplay()
        self.vad: Optional[MicVAD] = None

    # ---- MicVAD callbacks ----
    def on_speech_start(self):
        # User started speaking → listening face
        print("[DEBUG] speech start")
        self.face.set_state(STATE_LISTENING)

    def on_speech_end(self):
        # We do nothing here; we wait for full utterance in on_utterance
        print("[DEBUG] speech end")

    def on_utterance(self, audio_np: np.ndarray):
        print(f"[DEBUG] on_utterance called, samples={len(audio_np)}")

        # 1) Thinking face
        self.face.set_state(STATE_THINKING)

        # 2) Real STT (Groq Whisper)
        try:
            text = transcribe_audio_numpy(audio_np, SAMPLE_RATE)
        except Exception as e:
            print("[STT error]", e)
            text = ""

        if not text:
            reply = "Hmm, I didn't catch that."
        else:
            print("USER:", text)

            # 3) Real LLM (Groq Llama)
            try:
                reply = generate_reply(text)
            except Exception as e:
                print("[LLM error]", e)
                reply = "My brain glitched. Try again?"

        print("ENIAC:", reply)

        # 4) TODO: render reply under the eyes; for now just delay
        time.sleep(2.0)
        self.face.set_state(STATE_IDLE)

    # ---- Lifecycle ----
    def start(self):
        # Start face animation; smaller delay = faster GIF
        self.face.start(frame_delay_s=0.01)

        # Start VAD with callbacks
        self.vad = MicVAD(
            on_speech_start=self.on_speech_start,
            on_speech_end=self.on_speech_end,
            on_utterance=self.on_utterance,
            device=None,
        )
        self.vad.start()

    def stop(self):
        if self.vad is not None:
            self.vad.stop()
        self.face.stop()


def main():
    eniac = ENIACController()
    eniac.start()

    print(
        "ENIAC running: idle → listening → thinking, with Groq STT+LLM.\n"
        "Talk near the mic; watch the face change; replies printed in terminal.\n"
        "Press Ctrl+C to stop."
    )

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping ENIAC...")
        eniac.stop()


if __name__ == "__main__":
    main()

# src/main.py
import time
from typing import Optional

import numpy as np
from src.audio.tts import speak

from src.audio.mic import MicVAD
from src.faces.display_loop import (
    FaceDisplay,
    STATE_IDLE,
    STATE_LISTENING,
    STATE_THINKING,
    STATE_SPEAKING,
    STATE_ERROR, 
    STATE_WINK,
)
from src.brain.groq_client import transcribe_audio_numpy, generate_reply

SHOW_REPLY_ON_SCREEN = False 
SAMPLE_RATE = 48000  # must match RATE in MicVAD


class ENIACController:
    def __init__(self):
        self.face = FaceDisplay()
        self.vad: Optional[MicVAD] = None
        self.history = []        # conversation memory
        self.MAX_TURNS = 8       # keep last 8 exchanges

    def on_speech_start(self):
        print("[DEBUG] speech start")
        self.face.set_state(STATE_LISTENING)

    def on_speech_end(self):
        print("[DEBUG] speech end")

    def on_utterance(self, audio_np: np.ndarray):
        print(f"[DEBUG] on_utterance called, samples={len(audio_np)}")

        self.face.set_state(STATE_THINKING)

        try:
            text = transcribe_audio_numpy(audio_np, SAMPLE_RATE)
        except Exception as e:
            print("[STT error]", e)
            text = ""

        if not text:
            reply = "Hmm, I didn't catch that."
        else:
            print("USER:", text)

            try:
                result = generate_reply(text, history=self.history)
                reply = result["text"]
                mood = result["mood"]
            except Exception as e:
                print("[LLM error]", e)
                reply = "My brain glitched. Try again?"
                mood = "neutral"

            # Update memory after a successful exchange
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": reply})
            if len(self.history) > self.MAX_TURNS * 2:
                self.history = self.history[-self.MAX_TURNS * 2:]

        print("ENIAC:", reply)

        if SHOW_REPLY_ON_SCREEN:
            self.face.show_text_reply(reply)
        else:
            self.face.set_state(STATE_SPEAKING)

        speak(reply)  # must block until audio playback finishes

        self.face.set_state(STATE_IDLE)

    # ---- Lifecycle ----
    def start(self):
        # Start face animation; smaller delay = faster GIF
        self.face.start(frame_delay_s=0.9)

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
        "Talk near the mic; watch the face change; replies printed in terminal and on screen.\n"
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

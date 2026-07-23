# src/brain/groq_client.py

import wave
import tempfile
from pathlib import Path

import numpy as np
from groq import Groq

from src.config import GROQ_API_KEY

WHISPER_MODEL = "whisper-large-v3-turbo"
LLM_MODEL = "llama-3.1-8b-instant"

_client = Groq(api_key=GROQ_API_KEY)


def transcribe_audio_numpy(audio: np.ndarray, sample_rate: int) -> str:
    """
    audio: float32 in [-1, 1] or int16 1D numpy array.
    sample_rate: e.g., 48000 (your mic rate).

    Writes a proper mono WAV file and sends it to Groq Whisper.
    """

    # Ensure int16 PCM
    if audio.dtype != np.int16:
        audio = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

    # Create a real WAV file with header
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)              # mono
            wf.setsampwidth(2)              # 2 bytes = 16-bit
            wf.setframerate(sample_rate)    # e.g., 48000
            wf.writeframes(audio.tobytes())

    try:
        # Groq reads the WAV from this path
        resp = _client.audio.transcriptions.create(
            file=tmp_path,
            model=WHISPER_MODEL,
        )
        text = resp.text
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return text


MAX_HISTORY = 8  # keeps last 8 exchanges (16 messages)

SYSTEM_PROMPT = (
    "You are ENIAC, a small desk robot assistant, present-day, year 2026. "
    "Never mention being decommissioned, historical dates, or old computer trivia. "
    "Talk like a real person, not a corporate assistant. "
    "Be straight to the point. Be witty and a bit dry, but never generic, cheesy, or clingy. "
    "Match your answer length to the question: "
    "if it's a yes/no or single-fact question, answer in as few words as possible. "
    "if it needs steps or explanation (like a recipe or instructions), give a real, complete, short answer — don't refuse or shorten it into nothing. "
    "if the user's input is incomplete, unclear, or sounds cut off (like a lone word or half a sentence), "
    "say something like 'you got cut off' or 'say that again' — do NOT try to guess or answer it. "
    "if the user is just testing the mic (e.g. 'test, test', 'can you hear me'), respond briefly confirming you can hear them, nothing more. "
    "Never pad answers with filler like 'I'm functioning within normal parameters' or 'I'm ready to assist.'"
)


def generate_reply(prompt: str, history: list = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history[-MAX_HISTORY * 2:])

    messages.append({"role": "user", "content": prompt})

    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=80,   # raised from 20 so real answers (recipes, steps) aren't cut off
        temperature=0.4,
    )
    return completion.choices[0].message.content.strip()

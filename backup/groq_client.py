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


def generate_reply(prompt: str) -> str:
    """
    Call Groq LLaMA model for a reply to the given prompt.
    """

    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are ENIAC, a funny, friendly desk robot. Be concise and a bit playful.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=128,
    )
    return completion.choices[0].message.content.strip()

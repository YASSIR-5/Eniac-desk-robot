# src/brain/groq_client.py

import wave
import tempfile
from pathlib import Path

import numpy as np
from groq import Groq

from src.config import GROQ_API_KEY

# Switched from whisper-large-v3-turbo to the full whisper-large-v3.
# Turbo is a pruned/distilled model that trades accuracy for speed
# (32 decoder layers cut down to 4). On short, low-context commands
# like "power off" or "turn off" that accuracy loss matters a lot more
# than on full sentences/questions, where surrounding words give the
# model context to recover from a slightly clipped or mis-heard word.
# Both models are free on Groq's tier (2,000 audio requests/day
# either way), so this costs nothing.
WHISPER_MODEL = "whisper-large-v3"
LLM_MODEL = "openai/gpt-oss-20b"

_client = Groq(api_key=GROQ_API_KEY)

# Biases Whisper toward the short command vocabulary ENIAC actually
# needs to recognize reliably. This is a documented Whisper/Groq API
# parameter (prompt), not a guess — it nudges the decoder toward these
# words/phrases when the audio is ambiguous, which is exactly the
# failure mode on clipped or mis-heard short commands (e.g. "power
# off" being transcribed as "power of").
COMMAND_PROMPT = (
    "Power off. Shut down. Turn off. Hey Jarvis. "
    "What time is it. Set a timer."
)


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
            prompt=COMMAND_PROMPT,
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
    "if it needs steps or explanation, give a real, complete, short answer. "
    "if the user's input is incomplete or sounds cut off, say 'you got cut off' or 'say that again' — do NOT guess. "
    "if the user is testing the mic, briefly confirm you can hear them. "
    "Never pad answers with filler like 'I'm functioning within normal parameters.' "
    "\n\n"
    "After your answer, on a new line, output exactly one mood tag from this list: "
    "happy, sad, wink, judgy, neutral. "
    "Format your entire response EXACTLY like this, nothing else:\n"
    "TEXT: <your answer>\n"
    "MOOD: <one mood tag>"
)


def generate_reply(prompt: str, history: list = None) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history[-MAX_HISTORY * 2:])

    messages.append({"role": "user", "content": prompt})

    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=100,
        temperature=0.4,
    )

    raw = completion.choices[0].message.content.strip()

    mood = "neutral"
    text_lines = []

    lines = [l for l in raw.splitlines() if l.strip()]

    for line in lines:
        upper = line.upper()
        if upper.startswith("MOOD:"):
            mood = line.split(":", 1)[1].strip().lower()
        elif upper.startswith("TEXT:"):
            text_lines.append(line.split(":", 1)[1].strip())
        else:
            text_lines.append(line.strip())

    text = " ".join(text_lines).strip() if text_lines else raw

    valid_moods = {"happy", "sad", "wink", "judgy", "neutral"}
    if mood not in valid_moods:
        mood = "neutral"

    return {"text": text, "mood": mood}
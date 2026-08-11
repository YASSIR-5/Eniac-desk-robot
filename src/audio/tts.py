import asyncio
import re
import subprocess
import tempfile
import random 
import time 
from pathlib import Path

import edge_tts


VOICE = "en-US-AvaMultilingualNeural"

SOUND_EFFECT_DIR = Path(__file__).resolve().parent / "Sound_Effects"


async def _generate_speech(text: str, out_path: Path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(out_path))


def _play_mp3(path: Path, on_playback_start=None, stop_event=None):
    process = subprocess.Popen(
        ["mpg123", "-q", str(path)],
    )

    if on_playback_start:
        on_playback_start()

    while process.poll() is None:
        if stop_event is not None and stop_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
            return
        time.sleep(0.05)

    return_code = process.returncode

    if return_code != 0 and not (stop_event is not None and stop_event.is_set()):
        raise subprocess.CalledProcessError(
            return_code,
            ["mpg123", "-q", str(path)],
        )


def _prepare_text(text: str):
    return re.sub(r"\beniac\b", "Eniac", text, flags=re.IGNORECASE)


def speak(text: str, on_playback_start=None, stop_event=None):
    if not text:
        return

    text = _prepare_text(text)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        asyncio.run(_generate_speech(text, tmp_path))
        _play_mp3(tmp_path, on_playback_start=on_playback_start, stop_event=stop_event)

    except Exception as e:
        print(f"[TTS error] {e}")

    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def play_effect(filename: str):
    """
    Play a local MP3 from src/audio/Sound_Effects.
    """
    path = SOUND_EFFECT_DIR / filename

    if not path.exists():
        print(f"[Sound effect missing] {path}")
        return

    try:
        _play_mp3(path)
    except Exception as e:
        print(f"[Sound effect error] {e}")


def play_bootup():
    play_effect("Bootup.mp3")


def play_sleep():
    play_effect("Sleep.mp3")


def play_soft():
    play_effect("Soft.mp3")
    
    
THINKING_PHRASES = [
    "Thinking_01.mp3",
    "Thinking_02.mp3",
    "Thinking_03.mp3",
    "Thinking_04.mp3",
    "Thinking_05.mp3",
    "Thinking_06.mp3",
    "Thinking_07.mp3",
    "Thinking_08.mp3",
]


def play_random_thinking_phrase():
    filename = random.choice(THINKING_PHRASES)
    play_effect(filename)    
import asyncio
import subprocess
import tempfile
from pathlib import Path
import re 
import edge_tts


VOICE = "en-US-AvaMultilingualNeural"

SOUND_EFFECT_DIR = Path(__file__).resolve().parent / "Sound_Effects"


async def _generate_speech(text: str, out_path: Path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(out_path))


def _play_mp3(path: Path):
    subprocess.run(
        ["mpg123", "-q", str(path)],
        check=True,
    )

def _prepare_text(text: str):
    return re.sub(r"\beniac\b", "Eniac", text, flags=re.IGNORECASE)

def speak(text: str):
    """
    Generate spoken text with Ava and play it through the 3.5 mm jack.
    Blocks until generation and playback finish.
    """
    if not text:
        return
    
    text = _prepare_text(text)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        asyncio.run(_generate_speech(text, tmp_path))
        _play_mp3(tmp_path)

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
    This function blocks, so display callbacks call it in a separate thread.
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
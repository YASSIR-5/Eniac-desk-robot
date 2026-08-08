import subprocess
import tempfile
import asyncio
from pathlib import Path
import edge_tts

VOICE = "en-US-GuyNeural"  # change voice here if you want a different one


async def _generate_speech(text: str, out_path: Path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(out_path))


def speak(text: str):
    """
    Converts text to speech using edge-tts and plays it
    through the 3.5mm jack via mpg123. Blocks until playback finishes.
    """
    if not text:
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        asyncio.run(_generate_speech(text, tmp_path))
        subprocess.run(["mpg123", "-q", str(tmp_path)], check=True)
    except Exception as e:
        print(f"[TTS error] {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
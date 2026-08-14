import asyncio
from pathlib import Path

import edge_tts

VOICE = "en-US-AvaMultilingualNeural"
OUT_DIR = Path(__file__).resolve().parent / "src" / "audio" / "Sound_Effects"

PHRASES = {
    "OkWink_01.mp3": "On it.",
    "OkWink_02.mp3": "Got it.",
    "OkWink_03.mp3": "OK.",
    "OkWink_04.mp3": "Copy that.",
    "OkWink_05.mp3": "Understood.",
    "OkWink_06.mp3": "Gotcha.",
    "OkWink_07.mp3": "Got you.",
}


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename, text in PHRASES.items():
        out_path = OUT_DIR / filename
        print(f"Generating {filename} -> \"{text}\"")

        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(str(out_path))


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
from pathlib import Path

import edge_tts

VOICE = "en-US-AvaMultilingualNeural"
OUT_DIR = Path(__file__).resolve().parent / "src" / "audio" / "Sound_Effects"

PHRASES = {
    "Goodbye_01.mp3": "Goodbye.",
    "Goodbye_02.mp3": "See you soon.",
    "Goodbye_03.mp3": "Powering off. Bye.",
    "Goodbye_04.mp3": "See you later.",
    "Goodbye_05.mp3": "Shutting down now.",
    "Goodbye_06.mp3": "Catch you later.",
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

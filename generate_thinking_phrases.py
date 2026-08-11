import asyncio
from pathlib import Path

import edge_tts

VOICE = "en-US-AvaMultilingualNeural"
OUT_DIR = Path(__file__).resolve().parent / "src" / "audio" / "Sound_Effects"

PHRASES = {
    "Thinking_01.mp3": "On it.",
    "Thinking_02.mp3": "Computing.",
    "Thinking_03.mp3": "Let me think.",
    "Thinking_04.mp3": "One moment.",
    "Thinking_05.mp3": "Checking that.",
    "Thinking_06.mp3": "Give me a second.",
    "Thinking_08.mp3": "Working on it.",
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
V1 status update
Pi 3 A+ is running Raspberry Pi OS Lite with SSH dev workflow as planned.

2.8" ILI9341 SPI screen is wired to CE0 / GPIO24 / GPIO25 / MOSI / SCLK exactly as in the GPIO table, and confirmed working via Python.

Face system is now a live loop, not just static sprites: a Python thread alternates between idle.png and blank_background.png when idle, and switches to listening.png / listening2.png when wake word is detected.

USB mic is connected and streaming audio via sounddevice.RawInputStream at 48 kHz; audio is downsampled to 16 kHz for wake-word inference using scipy.signal.resample_poly.

Wake word is implemented with OpenWakeWord using a custom hey_eniac.onnx model, loaded via:
Model(wakeword_model_paths=[...], inference_framework="onnx").

Detection threshold is currently tuned to 0.18 with a 2-second cooldown to balance sensitivity vs false triggers. When confidence crosses threshold, ENIAC prints detection in the terminal and enters the Listening face state.

Suggested checklist section you can add:

text
### V1 Wake Word + Face Test (Done)

- [x] Install `openwakeword`, `sounddevice`, `scipy`, `Pillow`, `adafruit_rgb_display`
- [x] Load custom `hey_eniac.onnx` wake word model
- [x] Stream mic audio at 48 kHz and downsample to 16 kHz
- [x] Drive ILI9341 over SPI with `adafruit_rgb_display.ILI9341`
- [x] Idle face loop: toggle between `idle.png` and `blink.png`
- [x] On wake word detection: switch to `listening.png` / `listening2.png` animation
- [x] Tune threshold (~0.18) and cooldown (2s) for reliable detection
Brain & AI pipeline (near-term software plan)
You can tweak the “Brain & AI Pipeline” chat description to reflect the next concrete step:

V1: Wake, face, and text-only interaction loop on Pi

Input: wake word + mic recording (already partly done via test.txt).

Output (current phase): text drawn under the eyes on the LCD (no speaker yet), using Pillow to render text onto a “wide-eye” frame, as described in eniac_implementation_guide.md.

V2: swap in Groq Whisper + Groq Llama 3 for full STT → LLM → reply, then later add TTS once the MAX98357A + speaker are installed.

You can also add one short line under the Personality or Face section:

Status: ENIAC now blinks and reacts to “Hey ENIAC” in real time — the robot feels visually alive before any voice output.
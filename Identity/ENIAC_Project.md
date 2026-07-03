# ENIAC — Project Master Document

> **ENIAC** stands for the first computer ever built (1945). This project brings that name to life as a modern AI desk robot — funny, friendly, and alive.

---

## Project Vision

ENIAC is a physical AI desk buddy robot inspired by BMO from Adventure Time. It sits on the desk, has a screen face that shows emotions, listens to voice commands, responds with a funny and friendly personality, and over time becomes a fully agentic assistant that can connect to Gmail, Google Calendar, WhatsApp, and more.

The long-term goal: say **"Hey ENIAC"** and ENIAC can hear you, understand you, look at you, respond with personality, and take real actions in the world — like adding a calendar event, sending a message, or searching the web to answer a question.

This is the builder's **first hardware + software project of this kind**. The approach is beginner-friendly, step by step, with physical milestones to stay motivated.

---

## Personality

ENIAC is:
- **Funny** — will crack jokes and roast you lightly
- **Friendly** — always warm and approachable
- **Judgy in a fun way** — if you ask something obvious, it will call you out with humor
- **Alive** — expressive face, reacts to context, not just a cold assistant

---

## Project Versioning

| Version | Name | Goal | Key Features |
|---------|------|------|-------------|
| **V1** | The Face | Get ENIAC physically alive | Pi 3 A+ booting, SSH setup, screen showing animated face states (idle, listening, thinking, speaking) |
| **V2** | The Voice | ENIAC can speak and hear | USB mic input → Groq Whisper STT, Groq Llama LLM, Piper TTS voice output, basic conversation |
| **V3** | The Eyes | ENIAC can see | Camera module added, face/object recognition, "what is this?" visual Q&A via vision API |
| **V4** | The Agent | ENIAC can act | Agentic integrations: Google Calendar, Gmail, WhatsApp, web search, more services over time |
| **V5** | The Body | ENIAC can move | Motors/servos for head rotation or movement, physical reactions to touch and motion sensors |

---

## Hardware

### Already Ordered
- Raspberry Pi 3 A+
- 2.8" ILI9341 LCD screen (SPI, 240×320)
- USB microphone (plug & play, no driver)
- Jumper wires (female-to-female)

### Already Owned
- Micro USB power cable
- USB charger/adapter (5V / 3.5A) — sufficient for Pi 3 A+
- 16GB microSD card

### Planned for Future Versions
- MAX98357A I2S amplifier + small speaker (V2 — voice output)
- Camera module (V3 — vision)
- Touch sensor (TTP223 capacitive) (V5)
- PIR motion sensor (HC-SR501) (V5)
- Motors/servos (V5 — movement)

---

## Software Stack

| Layer | Tool | Notes |
|-------|------|-------|
| OS | Raspberry Pi OS Lite | Terminal only, headless, SSH access |
| Language | Python 3 | Main development language |
| Dev workflow | SSH from laptop | No keyboard/mouse/monitor on Pi |
| Wake word | OpenWakeWord | Trigger phrase: "Hey ENIAC" |
| Speech-to-text | Groq Whisper API | Free tier |
| LLM / Brain | Groq Llama 3 | Free tier, fast response |
| Text-to-speech | Piper TTS | Lightweight, runs locally on Pi |
| Vision | Google Gemini API | Free tier, for "what is this?" queries |
| Display | Python + Pillow + ST7789/ILI9341 lib | Face animation via PNG sprite switching |
| Agentic layer | TBD | Google Calendar, Gmail, WhatsApp — added per version |

---

## Face Animation Plan

Simple PNG sprite system stored on the Pi, switched via Python based on robot state:

| State | File | Description |
|-------|------|-------------|
| Idle | `idle.png` | Calm default face |
| Listening | `listening.png` | Eyes wide, attentive |
| Thinking | `thinking.png` | Eyes looking up or squinting |
| Speaking | `talk1.png` / `talk2.png` | Alternating mouth frames |
| Happy | `happy.png` | Smile, upbeat |
| Judgy | `judgy.png` | One eyebrow raised |

All sprites are small resolution PNGs drawn to match the 240×320 screen. Switching is handled in the main Python state machine.

---

## Project Folder Structure (on Pi)

```
eniac/
├── main.py              # Main robot loop and state machine
├── face/
│   ├── display.py       # Screen driver and image switching
│   └── sprites/         # PNG face images
│       ├── idle.png
│       ├── listening.png
│       ├── thinking.png
│       ├── talk1.png
│       ├── talk2.png
│       ├── happy.png
│       └── judgy.png
├── audio/
│   ├── mic.py           # Microphone capture
│   └── tts.py           # Piper TTS output
├── brain/
│   ├── stt.py           # Groq Whisper STT
│   ├── llm.py           # Groq Llama conversation
│   └── vision.py        # Gemini vision API (V3+)
├── agents/
│   └── calendar.py      # Google Calendar integration (V4+)
└── config.py            # API keys, settings, GPIO pins
```

---

## Setup Path (Current Focus: V1)

1. Flash **Raspberry Pi OS Lite** to the 16GB SD card using [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Enable SSH in Imager settings (set hostname, username, password, Wi-Fi credentials)
3. Boot Pi and connect via SSH from laptop
4. Install Python libraries: `Pillow`, `st7789` or `luma.lcd`
5. Wire 2.8" ILI9341 screen to Pi GPIO (SPI)
6. Test screen with a basic Python image display
7. Build face state system with PNG sprites
8. Test USB microphone input (ALSA / PyAudio)
9. Proceed to V2 pipeline

---

## GPIO Pin Reference (Pi 3 A+ — ILI9341 SPI Screen)

| Screen Pin | Pi GPIO Pin | Pi Physical Pin |
|------------|------------|----------------|
| VCC | 3.3V | Pin 1 |
| GND | GND | Pin 6 |
| CS | GPIO 8 (CE0) | Pin 24 |
| RESET | GPIO 25 | Pin 22 |
| DC | GPIO 24 | Pin 18 |
| MOSI | GPIO 10 (MOSI) | Pin 19 |
| SCK | GPIO 11 (SCLK) | Pin 23 |
| LED | 3.3V or GPIO | Pin 1 or Pin 17 |

---

## Budget Tracker

| Item | Cost | Status |
|------|------|--------|
| Raspberry Pi 3 A+ | ~€26 | Ordered |
| 2.8" LCD + USB mic + jumper wires | ~€18 | Ordered |
| Power adapter (5V/3.5A) | €0 | Already owned |
| 16GB microSD | €0 | Already owned |
| **V1 Total** | **~€44** | ✅ |
| MAX98357A amp + speaker (V2) | ~€8 | Planned |
| Camera module (V3) | ~€15 | Planned |
| Touch + motion sensors (V5) | ~€5 | Planned |

---

## Multi-Chat Structure

This project is managed across several focused Perplexity chats. Each chat specializes in one area but all share this document as their reference. When starting any chat, paste this document into the project resource and reference it.

| Chat Name | Responsibility |
|-----------|---------------|
| **ENIAC — Overview** | Big picture, decisions, versioning, project direction |
| **ENIAC — Hardware & Build** | Wiring, GPIO, screen setup, physical assembly |
| **ENIAC — Face & Display** | PNG sprites, face states, animation, display driver code |
| **ENIAC — Audio & Voice** | Microphone input, Piper TTS voice output, voice personality |
| **ENIAC — Brain & AI Pipeline** | STT, LLM, wake word, conversation loop, vision (V3+) |
| **ENIAC — Agents & Integrations** | Calendar, Gmail, WhatsApp, web search, future services |

---

## Notes

- Builder is a **beginner** in hardware and robotics — explanations should be clear and step-by-step
- Pi 3 A+ was chosen over Pi Zero 2 W (out of stock) and Orange Pi (compatibility issues)
- All API usage targets **free tiers** to keep costs at zero
- Physical progress is prioritized to maintain motivation
- Proteus 8 is available for wiring diagrams but cannot simulate the full Pi software stack


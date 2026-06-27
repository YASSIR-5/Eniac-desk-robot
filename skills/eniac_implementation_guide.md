# ENIAC: The Desk Assistant Robot - Implementation Guide & Tech Stack

This document provides a comprehensive guide to building the ENIAC desk assistant robot on a Raspberry Pi 3 Model A+. It details the recommended technology stack, justifies each choice based on the constraints of low latency and zero cost, and outlines a modular implementation strategy that accommodates the current speaker-less phase and future audio upgrades.

## 1. Recommended Technology Stack

The following technologies have been selected to meet the strict requirements of running headlessly on a Raspberry Pi 3A+ while utilizing free-tier APIs to achieve a 2-3 second response time.

### 1.1. Wake Word Detection: Picovoice Porcupine

**Justification:** Porcupine is the industry standard for lightweight, on-device wake word detection [1]. It is specifically optimized for embedded systems like the Raspberry Pi, consuming only 3.8% of a single core on a Pi 3 [1]. It operates entirely offline, ensuring privacy and zero latency for the initial trigger. The free developer tier allows for custom wake word training, making it perfect for a student project.

**Alternative:** OpenWakeWord is a viable open-source alternative that can run on a Pi Zero 2W [2], but Porcupine offers a more streamlined setup and proven enterprise-grade performance out of the box.

### 1.2. Speech-to-Text (STT): Deepgram (Primary) / Groq Whisper (Fallback)

**Justification:** Deepgram is renowned for its incredibly low latency and high accuracy, offering a generous $200 free credit upon signup, which equates to hundreds of hours of transcription [3]. This makes it ideal for the primary STT engine.

**Fallback Strategy:** Groq recently added Whisper to its API offerings. Given Groq's focus on ultra-low latency inference, this serves as an excellent, fast fallback if Deepgram credits are exhausted or rate limits are hit [8].

### 1.3. Large Language Model (LLM): Groq (Llama 3) / Google Gemini 1.5 Flash

**Justification:** Groq's LPU (Language Processing Unit) architecture provides unparalleled inference speed, often generating responses in milliseconds [8]. Their free tier offers access to models like Llama 3 with limits of 30 requests per minute and 14,400 requests per day, which is more than sufficient for a personal desk assistant [9].

**Fallback Strategy:** Google Gemini 1.5 Flash is another excellent low-latency option [6]. Its free tier provides 1,500 requests per day [7]. If Groq experiences downtime or rate limits, the system can seamlessly switch to Gemini.

### 1.4. Text-to-Speech (TTS): Edge-TTS (Primary) / eSpeak-ng (Fallback)

**Justification:** While cloud TTS APIs offer the best voices, they introduce latency and have strict free tiers. `edge-tts` is a Python library that utilizes the Microsoft Edge Read Aloud API. It provides high-quality, natural-sounding voices completely free of charge and without requiring API keys.

**Fallback Strategy:** `eSpeak-ng` is a completely offline, open-source TTS engine that can be installed directly on the Raspberry Pi. While the voice quality is robotic, it guarantees zero network latency and infinite usage, making it a bulletproof fallback.

### 1.5. Display & Animation: Pillow (PIL) + luma.lcd / luma.oled

**Justification:** Since the Pi 3A+ will run Pi OS Lite (headless), a lightweight approach to driving the SPI screen is required. The `luma` ecosystem (`luma.lcd` or `luma.oled`, depending on the specific screen hardware) is designed exactly for this purpose. It integrates perfectly with the `Pillow` library, allowing the pre-rendered PNG frames to be loaded and pushed directly to the screen buffer. `Pillow` also provides the necessary functions to overlay text onto the "Wide-eye" frame during the current speaker-less phase.

## 2. Modular Implementation Strategy

The ENIAC software should be structured as a state machine, transitioning between Idle, Listening, Thinking, and Responding states. This modularity is crucial for handling the transition from text-based responses to audio responses.

### 2.1. State Machine Architecture

The core Python application will manage the following states:

1.  **Idle State:**
    *   **Action:** Porcupine continuously listens for the wake word ("ENIAC").
    *   **Display:** Shows `idle.png`.
2.  **Listening State:**
    *   **Trigger:** Wake word detected.
    *   **Action:** Records audio from the microphone until silence is detected (using Voice Activity Detection - VAD).
    *   **Display:** Shows `listening.png`.
3.  **Thinking State:**
    *   **Trigger:** Audio recording complete.
    *   **Action:** Sends audio to STT API (Deepgram -> Groq Whisper). Sends transcribed text to LLM API (Groq -> Gemini).
    *   **Display:** Alternates between `thinking_left.png` and `thinking_right.png`.
4.  **Responding State (Current Phase - Text Only):**
    *   **Trigger:** LLM response received.
    *   **Action:** Formats the text for display.
    *   **Display:** Shows `response_wide.png`. Uses `Pillow` to draw the LLM response text onto the image buffer before sending it to the SPI screen. The text can be scrolled or paginated if it exceeds the screen area.
5.  **Responding State (Future Phase - Audio):**
    *   **Trigger:** LLM response received.
    *   **Action:** Sends text to TTS engine (`edge-tts` -> `eSpeak-ng`). Plays the resulting audio stream.
    *   **Display:** Rapidly alternates between `speaking_a.png` and `speaking_b.png` while audio is playing.

### 2.2. Handling the Audio Upgrade

To ensure a smooth transition when the speaker is added, the code should use a configuration flag:

```python
# config.py
AUDIO_OUTPUT_ENABLED = False # Set to True when speaker is installed
```

The `Response Handler` module will check this flag:

```python
# response_handler.py
import config
from display import show_text_response, animate_speaking
from tts import play_audio

def handle_response(text):
    if config.AUDIO_OUTPUT_ENABLED:
        # Future Phase
        animate_speaking() # Starts the mouth animation thread
        play_audio(text)   # Blocks until audio finishes
        # Return to idle
    else:
        # Current Phase
        show_text_response(text) # Shows wide-eye frame with text overlay
        # Wait for user to read, then return to idle
```

### 2.3. Robust Fallback Implementation

The API calls should be wrapped in a robust retry mechanism. Here is a conceptual example for the LLM call:

```python
def get_llm_response(prompt):
    try:
        # Attempt Primary (Groq)
        return call_groq_api(prompt)
    except RateLimitError:
        print("Groq rate limit hit. Switching to fallback.")
        try:
            # Attempt Fallback (Gemini)
            return call_gemini_api(prompt)
        except Exception as e:
            print(f"Fallback failed: {e}")
            return "I'm sorry, my brain is currently offline."
```

By structuring the code this way, ENIAC will remain responsive and functional even when free-tier limits are reached, fulfilling the requirement for a robust, low-latency desk assistant.

## References

[1] Picovoice Porcupine. (n.d.). *Porcupine Wake Word: On-Device Keyword Spotting for Enterprises*. Retrieved from https://picovoice.ai/products/voice/wake-word/
[2] Reddit. (2025, July 25). *I got wake word detection on a Pi Zero 2W without hating myself*. Retrieved from https://www.reddit.com/r/RASPBERRY_PI_PROJECTS/comments/1m9an0c/i_got_wake_word_detection_on_a_pi_zero_2w_without/
[3] Deepgram. (n.d.). *Deepgram Pricing*. Retrieved from https://deepgram.com/pricing
[6] dev.to. (2024, June 24). *Comparing 13 LLM Providers API Performance with Node.js*. Retrieved from https://dev.to/samestrin/comparing-13-llm-providers-api-performance-with-nodejs-latency-and-response-times-across-models-2ka4
[7] Google AI for Developers. (n.d.). *Rate limits | Gemini API*. Retrieved from https://ai.google.dev/gemini-api/docs/rate-limits
[8] Groq. (n.d.). *Groq is fast, low cost inference*. Retrieved from https://groq.com/
[9] CloudZero. (2026, May 4). *Groq Pricing In 2026: Every Model, Tier, And Cost Compared*. Retrieved from https://www.cloudzero.com/blog/groq-pricing/

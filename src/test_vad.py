from src.audio.mic import MicVAD

def on_start():
    print(">>> SPEECH START")

def on_end():
    print("<<< SPEECH END")

def on_utt(audio):
    print(f"[UTTERANCE] length={len(audio)} samples")

def main():
    vad = MicVAD(on_speech_start=on_start, on_speech_end=on_end, on_utterance=on_utt, device=None)
    vad.start()
    print("VAD running. Talk; Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        vad.stop()

if __name__ == "__main__":
    main()

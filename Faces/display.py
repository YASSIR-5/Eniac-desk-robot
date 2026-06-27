"""
display.py - ENIAC face tester with Tkinter (Pi side)

This script:
- Loads a subset of face sprites: idle, thinking_left/right, speaking_a/b.
- Opens a Tkinter window on the Pi (displayed on your laptop via SSH + X).
- Lets you switch between states using buttons:
    * Idle: show idle.png (no animation)
    * Thinking: toggle between thinking_left.png and thinking_right.png
    * Speaking: toggle between speaking_a.png and speaking_b.png
"""

import os
from PIL import Image, ImageTk  # Pillow
import tkinter as tk            # Tkinter GUI

# --- Config: filenames for each state ---

IDLE_FACE = "idle.png"

THINKING_FRAMES = [
    "thinking_left.png",
    "thinking_right.png",
]

SPEAKING_FRAMES = [
    "speaking_a.png",
    "speaking_b.png",
]


class FaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ENIAC Face Tester")

        # Load images once at startup
        self.images = self.load_images()

        # Current state and frame index
        self.current_state = "idle"   # "idle", "thinking", "speaking"
        self.current_frame_index = 0
        self.animation_job = None     # after() callback handle

        # GUI: label for image, buttons for states
        self.image_label = tk.Label(self.root)
        self.image_label.pack(padx=10, pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack(padx=10, pady=10)

        idle_button = tk.Button(button_frame, text="Idle", command=self.set_idle)
        idle_button.grid(row=0, column=0, padx=5)

        thinking_button = tk.Button(button_frame, text="Thinking", command=self.set_thinking)
        thinking_button.grid(row=0, column=1, padx=5)

        speaking_button = tk.Button(button_frame, text="Speaking", command=self.set_speaking)
        speaking_button.grid(row=0, column=2, padx=5)

        # Start in idle
        self.show_idle()

    def load_images(self):
        """
        Load all required images from the current folder and
        convert them to Tkinter-compatible PhotoImage objects.
        """
        images = {}

        def load_image(name):
            if not os.path.exists(name):
                print(f"Warning: image '{name}' not found")
                return None
            img = Image.open(name)
            # Optionally resize if needed; for now, keep original size
            return ImageTk.PhotoImage(img)

        # Idle
        images["idle"] = load_image(IDLE_FACE)

        # Thinking frames
        images["thinking"] = []
        for filename in THINKING_FRAMES:
            img = load_image(filename)
            images["thinking"].append(img)

        # Speaking frames
        images["speaking"] = []
        for filename in SPEAKING_FRAMES:
            img = load_image(filename)
            images["speaking"].append(img)

        return images

    # --- State setters ---

    def set_idle(self):
        self.stop_animation()
        self.current_state = "idle"
        self.show_idle()

    def set_thinking(self):
        self.current_state = "thinking"
        self.start_animation()

    def set_speaking(self):
        self.current_state = "speaking"
        self.start_animation()

    # --- Display helpers ---

    def show_idle(self):
        """Show the idle face (no animation)."""
        img = self.images.get("idle")
        if img is not None:
            self.image_label.config(image=img)
            self.image_label.image = img  # keep reference
        else:
            self.image_label.config(text="Idle image missing")

    def start_animation(self):
        """Start animation for the current state."""
        self.stop_animation()  # ensure no previous animation running
        self.current_frame_index = 0
        self.schedule_next_frame()

    def schedule_next_frame(self):
        """Schedule the next frame update using Tkinter's after()."""
        # Choose the correct frame list based on state
        if self.current_state == "thinking":
            frames = self.images.get("thinking", [])
        elif self.current_state == "speaking":
            frames = self.images.get("speaking", [])
        else:
            # For any other state, just show idle
            self.show_idle()
            return

        # If no frames loaded, fallback to idle
        if not frames or frames[0] is None:
            self.show_idle()
            return

        # Pick current frame
        frame = frames[self.current_frame_index]
        self.image_label.config(image=frame)
        self.image_label.image = frame  # keep reference

        # Advance frame index (flip-flop)
        self.current_frame_index = (self.current_frame_index + 1) % len(frames)

        # Schedule next update (e.g. every 200 ms)
        self.animation_job = self.root.after(200, self.schedule_next_frame)

    def stop_animation(self):
        """Stop any running animation."""
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None


def main():
    # Create Tkinter root window
    root = tk.Tk()
    app = FaceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).parent
GIF_DIR = BASE_DIR / "faces" / "Gifs"

for name in ["intro.gif", "idle.gif", "listening.gif", "thinking.gif"]:
    path = GIF_DIR / name
    try:
        im = Image.open(path)
    except FileNotFoundError:
        print(f"{name}: NOT FOUND")
        continue

    frames = getattr(im, "n_frames", 1)
    print(f"{name}: {frames} frame(s), mode={im.mode}, size={im.size}")

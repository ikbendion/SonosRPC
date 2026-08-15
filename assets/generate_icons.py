"""Generates placeholder tray/app icons with Pillow.

Run once (`python assets/generate_icons.py`) to (re)create:
  - icon.png / icon.ico       normal state, used for the tray icon and the
                               packaged exe's icon
  - icon_error.png / .ico     disconnected/error tray state
  - logo.png                  fallback Discord large_image asset -- upload
                               this in the Discord Developer Portal under
                               Rich Presence > Art Assets as the key "logo"

These are intentionally simple so the app has no missing-asset failures
out of the box; swap them for real artwork whenever you like, keeping the
same filenames.
"""
import os

from PIL import Image, ImageDraw

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))

SONOS_BLACK = (17, 17, 17, 255)
ACCENT_WHITE = (255, 255, 255, 255)
ERROR_RED = (220, 53, 69, 255)


def _base_speaker_icon(size: int, ring_color) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size * 0.08
    draw.ellipse([margin, margin, size - margin, size - margin], fill=SONOS_BLACK)
    for radius_frac in (0.34, 0.22, 0.10):
        r = size * radius_frac
        cx = cy = size / 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring_color, width=max(1, int(size * 0.035)))
    dot_r = size * 0.05
    cx = cy = size / 2
    draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=ring_color)
    return img


def _save_ico(img: Image.Image, path: str) -> None:
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])


def main() -> None:
    normal = _base_speaker_icon(256, ACCENT_WHITE)
    normal.save(os.path.join(ASSETS_DIR, "icon.png"))
    _save_ico(normal, os.path.join(ASSETS_DIR, "icon.ico"))

    error = _base_speaker_icon(256, ERROR_RED)
    error.save(os.path.join(ASSETS_DIR, "icon_error.png"))
    _save_ico(error, os.path.join(ASSETS_DIR, "icon_error.ico"))

    logo = _base_speaker_icon(512, ACCENT_WHITE)
    logo.save(os.path.join(ASSETS_DIR, "logo.png"))

    print(f"Wrote icon.png, icon.ico, icon_error.png, icon_error.ico, logo.png to {ASSETS_DIR}")


if __name__ == "__main__":
    main()

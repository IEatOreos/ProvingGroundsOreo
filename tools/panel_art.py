"""The game logos for the profile view's game list: tools/view_art/games/<game>.png (MCC's own UI art, tools/map_art.py) as
raw pixels the panel can load without an image library: native/bin/art/<game>.rgba = uint32 width, uint32 height, then
width*height RGBA bytes. Run by native/build.bat.

Also art/stage.rgba: the profile view's stage behind the 3D bot (backdrop()).

usage: python -I panel_art.py      -> "panel art: 7 logos -> native/bin/art"
"""
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "view_art", "games")
OUT = os.path.join(HERE, "..", "native", "bin", "art")


def write_rgba(img, path):
    img = img.convert("RGBA")
    with open(path, "wb") as f:
        f.write(struct.pack("<II", *img.size))
        f.write(img.tobytes())


def backdrop(w=520, h=760):
    """The profile view's stage: our own drawing in its manner, a deep blue room lit from above, shafts of light
    fanning down, a pool of light behind the figure and on the floor, darker edges. Not MCC's art."""
    import numpy as np
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = x / w, y / h
    top, bottom = np.array([34, 52, 118], np.float32), np.array([8, 12, 30], np.float32)
    img = top * (1 - v[..., None]) ** 1.2 + bottom * (1 - (1 - v[..., None]) ** 1.2)
    # shafts: narrow fans of light from points above the frame
    light = np.zeros((h, w), np.float32)
    for sx, ang, width, strength in ((0.40, -0.42, 0.070, 0.55), (0.45, -0.18, 0.085, 0.75), (0.52, 0.02, 0.10, 0.85),
                                     (0.58, 0.20, 0.085, 0.70), (0.62, 0.45, 0.070, 0.50)):
        cx = sx * w + ang * y                                # from above the frame, fanning out downward
        half = width * w * (0.4 + 1.6 * (y / h))             # wider as it goes down
        beam = np.clip(1 - np.abs(x - cx) / np.maximum(half, 1), 0, 1) ** 1.6
        light += beam * strength * (1 - v) ** 1.3
    # a soft pool behind the figure and on the floor
    glow = np.exp(-(((u - 0.5) / 0.30) ** 2 + ((v - 0.45) / 0.42) ** 2)) * 0.55
    floor = np.exp(-(((u - 0.5) / 0.28) ** 2 + ((v - 0.90) / 0.05) ** 2)) * 0.45
    tint = np.array([120, 160, 255], np.float32)
    img = img + (light + glow)[..., None] * tint * 0.55 + floor[..., None] * np.array([90, 130, 220], np.float32) * 0.6
    vig = 1 - 0.55 * (((u - 0.5) * 1.5) ** 2 + ((v - 0.5) * 1.1) ** 2)
    img = np.clip(img * np.clip(vig, 0.25, 1)[..., None], 0, 255)
    noise = np.random.default_rng(3).normal(0, 1.4, img.shape[:2])[..., None]   # no banding in the dark
    img = np.clip(img + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    write_rgba(backdrop(), os.path.join(OUT, "stage.rgba"))
    n = 0
    for name in sorted(os.listdir(SRC)):
        if name.endswith(".png"):
            write_rgba(Image.open(os.path.join(SRC, name)), os.path.join(OUT, name[:-4] + ".rgba"))
            n += 1
    print(f"panel art: {n} logos -> {os.path.normpath(OUT)}")


if __name__ == "__main__":
    sys.exit(main())

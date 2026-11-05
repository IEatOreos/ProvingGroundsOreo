"""The profile view's armor effects, from the game's own particle bitmaps: Reach's Sword Base map through model2obj
--bitmaps (the map tools; what Reach's objects\\characters\\spartans\\fx\\armor_fx effects use: head_fire's fire_large
through the fire and covenant_fire gradients, cupid_heart's flying_heart, bugs, thunder_cloud's soft_smoke_small,
lightning_flash's flash_soft).
Writes native/bin/art/fx_<name>.rgba (uint32 width, uint32 height, then RGBA, as tools/panel_art.py) for
native/bots_panel.cpp's effect layer: fire baked through its gradient (a pixel's brightness picks its colour, its
brightness its alpha), the hearts and flies as drawn, the smoke and flash white with their own alpha (tinted when
drawn). Run by native/build.bat when the sprites are missing.

usage: python -I fx_art.py [MCC folder]"""
import os
import struct
import subprocess
import sys

import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import paths  # noqa: E402  (where MCC and the map tools are)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
MCC = sys.argv[1] if len(sys.argv) > 1 else paths.mcc()
MAP = os.path.join(MCC or "", "haloreach", "maps", "20_sword_slayer.map")
SRC = os.path.join(ROOT, "maps", "_models", "fx")
OUT = os.path.join(ROOT, "native", "bin", "art")
TAGS = {"fire": r"fx\bitmaps\fire\fire_large", "grad_fire": r"fx\particles\fire\gradients\fire",
        "grad_cov": r"fx\particles\fire\gradients\covenant_fire",
        "hearts": r"fx\bitmaps\debug\flying_heart", "bugs": r"fx\bitmaps\nature\bugs",
        "smoke": r"fx\bitmaps\atmospheric\soft_smoke_small", "flash": r"fx\bitmaps\flash\flash_soft"}


def write_rgba(img, path):
    img = img.convert("RGBA")
    with open(path, "wb") as f:
        f.write(struct.pack("<II", img.width, img.height))
        f.write(img.tobytes())


def exported(key):
    """The bitmap's first submap as RGBA (exported once into maps/_models/fx, as model2obj names it)."""
    png = os.path.join(SRC, TAGS[key].replace("\\", "_") + "_0.png")
    if not os.path.exists(png):
        os.makedirs(SRC, exist_ok=True)
        exe = paths.need(paths.map_tool("model2obj"), "model2obj.exe (the map tools: tools/map_tools)")
        r = subprocess.run([exe, MAP, "--bitmaps", TAGS[key], SRC], capture_output=True, text=True, errors="replace")
        if r.returncode or not os.path.exists(png):
            said = (r.stdout + r.stderr).strip().splitlines()
            raise SystemExit(f"the map tools could not read {os.path.basename(MAP)} (exit {r.returncode & 0xFFFFFFFF:#x}"
                             + (f": {said[-1][:160]}" if said else "") + ")")
    return np.asarray(Image.open(png).convert("RGBA")).astype(np.float32) / 255.0


def palette_fire(src, grad, flip, size=256, tint=(1.0, 1.0, 1.0)):
    """The grayscale fire through a gradient row: bright pixels the hot end, alpha its brightness."""
    lum = np.asarray(Image.fromarray((src[..., 3] * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)) / 255.0
    row = grad[grad.shape[0] // 2, :, :3] * np.array(tint, np.float32)
    u = lum if flip else 1.0 - lum
    idx = np.clip((u * (row.shape[0] - 1) * 0.8).astype(int), 0, row.shape[0] - 1)
    rgb = row[idx] * (0.55 + 0.45 * lum[..., None])
    rgb = np.clip(rgb / max(row.max(), 1e-3), 0, 1)        # (the hot end at full brightness)
    a = np.clip(lum * 1.15, 0, 1)
    return Image.fromarray((np.dstack([rgb, a]) * 255).astype(np.uint8), "RGBA")


def white_alpha(src, size=None):
    a = src[..., 3]
    img = Image.fromarray((np.dstack([np.ones_like(a), np.ones_like(a), np.ones_like(a), a]) * 255).astype(np.uint8), "RGBA")
    return img.resize(size, Image.LANCZOS) if size else img


def main():
    if not os.path.exists(MAP):                      # (Steam installs each game on its own)
        raise SystemExit("needs Halo: Reach installed (its Sword Base map has the effects)")
    os.makedirs(OUT, exist_ok=True)
    fire = exported("fire")
    write_rgba(palette_fire(fire, exported("grad_fire"), False), os.path.join(OUT, "fx_fire.rgba"))
    write_rgba(palette_fire(fire, exported("grad_cov"), False), os.path.join(OUT, "fx_fire_blue.rgba"))
    write_rgba(palette_fire(fire, exported("grad_cov"), False, tint=(1.45, 0.55, 1.0)),   # (Halo 4's Eternal: purple)
               os.path.join(OUT, "fx_fire_purple.rgba"))
    write_rgba(Image.fromarray((exported("hearts") * 255).astype(np.uint8), "RGBA"), os.path.join(OUT, "fx_hearts.rgba"))
    write_rgba(Image.fromarray((exported("bugs") * 255).astype(np.uint8), "RGBA"), os.path.join(OUT, "fx_bugs.rgba"))
    write_rgba(white_alpha(exported("smoke"), (128, 128)), os.path.join(OUT, "fx_smoke.rgba"))
    write_rgba(white_alpha(exported("flash"), (128, 128)), os.path.join(OUT, "fx_flash.rgba"))
    print("armor effect sprites ->", OUT)


if __name__ == "__main__":
    main()

"""Each bot's own emblem.

It is an MCC emblem, the one every game's scoreboard and MCC's post-game report draw for a player (MCC renders it per
player from its player lookup, which botcore answers for the bots with this roll: native/report.cpp): one of MCC's
foregrounds (a primary and a secondary layer), one of its backgrounds and three of its 31 emblem colours
(maps/_looks/mcc_emblems.json and the layers' art: tools/emblems.py extract). Colour 31 is MCC's transparent one: the
secondary layer in it is the part switched off (a quarter of the bots). Rolled once from the bot's profile seed (the
same every match, like its armor), the primary colour readable on the background's; drawn into
native/bin/emblems/<name>.rgba for the Settings tab's profile view.
"""
import functools
import json
import os
import random

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CATALOG = os.path.join(ROOT, "maps", "_looks", "mcc_emblems.json")
ART = os.path.join(ROOT, "maps", "_models", "emblems_mcc")        # the layers' shapes (tools/emblems.py extract)
OUT = os.path.join(ROOT, "native", "bin", "emblems")
OFF = 31                        # MCC's transparent emblem colour ($COLOR_ALPHA): a layer in it is not drawn
TOGGLE_CHANCE = 0.25            # the foreground's second part switched off


@functools.lru_cache(maxsize=1)
def catalog():
    """(foregrounds [[id, primary layer, secondary layer, name]], backgrounds [[id, layer, name]],
    colours {id: (r, g, b) 0-255} without the transparent one)."""
    with open(CATALOG, encoding="utf-8") as f:
        c = json.load(f)
    cols = {int(k): tuple(round(255 * x) for x in v[:3]) for k, v in c["colours"].items() if v[3] > 0}
    return c["foregrounds"], c["backgrounds"], cols


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def roll(seed):
    """{fg, bg, primary, secondary, background}: MCC ids from a bot's profile seed (brain/looks.py seed_of)."""
    fgs, bgs, cols = catalog()
    rng = random.Random(f"{seed}:emblem")
    fg, bg = rng.choice(fgs)[0], rng.choice(bgs)[0]
    ids = sorted(cols)
    background = rng.choice(ids)
    far = [k for k in ids if abs(_lum(cols[k]) - _lum(cols[background])) >= 60]
    primary = rng.choice(far or ids)
    secondary = OFF if rng.random() < TOGGLE_CHANCE else rng.choice([k for k in ids if k != primary])
    return dict(fg=fg, bg=bg, primary=primary, secondary=secondary, background=background)


def ids(e):
    """The five numbers MCC keeps for an emblem, in its order: foreground, background, primary, secondary and
    background colours (botctl.add_bot's emblem=)."""
    return e["fg"], e["bg"], e["primary"], e["secondary"], e["background"]


def compose(e, size=128):
    """The emblem as an RGBA picture (PIL) as MCC layers it (background, secondary, primary), or None when the art
    is not extracted."""
    from PIL import Image
    import numpy as np
    fgs, bgs, cols = catalog()
    f = next(x for x in fgs if x[0] == e["fg"])
    b = next(x for x in bgs if x[0] == e["bg"])
    paths = [os.path.join(ART, n + ".png") for n in (b[1], f[2], f[1])]
    if not all(os.path.exists(p) for p in paths):
        return None
    out = np.zeros((size, size, 4), np.float32)
    for path, c in zip(paths, (e["background"], e["secondary"], e["primary"])):
        if c not in cols:                                        # (transparent: that layer is off)
            continue
        a = np.asarray(Image.open(path).convert("L").resize((size, size), Image.LANCZOS), np.float32)[..., None] / 255
        out[..., :3] = out[..., :3] * (1 - a) + np.asarray(cols[c], np.float32) / 255 * a
        out[..., 3:] = out[..., 3:] * (1 - a) + a
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


def write_rgba(img, path):
    import struct
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(struct.pack("<II", *img.size) + img.tobytes())
    os.replace(tmp, path)


def export(names_seeds):
    """Every bot's emblem picture: native/bin/emblems/<name>.rgba. Returns how many were written."""
    n = 0
    for name, seed in names_seeds:
        img = compose(roll(seed))
        if img is not None:
            write_rgba(img, os.path.join(OUT, f"{name}.rgba"))
            n += 1
    return n


def selftest():
    fgs, bgs, cols = catalog()
    a, b = roll(12345), roll(12345)
    assert a == b, "the same seed rolls the same emblem"
    rolls = [roll(s) for s in range(400)]
    assert len({(r["fg"], r["bg"]) for r in rolls[:200]}) > 180, "200 seeds, too few different emblems"
    assert {r["fg"] for r in rolls} <= {f[0] for f in fgs} and {r["bg"] for r in rolls} <= {x[0] for x in bgs}
    assert all(r["primary"] in cols and r["background"] in cols and r["secondary"] in set(cols) | {OFF} for r in rolls)
    off = sum(r["secondary"] == OFF for r in rolls)
    assert 60 < off < 140, f"second part off {off} of 400"
    assert all(abs(_lum(cols[r["primary"]]) - _lum(cols[r["background"]])) >= 60 for r in rolls)
    print("emblems OK")


if __name__ == "__main__":
    selftest()

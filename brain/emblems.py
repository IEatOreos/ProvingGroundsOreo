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


# (custom, Nov 18, the owner: an emblem editor for each bot on the Service Record, "like MCC's own") the emblems the
# owner picked in the site's edit mode (tools/service_record_edit.py), by bot name: native/bin/emblems/chosen.json
# {name: {fg, bg, primary, secondary, background}}. A bot with one shows it everywhere its roll showed (the lobby's
# .ids, the .rgba picture, matches: brain/looks.py emblem_of); the others keep their roll.
KEYS = ("fg", "bg", "primary", "secondary", "background")


def chosen_path():
    return os.path.join(OUT, "chosen.json")


def chosen():
    """{name: emblem} as saved; an entry that is not a good emblem (valid) is left out."""
    try:
        with open(chosen_path(), encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    return {n: {k: e[k] for k in KEYS} for n, e in (raw.items() if isinstance(raw, dict) else [])
            if isinstance(n, str) and valid(e)}


def valid(e):
    """Whether e is an emblem MCC has: a foreground and a background of the catalog, three of its colours (the
    secondary may be OFF, the second part switched off)."""
    if not isinstance(e, dict) or any(not isinstance(e.get(k), int) or isinstance(e.get(k), bool) for k in KEYS):
        return False
    fgs, bgs, cols = catalog()
    return (any(x[0] == e["fg"] for x in fgs) and any(x[0] == e["bg"] for x in bgs) and e["primary"] in cols
            and e["background"] in cols and (e["secondary"] in cols or e["secondary"] == OFF))


def save_chosen(name, e):
    """The bot's emblem picked (e None: back to its roll). ValueError for an emblem that is not one (valid)."""
    if not isinstance(name, str) or not name.strip() or len(name) > 32:
        raise ValueError("not a bot name")
    picks = chosen()
    if e is None:
        picks.pop(name, None)
    elif valid(e):
        picks[name] = {k: e[k] for k in KEYS}
    else:
        raise ValueError("not an emblem MCC has")
    os.makedirs(OUT, exist_ok=True)
    tmp = chosen_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=1, sort_keys=True)
    os.replace(tmp, chosen_path())


def emblem_for(name, seed):
    """The bot's emblem: the one picked for it (chosen; its name in any case), else its roll."""
    picks = chosen()
    pick = picks.get(name) or next((e for n, e in picks.items() if n.lower() == str(name).lower()), None)
    return dict(pick) if pick else roll(seed)


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


def write_ids(e, path):
    """(custom, Nov 13) The emblem's five MCC numbers (ids order), one line: MCC's own lobby rows for the bot
    (native/report.cpp reads <name>.ids, MCC draws the emblem from them)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(" ".join(str(v) for v in ids(e)) + "\n")
    os.replace(tmp, path)


def export(names_seeds):
    """Every bot's emblem picture: native/bin/emblems/<name>.rgba, and its numbers, <name>.ids (written even without
    the art): the one picked for it, else its roll (emblem_for). Returns how many pictures were written."""
    n = 0
    for name, seed in names_seeds:
        e = emblem_for(name, seed)
        write_ids(e, os.path.join(OUT, f"{name}.ids"))
        try:
            img = compose(e)
        except ImportError:                                      # (no PIL: the numbers still go out)
            img = None
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


def draw(path, fg, bg, primary, secondary, background):
    """(custom, Nov 17) Any emblem by MCC's five numbers (the person's own, as MCC's player lookup gives them:
    native/bots_panel.cpp player_emblem) into an .rgba picture. False when the art or a number is not known."""
    fgs, bgs, _ = catalog()
    if not any(x[0] == fg for x in fgs) or not any(x[0] == bg for x in bgs):
        return False
    img = compose(dict(fg=fg, bg=bg, primary=primary, secondary=secondary, background=background))
    if img is None:
        return False
    write_rgba(img, path)
    return True


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--draw"] and len(sys.argv) == 8:
        ok = draw(sys.argv[2], *(int(v) for v in sys.argv[3:8]))
        print("drawn" if ok else "not drawn")
        sys.exit(0 if ok else 1)
    selftest()

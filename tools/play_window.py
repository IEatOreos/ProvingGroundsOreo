"""(custom, Nov 23) A Forge layout's play area, for its nav window (brain/variants.py play_limit).

The owner, on Renegade's nav (3.46 million points, 9% of them reachable and over half of those out of bounds): "Remove
the waste from renegade and see what you can do". This builds the layout's nav on its whole window, puts its kill and
safe zones on it (brain/oob.py: killzones.json and the spots learned), and keeps the box round the floor a player reaches
inside them (variants.play_window_of) in its variant.json with its kill zones' fingerprint. From the next match its nav
is cut to it. A layout with no kill or safe zones is left as it is.

usage: python -I tools/play_window.py reach_forge_halo/variants/vf1ed8bb6 [--dry]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brain import maps, variants        # noqa: E402
from brain.oob import Oob               # noqa: E402

MIN_SHARE = 0.9    # the play window keeps at least this share of the layout's spawns in bounds, or it is not kept


def work_out(name):
    """(play window, report) for a variant from its whole window; (None, why) when there is none to keep."""
    import numpy as np
    data = variants.info(name)
    if data is None:
        return None, "not a filed map variant"
    if variants.killzones_print(name) is None:
        return None, "no kill or safe zones (killzones.json)"
    m = maps.get_map(name)
    whole = tuple(data["window"]) if data.get("window") else None
    T = maps._build(m, whole)
    o = Oob(name)
    if not o.volumes:
        return None, "its kill zones are empty"
    T.set_oob(o.spots, o.version, o.volumes)
    inb = T.reach & ~T.oob
    if not inb.any():
        return None, "nothing reachable in bounds"
    l, j, i = np.nonzero(inb)
    xs, ys = T.x0 + i * T.cell, T.y0 + j * T.cell
    pw = variants.clip(variants.play_window_of(xs, ys), whole)
    spawns = [p for p in maps.spawn_points(m) if T.inside(p.x, p.y) and T.reach[T._node(p)] and not T.oob[T._node(p)]]
    kept = [p for p in spawns if pw[0] <= p.x <= pw[2] and pw[1] <= p.y <= pw[3]]
    if spawns and len(kept) < MIN_SHARE * len(spawns):
        return None, f"only {len(kept)} of {len(spawns)} in-bounds spawns inside {pw}"
    area = lambda w: (w[2] - w[0]) * (w[3] - w[1])
    report = (f"{name}: window {whole} -> play window {pw} ({area(pw) / area(whole):.0%} of its area); reachable "
              f"{int(T.reach.sum())}, in bounds {int(inb.sum())}; spawns in bounds {len(kept)} of {len(spawns)}")
    return pw, report


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    for name in names:
        pw, report = work_out(name)
        print(report, flush=True)
        if pw is not None and "--dry" not in sys.argv:
            variants.save_play_window(name, pw)
            print(f"  kept in {os.path.join('maps', name, 'variant.json')}", flush=True)


if __name__ == "__main__":
    main()

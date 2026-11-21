"""(custom, Nov 20) What Noble has learned (brain/noble.py): its tuned settings (user/noble_tune.json, tools/noble_tune.py)
and its shots' hit rate by gun and distance band, by pace and by part (user/noble_shots.json, written by the live
Nobles: every press of a precision gun watched for his shield or body dropping). The per-round accuracy the match
recordings do not keep. Read-only.

usage: python -I tools/noble_report.py [--game reach]"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from brain import noble  # noqa: E402


def band_name(b):
    lo = 0.0 if b == 0 else noble.BANDS[b - 1]
    return f"{lo:.0f}-{noble.BANDS[b]:.0f} u" if b < len(noble.BANDS) else f"{lo:.0f}+ u"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="reach")
    o = ap.parse_args()
    st = noble.tune(o.game)
    diff = {k: v for k, v in st.items() if noble.DEFAULTS[k] != v}
    print(f"tune ({o.game}): {diff or 'the defaults'}")
    meta = (noble._read(noble.TUNE_FILE).get(o.game) or {})
    if meta:
        print(f"  found {meta.get('when')}: {meta.get('margin')} kills a game over Demon in {meta.get('games')} sim games")
    cells = noble.book().data.get(o.game, {})
    if not cells:
        print("no shots recorded yet (user/noble_shots.json): play a match with Nobles")
        return
    for w, table in sorted(cells.items()):
        tot = sum(n for n, _ in table.values())
        hits = sum(h for _, h in table.values())
        print(f"\n{w}: {hits} of {tot} rounds landed ({100.0 * hits / max(tot, 1):.0f}%)")
        for b in range(len(noble.BANDS) + 1):
            row = {k: v for k, v in table.items() if int(k.split("|")[0]) == b}
            if not row:
                continue
            n = sum(v[0] for v in row.values())
            h = sum(v[1] for v in row.values())
            paces = {}
            parts = {}
            for k, (cn, ch) in row.items():
                _, p, part = k.split("|")
                a = paces.setdefault(p, [0, 0])
                a[0], a[1] = a[0] + cn, a[1] + ch
                a = parts.setdefault(part, [0, 0])
                a[0], a[1] = a[0] + cn, a[1] + ch
            pace_s = ", ".join(f"x{p} {v[1]}/{v[0]}" for p, v in sorted(paces.items(), key=lambda x: str(x[0])))
            part_s = ", ".join(f"{p} {v[1]}/{v[0]}" for p, v in sorted(parts.items()))
            print(f"  {band_name(b):>8}: {h}/{n} ({100.0 * h / n:.0f}%)   pace: {pace_s}   part: {part_s}")


if __name__ == "__main__":
    main()

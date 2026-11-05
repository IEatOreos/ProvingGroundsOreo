"""Brings the BOTS panel's Scaling hover box up to date (botcore runs it when the panel opens): keeps the last match's
post-game report beside its trace (play.py keep_carnage, otherwise done only as the next match starts), counts any new
Scaling game and writes logs/scaling_view.txt (brain/scaling.py write_view).

usage: python -I scaling_view.py [botcore.ini [scaling.ini]]   (scaling.ini: the Advanced tab's; beside botcore.ini)
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from brain import scaling  # noqa: E402


def main():
    try:
        from play import keep_carnage
        keep_carnage(sorted(glob.glob(os.path.join(ROOT, "logs", "trace_*_????????-??????.jsonl")), key=os.path.getmtime))
    except Exception as e:                       # (the counted games still show)
        print("post-game report not kept:", e)
    ini = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "native", "bin", "botcore.ini")
    cfg = scaling.settings(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(ini), "scaling.ini"))
    st = scaling.update(n=scaling.games_window(ini), cfg=cfg)
    print(f"scaling view: {len(st['games'])} games, skill rating {100 * st['play']:.0f}%")


if __name__ == "__main__":
    main()

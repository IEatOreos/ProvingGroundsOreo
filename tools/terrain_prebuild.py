"""(custom, Nov 21) Build a map's next terrain after a match, in the background (brain/maps.py prebuild_after_match):
the map as it was loaded at that match's start (a pickle written there), against the data the match just saved, filed in
the terrain cache (logs/terrain_cache) so the next match on that map loads it instead of building it while the bots
stand at their spawns. Nothing is built when the cache has it already.

usage: python -I terrain_prebuild.py <next_<map>.pkl>"""
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, ".."), HERE]

from brain import maps   # noqa: E402


def main(path):
    m = pickle.load(open(path, "rb"))
    key = maps.cache_key(m)
    if os.path.exists(maps._cache_file(m["name"], key)):
        return f"{m['name']}: cached already"
    t0 = time.time()
    T = maps._build(m, m.get("window"))
    maps._cache_save(m, key, T, wait=True)
    return f"{m['name']}: built in {time.time() - t0:.1f} s, cached"


if __name__ == "__main__":
    try:
        msg = main(sys.argv[1])
    except Exception as e:
        msg = f"failed: {type(e).__name__}: {e}"
    try:
        with open(os.path.join(maps.CACHE_DIR, "prebuild.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass

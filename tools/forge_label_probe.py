"""Find where Halo: Reach keeps a map variant object's Forge label (GitHub issue 2: Invasion on a Forge map, Tempest, read
as Slayer: the mod knows Invasion's objectives, respawn zones and gates only from a built-in map's scenario). Read-only:
it reads MCC's memory, never writes it and sends no input.

Run it in a Forge map variant's Invasion match (custom game, the host's PC, after the round has started):
  python -I tools\\forge_label_probe.py [tag]       -> logs/forge_label_probe_<tag>.json and a summary
What it saves:
  variant      the game variant's name, engine icon (game globals +0x1524) and teams flag (Invasion's icon is not read yet)
  objects      every live object: handle, type, tag name, position and its first 0x300 bytes (hex)
  strings      every "inv_" text (ASCII or UTF-16, any case) in the game globals and anywhere in writable memory
               (the game variant's Forge label table, the map variant's labels)
  pos_hits     for each marker-like object (hill markers, respawn zones and points, flag stands, capture plates, the
               core and bomb), every other place in writable memory holding its exact position, with 0x80 bytes either
               side: the map variant's object record (label, team, shape) is one of them
  arrays       the engine's named data arrays (tools/memread.py data_arrays)
The person who built the map knows each object's label: the next session matches the records to them.
"""
import json
import os
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
MARKERS = ("spawning", "respawn", "hill_beacon", "mp_circle", "capture", "flag_stand", "flag_base", "power_module",
           "powermodule", "data_core", "assault_bomb", "covenant_bomb", "invasion", "territory", "objective", "goal")
CHUNK = 64 << 20
MAX_POS = 80            # marker objects whose positions are searched for
MAX_HITS = 40


def scan(g, needles, max_hits=MAX_HITS, skip=()):
    """{needle: [address]} for each bytes needle in every committed writable region (memread.Game.regions)."""
    out = {n: [] for n in needles}
    for base, size in g.regions():
        for off in range(0, size, CHUNK):
            blob = g.read(base + off, min(CHUNK + 64, size - off))
            if not blob:
                continue
            for n in needles:
                if len(out[n]) >= max_hits:
                    continue
                i = blob.find(n)
                while i != -1 and len(out[n]) < max_hits:
                    a = base + off + i
                    if i < CHUNK and not any(lo <= a < hi for lo, hi in skip):
                        out[n].append(a)
                    i = blob.find(n, i + 1)
    return out


def texts(blob, base):
    """[(address, encoding, text)] of every "inv_" text in blob (ASCII or UTF-16, any case)."""
    out = []
    for m in re.finditer(rb"(?i)inv_[a-z0-9_]{0,40}", blob):
        out.append((base + m.start(), "ascii", m.group().decode("ascii")))
    for m in re.finditer(rb"(?i)i\x00n\x00v\x00_\x00(?:[a-z0-9_]\x00){0,40}", blob):
        out.append((base + m.start(), "utf16", m.group().decode("utf-16-le")))
    return out


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    from brain.live import LiveReach
    from brain.forge import _tag_names
    import memread
    live = LiveReach()
    live.players()
    gg = live.g.u64(live._blk + 0x48)
    ggb = live.g.read(gg, 0x30000) or b""
    out = dict(map=live.map_name(), variant=dict(
        name=live.variant_name(), icon=struct.unpack_from("<i", ggb, 0x1524)[0] if len(ggb) > 0x1528 else None,
        teams=bool(ggb[0x17A4] & 1) if len(ggb) > 0x17A4 else None))
    names = _tag_names(live)
    ents, mx, _ = live._array(live.OBJECTS_AT)
    table = live.g.read(ents, mx * 0x18)
    objs, spans = [], []
    for i in range(mx):
        salt = struct.unpack_from("<H", table, i * 0x18)[0]
        if not salt:
            continue
        typ, addr = table[i * 0x18 + live.TYPE_AT], struct.unpack_from("<Q", table, i * 0x18 + 0x10)[0]
        head = live.g.read(addr, 0x300)
        if not head:
            continue
        t = struct.unpack_from("<I", head, 0)[0]
        name = names[t & 0xFFFF] if (t & 0xFFFF) < len(names) else "?"
        pos = struct.unpack_from("<3f", head, live.POS_AT)
        objs.append(dict(handle=(salt << 16) | i, type=typ, tag=f"{t:08x}", name=name, pos=[round(v, 4) for v in pos],
                         addr=f"{addr:x}", head=head.hex()))
        spans.append((addr, addr + 0x300))
    out["objects"] = objs
    print(f"{out['map']}: variant {out['variant']}, {len(objs)} objects", flush=True)
    strings = texts(ggb, gg)
    print("scanning memory for inv_ texts ...", flush=True)
    for base, size in live.g.regions():
        for off in range(0, size, CHUNK):
            blob = live.g.read(base + off, min(CHUNK, size - off))
            if blob:
                strings += [s for s in texts(blob, base + off) if not (gg <= s[0] < gg + 0x30000)]
            if len(strings) > 400:
                break
    out["strings"] = [(f"{a:x}", enc, s, f"gg+{a - gg:x}" if gg <= a < gg + 0x30000 else "") for a, enc, s in strings[:400]]
    print(f"  {len(strings)} texts, e.g. {sorted({s for _, _, s in strings})[:20]}", flush=True)
    # on a built-in Invasion map the scenario's labelled objects (objects.json netgame flags) are known: those first
    flagged = []
    fp = os.path.join(ROOT, "maps", "reach_" + (out["map"] or ""), "objects.json")
    if os.path.exists(fp):
        import math
        pts = [f["pos"] for f in json.load(open(fp, encoding="utf-8")).get("netgame_flags", []) if f.get("object")]
        flagged = [o for o in objs if any(math.dist(p, o["pos"]) < 0.05 for p in pts)]
    marks = (flagged + [o for o in objs if o not in flagged and any(w in o["name"].rsplit("\\", 1)[-1] for w in MARKERS)])
    marks = marks[:MAX_POS]
    print(f"searching memory for the positions of {len(marks)} marker objects ...", flush=True)
    needles = {o["handle"]: bytes.fromhex(o["head"])[live.POS_AT:live.POS_AT + 12] for o in marks}
    hits = scan(live.g, list(needles.values()), skip=spans)
    out["pos_hits"] = []
    for o in marks:
        for a in hits[needles[o["handle"]]]:
            around = live.g.read(a - 0x80, 0x100 + 12) or b""
            out["pos_hits"].append(dict(handle=o["handle"], name=o["name"].rsplit("\\", 1)[-1], addr=f"{a:x}",
                                        around=around.hex()))
    print(f"  {len(out['pos_hits'])} places hold a marker's position", flush=True)
    out["arrays"] = [dict(name=n, max=m, size=s, addr=f"{a:x}") for n, m, s, a, *_ in memread.data_arrays(live.g)]
    dst = os.path.join(ROOT, "logs", f"forge_label_probe_{tag}.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    print("saved", dst, flush=True)


if __name__ == "__main__":
    main()

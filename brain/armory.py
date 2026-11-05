"""The armor a bot wears where the game rolls it from its own Armory (Reach: native/reach.cpp hr_roll_armor, Halo 4:
native/h4f.cpp f_roll_armor), worked out offline so the profile view shows the exact pieces.
maps/_looks/<game>_armory.json (tools/armory_tables.py) holds the catalog botcore picks from, what each pick writes
into the appearance block, and which model pieces each written value means."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REACH = os.path.join(ROOT, "maps", "_looks", "reach_armory.json")
_cache = {}


def table(path=REACH):
    if path not in _cache:
        _cache[path] = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    return _cache[path]


def xorshift(x):
    """botcore's generator (32 bits: x ^= x << 13; x ^= x >> 17; x ^= x << 5)."""
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    return x ^ ((x << 5) & 0xFFFFFFFF)


def roll(seed, slots, none, catalog):
    """{slot: (item, variant)} as hr_roll_armor picks them: "none" slots first (the catalog's first item, variant 0),
    then each slot in the mask in order, one step for the item (also for a slot with no items) and one for the
    variant. catalog[slot] = [variant count per item]. Halo 4's f_roll_armor is the same while its none mask is 0,
    which it always is (its armor effect is a byte of its own, brain/looks.py)."""
    picks = {s: (0, 0) for s in range(len(catalog)) if none >> s & 1 and catalog[s]}
    x = seed or 0x9E3779B9
    for s, items in enumerate(catalog):
        if not slots >> s & 1:
            continue
        x = xorshift(x)
        if not items:
            continue
        item = x % len(items)
        x = xorshift(x)
        picks[s] = (item, x % items[item] if items[item] > 0 else 0)
    return picks


def appearance(picks, t):
    """{appearance block offset: value} the picks write (the game's own equip, logged per variant; a faulted equip
    writes nothing), or None when a pick's variant was not logged (Halo 4 before botcore s103: variants 0 and 1)."""
    out = {}
    for s, (item, v) in sorted(picks.items()):
        logged = t["writes"][s][item] if s < len(t["writes"]) and item < len(t["writes"][s]) else []
        if v >= len(logged):
            return None
        out.update({int(k): val for k, val in (logged[v] or {}).items()})
    return out


BODY = {"male": 0, "female": 1, "elite": 2}      # a record's mask bit: 1 << this (tools/armory_tables.py)


def pieces(app, body, t):
    """[(region, permutation)] the model wears: the base pieces (the female body over them), then each armor byte's
    option in order, a region's last record winning; records for the other body left out. Bytes 0x38-0x3E, or the
    table's own (spartan_bytes / elite_bytes: Reach's Elite its set byte 0x3F, Halo 3 each species its own eight);
    the effects (0x40, 0x41) are particles, not pieces."""
    bit = 1 << BODY[body]
    recs = list(t["elite_base"] if body == "elite" else t["base"] + (t["female"] if body == "female" else []))
    for off in t.get("elite_bytes" if body == "elite" else "spartan_bytes", range(0x38, 0x3F)):
        opts = t["options"].get(str(off), [])
        if off in app and 0 <= app[off] < len(opts):
            recs += opts[app[off]]
    worn = {}
    for region, perm, mask in recs:
        if not mask or mask & bit:
            worn[region] = perm
    return sorted(worn.items())

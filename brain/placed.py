"""The map's placed solid objects in the nav (a bot pushed 65 s into a crate the level mesh does not have, live on
Boneyard).

maps/<map>/objects.json "placed" (tools/reach_export.py): every scenery / crate / machine / control placement with its
rotation, megalo label and spawn flags. maps/_shapes/<game>.json (tools/object_shapes.py): each object's box from the
editing kit (collision model, else the physics model's boxes). A placement counts when it is in every game type (no
label, or no "hide unless megalo required" flag); game-type objects (Invasion's gates, Race's barriers) come and go and
are the modes' business (brain/invasion.py). Doors (they open), lifts (you ride them), energy fields and holograms
(beacons, markers) are left out. Terrain.add_blocks stamps the boxes into the level's wall heights, so paths go around
them and sight lines stop at them.
"""
import json
import math
import os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
SKIP_NAMES = ("door", "lift", "light", "camera", "cinematic", "skybox", "fx_", "sound", "hologram", "decal", "kill_volume",
              "danger_zone", "spawn", "marker", "beacon", "mp_circle", "flag_base", "health")
SKIP_MATERIALS = ("energy", "hologram")


def _shapes(game):
    p = os.path.join(ROOT, "_shapes", game + ".json")
    return json.load(open(p, encoding="utf-8"))["shapes"] if os.path.exists(p) else {}


def frame(rot, roll_sign=1.0):
    """(forward, left, up) unit vectors of a Halo placement's rotation (yaw, pitch, roll in degrees)."""
    y, p, r = (math.radians(v) for v in rot)
    r *= roll_sign
    f = (math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))
    l0 = (-math.sin(y), math.cos(y), 0.0)
    u0 = (-math.cos(y) * math.sin(p), -math.sin(y) * math.sin(p), math.cos(p))
    l = tuple(l0[k] * math.cos(r) + u0[k] * math.sin(r) for k in range(3))
    u = tuple(u0[k] * math.cos(r) - l0[k] * math.sin(r) for k in range(3))
    return f, l, u


def static_boxes(objs, game="reach"):
    """[(pos, (f, l, u), min, max, name)]: the solid objects present in every game type. A rolled object is given
    with both roll senses (the sign of Halo's roll is not checked: both are blocked, a little more than the object)."""
    shapes = _shapes(game)
    out = []
    for it in objs.get("placed", []):
        name, flags = it["name"], it.get("flags", "")
        # a game type's object: Reach names the flag; Halo 4 / H2A give the spawn flags as a number, bit 2 (4 on
        # Adrift's Extraction crates, CTF stands and hill beacons, 0 on its own crates; live)
        if it.get("label") and ("hide unless megalo required" in flags or (flags.isdigit() and int(flags) & 4)):
            continue
        if game != "reach" and it.get("kind") in ("machines", "controls"):
            continue                                  # (Halo 4's cranes, robot arms and lifts move)
        if any(s in name.lower() for s in SKIP_NAMES):
            continue
        s = shapes.get(name)
        if not s or any(m in s.get("material", "") for m in SKIP_MATERIALS):
            continue
        lo, hi = s["min"], s["max"]
        if hi[2] - lo[2] < 0.35 or (hi[0] - lo[0]) * (hi[1] - lo[1]) < 0.04:
            continue                                  # low or tiny: nothing a body bumps into
        rot = it.get("rot", [0, 0, 0])
        for sign in ((1.0, -1.0) if abs(rot[2]) > 1.0 else (1.0,)):
            out.append((tuple(it["pos"]), frame(rot, sign), lo, hi, name))
    return out

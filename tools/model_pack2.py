"""Pack a character model with its textures, posed, holding its weapon, for native/model_view.cpp:
native/bin/models/<name>.mdl (version 2) and its textures in native/bin/models/tex/.

Input: tools/model2obj with --uv --skin --tex (the OBJ, <obj>.skin, <obj>.mat.json, <obj>.markers.json and the PNGs),
and the weapon the same way. The pose: the gun held by the game's own hand markers (its grip on the right hand, a
two-handed gun's fore-end in the left), the arms bent to reach by two-bone IK, the forearms rolled for straight wrists,
the fingers closed on it; a turn of the chest and head and a stance in the legs. Linear blend skinning with the game's
own weights. A gun part the game colours from its shader's settings (Halo 2's guns) gets a flat gun colour (FLAT),
never the armor's.

  header   "HBMD", uint32 version 2, groups, vertices, indices, materials, then 6 floats bounds (min, max)
  material char name[48], 5 x char file[48] (diffuse, color_change, normal, self_illum, detail_normal; "" none),
           float detail tiling, float spare
  group    char region[24], char perm[32], int32 perm index, int32 kind, uint32 first, uint32 count, int32 material
  vertex   float3 position, float3 normal, float2 uv
  index    uint32
Region "weapon" is the held weapon (always drawn); kind 6: an energy sword's blade (drawn glowing). Reach's instanced
flair (model2obj's "<Instances>" group) is packed under each region / permutation that wears it (<obj>.regions.json
"owners"), so the panel picks it with its piece.

usage: python -I model_pack2.py <species: spartan|elite> <body.obj> <weapon.obj> <out.mdl> [--prefix h3] [--drop el_]
                                [--one-hand] [--hold "grip=f,l,u;barrel=f,l,u"] [--preview p.png] [--sticks p.png]
"""
import json
import os
import re
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model_pack import kind_of  # noqa: E402

SLOTS = ("diffuse", "color_change", "normal", "self_illum", "normal_detail")
TEX_SIZE = {"diffuse": 512, "color_change": 256, "normal": 512, "self_illum": 256, "normal_detail": 256}
# a gun part the game colours from its shader's settings, not a map (Halo 2's guns): (name part, colour, specular)
FLAT = [("luminous", (60, 120, 230), 60), ("lens", (20, 24, 32), 230), ("plasma", (104, 92, 150), 170),
        ("", (60, 62, 66), 150)]


def instance_owners(path):
    """{instance name: [(region, permutation index, permutation)]}: Reach's instanced flair (model2obj's "<Instances>"
    group) and the pieces that wear each one, from <obj>.regions.json "owners"; None for a model without."""
    if not os.path.exists(path):
        return None
    regions = json.load(open(path))
    index = {(r["name"], p): k for r in regions for k, p in enumerate(r["perms"])}
    out = None
    for r in regions:
        for name, owners in zip(r["perms"], r.get("owners", [])):
            out = out or {}
            out[name] = [(o.split("\\")[0], index[tuple(o.split("\\", 1))], o.split("\\", 1)[1]) for o in owners]
    return out


# meshes the game shows only for a moment, left out: Reach's Elite carries its assassination knives in its body mesh
# (elite_knifeblade_l / _r and their glow layers): they stood out of both fists as thin blue blades in every profile
HIDDEN = ("knifeblade",)


def read_obj(path, drop=(), owners=None):
    """owners (instance_owners): an instanced piece's faces go under each piece that wears it (none: left out)."""
    pos, nrm, uv, faces, cur = [], [], [], {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = line[:2]
            if t == "v ":
                pos.append(line.split()[1:4])
            elif t == "vn":
                nrm.append(line.split()[1:4])
            elif t == "vt":
                uv.append(line.split()[1:3])
            elif t == "g ":
                region, pi, perm, mat = line[2:].rstrip("\n").split("|")
                keys = ([(r, i, p, mat) for r, i, p in owners.get(perm, [])] if owners is not None and region == "<Instances>"
                        else [(region, int(pi), perm, mat)])
                # (H2A / Halo 4's placeholder pieces: material "invalid"; HIDDEN's)
                cur = [k for k in keys if not ((drop and k[2].startswith(drop)) or mat == "invalid"
                                               or any(h in mat for h in HIDDEN))]
                for k in cur:
                    faces.setdefault(k, [])
            elif t == "f " and cur:
                tri = [int(x.split("/")[0]) - 1 for x in line.split()[1:4]]
                for k in cur:
                    faces[k].extend(tri)
    pos = np.array(pos, np.float32)
    nrm = np.array(nrm, np.float32) if len(nrm) == len(pos) else np.zeros_like(pos)
    uv = np.array(uv, np.float32) if len(uv) == len(pos) else np.zeros((len(pos), 2), np.float32)
    return pos, nrm, uv, faces


def read_skin(path):
    b = open(path, "rb").read()
    assert b[:4] in (b"SKN1", b"SKN2"), path
    v2 = b[:4] == b"SKN2"
    n = struct.unpack_from("<i", b, 4)[0]
    o, bones, local = 8, [], []
    for _ in range(n):
        name = b[o:o + 64].split(b"\0")[0].decode()
        parent = struct.unpack_from("<i", b, o + 64)[0]
        m = np.array(struct.unpack_from("<16f", b, o + 68), np.float64).reshape(4, 4)
        local.append(np.array(struct.unpack_from("<16f", b, o + 132), np.float64).reshape(4, 4) if v2 else None)
        bones.append([name, parent, m])
        o += 64 + 4 + 64 + (64 if v2 else 0)
    if v2 and all(np.allclose(bn[2], np.eye(4)) for bn in bones):     # Halo CE: world matrices from the locals
        for k, bn in enumerate(bones):                                  # (parents come first)
            bn[2] = local[k] @ bones[bn[1]][2] if bn[1] >= 0 else local[k]
    bones = [tuple(bn) for bn in bones]
    nv = struct.unpack_from("<i", b, o)[0]
    rec = np.frombuffer(b, np.uint8, nv * 20, o + 4).reshape(nv, 20)
    idx = rec[:, :4].astype(np.int64)
    w = np.frombuffer(rec[:, 4:].tobytes(), np.float32).reshape(nv, 4).astype(np.float64)
    return bones, idx, w


def rot(axis, deg):
    """3x3 rotation about a unit axis (row-vector convention: v @ R)."""
    a = np.radians(deg)
    x, y, z = np.asarray(axis, float) / np.linalg.norm(axis)
    c, s, C = np.cos(a), np.sin(a), 1 - np.cos(a)
    R = np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                  [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                  [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])
    return R.T                                   # column-vector R -> row-vector form


def rot_between(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    v, c = np.cross(a, b), float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    return rot(v, np.degrees(np.arccos(np.clip(c, -1, 1))))


class Skeleton:
    """World (bind) matrices, row-vector convention (v_world = v_local @ M); pose by world rotations about joints."""
    def __init__(s, bones):
        s.names = [b[0] for b in bones]
        s.parent = [b[1] for b in bones]
        s.bind = [b[2] for b in bones]
        s.pose = [m.copy() for m in s.bind]
        s.kids = {i: [k for k, p in enumerate(s.parent) if p == i] for i in range(len(bones))}

    def i(s, name):
        for n in (name, "b_" + name, "bip01 " + name.replace("_", " ")):   # Reach, H2A, Halo 4: "b_r_hand"; CE:
            if n in s.names:                                                   # "bip01 r hand"
                return s.names.index(n)
        raise ValueError(f"no bone {name}")

    def pos(s, name):
        return s.pose[s.i(name)][3, :3].copy()

    def turn(s, name, R):
        """Rotate bone `name` and everything under it about its own joint by world rotation R (3x3 row form)."""
        s.turn_about(name, R, s.pose[s.i(name)][3, :3].copy())

    def turn_about(s, name, R, pivot):
        """Rotate bone `name` and everything under it about a world point by world rotation R (3x3 row form)."""
        j = s.i(name)
        pivot = np.asarray(pivot, float).copy()
        todo = [j]
        while todo:
            k = todo.pop()
            m = s.pose[k]
            m[:3, :3] = m[:3, :3] @ R
            m[3, :3] = (m[3, :3] - pivot) @ R + pivot
            todo += s.kids[k]

    def hinge(s, upper, lower, end):
        """The joint's own hinge in the upper bone's frame: the way the model's rest pose bends it (an elbow, a knee)."""
        a, b, c = (s.bind[s.i(n)][3, :3] for n in (upper, lower, end))
        h = np.cross(b - a, c - b)
        return h / max(np.linalg.norm(h), 1e-12) @ s.bind[s.i(upper)][:3, :3].T

    def ik(s, upper, lower, end, target, pole):
        """Two-bone IK: the end bone's joint onto target, the elbow / knee bent toward the pole direction (world), on its
        own hinge: the upper bone turned about itself so the joint bends the way the model's rest pose bends it."""
        a, b, c = s.pos(upper), s.pos(lower), s.pos(end)
        la, lb = np.linalg.norm(b - a), np.linalg.norm(c - b)
        t = np.asarray(target, float)
        d = float(np.clip(np.linalg.norm(t - a), abs(la - lb) * 1.01, (la + lb) * 0.999))
        axis = (t - a) / max(np.linalg.norm(t - a), 1e-9)
        t = a + axis * d
        side = np.asarray(pole, float) - np.dot(pole, axis) * axis
        side /= max(np.linalg.norm(side), 1e-9)
        cos_a = np.clip((la * la + d * d - lb * lb) / (2 * la * d), -1, 1)
        center, radius = a + axis * (la * cos_a), la * np.sqrt(1 - cos_a * cos_a)
        # the elbow on its circle near the pole where the joint's own hinge needs the least turn of the upper bone about
        # itself (a forced elbow direction twisted H2A's Elite's upper arm 83 degrees and its shoulder pad round with
        # it): a degree of twist saved for a degree off the pole
        hl, R0, perp = s.hinge(upper, lower, end), s.pose[s.i(upper)][:3, :3], np.cross(axis, side)

        def twist_for(el):
            h = hl @ (R0 @ rot_between(b - a, el - a))
            u = (el - a) / max(np.linalg.norm(el - a), 1e-9)
            n = np.cross(el - a, t - el)
            hp, nq = h - np.dot(h, u) * u, n - np.dot(n, u) * u
            if np.linalg.norm(hp) < 1e-9 or np.linalg.norm(nq) < 1e-9:
                return 0.0
            return float(np.degrees(np.arctan2(np.dot(np.cross(hp, nq), u), np.dot(hp, nq))))
        at = lambda ph: center + radius * (np.cos(np.radians(ph)) * side + np.sin(np.radians(ph)) * perp)
        phi = min(range(-60, 61, 5), key=lambda ph: abs(twist_for(at(ph))) + abs(ph)) if radius > 1e-6 else 0
        elbow = at(phi)
        s.turn(upper, rot_between(b - a, elbow - a))
        u = (elbow - a) / np.linalg.norm(elbow - a)
        n = np.cross(elbow - a, t - elbow)                    # the bend's own axis (it folds this way)
        if np.linalg.norm(n) > 1e-9:
            h = s.hinge(upper, lower, end) @ s.pose[s.i(upper)][:3, :3]
            hp, n_p = h - np.dot(h, u) * u, n - np.dot(n, u) * u
            if np.linalg.norm(hp) > 1e-9:
                ang = np.arctan2(np.dot(np.cross(hp, n_p), u), np.dot(hp, n_p))
                s.turn(upper, rot(u, np.degrees(ang)))        # the hinge square to the bend, the natural way round
        b, c = s.pos(lower), s.pos(end)
        s.turn(lower, rot_between(c - b, t - b))

    def skin(s, pos, nrm, idx, w):
        """Linear blend skinning from the bind to the pose."""
        out, outn = np.zeros_like(pos, np.float64), np.zeros_like(nrm, np.float64)
        P = np.ones((len(pos), 4))
        P[:, :3] = pos
        for k in range(len(s.bind)):
            sk = np.linalg.inv(s.bind[k]) @ s.pose[k]
            for slot in range(4):
                sel = (idx[:, slot] == k) & (w[:, slot] > 0)
                if not sel.any():
                    continue
                out[sel] += (P[sel] @ sk)[:, :3] * w[sel, slot, None]
                outn[sel] += (nrm[sel] @ sk[:3, :3]) * w[sel, slot, None]
        ws = w.sum(1, keepdims=True)
        outn /= np.maximum(np.linalg.norm(outn, axis=1, keepdims=True), 1e-9)
        return (out / np.maximum(ws, 1e-9)).astype(np.float32), outn.astype(np.float32)


FWD, LEFT, UP = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])   # the model faces +x


def qrow(q):
    """Row-form 3x3 rotation (v @ R) of a unit quaternion (x, y, z, w), as System.Numerics builds it."""
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                     [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
                     [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]])


def read_markers(path):
    """{name: (bone, pos, row rotation)} from model2obj's <obj>.markers.json (first instance of each name); {} without."""
    if not os.path.exists(path):
        return {}
    out = {}
    for m in json.load(open(path)):
        out.setdefault(m["name"].replace(" ", "_"), (m["bone"], np.array(m["pos"], float), qrow(m["rot"])))   # (CE: "right hand")
    return out


def gun_markers(weapon):
    """A held weapon's markers (read_markers), each with a 4th value: how far the gun's own surface is from it (pose_hold:
    a palm's marker lies on its grip, a wrist's a palm's width off it)."""
    wm = read_markers(weapon + ".markers.json")
    wpos, _, _, wfaces = read_obj(weapon)
    pts = np.vstack([wpos[f] for f in wfaces.values() if f]) if any(wfaces.values()) else wpos
    return {k: v + (float(np.linalg.norm(pts - v[1], axis=1).min()),) for k, v in wm.items()}


MARK_SPECIES = {"spartan": ("spartan", "cyborg", "mc"), "elite": ("elite",)}   # the games' names for a species in hand markers


def hand_mark(m, side, species):
    """A hand's marker: the species' own ("right_hand_elite", Halo: CE's "left hand cyborg") before the plain one; None
    without any."""
    return next((m[k] for k in [f"{side}_hand_{s}" for s in MARK_SPECIES[species]] + [f"{side}_hand"] if k in m), None)


def hand_axes(S, side="r"):
    """A hand's anatomy in its own bone frame: (fingers, channel, palm) unit vectors: from the hand joint to the index
    and ring knuckles, from the index knuckle to the pinky's, and the way the fingers close. None without finger bones
    (Halo: CE)."""
    try:
        h, idx, pin, ring, nxt = (S.i(f"{side}_{n}") for n in ("hand", "index1", "pinky1", "ring1", "index2"))
    except ValueError:
        return None
    inv = np.linalg.inv(S.bind[h])
    loc = lambda k: (np.r_[S.bind[k][3, :3], 1] @ inv)[:3]
    unit = lambda v: v / np.linalg.norm(v)
    fingers = unit(loc(idx) + loc(ring))
    channel = loc(pin) - loc(idx)
    channel = unit(channel - np.dot(channel, fingers) * fingers)
    palm = unit(np.cross(fingers, channel))
    return fingers, channel, palm if np.dot(palm, loc(nxt) - loc(idx)) >= 0 else -palm


def sword_turn(S, gr):
    """The hand marker's turn that puts a sword's hilt across the fist as Halo 3's does (the player passed it): its blade
    (+x) along the fingers, its hilt bar (+z) along the fist's channel, for the sword's own grip frame gr. Reach's and
    Halo 2: Anniversary's markers turned the bar through the palm. None without finger bones."""
    ax = hand_axes(S, "r")
    if ax is None:
        return None
    x, z = ax[0], -ax[1]
    z = z - np.dot(z, x) * x
    z /= np.linalg.norm(z)
    return gr @ np.array([x, np.cross(z, x), z])


def hand_hold(S, m, side, species):
    """Where a hand takes a gun, as a marker (bone, position and turn in the hand's frame): the hand marker's turn (the
    weapon's frame), at the skeleton's grip bone where it has one (Reach, Halo 2: Anniversary, Halo 4: b_r_grip, in the
    palm just short of the knuckles, as Halo 3's markers sit; their hand markers sit at the wrist joint or the heel of
    the palm, so a gun hung at the wrist and a sword's hilt outside the fist). The grip bone's own axes are not the
    weapon's (Halo 4's wrists turned 105-137 degrees by them)."""
    mk = hand_mark(m, side, species)
    try:
        g, h = S.i(f"{side[0]}_grip"), S.i(f"{side[0]}_hand")
    except ValueError:
        return mk
    G, Hb = S.bind[g], S.bind[h]
    pos = (G[3, :3] - Hb[3, :3]) @ Hb[:3, :3].T
    return (h, pos, mk[2] if mk is not None else G[:3, :3] @ Hb[:3, :3].T)


def frame(d, up):
    """Row-form rotation whose x axis is d and z axis the part of `up` square to it (a gun: barrel, top)."""
    x = np.asarray(d, float) / np.linalg.norm(d)
    z = np.asarray(up, float) - np.dot(up, x) * x
    z /= np.linalg.norm(z)
    return np.array([x, np.cross(z, x), z])


def mount(S, hand, upper, lower, marker, target_pos, target_rot, pole):
    """The hand where its marker (bone-space pos, rot) meets a target frame (the gun's grip or fore-end, world): the hand
    bone's rotation and joint from it, the arm bent to reach (two-bone IK toward the pole), the forearm rolled about
    itself to keep the wrist as straight as it goes. Returns the wrist's turn from the bind (degrees) and how far the
    hand fell short (units)."""
    mp, mr = marker[1], marker[2]                # (a gun marker may carry its surface distance: main)
    H = mr.T @ target_rot                       # marker world rot = mr @ H = target_rot
    wrist = np.asarray(target_pos, float) - mp @ H
    S.ik(upper, lower, hand, wrist, pole)
    f, h = S.i(lower), S.i(hand)
    axis = S.pose[h][3, :3] - S.pose[f][3, :3]  # (the wrist stays put as the forearm rolls about this)
    bind = S.bind[h][:3, :3] @ S.bind[f][:3, :3].T

    def turn_from_bind(t):
        D = H @ (S.pose[f][:3, :3] @ rot(axis, t)).T @ bind.T
        return np.degrees(np.arccos(np.clip((np.trace(D) - 1) / 2, -1, 1)))
    # the forearm's own turn for the straightest wrist (a rest pose's palms face down, so a hand under a fore-end turns
    # most of a half turn from it; the elbow bends on its own hinge: Skeleton.ik)
    t = min(range(-177, 178, 3), key=turn_from_bind)
    bend = turn_from_bind(t)
    roll_forearm(S, lower, hand, axis, t)
    S.turn(hand, S.pose[h][:3, :3].T @ H)
    return bend, float(np.linalg.norm(S.pos(hand) - wrist))


def roll_forearm(S, lower, hand, axis, t):
    """The forearm's roll about itself (t degrees), spread along its twist helpers where it has them (Halo 2:
    Anniversary, Halo 4, Reach: b_l_forearm_helper1-4, b_l_forearm_fixup, b_l_hand_twist, its Elite's helper_mult1-3):
    each by where it sits from the elbow to the wrist, the elbow's own pieces not at all, the hand fully, as the game
    turns them. Rolled whole at the elbow it tore the elbow armour. A forearm without helpers rolls whole (CE, Halo 2,
    Halo 3: the player passed Halo 2's that way)."""
    f, h = S.i(lower), S.i(hand)
    helpers = [k for k in S.kids[f] if k != h]
    if not helpers:
        S.turn(lower, rot(axis, t))
        return
    e, w = S.pose[f][3, :3], S.pose[h][3, :3]
    L = max(np.linalg.norm(w - e), 1e-9)
    for k in helpers:
        n = S.names[k]
        frac = (0.0 if "elbow" in n else 0.75 if "hand_twist" in n else 0.5 if "hand_half" in n
                else float(np.clip(np.dot(S.pose[k][3, :3] - e, axis / np.linalg.norm(axis)) / L, 0.0, 1.0)))
        S.turn(n, rot(axis, frac * t))
    S.turn(S.names[h], rot(axis, t))


def curl(S, side, deg):
    """Closes a hand: each finger joint turned deg (the thumb half) toward the palm, about the finger's own bend axis
    (the bind's slight curl; the hand's z where a finger is straight). Halo: CE's hands have no finger bones."""
    if not any(n.startswith((side + "_index", "b_" + side + "_index")) for n in S.names):
        return
    h = S.i(side + "_hand")
    Hb = S.bind[h]
    to_hand = np.linalg.inv(Hb)
    for finger in ("index", "middle", "ring", "pinky", "thumb"):
        chain = [k for k, n in enumerate(S.names) if n.startswith((f"{side}_{finger}", f"b_{side}_{finger}"))]
        if not chain:
            continue
        pts = [np.zeros(3)] + [(np.r_[S.bind[k][3, :3], 1] @ to_hand)[:3] for k in chain]
        seg = np.diff(pts, axis=0)
        n = sum(np.cross(seg[i], seg[i + 1]) for i in range(len(seg) - 1))
        local = n / np.linalg.norm(n) if np.linalg.norm(n) > 1e-7 else np.array([0, 0, 1.0])
        axis = local @ S.pose[h][:3, :3]
        for k in chain:
            S.turn(S.names[k], rot(axis, deg * (0.5 if finger == "thumb" else 1.0)))


# the hold per species: the figure's turn (negative: to its right), the chin (down, degrees), and in a Spartan's units,
# as (forward, left, up) from the pelvis: the right hand on the grip, the gun's barrel direction, the elbows' pulls (IK
# poles); twist: the chest and head turned back toward us (degrees); stance: each thigh out from the middle (degrees);
# upright: the torso turned back from the model's own lean (degrees; negative: further forward); a one-handed hold's
# free left hand: where it hangs (rest) and how far its fingers close (curl_l, degrees). Spartan (the player's picture,
# logs/tmp/owner_img_1.jpg: Master Chief at low ready): the rifle across the chest, the stock against the right of the
# chest, the right hand on the grip below the right pectoral with the elbow down at the side, the left hand under the
# fore-end by the left hip, the muzzle toward the left knee, the gun against the body but not in it. The legs under the
# hips. Elite (the player's picture, logs/tmp/owner_img_2.png): slouched forward, top-front heavy, the head forward and
# a little down ("some elite heads are facing too far up"; eve: Reach's "looking up too much"), the arms hanging out
# from its sides, the energy sword low in the right fist with the blade down and out, the left hand open like a claw,
# the feet a little wider than its own stance. Each model's own hold: make_models.MODELS; the checks:
# tools/test_model_pose.py.
HOLDS = {   # (the defaults: Halo 2's Spartan, the one the player passed; Halo 3's Elite)
    "spartan": dict(yaw=-16.0, chin=5.0, grip=(0.11, 0.01, 0.08), barrel=(0.35, 0.80, -0.45),
                    pole_r=(-0.3, -0.8, -0.5), pole_l=(-0.5, 0.5, -0.7), twist=9.0, stance=1.5),
    "elite": dict(yaw=14.0, chin=8.0, grip=(0.09, -0.21, -0.05), barrel=(0.45, -0.30, -0.84),
                  pole_r=(-0.6, -0.6, -0.4), pole_l=(-0.3, 0.8, -0.2), twist=0.0, stance=3.0, upright=-10.0,
                  rest=(0.10, 0.21, -0.05), curl_l=35.0),
}


def apply_hold(species, text):
    """A model's own hold over its species' (make_models: "grip=0.12,0,0.07;barrel=..;upright=10"): one number a
    degree value, several a vector."""
    for kv in text.split(";"):
        k, v = kv.split("=")
        x = tuple(float(c) for c in v.split(","))
        HOLDS[species][k] = x[0] if len(x) == 1 else x


VIEW = np.array([np.cos(0.35), np.sin(0.35), 0.0])   # toward the profile's camera as it opens (bots_panel.cpp g_yaw)


def pose_hold(S, species, bm, wm, two):
    """The profile pose with the gun on the hands by the game's own markers: the gun's origin, its grip, on the right
    hand's \"right_hand\" marker, and for a two-handed gun the left hand's \"left_hand\" marker on the gun's; the arms
    bent to reach (HOLDS). Returns the gun's frame (row rotation) and origin, and the wrists' bends and shortfalls. The
    stances are HOLDS': the Spartan turned a little to its right with the rifle across the body; the Elite square to us
    with the sword low in its right hand and the left hand open."""
    names = set(S.names)
    has = lambda n: n in names or "b_" + n in names or ("bip01 " + n.replace("_", " ")) in names
    elite = species == "elite"
    hold = HOLDS[species]
    Rz = rot(UP, hold["yaw"])
    S.turn("pelvis", Rz)                                       # the figure a little turned to its right
    fwd, left = FWD @ Rz, LEFT @ Rz
    vec = lambda c: fwd * c[0] + left * c[1] + UP * c[2]
    if hold.get("upright"):                                    # the torso back (negative: forward) from the model's own
        S.turn("spine" if has("spine") else "spine1", rot(left, -hold["upright"]))   # lean (its lowest spine bone)
    tw = hold["twist"]
    for n, R in (("spine1", rot(UP, tw)), ("head", rot(UP, tw * 1.1) @ rot(left, hold["chin"]))):
        if has(n):
            S.turn(n, R)                                       # the chest and head back toward us, the chin down a bit
    for side, sgn in (("l", 1), ("r", -1)):                    # feet a little apart: each thigh out from the middle
        if has(f"{side}_thigh"):
            S.turn(f"{side}_thigh", rot(fwd, hold["stance"] * sgn))
    relax = hold.get("relax", 1.0)                             # (0: both legs straight)
    if has("r_thigh") and has("r_calf") and not elite and relax:   # the weight on the left leg, the right knee easy
        S.turn("r_thigh", rot(left, -6 * relax))
        S.turn("r_calf", rot(left, 8 * relax))
    knees = hold.get("knees")
    if knees and all(has(f"{s}_{n}") for s in "lr" for n in ("thigh", "calf", "foot")):
        # knees bent on their own hinge with the feet planted: the hips lowered until the straighter leg bends `knees`
        # degrees, each foot put back where it stood (two-bone IK, the knee toward the front) and kept flat as it was
        feet = {s: (S.pos(f"{s}_foot"), S.pose[S.i(f"{s}_foot")][:3, :3].copy()) for s in "lr"}
        def reach(s):                                          # the hip-to-ankle length for that knee bend
            a, b, c = (S.pos(f"{s}_{n}") for n in ("thigh", "calf", "foot"))
            la, lb = np.linalg.norm(b - a), np.linalg.norm(c - b)
            return np.linalg.norm(c - a), np.sqrt(la * la + lb * lb + 2 * la * lb * np.cos(np.radians(knees)))
        drop = max(0.0, max(now - want for now, want in (reach("l"), reach("r"))))
        for m in S.pose:
            m[3, :3] -= UP * drop
        for s in "lr":
            S.ik(f"{s}_thigh", f"{s}_calf", f"{s}_foot", feet[s][0], fwd)
            f = S.i(f"{s}_foot")
            S.turn(f"{s}_foot", S.pose[f][:3, :3].T @ feet[s][1])
    pel = S.pos("pelvis")
    k = (S.pos("head")[2] - min(m[3, 2] for m in S.pose)) / 0.61   # sizes in a Spartan's units (head 0.61 over the feet)
    rh, lg = hand_hold(S, bm, "right", species), hand_mark(wm, "left", species)
    # the left hand takes the gun's left marker by the marker's own place: on the fore-end's surface it is a palm's
    # (the grip bone, hand_hold); a palm's width off it (Reach's left_hand_spartan, 0.024 u: its wrist joint) it is the
    # body's own hand marker at the wrist; wm's 4th value: the surface distance (main)
    wrist_left = lg is not None and len(lg) > 3 and lg[3] > 0.015
    lh = hand_mark(bm, "left", species) if wrist_left else hand_hold(S, bm, "left", species)
    # the gun's own grip marker (H2A, Halo 4); older guns: their origin (gun_origin: the origin even where it has one)
    rg = None if hold.get("gun_origin") else hand_mark(wm, "right", species)
    gp, gr = (rg[1], rg[2]) if rg is not None else (np.zeros(3), np.eye(3))
    if not two and rh is not None and sword_turn(S, gr) is not None:
        rh = (rh[0], rh[1], sword_turn(S, gr))                 # a sword's hilt across the fist, as Halo 3's
    two = two and lh is not None and lg is not None
    grip = pel + vec(hold["grip"]) * k
    d = vec(hold["barrel"]) / np.linalg.norm(vec(hold["barrel"]))
    top = np.cross(d, VIEW - np.dot(VIEW, d) * d)              # the gun's side to the viewer, its top up
    top = top if top[2] >= 0 else -top
    save = [m.copy() for m in S.pose]

    def hold_gun(roll):                     # the gun rolled about its barrel by roll degrees, the hands on it
        S.pose = [m.copy() for m in save]
        W = frame(d, top @ rot(d, roll))
        origin = grip - gp @ W
        out = {"right": mount(S, "r_hand", "r_upperarm", "r_forearm", rh, grip, gr @ W, vec(hold["pole_r"]))}
        if two:
            out["left"] = mount(S, "l_hand", "l_upperarm", "l_forearm", lh, lg[1] @ W + origin, lg[2] @ W,
                                vec(hold["pole_l"]))
        return W, origin, out
    # a roll from there where it keeps the wrists straighter, the hands on the gun: a rifle within 30 degrees (its side
    # to the viewer); a one-handed sword all the way round (turned to show its blades flat to us the hilt lay across a
    # knuckles-out fist, the wrist bent 34 degrees; in a hanging fist the hilt runs front to back and the blade carries
    # on from the forearm, as in the player's picture) A sword's fist shows its palm side to the camera, the fingers
    # round the hilt, as the player's picture ("Halo 2 Elite holding energy sword hand needs to do a 180, palm is facing
    # away from the camera")
    rolls, per = (range(-30, 31, 5), 0.5) if two else (range(-180, 180, 10), 0.05)
    axes = hand_axes(S, "r") if not two else None

    def palm_away():
        if axes is None:
            return 0.0
        return 60.0 * max(0.0, 0.8 - float(np.dot(axes[2] @ S.pose[S.i("r_hand")][:3, :3], VIEW)))
    cost = lambda a, o: (max(b for b, _ in o.values()) + per * abs(a) + 1000 * sum(sh for _, sh in o.values())
                         + palm_away())
    roll = min(rolls, key=lambda a: cost(a, hold_gun(a)[2]))
    W, grip, out = hold_gun(roll)
    curl(S, "r", 55)                                           # the hands closed on the gun
    if two:
        curl(S, "l", 55)
    elif has("l_hand"):
        rest = pel + vec(hold.get("rest", (0.04, 0.17, -0.05))) * k   # hanging a little out from its side
        S.ik("l_upperarm", "l_forearm", "l_hand", rest, pole=left * 0.6 - UP * 0.2 - fwd * 0.6)
        curl(S, "l", hold.get("curl_l", 20.0))                 # (a loose hand; the Elite's open claw)
    return W, grip, out


def shrink(src, dst, size, jpg, channel="Default"):
    """The texture, at most size on a side; channel (Halo CE's multipurpose map packs several in one picture: colour
    change in blue, self-illumination in green): that channel alone, as red (the colour-change primary) and grey."""
    from PIL import Image
    im = Image.open(src)
    if channel == "Surface":         # Halo 2: Anniversary's armor surface (..._s): light grey with its panel detail, the
        g = im.convert("L")             # map itself the specular mask (the player colour carries the colour)
        if max(g.size) > size:          # (shrunk alone: Pillow shrinks RGBA premultiplied, and where this mask is 0 the
            k = size / max(g.size)      # grey went black: the Elite's dark maps came out blotched)
            g = g.resize((max(1, int(g.size[0] * k)), max(1, int(g.size[1] * k))), Image.LANCZOS)
        rgb = g.point(lambda v: 158 + v * 97 // 255)
        im = Image.merge("RGBA", (rgb, rgb, rgb, g))
    if channel == "Control":            # Halo 4's armor control map as the diffuse: its green the albedo, its red the
        rgba = im.convert("RGBA")       # specular mask
        g = rgba.getchannel("G")
        im = Image.merge("RGBA", (g, g, g, rgba.getchannel("R")))
    elif channel in ("Red", "Green", "Blue", "Alpha"):
        c = im.convert("RGBA").getchannel(channel[0] if channel != "Alpha" else "A")
        black = Image.new("L", im.size, 0)
        if dst.endswith("color_change.png") and channel == "Alpha":   # Halo 4's colour mask: three levels, white the
            im = Image.merge("RGBA", (c.point(lambda v: min(255, max(0, (v - 150) * 5))),   # main plates (primary),
                                      c.point(lambda v: max(0, 255 - abs(v - 100) * 5)),    # ~100 the trim (taken as
                                      black, Image.new("L", im.size, 255)))                 # the secondary), 0 none
        elif dst.endswith("color_change.png"):
            im = Image.merge("RGBA", (c, black, black, Image.new("L", im.size, 255)))
        else:
            im = Image.merge("RGB", (c, c, c))
    if im.size[0] > size or im.size[1] > size:
        k = size / max(im.size)
        im = im.resize((max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k))), Image.LANCZOS)
    if jpg:
        im.convert("RGB").save(dst, quality=88)
    else:
        im.save(dst)


def slot_of(m, entries):
    """A map's slot. Halo 2: Anniversary's armor lists two "diffuse" maps: ..._s is the surface (grey albedo), ..._d
    the player colour mask (red primary, green secondary islands, checked by eye); its ..._c1 is a control map."""
    u, b = m["usage"], m.get("bitmap", "").lower()
    pair = {e.get("bitmap", "").lower()[-2:] for e in entries if e["usage"] == "diffuse"} >= {"_s", "_d"}
    if pair and u == "diffuse":
        return "diffuse" if b.endswith("_s") else "color_change" if b.endswith("_d") else u
    if u == "other" and m.get("channel") == "Alpha" and b.endswith("_control"):
        return "color_change"           # Halo 4's armor: its control map's alpha is the colour mask ("cm" in its shader's
    return "control" if pair and b.endswith("_c1") else u   # control_map_spdiglcm: specular, diffuse, gloss, colour mask)


def flat_part(outdir, prefix, name, slot, maps):
    """A gun part's map the game makes from its shader's settings (FLAT): a flat diffuse (dark under the part's own glow
    map), a glow for its luminous parts; "" for the others. (A gun never wears the armor colour.)"""
    from PIL import Image
    if slot == "diffuse":
        rgb, spec = ((14, 14, 16), 40) if "self_illum" in maps else next((c, s) for k, c, s in FLAT if k in name.lower())
    elif slot == "self_illum" and "luminous" in name.lower():
        rgb, spec = (70, 150, 255), 255
    else:
        return ""
    fn = f"{prefix}_{re.sub(r'[^A-Za-z0-9]+', '_', name)}_flat_{slot}.png"
    if len(fn) > 47:                                           # (the .mdl keeps 47 characters of a file name)
        fn = f"{prefix}_flat{zlib.crc32(name.encode()):08x}_{slot}.png"
    Image.new("RGBA", (4, 4), (*rgb, spec)).save(os.path.join(outdir, fn))
    return fn


def materials(matjson, texdir, outdir, prefix, used, weapon=False):
    """[(name, files[5], tiling)] for the used materials, their textures shrunk into outdir (shared by file)."""
    data = json.load(open(matjson))
    os.makedirs(outdir, exist_ok=True)
    out, done = [], {}
    for name in used:
        files, tiling = [], 1.0
        entries = [m for m in data.get(name, []) if m.get("file")]
        maps = {slot_of(m, entries): m for m in entries}
        h2a_armor = {e.get("bitmap", "").lower()[-2:] for e in entries if e["usage"] == "diffuse"} >= {"_s", "_d"}
        for slot in SLOTS:
            m = maps.get(slot)
            if m is None:
                files.append(flat_part(outdir, prefix, name, slot, maps) if weapon else "")
                continue
            jpg = slot in ("normal", "normal_detail") or (slot == "diffuse" and False)
            ch = "Surface" if slot == "diffuse" and h2a_armor else m.get("channel", "Default")
            if slot == "diffuse" and ch == "Green" and m.get("bitmap", "").lower().endswith("_control"):
                ch = "Control"                 # (Halo 4's armor: the albedo with its specular mask)
            tag = "" if ch == "Default" else ch[0].lower()
            fn = f"{prefix}_{os.path.splitext(m['file'])[0]}{tag}_{slot}." + ("jpg" if jpg else "png")
            if fn not in done:
                shrink(os.path.join(texdir, m["file"]), os.path.join(outdir, fn), TEX_SIZE[slot], jpg, ch)
                done[fn] = True
            files.append(fn)
            if slot == "normal_detail":
                tiling = float(m["tiling"][0])
        out.append((name, files, tiling))
    return out


def main():
    species, body, weapon, out = sys.argv[1:5]
    drop = tuple(sys.argv[sys.argv.index("--drop") + 1].split(",")) if "--drop" in sys.argv else ()
    pos, nrm, uv, faces = read_obj(body, drop, instance_owners(body + ".regions.json"))
    bones, idx, w = read_skin(body + ".skin")
    S = Skeleton(bones)
    wpos, wnrm, wuv, wfaces = read_obj(weapon)
    wdata = json.load(open(weapon + ".mat.json"))             # parts with no maps at all (Halo 2's ammo digits and heat
    drawn = lambda mat: any(m.get("file") and m["usage"] in SLOTS + ("diffuse_detail", "reflection_cube")
                            for m in wdata.get(mat, []))       # gauge: the game's own shaders) are left out
    wfaces = {k: f for k, f in wfaces.items() if drawn(k[3]) or k[0] == "blade"}   # (an energy blade: the game's own
    wfaces = {k: f for k, f in wfaces.items()                     # shader) and only its default permutation (Halo 2's
              if k[2] == "default" or not any(j[0] == k[0] and j[2] == "default" for j in wfaces)}   # sword: "noblade")
    glow = {"W:" + k[3] for k in wfaces if k[0] == "blade"}         # its blade glows (model_view.cpp kind 6)
    bm, wm = read_markers(body + ".markers.json"), gun_markers(weapon)
    if "--hold" in sys.argv:                               # a model's own hold (make_models): "grip=0.12,0,0.07;barrel=.."
        apply_hold(species, sys.argv[sys.argv.index("--hold") + 1])
    if hand_mark(bm, "right", species) is None:
        sys.exit(f"{body}: no right hand marker (export it with tools/model2obj, which writes <obj>.markers.json)")
    W, grip, fit = pose_hold(S, species, bm, wm, "--one-hand" not in sys.argv)
    print("hands: " + ", ".join(f"{h} wrist turn {b:.0f} deg, short {sh:.3f} u" for h, (b, sh) in fit.items()))
    if "--sticks" in sys.argv:
        sticks(S, grip, grip + W[0] * 0.15, sys.argv[sys.argv.index("--sticks") + 1])
        return
    pos, nrm = S.skin(pos, nrm, idx, w)
    wpos, wnrm = (wpos @ W + grip).astype(np.float32), (wnrm @ W).astype(np.float32)   # the gun in the hands
    # merge: the weapon's vertices after the body's, its groups as region "weapon"
    nb = len(pos)
    pos, nrm, uv = np.vstack([pos, wpos]), np.vstack([nrm, wnrm]), np.vstack([uv, wuv])
    allf = dict(faces)
    for (region, pi, perm, mat), f in wfaces.items():
        allf[("weapon", 0, "weapon", "W:" + mat)] = allf.get(("weapon", 0, "weapon", "W:" + mat), []) + [i + nb for i in f]
    gear = sys.argv[sys.argv.index("--gear") + 1] if "--gear" in sys.argv else None
    if gear:
        # a model of its own the game hangs on the body by a marker of the same name (Halo 3's MCC backpacks, the
        # mp_masterchief gear model's chest_flair on the body's "backpack" marker): "<obj>|region=marker...", each
        # region's pieces put where its marker meets the posed body's, as the game draws them
        gobj, spec = gear.split("|")
        want = dict(kv.split("=") for kv in spec.split(","))
        gpos, gnrm, guv, gfaces = read_obj(gobj)
        gm = read_markers(gobj + ".markers.json")
        gbones = read_skin(gobj + ".skin")[0] if os.path.exists(gobj + ".skin") else None
        n0 = len(pos)
        blocks = [(pos, nrm, uv)]
        for region, marker in want.items():
            if marker not in gm or marker not in bm:
                sys.exit(f"{gobj}: no marker {marker!r} on the gear or the body")
            gb, gp, gr = gm[marker]
            G = gbones[gb][2] if gbones else np.eye(4)
            gpw, grw = gp @ G[:3, :3] + G[3, :3], gr @ G[:3, :3]        # the gear's marker in its model's space
            bb, bp, br = bm[marker]
            P = S.pose[bb]
            bpw, brw = bp @ P[:3, :3] + P[3, :3], br @ P[:3, :3]        # the body's, posed
            T = grw.T @ brw
            keys = [k for k in gfaces if k[0] == region]
            used_v = sorted({i for k in keys for i in gfaces[k]})
            vmap = {i: n0 + j for j, i in enumerate(used_v)}
            blocks.append((((gpos[used_v] - gpw) @ T + bpw).astype(np.float32), (gnrm[used_v] @ T).astype(np.float32),
                           guv[used_v]))
            n0 += len(used_v)
            for (rg, pi, perm, mat) in keys:
                allf[(rg, pi, perm, "G:" + mat)] = allf.get((rg, pi, perm, "G:" + mat), []) + [vmap[i] for i in gfaces[(rg, pi, perm, mat)]]
        pos, nrm, uv = (np.vstack([b[k] for b in blocks]) for k in range(3))
    used = sorted({k[3] for k in allf})
    outdir = os.path.join(os.path.dirname(os.path.abspath(out)), "tex")
    prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "h3"
    bmats = materials(body + ".mat.json", os.path.join(os.path.dirname(body), "tex"), outdir, prefix + species,
                      [u for u in used if not u.startswith(("W:", "G:"))])
    wmats = materials(weapon + ".mat.json", os.path.join(os.path.dirname(weapon), "tex"), outdir, prefix + species + "w",
                      [u[2:] for u in used if u.startswith("W:")], weapon=True)
    mats = {m[0]: m for m in bmats}
    mats.update({"W:" + m[0]: ("W:" + m[0], m[1], m[2]) for m in wmats})
    if gear:
        gmats = materials(gobj + ".mat.json", os.path.join(os.path.dirname(gobj), "tex"), outdir, prefix + species + "g",
                          [u[2:] for u in used if u.startswith("G:")])
        mats.update({"G:" + m[0]: ("G:" + m[0], m[1], m[2]) for m in gmats})
    mat_index = {name: k for k, name in enumerate(used)}
    keep = sorted({i for f in allf.values() for i in f})
    remap = np.full(len(pos), -1, np.int64)
    remap[keep] = np.arange(len(keep))
    verts = np.hstack([pos[keep], nrm[keep], uv[keep]]).astype(np.float32)
    table, ind = [], []
    for (region, pi, perm, mat), f in sorted(allf.items()):
        if not f:
            continue
        kind = 6 if mat in glow else kind_of(mat[2:] if mat.startswith(("W:", "G:")) else mat)
        table.append((region, perm, pi, kind, len(ind), len(f), mat_index[mat]))
        ind.extend(remap[f].tolist())
    ind = np.array(ind, np.uint32)
    lo, hi = verts[:, :3].min(0), verts[:, :3].max(0)
    with open(out, "wb") as fh:
        fh.write(b"HBMD" + struct.pack("<IIIII", 2, len(table), len(verts), len(ind), len(used)) + struct.pack("<6f", *lo, *hi))
        for name in used:
            _, files, tiling = mats.get(name, (name, [""] * 5, 1.0))
            fh.write(name.encode()[:47].ljust(48, b"\0"))
            for fn in files:
                assert len(fn.encode()) <= 47, f"texture file name too long for the .mdl: {fn}"
                fh.write(fn.encode().ljust(48, b"\0"))
            fh.write(struct.pack("<2f", tiling, 0.0))
        for region, perm, pi, kind, first, n, mi in table:
            fh.write(region.encode()[:23].ljust(24, b"\0") + perm.encode()[:31].ljust(32, b"\0")
                     + struct.pack("<iiIIi", pi, kind, first, n, mi))
        fh.write(verts.tobytes())
        fh.write(ind.tobytes())
    print(f"{out}: {len(table)} groups, {len(verts)} vertices, {len(ind) // 3} triangles, {len(used)} materials, "
          f"{os.path.getsize(out) / 1e6:.1f} MB, bounds {lo.round(2)} .. {hi.round(2)}")
    if "--preview" in sys.argv:
        preview(verts[:, :3], sys.argv[sys.argv.index("--preview") + 1])


def sticks(S, grip, fore, path):
    """The posed skeleton front and side, with the hand targets: checks the pose in a second."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 600), (25, 25, 30))
    d = ImageDraw.Draw(img)
    for ox, ax in ((200, 1), (600, 0)):                       # front: screen x = world y; side: screen x = world x
        P = lambda q: (ox - q[ax] * 600 if ax == 1 else ox + q[0] * 600, 560 - q[2] * 650)
        for k, par in enumerate(S.parent):
            if par >= 0 and not any(t in S.names[k] for t in ("index", "middle", "pinky", "ring", "thumb")):
                d.line([P(S.pose[par][3, :3]), P(S.pose[k][3, :3])], fill=(220, 220, 220), width=3)
        for q, col in ((grip, (255, 80, 80)), (fore, (80, 255, 80))):
            x, y = P(q)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=col, width=2)
        d.line([P(grip), P(fore)], fill=(255, 200, 0), width=2)
    img.save(path)


def preview(p, path):
    """A quick point picture from the front-right (the panel's view direction): checks the pose without the panel."""
    from PIL import Image
    yaw = np.radians(-25)
    x = p[:, 1] * np.cos(yaw) + p[:, 0] * np.sin(yaw)
    d = p[:, 0] * np.cos(yaw) - p[:, 1] * np.sin(yaw)
    z = p[:, 2]
    W, H = 500, 700
    sx = ((x - x.min()) / (z.max() - z.min()) * (H - 40) + 20).astype(int)
    sy = (H - 20 - (z - z.min()) / (z.max() - z.min()) * (H - 40)).astype(int)
    img = np.zeros((H, W, 3), np.uint8) + 30
    order = np.argsort(-d)
    shade = (120 + 135 * (d - d.min()) / max(1e-6, d.max() - d.min())).astype(np.uint8)
    ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    for k in order[ok[order]]:
        img[sy[k], sx[k]] = shade[k]
    Image.fromarray(img).save(path)


if __name__ == "__main__":
    main()

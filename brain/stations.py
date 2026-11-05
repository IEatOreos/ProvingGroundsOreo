"""Every gameplay object on the running map, by kind, kept per map or Forge layout, for LiDAR and the bots' map
knowledge: armor abilities, teleporters, man cannons, lifts and the rest.

scan(live, game): the object table read whole, each object named by the map's own tag names (tools/reach_tag_names.py:
Halo 3, Reach, Halo 4, H2A, the games with Forge) and sorted by classify(): armor abilities and equipment to pick up,
teleporters (sender, receiver, two-way), man cannons, gravity lifts, power-ups, health, ammo, grenades, weapons and
vehicles where they spawn, objectives, spawn points, kill / safe / trait zones, switches. Building pieces are not
stations (the nav has them: brain/forge.py).

Stations keeps them in maps/<map>/stations.json (a layout's folder for a Forge layout: brain/variants.py):
  {"objects": [{kind, what, pos, fwd, seen, last}], "teleports": [[from, to, times]], "marks": [{text, pos, stamp, t,
   near: [[kind, what, pos, dist]]}]}
A held or carried thing is kept where it lay before anyone took it (its spawn), a vehicle where it stood before anyone
rode it; an object moved in Forge with nobody on it follows. Teleporter pairs are learned from people and bots going
through them (a jump from beside a sender to beside a receiver). Marks are the player's bug reports (tools/bug_reports.py)
with the stations nearest to him then. Objects not seen in a run of RUN_MIN s or more are gone from the layout.
"""
import json
import math
import os
import re
import struct
import time

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
NONE = 0xFFFFFFFF
MERGE_R = 1.5        # u: a respawned copy this near a kept spot of its kind is that spot
VEHICLE_R = 3.0      # u: (a vehicle settles on its wheels farther off)
MOVED_R = 0.5        # u: an object this far from its kept spot was moved (in Forge)
HELD_R = 1.5         # u: a thing to hold this near a living player has been taken, not moved
TELE_JUMP = 6.0      # u in one step: a teleport (or a respawn: only near a teleporter counts)
TELE_NEAR = 2.5      # u: a teleporter this near where the jump began / ended is the one used
NEAR_R, NEAR_N = 12.0, 5   # a mark's nearest stations
RUN_MIN = 60.0       # s: a run this long that never saw an object: it is gone from the layout
HOLDABLE = {"ability", "powerup", "health", "ammo", "grenade", "weapon", "objective"}
# the object's place, forward and up in its header, per game (brain/forge.py AXES_AT; Halo 3: its place only)
AXES = {"reach": (0x44, 0x50, 0x5C), "h4": (0x64, 0x70, 0x7C), "h2a": (0x64, 0x70, 0x7C)}
# an armor ability's or equipment's tag name -> the brain's kind (brain/live.py TYPE_ORDER, brain/equipment.py NAMES)
ABILITY = {"jet_pack": "jetpack", "armor_lockup": "armor_lock", "active_camouflage": "active_camo", "evade": "evade",
           "sprint": "sprint", "hologram": "hologram", "drop_shield": "drop_shield", "equipment_pack": "equipment_pack",
           "storm_jet_pack": "jetpack", "storm_jet_pack_pve": "jetpack", "storm_thruster_pack": "thruster",
           "storm_active_camo": "active_camo", "storm_active_shield": "hardlight_shield", "storm_hologram": "hologram",
           "storm_auto_turret": "autosentry", "storm_forerunner_vision": "promethean_vision",
           "storm_regen_field": "regen_field", "storm_equipment_pack": "equipment_pack",
           "bubbleshield_equipment": "bubble_shield", "powerdrain_equipment": "power_drain",
           "regenerator_equipment": "regenerator", "tripmine_equipment": "trip_mine", "gravlift_equipment": "grav_lift",
           "instantcover_equipment": "deployable_cover", "instantcover_equipment_mp": "deployable_cover",
           "superflare_equipment": "flare", "jammer_equipment": "radar_jammer", "autoturret_equipment": "auto_turret",
           "invincibility_equipment": "invincibility", "invisibility_equipment": "invisibility"}
ZONES = [(r"soft_?kill|kill_volume|kill_zone|kill_boundary", "kill_zone"), (r"soft_?safe|safe_volume|safe_zone", "safe_zone"),
         (r"trait_zone", "trait_zone"), (r"anti_respawn|respawn_zone", "spawn_zone")]


def classify(path, typ):
    """(kind, what) of an object by its tag path and object type (1 vehicle, 2 weapon in every game here), or (None,
    None): not a station (a building piece, a deployed shield, a light ...)."""
    p = (path or "").lower()
    n = p.rsplit("\\", 1)[-1]
    if not n:
        return None, None
    if "teleport" in n and "frame" not in n:
        side = ("2way" if re.search(r"2_?way|two_way", n) else "receiver" if re.search(r"rec(ei|ie)ver", n) else
                "sender" if "sender" in n else "")
        return "teleporter", side or "teleporter"
    if re.search(r"man_?cannon|cannon_man|cannon_vehicle|veh_man_cannon", n):
        return "launcher", n
    if re.search(r"grav_?lift", n) and "\\equipment\\" not in p or n == "gravlift_permanent":
        return "lift", n
    if "\\equipment\\" in p:
        # the thing to pick up: its own folder (objects\equipment\jet_pack\jet_pack); a deployed one (Halo 3's
        # bubbleshield, Halo 4's turret, a hologram biped) is no station
        if n in ABILITY:
            return "ability", ABILITY[n]
        if n == "health_pack":
            return "health", n
        return None, None
    if re.search(r"_ammo$|\\ammo\\", p):
        return "ammo", n
    if "powerup" in p or n in ("overshield", "active_camo_powerup", "custom_powerup"):
        return "powerup", n
    for pat, kind in ZONES:
        if re.search(pat, n):
            return kind, n
    # (before spawns: Halo 3's ctf_flag_spawn_point and assault_bomb_spawn_point are objectives' stands, not players'.
    # mp_flag_base: Reach's Forge objective marker, every game type's (flag stands, plates, hills on a layout))
    if re.search(r"^(ctf_)?flag$|ff_flag|flag_stand|flag_spawn|flag_return|mp_flag_base|oddball|assault_bomb|bomb_spawn|bomb_goal|"
                 r"goal_area|koth_hill|hill_marker|hill_beacon|territor|capture_plate|skull", n):
        return "objective", n
    if re.search(r"respawn_point|initial_spawn_point|spawn_point", n):
        return "spawn", n
    if re.search(r"switch|button|terminal|control_panel|lever", n):
        return "control", n
    if typ == 1:
        return "vehicle", n
    if typ == 2:
        return ("grenade" if "grenade" in n else "weapon"), n
    return None, None


def tag_names(live, game):
    """The running map's tag names by index (cached per map: tools/reach_tag_names.py); [] in a game without them."""
    import sys
    cache = getattr(live, "_station_names", None)
    if cache is not None:
        return cache
    names = []
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "tools"))
        import reach_tag_names
        if game in reach_tag_names.GAME_DIR:
            map_file = live.map_name().replace("/", "\\").rsplit("\\", 1)[-1]
            names = reach_tag_names.cached(map_file, game)
    except Exception as e:                         # (no names: no stations this match; the brain plays on)
        print(f"stations: no tag names ({type(e).__name__}: {e})", flush=True)
    live._station_names = names
    return names


def scan(live, game, names=None):
    """[{h, kind, what, pos, fwd, parent}] of the running match's stations (classify), from the object table."""
    names = tag_names(live, game) if names is None else names
    if not names:
        return []
    pos_at, fwd_at, _ = AXES.get(game, (live.POS_AT, None, None))
    tag_at, par_at = getattr(live, "TAG_AT", 0), getattr(live, "PARENT_AT", 0x14)
    ents, mx, _ = live._array(live.OBJECTS_AT)
    b = live.g.read(ents, mx * 0x18)
    size = max(pos_at, fwd_at or 0, par_at, tag_at) + 12
    out, rides_on = [], {}                           # (parent handle -> what rides on it: a Warthog's gun or troop bed)
    for i in range(mx):
        salt = struct.unpack_from("<H", b, i * 0x18)[0]
        if not salt:
            continue
        typ = b[i * 0x18 + live.TYPE_AT]
        try:
            head = live.g.read(struct.unpack_from("<Q", b, i * 0x18 + 0x10)[0], size)
        except OSError:
            continue
        if not head or len(head) < size:
            continue
        tag = struct.unpack_from("<I", head, tag_at)[0] & 0xFFFF
        parent = struct.unpack_from("<I", head, par_at)[0]
        if parent != NONE and tag < len(names):
            rides_on.setdefault(parent, []).append(names[tag].rsplit("\\", 1)[-1])
        kind, what = classify(names[tag] if tag < len(names) else "", typ)
        if kind is None:
            continue
        pos = struct.unpack_from("<3f", head, pos_at)
        if not all(math.isfinite(v) for v in pos):
            continue
        out.append(dict(h=(salt << 16) | i, kind=kind, what=what, pos=tuple(round(v, 2) for v in pos),
                        fwd=tuple(round(v, 3) for v in struct.unpack_from("<3f", head, fwd_at)) if fwd_at else None,
                        parent=parent))
    from .vehicles import variant                    # a Warthog by what rides on it: gauss, rocket, transport (thog)
    for o in out:
        if o["kind"] == "vehicle" and o["h"] in rides_on:
            o["what"] = variant(o["what"], rides_on[o["h"]])
    return out


def path_of(map_name):
    return os.path.join(ROOT, map_name, "stations.json")


def load(map_name):
    try:
        d = json.load(open(path_of(map_name), encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"objects": d.get("objects", []), "teleports": d.get("teleports", []), "marks": d.get("marks", [])}


class Stations:
    def __init__(s, map_name, clock=time.time):
        s.map, s.clock = map_name, clock
        d = load(map_name)
        s.objects, s.teleports, s.marks = d["objects"], d["teleports"], d["marks"]
        s.by_handle, s.held, s.ridden, s.last_at = {}, set(), set(), {}
        s.seen_run, s.started, s.version = set(), None, 0

    def _find(s, kind, what, pos):
        r = VEHICLE_R if kind == "vehicle" else MERGE_R
        best = min((o for o in s.objects if o["kind"] == kind and o["what"] == what),
                   key=lambda o: math.dist(o["pos"], pos), default=None)
        return best if best is not None and math.dist(best["pos"], pos) <= r else None

    def update(s, objs, ridden=(), people=()):
        """A scan's objects (scan()); ridden: handles of vehicles someone sits in now; people: where the living players
        are (a thing to hold that moved to beside one is in his hands, where the game keeps no parent for it)."""
        now = s.clock()
        s.started = s.started or now
        s.ridden |= set(ridden)
        for o in objs:
            h = o["h"]
            if o["parent"] != NONE:
                if o["kind"] in HOLDABLE:
                    s.held.add(h)               # in a hand, a backpack, on a vehicle: where it lay before is its spot
                continue                         # (a gun riding a vehicle, a piece attached to another: not a station)
            if h in s.held:
                continue                         # dropped where its holder died or let it go: no spawn
            e = s.by_handle.get(h)
            if e is None:
                e = s._find(o["kind"], o["what"], o["pos"])
                if e is None:
                    e = dict(kind=o["kind"], what=o["what"], pos=list(o["pos"]), fwd=list(o["fwd"]) if o["fwd"] else None,
                             seen=round(now))
                    s.objects.append(e)
                    s.version += 1
                s.by_handle[h] = e
            elif (math.dist(e["pos"], o["pos"]) > MOVED_R and h not in s.ridden
                  and not (o["kind"] in HOLDABLE and any(math.dist(q, o["pos"]) < HELD_R for q in people))):
                e["pos"], e["fwd"] = list(o["pos"]), list(o["fwd"]) if o["fwd"] else None   # moved in Forge
                s.version += 1
            e["last"] = round(now)
            s.seen_run.add(id(e))

    def watch(s, players):
        """[(id, (x, y, z) or None, alive)] each tick: a jump from beside a sender (or two-way) to beside a receiver (or
        two-way) is that pair's teleport."""
        for pid, pos, alive in players:
            last = s.last_at.get(pid)
            pos = pos if alive and pos is not None and all(math.isfinite(v) for v in pos) else None
            s.last_at[pid] = pos
            if last is None or pos is None or not alive or math.dist(last, pos) < TELE_JUMP:
                continue
            a = s._near_tele(last, ("sender", "2way"))
            b = s._near_tele(pos, ("receiver", "2way"))
            if a is None or b is None or a is b:
                continue
            for t in s.teleports:
                if math.dist(t[0], a["pos"]) < 0.5 and math.dist(t[1], b["pos"]) < 0.5:
                    t[2] += 1
                    break
            else:
                s.teleports.append([list(a["pos"]), list(b["pos"]), 1])
                s.version += 1

    def _near_tele(s, pos, sides):
        best = min((o for o in s.objects if o["kind"] == "teleporter" and o["what"] in sides),
                   key=lambda o: math.dist(o["pos"], pos), default=None)
        return best if best is not None and math.dist(best["pos"], pos) <= TELE_NEAR else None

    def near(s, pos, r=NEAR_R, n=NEAR_N):
        """[[kind, what, pos, dist]] of the stations nearest pos, within r."""
        found = sorted((math.dist(o["pos"], pos), o) for o in s.objects if math.dist(o["pos"], pos) <= r)
        return [[o["kind"], o["what"], o["pos"], round(d, 1)] for d, o in found[:n]]

    def mark(s, text, pos, stamp, t=None):
        """the player's note (a bug report) at his place, with the stations nearest him."""
        if any(m.get("stamp") == stamp for m in s.marks):
            return None
        m = dict(text=text, pos=[round(v, 2) for v in pos], stamp=stamp, t=t, near=s.near(pos))
        s.marks.append(m)
        s.version += 1
        return m

    def save(s):
        """stations.json (whole file, replaced): objects not seen in a run of RUN_MIN s or more are gone."""
        now = s.clock()
        if s.started is not None and now - s.started >= RUN_MIN:
            keep = [o for o in s.objects if id(o) in s.seen_run]
            if len(keep) != len(s.objects):
                s.objects[:] = keep
                s.version += 1
        path = path_of(s.map)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"objects": s.objects, "teleports": s.teleports, "marks": s.marks}, f, indent=0)
        os.replace(tmp, path)
        return path


def features(map_name, data=None):
    """The stations as the LiDAR view's map features (tools/lidar.py load_features): kinds it draws, teleports as
    teleporter lines, the player's marks."""
    d = data if data is not None else load(map_name)
    out = []
    for o in d["objects"]:
        k = o["kind"]
        f = dict(kind={"kill_zone": "zone", "safe_zone": "zone", "trait_zone": "zone", "spawn_zone": "zone",
                       "health": "powerup"}.get(k, k), name=o["what"], pos=o["pos"], station=k)
        if k == "teleporter":
            f.update(name=f"teleporter {o['what']}" if o["what"] != "teleporter" else "teleporter",
                     exit=o["what"] == "receiver")
        out.append(f)
    for m in d["marks"]:
        out.append(dict(kind="mark", name=m["text"], pos=m["pos"]))
    return out, [[t[0], t[1]] for t in d["teleports"]]


def describe(map_name):
    """The stations in words (python -I -m brain.stations <map>)."""
    d = load(map_name)
    lines = [f"{map_name}: {len(d['objects'])} stations, {len(d['teleports'])} teleporter pairs, {len(d['marks'])} marks"]
    by = {}
    for o in d["objects"]:
        by.setdefault(o["kind"], []).append(o)
    for k in sorted(by):
        lines.append(f"  {k} ({len(by[k])}): " + ", ".join(f"{o['what']} at {o['pos']}" for o in by[k][:12]) +
                     (" ..." if len(by[k]) > 12 else ""))
    for a, b, n in d["teleports"]:
        lines.append(f"  teleport {a} -> {b} ({n}x)")
    for m in d["marks"]:
        lines.append(f"  mark \"{m['text']}\" at {m['pos']}: " +
                     "; ".join(f"{k} {w} {dist} u" for k, w, _, dist in m["near"]))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print(describe(sys.argv[1]))

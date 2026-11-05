"""Every map's features, painted onto its LiDAR map and given to the bots (the player: "paint the
weapons and it'll mark their spots, along with any objective spawn points / returns; paint
interactables so the bots know they can use them: teleporters, map-placed man cannons, interaction
points like turning on H2A's shield dome"). From the map's own data, no game needed:
  objects.json            weapons, powerups, grenades, ammo, vehicles; objective points (netgame
                          flags: flag spawns and returns, hills, balls, territories, bomb spawns and
                          goals, havens, race points, ...); teleporters given as flags
  source/*.xml            the scenario as the kits export it: every machine, control, crate and
                          scenery placement: man cannons, gravity lifts, teleporters (H2A / H4 name
                          theirs fw_teleporter_*: the exporter missed them), switches, doors, shields
Writes maps/<map>/features.json: {"features": [{kind, name, pos, ...}], "teleporters": [[from, to]]}.
kinds: weapon powerup grenade ammo vehicle objective teleporter launcher lift control door shield.

usage: python -I map_features.py [map ...]      (default: every map)
"""
import glob
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
MAPS = os.path.join(HERE, "..", "maps")
sys.path.insert(0, HERE)

# objective roles by netgame flag / megalo label (every game's own names); None = not a point bots use
ROLES = [(r"ctf.*return|flag return|ctf_flag_return", "flag_return"), (r"^ctf - flag$|ctf_flag|stp_flag|stockpile_flag", "flag"),
         (r"hill|koth", "hill"), (r"oddball|ball_spawn|^ball|rico_ballspawn", "ball"), (r"rico_endzone|rico_hoop", "goal"),
         (r"terr|territor|dominion|dom_base$|^dom$", "territory"), (r"bomb.*return|as_goal|grif_goal|bomb_goal|ob_goal", "bomb_goal"),
         (r"as_arm_zone", "bomb_arm"), (r"bomb|as_bomb|grif_spawn", "bomb"), (r"haven", "haven"), (r"race|checkpoint|rally", "race"),
         (r"hh_drop_point|headhunter", "drop_point"), (r"ext_site|extraction", "extraction"), (r"stp_goal", "stockpile_goal"),
         (r"vip|juggernaut", "mode_point"), (r"inv_objective|inv_obj_flag|inv_res|inv_slayer_res", "invasion")]
SKIP_FLAG = re.compile(r"decal|decor|cinematic|delete|unused|^none$|bounds|warning_lights|screen|fortify|shield|ext_target|"
                       r"inf_flight|race - vehicle|inv_gates|inv_platform|inv_weapon|no_dom|no_core|team_only", re.I)
INTERACT = [(r"teleport", "teleporter"), (r"man_?cannon|launch_tube|outsidecannon", "launcher"),
            (r"grav_?lift|lift|elevator", "lift"), (r"switch|button|control|terminal|_device$", "control"),
            (r"door|gate", "door"), (r"dome_shield|team_shield|shield_door", "shield")]
NOT_INTERACT = re.compile(r"forklift|turret|truck|wires|sandbag|battery|lights|_case$|halogram|decal|cable|chainlink|"
                          r"panel_truck|glasspanel|plug|ceiling|security_gate|survival|offramp|evac|mortar|pod_door", re.I)


def norm(name):
    return (name or "").replace("\\", "/").split("/")[-1].strip()


def item_kind(name):
    n = name.lower()
    if "grenade" in n:
        return "grenade"
    if "ammo" in n:
        return "ammo"
    if re.search(r"powerup|overshield|super_shield|invisib|camo|health|speedboost|damage_boost|ord_equip|armor_ability|"
                 r"bubble_shield|regenerator|power_drain|trip_mine|radar_jammer|deployable_cover|flare|jet_pack|"
                 r"hologram|sprint|evade|drop_shield|thruster|autoturret|promethean_vision|hardlight", n):
        return "powerup"
    return "weapon"


def role_of(t):
    if SKIP_FLAG.search(t):
        return None
    return next((r for pat, r in ROLES if re.search(pat, t, re.I)), None)


def from_objects(o):
    out, tele = [], []
    for e in o.get("equipment", []):
        name = norm(e.get("item") or e.get("tag"))
        if name:                                     # Zenith's shield dome is placed as equipment
            out.append(dict(kind=interact_kind(name) or item_kind(name), name=name, pos=e["pos"], team=e.get("team", 8),
                            respawn=e.get("spawn_time", 0)))
    for v in o.get("vehicles", []):
        name = norm(v.get("vehicle") or v.get("item") or v.get("tag"))
        if name and v.get("pos"):
            out.append(dict(kind="vehicle", name=name, pos=v["pos"], team=v.get("team", 8)))
    ends = {}
    for f in o.get("netgame_flags", []):
        t = f.get("type") or ""
        if t in ("teleport from", "teleport to"):
            ends.setdefault((str(f.get("id")), t), []).append(f["pos"])
            continue
        if t == "lift" or t == "teleporter" or t == "inv_mancannon":
            out.append(dict(kind={"lift": "lift", "teleporter": "teleporter", "inv_mancannon": "launcher"}[t], name=t,
                            pos=f["pos"], source="flag"))
            continue
        role = role_of(t)
        if role:
            out.append(dict(kind="objective", role=role, name=t, pos=f["pos"], team=f.get("team", f.get("id", 8))))
    for (chan, t), ps in ends.items():
        if t == "teleport from":
            for a in ps:
                for b in ends.get((chan, "teleport to"), []):
                    tele.append([a, b])
                out.append(dict(kind="teleporter", name="teleport from", pos=a, channel=chan))
    for (chan, t), ps in ends.items():
        if t == "teleport to":
            out += [dict(kind="teleporter", name="teleport to", pos=b, channel=chan, exit=True) for b in ps]
    return out, tele


def from_xml(path):
    """[(group, palette name, position, element)] of machines, controls, crates and scenery."""
    import reach_export as R
    import scenario_extract as X
    out = []
    try:
        root = R.parse(path)
    except ET.ParseError:
        return out
    new = '" value="' in open(path, errors="replace").read(4000)
    for group in ("machines", "controls", "crates", "scenery"):
        if new:
            try:
                placed = R.items(root, group)
            except (KeyError, ValueError):
                continue
            for name, e in placed:
                p = R.fld(e, "position")
                if name != "NONE" and p:
                    out.append((group, norm(name), R.vec(p), e))
        else:                                       # CE / Halo 2 kit XML
            pal_name = {"machines": "machine palette", "controls": "control palette", "crates": "crate palette",
                        "scenery": "scenery palette"}[group]
            pal = X.palette(root, pal_name)
            for e in X.block(root, group):
                bi = next((x for x in e if x.tag == "block_index"), None)
                i = int(bi.attrib.get("index", -1)) if bi is not None else -1
                p = X.field(e, "position")
                if 0 <= i < len(pal) and p:
                    out.append((group, norm(pal[i]), X.point(p), e))
    return out


def interact_kind(name):
    if NOT_INTERACT.search(name):
        return None
    return next((k for pat, k in INTERACT if re.search(pat, name, re.I)), None)


def build(m):
    d = os.path.join(MAPS, m)
    o = json.load(open(os.path.join(d, "objects.json")))
    feats, tele = from_objects(o)
    xmls = [x for x in glob.glob(os.path.join(d, "source", "*.xml"))
            if "scenario" in os.path.basename(x) and not (os.path.exists(x[:-4] + ".slim.xml") and not x.endswith(".slim.xml"))
            and not os.path.basename(x).endswith(".xml.xml")]
    import reach_export as R
    senders, receivers = {}, {}
    for x in xmls:
        for group, name, pos, e in from_xml(x):
            k = interact_kind(name)
            if not k:
                continue
            f = dict(kind=k, name=name, pos=pos, group=group)
            if k == "teleporter":
                chan = R.fld(e, "teleporter channel")
                if chan is None:                     # CE / Halo 2 XML has no channels: the netgame flags pair them
                    continue
                f["channel"] = chan
                two = "2way" in name or "2_way" in name or "two_way" in name
                if two or "sender" in name:
                    senders.setdefault(chan, []).append(pos)
                if two or "rec" in name:
                    receivers.setdefault(chan, []).append(pos)
            feats.append(f)
    if not tele:                                     # placed teleporters (no flags): each sender to its channel's receivers
        for chan, ps in senders.items():
            for a in ps:
                for b in receivers.get(chan, []):
                    if math.dist(a, b) > 1.0:
                        tele.append([a, b])
    out, seen = [], []
    for f in feats:                                  # one marker per thing (a flag and its object coincide)
        key = (f["kind"], f.get("role"), f["name"])
        if any(k == key and math.dist(p, f["pos"]) < 0.3 for k, p in seen):
            continue
        seen.append((key, f["pos"]))
        out.append(f)
    uniq = []
    for a, b in tele:
        if not any(math.dist(a, x) < 0.3 and math.dist(b, y) < 0.3 for x, y in uniq):
            uniq.append([a, b])
    data = dict(features=out, teleporters=uniq)
    tmp = os.path.join(d, "features.json.tmp")
    json.dump(data, open(tmp, "w"), indent=0)
    os.replace(tmp, os.path.join(d, "features.json"))
    return data


def main():
    names = sys.argv[1:] or sorted(m for m in os.listdir(MAPS) if os.path.exists(os.path.join(MAPS, m, "objects.json")))
    for m in names:
        data = build(m)
        kinds = {}
        for f in data["features"]:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
        print(f"{m:28s} " + " ".join(f"{k}:{v}" for k, v in sorted(kinds.items())) + f" | teleport pairs {len(data['teleporters'])}", flush=True)


if __name__ == "__main__":
    main()

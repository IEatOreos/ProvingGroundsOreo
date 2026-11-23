"""Per-map knowledge, built from the map's real data:
  maps/<map>/objects.json   flags, teleporters, weapon/vehicle spawns, player spawns
                            (tools/scenario_extract.py from the CE kit's scenario tag)
  maps/<map>/callouts.json  named callout zones (docs/research/06 for where names come from)
  maps/<map>/heightmap.npz  level surface heights (tools/heightmap.py from the level mesh)
"""
import math
import os

from .core import Vec
from .callouts import ZoneMap, read_json

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
# the games whose nav has no drops into seams no body fits (Terrain slit_rule): Reach's 0.25 u cells (Countdown)
SLIT_GAMES = ("reach_",)
# (custom, Nov 8) floor people walked crouched makes bots crouch (Bot.crouch_spots) only under a low ceiling (terrain)
CROUCH_LOW_ONLY = True


def _v(p):
    return Vec(p[0], p[1], p[2] if len(p) > 2 else 0.0)


SPOT_KINDS = {"koth_hill": "hills", "oddball_ball": "balls", "terr_object": "territories", "hh_drop_point": "drop_points",
              "inf_haven": "havens", "as_bomb": "bombs", "as_goal": "bomb_goals", "stp_flag": "stockpile_flags",
              "stp_goal": "stockpile_goals"}
H3_TYPES = {"oddball_ball_spawn_point": "oddball_ball", "koth_hill_static": "koth_hill", "territory_static": "terr_object"}


# (custom, Nov 7) the gametype labels Halo 4 and H2A give a placed teleporter (the netgame flag on its spot, objects.json):
# the modes it stands in. The owner's Gore Valley Slayer report, "Bots get stuck here": its two-way pads are Dominion's
# ("dominion", fw_teleporter_2_way), not there in Slayer or CTF, and three bots stood on the one by red's spawn 60 s
# (Terrain.nav: on a teleporter that is the way, step onto its centre). Canyon's Dominion pair likewise; Warlock's and
# Ascension's (H2A) are removed in CTF. Modes as brain/modes.py names them (Dominion: territories)
TELE_ONLY = {"dominion": {"territories"}}              # only in these modes
TELE_NOT = {"no_dom": {"territories"}, "ctf_delete": {"ctf"}}   # in every mode but these


def teleporter_tag(objs, p, near=0.15):
    """The gametype label (TELE_ONLY / TELE_NOT) of the netgame flag on teleporter end p (the nearest within near: Canyon's
    Dominion two-way pads stand 0.1 u from its other modes' one-way receivers), or None."""
    best, label = near, None
    for f in (objs or {}).get("netgame_flags", ()):
        t = f.get("type")
        q = f.get("pos")
        if (t in TELE_ONLY or t in TELE_NOT) and q and abs(q[2] - p.z) < 0.5:
            d = math.hypot(q[0] - p.x, q[1] - p.y)
            if d < best:
                best, label = d, t
    return label


def tele_in_mode(tags, mode):
    """A teleporter whose ends carry these labels stands in this mode (None: Slayer or a mode not read)."""
    for t in tags:
        if t in TELE_ONLY and mode not in TELE_ONLY[t]:
            return False
        if t in TELE_NOT and mode in TELE_NOT[t]:
            return False
    return True


def set_mode(m, mode):
    """Keep only the teleporters that stand in this mode (m["teleporters"], what the nav links and the bots know), the
    whole set kept in m["teleporters_all"]; a terrain built before is dropped when that changes. Returns the pairs left
    out."""
    allp = m.setdefault("teleporters_all", list(m.get("teleporters", ())))
    keep = [(a, b) for a, b in allp
            if tele_in_mode({teleporter_tag(m.get("objects"), a), teleporter_tag(m.get("objects"), b)} - {None}, mode)]
    if len(keep) != len(m.get("teleporters", ())):
        _TERRAIN.pop(m["name"], None)
    m["teleporters"], m["mode"] = keep, mode
    return [p for p in allp if p not in keep]


def load_map(name):
    """A map by name; a map variant ("<base>/variants/<id>", brain/variants.py) has its base map's level and scenario
    with its own navmesh data (its folder: lidar.json, learned spots, paint), its nav window, and its own callouts and
    power positions once made (tools/variant_strategy.py: the base's are a Forge canvas's, not the layout's)."""
    from . import variants
    from .variants import base_of, info
    d = os.path.join(ROOT, base_of(name))
    vd = os.path.join(variants.ROOT, name) if name != base_of(name) else d
    objs = read_json(os.path.join(d, "objects.json"))
    # (a built-in map's variant, Invasion: Spire's layout, a CTF variant: the base map's callouts and power positions,
    # its teams' own holds; the strategy made per layout gave both teams one set of holds: data_names)
    builtin = vd != d and bool(variants.base_area(objs))
    own = lambda fn: (os.path.join(vd, fn) if os.path.exists(os.path.join(vd, fn)) and not builtin
                      else os.path.join(d, fn))
    mv = os.path.join(vd, "mvar_objects.json") if vd != d else None
    if mv and os.path.exists(mv):       # its own .mvar file read (brain/mvar.py): its labelled objects, spawns, weapons
        mo = read_json(mv)              # and vehicles replace the scenario's; the scenario's CTF stands stay where the
        ctf = [f for f in objs["netgame_flags"] if f["type"] in ("ctf - flag", "CTF flag return")]   # file has none
        has = {f["id"] for f in mo["netgame_flags"] if f["type"] == "ctf - flag"} >= {0, 1}
        objs = dict(objs, netgame_flags=mo["netgame_flags"] + ([] if has else ctf), mvar=mo.get("source"),
                    **{k: mo[k] for k in ("spawns", "equipment", "vehicles", "powerups") if mo.get(k)})
    for f in objs["netgame_flags"]:     # Halo 3's names for Reach's (Construct Team Oddball: no ball spots,
        f["type"] = H3_TYPES.get(f["type"], f["type"])    # so the ball was never found and the match ran as Slayer)
    flags = {f["id"]: _v(f["pos"]) for f in objs["netgame_flags"] if f["type"] == "ctf - flag"}
    spots = {t: [_v(f["pos"]) for f in objs["netgame_flags"] if f["type"] == "ctf - flag" and f["id"] == t] for t in (0, 1)}
    if len(spots[0]) > 1 or len(spots[1]) > 1:      # several setups (Halo 3): the farthest pair
        flags[0], flags[1] = max(((a, b) for a in spots[0] for b in spots[1]), key=lambda ab: (ab[0] - ab[1]).flat())
    # where each team captures (Halo 3's "CTF flag return": on most maps at its stand, on Sandtrap's static setup 0.6 u
    # off it; its Elephants' ride with them: tools/live_bots.py): the team's own return nearest its stand, at any
    # distance (Avalanche's sit 7.8 u off the stands on the floor below: live carriers stood 9 s on their own stand,
    # own flag home, and never scored) if it is nearer its stand than the other's (a team tag the other way round, as
    # on the Lockout remake's, is not trusted), else any return within 3 u of the stand
    rets = [(f.get("team", f.get("id")), _v(f["pos"])) for f in objs["netgame_flags"] if f["type"] == "CTF flag return"]
    returns = {}
    for t in flags:
        far = flags.get(1 - t)
        mine = [r for k, r in rets if k == t and (far is None or (r - flags[t]).flat() < (r - far).flat())]
        mine = mine or [r for k, r in rets if (r - flags[t]).flat() < 3.0]
        if mine:
            returns[t] = min(mine, key=lambda r: (r - flags[t]).flat())
    tele_from = {f["id"]: _v(f["pos"]) for f in objs["netgame_flags"] if f["type"] == "teleport from"}
    tele_to = {f["id"]: _v(f["pos"]) for f in objs["netgame_flags"] if f["type"] == "teleport to"}
    spawns = {"ctf": {0: [], 1: []}, "slayer": {0: [], 1: []}}
    for sp in objs["spawns"]:
        games = sp["games"] or ["all games"]   # no game types listed = every game (Halo 2 Relic, Warlock,
                                               # Sanctuary: all 121 spawns had an empty list, so no spawns at all)
        team = sp["team"] % 2           # extra spawn groups (Boarding Action has teams 2, 3) -> red/blue
        if "ctf" in games:
            spawns["ctf"][team].append(_v(sp["pos"]))
        if any(g.startswith("all") and g != "all except slayer" for g in games) or "slayer" in games:
            spawns["slayer"][team].append(_v(sp["pos"]))
    cfg = read_json(own("callouts.json"))
    teleporters = [(tele_from[k], tele_to[k]) for k in tele_from if k in tele_to]
    features = read_json(os.path.join(d, "features.json")) if os.path.exists(os.path.join(d, "features.json")) else {}
    for a, b in features.get("teleporters", []):   # placed teleporters the flags lack (H2A, H4: tools/map_features.py)
        a, b = _v(a), _v(b)
        if not any((a - x).flat() < 0.5 and (b - y).flat() < 0.5 for x, y in teleporters):
            teleporters.append((a, b))
    m = {
        "name": name,
        "flags": flags,
        "returns": returns,
        "teleporters": teleporters,
        "features": features.get("features", []),   # weapons, objective points, interactables (painted)
        "spawns": spawns,
        "zones": ZoneMap.load(own("callouts.json")),
        "bases": [(flags[t], cfg["base_radius"], cfg["roof_z"]) for t in (0, 1)],
        "heightmap": os.path.join(d, "heightmap.npz"),
        "objects": objs,
    }
    pts = {k: _v(v) for k, v in cfg["points"].items()}
    m["points"] = pts
    m["holds"] = {0: [_v(p) for p in cfg["holds"]["red"]], 1: [_v(p) for p in cfg["holds"]["blue"]]}
    m["lanes"] = [_v(p) for p in cfg["lanes"]]
    patrols = os.path.join(d, "infantry_patrols.json")
    if os.path.exists(patrols):
        team_ids = {"red": 0, "blue": 1}
        m["infantry_patrols"] = tuple(
            (_v(p["pos"]), team_ids[p["team"]]) if isinstance(p, dict) else (_v(p), None)
            for p in read_json(patrols).values()
        )
    m["sneak"] = {0: [[_v(p) for p in r] for r in cfg.get("sneak", {}).get("red", [])],
                  1: [[_v(p) for p in r] for r in cfg.get("sneak", {}).get("blue", [])]}
    # objective spots by game type (Halo: Reach netgame flags, tools/reach_export.py): KotH hills, ball spawns,
    # territories, Headhunter drop points, Infection havens, Assault bombs / goals, Stockpile flags / goals
    m["spots"] = {}
    for f in objs["netgame_flags"]:
        if f["type"] in SPOT_KINDS:
            m["spots"].setdefault(SPOT_KINDS[f["type"]], []).append(_v(f["pos"]))
    h4 = base_of(name).startswith("h4_")
    m["items"] = power_items(objs, base_of(name).startswith("h3_"), h4)
    m["ordnance_power"] = ordnance_power(objs) if h4 else []
    pos = own("positions.json")                    # power positions (tools/power_positions.py)
    rows = read_json(pos) if os.path.exists(pos) else []
    m["positions"] = [_v(p["pos"]) for p in rows]
    # and why each one is: height over its surroundings, floor it sees, cover to duck behind (the commander)
    m["position_info"] = [dict(pos=_v(p["pos"]), height=p.get("height", 0.0), sees=p.get("sees", 0),
                               duck=bool(p.get("duck")), score=p.get("score", 0.0)) for p in rows]
    m["base"] = base_of(name)
    v = info(name)
    if v is not None:
        m["variant"], m["window"] = v, tuple(v["window"]) if v.get("window") else None
    # (custom, Nov 18) the base's lifts and cannons this layout lacks: left out, their rides too (_build: off_gone_pads)
    m["features"], m["lifts_gone"] = layout_lifts(m["features"], m.get("variant"),
                                                  {it["name"] for it in objs.get("placed", ())})
    m["features"] = forge_pads(m["features"], m.get("variant"))   # (custom, Nov 18) its Forge lifts and cannons
    m["features"] = owner_ride_pads(m["features"], data_names(m))   # (custom) the owner's lift / man cannon pads
    return m


# Power items bots with map knowledge go for. Respawn: the scenario's own field where set
# (rockets 90 s, snipers 120 s); 0 means the game type default, assumed 60 s for powerups and
# 45 s for weapons (UNVERIFIED for CE, check in game).
POWER = {"rocket launcher": ("rockets", "weapon", 1.0), "sniper rifle": ("sniper", "weapon", 0.8),
         "powerup super shield": ("overshield", "powerup", 0.9), "shield-invisibility": ("camo", "powerup", 0.7),
         "powerup invisibility": ("camo", "powerup", 0.7),
         "plasma_cannon": ("fuelrod", "weapon", 0.6),
         # Halo 2 (item collection names)
         "rocket_launcher": ("rockets", "weapon", 1.0), "sniper_rifle": ("sniper", "weapon", 0.8),
         "energy_sword": ("sword", "weapon", 0.9), "beam_rifle": ("beam_rifle", "weapon", 0.6),
         "powerup_super_shield": ("overshield", "powerup", 0.9), "powerup_invisibility": ("camo", "powerup", 0.7),
         # Halo 3 (placement palette names)
         "spartan_laser": ("spartan_laser", "weapon", 0.9), "gravity_hammer": ("gravity_hammer", "weapon", 0.8),
         "missile_pod": ("missile_pod", "weapon", 0.5), "energy_blade": ("sword", "weapon", 0.9),
         # Halo: Reach (tools/reach_export.py writes the brain's weapon names)
         "rockets": ("rockets", "weapon", 1.0), "sniper": ("sniper", "weapon", 0.8), "sword": ("sword", "weapon", 0.9),
         "fuelrod": ("fuelrod", "weapon", 0.6), "plasma_launcher": ("plasma_launcher", "weapon", 0.6),
         # Halo 3 equipment pickups (one slot; guide 08 pickup priority: bubble, power drain,
         # regenerator, trip mine, grav lift, cover, flare and jammer), below the power weapons and
         # powerups (valued above the sniper, top bots ran the map for them: sim A/B)
         "bubbleshield_equipment": ("bubble_shield", "equipment", 0.55),
         "powerdrain_equipment": ("power_drain", "equipment", 0.5),
         "regenerator_equipment": ("regenerator", "equipment", 0.45),
         "tripmine_equipment": ("trip_mine", "equipment", 0.4), "gravlift_equipment": ("grav_lift", "equipment", 0.3),
         "superflare_equipment": ("flare", "equipment", 0.25), "jammer_equipment": ("radar_jammer", "equipment", 0.25),
         # H2A and Halo 4 powerups
         "h2a_overshield": ("overshield", "powerup", 0.9), "h2a_activecamo": ("camo", "powerup", 0.7),
         "h2a_speedboost": ("speed_boost", "powerup", 0.6), "ord_equip_overshield": ("overshield", "powerup", 0.9),
         "speedboost": ("speed_boost", "powerup", 0.6),
         # (custom, Nov 23) Halo: Reach's Forge powerups by their tag names (a .mvar's, the live reader's): the owner,
         # Beaver Creek Anniversary's powerup_red, "These are overshields"; "Blue camo, yellow custom" (the custom
         # powerup's traits are the game type's: valued as Halo 4's speed boost)
         "powerup_red": ("overshield", "powerup", 0.9), "powerup_blue": ("camo", "powerup", 0.7),
         "powerup_yellow": ("custom_powerup", "powerup", 0.6)}


# Halo 4's ordnance guns (custom, Nov 8), beside POWER's, by the exports' item names (the brain's): power 0.8 and up
# gets the team's runs (director.power_runs). Its needler and grenade drops are no trip: a bot takes them by the way
# (Bot.upgrade_point). (custom, Nov 8: the SAW is a power weapon, the owner's call: the Railgun's 0.8)
H4_ORDNANCE = {"incineration_cannon": ("incineration_cannon", "weapon", 0.9),
               "binary_rifle": ("binary_rifle", "weapon", 0.85), "railgun": ("railgun", "weapon", 0.8),
               "lmg": ("lmg", "weapon", 0.8),
               "scattershot": ("scattershot", "weapon", 0.6), "concussion_rifle": ("concussion_rifle", "weapon", 0.5),
               "sticky_detonator": ("sticky_detonator", "weapon", 0.5), "shotgun": ("shotgun", "weapon", 0.5)}
# A Halo 4 initial drop, once seen gone, is not timed back: Infinity Slayer drops it once at the start, and later
# ordnance falls on the random points. A gun seen on its spot again brings it back (tools/live_bots.py item_check)
ORDNANCE_GONE = 1e6


def power_items(objs, h3=False, h4=False):
    """h3: MCC Halo 3, where a weapon's timer starts 2 s after it is disturbed (map brain MAP-12; guide 21 Part 2 from
    the Steam Halo 3 spawn guide): its respawn is 2 s longer from the pickup. h4: Halo 4's ordnance (custom, Nov 8): the
    export marks each placement "initial" (lying there at the start) or "random" (a point a random drop may land on);
    the initial ones are items (ORDNANCE_GONE once seen taken), the random ones none (ordnance_power)."""
    table = {**POWER, **H4_ORDNANCE} if h4 else POWER
    out = []
    for e in list(objs["equipment"]) + list(objs.get("powerups") or ()):   # (custom, Nov 23: a .mvar's powerups)
        key = e["item"].split("\\")[-1]
        if key in table:
            name, kind, value = table[key]
            ordnance = e.get("ordnance") if h4 else None
            if ordnance == "random":
                continue
            default = 60 if kind == "powerup" else 45
            it = {"name": name, "kind": kind, "value": value, "pos": _v(e["pos"]),
                  "respawn": (e["spawn_time"] or default) + (2 if h3 and kind == "weapon" else 0)}
            if ordnance:
                it["ordnance"], it["respawn"] = ordnance, ORDNANCE_GONE
            out.append(it)
    return out


def ordnance_power(objs):
    """Halo 4: the power guns (value 0.8 and up) a random drop point may bring, by the brain's names."""
    table = {**POWER, **H4_ORDNANCE}
    return sorted({table[k][0] for k in (e["item"].split("\\")[-1] for e in objs["equipment"]
                                         if e.get("ordnance") == "random")
                   if k in table and table[k][1] == "weapon" and table[k][2] >= 0.8})


_MAPS = {}
_TERRAIN = {}


PVP = False     # tools/live_bots.py sets it: a fighting match, not a LiDAR or simulator run


def path_rises(zs, h=0.15):
    """How many times a path climbs h or more after a low point: a jump once, a drop none, a lift ride once; a person's
    hops in a row recorded as one jump (the tracker's landing needs 0.1 s on the ground and a bunny hop touches it for
    less) two and more. Spire: link 140, 3.5 s of hops read as a 7.5 u jump, held the core carrier at the plateau's
    lip; the player's match that day added 41 links, 2-9 s in the air and up to 17 u long, many such."""
    if not zs:
        return 0
    n, up, ext = 0, False, zs[0]
    for z in zs[1:]:
        if up:
            if z > ext:
                ext = z
            elif ext - z >= h:
                up, ext = False, z
        elif z < ext:
            ext = z
        elif z - ext >= h:
            up, ext, n = True, z, n + 1
    return n


LAUNCH_SNAP = 5.0    # u: a ride up starting this near a man cannon or gravity lift starts on it
LAUNCH_RISE = 10.0   # u: a link rising this much is a launch (no jump gets a person 10 u up)
PAD_TRIGGER = 1.2    # u: a ride people started this near a launch's marker starts at its trigger
# a climb of LIFT_RISE+ from within LIFT_COLUMN of a gravity lift's base (Bot.lift_near's radius) is the lift's ride, one
# way, however low: Blood Cavern's back lift rises 2.8 u, read as a jump back down, and the nav sent bots into its top,
# where it pushes up (flagged Nov 6 16:50: bots kept trying to enter its exit end); Lockout's and Ivory Tower's low
# lifts the same
LIFT_RISE, LIFT_COLUMN = 2.0, 2.0


def anchor_launches(links, features):
    """People's rides up (a link rising LAUNCH_RISE+) recorded from near a man cannon or gravity lift (features.json
    "launcher" / "lift") start at its trigger, marked a ride: LiDAR set the take-off where the person left the ground, a
    few units off when he jumped onto the pad (live Spire: one 4.1 u off the middle cannon, where three bots circled
    pressing jump; "Do these stupid fucks think the man cannon is there?"). The trigger is the ride people started
    nearest the marker, within PAD_TRIGGER of it: the marker itself sits up to 1.2 u into the cannon's body ("Right here
    where im standing, if I go forward it will shoot me up", 0.4 u from such a ride's start and 1.2 u from the marker; a
    bot dithered 2 u off the Elites' cannon). With none that near, the marker. Copies; the rest as they are."""
    pads = [f["pos"] for f in features if f.get("kind") in ("launcher", "lift")]
    if not pads:
        return list(links)
    flat = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    rides = [k for k in links if k.get("take_off") and k.get("land") and k["land"][2] - k["take_off"][2] >= LAUNCH_RISE]
    trigger = {}
    for i, p in enumerate(pads):
        starts = [k["take_off"] for k in rides if flat(k["take_off"], p) < PAD_TRIGGER and abs(k["take_off"][2] - p[2]) < 3.0]
        trigger[i] = list(min(starts, key=lambda q: flat(q, p))[:3]) if starts else list(p[:3])
    out, ride_ids = [], {id(k) for k in rides}
    lifts = [f["pos"] for f in features if f.get("kind") == "lift"]
    for k in links:
        to = k.get("take_off")
        if id(k) in ride_ids:
            i = min(range(len(pads)), key=lambda j: flat(pads[j], to))
            if flat(pads[i], to) < LAUNCH_SNAP and abs(pads[i][2] - to[2]) < 3.0:
                k = dict(k, take_off=trigger[i] + list(to[3:]), ride=1)
                k.pop("runup", None)
        elif (to and k.get("land") and not k.get("ride") and k["land"][2] - to[2] >= LIFT_RISE
              and any(flat(p, to) < LIFT_COLUMN and abs(p[2] - to[2]) < 3.0 for p in lifts)):
            k = dict(k, ride=1)             # a low lift's ride: one way (jump_ways), from where it was taken
        out.append(k)
    return out


OWNER_RIDES = "owner_rides.json"   # (custom) gravity lifts and man cannons the owner drew in the LiDAR view (tools/spots.py)
OWNER_PAD_SAME = 1.5               # u: a lift or launcher marker this near an owner ride's pad is that pad's (no second one)
# u/s along the flat in a man cannon's throw: the owner's three rides of the one he drew on Halo 4 Adrift went 17.8 u in
# 2.14-2.42 s (trace 20261109-214318). (Nov 13, "on adrift halo 4 they've never used them": scored as a 17.8 u jump,
# 27.6, the ride cost more than the 23.9 walk round, so the nav never took it; Terrain's launch cost, by its airtime)
OWNER_CANNON_SPEED = 7.5


def owner_rides(name):
    """The rides the owner drew for map folder `name` (maps/<name>/owner_rides.json): [{name, kind "lift" | "cannon",
    take_off [x, y, z] (where you step in), land [x, y, z] (where it puts you down)}], the malformed ones left out."""
    path = os.path.join(ROOT, name, OWNER_RIDES)
    if not os.path.exists(path):
        return []
    ok = lambda p: isinstance(p, list) and len(p) == 3 and all(isinstance(v, (int, float)) for v in p)
    return [r for r in (read_json(path) or {}).get("rides", [])
            if isinstance(r, dict) and r.get("kind") in ("lift", "cannon") and ok(r.get("take_off")) and ok(r.get("land"))]


def owner_ride_links(names):
    """The owner's rides as people's ride links (one way; bots ride them as the rides people recorded: Bot.lift_base, the
    nav's launch cost), not moved to a marker's trigger (anchor_launches): his pad is where he put it. A man cannon's is
    marked launch, with its airtime at OWNER_CANNON_SPEED (the nav's launch cost however flat; Bot.ride_cannon)."""
    def link(r):
        k = dict(kind="jump", ride=1, painted=1, human=1, found_by="owner", name=r.get("name", ""),
                 take_off=list(r["take_off"]), land=list(r["land"]))
        if r["kind"] == "cannon":
            flat = math.hypot(r["land"][0] - r["take_off"][0], r["land"][1] - r["take_off"][1])
            k.update(launch=1, air_s=round(max(1.0, flat / OWNER_CANNON_SPEED), 2))
        return k
    return [link(r) for nm in names for r in owner_rides(nm)]


def owner_ride_pads(features, names):
    """features plus a "lift" (a gravity lift) or "launcher" (a man cannon) marker at each owner ride's pad no marker of
    the map is near: what makes a bot step into a lift and wait (Bot.lift_near) and keeps drops out of its column."""
    out = list(features)
    for r in (r for nm in names for r in owner_rides(nm)):
        p = r["take_off"]
        if not any(f.get("kind") in ("lift", "launcher") and math.hypot(f["pos"][0] - p[0], f["pos"][1] - p[1]) < OWNER_PAD_SAME
                   and abs(f["pos"][2] - p[2]) < 3.0 for f in out):
            out.append(dict(kind="lift" if r["kind"] == "lift" else "launcher", name=r.get("name") or "owner ride",
                            pos=list(p), owner=True))
    return out


# (custom, Nov 18) a map variant's lifts: the base scenario's gravity lifts and man cannons (features.json group "crates")
# its layout has no piece of, within LAYOUT_PAD_SAME, are not there. The owner's bug report, Damnation Anniversary
# (reach_cex_damnation v08b84b0d), "Bots stuck on damnation": its .mvar has the tall lift, not the short one, and three
# bots stood in the short one's spot 105-157 s each, waiting for a push (its ride from the base map's simulator rides)
LAYOUT_PAD_SAME = 1.5    # u, flat and in height: a lift or cannon piece this near a base lift's pad is that lift
LAYOUT_PAD_R = 2.0       # u: a ride link from this near a gone pad's base (LIFT_COLUMN) is its ride
_LIFT_PIECE = ("lift", "cannon")


def layout_lifts(features, variant, placed=()):
    """(features kept, pads gone [(name, pos)]): a variant's (variant.json "pieces") base lifts and launchers of the
    scenario's crates with no lift or cannon piece on their pad (any name: Battle Canyon's blue lift is a
    gravity_lift_blue on the base's gravity_lift). Only when its pieces carry the base's placed objects (placed: their
    names, objects.json): a layout read without them says nothing of its lifts. Not a variant: as they are."""
    pieces = (variant or {}).get("pieces") or []
    if not pieces or not any(p[0] in placed for p in pieces):
        return list(features), []
    pads = [p for p in pieces if any(w in p[0].lower() for w in _LIFT_PIECE) and "door" not in p[0].lower()]
    keep, gone = [], []
    for f in features:
        q = f.get("pos")
        if (f.get("kind") in ("lift", "launcher") and f.get("group") == "crates" and q
                and not any(math.hypot(p[1] - q[0], p[2] - q[1]) < LAYOUT_PAD_SAME and abs(p[3] - q[2]) < LAYOUT_PAD_SAME
                            for p in pads)):
            gone.append((f.get("name", ""), list(q[:3])))
            continue
        keep.append(f)
    return keep, gone


# (custom, Nov 18) gravity lifts and man cannons placed in Forge are markers too (features.json has the scenario's alone).
# The owner, "What about the cage the forge map?": The Cage (Forge World vd7eaef53) has one ff_man_cannon_forge, and
# its recorded throw (15.5 u in 3.2 s) was a 15 u jump to the nav (cost 24) run as a jump, never the cheap way
FORGE_LIFT = (("man_cannon", "launcher"), ("mancannon", "launcher"), ("grav_lift", "lift"), ("gravlift", "lift"),
              ("gravity_lift", "lift"))
CANNON_PAD_R = 2.0     # u: a link from this near a Forge cannon's piece (and 3 u of its height) ...
CANNON_THROW = 7.0     # u: ... going this far or more on the flat is its throw (no jump goes 7 u): ride, launch


def forge_pads(features, variant):
    """features plus a "lift" or "launcher" marker (group "forge") at each lift or cannon piece of a variant's layout
    (variant.json "pieces", by name: FORGE_LIFT) no lift or launcher marker is within LAYOUT_PAD_SAME of."""
    out = list(features)
    for p in (variant or {}).get("pieces") or []:
        n = p[0].lower()
        kind = next((k for w, k in FORGE_LIFT if w in n), None)
        if kind is None or "door" in n:
            continue
        if any(f.get("kind") in ("lift", "launcher") and math.hypot(f["pos"][0] - p[1], f["pos"][1] - p[2]) < LAYOUT_PAD_SAME
               and abs(f["pos"][2] - p[3]) < LAYOUT_PAD_SAME for f in out):
            continue
        out.append(dict(kind=kind, name=p[0], pos=[float(p[1]), float(p[2]), float(p[3])], group="forge"))
    return out


def forge_throws(links, features):
    """links with each throw from a Forge man cannon (forge_pads) marked ride and launch: from within CANNON_PAD_R of its
    piece, CANNON_THROW+ u on the flat. The nav prices it by its airtime (Terrain.add_human_links) and the bot steps on
    and is thrown (Bot.cannon_of, ride_cannon), as the owner's drawn cannons. Copies; the rest as they are."""
    pads = [f["pos"] for f in features if f.get("kind") == "launcher" and f.get("group") == "forge"]
    if not pads:
        return list(links)
    out = []
    for k in links:
        to, la = k.get("take_off"), k.get("land")
        if (to and la and not k.get("launch") and math.hypot(la[0] - to[0], la[1] - to[1]) >= CANNON_THROW
                and any(math.hypot(to[0] - p[0], to[1] - p[1]) < CANNON_PAD_R and abs(to[2] - p[2]) < 3.0 for p in pads)):
            k = dict(k, ride=1, launch=1, air_s=max(1.0, float(k.get("air_s") or 0.0)))
        out.append(k)
    return out


def off_gone_pads(links, gone):
    """links less the rides from a pad its layout lacks (layout_lifts): flagged ride, or rising LIFT_RISE+, from within
    LAYOUT_PAD_R of its base and 3 u of its height (no jump climbs 2 u there: something pushed)."""
    if not gone:
        return list(links)

    def ride_off(k):
        to, la = k.get("take_off"), k.get("land")
        if not (to and la) or not (k.get("ride") or k.get("launch") or la[2] - to[2] >= LIFT_RISE):
            return False
        return any(math.hypot(to[0] - p[0], to[1] - p[1]) < LAYOUT_PAD_R and abs(to[2] - p[2]) < 3.0 for _, p in gone)
    return [k for k in links if not ride_off(k)]


# (custom, Nov 18) a gravity lift nobody rode is in the nav too: its ride solved from its tags (tools/lidar_rides.py,
# maps/<map>/phantoms.json), as LiDAR runs had it alone. The owner: "Ive never seen them ever use one": in matches a
# lift was known only from a recorded ride; Launch Station's main lift had none, Prisoner Anniversary's had one lift's
# of its five. A solved ride rising MAP_RIDE_RISE+ from a lift no recorded ride starts within LAYOUT_PAD_R of
MAP_RIDE_RISE = 1.5   # u (Prisoner's low lifts: 1.7 u up; lidar_rides keeps none under 1 u)
MAP_RIDE_GAMES = ("reach_", "h3_", "odst_", "h4_", "h2a_")   # (lidar_rides.KITS: the games phantoms.json is read for)


def map_lift_rides(name, T, links):
    """The map's gravity lifts' solved rides (lidar_rides.ride_links: a variant's, those its layout has) from lifts no
    ride in links starts at, or [] (a game without them, or no data)."""
    if not name.startswith(MAP_RIDE_GAMES):
        return []
    import sys
    tools = os.path.join(os.path.dirname(ROOT), "tools")
    if tools not in sys.path:
        sys.path.append(tools)
    try:
        import jumpphys
        import lidar_rides
        rides = lidar_rides.ride_links(name, T, jumpphys.Phys(jumpphys.game_of(name), getattr(T, "jump_apex", None)))
    except Exception:                                # (no phantoms, no physics: the recorded rides alone)
        return []
    lifts = {o["name"] for o in lidar_rides.layout(name).get("objects", []) if o.get("kind") == "lift"}
    rode = [k["take_off"] for k in links if k.get("ride") and k.get("take_off")]
    near = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]) < LAYOUT_PAD_R and abs(a[2] - b[2]) < 1.5
    oob = getattr(T, "oob", None)                    # (none into a kill zone: tools/lidar.py nav_learn, Zealot's walkway)
    killed = lambda p: oob is not None and T.inside(p[0], p[1]) and bool(oob[T._node(Vec(*p[:3]))])
    return [k for k in rides if k.get("name") in lifts and k["land"][2] - k["take_off"][2] >= MAP_RIDE_RISE
            and not any(near(k["take_off"], q) for q in rode) and not killed(k["land"])]


VEHICLE_BLOCKS = "vehicle_blocks.json"   # (custom, Nov 13) areas the owner keeps every ground vehicle out of


def owner_vblocks(name):
    """The owner's vehicle blockers for map folder `name` (maps/<name>/vehicle_blocks.json, the LiDAR view's Edit
    spots): [(centre Vec, radius)], the malformed ones left out (Terrain.vblock_nodes)."""
    path = os.path.join(ROOT, name, VEHICLE_BLOCKS)
    if not os.path.exists(path):
        return []
    out = []
    for b in (read_json(path) or {}).get("blocks", []):
        p, r = (b.get("pos"), b.get("r")) if isinstance(b, dict) else (None, None)
        if (isinstance(p, list) and len(p) == 3 and all(isinstance(v, (int, float)) for v in p)
                and isinstance(r, (int, float)) and 0.0 < r <= 30.0):
            out.append((_v(p), float(r)))
    return out


# (custom, Nov 23, the owner: Powerhouse One Bomb, "the jump up to get the bomb was mapped, but they cant get it")
# split_hops: a person's two hops recorded as one jump. LiDAR ends a jump on 0.1 s on the ground; the owner's climb
# onto Powerhouse's roof (floor 39.4 -> a rock top at 39.96 -> the roof at 40.65) touched the rock top for less and was
# filed as one 1.6-2.4 s "jump" rising 1.2 u, its dip on the rock top 0.10 u, under path_rises' 0.15. Bots called it as
# one jump 62 times (20261123-021733) and peaked at 40.05-40.14, never on the roof. A recorded path that comes down
# onto walkable floor (within HOP_TOUCH of it) away from its ends and then climbs HOP_CLIMB more is cut there into two
# jumps, each a person's (its part of the path, apex and air time); the second leaves from that floor
HOP_TOUCH, HOP_CLIMB, HOP_END = 0.12, 0.25, 0.4
# ... only when every hop it makes is one a person jumps (HOP_MAX_FLAT u flat at most): a Forge man cannon's recorded
# throw (The Cage's, 15.5 u) began with the person's step onto its pad, and cut there it lost its take-off on the pad
HOP_MAX_FLAT = 5.0


def split_hops(links, T):
    """links with every recorded jump that touched walkable floor partway cut into its hops (see HOP_TOUCH)."""
    out = []
    for k in links:
        parts = _split_hop(k, T)
        if len(parts) > 1 and any(math.dist(p["take_off"][:2], p["land"][:2]) > HOP_MAX_FLAT for p in parts):
            parts = [k]                          # (a launch, a ride: kept whole)
        out += parts
    return out


def _split_hop(k, T, depth=0):
    path = k.get("path") or []
    if (depth > 6 or k.get("kind") in ("crouch", "route") or k.get("ride") or len(path) < 5
            or not k.get("take_off") or not k.get("land")):
        return [k]
    a, b = k["take_off"], k["land"]
    for n in range(1, len(path) - 1):
        x, y, z = path[n][:3]
        if math.hypot(x - a[0], y - a[1]) < HOP_END or math.hypot(x - b[0], y - b[1]) < HOP_END:
            continue
        if max(q[2] for q in path[n + 1:]) < z + HOP_CLIMB or not T.inside(x, y):
            continue
        l, j, i = T._node(Vec(x, y, z))
        if not T.lwalk[l, j, i] or abs(float(T.lz[l, j, i]) - z) > HOP_TOUCH:
            continue
        frac = n / (len(path) - 1)
        air = k.get("air_s")
        first = dict(k, land=list(path[n][:3]), path=[list(q) for q in path[:n + 1]],
                     apex=round(max(q[2] for q in path[:n + 1]), 2), split=1)
        second = dict(k, take_off=list(path[n][:3]), runup=list(path[n][:3]), path=[list(q) for q in path[n:]],
                      apex=round(max(q[2] for q in path[n:]), 2), split=1)
        if air is not None:
            first["air_s"], second["air_s"] = round(air * frac, 2), round(air * (1 - frac), 2)
        return [first] + _split_hop(second, T, depth + 1)
    return [k]


def usable_links(links, pvp=None):
    """LiDAR links bots may use: people's; jumps a bot called and landed on the call, in a match or in the
    simulator (tools/lidar_sim.py); others bots did twice. Not ones bots keep failing. In PvP matches
    (PVP) a big drop (2.5+ units down) only the simulator has landed waits until a bot has landed it
    once in a real game (LiDAR bots try them): the simulator's physics is close, not exact, and a
    missed drop is a death that gives the enemy a point. Small hops stay: the simulator only calls
    jumps whose small misses it survives, and gating them all cut Halo 3 Construct's levels apart
    (kills 4.9 -> 3.2 a minute)."""
    pvp = PVP if pvp is None else pvp

    def ok(k):
        if k.get("bot_fail", 0) >= 3 and not k.get("bot_ok", 0):
            return False
        if k.get("kind") not in ("crouch", "route") and path_rises([q[2] for q in k.get("path") or []]) >= 2:
            return False          # hops in a row recorded as one jump: not one a bot can make (hop_chain)
        if k.get("sim_fail", 0) >= 3 and k.get("sim_fail", 0) > 2 * k.get("sim_ok", 0) and not k.get("bot_ok", 0):
            return False
        if (pvp and not k.get("human", 0) and not k.get("bot_ok", 0)
                and k.get("take_off") and k.get("land") and k["take_off"][2] - k["land"][2] > 2.5):
            return False
        return bool(k.get("human", 0) or k.get("bot_ok", 0) >= 2
                    or ((k.get("called") or k.get("ride")) and (k.get("bot_ok", 0) or k.get("sim_ok", 0))))
    return [k for k in links if ok(k)]


def reviewed_moves(name):
    """maps/<map>/moves_review.json (tools/review_moves.py): people's moves off the nav, each reviewed:
    [{id, kind: "floor", ok, cells [[x, y, z]], why, by, at}]."""
    path = os.path.join(ROOT, name, "moves_review.json")
    return read_json(path).get("reviews", []) if os.path.exists(path) else []


def air_heights(hist):
    """(strafing, travelling) clearance over the floor from flown time per half-unit height (rides.json "h"): a quarter
    of the flying lower than the strafing height, three quarters lower than the travelling height; None under 30."""
    pts = sorted((float(b), n) for b, n in hist.items())
    tot = sum(n for _, n in pts)
    if tot < 30:
        return None

    def q(f):
        acc = 0
        for b, n in pts:
            acc += n
            if acc >= f * tot:
                return b
        return pts[-1][0]
    low = min(max(q(0.25), 2.0), 8.0)
    return low, min(max(q(0.75), low + 3.0), 30.0)


def rides_layers(names, T, files=None):
    """What people and bots drove and flew on these maps (maps/<name>/rides.json, tools/lidar.py RideWatch), for
    Terrain.add_rides: (drive cells [(x, y, z)], air {"low"|"high": {half-unit cell: floor z}}, heights (strafing,
    travelling) or None, marks {"takeoff"|"landing"|"turnback": [(x, y, z)]}). A drive cell counts once a person drove
    it or bots twice; heights come from people's flying (bots fly the heights they are given), else the bots'.
    Flown cells go to the layer their height is in (low under the middle of the two heights, high over it, both when
    flown at both)."""
    drive, hist, cells, marks = [], {"human": {}, "bot": {}}, {}, {"takeoff": [], "landing": [], "turnback": []}
    people, owner = [], []
    for f in files or [os.path.join(ROOT, nm, "rides.json") for nm in names]:
        d = read_json(f) if os.path.exists(f) else {}
        rows = [r for r in d.get("drive", []) if len(r) >= 5]
        drive += [tuple(r[:3]) for r in rows if r[3] >= 1 or r[4] >= 2 or (len(r) > 5 and r[5] >= 1)]
        people += [tuple(r[:3]) for r in rows if r[3] >= 1]
        owner += [tuple(r[:3]) for r in rows if len(r) > 5 and r[5] >= 1]
    if T is not None:                             # (called again on every rides save: set whole)
        # (custom, Nov 17) the owner's routes, his drives in LiDAR mode (tools/lidar.py RideWatch owner): the bots'
        # roads (Terrain._build_vnav OWNER_ROAD_COST). Once a map has them, people's drives in matches stay drivable
        # ground but are no roads (the owner: "sometimes my routes wouldn't be ideal for bots that's why I created the
        # lidar driving routes"); a map without them keeps people's drives as its roads (ROAD_COST)
        T.owner_drive = owner
        T.people_drive = [] if owner else people
        for r in d.get("air", []):
            c = cells.get((r[0], r[1]))
            cells[(r[0], r[1])] = list(r[2:]) if c is None else [c[0], c[1] + r[3], c[2] + r[4], min(c[3], r[5]),
                                                                   max(c[4], r[6])]
        for src in ("human", "bot"):
            for b, n in d.get("h", {}).get(src, {}).items():
                hist[src][b] = hist[src].get(b, 0) + n
        for k in marks:
            marks[k] += [tuple(r[:3]) for r in d.get(k, [])]
    heights = air_heights(hist["human"]) or air_heights(hist["bot"])
    mid = (heights[0] + heights[1]) / 2 if heights else 6.0
    air = {"low": {}, "high": {}}
    for c, (gz, sum_h, n, lo, hi) in cells.items():
        mean = sum_h / max(n, 1)
        if mean < mid or lo < mid:
            air["low"][c] = gz
        if mean >= mid or hi >= mid:
            air["high"][c] = gz
    return drive, air, heights, marks


def terrain(m, live_blocks=None):
    """The map's walkable terrain (brain/terrain.py), built once, with reachability from every spawn point so goals no
    player can reach snap to the nearest place one can. Floor people walked that the level data lacks joins it once
    reviewed and approved. live_blocks: solid objects read from the running game (brain/forge.py: a map variant's
    Forge pieces); given, the terrain is built again with them (kept in m, for growing). A map variant's terrain
    covers its window only (brain/variants.py), grown by grow and swap; m["shields"] (brain/forge.py shields) go
    onto every build. (custom, Nov 21) The first build of a map comes from the terrain cache when its exact inputs were
    built before (cache_key, prebuild_after_match), else it is built and filed there."""
    if live_blocks is not None:
        _TERRAIN.pop(m["name"], None)
        m["live_blocks"] = live_blocks
    if m["name"] not in _TERRAIN:
        T = None
        if live_blocks is None:
            try:
                _PRE[m["name"]] = _pickle_m(m)     # (this match's inputs, for the build after it: prebuild_after_match)
                T = _cache_load(m, cache_key(m))
                print(f"terrain: {'from the cache' if T is not None else 'building (not cached)'}", flush=True)
            except Exception as e:                   # (no cache: built as ever)
                print(f"terrain cache not read: {type(e).__name__}: {e}", flush=True)
                T = None
        if T is None:
            # (not filed here: the match changes its data, the people's walk, so the next match's terrain is built after
            # it, prebuild_after_match; filing it now pickled 640 MB in the match for a key the next match never asks)
            T = _build(m, m.get("window"))
        _TERRAIN[m["name"]] = T
    return _TERRAIN[m["name"]]


# (custom, Nov 21, the owner: the bots "stand still" at the start of a match) Building a map's terrain took 7.3 s on
# Asylum (reach_forge_halo/variants/v8e4a8930), every match, while the bots stood at their spawns: the brain's first tick
# came 10-17 s into each match. The terrain cache keeps the built terrain (and what _build sets on the map) in
# logs/terrain_cache, filed under a hash of everything it is built from: the map code (CACHE_CODE), every file in the
# map's data folders but those it never reads (CACHE_SKIP: written each match, read by others), the piece shapes, and
# the loaded map itself (its variant's first / last seen left out). The same inputs load it back in under a second; any
# change builds it again. Each match's data changes as it is played (the people's LiDAR walk, what bots learned), so
# after a match the next match's terrain is built from the saved data in the background (prebuild_after_match,
# tools/terrain_prebuild.py) while the person is in the post-game. CACHE_KEEP files are kept, the newest
CACHE_DIR = os.path.join(os.path.dirname(ROOT), "logs", "terrain_cache")
CACHE_KEEP = 6
CACHE_VERSION = b"terrain-cache 1"
CACHE_SKIP = frozenset(("stations.json", "lore.json", "oob.json", "owner_profile.json", "topdown.png", "lidar_sim.json",
                        "variant.json"))     # (variant.json: in the loaded map, m["variant"], its times left out)
CACHE_CODE = ("brain/terrain.py", "brain/maps.py", "brain/forge.py", "brain/placed.py", "brain/variants.py",
              "brain/callouts.py", "brain/core.py", "tools/lidar_rides.py", "tools/jumpphys.py")
CACHE_M_STATE = ("live_blocks", "shields", "points", "lanes", "holds",   # what _build sets on the map
                 "positions", "position_info")
_PRE = {}                                    # map name -> its pickled inputs at its first build (prebuild_after_match)


def _canon(x):
    """x as plain JSON data, the same in every process (sets sorted, objects by their fields, arrays by a hash)."""
    import hashlib
    if isinstance(x, dict):
        return {str(k): _canon(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    if isinstance(x, (set, frozenset)):
        import json
        return sorted((_canon(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True))
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if hasattr(x, "tobytes") and hasattr(x, "shape"):              # a numpy array
        return ["array", list(x.shape), str(x.dtype), hashlib.blake2b(x.tobytes(), digest_size=16).hexdigest()]
    if hasattr(x, "__dict__"):
        return [type(x).__name__, _canon(vars(x))]
    if hasattr(x, "__slots__"):
        return [type(x).__name__, [_canon(getattr(x, k, None)) for k in x.__slots__]]
    return repr(x)


def _map_inputs(m):
    """The loaded map as the cache key sees it: every field, its variant's first / last seen left out."""
    out = {k: v for k, v in m.items() if k not in ("grow",)}
    if isinstance(out.get("variant"), dict):
        out["variant"] = {k: v for k, v in out["variant"].items() if k not in ("first_seen", "last_seen")}
    return out


def cache_key(m):
    """(custom, Nov 21) The hash of everything m's terrain is built from (see CACHE_DIR), before its build."""
    import hashlib
    import json
    h = hashlib.blake2b(CACHE_VERSION, digest_size=20)
    top = os.path.dirname(ROOT)
    for rel in CACHE_CODE:
        p = os.path.join(top, *rel.split("/"))
        h.update(rel.encode())
        h.update(_read(p) if os.path.exists(p) else b"-")
    shapes = os.path.join(ROOT, "_shapes")
    if os.path.isdir(shapes):
        for fn in sorted(os.listdir(shapes)):
            st = os.stat(os.path.join(shapes, fn))
            h.update(f"{fn}:{st.st_size}:{st.st_mtime_ns}".encode())
    seen = set()
    for nm in data_names(m):
        d = os.path.join(ROOT, nm)
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else ():
            p = os.path.join(d, fn)
            if fn in CACHE_SKIP or fn.endswith(".tmp") or not os.path.isfile(p):
                continue
            seen.add(os.path.normcase(os.path.abspath(p)))
            h.update(f"{nm}/{fn}".encode())
            h.update(_read(p))
    hm = m.get("heightmap")
    if hm and os.path.normcase(os.path.abspath(hm)) not in seen and os.path.exists(hm):
        h.update(_read(hm))
    h.update(json.dumps(_canon(_map_inputs(m)), sort_keys=True).encode())
    return h.hexdigest()


def _read(p):
    with open(p, "rb") as f:
        return f.read()


def _cache_file(name, key):
    return os.path.join(CACHE_DIR, name.replace("/", "~").replace("\\", "~") + "." + key + ".pkl.z")


def _pickle_m(m):
    import pickle
    return pickle.dumps(_map_inputs(m), protocol=5)


def _m_state(m):
    """What _build sets on the map (CACHE_M_STATE, items' reachable, zone centres), to put back on a cache load."""
    return dict({k: m.get(k) for k in CACHE_M_STATE}, reachable=[it.get("reachable") for it in m["items"]],
                zones=[z.center for z in m["zones"].zones])


def _cache_load(m, key):
    """The cached terrain for key, its build's settings put on m; None when there is none (or it does not fit m)."""
    import pickle
    import zlib
    p = _cache_file(m["name"], key)
    if not os.path.exists(p):
        return None
    T, state = pickle.loads(zlib.decompress(_read(p)))
    if len(state["reachable"]) != len(m["items"]) or len(state["zones"]) != len(m["zones"].zones):
        return None
    for k in CACHE_M_STATE:
        if state.get(k) is not None or k in m:
            m[k] = state[k]
    for it, r in zip(m["items"], state["reachable"]):
        if r is not None:
            it["reachable"] = r
    for z, c in zip(m["zones"].zones, state["zones"]):
        z.center = c
    os.utime(p)                              # (recently used: kept, CACHE_KEEP)
    return T


def _cache_save(m, key, T, wait=True):
    """File T (built from m's inputs, key) and m's build settings: pickled now, compressed and written in the background
    unless wait. The map's older files and all but the newest CACHE_KEEP go."""
    import pickle
    import zlib
    blob = pickle.dumps((T, _m_state(m)), protocol=5)

    def write():
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            p = _cache_file(m["name"], key)
            tmp = p + ".tmp"
            with open(tmp, "wb") as f:
                f.write(zlib.compress(blob, 3))
            os.replace(tmp, p)
            prefix = os.path.basename(_cache_file(m["name"], "")).rsplit(".pkl.z", 1)[0]
            files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f.endswith(".pkl.z")]
            for f in files:
                if os.path.basename(f).startswith(prefix) and os.path.abspath(f) != os.path.abspath(p):
                    os.remove(f)
            files = sorted((f for f in files if os.path.exists(f)), key=os.path.getmtime, reverse=True)
            for f in files[CACHE_KEEP:]:
                os.remove(f)
        except Exception as e:
            print(f"terrain cache not written: {type(e).__name__}: {e}", flush=True)
    if wait:
        write()
    else:
        import threading
        threading.Thread(target=write, daemon=True).start()


def prebuild_after_match(m):
    """(custom, Nov 21) After a match, its data saved: build the next match's terrain for this map from it in the
    background (tools/terrain_prebuild.py), from the inputs it was built from at this match's start (_PRE: its game
    mode's teleporters, its items) with its window as it is now. Returns the process, or None (no first build here)."""
    import pickle
    import subprocess
    import sys
    pre = _PRE.get(m["name"])
    if pre is None:
        return None
    m0 = pickle.loads(pre)
    m0["window"] = m.get("window")
    os.makedirs(CACHE_DIR, exist_ok=True)
    p = os.path.join(CACHE_DIR, "next_" + m["name"].replace("/", "~") + ".pkl")
    with open(p + ".tmp", "wb") as f:
        pickle.dump(m0, f, protocol=5)
    os.replace(p + ".tmp", p)
    tool = os.path.join(os.path.dirname(ROOT), "tools", "terrain_prebuild.py")
    return subprocess.Popen([sys.executable, "-I", tool, p], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def data_names(m):
    """Whose navmesh data a map's nav is built from: its own; a map variant of a built-in map (one whose scenario places
    things: Invasion: Spire's layout, a CTF variant) the base map's first, then its own. Live: Spire's Invasion layout,
    filed as a variant, had none of the base's LiDAR jumps, approved ramps and cover spots, so no attacker could get up
    to the core (four games) and the cover posts found no cover. A Forge canvas's variants (Forge World) keep their own
    navmesh, as the player asked ("paradiso is a separate navmesh")."""
    from .variants import base_of, base_area
    base = base_of(m["name"])
    if base != m["name"] and base_area(m.get("objects") or {}):
        return [base, m["name"]]
    return [m["name"]]


def people_walked(names, kinds=None):
    """Cells stood on, from the maps' LiDAR "walk" (0.25 u x 0.1 u keys): every record, or only those of the given kinds
    (tools/lidar.py KIND_*: 0 bot, 1 human, 3 crouched human...)."""
    out = set()
    for nm in names:
        lp = os.path.join(ROOT, nm, "lidar.json")
        if os.path.exists(lp):
            d = read_json(lp)
            c, zs = d.get("cell", 0.25), d.get("zstep", 0.1)
            out |= {(round(w[0] * c / 0.25), round(w[1] * c / 0.25), round(w[2] * zs / 0.1)) for w in d.get("walk", ())
                    if kinds is None or (w[3] if len(w) > 4 else 0) in kinds}
    return out


def _build(m, window):
    """A new terrain for map m over window (None: the whole level); terrain() keeps it, grow() makes one bigger."""
    from .terrain import Terrain
    names = data_names(m)
    floor = [c for nm in names for r in reviewed_moves(nm) if r.get("ok") and r.get("kind") == "floor" for c in r["cells"]]
    pdata = {}
    for nm in names:                     # painted by hand on the roofless view (tools/paint.py)
        pf = os.path.join(ROOT, nm, "paint.json")
        d = read_json(pf) if os.path.exists(pf) else {}
        for k, v in d.get("layers", {}).items():
            pdata.setdefault("layers", {}).setdefault(k, []).extend(v)
        pdata.setdefault("jumps", []).extend(d.get("jumps", []))
    paint = pdata.get("layers", {})
    # jumps the player drew on the painter's view (tools/paint.py "jumps"): people's jumps, one way, never
    # filtered
    painted = [dict(take_off=list(j[:3]), land=list(j[3:6]), kind="jump", painted=1, human=1, found_by="person")
               for j in pdata.get("jumps", []) if len(j) == 6]
    # drops the player showed onto something that breaks the fall (maps/<map>/drops.json; Spire's heat vents):
    # people's too, with a run-up (soft: onto a vent)
    for nm in names:
        df = os.path.join(ROOT, nm, "drops.json")
        painted += [dict(k, kind="jump", painted=1, human=1, found_by="person", soft=1)
                    for k in (read_json(df).get("drops", []) if os.path.exists(df) else [])]
    floor = list(floor) + [tuple(c) for c in paint.get("walk", [])]
    from .placed import static_boxes             # placed crates, walls, rocks the level mesh lacks (brain/placed.py); a
    # map variant's are its own pieces (it may have moved or removed the scenario's), kept in its variant.json
    game = next((g for g in ("reach", "h4", "h2a") if m["name"].startswith(g + "_")), None)
    blocks = static_boxes(m["objects"], game) if game and "variant" not in m else []
    if "variant" in m and m.get("live_blocks") is None:
        from .forge import nav_pieces, piece_key
        from .variants import pieces_of
        # pieces seen to come and go (variant.json "dynamic", forge.PieceWatch): walls only while they stand
        dyn = set(m["variant"].get("dynamic", ()))
        m["live_blocks"], m["shields"] = nav_pieces([p for p in pieces_of(m["variant"]) if piece_key(p[0], p[1]) not in dyn],
                                                    m["variant"].get("game") or "reach")
    blocks = list(blocks) + list(m.get("live_blocks") or [])
    # cells people stood on (LiDAR "walk" of a person, standing or crouched: the bots' own records are no proof a body
    # fits; Spire's variant had bot records under the rock lip its attackers stalled at, S10)
    walked = people_walked(names, kinds=(1, 3))
    T = Terrain(m["heightmap"], m["bases"], extra_floor=floor, blocks=blocks, slit_rule=m["name"].startswith(SLIT_GAMES),
                stair_rule=m["name"].startswith(("h4_", "h2a_")),
                window=window, walked=walked, lifts=[f["pos"] for f in m.get("features", []) if f.get("kind") == "lift"])
    T.add_links(m["teleporters"])
    T.vblocks = [b for nm in names for b in owner_vblocks(nm)]   # (custom, Nov 13: no vehicle in these, every size)
    if not m["name"].startswith(("h2_", "h3_", "reach_", "odst_", "h2a_", "h4_")):  # jump links, for skilled bots (CE jump physics; ponytail:
        T.build_jumps()                  # Halo 2's jump is not measured yet, so no gap jumps there)
    data = {}
    for nm in names:                     # jumps people landed (tools/lidar.py), unless bots keep failing them
        lidar = os.path.join(ROOT, nm, "lidar.json")
        d = read_json(lidar) if os.path.exists(lidar) else {}
        for k in ("walk", "cover", "jumps", "links"):
            data.setdefault(k, []).extend(d.get(k, []))
    links = []
    if any(data.values()):
        from .terrain import crouch_key  # and floor people walked crouched: every bot crouches there
        # (custom, Nov 8: only under a ceiling a standing body does not fit under, Terrain.low_overhead. The live LiDAR
        # paints every place a person held crouch, his fight crouches too: Haven had 535 such cells, 11 of them under a
        # low ceiling, and 57-76% of every tier's crouched rows stood on them, Demons crouched 19-21% of the time on foot
        # to 1.7-6% before; the owner, Nov 8: "why do the demons crouch so much now". CROUCH_LOW_ONLY False: every cell)
        pts = [(x * 0.25, y * 0.25, z * 0.1) for x, y, z, k, n in data.get("walk", []) if k == 3]
        keep = T.low_overhead(pts) if CROUCH_LOW_ONLY else [True] * len(pts)
        T.crouch_cells = {crouch_key(*p) for p, ok in zip(pts, keep) if ok}
        if data.get("cover"):                # floor in front of upright walls LiDAR painted (glass excluded)
            import numpy as np
            T.cover_spots = np.array(data["cover"], dtype=float)
        jumps = sorted(data.get("jumps", []))       # apexes LiDAR measured on this map
        T.jump_apex = jumps[len(jumps) // 2] if len(jumps) >= 20 else 0.8
        links = usable_links(split_hops(data.get("links", []), T))   # (custom, Nov 23: a person's hops, one at a time)
    links = off_gone_pads(anchor_launches(links + painted, m.get("features", [])), m.get("lifts_gone"))
    links = forge_throws(links, m.get("features", []))   # (custom, Nov 18) a Forge cannon's recorded throws
    links += owner_ride_links(names)    # (custom) the owner's lifts and man cannons (LiDAR view, Edit spots)
    links += map_lift_rides(m["name"], T, links)   # (custom, Nov 18) lifts nobody rode: their solved rides
    if links:
        T.add_human_links(links)
    if paint:
        T.apply_paint(paint)             # blocked, drivable and flying cells (Terrain.apply_paint)
    # where bot drivers wedged, live (tools/wedges.py): the floor round them no person drove is left off the vehicles'
    # ground (Terrain._build_vnav; Spire's gap south of (-143, -354))
    wedge_files = [os.path.join(ROOT, nm, "wedges.json") for nm in names]
    T.nodrive = [c for f in wedge_files if os.path.exists(f) for c in read_json(f).get("nodrive", [])]
    drive, air, heights, marks = rides_layers(names, T)   # and what people and bots drove and flew (tools/lidar.py)
    if drive or air["low"] or air["high"] or heights or any(marks.values()):
        T.add_rides(drive, air, heights, marks)
    T.set_spawns(spawn_points(m))
    for it in m["items"]:                # an item on a rock top nobody can reach is not worth a trip
        it["reachable"] = T.inside(it["pos"].x, it["pos"].y) and bool(T.reach[T._node(it["pos"])])
    keep_reachable_positions(m, T)       # (custom, Nov 23) power positions nobody can stand on: left out

    def snap(p):                         # a point no player can stand on (Halo 2 Lockout's mid at
        if not T.inside(p.x, p.y):       # (outside a variant's window: left as it is)
            return p
        l, j, i = T._node(p)             # z 0, in the air between its levels) -> nearest reachable floor
        return T._center(*T._reachable_node(l, j, i, p.z))
    m["points"] = {k: snap(p) for k, p in m["points"].items()}
    m["lanes"] = [snap(p) for p in m["lanes"]]
    m["holds"] = {t: [snap(p) for p in hs] for t, hs in m["holds"].items()}
    for z in m["zones"].zones:           # zone centres at the real floor height (callout spots),
        if T.inside(z.center.x, z.center.y):
            c = Vec(z.center.x, z.center.y, T.floor_in_band(z.center.x, z.center.y, z.zmin, z.zmax))
            z.center = snap(c)           # and on ground players reach (Sidewinder's Mid sat in rock)
    T.people_walked = people_walked(names)   # cells anyone stood on: never a learned wall (Terrain.learn_stuck)
    for nm in names:                     # (a built-in map's variant: the base's learned spots too)
        learned = os.path.join(ROOT, nm, "los_learned.json")
        if os.path.exists(learned):
            T.blocked = set(getattr(T, "blocked", set())) | {tuple(k) for k in read_json(learned)}
        learned = os.path.join(ROOT, nm, "nav_learned.json")
        if os.path.exists(learned):
            for x, y, z in read_json(learned):
                T.learn_stuck(Vec(x, y, z), sure=True)
    kinds = {}                           # windows and fences (tools/lidar_walls.py): walls you see through, fences you
    for nm in names:                     # shoot through too (Terrain.set_wall_kinds, sees, shot_los)
        wk = os.path.join(ROOT, nm, "wall_kinds.json")
        if os.path.exists(wk):
            kinds = read_json(wk)
            break
    from .terrain import piece_wall_kinds   # and placed pieces' own (a Forge railing, glass, an energy pane)
    pk = piece_wall_kinds(blocks)
    learned = []                         # and spots rounds went through (Terrain.learn_shot_through): fences
    for nm in names:
        lf = os.path.join(ROOT, nm, "walls_learned.json")
        learned += read_json(lf) if os.path.exists(lf) else []
    # (custom, Nov 18) none inside a Forge piece (Terrain.piece_solid: its collision model is exact; Pinnacle's 40 were
    # all in its dish, rocks, bridges and tower). Kept in the file, only not used
    used = [c for c in learned if not T.piece_solid(c[0] / 4, c[1] / 4, c[2], c[3], deck=bool(c[4]))]
    pk["fence"] += [c[:4] for c in used if not c[4]]
    pk["fence_floor"] += [c[:4] for c in used if c[4]]
    if any(pk.values()):
        kinds = dict(kinds, **{k: list(kinds.get(k, [])) + v for k, v in pk.items()})
    if any(kinds.get(k) for k in ("window", "fence", "window_floor", "fence_floor")):
        T.set_wall_kinds(kinds)
    T.walls_learned = [list(c) for c in learned]
    open_areas = []                      # custom: air under a lone overhead surface over a ground hole in the export
    for nm in names:                     # (Terrain.set_open_under; Breakpoint's tower-to-bridge gap)
        so = os.path.join(ROOT, nm, "sight_open.json")
        open_areas += read_json(so).get("areas", []) if os.path.exists(so) else []
    T.set_open_under(open_areas)
    if m.get("shields"):                 # Forge shields (brain/forge.py): sight-line stops and one-way barriers
        from .forge import apply_shields
        apply_shields(T, m["shields"])
    return T


def keep_reachable_positions(m, T):
    """(custom, Nov 23, the owner on Sword Base: "Make bots use this lift ... it leads to floor 3. So make routes worth
    it", "Swordbase is usually height is most important") The power positions (positions.json) no player can stand on
    are left out, with their position_info: Sword Base's four on its roof (z 38) got 40% of the bots' orders in match
    20261123-132333 while nobody stood over z 33, and the bots held the floor under them (z 24.5-29.6) instead of floor
    3's four posts. Outside a variant's window they are kept as they are."""
    pts, info = m.get("positions") or [], m.get("position_info") or []
    ok = [not T.inside(p.x, p.y) or bool(T.reach[T._node(p)]) for p in pts]
    if all(ok):
        return
    gone = [p for p, k in zip(pts, ok) if not k]
    print(f"positions: {len(gone)} of {len(pts)} out of reach, left out: "
          + ", ".join(f"({p.x:.0f}, {p.y:.0f}, {p.z:.0f})" for p in gone), flush=True)
    m["positions"] = [p for p, k in zip(pts, ok) if k]
    if len(info) == len(pts):
        m["position_info"] = [i for i, k in zip(info, ok) if k]


def spawn_points(m):
    """Where players start: a map variant's own spawn objects (named *spawn*; Forge World's scenario spawns are not
    its), else the map's spawns."""
    own = [_v(o[1:4]) for o in (m.get("variant") or {}).get("objects", []) if "spawn" in o[0]]
    return own or [p for mode in m["spawns"].values() for team in mode.values() for p in team]


def grow(m, positions):
    """Grow a map variant's nav window when a player nears an edge the level goes on past: the bigger terrain is built
    in the background, swap puts it in. Returns the new window, or None (no variant, nothing to grow, a build already
    running)."""
    g = m.setdefault("grow", {})
    T = _TERRAIN.get(m["name"])
    if m.get("window") is None or T is None or g.get("job") is not None or g.get("ready"):
        return None
    from .variants import grown
    win = tuple(m["window"])
    for p in positions:
        win = grown(win, p, T.full) or win
    if win == tuple(m["window"]):
        return None
    import threading

    def job():
        try:
            g["ready"] = (win, _build(m, win))
        finally:
            g["job"] = None
    g["job"] = threading.Thread(target=job, daemon=True)
    g["job"].start()
    return win


def swap(m):
    """Put a grown terrain (grow) in the place of the one in use, in the same object, so bots, directors and LiDAR keep
    theirs; what they learned meanwhile comes along; the window is kept for the variant's next match. Call between
    ticks. True when it swapped."""
    ready = (m.get("grow") or {}).pop("ready", None)
    if not ready:
        return False
    win, new = ready
    T = _TERRAIN.get(m["name"])
    if T is not None:
        new.blocked |= T.blocked
        for k in T.stuck - new.stuck:
            new.learn_stuck(Vec(*k), sure=True)
        T.__dict__.clear()
        T.__dict__.update(new.__dict__)
    else:
        _TERRAIN[m["name"]] = new
    m["window"] = win
    from .variants import save_window
    save_window(m["name"], win)
    return True


def save_learned(m):
    """Write what bots learned the level data misses to the map folder, so the next match starts
    knowing it: blocked sight lines (Terrain.learn_blocked), spots they could not walk through
    (Terrain.learn_stuck), spots rounds went through (Terrain.learn_shot_through)."""
    T = _TERRAIN.get(m["name"])
    if T is None:
        return
    import json
    for name, data in (("los_learned.json", T.blocked), ("nav_learned.json", T.stuck),
                       ("walls_learned.json", [tuple(c) for c in getattr(T, "walls_learned", [])])):
        if data:
            tmp = os.path.join(ROOT, m["name"], name + ".tmp")
            json.dump(sorted(data), open(tmp, "w"))
            os.replace(tmp, tmp[:-4])
    from . import lore                   # (custom, Nov 19) and the layout's map memory (brain/lore.py: lore.json)
    try:
        lore.save(m)
    except OSError as e:
        print(f"map memory not saved: {e}", flush=True)


def get_map(name):
    """Map data by name (the scenario's file name, e.g. bloodgulch), loaded once."""
    if name not in _MAPS:
        _MAPS[name] = load_map(name)
    return _MAPS[name]


BLOODGULCH = get_map("bloodgulch")

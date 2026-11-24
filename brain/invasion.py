"""Halo: Reach Invasion.

The game: Elites attack, Spartans defend, in three phases. Phases 1 and 2: the attackers take either of two
territories (stand in it, uncontested); phase 3: they carry the core from its stand to the delivery point. Each phase
moves both teams' respawn zones forward, and opens gates (laser fields, shield doors) on the attackers' way. The
Spartans' spawn rooms have one-way shields: out only.

Everything here comes from the map's own scenario (maps/<map>/objects.json, Invasion's labelled netgame objects) and
the editing kit's collision models (maps/_shapes/reach.json, tools/object_shapes.py):
  inv_objective     the territories and the core's delivery point (which is which: by phase, below)
  inv_obj_flag      the core's stand
  inv_res_p1..p3    each team's respawn zones by phase (team 0, team 1)
  inv_gates         objects that block until a phase opens them (present while closed)
  one-way shields   any Invasion object whose collision material ends "_for" (ff_one_way_door_*,
                    dlc_vehicle_bay_shield_door_*): through from its front (facing) side to its back only
Phases are told apart live by where each team respawns (brain/invasion.py phase_from_spawns) and by the core.
"""
import json
import math
import os

from .core import Vec

SHAPES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps", "_shapes", "reach.json")
TERRITORY_R = 3.5          # ponytail: a territory's boundary is a Megalo shape not read; ~3.5 u is a hill beacon's ring
SPAWN_NEAR = 10.0          # a respawn this close to a respawn zone of the attackers says its phase (Boneyard: within ~8 u)


def _v(p):
    return Vec(p[0], p[1], p[2])


def _shapes():
    return json.load(open(SHAPES, encoding="utf-8"))["shapes"] if os.path.exists(SHAPES) else {}


def _centroid(pts):
    return Vec(sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), sum(p.z for p in pts) / len(pts))


def layout(objs, shapes=None, styles=None):
    """The map's Invasion setup, or None on a map without one:
    dict(attackers=team, defenders=team, phases={1: [territory Vec, ...], 2: [...], 3: [delivery Vec]},
         core=Vec (the stand), res={team: {phase: [Vec]}}, barriers=[dict(key, a, b, z0, z1, through, kind)], bomb=Vec
         or None, bomb_phase). styles: a custom variant's phase objectives (brain/mvar.py phase_styles, {phase:
         "assault" ...}): a map variant file's Assault phase has its bomb at that phase's inv_obj_flag."""
    flags = objs.get("netgame_flags", [])
    of = lambda t: [f for f in flags if f["type"] == t]
    goals = [_v(f["pos"]) for f in of("inv_objective")]
    # each objective's zone size from its boundary (tools/reach_export.py): a cylinder's radius, half a box's short
    # side (Boneyard's territories are boxes of 1.75 x 2.5: a bot 2 u off the marker stood outside)
    zone_r = []
    for f in of("inv_objective"):
        b = f.get("boundary") or {}
        r = b.get("w", 0) if b.get("shape") == "cylinder" else min(b.get("w", 0), b.get("l", 0) or b.get("w", 0)) / 2
        zone_r.append((_v(f["pos"]), max(0.6, min(4.0, r or TERRITORY_R))))
    core = [_v(f["pos"]) for f in of("inv_obj_flag")]
    res = {}
    # a map variant read from its file (brain/mvar.py) gives each object's spawn sequence as "phase": on Bungie's own
    # Boneyard and Breakpoint files inv_objective 1, 2, 3 are the phase 1 and 2 territories and the delivery point,
    # inv_obj_flag 3 the core's stand, 2 Breakpoint's bomb (DERIVED, haloreach/map_variants). Respawn zones: inv_res_zone
    # by team and sequence where the map has them so (issue #2: custom maps use Inv_res_zone alone, as Inv_Res_ph1 to 3
    # do not work in customs) when it has no inv_res_p1..p3 (Boneyard has both: its p1..p3 hold)
    zoned = [] if any(of(f"inv_res_p{ph}") for ph in (1, 2, 3)) else [
        f for f in of("inv_res_zone") if f.get("phase") in (1, 2, 3) and f["team"] in (0, 1)]
    for ph in (1, 2, 3):
        for f in [f for f in zoned if f["phase"] == ph] if zoned else of(f"inv_res_p{ph}"):
            res.setdefault(f["team"] % 2, {}).setdefault(ph, []).append(_v(f["pos"]))
    if len(goals) < 3 or not core or len(res) < 2 or any(1 not in r for r in res.values()):
        return None
    staged = {ph: [_v(f["pos"]) for f in of("inv_objective") if f.get("phase") == ph] for ph in (1, 2, 3)}
    staged = staged if all(staged.values()) else None
    # the attackers start farther from every objective (Boneyard: team 1 at x 220, the objectives at 250-310), from
    # phase 1's where the file says which they are (Tempest, issue #2: the attackers' Pelican waits by their own side)
    far = {t: min((_centroid(r[1]) - g).flat() for g in (staged[1] if staged else goals)) for t, r in res.items()}
    att = max(far, key=far.get)
    dfn = 1 - att
    # each phase's territories: the two objectives nearest the defenders' respawn zone of that phase; the one left
    # (farthest from where the core stands... nearest the attackers' phase 3 zone) is the core's delivery point
    left = list(goals)
    phases = {}
    for ph in (1, 2):
        zone = res[dfn].get(ph) or res[dfn][1]
        c = _centroid(zone)
        pick = sorted(left, key=lambda g: (g - c).flat())[:2]
        phases[ph] = pick
        left = [g for g in left if g not in pick]
    # the core's stand: beside the phase 2 territories (Breakpoint has a second core marker by phase 1)
    c2 = _centroid(phases[2])
    stand = min(core, key=lambda q: (q - c2).flat())
    phases[3] = [max(left, key=lambda g: (g - stand).flat())] if left else [goals[-1]]
    # Breakpoint's phase 2 is a bomb run (halopedia, Invasion: "arm the bomb"; Breakpoint: "plant a bomb on the outside
    # of the vault"): its second core marker, by phase 1, is the bomb's stand; the phase 2 markers are where it is armed
    bomb = next((q for q in core if (q - stand).flat() > 5.0), None)
    if staged:                                    # (the file's own phases, core stand and bomb stand)
        phases = {1: staged[1], 2: staged[2], 3: staged[3][:1]}
        by = {f.get("phase"): _v(f["pos"]) for f in of("inv_obj_flag")}
        stand = by.get(3, stand)
        bp = next((ph for ph in (1, 2) if styles.get(ph) == "assault"), None) if styles else 2
        bomb = by.get(bp) if bp else None
    shp = _shapes() if shapes is None else shapes
    bars = []
    for k, f in enumerate(flags):
        name = f.get("object", "")
        s = shp.get(name)
        if not s or f["type"] not in ("invasion", "inv_gates", "inv_platform"):
            continue
        (x0, y0, z0), (x1, y1, z1) = s["min"], s["max"]
        if z1 - z0 < 0.5 or max(x1 - x0, y1 - y0) < 0.6:
            continue                              # too low or too small to stop a body (hill beacons, markers)
        if f["type"] == "inv_platform" and any((_v(f["pos"]) - q).flat() < 1.0 for q in core):
            continue                              # the core's (or bomb's) own stand: walked up to, not a wall (Spire's
                                                  # cov_powermodule_stand, a gate on the core: attackers 2 u off, live)
        if f["type"] == "inv_platform" and staged and (_v(f["pos"]) - phases[3][0]).flat() < 5.0:
            continue                              # the ship the core is delivered to (Tempest's Pelican, 1.7 u off)
        uz = (f.get("up") or (0, 0, 1))[2]
        if abs(uz) < 0.9:
            continue                              # a piece on its side (a floor tile stood up as a wall): brain/forge.py
                                                  # PieceWatch walls it with its real axes; this outline is yaw-only
        if uz < 0:                                # upside down (a map variant file's: Spire's big phase 1 shield
            z0, z1, y0, y1 = -z1, -z0, -y1, -y0   # doors hang from their spot), so it reaches down, left mirrored
        yaw = math.radians(f.get("facing") or 0.0)
        fx, fy = math.cos(yaw), math.sin(yaw)     # the object's forward; left = (-fy, fx)
        p = _v(f["pos"])
        if y1 - y0 >= x1 - x0:                    # a wall across its forward axis (doors, fields): its long side
            cx = (x0 + x1) / 2
            a = Vec(p.x + fx * cx - fy * y0, p.y + fy * cx + fx * y0, 0.0)
            b = Vec(p.x + fx * cx - fy * y1, p.y + fy * cx + fx * y1, 0.0)
        else:                                     # long along its forward axis (a bomb door, a barrier)
            cy = (y0 + y1) / 2
            a = Vec(p.x + fx * x0 - fy * cy, p.y + fy * x0 + fx * cy, 0.0)
            b = Vec(p.x + fx * x1 - fy * cy, p.y + fy * x1 + fx * cy, 0.0)
        one_way = s.get("material", "").endswith("_for")
        kind = "one_way" if one_way else ("gate" if f["type"] in ("inv_gates", "inv_platform") else "solid")
        bars.append(dict(key=f"inv{k}", a=a, b=b, z0=p.z + z0, z1=p.z + z1, kind=kind, name=name, pos=p,
                         through=Vec(-fx, -fy, 0.0) if one_way else None))
    # the phase's man cannons: an inv_mancannon spawns in its sequence's phase (Spire's three: 3, a Nov 6 playtest:
    # phase 3 only); phase_link_gates closes the people's links off them before then
    launchers = [(_v(f["pos"]), f.get("phase", f.get("seq"))) for f in flags if f.get("type") == "inv_mancannon"]
    # a map variant's own Invasion vehicles (inv_vehicle, its team the side's label, its sequence the phase it first
    # spawns in; the built-in maps' come from their scenario: inv_vehicles); label_pick sends a driver for each
    # (upstream 0.3.0, build 20261118-1714)
    vehicles = [dict(kind=f.get("object"), pos=_v(f["pos"]),
                     side="att" if f.get("team") == att else "def" if f.get("team") == dfn else None,
                     phase=f.get("phase", f.get("seq")) if f.get("phase", f.get("seq")) in (1, 2, 3) else 1)
                for f in flags if f.get("type") == "inv_vehicle"]
    return dict(attackers=att, defenders=dfn, phases=phases, core=stand, res=res, barriers=bars, zone_r=zone_r,
                bomb=bomb, bomb_phase=(bp if staged else 2) if bomb is not None else None, launchers=launchers,
                spawn_res=label_spawns(flags), vehicles=vehicles)


def label_spawns(flags):
    """{label team: {phase: [Vec]}}: where a side respawns each phase by the map's Invasion labels (GitHub #26, a
    custom Tempest map: the bots never spawned in its zones). inv_res_p1..p3 serve their own phase only; an inv_res_zone
    with spawn sequence k serves phase k and every later one (sequence 1: all three; 2: phases 2 and 3; 3: phase 3; no
    sequence: all). Team 8 (neutral) zones serve both teams. The labels' team is the map's: the side that attacks a
    round uses the map attackers' zones (the teams swap each round, the zones do not). (upstream 0.3.0, build
    20261118-1714)"""
    out = {}
    for f in flags:
        t, team, seq = f.get("type", ""), f.get("team"), f.get("phase", f.get("seq"))
        if t in ("inv_res_p1", "inv_res_p2", "inv_res_p3"):
            phases = (int(t[-1]),)
        elif t == "inv_res_zone":
            k = seq if seq in (1, 2, 3) else 1
            phases = tuple(range(k, 4))
        else:
            continue
        for tm in ((0, 1) if team not in (0, 1) else (team,)):
            for ph in phases:
                out.setdefault(tm, {}).setdefault(ph, []).append(_v(f["pos"]))
    return out


def label_spawn(inv, phase, attacking, goal):
    """The zone a dead bot respawns at on a map with labelled zones and no named spawns (label_spawns): its side's
    zones this phase (the attackers': the map attackers' labels), the one nearest the phase's objective `goal` (the
    reporter's play: later, forward spawns; a phase with none: the nearest phase before). None where the map has none.
    (upstream 0.3.0, build 20261118-1714)"""
    team = inv["attackers"] if attacking else inv["defenders"]
    zones = (inv.get("spawn_res") or {}).get(team) or {}
    for ph in range(phase, 0, -1):
        if zones.get(ph):
            pts = zones[ph]
            return min(pts, key=lambda q: (q - goal).flat()) if goal is not None else pts[0]
    return None


# the ways up to a phase 3 core on high (a Spire playtest, Nov 6 19:11-19:38: the attackers all funnelled
# into one way up; 12 of 16 climbs went by lift 2): where each starts
# (the playtest's places), the attackers' runners spread over them (director.assign_roles: the via of a runner)
CLIMBS = {"reach_35_island": [(-172.15, -401.02, -62.49), (-177.67, -400.60, -62.38), (-142.14, -391.64, -53.68),
                              (-161.15, -381.07, -57.29), (-191.63, -389.23, -57.24)]}   # lift 2, lift 1, cannons 1-3
CLIMB_UP = 15.0           # u: a core this high over a climb's start is taken by one of them


def climbs_for(map_name):
    """CLIMBS for a map (its base map's for a variant), [] where none."""
    return [Vec(*p) for p in CLIMBS.get((map_name or "").split("/")[0].split("@")[0], ())]


# rides whose landing a phase changes (a Spire playtest Nov 6: in phase 2 every spire grav lift lands
# on the lower building's roof, (-173.8, -399.3, -55.9); in phase 3 to the spire's top): {base map: [(take-off
# x, y, within u, landing over z, from phase)]}: a people's link off that lift landing over that height is closed before
LIFT_PHASES = {"reach_35_island": [(-177.67, -400.60, 3.0, -40.0, 3), (-172.15, -401.02, 3.0, -40.0, 3)]}
LAUNCHER_R, LAUNCH_UP = 2.5, 5.0   # u: a people's link taking off this near a man cannon (flat, 3 u up or down) and
                                  # climbing this much is its ride (not a hop off its pad)


def phase_link_gates(T, inv, phase, map_name=None):
    """Close the people's links (T.hjumps) the phase does not have: off a man cannon not spawned yet (inv launchers), up a
    lift to a landing it only reaches later (LIFT_PHASES). Applied by Watch at each phase."""
    rules = LIFT_PHASES.get((map_name or "").split("/")[0].split("@")[0], ())
    closed = set()
    for n, (f, t, k, w) in enumerate(getattr(T, "hjumps", ())):
        to, ld = k.get("take_off"), k.get("land")
        if not to or not ld:
            continue
        if ld[2] - to[2] >= LAUNCH_UP and any(
                ph is not None and phase < ph and math.hypot(p.x - to[0], p.y - to[1]) < LAUNCHER_R and abs(p.z - to[2]) < 3.0
               for p, ph in inv.get("launchers", ())):
            closed.add(n)
        elif any(phase < ph and math.hypot(x - to[0], y - to[1]) < r and ld[2] > zl for x, y, r, zl, ph in rules):
            closed.add(n)
    if hasattr(T, "set_link_gates"):
        T.set_link_gates(closed)
    return closed


def zone_radius(inv, p):
    """The size of the objective zone at (or nearest within 1 u of) p, else TERRITORY_R."""
    best = min(inv.get("zone_r", []), key=lambda zr: (zr[0] - p).flat(), default=None)
    return best[1] if best is not None and (best[0] - p).flat() < 1.0 else TERRITORY_R


def phase_from_spawns(inv, spawns, res=None):
    """The phase the attackers' respawns say: spawns [(team, Vec)] (the attacking team's recent respawn positions). Each
    votes for the phase of the attackers' zone nearest it; phases 2 and 3 share zones on most maps, so this tells 1
    from 2+. Only the attackers' zones: Boneyard's defender spawns lie nearest the attackers' phase 3 zone (live,
    round 2 of an 8v3: the defenders' respawns read as phase 3 for four minutes). res: the zones to read (default the
    p labels, inv["res"]; Watch falls back to every label, inv["spawn_res"], where they say nothing): there a zone that
    serves phase 1 and later ones (an inv_res_zone of sequence 1) says nothing of the phase. (upstream 0.3.0, build
    20261118-1714)"""
    votes = {}
    zones = (res or inv["res"]).get(inv["attackers"], {})
    for team, p in spawns:
        near = {ph: min((q - p).flat() for q in zs) for ph, zs in zones.items() if zs}
        best = min(near.items(), key=lambda x: x[1], default=None)
        if best is not None and res is not None:
            tied = {ph for ph, d in near.items() if d <= best[1] + 0.01}
            if 1 in tied and len(tied) > 1:
                continue
        # only a spawn in (or by) a zone says anything (live: blue respawns 20-50 u from every attackers' zone voted
        # phase 2 a minute early); phases 2 and 3 share their zones: a spawn says 2 at most
        if best is not None and best[1] < SPAWN_NEAR:
            votes[min(best[0], 2)] = votes.get(min(best[0], 2), 0) + 1
    if not votes:
        return None
    return max(votes, key=lambda ph: (votes[ph], ph))


def roles_from_spawns(inv, spawns, phase=1, res=None):
    """{player team: True if attacking} from recent respawns [(team, Vec)]: the side of the zone each team respawns in
    (the teams swap roles between rounds, so the scenario's team labels name roles, not the players' colours). Only
    that phase's zones count: the defenders' opening spawns on Boneyard lie nearer the attackers' phase 3 zone than
    any of their own (live: both teams read as attackers). res: the zones to read (default inv["res"], the p labels;
    Watch retries with inv["spawn_res"], every label, when they give no one attacker side: a custom Tempest's
    inv_res_zone spawns lie 8-25 u from its p labels and read as both teams defending). (upstream 0.3.0, build
    20261118-1714)"""
    votes = {}
    zones = {lb: zs.get(phase) or zs.get(1) or [] for lb, zs in (res or inv["res"]).items()}
    for team, p in spawns:
        label = min(zones, key=lambda lb: min(((q - p).flat() for q in zones[lb]), default=1e9))
        votes.setdefault(team, []).append(label == inv["attackers"])
    return {t: sum(v) * 2 > len(v) for t, v in votes.items()}


class Watch:
    """The live Invasion state for tools/live_bots.py: fills the snapshot's inv_ fields every tick and keeps the
    terrain's barriers in step with the gates standing in the game."""
    SPAWN_WINDOW = 45.0      # respawns this recent say the phase and the sides (a new round resets them at once)
    ROUND_WAIT = 30.0        # s after nearly everyone died at once (a round's change) before picks go out without one

    def __init__(s, inv, T):
        s.inv, s.T = inv, T
        s.alive, s.spawns = {}, []
        s.births, s.round_wait_until = [], -1.0   # everyone's respawn times (placed too); a round's change pending
        s.placed = set()                          # bots spawning where the brain picked (tools/live_bots.py spawn_check):
                                                  # picked by this phase, their spawns cannot tell it
        s.phase, s.attackers, s.sides_set = 1, inv["attackers"], False
        s.score_base = "first"                    # (attacking team, its score at the round's start); "first": 0 (a brain
                                                  # started mid-round counts the phases taken so far)
        s.score_seen, s.round_t = None, -99.0     # every team's score at the round's start (first read); when it began
                                                  # (upstream 0.3.0, build 20261120-1620: score_attacker)
        s.core, s.carrier, s.core_t = None, None, -9.0
        s.gates_t, s.gates = -9.0, [b for b in inv["barriers"] if b["kind"] == "gate"]
        s.gates_n, s.gates_low, s.step_t, s.gate_steps = None, None, -99.0, 0   # gates at the last step; last read
        apply_barriers(T, inv)

    SCORE_SETTLE = 10.0      # s into a round before its scores are taken as its zero (the round's change settles first)

    def score_attacker(s, scores, now):
        """The team whose score rises inside a round is the attackers (only they score: a phase taken). scores: {team:
        score} (low 16 bits). One team up by 1-2 since the round's start and not the one read: the sides were misread
        (a reported City match: the side's guess from its labels was a near tie, the score route read the other team's 0
        and phase 1 stood for 135 s after the capture), corrected, and that capture counts. Two teams up at once, a jump
        of 3 or more (a round's points), or within SCORE_SETTLE s of a round's start: nothing. Not while the Elites'
        team reads (elite_ok: that read decides). (upstream 0.3.0, build 20261120-1620)"""
        if s.score_seen is None:
            if now - s.round_t >= s.SCORE_SETTLE:
                s.score_seen = dict(scores)
            return
        for t, v in scores.items():
            if v < s.score_seen.get(t, 0):        # (a reset: the new zero)
                s.score_seen[t] = v
        up = [t for t, v in scores.items() if 1 <= v - s.score_seen.get(t, 0) <= 2]
        jumps = [t for t, v in scores.items() if v - s.score_seen.get(t, 0) > 2]
        if len(up) == 1 and not jumps and up[0] != s.attackers and not s.__dict__.get("elite_ok"):
            t = up[0]
            s.attackers, s.sides_set, s.score_base = t, True, (t, s.score_seen.get(t, 0))

    def update(s, live, snap, now, raw=None):
        for p in snap.players:                    # spawns: alive again after a death, or first seen alive (the
            if p.alive and not s.alive.get(p.id, False):                            # match start: the sides are known
                s.births.append(now)                                                # from the first tick)
                if p.id not in s.placed:
                    s.spawns.append((now, p.team, p.pos))
            s.alive[p.id] = p.alive
        s.spawns = [x for x in s.spawns if now - x[0] < s.SPAWN_WINDOW]
        s.births = [x for x in s.births if now - x < 3.0]
        # a round's change: nearly everyone dead at once (live Spire, 530-537 s: 0 of 16 alive). Until the new round
        # reads, spawn_check sends no picks (tools/live_bots.py): its picks by the old phase put the opening respawns
        # in the old round's spawns and out of the burst below, the round never read, the brain played phase 3 all of
        # round 2 with everyone spawning there
        if snap.players and sum(1 for p in snap.players if p.alive) * 5 <= len(snap.players):
            s.round_wait_until = now + s.ROUND_WAIT
        # a new round: most of the lobby spawning at once (the teams swap sides between rounds; live, Boneyard: the
        # last round's respawns outvoted the new ones for a minute). Only the burst counts from then on (after a
        # round's change everyone's respawn counts, a placed bot's too: the burst is about when, not where)
        burst = [x for x in s.spawns if now - x[0] < 3.0]
        need = max(3, 0.6 * len(snap.players))
        new_round = len(burst) >= need or (now < s.round_wait_until and len(s.births) >= need)
        if new_round and (len(burst) < len(s.spawns) or s.sides_set):   # (no deaths in the window: still a new round)
            s.spawns, s.core, s.carrier, s.phase = burst, None, None, 1
            s.round_wait_until = -1.0
            s.gate_steps, s.gates_n = 0, None     # (the gates stand again)
            s.score_base = None                   # the attackers' score now is the round's zero
            s.score_cap = 1 if s.__dict__.get("score_cap") is not None else None   # (the score reads: phase 1 until it says)
            # the sides unread until this round's spawns say them (a failed read kept last round's: the teams swap, so
            # the stale side is the wrong one; a reported City match). Until then no picks go out (spawn_check, the zone
            # path): the game's own opening spawns stand and tell the sides (upstream 0.3.0, build 20261120-1620)
            s.sides_set, s.score_seen, s.round_t = False, None, now
        recent = [(team, pos) for _, team, pos in s.spawns]
        # the sides: from the round's start, where everyone spawns in their side's first zone, then kept for the round
        # (live: defenders' later respawns sometimes land nearer an attackers' zone and flipped the sides every tick)
        if new_round or (not s.sides_set and len(recent) >= 4):
            seen = [(t, p) for _, t, p in (burst if new_round else s.spawns)]
            ph = 1 if new_round else s.phase
            att = [t for t, a in roles_from_spawns(s.inv, seen, ph).items() if a]
            if len(att) != 1 and s.inv.get("spawn_res"):
                # (the p labels gave no one side: every label, a map whose spawns are inv_res_zone objects; upstream
                # 0.3.0, build 20261118-1714)
                att = [t for t, a in roles_from_spawns(s.inv, seen, ph, s.inv["spawn_res"]).items() if a]
            if len(att) == 1:
                s.attackers, s.sides_set = att[0], True
        attacking = [x for x in recent if x[0] == s.attackers]
        if s.sides_set and len(attacking) >= 3:
            # respawns back the phase up only with a clear majority (they lag: a phase change shows only after deaths)
            # (by the p labels; a spawn they say nothing of, by every label: upstream 0.3.0, build 20261118-1714)
            sr = s.inv.get("spawn_res")
            votes = [v for v in ((phase_from_spawns(s.inv, [x]) or (phase_from_spawns(s.inv, [x], sr) if sr else None))
                                 for x in attacking[-8:]) if v is not None]
            best = max(set(votes), key=votes.count, default=None)
            # (never past what the attackers' score says once it reads: live Spire, round 2, the vote said phase 2 with
            # the score 0 and the attackers held phase 2's empty territories for 197 s while phase 1 ran out)
            if best is not None and len(votes) >= 3 and votes.count(best) >= 0.75 * len(votes):
                cap = s.__dict__.get("score_cap")
                s.phase = max(s.phase, best if cap is None else min(best, cap))
        if raw is not None and now - s.core_t > 0.5:
            s.core_t = now
            # the attackers' score is the phases they took this round (live, Boneyard: red 1 right after its
            # territory; the next round started 0-0). The low 16 bits: the next team's cell reads 65536 for 0 counted
            # from the round's start: the score carries over (live: red won round 1 defending, then 0 -> 3 at its
            # first territory in round 2)
            try:                                  # the Elites attack, every round: their team is the attackers when it
                et = live.elite_team(raw) if hasattr(live, "elite_team") else None   # reads (LiveReach.elite_team), the
            except Exception:                     # spawn labels and the score only stand in when it does not
                et = None                         # (upstream 0.3.0, build 20261120-1620)
            s.elite_ok = et is not None
            if et is not None and (et != s.attackers or not s.sides_set):
                s.attackers, s.sides_set = et, True
            try:
                scores = {t: v & 0xFFFF for t, v in live.match_state()["score"].items()}
                s.score_attacker(scores, now)
                sc = scores.get(s.attackers, 0)
                if s.score_base == "first":
                    s.score_base = (s.attackers, 0)
                elif s.score_base is None or s.score_base[0] != s.attackers or sc < s.score_base[1]:
                    s.score_base = (s.attackers, sc)
                taken = sc - s.score_base[1]
                if 0 <= taken <= 2:
                    s.phase, s.score_cap = max(s.phase, 1 + taken), 1 + taken
            except Exception:
                pass
            # the core: its object sits on the stand before phase 3 (live: a weapon 0.5 u off it in phase 2), so it
            # only counts once carried or moved off the stand; in phase 3 its stand is the goal until then
            try:
                # (not before phase 3 where phase 2 is a bomb run: the bomb in a carrier's third slot read as the
                # core carried, the phase as 3, and he ran the bomb to the Phantom; Breakpoint, live)
                c = [] if s.inv.get("bomb") is not None and s.phase < 3 else live.core(raw, s.inv["core"])
            except Exception:
                c = []
            s.core, s.carrier = (Vec(*c[0]["pos"]), c[0]["carrier"]) if c else (None, None)
            if s.core is not None and (s.carrier is not None or (s.core - s.inv["core"]).flat() > 1.5):
                s.phase = 3
        if s.gates and now - s.gates_t > 2.0:     # gates: a barrier while the object stands
            s.gates_t = now
            try:
                here = live.present([b["pos"] for b in s.gates], names=[b.get("name") for b in s.gates])
                # Breakpoint's vault doors (the gates at its bomb's plant markers) are what the bomb blows open: in
                # phase 3 they are open whatever still stands there (live: read closed after the detonation, the
                # attackers' way in went over the vault's roof and they stood 4 u over the core for 250 s)
                bp = s.inv.get("bomb_phase") or 2
                blown = [] if s.phase <= bp or s.inv.get("bomb") is None else [
                    k for k, b in enumerate(s.gates) if any((b["pos"] - q).flat() < 1.5 for q in s.inv["phases"][bp])]
                apply_barriers(s.T, s.inv, {b["key"]: k in here and k not in blown for k, b in enumerate(s.gates)})
                # gates opening = the phase moved on (live, Boneyard: all 9 laser fields went when phase 1 was
                # taken). Two reads in a row, so a flicker is not a phase; 20 s between steps (gate openings no
                # longer count phases: more gates open during a phase, live they read as phase 3 thirty seconds into
                # phase 2; the attackers' score and the core say the phase)
            except Exception:
                pass
        snap.mode = "invasion"
        if (s.phase, s.attackers) != s.__dict__.get("_phase_key"):     # a new phase or round: its clock starts
            s._phase_key, s.phase_since = (s.phase, s.attackers), now
            phase_link_gates(s.T, s.inv, s.phase, s.inv.get("map"))     # (its man cannons, its lifts' landings)
        snap.inv_phase_t = now - s.phase_since
        snap.inv_phase, snap.inv_attackers = s.phase, s.attackers
        snap.inv_zones = list(s.inv["phases"][3 if s.phase == 3 else s.phase])
        snap.inv_zone_r = [zone_radius(s.inv, z) for z in snap.inv_zones]
        snap.inv_delivery = s.inv["phases"][3][0]
        snap.inv_core, snap.inv_core_carrier = (s.core, s.carrier) if s.phase == 3 else (None, None)
        snap.inv_stand = s.inv["core"]
        if s.phase == 3 and s.core is None:       # phase 3 but the core not seen yet: go for its stand
            snap.inv_core = s.inv["core"]
        if s.phase == (s.inv.get("bomb_phase") or 2) and s.inv.get("bomb") is not None:
            # Breakpoint's bomb run, played as phase 3's core run: the attackers take the bomb from its stand to the
            # nearer phase 2 marker and arm it there; the defenders guard the stand, hunt the carrier, hold the marker
            # (live: both rounds stood on the markers for minutes; nothing happens there without the bomb)
            try:
                bm = live.core(raw, s.inv["bomb"], key="bomb")
            except Exception:
                bm = []
            # the bomb, not the core waiting in the vault (the same kind of object: once the armed bomb was gone the
            # first one read was the core, 4 u under the floor, and the attackers chased it 280 s; live): carried,
            # else the one nearest where the bomb was last
            last = getattr(s, "bomb_last", s.inv["bomb"])
            bm = [b for b in bm if b["carrier"] is not None or (Vec(*b["pos"]) - s.inv["core"]).flat() > 2.0]
            b = next((b for b in bm if b["carrier"] is not None), None) or min(
                bm, key=lambda b: (Vec(*b["pos"]) - last).flat(), default=None)
            pos, carrier = (Vec(*b["pos"]), b["carrier"]) if b else (s.inv["bomb"], None)
            s.bomb_last = pos
            plant = min(s.inv["phases"][s.inv.get("bomb_phase") or 2], key=lambda z: (z - pos).flat())
            snap.inv_phase, snap.inv_zones, snap.inv_zone_r = 3, [plant], [zone_radius(s.inv, plant)]
            snap.inv_delivery, snap.inv_core, snap.inv_core_carrier = plant, pos, carrier
            snap.inv_stand = s.inv["bomb"]
            # lying in its plant zone: armed (live: the carrier stood 4.6 s on the marker, then the game took it from
            # his hands); the attackers guard it, the defenders go to disarm it
            snap.inv_armed = carrier is None and (pos - plant).flat() <= zone_radius(s.inv, plant) + 0.5
            snap.inv_bomb = True
            s.carrier = carrier
        for p in snap.players:
            if s.carrier is not None and p.id == s.carrier:
                p.has_flag = True                 # carries the objective: runs, no stopping to fight


def apply_barriers(T, inv, present=None):
    """Put the map's Invasion barriers on terrain T: one-way shields always, solid pieces always (they exist in
    every Invasion game), gates while present (present: {key: bool} from the live game; unknown = closed)."""
    for b in inv["barriers"]:
        on = True if b["kind"] != "gate" else (present or {}).get(b["key"], True)
        T.set_barrier(b["key"], b["a"], b["b"], b["z0"], b["z1"], through=b["through"], on=on)


def clear_barriers(T, inv):
    for b in inv["barriers"]:
        T.set_barrier(b["key"], b["a"], b["b"], b["z0"], b["z1"], through=b["through"], on=False)


# --- where a bot respawns: the player's honor system ("if tier 1 > Spawn river unlocked, Spawn Spire locked, if tier 2
# > Spawn spire unlocked, Elites prefer spire spawn, Spartans prefer River and surrounding area spawn and ally"). A bot
# spawns where a person on its side could: a spawn its side's spawn screen offers this phase, or on a teammate out of
# the fight. botcore moves it there as it spawns (tools/live_bots.py spawn_check, native/reach.cpp hr_spawn_moves)
FOR_VEHICLE_R = 25.0   # a spawn kept for the vehicles by it (River in phases 2-3) is offered with one free this near
ALLY_BEHIND = 1.0      # spawned on a teammate: this far behind him
ALLY_CLEAR_R = 25.0    # ... a teammate is out of the fight with no enemy this near seeing him, shields and health full
SPAWN_CLEAR = 0.8      # a spawn point this near a player, or another bot's pick, is taken


def honor_spawns(map_name):
    """(named spawns, teammate weights {side: weight}) for a map, or None where no spawns are named."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps", map_name, "inv_spawns.json")
    d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    return (d["named"], d.get("ally", {})) if d.get("named") else None


def mate_clear(mate, players, T):
    """A teammate a bot may spawn on: alive, on foot, not carrying the core, unhurt, no enemy within ALLY_CLEAR_R
    seeing him."""
    if not mate.alive or mate.vehicle not in (None, -1) or mate.has_flag or mate.shield < 0.99 or mate.health < 0.99:
        return False
    return not any(p.alive and p.team != mate.team and (p.pos - mate.pos).flat() < ALLY_CLEAR_R and T.los(p.pos, mate.pos)
                   for p in players)


def ally_spot(mate, players, T, taken=()):
    """Where a bot spawning on `mate` appears: ALLY_BEHIND behind him, else behind-left, behind-right, left, right; on
    floor, in his sight (no wall between) and clear of everyone. None if nowhere."""
    for turn in (math.pi, 0.75 * math.pi, -0.75 * math.pi, 0.5 * math.pi, -0.5 * math.pi):
        a = mate.yaw + turn
        p = Vec(mate.pos.x + ALLY_BEHIND * math.cos(a), mate.pos.y + ALLY_BEHIND * math.sin(a), mate.pos.z)
        if (T.ground_ok(p.x, p.y, p.z + 0.4, drop=1.0) and T.los(mate.pos, p)
                and all((q.pos - p).flat() >= SPAWN_CLEAR for q in players if q.alive and q.id != mate.id)
                and all((q - p).flat() >= SPAWN_CLEAR for q in taken)):
            return p
    return None


def spawn_weight(n, phase):
    """A named spawn's weight this phase ("weight": a number, or {phase: number})."""
    w = n["weight"]
    return w.get(str(phase), 0) if isinstance(w, dict) else w


def free_rides(n, phase, vehicles, errands=()):
    """The vehicles a spawn kept for them this phase serves ("for_vehicles": River in phases 2-3): free, drivable, not
    another bot's errand, within FOR_VEHICLE_R of its points. None where the spawn is not kept for vehicles this
    phase."""
    if str(phase) not in n.get("for_vehicles", ()):
        return None
    from .vehicles import spec
    pts = n["points"][str(phase)]
    return [v for v in vehicles if not v.get("occupied") and v["handle"] not in errands
            and (spec(v["kind"]) or {}).get("move", "none") != "none"
            and min(math.dist(v["pos"][:2], p[:2]) for p in pts) <= FOR_VEHICLE_R]


# (upstream 0.3.0, build 20261118-1714) smart Invasion spawns: honor_spawn, spawn_offers, _weighted, _named_point
# and the smart-spawn helpers below are his, replacing upstream s181's honor_spawn (never customized by us);
# the vehicles passed in are already the ones the bot's tier may drive (tools/live_bots.py drivable, #46b)
def honor_spawn(spawns, phase, side, me, players, rng, T, taken=(), goal=None, vehicles=(), errands=(), lanes=(),
                inv_veh=()):
    """Where dead bot `me` respawns: one of its side's offers this phase (a named spawn's free point, or behind a
    teammate out of the fight). side "att" / "def"; taken: points other bots spawn at; lanes: the phase's territories
    (snap.inv_zones, two in phases 1-2); inv_veh: the map's Invasion vehicles (inv_vehicles). A job first: a free
    vehicle of its side waiting at its spot by one of its spawns this phase (one bot each: errands) sends it to that
    spawn for it (Nov 18: back at the earliest spawn to take a vehicle, never for no reason); a spawn kept
    for vehicles ("for_vehicles": River in phases 2-3) is used for that only. Else by weight (spawn_offers) ->
    dict(pos=Vec, yaw=radians, name=str, mate=player id or None, ride=vehicle handle or None), or None."""
    named, ally = spawns
    for n in named:                                   # the job: a vehicle waiting for a driver
        if n["side"] != side or str(phase) not in n["points"] or spawn_weight(n, phase) <= 0:
            continue
        rides = (free_rides(n, phase, vehicles, errands) or []) + waiting_rides(inv_veh, side, phase, vehicles, errands,
                                                                                n["points"][str(phase)])
        if rides:
            return dict(_named_point(n, phase, players, taken, rng, me, T), ride=rides[0]["handle"])
    offers = spawn_offers(spawns, phase, side, me, players, T, taken, goal, lanes)
    if not offers:
        return None
    o = _weighted(offers, rng)
    if "mate" in o:
        return o
    return dict(_named_point(o, phase, players, taken, rng, me, T), ride=None)


def spawn_offers(spawns, phase, side, me, players, T, taken=(), goal=None, lanes=()):
    """[(weight, offer)]: a side's named spawns this phase (offer: the spawn's dict) and teammates to spawn on (offer:
    dict(pos, yaw, name, mate, ride)), weighted (Nov 18: random but smart, split across both lanes;
    Spire phases 2-3: the attackers' Conveyor Belt took 80% of their spawns 31 u from the defenders' High Trail, a
    deathmatch by the spire and nothing on the other side of the map):
      the file's weight, times lane_factor (by the territory short of its share of the team: likelier), times
      ENEMY_SPAWN_W where the other side spawns within ENEMY_SPAWN_R this phase, 0 with a seen enemy within DANGER_R
      of every point; a teammate spawn per lane (the ally weight shared), on the clear mate nearest that lane.
    Every weight 0: the file's weights (never fewer spawns than before). A spawn kept for vehicles is not offered."""
    named, ally = spawns
    me_team = me.team if me is not None else None
    live = [n for n in named if str(phase) in n["points"] and spawn_weight(n, phase) > 0]
    counts = lane_counts(lanes, players, me_team, me)
    offers = []
    for n in live:
        if n["side"] != side or str(phase) in n.get("for_vehicles", ()):
            continue
        pts = [Vec(*p) for p in n["points"][str(phase)]]
        c = _centroid(pts)
        w = spawn_weight(n, phase)
        smart = w * lane_factor(c, lanes, counts)
        if any(o["side"] != side and (_centroid([Vec(*q) for q in o["points"][str(phase)]]) - c).flat() < ENEMY_SPAWN_R
               for o in live):
            smart *= ENEMY_SPAWN_W
        if all(danger(p, players, me_team, T) for p in pts):
            smart = 0.0
        offers.append((smart, w, n))
    mates = [p for p in players if me is not None and p.team == me.team and p.id != me.id and mate_clear(p, players, T)]
    if mates and ally.get(side):
        ways = list(lanes) if len(lanes) >= 2 else [goal]
        used = set()
        for z in ways:
            for mate in sorted(mates, key=lambda p: (p.pos - z).flat() if z is not None else 0.0):
                if mate.id in used:
                    continue
                spot = ally_spot(mate, players, T, taken)
                if spot is not None:
                    used.add(mate.id)
                    w = ally[side] / len(ways)
                    offers.append((w * lane_factor(mate.pos, lanes, counts), w,
                                   dict(pos=spot, yaw=mate.yaw, name=f"ally #{mate.id}", mate=mate.id, ride=None)))
                    break
    if offers and not any(sw > 0 for sw, _, _ in offers):
        return [(w, o) for _, w, o in offers]
    return [(sw, o) for sw, _, o in offers if sw > 0]


def _weighted(offers, rng):
    """One offer of [(weight, offer)], by weight."""
    k = rng.random() * sum(w for w, _ in offers)
    for w, o in offers:
        k -= w
        if k < 0:
            return o
    return offers[-1][1]


def _named_point(n, phase, players, taken, rng, me=None, T=None):
    """A named spawn's point for a dead bot: free (no one on it, no other pick), out of a seen enemy's reach if one is."""
    pts = [Vec(*p) for p in n["points"][str(phase)]]
    free = [p for p in pts if all((q.pos - p).flat() >= SPAWN_CLEAR for q in players if q.alive)
            and all((q - p).flat() >= SPAWN_CLEAR for q in taken)]
    safe = [p for p in free if not danger(p, players, me.team if me is not None else None, T)]
    return dict(pos=rng.choice(safe or free or pts), yaw=math.radians(n["at"][str(phase)][3]), name=n["name"], mate=None)


# --- smart spawns (Nov 18: random but smart, split across both lanes each phase; upstream 0.3.0, build 20261118-1714)
DANGER_R = 15.0          # u: an enemy this near a spawn point, seeing it, rules the point out
ENEMY_SPAWN_R, ENEMY_SPAWN_W = 40.0, 0.25   # a spawn this near the other side's spawn this phase counts this much
LANE_W = 3.0             # a spawn by a territory with none of an even share of the team there: 1 + LANE_W times as likely
LANE_MIN = 0.25          # ... by one with twice its share or more: this much
NEAR_BIAS = 1.5          # labelled zones (label_pick): the one nearest the phase's objective, this many times as likely
RIDE_AT = 6.0            # u: an Invasion vehicle this near its spot is waiting there (not driven off)


def danger(p, players, team, T=None):
    """An enemy alive within DANGER_R of p, seeing it (no wall between; without a nav, any that near)."""
    return any(q.alive and q.team != team and (q.pos - p).flat() < DANGER_R and (T is None or T.los(q.pos, p))
               for q in players)


def lane_counts(lanes, players, team, me=None):
    """Teammates alive by their nearest lane (territory); [] with fewer than two lanes."""
    if len(lanes) < 2:
        return []
    out = [0] * len(lanes)
    for p in players:
        if p.alive and p.team == team and (me is None or p.id != me.id):
            out[min(range(len(lanes)), key=lambda i: (lanes[i] - p.pos).flat())] += 1
    return out


def lane_factor(p, lanes, counts):
    """How much likelier a spawn at p is by its nearest lane's shortfall from an even share of the team: 1 + LANE_W
    with nobody there, 1 at its share, down to LANE_MIN at twice it. 1 with fewer than two lanes."""
    if len(lanes) < 2 or not counts:
        return 1.0
    share = max(1.0, sum(counts) / len(lanes))
    need = (share - counts[min(range(len(lanes)), key=lambda i: (lanes[i] - p).flat())]) / share
    return 1.0 + LANE_W * need if need >= 0 else max(LANE_MIN, 1.0 + need)


def inv_vehicles(map_name):
    """The map's Invasion vehicles (maps/<map>/inv_vehicles.json, tools/inv_vehicles.py): [dict(kind, pos=Vec, side
    "att" / "def" / None, phase)], [] without the file."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps",
                        (map_name or "").split("/")[0].split("@")[0], "inv_vehicles.json")
    if not os.path.exists(path):
        return []
    return [dict(v, pos=_v(v["pos"])) for v in json.load(open(path, encoding="utf-8")).get("vehicles", [])]


def waiting_rides(inv_veh, side, phase, vehicles, errands, near, r=FOR_VEHICLE_R):
    """Live vehicles (snap.vehicles) free for side this phase: at one of its Invasion vehicles' spots (within RIDE_AT;
    spawned by now: its phase at most this one), drivable, empty, not another bot's errand, within r of a point in
    near ([(x, y, z)] or [Vec])."""
    spots = [v["pos"] for v in inv_veh if v.get("side") in (side, None) and v.get("phase", 1) <= phase]
    if not spots or not near:
        return []
    from .vehicles import spec
    near = [(q.x, q.y) if hasattr(q, "x") else (q[0], q[1]) for q in near]
    return [v for v in vehicles if not v.get("occupied") and v["handle"] not in errands
            and (spec(v["kind"]) or {}).get("move", "none") != "none"
            and any(math.hypot(v["pos"][0] - q.x, v["pos"][1] - q.y) <= RIDE_AT for q in spots)
            and min(math.hypot(v["pos"][0] - x, v["pos"][1] - y) for x, y in near) <= r]


def label_pick(inv, phase, attacking, goal, rng, me=None, players=(), T=None, lanes=(), vehicles=(), errands=()):
    """A dead bot's zone on a map with labelled zones and no named spawns (label_spawns), the smart way: a job first (a
    free vehicle of its side waiting by one of its zones this phase or an earlier one: that zone, the earliest spawn
    for it), else one of its side's zones serving this phase (a phase with none: the nearest phase before) by weight:
    NEAR_BIAS for the one nearest the phase's objective `goal`, times lane_factor, 0 with a
    seen enemy within DANGER_R (every weight 0: all alike). -> dict(pos=Vec, ride=handle or None), or None."""
    team = inv["attackers"] if attacking else inv["defenders"]
    zones = (inv.get("spawn_res") or {}).get(team) or {}
    side = "att" if attacking else "def"
    veh = inv.get("vehicles") or ()
    earlier = [q for ph in range(1, phase + 1) for q in zones.get(ph, ())]
    rides = waiting_rides(veh, side, phase, vehicles, errands, earlier) if veh and earlier else []
    if rides:
        v = rides[0]
        return dict(pos=min(earlier, key=lambda q: math.hypot(q.x - v["pos"][0], q.y - v["pos"][1])), ride=v["handle"])
    pool = next((zones[ph] for ph in range(phase, 0, -1) if zones.get(ph)), None)
    if not pool:
        return None
    team_id = me.team if me is not None else None
    counts = lane_counts(lanes, players, team_id, me)
    near = min(pool, key=lambda q: (q - goal).flat()) if goal is not None else None
    ws = [(NEAR_BIAS if q is near else 1.0) * lane_factor(q, lanes, counts) * (0.0 if danger(q, players, team_id, T)
                                                                               else 1.0) for q in pool]
    if not any(ws):
        ws = [1.0] * len(pool)
    return dict(pos=_weighted(list(zip(ws, pool)), rng), ride=None)

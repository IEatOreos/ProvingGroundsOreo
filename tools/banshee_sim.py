"""(custom, Nov 19) Offline Big Team Slayer with a Reach Banshee: the real brain (brain/bot.py Bot, brain/director.py
Director) for every player, no game. Test tool only: it writes nothing into maps/ or the user's data.

The owner's ask (Nov 19): "simulate games ... until a bot gets 20 or more kills in a single 8v8 to 100 slayer game in a
banshee". The upstream test simulator (brain/sim.py) is not in this install, so this is its own small match loop:

- players walk the map's nav (Terrain.can_step / nav_z) at WALK u/s where their throttle points, no jumps;
- hand guns are hitscan along the view with a little spread (GUNS: the DMR's 1.2 s kill from full, brain/odds.py
  REACH_GUNS; shield 70, body 45; a DMR head shot on a broken shield kills), line of sight by Terrain.shot_los;
- one Banshee (Boneyard's, at its pad): it flies where its pilot looks, its nose turning at most TURN rad/s, CRUISE u/s
  at full throttle and BOOST boosted (the owner's own Boneyard flights, trace_reach_70_boneyard_20261115-044159: median
  8.3 u/s, p90 13, turns p90 155 deg/s); its cannons' bolts fly BOLT_SPEED u/s (the brain's lead, PROJECTILE_SPEED's
  plasma_rifle: NOT measured on the Banshee), its bomb is cycled to and flies REACH_BOMB_SPEED with a little drop, one
  every REACH_FUELROD[0] s (the owner's capture); the level stops it (a hit costs body by speed), a kill volume kills it;
- a pilot is not hit through its canopy: rounds on him hit the Banshee (VEH_HP); it dies with its Banshee; it respawns at
  its pad VEH_RESPAWN s after;
- deaths respawn after RESPAWN s at the map's slayer spawn farthest from the enemy (of a random few), shields recharge.

ASSUMED, not measured: the Banshee's body against small arms (VEH_HP), its bolts' damage and speed, the bomb's blast,
the walk speed, no grenades, armour abilities, power weapons, other vehicles. Read its results as the brain's flying
against bots that shoot back with DMRs, not as a Reach match.

usage: python -I banshee_sim.py [--seed 1] [--limit 100] [--minutes 20] [--map reach_70_boneyard] [--tiers demon,...]
                                [--trace out.jsonl] [--quiet]
"""
import argparse
import collections
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import brain.maps  # noqa: E402
brain.maps.PVP = True
from brain import noble as _noble  # noqa: E402
_noble.SAVE = False     # (custom, Nov 22) a simulated match writes nothing to user/noble_*.json: those are live play's
from brain import oob as O  # noqa: E402
from brain import vehicles as V  # noqa: E402
from brain.bot import REACH_BOMB_SPEED, REACH_FUELROD, Bot  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director  # noqa: E402
from brain.maps import get_map, set_mode, terrain  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

HZ = 30
DT = 1.0 / HZ
WALK = 2.3                     # u/s on foot (ASSUMED: the upstream simulator's)
EYE = 0.62
SHIELD, BODY = 70.0, 45.0
SHIELD_DELAY, SHIELD_REFILL = 5.0, 4.0
RESPAWN = 5.0
# gun: seconds between rounds, damage a round, head shots kill an unshielded man, reach u, spread rad (1 sigma)
GUNS = {"dmr": (0.3, 17.5, True, 80.0, 0.008), "assault_rifle": (0.1, 7.5, False, 30.0, 0.035),
        "magnum": (0.3, 15.0, True, 40.0, 0.006)}
BODY_R, BODY_LO, BODY_HI = 0.2, 0.05, 0.6     # a Spartan's hit cylinder over his place
HEAD_R, HEAD_Z = 0.09, 0.66
MELEE_DMG, MELEE_R, MELEE_EVERY = 70.0, 1.2, 1.0
# the Banshee
CRUISE, BOOST, ACCEL, TURN, PITCH_TURN = 8.3, 13.0, 9.0, math.radians(110.0), math.radians(120.0)
BOOST_S, BOOST_REFILL = 4.0, 4.0             # s of boost a full meter holds, s to refill it (ASSUMED)
VEH_R = 1.2                                   # u: its hull for rounds and the level
HULL_HALF = 0.7                               # u: its wing tips off the middle, for the level (ASSUMED: ~4.3 m span)
# ASSUMED, the owner's middle (Nov 20): an empty Banshee takes 38 DMR rounds, "but I think it has thresholds that reset if
# not enough damage is taken. I can't find what those are so. Just average it in the middle": 82 rounds, halfway from
# his 38 to the ~125 (2200) that let the brain's Banshees live about as long as live bot ones (Boneyard 20261107-014245
# / 20261112-215423: bot rides 9-148 s, median ~45; his own 99 and 163 s). At 38 the sim's Normal men downed the Demon
# pilot in 10-30 s
VEH_HP = 82 * GUNS["dmr"][1]
VEH_RESPAWN = 180.0            # s: live Boneyard, a Banshee gone at 215 s back at 396, gone at 166 back at 347
BOLT_SPEED, BOLT_EVERY, BOLT_DMG, BOLT_R, BOLT_SPLASH = 37.0, 0.12, 11.0, 0.35, 0.6
BOMB_DROP, BOMB_KILL_R, BOMB_R, BOMB_DMG = 3.0, 1.8, 4.0, 220.0
GIMBAL = math.radians(15.0)    # ASSUMED: how far off the craft's nose its guns still go to the reticle
SPLAT_SPEED, SPLAT_R = 5.0, 1.1
SOFT_KILL_S = 9.5             # s: live Spire, pilots over the soft roof died 9-10 s later (brain/terrain.py air_roof)
BANSHEE_PAD = {"reach_70_boneyard": (Vec(295.7, 100.4, -5.0), 0.0)}
DEFAULT_TIERS = "demon,top,top,strong,strong,average,average,blind"
STYLES = ("rusher", "flanker", "camper", "grudger", "spammer", "objector", "flanker", "rusher")


def nose(yaw, pitch):
    c = math.cos(pitch)
    return Vec(math.cos(yaw) * c, math.sin(yaw) * c, math.sin(pitch))


def wrap(a):
    return math.remainder(a, 2 * math.pi)


def seg_point_dist(a, d, length, p):
    """Closest distance from point p to the segment a + d * t, t in [0, length] (d a unit vector), and that t."""
    w = p - a
    t = max(0.0, min(length, w.x * d.x + w.y * d.y + w.z * d.z))
    q = a + d * t
    return (p - q).length(), t


class Man:
    def __init__(s, pid, team, name, tier):
        s.id, s.team, s.name, s.tier = pid, team, name, tier
        s.pos, s.vel, s.yaw, s.pitch = Vec(), Vec(), 0.0, 0.0
        s.alive, s.respawn_at = False, 0.0
        s.shield, s.body, s.hit_at = SHIELD, BODY, -99.0
        s.weapon, s.weapons, s.next_shot, s.next_melee = "dmr", ["dmr", "assault_rifle"], 0.0, 0.0
        s.vehicle = -1
        s.last_by = None              # (killer id, his Banshee?) of the last damage
        s.kills = s.deaths = s.veh_kills = 0
        s.action_was = False
        s.crouch = False

    def state(s, veh):
        pos = veh.pos if s.vehicle != -1 and veh is not None else s.pos
        vel = veh.vel if s.vehicle != -1 and veh is not None else s.vel
        return PlayerState(s.id, s.team, s.name, pos, vel, s.yaw, s.pitch, s.alive, s.shield / SHIELD,
                           max(0.0, s.body) / BODY, s.weapon, list(s.weapons), [], [], s.vehicle, crouching=s.crouch,
                           is_bot=True)


class Banshee:
    def __init__(s, handle, pos, yaw):
        s.handle, s.pad, s.pad_yaw = handle, pos, yaw
        s.pos, s.vel, s.yaw, s.pitch = pos, Vec(), yaw, 0.0
        s.hp, s.alive, s.respawn_at, s.driver = VEH_HP, True, 0.0, None
        s.bomb_sel, s.bomb_at, s.bolt_at, s.cycle_was = False, 0.0, 0.0, False
        s.boost = BOOST_S
        s.soft = 0.0
        s.entered = 0.0

    def row(s, men):
        d = men.get(s.driver) if s.driver is not None else None
        n = nose(s.yaw, s.pitch)
        return dict(handle=s.handle, kind="banshee", pos=(s.pos.x, s.pos.y, s.pos.z), occupied=d is not None,
                    riders=1 if d is not None else 0, team=d.team if d is not None else -1,
                    fwd=(n.x, n.y, n.z), up=(0.0, 0.0, 1.0), turrets=[], manned=[],
                    left=round(s.hp / VEH_HP, 3), dead=False, vel=(s.vel.x, s.vel.y, s.vel.z))


class Shot:
    __slots__ = ("kind", "pos", "vel", "owner", "team", "born")

    def __init__(s, kind, pos, vel, owner, team, born):
        s.kind, s.pos, s.vel, s.owner, s.team, s.born = kind, pos, vel, owner, team, born


class Match:
    def __init__(s, map_name="reach_70_boneyard", seed=1, tiers=DEFAULT_TIERS, limit=100, per_team=8, trace=None,
                 quiet=False, pilot=None, red_tiers=None, seat_team=None):
        s.rng = random.Random(seed)
        s.pilot = pilot              # drill: this player is seated in the Banshee whenever it stands free and he lives
        # (the owner, Nov 19: "make the bots on one team all demons. And they will gurantee to get one") seat_team: a
        # living man of that team is seated whenever the Banshee stands free, its last pilot first; red_tiers: team 0's
        s.seat_team, s.last_pilot = seat_team, None
        s.M = get_map(map_name)
        set_mode(s.M, "slayer")
        s.T = terrain(s.M)
        s.vols = O.volumes(map_name) or []
        s.T.set_oob([], 0, s.vols)
        s.spawns = {t: list(s.M["spawns"]["slayer"][t]) for t in (0, 1)}
        s.limit, s.quiet = limit, quiet
        s.now = 0.0
        s.men, s.bots = {}, {}
        pid = 0
        for team in (0, 1):
            tl = (red_tiers if team == 0 and red_tiers else tiers).split(",")
            for k in range(per_team):
                pid += 1
                tier = tl[k % len(tl)]
                style = STYLES[k % len(STYLES)]
                m = Man(pid, team, f"{tier[:3]}{'RB'[team]}{k}", tier)
                s.men[pid] = m
                b = Bot(pid, team, make_profile(tier, style, random.Random(seed * 100 + pid)), s.M,
                        random.Random(seed * 1000 + pid))
                b.game_team = team
                b.can_pickup = False
                b.can_melee = True
                b.can_cycle = True
                b.kit.pressable = False
                b.kit.sprint_ok = False
                b.kit.decoys_listed = False
                s.bots[pid] = b
        s.directors = {t: Director(t, s.M, {i: b for i, b in s.bots.items() if s.men[i].team == t},
                                   random.Random(seed + t), log=[], side=t, home_rule=True) for t in (0, 1)}
        # (a variant, "<base>/variants/<id>": its base map's pad; the Banshee is the base scenario's, not a Forge piece)
        pad, yaw = BANSHEE_PAD.get(map_name) or BANSHEE_PAD.get(map_name.replace("\\", "/").partition("/")[0], (None, 0.0))
        s.veh = Banshee(0x5A000001, pad, yaw) if pad is not None else None
        s.shots = []
        s.score = {0: 0, 1: 0}
        s.events = []                # (t, killer, victim, how)
        s.rides = []                 # [driver, t in, t out, kills]
        s.trace = open(trace, "w") if trace else None
        s.stats = collections.Counter()
        s.oob_time, s.oob_deaths = {}, []      # seconds the Banshee spent out of bounds, by volume; where it died of it
        s.exits = []                           # (t, x, y, z, height over the floor, notes) of each pilot's get-out
        for m in s.men.values():
            s.spawn(m, first=True)

    # --- spawning ---------------------------------------------------------------------------------------------------
    def spawn(s, m, first=False):
        pts = s.spawns[m.team]
        foes = [o.pos for o in s.men.values() if o.alive and o.team != m.team]
        if first:
            base = s.M["flags"][m.team]
            cand = sorted(pts, key=lambda p: (p - base).flat())[:12]
            p = s.rng.choice(cand)
        else:
            cand = s.rng.sample(pts, min(8, len(pts)))
            p = max(cand, key=lambda q: min(((q - f).flat() for f in foes), default=99.0))
        m.pos = Vec(p.x, p.y, s.T.nav_z(p.x, p.y, p.z))
        m.vel, m.alive, m.shield, m.body, m.vehicle = Vec(), True, SHIELD, BODY, -1
        m.weapon, m.next_shot, m.last_by = "dmr", s.now + 0.5, None
        mid = Vec(280.0, 96.0, m.pos.z)
        m.yaw, m.pitch = math.atan2(mid.y - m.pos.y, mid.x - m.pos.x), 0.0

    # --- the world each bot sees ------------------------------------------------------------------------------------
    def snapshot(s):
        v = s.veh if s.veh is not None and s.veh.alive else None
        players = [m.state(v) for m in s.men.values()]
        return Snapshot(s.now, players, score=dict(s.score), mode="slayer", score_limit=s.limit, score_live=True,
                        vehicles=[v.row(s.men)] if v is not None else [])

    # --- damage -----------------------------------------------------------------------------------------------------
    def hurt(s, m, dmg, by, head=False, veh_shot=False, how="gun"):
        if not m.alive:
            return
        killer = s.men.get(by)
        if m.vehicle != -1 and s.veh is not None and s.veh.alive:
            s.veh_hurt(dmg, by, veh_shot, how)
            return
        m.hit_at = s.now
        m.last_by = (by, veh_shot)
        if m.shield > 0:
            m.shield -= dmg
            if m.shield < 0:
                m.body += m.shield
                m.shield = 0.0
        else:
            if head:
                m.body = -1.0
            m.body -= dmg
        if m.body <= 0:
            s.kill(m, killer, veh_shot, how)

    def veh_hurt(s, dmg, by, veh_shot=False, how="gun"):
        v = s.veh
        v.hp -= dmg
        if by is not None:
            v.last_by = (by, veh_shot)
        if v.hp <= 0:
            s.veh_destroyed(how)

    def veh_destroyed(s, how):
        v = s.veh
        v.alive, v.respawn_at = False, s.now + VEH_RESPAWN
        lb = getattr(v, "last_by", None)
        d = s.men.get(v.driver) if v.driver is not None else None
        s.stats["banshee_destroyed_" + how] += 1
        if d is not None:
            s.leave(d)
            d.vehicle = -1
            killer = s.men.get(lb[0]) if lb else None
            s.kill(d, killer if killer is not None and killer.team != d.team else None, lb[1] if lb else False,
                   "banshee_" + how)

    def kill(s, m, killer, veh_shot, how):
        if not m.alive:
            return
        if m.vehicle != -1:
            s.leave(m)
        m.alive, m.respawn_at, m.deaths = False, s.now + RESPAWN, m.deaths + 1
        m.vehicle = -1
        if killer is not None and killer.team != m.team:
            killer.kills += 1
            s.score[killer.team] += 1
            if veh_shot:
                killer.veh_kills += 1
                if s.rides and s.rides[-1][0] == killer.id and s.rides[-1][2] is None:
                    s.rides[-1][3] += 1
        elif killer is None:
            s.score[m.team] = max(0, s.score[m.team] - 1) if how in ("fall", "oob", "crash") else s.score[m.team]
        s.events.append((round(s.now, 2), killer.id if killer else None, m.id, how + ("/veh" if veh_shot else "")))
        d = s.directors[m.team]
        b = s.bots[m.id]
        if killer is not None:
            d.report(s.now, m.id, "died", killer.pos if killer.vehicle == -1 else s.veh.pos, enemy=killer.id,
                     killer_weak=killer.shield <= 0, died_at=m.pos)
        b.on_death(killer.id if killer is not None else None)

    # --- vehicles ---------------------------------------------------------------------------------------------------
    def enter(s, m):
        v = s.veh
        v.driver, m.vehicle, v.entered = m.id, v.handle, s.now
        v.bomb_sel = False
        s.rides.append([m.id, round(s.now, 1), None, 0])

    def leave(s, m):
        v = s.veh
        if v is not None and v.driver == m.id:
            v.driver = None
            if s.rides and s.rides[-1][0] == m.id and s.rides[-1][2] is None:
                s.rides[-1][2] = round(s.now, 1)
            if v.alive:
                m.pos = Vec(v.pos.x, v.pos.y, s.T.nav_z(v.pos.x, v.pos.y, v.pos.z))
        m.vehicle = -1

    def fly(s, m, a):
        """The Banshee under its pilot's action a this tick."""
        v = s.veh
        want_yaw, want_pitch = a.yaw, max(-1.2, min(1.2, a.pitch))
        dy = wrap(want_yaw - v.yaw)
        sp0 = v.vel.length()
        # its turn by its speed (the owner's Reach Banshee, brain/bot.py AIR_TIGHT_TURN: 105 deg/s pulled back, 66 at full
        # throttle, 32 boosted; TURN at a hover)
        turn = (TURN if sp0 <= 3.0 else
                TURN + (math.radians(66.0) - TURN) * (sp0 - 3.0) / (CRUISE - 3.0) if sp0 <= CRUISE else
                max(math.radians(32.0), math.radians(66.0) - math.radians(34.0) * (sp0 - CRUISE) / (BOOST - CRUISE)))
        v.yaw = wrap(v.yaw + max(-turn * DT, min(turn * DT, dy)))
        v.pitch += max(-PITCH_TURN * DT, min(PITCH_TURN * DT, want_pitch - v.pitch))
        m.yaw, m.pitch = a.yaw, a.pitch
        boosting = bool(a.fire2) and v.boost > 0.0 and a.forward > 0.2
        v.boost = max(0.0, v.boost - DT) if boosting else min(BOOST_S, v.boost + DT * BOOST_S / BOOST_REFILL)
        top = BOOST if boosting else CRUISE
        n = nose(v.yaw, v.pitch)
        side = Vec(-math.sin(v.yaw), math.cos(v.yaw), 0.0)
        # the throttle along the nose's heading; its height where the nose points whichever way the throttle goes (live
        # Reach bot pilots, Boneyard 20261115-195851: reverse with the nose down sank, median -0.6 u/s; with it up rose)
        f = max(-0.4, min(1.0, a.forward))
        flat = Vec(math.cos(v.yaw), math.sin(v.yaw), 0.0) * (f * top * math.cos(v.pitch))
        target = flat + Vec(0.0, 0.0, abs(f) * top * math.sin(v.pitch)) + side * (max(-1.0, min(1.0, a.strafe)) * CRUISE * 0.5)
        dv = target - v.vel
        k = min(1.0, (ACCEL * (2.0 if boosting else 1.0)) * DT / max(dv.length(), 1e-6))
        v.vel = v.vel + dv * k
        step = v.vel * DT
        sp = v.vel.length()

        def blocked(st):
            if st.length() < 1e-6:
                return False
            yaw, pitch = math.atan2(st.y, st.x), math.atan2(st.z, max(1e-6, st.flat()))
            # (the hull's middle and its wing tips, HULL_HALF to the sides: a point slipped into walled pockets the
            # brain's wall grid reads solid, Boneyard 267, 85, and sat there 200 s)
            return any(s.T.aim_hit(v.pos + side * k, yaw, pitch, reach=st.length() + 0.3) is not None
                       for k in (0.0, -HULL_HALF, HULL_HALF))
        if sp > 1e-3 and blocked(step):
            # the level in the way: it slides along it (the flat part, else the up / down part), a hard hit costs body
            s.stats["veh_bumps"] += 1
            flat_st, up_st = Vec(step.x, step.y, 0.0), Vec(0.0, 0.0, step.z)
            if not blocked(flat_st):
                step, v.vel = flat_st, Vec(v.vel.x, v.vel.y, 0.0)
            elif not blocked(up_st):
                step, v.vel = up_st, Vec(0.0, 0.0, v.vel.z)
            else:
                if sp > 4.0:
                    s.veh_hurt((sp - 4.0) * 25.0, None, how="crash")
                    if not v.alive:
                        return
                v.vel = v.vel * -0.2
                step = Vec()
        p = v.pos + step
        floor = p.z - s.T.height_over(p.x, p.y, p.z)
        if p.z < floor + 0.6:
            s.stats["veh_floor"] += 1
            p = Vec(p.x, p.y, floor + 0.6)
            v.vel = Vec(v.vel.x, v.vel.y, max(0.0, v.vel.z))   # (slides on: only the way down is stopped)
        v.pos = p
        where = O.where(s.vols, (p.x, p.y, p.z)) if s.vols else None
        if where is not None and where["kind"] == "hard":
            s.stats["veh_oob_hard"] += 1
            s.veh_hurt(VEH_HP * 2, None, how="oob")
            return
        if where is not None:
            v.soft += DT
            lab = where.get("label", "?")
            s.oob_time[lab] = s.oob_time.get(lab, 0.0) + DT
            if v.soft > SOFT_KILL_S:
                s.stats["veh_oob_soft"] += 1
                s.oob_deaths.append((round(s.now, 1), lab, round(p.x, 1), round(p.y, 1), round(p.z, 1)))
                s.veh_hurt(VEH_HP * 2, None, how="oob")
                return
        else:
            v.soft = 0.0
        # weapons: the cycle swaps cannons / bomb (a press), the trigger fires the one selected
        if a.cycle and not v.cycle_was:
            v.bomb_sel = not v.bomb_sel
            s.stats["cycles"] += 1
        v.cycle_was = bool(a.cycle)
        if a.fire:
            # ASSUMED: its guns go toward the reticle (the view) within GIMBAL of the craft's nose, as fixed vehicle guns
            # aim at the crosshair's point; past that, along the nose
            gy = v.yaw + max(-GIMBAL, min(GIMBAL, wrap(a.yaw - v.yaw)))
            gp = v.pitch + max(-GIMBAL, min(GIMBAL, a.pitch - v.pitch))
            n = nose(gy, gp)
            muzzle = v.pos + n * (VEH_R + 0.3)
            if v.bomb_sel:
                if s.now >= v.bomb_at:
                    v.bomb_at = s.now + REACH_FUELROD[0] - 0.14
                    s.shots.append(Shot("bomb", muzzle, n * REACH_BOMB_SPEED, m.id, m.team, s.now))
                    s.stats["bombs"] += 1
                else:
                    s.stats["bomb_not_ready"] += 1
            elif s.now >= v.bolt_at:
                v.bolt_at = s.now + BOLT_EVERY
                s.shots.append(Shot("bolt", muzzle, n * BOLT_SPEED, m.id, m.team, s.now))
                s.stats["bolts"] += 1
        # a man in its way at speed is run down
        if sp > SPLAT_SPEED:
            for o in s.men.values():
                if o.alive and o.vehicle == -1 and o.team != m.team and (o.pos + Vec(0, 0, 0.35) - v.pos).length() < SPLAT_R:
                    s.hurt(o, 500.0, m.id, veh_shot=True, how="splatter")

    # --- shots ------------------------------------------------------------------------------------------------------
    def fire_gun(s, m, a):
        g = GUNS.get(m.weapon, GUNS["dmr"])
        if s.now < m.next_shot:
            return
        m.next_shot = s.now + g[0]
        s.stats["rounds"] += 1
        eye = m.pos + Vec(0, 0, EYE)
        yaw = a.yaw + s.rng.gauss(0.0, g[4])
        pitch = a.pitch + s.rng.gauss(0.0, g[4])
        d = nose(yaw, pitch)
        wall = s.T.aim_hit(eye, yaw, pitch, reach=g[3])
        reach = (wall - eye).length() if wall is not None else g[3]
        best = None
        for o in s.men.values():
            if not o.alive or o.team == m.team:
                continue
            if o.vehicle != -1 and s.veh is not None and s.veh.alive:
                r, t = seg_point_dist(eye, d, reach, s.veh.pos)
                if r < VEH_R and (best is None or t < best[0]):
                    best = (t, o, False)
                continue
            mid = o.pos + Vec(0, 0, (BODY_LO + BODY_HI) / 2)
            r, t = seg_point_dist(eye, d, reach, mid)
            if r > 0.6:
                continue
            q = eye + d * t
            dz = q.z - o.pos.z
            flat = math.hypot(q.x - o.pos.x, q.y - o.pos.y)
            hr, _ = seg_point_dist(eye, d, reach, o.pos + Vec(0, 0, HEAD_Z))
            head = hr < HEAD_R
            body = flat < BODY_R and BODY_LO <= dz <= BODY_HI
            if (head or body) and (best is None or t < best[0]):
                best = (t, o, head)
        if best is not None:
            t, o, head = best
            s.stats["hits"] += 1
            s.hurt(o, g[1], m.id, head=head and g[2])

    def melee(s, m, a):
        if s.now < m.next_melee:
            return
        m.next_melee = s.now + MELEE_EVERY
        for o in s.men.values():
            if o.alive and o.team != m.team and o.vehicle == -1 and (o.pos - m.pos).length() < MELEE_R:
                ang = abs(wrap(math.atan2(o.pos.y - m.pos.y, o.pos.x - m.pos.x) - a.yaw))
                if ang < 0.6:
                    s.hurt(o, MELEE_DMG if o.shield > 0 else BODY + 1, m.id, how="melee")
                    return

    def step_shots(s):
        keep = []
        for sh in s.shots:
            if sh.kind == "bomb":
                sh.vel = sh.vel + Vec(0, 0, -BOMB_DROP * DT)
            step = sh.vel * DT
            ln = step.length()
            d = step * (1.0 / max(ln, 1e-9))
            boom = None
            for o in s.men.values():
                if not o.alive or o.team == sh.team or o.vehicle != -1:
                    continue
                r, t = seg_point_dist(sh.pos, d, ln, o.pos + Vec(0, 0, 0.35))
                if r < (BOLT_R if sh.kind == "bolt" else 0.5):
                    boom = sh.pos + d * t
                    break
            if boom is None:
                wall = s.T.aim_hit(sh.pos, math.atan2(d.y, d.x), math.atan2(d.z, max(1e-9, d.flat())), reach=ln)
                if wall is not None:
                    boom = wall
            if boom is None and s.now - sh.born > (60.0 / BOLT_SPEED if sh.kind == "bolt" else 4.0):
                continue
            if boom is None:
                sh.pos = sh.pos + step
                keep.append(sh)
                continue
            s.explode(sh, boom)
        s.shots = keep

    def explode(s, sh, at):
        r_kill, r_max, dmg = (BOLT_R, BOLT_SPLASH, BOLT_DMG) if sh.kind == "bolt" else (BOMB_KILL_R, BOMB_R, BOMB_DMG)
        for o in s.men.values():
            if not o.alive or o.vehicle != -1 or o.team == sh.team:
                continue
            q = o.pos + Vec(0, 0, 0.35)
            d = (q - at).length()
            if d > r_max:
                continue
            if d > 0.5 and not s.T.shot_los(at + Vec(0, 0, 0.2), q):
                continue
            f = 1.0 if d <= r_kill else max(0.0, 1.0 - (d - r_kill) / max(1e-6, r_max - r_kill))
            if sh.kind == "bolt" and d > BOLT_R:
                f *= 0.5
            if f > 0:
                s.stats[sh.kind + "_hits"] += 1
                s.hurt(o, dmg * f, sh.owner, veh_shot=True, how=sh.kind)

    # --- the tick ---------------------------------------------------------------------------------------------------
    def tick(s):
        s.now += DT
        v = s.veh
        if v is not None and not v.alive and s.now >= v.respawn_at:
            s.veh = Banshee(v.handle + 1, v.pad, v.pad_yaw)
            v = s.veh
        if (s.pilot is not None and v is not None and v.alive and v.driver is None and s.men[s.pilot].alive
                and s.men[s.pilot].vehicle == -1 and s.now - getattr(v, "free_since", s.now) >= 0.0):
            s.enter(s.men[s.pilot])
        if s.seat_team is not None and v is not None and v.alive and v.driver is None:
            crew = [m for m in s.men.values() if m.team == s.seat_team and m.alive and m.vehicle == -1]
            if crew:
                m = next((c for c in crew if c.id == s.last_pilot), None) or min(crew, key=lambda c: c.id)
                s.last_pilot = m.id
                s.enter(m)
        for m in s.men.values():
            if not m.alive and s.now >= m.respawn_at:
                s.spawn(m)
            if m.alive and m.vehicle == -1 and s.now - m.hit_at > SHIELD_DELAY:
                m.shield = min(SHIELD, m.shield + SHIELD * DT / SHIELD_REFILL)
                if m.shield > 0:
                    m.body = min(BODY, m.body + BODY * DT / SHIELD_REFILL)
        snap = s.snapshot()
        for d in s.directors.values():
            d.update(s.now, snap)
        acts = {}
        order = list(s.men)
        s.rng.shuffle(order)
        for pid in order:
            m = s.men[pid]
            if not m.alive:
                continue
            b, d = s.bots[pid], s.directors[m.team]
            a = b.think(s.now, DT, snap, s.T.sees, s.T.nav, d.callouts, d.item_up)
            for kind, eid, pos, t, busy in b.reports:
                d.report(t, pid, kind, pos, enemy=eid, busy=busy)
            b.reports.clear()
            acts[pid] = a
        for pid, a in acts.items():
            m = s.men[pid]
            if not m.alive:
                continue
            pressed = bool(a.action) and not m.action_was
            m.action_was = bool(a.action)
            if m.vehicle != -1 and v is not None and v.alive and v.driver == pid:
                if pressed and s.now - v.entered > 1.0:
                    s.stats["exits"] += 1
                    s.exits.append((round(s.now, 1), round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1),
                                    round(s.T.height_over(v.pos.x, v.pos.y, v.pos.z), 1), s.bots[pid].notes[:3]))
                    s.leave(m)
                    continue
                s.fly(m, a)
                b = s.bots[pid]
                if s.trace and int(s.now * HZ) % 3 == 0:
                    s.trace.write(json.dumps(dict(t=round(s.now, 2), id=pid, pos=[round(c, 2) for c in (v.pos.x, v.pos.y, v.pos.z)],
                                                  cmd=[round(a.forward, 2), round(a.strafe, 2), round(a.yaw, 3),
                                                       int(a.fire) | (int(a.fire2) << 21) | (int(a.cycle) << 22),
                                                       round(a.pitch, 3)],
                                                  att=b.att, notes=b.notes, veh=v.handle, seat="driver",
                                                  goal=b.goal[0], hp=round(v.hp), bomb=int(v.bomb_sel),
                                                  spd=round(v.vel.length(), 1))) + "\n")
                continue
            if (pressed and v is not None and v.alive and v.driver is None and m.vehicle == -1
                    and (m.pos - v.pos).length() < 2.4):
                s.enter(m)
                continue
            s.walk(m, a)
            if a.fire:
                s.fire_gun(m, a)
            if a.melee:
                s.melee(m, a)
            if 0 <= a.weapon < len(m.weapons):
                m.weapon = m.weapons[a.weapon]
        if s.veh is not None and s.veh.alive and s.veh.driver is not None and s.veh.driver not in acts:
            s.veh.driver = None
        s.step_shots()
        if s.trace and int(s.now * HZ) % 8 == 0:
            vv = s.veh
            s.trace.write(json.dumps(dict(t=round(s.now, 2), score=s.score, world=[
                [m.id, m.team, int(m.alive), round((vv.pos if m.vehicle != -1 else m.pos).x, 2),
                 round((vv.pos if m.vehicle != -1 else m.pos).y, 2), round((vv.pos if m.vehicle != -1 else m.pos).z, 2),
                 0, 0, 0, 0, round(m.yaw, 3)] for m in s.men.values()],
                vehicles=[[vv.handle, "banshee", round(vv.pos.x, 2), round(vv.pos.y, 2), round(vv.pos.z, 2),
                           int(vv.driver is not None), -1, 1.0, round(vv.hp / VEH_HP, 2), 0]]
                if vv is not None and vv.alive else [])) + "\n")

    def walk(s, m, a):
        m.yaw, m.pitch = a.yaw, a.pitch
        m.crouch = bool(a.crouch)
        f, st = max(-1.0, min(1.0, a.forward)), max(-1.0, min(1.0, a.strafe))
        mag = math.hypot(f, st)
        if mag > 1.0:
            f, st = f / mag, st / mag
        sp = WALK * (0.5 if m.crouch else 1.0)
        c, sn = math.cos(a.yaw), math.sin(a.yaw)
        mv = Vec((c * f - sn * st) * sp * DT, (sn * f + c * st) * sp * DT, 0.0)
        if mv.flat() < 1e-6:
            m.vel = Vec()
            return
        p0 = m.pos
        for cand in (mv, Vec(mv.x, 0.0, 0.0), Vec(0.0, mv.y, 0.0)):
            q = Vec(p0.x + cand.x, p0.y + cand.y, p0.z)
            if s.T.can_step(p0, q):
                m.pos = Vec(q.x, q.y, s.T.nav_z(q.x, q.y, p0.z))
                break
        m.vel = (m.pos - p0) * HZ

    def over(s):
        return max(s.score.values()) >= s.limit

    def run(s, minutes=20.0, report_every=60.0):
        t0, nxt = time.time(), report_every
        while not s.over() and s.now < minutes * 60.0:
            s.tick()
            if not s.quiet and s.now >= nxt:
                nxt += report_every
                top = max(s.men.values(), key=lambda m: m.veh_kills)
                print(f"{s.now:6.0f}s score {s.score[0]}-{s.score[1]}  banshee kills: best {top.name} {top.veh_kills}  "
                      f"rides {len(s.rides)}  real {time.time() - t0:.0f}s", flush=True)
        if s.trace:
            s.trace.close()
        return s.result(time.time() - t0)

    def result(s, real):
        best = max(s.men.values(), key=lambda m: m.veh_kills)
        return dict(t=round(s.now, 1), score=dict(s.score), real_s=round(real, 1),
                    best=dict(name=best.name, id=best.id, tier=best.tier, banshee_kills=best.veh_kills,
                              kills=best.kills, deaths=best.deaths),
                    banshee_kills={m.name: m.veh_kills for m in s.men.values() if m.veh_kills},
                    rides=[r for r in s.rides], stats=dict(s.stats), events=s.events,
                    oob_time={k: round(v, 1) for k, v in s.oob_time.items()}, oob_deaths=s.oob_deaths, exits=s.exits,
                    kd={m.name: (m.kills, m.deaths) for m in s.men.values()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--minutes", type=float, default=20.0)
    ap.add_argument("--map", default="reach_70_boneyard")
    ap.add_argument("--tiers", default=DEFAULT_TIERS)
    ap.add_argument("--trace")
    ap.add_argument("--json")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--pilot", type=int, help="drill: seat this player in the Banshee whenever it stands free")
    ap.add_argument("--veh-respawn", type=float, help="the Banshee's respawn, s (drills: more rides a run)")
    ap.add_argument("--red-tiers", help="team 0's tiers (e.g. demon,demon,...), the rest --tiers")
    ap.add_argument("--seat-team", type=int, help="seat a man of this team whenever the Banshee stands free")
    o = ap.parse_args()
    global VEH_RESPAWN
    if o.veh_respawn is not None:
        VEH_RESPAWN = o.veh_respawn
    m = Match(o.map, o.seed, o.tiers, o.limit, trace=o.trace, quiet=o.quiet, pilot=o.pilot, red_tiers=o.red_tiers,
              seat_team=o.seat_team)
    r = m.run(o.minutes)
    print(json.dumps(r, indent=1))
    if o.json:
        with open(o.json, "w") as f:
            json.dump(r, f, indent=1)


if __name__ == "__main__":
    main()

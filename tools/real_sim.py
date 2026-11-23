"""(custom, Nov 23) Offline Reach Slayer by the real game's rules, for the owner's 50-20 goal ("I want you to continuously
run simulations until 4 nobles can beat 4 demons 50-20. asylum with no weapons on the map", "Follow the real games
rules", "All of it"). The real brain (brain/bot.py Bot, brain/director.py Director) plays every player; no game.
Test tool only: it writes nothing into maps/ or the user's data (banshee_sim sets noble.SAVE False).

It is tools/banshee_sim.py's match (its walking, guns, shields, spawns, the game's read delays) plus the rules the owner's
real Asylum Slayer games have (live trace_reach_forge_halo_20261123-000210: Slayer to 50, 12 minutes, every spawn a DMR
and an assault rifle, frag grenades, jumps, the armor abilities sprint, jetpack, armor lock, active camo and hologram)
and no weapons on the map (no pickups; banshee_sim's Banshee is only on Boneyard).

MEASURED, reused:
- each armor ability's meter: Reach's own tags (brain/equipment_tags.json through brain/equipment.Energy, the bot's own
  model of it): its activation cost, drain while on, refill, minimum to start, recovery time, warmup;
- how each ability takes its button (brain/equipment.use_of / hold_bit: hold-mode kinds need act.ability as live);
- a jump: Reach's take-off speed and gravity (tools/jumpphys.py PHYS, fitted to live arcs), the air step (air_step);
- a frag's throw: its launch speed, gravity, the launch's offset off the view and the press-to-release delay (brain/
  nade.model("reach"), fitted to 60 of the bots' own live throws in user/grenade_flights.json);
- the jetpack's lift (brain/equipment.JET_BRAKE, the owner's collector: 1.4 u/s^2 over gravity) and its sideways speed
  (JET_FLY).
ASSUMED, not measured (marked below): the frag's fuse, blast and bounce; sprint's speed; the most a jetpack climbs at;
camo's drain while moving and its reveal on a shot; the throw's cooldown. Holograms do nothing to bots: live, the
readers list players only, so a bot never sees one (brain/equipment.Kit.decoys_listed is False live and here).

usage: python -I real_sim.py [--seeds 1,2,3] [--red-tiers noble] [--tiers demon] [--per-team 4] [--limit 50]
                             [--minutes 12] [--map reach_forge_halo/variants/v8e4a8930] [--json out.json] [--no-delay]
"""
import argparse
import dataclasses
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import banshee_sim as BS  # noqa: E402
import jumpphys as JP  # noqa: E402
from brain import equipment as EQ  # noqa: E402
from brain import loadouts as LO  # noqa: E402
from brain import nade as NADE  # noqa: E402
from brain.core import Vec  # noqa: E402

ASYLUM = "reach_forge_halo/variants/v8e4a8930"
GAME = "reach"
LIMIT, TIME_LIMIT = 50, 720.0         # live: Slayer to 50, 694 s left at the brain's start (a 12-minute match)
ABILITIES = ("sprint", "jetpack", "armor_lock", "active_camo", "hologram")   # live Asylum's five loadouts, DMR + AR each
FRAGS = 2                             # frag grenades a spawn carries (Reach's default; live: frags thrown all match)
_M = NADE.model(GAME) or dict(speed=10.0, gravity=3.7, pitch_off=0.02, yaw_off=-0.01, delay=0.27)
NADE_SPEED, NADE_G = _M["speed"], _M["gravity"]
NADE_PITCH_OFF, NADE_YAW_OFF, NADE_DELAY = _M["pitch_off"], _M["yaw_off"], _M["delay"]
NADE_EVERY = 1.0                      # s between throws (ASSUMED: the throw's animation)
FUSE_BOUNCE, FUSE_MAX = 1.2, 3.0      # s after its first bounce it goes off; at most this long after the throw (ASSUMED)
FRAG_DMG, FRAG_KILL_R, FRAG_R = 130.0, 1.0, EQ.NADE_BLAST   # full damage within KILL_R (a full Spartan's 115), none at
                                                            # NADE_BLAST (ASSUMED; the brain's own blast reach)
BOUNCE_UP, BOUNCE_KEEP, WALL_KEEP = 0.3, 0.6, 0.4           # a bounce's kept speeds: up, along the floor, off a wall (ASSUMED)
SPRINT = 3.5                          # u/s (ASSUMED: brain/equipment.LONG_WALK's note, Reach's 4 s sprint about 14 u)
JET_NET, JET_VZ_MAX = EQ.JET_BRAKE, 1.6   # lift over gravity (measured); its climb speed cap (ASSUMED: 5.3 u in 3.9 s)
CAMO_DRAIN_RUN = 0.25                 # camo meter a second at a run, less walking, none still (ASSUMED)
CAMO_SHOT_REVEAL, CAMO_SHOT_COST = 0.5, 0.05   # s seen after a shot from camo, meter a shot (ASSUMED)
PHYS = JP.Phys(GAME)


def clear(T, a, b):
    """A frag's step from a to b is open: the line check the bots' throws are planned with (Terrain.point_los)."""
    try:
        return bool(T.point_los(a, b))
    except Exception:
        return True


def floor_crossed(T, x, y, z0, z1):
    """The highest floor at (x, y) a body going down from z0 to z1 crosses (jumpphys.air_step's rule: the level's floors,
    else the top of floorless rock), or None."""
    c = JP._cell(T, x, y)
    if c is None:
        return None
    j, i = c
    f = T.lz[:, j, i]
    best = None
    for l in range(T.L):
        z = float(f[l])
        if math.isfinite(z) and z1 <= z <= z0 + 0.05 and (best is None or z > best):
            best = z
    if best is None and not any(math.isfinite(float(z)) for z in f):
        top = float(T.top[j * T.nstep, i * T.nstep])
        if top < 999 and z1 <= top <= z0 + 0.05:
            best = top
    return best


class Frag:
    __slots__ = ("h", "pos", "vel", "owner", "team", "born", "out_at", "first", "bounced", "rest")

    def __init__(s, h, pos, vel, owner, team, born):
        s.h, s.pos, s.vel, s.owner, s.team, s.born = h, pos, vel, owner, team, born
        s.out_at, s.first, s.bounced, s.rest = born, pos, None, False


class RealMatch(BS.Match):
    """banshee_sim.Match by the real game's rules (the module docstring)."""

    def __init__(s, map_name=ASYLUM, seed=1, tiers="demon", limit=LIMIT, per_team=4, quiet=True, red_tiers="noble",
                 delay=True, time_limit=TIME_LIMIT):
        s.time_limit = time_limit
        s.frags, s.nade_h = [], 0
        super().__init__(map_name, seed, tiers, limit, per_team, quiet=quiet, red_tiers=red_tiers, delay=delay)
        s.palette = LO.Palette()
        for k, kind in enumerate(ABILITIES):
            s.palette.learn(k, ["dmr", "assault_rifle"], kind)
        for pid, b in s.bots.items():
            b.can_pickup = False                  # no weapons on the map
            b.kit.pressable = True                # the armor ability's button
            b.kit.sprint_ok = False               # (Halo 4's own sprint button; Reach's sprint is an ability)
            b.kit.decoys_listed = False           # as live: holograms are not among the players a bot reads
            b.liked = LO.liked_guns(s.men[pid].name)
        for m in s.men.values():
            s.kit_up(m, first=True)

    # --- a life's kit -------------------------------------------------------------------------------------------------
    def kit_up(s, m, first=False):
        """A spawn's loadout: the slot the bot's own picker asks for (brain/loadouts.liked_slot: its teammates' kinds
        spread), two frags, the meter full."""
        b = s.bots.get(m.id) if hasattr(s, "bots") else None
        slot = getattr(m, "slot", None)
        if b is not None and hasattr(s, "palette"):
            carried = [getattr(o, "kind", "") for o in s.men.values() if o.team == m.team and o.id != m.id]
            want = LO.liked_slot(b, s.palette, slot, carried)
            if want is not None:
                slot = want
        if slot is None:
            slot = (m.id - 1) % len(ABILITIES)
        m.slot, m.kind = slot, ABILITIES[slot]
        m.energy = EQ.Energy(GAME, m.kind)
        m.on, m.lock_since, m.camo_want, m.eq_was = False, None, False, False
        m.reveal_until = 0.0
        m.frags, m.nade_ready, m.nade_was, m.throw_at = FRAGS, 0.0, False, None
        m.air, m.v3, m.jump_was = False, [0.0, 0.0, 0.0], False
        if b is not None:
            b.slot = slot

    def spawn(s, m, first=False):
        super().spawn(m, first)
        if hasattr(s, "palette"):
            s.kit_up(m)

    # --- the world each bot sees --------------------------------------------------------------------------------------
    def snapshot(s):
        snap = super().snapshot()
        players = []
        for p in snap.players:
            m = s.men[p.id]
            on = bool(getattr(m, "on", False))
            camo = on and m.kind == "active_camo" and s.now >= getattr(m, "reveal_until", 0.0)
            vz = m.v3[2] if getattr(m, "air", False) else 0.0
            players.append(dataclasses.replace(p, equipment=getattr(m, "kind", ""), ability_on=on,
                                               camo_until=s.now + 0.3 if camo else 0.0,
                                               vel=Vec(p.vel.x, p.vel.y, vz)))
        return dataclasses.replace(snap, players=players, score_limit=s.limit,
                                   time_left=max(0.0, s.time_limit - s.now),
                                   grenades=[dict(h=f.h, kind="frag_grenade", pos=f.pos, vel=f.vel, since=f.out_at,
                                                  team=f.team, t=f.out_at, **{"from": f.first}) for f in s.frags])

    # --- damage -------------------------------------------------------------------------------------------------------
    def hurt(s, m, dmg, by, head=False, veh_shot=False, how="gun"):
        if m.alive and getattr(m, "on", False) and m.kind == "armor_lock":
            s.stats["lock_blocked"] += 1
            return                                # armor lock: no damage gets through
        super().hurt(m, dmg, by, head, veh_shot, how)

    def kill(s, m, killer, veh_shot, how):
        was = m.alive
        super().kill(m, killer, veh_shot, how)
        if was and killer is not None and killer.id == m.id:
            s.score[m.team] = max(0, s.score[m.team] - 1)   # a suicide (its own frag): a point off, as Reach's
            s.stats["suicides"] += 1
        m.on, m.air = False, False

    # --- the abilities, jumps and throws ------------------------------------------------------------------------------
    def ability(s, m, a):
        """The game's side of the armor ability: the button (and the hold bit for hold-mode kinds, as live), the meter
        (Reach's tags), each kind's effect."""
        k = m.kind
        hold = EQ.hold_bit(GAME, k)
        down = bool(a.equipment) and (bool(a.ability) or not hold)
        press = down and not m.eq_was
        m.eq_was = down
        if k == "active_camo":
            if press:
                m.camo_want = not m.camo_want and m.energy.ready()
            want = m.camo_want
        elif k == "sprint":
            # live Reach: a press at full stick starts it and it runs on after the button is let go, until a second
            # press (77 of 79 ended within 0.2 s of one), the meter dry or the stick off forward (ASSUMED: under half);
            # no shot while it runs (brain/bot.py noble_sprint_off)
            if press:
                m.camo_want = (not m.on) and a.forward >= 0.9 and not m.air
            elif m.on and a.forward < 0.5:
                m.camo_want = False
            want = m.camo_want
        elif k == "armor_lock":
            if down and m.lock_since is None:
                m.lock_since = s.now
            if not down:
                m.lock_since = None
            want = down and s.now - m.lock_since >= (EQ.TAGS[GAME][k].get("warmup_time", 0.0) or 0.0)
        elif k == "hologram":
            want = press and m.energy.ready()
            if want:
                s.stats["holograms"] += 1
        else:                                     # jetpack
            want = down
        if want and not m.energy.on and not m.energy.ready():
            want = False
        if k == "active_camo" and want:
            sp = math.hypot(m.vel.x, m.vel.y)
            m.energy.level -= CAMO_DRAIN_RUN * min(1.0, sp / BS.WALK) * BS.DT
        on = m.energy.tick(s.now, BS.DT, want)
        if k in ("active_camo", "sprint") and not on:
            m.camo_want = False                   # (m.camo_want: a toggle kind's wanted state, camo's or sprint's)
        if on and not m.on:
            s.stats["on_" + k] += 1
        m.on = on and k != "hologram"
        if on:
            s.stats["on_s_" + k] += BS.DT

    def throw(s, m, a):
        press = bool(a.grenade) and not m.nade_was
        m.nade_was = bool(a.grenade)
        if (press and m.frags > 0 and s.now >= m.nade_ready and m.throw_at is None
                and not (m.on and m.kind in ("armor_lock", "sprint"))):
            m.frags -= 1
            m.nade_ready = s.now + NADE_EVERY
            m.throw_at = (s.now + NADE_DELAY, a.yaw, a.pitch)
        if m.throw_at is not None and s.now >= m.throw_at[0]:
            _, yaw, pitch = m.throw_at
            m.throw_at = None
            yaw, pitch = yaw + NADE_YAW_OFF, pitch + NADE_PITCH_OFF
            d = BS.nose(yaw, pitch)
            eye = m.pos + Vec(0, 0, BS.EYE)
            s.nade_h += 1
            s.frags.append(Frag(s.nade_h, eye + d * 0.3, d * NADE_SPEED, m.id, m.team, s.now))
            s.stats["frags_thrown"] += 1

    def walk(s, m, a):
        """The ability, the throw, the jump, then the move: on the ground banshee_sim's walk (sprint faster, armor lock
        none), in the air Reach's air step (a jump, a fall, the jetpack's lift)."""
        s.ability(m, a)
        s.throw(m, a)
        locked = m.on and m.kind == "armor_lock"
        jump = bool(a.jump) and not m.jump_was
        m.jump_was = bool(a.jump)
        if locked:
            m.yaw, m.pitch, m.vel = a.yaw, a.pitch, Vec()
            return
        jet = m.on and m.kind == "jetpack"
        if not m.air and (jump or jet):
            m.air = True
            m.v3 = [m.vel.x, m.vel.y, PHYS.v0 if jump else 0.3]
            if jump:
                s.stats["jumps"] += 1
        if not m.air:
            sp = SPRINT if m.on and m.kind == "sprint" else BS.WALK
            old = BS.WALK
            BS.WALK = sp
            try:
                super().walk(m, a)
            finally:
                BS.WALK = old
            return
        # in the air: steer toward the stick (air control), the jetpack's lift, Reach's gravity and the level's faces
        m.yaw, m.pitch = a.yaw, a.pitch
        f, st = max(-1.0, min(1.0, a.forward)), max(-1.0, min(1.0, a.strafe))
        mag = math.hypot(f, st)
        if mag > 1.0:
            f, st = f / mag, st / mag
        c, sn = math.cos(a.yaw), math.sin(a.yaw)
        top = EQ.JET_FLY if jet else max(BS.WALK, math.hypot(m.v3[0], m.v3[1]))
        want = ((c * f - sn * st) * top, (sn * f + c * st) * top)
        k = JP.AIR_ACCEL * BS.DT * (3.0 if jet else 1.0)
        for i in (0, 1):
            m.v3[i] += max(-k, min(k, want[i] - m.v3[i]))
        if jet:
            m.v3[2] = min(JET_VZ_MAX, m.v3[2] + (PHYS.g + JET_NET) * BS.DT)
        p = [m.pos.x, m.pos.y, m.pos.z]
        JP.prepare(s.T)
        out, impact = JP.air_step(s.T, PHYS, p, m.v3, BS.DT)
        p0 = m.pos
        if out == "void":
            s.kill(m, None, False, "fall")
            return
        if out == "land":
            m.air = False
            m.pos = Vec(p[0], p[1], s.T.nav_z(p[0], p[1], p[2]))
            if impact > PHYS.lethal_v:
                s.kill(m, None, False, "fall")
                return
        else:
            m.pos = Vec(p[0], p[1], p[2])
        m.vel = (m.pos - p0) * BS.HZ

    def fire_gun(s, m, a):
        if m.on and m.kind in ("sprint", "armor_lock") or m.throw_at is not None:
            return                                # no shot sprinting, locked or mid-throw
        shots = s.stats["rounds"]
        super().fire_gun(m, a)
        if s.stats["rounds"] > shots and m.on and m.kind == "active_camo":
            m.reveal_until = s.now + CAMO_SHOT_REVEAL
            m.energy.level = max(0.0, m.energy.level - CAMO_SHOT_COST)

    def melee(s, m, a):
        if m.on and m.kind == "armor_lock":
            return
        super().melee(m, a)

    # --- grenades in flight -------------------------------------------------------------------------------------------
    def step_shots(s):
        super().step_shots()
        keep = []
        for g in s.frags:
            if g.bounced is not None and s.now - g.bounced >= FUSE_BOUNCE or s.now - g.born >= FUSE_MAX:
                s.frag_blast(g)
                continue
            if g.rest:
                keep.append(g)
                continue
            g.vel = g.vel + Vec(0, 0, -NADE_G * BS.DT)
            step = g.vel * BS.DT
            ln = step.length()
            if ln < 1e-6:
                keep.append(g)
                continue
            d = step * (1.0 / ln)
            q = g.pos + step
            # the level as the bots' own throw check sees it (Terrain.point_los: brain/nade.py arc_clear), with Forge
            # pieces' real tops (piece_top); aim_hit's wall bins stood a lip's whole 0.25 u step over its top, and frags
            # thrown over cover lips bounced back at the thrower's feet (3 to 16 suicides a match, live 7 in 2,639 kills)
            floor = floor_crossed(s.T, q.x, q.y, g.pos.z, q.z) if step.z < 0 else None
            if floor is not None:                 # onto the floor first (a line into the floor is no wall)
                hit, d = Vec(q.x, q.y, floor + 0.05), Vec(d.x, d.y, -1.0)
            else:
                hit = None if clear(s.T, g.pos, q) else g.pos
            if hit is None:
                g.pos = q
            else:
                g.pos = hit - d * 0.05
                if g.bounced is None:
                    g.bounced = s.now
                if d.z < -0.3:                    # onto a floor: up a little, on along it slower
                    g.vel = Vec(g.vel.x * BOUNCE_KEEP, g.vel.y * BOUNCE_KEEP, -g.vel.z * BOUNCE_UP)
                else:                             # a wall: its square-on part reflected, the rest kept (ASSUMED)
                    bx = None if clear(s.T, g.pos, g.pos + Vec(step.x + math.copysign(0.05, step.x), 0, 0)) else 1
                    by = None if clear(s.T, g.pos, g.pos + Vec(0, step.y + math.copysign(0.05, step.y), 0)) else 1
                    fx = -WALL_KEEP if bx is not None or by is None else BOUNCE_KEEP
                    fy = -WALL_KEEP if by is not None or bx is None else BOUNCE_KEEP
                    g.vel = Vec(g.vel.x * fx, g.vel.y * fy, g.vel.z * WALL_KEEP)
                if g.vel.length() < 0.6:
                    g.rest, g.vel = True, Vec()
            keep.append(g)
        s.frags = keep

    def frag_blast(s, g):
        s.stats["frag_blasts"] += 1
        for o in list(s.men.values()):
            if not o.alive or o.vehicle != -1 or (o.team == g.team and o.id != g.owner):
                continue                          # (friendly fire off; its thrower hurts itself: ASSUMED)
            q = o.pos + Vec(0, 0, 0.35)
            dd = (q - g.pos).length()
            if dd > FRAG_R or (dd > 0.5 and not s.T.shot_los(g.pos + Vec(0, 0, 0.2), q)):
                continue
            f = 1.0 if dd <= FRAG_KILL_R else max(0.0, 1.0 - (dd - FRAG_KILL_R) / (FRAG_R - FRAG_KILL_R))
            if f > 0:
                s.stats["frag_hits"] += 1
                deaths = o.deaths
                s.hurt(o, FRAG_DMG * f, g.owner, how="grenade")
                if o.deaths > deaths and g.owner != o.id:
                    s.stats["frag_kills"] += 1

    # --- the match ------------------------------------------------------------------------------------------------------
    def over(s):
        return max(s.score.values()) >= s.limit or s.now >= s.time_limit

    def run(s, minutes=None, report_every=60.0):
        return super().run(minutes=(minutes or s.time_limit / 60.0), report_every=report_every)


def summary(m, seed):
    tiers = {0: m.men[min(i for i in m.men if m.men[i].team == 0)].tier,
             1: m.men[min(i for i in m.men if m.men[i].team == 1)].tier}
    kd = {}
    for o in m.men.values():
        k = kd.setdefault(o.team, [0, 0])
        k[0] += o.kills
        k[1] += o.deaths
    st = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in sorted(m.stats.items())}
    return dict(seed=seed, t=round(m.now, 1), score={tiers[0]: m.score[0], tiers[1]: m.score[1]},
                kd={tiers[t]: kd.get(t) for t in (0, 1)}, stats=st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--map", default=ASYLUM)
    ap.add_argument("--red-tiers", default="noble", help="team 0")
    ap.add_argument("--tiers", default="demon", help="team 1")
    ap.add_argument("--per-team", type=int, default=4)
    ap.add_argument("--limit", type=int, default=LIMIT)
    ap.add_argument("--minutes", type=float, default=TIME_LIMIT / 60.0)
    ap.add_argument("--json")
    ap.add_argument("--no-delay", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    o = ap.parse_args()
    out = []
    for seed in [int(x) for x in o.seeds.split(",")]:
        t0 = time.time()
        m = RealMatch(o.map, seed, o.tiers, o.limit, o.per_team, quiet=not o.verbose, red_tiers=o.red_tiers,
                      delay=not o.no_delay, time_limit=o.minutes * 60.0)
        m.run()
        r = summary(m, seed)
        r["real_s"] = round(time.time() - t0, 1)
        out.append(r)
        print(json.dumps(r), flush=True)
    if o.json:
        with open(o.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()

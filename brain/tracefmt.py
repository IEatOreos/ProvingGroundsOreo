"""The extra trace lines tools/observer.py reads, written the same way by the live brain
(tools/live_bots.py) and the simulator (brain/sim.py):

  meta   {"t", "meta": {"map", "game", "bot": {id, name, team, tier, pers}}}   once per bot
  think  {"t", "id", "think": [[goal, arg, score] x6], "chose", "flags", "order", "posture", "beliefs"}
         whenever a bot decides (beliefs: [enemy id, x, y, z, seen 0/1, source, age s])
  call   {"t", "call": text, "team", "kind", "speaker", "zone", "pos", "heard"}  every callout, once
  world  {"t", ..., "world": Everyone.rows(), "blitz": blitz_rows()}   everyone, 4 a second (8 in the simulator)
  bot    {"t", "id", "pos", "yaw", "pitch", "goal", ..., "att": [kind, what, x, y]}   what the bot pays
         attention to: aim (an enemy), watch (a belief: "#5 radar"), flank (a glance left / right), path,
         grenade, gear (an equipment throw); x, y where it looks (Bot.att)
"""
import json
import math

from .core import Vec, angles_to, eye, wrap

# teammates this close are formed up with each other (guide 01 support style: "stays within Medium band
# of a teammate"; the director's support slot is a few units behind its slayer)
FORM_R = 8.0


AIM_REACH = 150.0      # u: how far a crosshair is followed (crosshair)
AIM_R, VEH_R = 0.6, 1.8   # u: a player's chest / a vehicle's middle this near the view line is under the crosshair


def crosshair(p, players, vehicles, T, reach=AIM_REACH):
    """What a person's crosshair is on: [x, y, z, on] where the view line from the eye first meets a player (on: his id), a
    vehicle (on: "v<handle>") or the level (on: None) within reach; None: nothing but sky. In a vehicle, what is within
    3 u of the eye (the vehicle, the gun riding on it, who rides with him) is passed over. ponytail: in a vehicle the
    line starts at the seat, not the game's third-person camera behind it: a unit or two off up close; read the camera
    if needed."""
    if not p.alive:
        return None
    o = eye(p)
    cp = math.cos(p.pitch)
    d = Vec(math.cos(p.yaw) * cp, math.sin(p.yaw) * cp, math.sin(p.pitch))
    hit = T.aim_hit(o, p.yaw, p.pitch, reach) if T is not None and hasattr(T, "aim_hit") else None
    best, on = (hit - o).length() if hit is not None else reach, None
    things = [(q.pos + Vec(0.0, 0.0, 0.4), AIM_R, q.id) for q in players if q.alive and q.id != p.id] + \
             [(Vec(*v["pos"]), VEH_R, f"v{v['handle']}") for v in vehicles if v.get("handle") != p.vehicle]
    near = 3.0 if p.vehicle != -1 else 0.0
    for c, r, who in things:
        t = (c.x - o.x) * d.x + (c.y - o.y) * d.y + (c.z - o.z) * d.z
        if 0.0 < t < best and (c - o).length() > near and ((o + d * t) - c).length() < r:
            best, on = t, who
    if on is None and hit is None:
        return None
    q = o + d * best
    return [round(q.x, 2), round(q.y, 2), round(q.z, 2), on]


def seat_of(p, vehicles):
    """[vehicle kind, gun] a person rides in ("" for the gun when not on one), None on foot."""
    if p.vehicle == -1:
        return None
    v = next((v for v in vehicles if v.get("handle") == p.vehicle), None)
    return [v["kind"] if v else "?", p.turret or ("gun" if p.gunner_seat else "")]


class Everyone:
    """The world line's rows, every player: 0 id, 1 team, 2 alive, 3-5 x y z, 6 shield, 7 health, 8 bot, 9 flag, 10
    yaw, 11 pitch, 12 seconds standing still, 13 ids of the teammates formed up with it (FORM_R), 14 the enemy in
    its sights (-1 nobody); people only (aims given): 15 their crosshair (crosshair), 16 what they ride (seat_of)."""
    def __init__(s):
        s.anchor = {}                 # id -> (where it last moved to, when)

    def rows(s, now, players, bots, los, aims=None):
        out = []
        for p in players:
            still = 0.0
            if p.alive:
                a = s.anchor.get(p.id)
                if a is None or (p.pos - a[0]).flat() > 0.3:
                    s.anchor[p.id] = a = (p.pos, now)
                still = now - a[1]
            else:
                s.anchor.pop(p.id, None)
            mates = [q.id for q in players if p.alive and q.alive and q.id != p.id and q.team == p.team
                     and (q.pos - p.pos).flat() < FORM_R and abs(q.pos.z - p.pos.z) < 3.0]
            out.append([p.id, p.team, p.alive, round(p.pos.x, 2), round(p.pos.y, 2), round(p.pos.z, 2),
                        round(p.shield, 2), round(p.health, 2), p.id in bots, p.has_flag, round(p.yaw, 2),
                        round(p.pitch, 2), round(still, 1), mates, sights(p, players, los)])
            if aims and p.id in aims:
                out[-1] += list(aims[p.id])
        return out


def sights(p, players, los):
    """The enemy in a player's sights: nearest its aim line (a little wider up close) with a line of sight,
    else -1. A person's attention, read from where they aim."""
    if not p.alive:
        return -1
    best, off_best = -1, 9.0
    for e in players:
        if e.team == p.team or not e.alive or e.id == p.id:
            continue
        d = (e.pos - p.pos).flat()
        if d > 80.0:
            continue
        yaw, pitch = angles_to(eye(p), e.pos + Vec(0, 0, 0.35))
        off = math.hypot(wrap(yaw - p.yaw), pitch - p.pitch)
        if off < max(0.12, math.atan2(0.6, max(d, 0.1))) and off < off_best and los(p.pos, e.pos):
            best, off_best = e.id, off
    return best


def brief(x):
    """A goal's argument, an order's point, a call's place, short for the trace."""
    if isinstance(x, Vec):
        return [round(x.x, 1), round(x.y, 1), round(x.z, 1)]
    if x is None or isinstance(x, (int, float, str)):
        return x
    return str(x)[:40]


def think_line(now, index, b):
    """One decision: the top scores (what it weighed), what it chose, the facts behind them (flags),
    its director order, its posture and where it believes the enemies are."""
    top = sorted((getattr(b, "last_scores", None) or {}).items(), key=lambda kv: -kv[1])[:6]
    beliefs = [[k, round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1), int(v.seen), v.source, round(now - v.t, 1)]
               for k, v in b.per.beliefs.items() if isinstance(k, int)][:10]
    return json.dumps(dict(t=round(now, 3), id=index, think=[[k[0], brief(k[1]), round(v, 2)] for k, v in top],
                           chose=[b.goal[0], brief(b.goal[1])], flags=getattr(b, "last_flags", {}),
                           order=[b.order.role, brief(b.order.point)], posture=round(getattr(b, "posture", 0.5), 2),
                           beliefs=beliefs)) + chr(10)


def meta_line(now, map_name, game, index, name, team, prof):
    return json.dumps(dict(t=round(now, 3), meta=dict(map=map_name, game=game, bot=dict(
        id=index, name=name, team=team, tier=prof.tier, pers=prof.personality)))) + chr(10)


def blitz_rows(directors):
    """The world line's "blitz": {team: [why, rally | go]} for each team in one (director.blitz_tick)."""
    # (and a free for all's sides, Infection's: keyed ("side", team); their charge was never written)
    return {str(t if isinstance(t, int) else d.team): [d.blitz["why"], "go" if d.blitz["go"] is not None else "rally"]
            for t, d in directors.items()
            if (isinstance(t, int) or (isinstance(t, tuple) and t[0] == "side")) and getattr(d, "blitz", None)}


def call_lines(now, director, said):
    """New callouts of one team's director (said: keys already written, updated)."""
    out = []
    for c in director.callouts:
        ck = (c.speaker, round(c.t_event, 2), c.text)
        if ck not in said:
            said.add(ck)
            out.append(json.dumps(dict(t=round(now, 3), call=c.text, team=director.team, kind=c.kind,
                                       speaker=c.speaker, zone=c.zone, pos=brief(c.pos),
                                       heard=round(c.t_heard, 2))) + chr(10))
    return out

"""Firefight teammates without map data (ODST: the kit does not export the collision geometry of the
areas Firefight uses). Each bot follows the player by walking a skilled player's footsteps (a
trail of his positions: always walkable), keeps 3-6 units from him, and fights the nearest
Covenant in range: lead-aimed, reaction delay and aim error by tier, burst fire, and a target its
shots do not hurt (behind cover the bot cannot see) is dropped for a few seconds. Logs every tick
to logs/escort_<game>.jsonl and prints a score at the end.

usage: python -I escort_bots.py [seconds=120] [--game odst] [--tier average]
"""
import argparse
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import botctl  # noqa: E402

HZ = 30
CHEST = 0.45                          # aim this far above the feet (Elites and Brutes stand tall)
TIERS = {"novice": (0.45, 0.06), "average": (0.30, 0.035), "strong": (0.22, 0.02), "top": (0.15, 0.012)}   # reaction s, aim error rad
TIERS["demon"] = (0.15, 0.012)  # explicit campaign/Firefight settings, independently tunable
RANGE = 28.0
MATCH_GONE = 6                         # failed reads in a row (0.5 s apart) that mean the match is over


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Escort:
    def __init__(s, slot, index, tier, rng):
        s.slot, s.index, s.rng = slot, index, rng
        s.react, s.err = TIERS[tier]
        s.trail_i, s.target, s.seen_at = 0, None, 0.0
        s.shots, s.hp_at_start, s.banned = 0, 1.0, {}
        s.last, s.stuck_t, s.wiggle_until, s.wiggle = None, 0.0, 0.0, (0.0, 0.0)
        s.err_xy, s.err_t, s.strafe, s.strafe_t = (0.0, 0.0), 0.0, 1.0, 0.0
        s.prev_tpos = None

    def think(s, now, me, person, trail, enemies):
        fwd = strafe = 0.0
        yaw = math.atan2(me["aim"][1], me["aim"][0]) if me["aim"] else 0.0
        pitch, fire = 0.0, False
        pos = me["pos"]
        # --- fight: nearest Covenant in range, not banned (unhittable from here)
        live = [e for e in enemies if math.dist(e["pos"], pos) < RANGE and s.banned.get(e["index"], 0) < now]
        tgt = min(live, key=lambda e: math.dist(e["pos"], pos) - (4 if e["index"] == s.target else 0), default=None)
        if tgt and tgt["index"] != s.target:
            s.target, s.seen_at, s.shots, s.hp_at_start, s.prev_tpos = tgt["index"], now, 0, tgt["health"] + tgt["shield"], None
        if not tgt:
            s.target = None
        # --- move: walk the player's footsteps until 3-6 units from him
        d_person = math.dist(person["pos"][:2], pos[:2]) if person["pos"] else 0.0
        if trail and (s.trail_i >= len(trail) or math.dist(trail[min(s.trail_i, len(trail) - 1)][:2], pos[:2]) > 12):
            s.trail_i = min(range(len(trail)), key=lambda i: math.dist(trail[i][:2], pos[:2]))   # rejoin (respawned)
        goal = None
        if d_person > (6.0 if s.target is None else 9.0) and trail:
            while s.trail_i < len(trail) - 1 and math.dist(trail[s.trail_i][:2], pos[:2]) < 1.2:
                s.trail_i += 1
            goal = trail[min(s.trail_i, len(trail) - 1)]
        if goal is not None:
            move = math.atan2(goal[1] - pos[1], goal[0] - pos[0])
        if s.target is not None and now - s.seen_at > s.react:
            tp, tv = tgt["pos"], (0.0, 0.0, 0.0)
            if s.prev_tpos:
                tv = tuple((a - b) * HZ for a, b in zip(tp, s.prev_tpos))
            s.prev_tpos = tp
            eye = (pos[0], pos[1], pos[2] + 0.62)
            d = math.dist(tp, eye)
            lead = d / 300.0 + 0.05
            aim = (tp[0] + tv[0] * lead, tp[1] + tv[1] * lead, tp[2] + CHEST + tv[2] * lead)
            if now > s.err_t:                       # a fresh small aim error every half second
                s.err_xy, s.err_t = (s.rng.gauss(0, s.err), s.rng.gauss(0, s.err)), now + 0.5
            yaw = math.atan2(aim[1] - eye[1], aim[0] - eye[0]) + s.err_xy[0]
            pitch = math.atan2(aim[2] - eye[2], math.hypot(aim[0] - eye[0], aim[1] - eye[1])) + s.err_xy[1]
            fire = int(now * 8) % 4 < 2            # bursts
            if fire:
                s.shots += 1
            hp = tgt["health"] + tgt["shield"]
            if hp < s.hp_at_start - 0.01:
                s.shots, s.hp_at_start = 0, hp     # landing: keep going
            elif s.shots > 45:                     # 45 trigger ticks, nothing landed: out of sight
                s.banned[s.target] = now + 5.0
                s.target = None
            if now > s.strafe_t:                   # strafe while shooting, as people do
                s.strafe, s.strafe_t = s.rng.choice((-1.0, 1.0)), now + s.rng.uniform(0.6, 1.4)
            strafe = 0.6 * s.strafe
        elif person["aim"] and goal is None:
            yaw = math.atan2(person["aim"][1], person["aim"][0])   # idle: look where the player looks
        if goal is not None:
            if s.target is None or now - s.seen_at <= s.react:
                yaw = move                           # not shooting: face where you walk
            rel = wrap(move - yaw)
            fwd, strafe = math.cos(rel), math.sin(rel)
        # --- unstick: pressing to move but not moving for 1 s: jump and sidestep
        if s.last and (abs(fwd) + abs(strafe)) > 0.3 and math.dist(pos[:2], s.last[:2]) < 0.02:
            s.stuck_t += 1.0 / HZ
        else:
            s.stuck_t = 0.0
        s.last = pos
        jump = False
        if s.stuck_t > 1.0:
            a = s.rng.uniform(0, 2 * math.pi)
            s.wiggle, s.wiggle_until, s.stuck_t = (math.cos(a), math.sin(a)), now + 0.6, 0.0
            jump = True
        if now < s.wiggle_until:
            fwd, strafe = s.wiggle
        buttons = (botctl.BTN["fire"] if fire else 0) | (botctl.BTN["jump"] if jump else 0)
        return fwd, strafe, yaw, pitch, buttons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seconds", type=float, nargs="?", default=120)
    ap.add_argument("--game", default="odst")
    ap.add_argument("--tier", default="average")
    o = ap.parse_args()
    from brain.live import LiveODST, LiveReach
    live, m = {"odst": LiveODST, "reach": LiveReach}[o.game](), botctl.shm()   # (Reach: its Firefight maps)
    rng = random.Random(5)
    bots = {}
    trail = []
    log = open(os.path.join(HERE, "..", "logs", f"escort_{o.game}.jsonl"), "w")
    t0 = time.time()
    fails = 0
    while time.time() - t0 < o.seconds:
        tick = time.time()
        now = tick - t0
        try:
            players = live.players()
            enemies = live.ai_units(players)
        except Exception as e:                       # a read raced the game (match over, object gone)
            print("read failed:", e)
            fails += 1
            # the match is over (3 s of failed reads, as live_bots): stop. botcore ends play.py at the next match, not
            # this child: live Nov 6 an Installation 04 escort brain drove the next match's bots beside its brain
            if fails >= MATCH_GONE:
                print("game gone, brain stopping:", e, flush=True)
                break
            time.sleep(0.5)
            continue
        fails = 0
        ps = {p["index"]: p for p in players}
        person = ps.get(0)
        if person and person["pos"] and (not trail or math.dist(trail[-1][:2], person["pos"][:2]) > 0.75):
            trail.append(person["pos"])
            trail = trail[-600:]
        for slot, index in botctl.status(m)["bots"].items():
            if index not in bots:
                bots[index] = Escort(slot, index, o.tier, rng)
            me = ps.get(index)
            if not me or not me["pos"] or not person or not person["pos"]:
                continue
            foes = [e for e in enemies if e["team"] != me["team"]]     # (Versus' Elite round: the Covenant are allies)
            fwd, strafe, yaw, pitch, buttons = bots[index].think(now, me, person, trail, foes)
            botctl.act(m, slot, fwd, strafe, yaw, pitch, buttons)
            b = bots[index]
            tgt = next((e for e in enemies if e["index"] == b.target), None)
            log.write(json.dumps(dict(t=round(now, 3), id=index, pos=[round(v, 2) for v in me["pos"]],
                                      owner_d=round(math.dist(me["pos"], person["pos"]), 2), target=b.target,
                                      target_hp=round(tgt["health"] + tgt["shield"], 3) if tgt else None,
                                      fire=bool(buttons & 1), cmd=[round(fwd, 2), round(strafe, 2)],
                                      enemies=len(enemies), hp=round(me["health"], 2))) + "\n")
        time.sleep(max(0.0, 1.0 / HZ - (time.time() - tick)))
    log.close()
    print(json.dumps(score(os.path.join(HERE, "..", "logs", f"escort_{o.game}.jsonl"))))


def score(path):
    rows = [json.loads(l) for l in open(path)]
    by = {}
    for r in rows:
        by.setdefault(r["id"], []).append(r)
    hits = kills = fire_ticks = stuck = moving = 0
    for rs in by.values():
        for a, b in zip(rs, rs[1:]):
            fire_ticks += a["fire"]
            if a["target"] is not None and a["target"] == b["target"] and a["target_hp"] is not None and b["target_hp"] is not None:
                hits += b["target_hp"] < a["target_hp"] - 0.005
            if a["target"] is not None and a["target"] != b["target"] and a["target_hp"] is not None and a["target_hp"] < 0.35:
                kills += 1                           # dropped a nearly dead target: it died (or vanished)
            if abs(a["cmd"][0]) + abs(a["cmd"][1]) > 0.3:
                moving += 1
                stuck += math.dist(a["pos"][:2], b["pos"][:2]) < 0.02
    dists = sorted(r["owner_d"] for r in rows)
    return dict(minutes=round((rows[-1]["t"] - rows[0]["t"]) / 60, 1) if rows else 0, bots=len(by), fire_ticks=fire_ticks,
                damage_ticks=hits, likely_kills=kills, median_person_dist=dists[len(dists) // 2] if dists else None,
                stuck_share=round(stuck / max(moving, 1), 2))


def selftest():
    e = Escort(0, 1, "average", random.Random(1))
    person = dict(pos=(20.0, 0.0, 0.0), aim=(1.0, 0.0, 0.0))
    trail = [(x, 0.0, 0.0) for x in range(0, 21)]
    me = dict(pos=(0.0, 0.0, 0.0), aim=(0.0, 1.0, 0.0))
    fwd, strafe, yaw, pitch, b = e.think(0.0, me, person, trail, [])
    assert abs(wrap(yaw + math.atan2(strafe, fwd))) < 0.2 and fwd > 0.9 and abs(yaw) < 0.2, "walks east, facing east"
    near = dict(pos=(17.0, 0.0, 0.0), aim=(1.0, 0.0, 0.0))
    assert e.think(0.1, near, person, trail, [])[:2] == (0.0, 0.0), "holds within 6 units of the person"
    foe = dict(index=1007, pos=(17.0, 10.0, 0.0), health=1.0, shield=1.0)
    assert not e.think(0.2, near, person, trail, [foe])[4] & 1, "no shot before the reaction time"
    assert any(e.think(0.6 + k / 30, near, person, trail, [foe])[4] & 1 for k in range(8)), "fires after it"
    print("escort self-check OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()

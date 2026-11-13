"""Per-team director: the team's comms. Knows only what its bots report.

- Bot reports become spoken callouts through one team voice channel (brain/callouts.py):
  named zones from maps/<map>/callouts.json, speech timing by the speaker's skill tier,
  urgent calls first, duplicates merged, stale sightings dropped instead of read out late.
- Every 2 s it hands out roles (CTF: runner, escort, defender, hunter, push; Slayer:
  mid control and hunters) by a cost function: distance, role inertia, personality fit.
- A death near our flag pulls the nearest free bots back to defend for 15 s.
- The team's play follows the mode, the score and the clock (brain/match.py posture and tempo: careful when the
  enemy is about to win, all in when behind late), with each mode's own plans (CTF carries and escorts, Invasion
  phases, King hill pushes, ...).
"""
from . import profiles
import math
import random
from .core import PlayerState, Vec, dist
from .bot import Bot, Order, VEHICLE_TRIP, GETAWAY_PARK_R
from .callouts import Call, VoiceChannel, TIMING, LISTENER_BUSY
from .modes import NEW_MODES
from .match import posture, tempo, one_flag_posture, Posture

DEFEND_PULL_TIME = 15.0
SPLIT_CHANCE = 0.5          # a CTF attack cycle (40-70 s) split over two lanes instead of one group
# seconds into an Invasion phase: the attackers all go into the territory. 0: from the start. Live Boneyard B17-B25
# the round 2 attack had its pile-on from the first second (its side's director kept inv_push from round 1) and took
# phase 1 in 7 of 9 rounds; round 1's split for 60 s (two in, one to the other territory, escorts, overlooks) 2 of 9,
# with the same movement and speed on both sides (logs/tmp/invasion_regress sidecmp.py / speeds.py, tools/test_round_plan)
PUSH_AFTER = 0.0
INV_STALL = 25.0            # ... and kept while one of the team was within 8 u of it in the last this many s (director)
INV_COMMIT = 30.0           # an Invasion attack keeps its territory at least this long after picking it (director)
# a CTF carry as the team's play: three escorts from six of us, one screen SCREEN_BACK u toward their base, the pushers
# SCREEN_AHEAD u ahead of him on his way home (role_slots); CUTOFF: hunters on their carrier cut him off on his way
# home (custom, Nov 10: intercepts, CUT_* below; upstream sent one CUTOFF_AHEAD u ahead with three or more). False:
# the play before (A/B)
CARRY_PLAY, CUTOFF = True, True
CTF_DEFEND_LEAD = 2         # (custom, Nov 9) CTF: one defender only this many captures ahead or more (role_slots)
# (custom, Nov 10) CTF cut-offs (Director.intercepts): a hunter goes to the first point on the enemy carrier's way home
# it reaches CUT_MARGIN_S s before him (both at CUT_RUN u/s, his pace CARRIER_PACE of ours: ASSUMED equal, a Halo 4
# carrier's speed is unmeasured), points every CUT_STEP u from CUT_MIN_AHEAD u ahead of him; never one behind him. His
# ways: the shortest from where he is, the next shortest from our stand (CUT_ALT_COST times the cost within CUT_ALT_R u
# of the first) and the enemy's hand-drawn sneak routes reversed, each one he is within CUT_ON_ROUTE u of and at most
# CUT_DETOUR times the shortest, not CUT_OVERLAP the same as one already taken. One bot a way; a bot within CUT_CHASE_R
# u of him keeps one hunter chasing; within CUT_NEAR_GOAL u of his goal, all chase. CUT_CANDIDATES nearest bots weighed
# A point is made when the bot is within CUT_NEAR u of it on its floor (CUT_LEVEL_DZ) first: it waits there, in range
CUT_RUN, CARRIER_PACE, CUT_MARGIN_S, CUT_NEAR, CUT_LEVEL_DZ = 2.25, 1.0, 1.0, 5.0, 2.0
CUT_STEP, CUT_MIN_AHEAD, CUT_SPREAD = 3.0, 4.0, 8.0
CUT_ON_ROUTE, CUT_DETOUR, CUT_OVERLAP, CUT_ALT_R, CUT_ALT_COST = 6.0, 1.6, 0.6, 3.0, 3.0
CUT_CHASE_R, CUT_NEAR_GOAL, CUT_CANDIDATES, CUT_MAX_STEPS = 15.0, 8.0, 6, 1600
# (custom, Nov 10, owner) Team Slayer high ground, Legendary / Blind / Scaling / Demon (profiles.high_ground; Bot.slayer_post
# holds them on it). The team's post (slayer_slots) is kept POST_EXTEND s at a time while one of those tiers holds it
# (within ANCHOR_R) and sees men from it (one seen in the last POST_QUIET s), up to POST_HOLD_MAX s; two of ours dead
# within POST_LOSS_R u of it in POST_LOSS_S s and the team moves on at once (upstream: a new post every 25-45 s, the
# walk up to Complex's top floor about as long). The support and the floater sent on a sweep, when one of those tiers,
# go to a perch: the map's power position PERCH_MIN-PERCH_MAX u from the fight, PERCH_DZ u or more above it, that sees it
# (else the sweep's power position), and hold it ("mid"); the lead hunter still goes straight at the fight
POST_EXTEND, POST_HOLD_MAX, POST_QUIET, POST_LOSS_R, POST_LOSS_S = 15.0, 120.0, 20.0, 12.0, 30.0
PERCH_MIN, PERCH_MAX, PERCH_DZ = 5.0, 25.0, 1.0
# the getaway ride: one transport driver parks GETAWAY_D u from their stand on our side while our runners go in, then
# fetches our carrier at any distance
GETAWAY, GETAWAY_D = True, 16.0
# King: theirs on the hill, we take it (Director.king_take): KING_TAKE False is the play before (A/B)
KING_TAKE, KING_TAKE_HOLD = True, 4.0
# CTF's attack wave (wave_tick): gather at the rally WAVE_GATHER_S at most, then all in WAVE_GO_S, WAVE_COOL_S between
WAVE = True
WAVE_GATHER_S, WAVE_GO_S, WAVE_COOL_S = 6.0, 20.0, 4.0
SCREEN_BACK, SCREEN_AHEAD, CUTOFF_AHEAD = 8.0, 12.0, 10.0
LEGENDARY_POWER_RUN_R = 80.0  # fixed Legendary contests power weapons from farther away; Scaling keeps POWER_RUN_R
POWER_RUN_R = 40.0          # a power weapon lying this near (on its level) sends one of the team for it (power_runs)
POWER_PRESS_R = 10.0        # ... this near for an attacker whose objective is pressing (Bot.pressing: Invasion's attackers)
POWER_DETOUR = 12.0         # ... or this much more than its straight way to the objective (press_fetch_ok)
POWER_EARLY, POWER_WAIT = 10.0, 8.0   # a power spawn due back within this is fetched; the fetcher waits this past its time
# the blitz (blitz_tick): the team rallies BLITZ_RALLY_D short of the objective, BLITZ_GATHER_S at most or until
# BLITZ_READY of it is there, goes in together BLITZ_GO_S at most, then plays its normal plan BLITZ_COOL_S
BLITZ_RALLY_D, BLITZ_GATHER_S, BLITZ_GO_S, BLITZ_COOL_S, BLITZ_READY = 14.0, 4.0, 25.0, 15.0, 0.6
# Invasion phase 3's core waves (Director.regather): from a respawn, wait REGATHER_D short of the core for REGATHER_N
# goers or REGATHER_S s, then in together
REGATHER_D, REGATHER_N, REGATHER_S = 22.0, 3, 8.0
BLITZ_SPREAD = 25.0         # u: one of the team this far from the rest makes the rest rally for it first
AMBUSH_S = 30.0             # s an infected waits at one corner (director.ambush_fresh), then hunts as long
INF_SPREAD, INF_GATHER_S = 8.0, 8.0  # Infection's charge (desperate): gathered unless within 8 u of each other, 8 s at most
BLITZ_DETOUR = 1.3         # the second prong's way at most this many times the first's (rally -> prong -> target)
PRONG_NAV_DETOUR = 2.5     # a prong's way by the nav at most this many times the rally's own (prong_pair; Blood Gulch's 1.4)
# an Invasion push's flanks (push_lanes): LANE_R u out from the territory, LANE_ANGLE off the team's line in, kept
# LANE_KEEP_S per territory; attackers with posts within LANE_NEAR of it take them in turn
LANE_R, LANE_ANGLE, LANE_KEEP_S, LANE_NEAR = 14.0, math.radians(60.0), 30.0, 15.0
LANE_PHASES = (2,)          # the Invasion phases whose push takes the flanks (assign_roles: phase 1 rushes straight)
BLITZ_MODES = ("ctf", "assault", "stockpile", "king", "headhunter")    # (+ Invasion attacking; desperate says why not others)
AIR_CALL = 2.5               # a transport aircraft calls riders from this many CALL_R (rider_calls; Bot.crew_coming waits)
HORN_CALL_R = 40.0           # u: the bot a person's horn picked (his view on him) is called from this far (honk_orders)
LAND_CALL_R_PERSON = 20.0    # u: (custom) ... a person's aircraft set down (honk_orders)
LAND_CALL_R = 10.0          # u: an aircraft of ours set down calls the bots on foot this near aboard (honk_orders) ...
LANDED_H, LANDED_V = 1.5, 1.0   # ... down: under this high over the floor (u) and this slow (u/s) (landed_aircraft)
# Invasion's desperate moments for the attackers (desperate): the phase's last INV_LAST_S of its INV_PHASE_S clock (guide
# 19's rule facts: 4 minutes a phase; it running out loses the round), or a wave wiped: two thirds of the team (2 at
# least) dead in INV_WIPE_S
INV_PHASE_S, INV_LAST_S, INV_WIPE_S = 240.0, 60.0, 60.0
COUNT_WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four"}
OBJECTIVE_TEXT = {"flag_taken": "enemy pulled our flag at {zone}", "flag_dropped": "our flag dropped at {zone}",
                  "flag_returned": "our flag is home", "scored": "we captured", "enemy_scored": "enemy captured our flag"}


class Director:
    def __init__(s, team, mapdata, bots, rng=None, log=None, legacy_comms=False, side=None, home_rule=True):
        s.team, s.map, s.bots = team, mapdata, bots   # bots: id -> Bot (this team); team: the game's team
        s.side = team % 2 if side is None else side   # map knowledge (home flag, holds, routes) is red/blue
        s.zones = mapdata["zones"]
        s.rng = rng or random.Random(team)
        s.events = []                  # (time, kind, text): kill feed, respawns, objective, phase (9.3)
        s.alive_was, s.died_at, s.human_ids = {}, {}, {}
        s.phase, s.rule_state = "opening", "unknown"
        s.role_changes = []
        # the whole match so far, kept by code every tick for the commander's report: no model time
        s.match = dict(samples=[], our_deaths={}, our_kills={}, enemy_seen={}, bot_deaths={}, bot_kills={}, plays={})
        s.voice = VoiceChannel(s.rng, legacy=legacy_comms, text_of=s.text)
        s.callouts = []       # heard, still fresh: what every bot on the team knows
        s.threat = {}         # zone -> (level, time)
        s.threat_at = {}      # zone -> where in it the last report put the enemy (slayer_slots' hunt target)
        s.next_roles = 0.0
        s.defend_until = 0.0
        # CTF: a capture needs our flag home. Per-game custom defaults (docs/research/12 section 1.1): CE's built-in CTF
        # and Reach yes (seen in Reach's lobby), Halo 2 / 3 / H2A no; off for the match once we score with it out
        s.home_rule = home_rule
        s.plan = {"stance": "balanced", "defenders": 2}
        s.posture, s.posture_state = Posture(0.5, "unknown"), "unknown"
        s.log = log if log is not None else []
        s.roles = {}
        # power item timers the team knows: item index -> when it should be back (0 = up now)
        s.item_up = {i: 0.0 for i in range(len(mapdata.get("items", [])))}

    def item_taken(s, i, now, respawn):
        """A teammate took it, or someone on the team saw it taken: start its timer. Nobody of ours within 3 u of it
        then: the enemy took it (the commander's TENDENCIES: which power item they go for)."""
        s.item_up[i] = now + respawn
        items = s.map.get("items", [])
        if i < len(items) and not any(dist(q, items[i]["pos"]) < 3.0 for q in getattr(s, "mine_pos", ())):
            s.tally("enemy_items", items[i]["name"])

    # --- reports from bots
    def report(s, now, bot_id, kind, pos, count=1, enemy=None, busy=False, killer_weak=False, died_at=None):
        """pos: where the thing is (for a death: where the killer was). died_at: where a bot died."""
        zone = s.zones.name(pos)
        if kind in OBJECTIVE_TEXT:                     # the announcer: an objective event for the coach (9.3)
            s.event(now, kind, OBJECTIVE_TEXT[kind].format(zone=zone))
        if kind == "seen":                             # where the enemy keeps turning up, all match
            s.tally("enemy_seen", zone, count)
            s.match.setdefault("seen_min", {}).setdefault(zone, set()).add(int(now // 60))   # (TENDENCIES)
            s.tally("sightings", "group" if count >= 2 else "alone")
        if kind != "pickup":                           # (a driver's "Get in" is no sign of enemies there)
            lvl = s.threat.get(zone, (0, now))[0]
            s.threat[zone] = (min(lvl + (3 if kind == "died" else 1), 10), now)
            s.threat_at[zone] = pos
        home = s.map["flags"][s.side]
        if kind == "died" and dist(died_at or pos, home) < 12:
            s.tally("base_hits", zone)                  # where they hit our base from (TENDENCIES)
            s.defend_until = now + DEFEND_PULL_TIME   # losing people at our flag: send help
            if dist(pos, home) < 15:
                kind = "died_at_flag"                   # and the killer is on it: urgent
        if busy and kind in ("seen", "cracked", "one_shot"):
            zone = s.zones.area_name(pos)   # in a fight you blurt the general area
        b = s.bots.get(bot_id)
        if b is not None and b.p.teamwork <= 0:
            return None        # Easy plays for itself: it calls nothing out
        tier = b.p.tier if b else ("top" if bot_id == -1 else "average")   # -1: game announcer / HUD
        c = Call(kind, zone, pos, now, bot_id, tier, busy, count, {enemy})
        c.killer_weak = killer_weak
        return s.voice.post(now, c)

    def text(s, c):
        """Blood Gulch big-team comms style, docs/research/06 section 8.3:
        [count] [place][, status]. "Two Big Hill", "One shot, Water", "Carrier Red port!"."""
        z = c.zone
        if c.kind == "seen":
            if c.update:
                return f"{COUNT_WORD.get(c.count, 'A bunch')} now, {z}"
            return f"{COUNT_WORD.get(c.count, 'A bunch')} {z}"
        if c.kind == "cracked":
            return f"Weak, {z}"
        if c.kind == "one_shot":
            return f"One shot, {z}"
        if c.kind == "died_at_flag":
            return f"On our flag, {z}!"
        if c.kind == "backup":                    # (backup_orders: a post we hold is contested)
            return f"Need backup, {z}!"
        if c.kind == "pickup":                    # (rider_calls: a driver flags teammates down)
            return f"Get in, {z}!"
        if c.kind == "died":   # a dead player calls where the killer is
            return f"Dead, one shot {z}" if c.killer_weak else f"Dead, he's {z}"
        if c.kind == "flag_taken":
            return "Flag pulled!"
        if c.kind == "flag_carrier":
            return f"Carrier {z}!"
        if c.kind == "flag_dropped":
            return f"Flag's down, {z}"
        if c.kind == "scored":
            return "We scored!"
        if c.kind == "enemy_scored":
            return "They capped, reset!"
        if c.kind == "flag_returned":
            return "Flag's home"
        return z

    def said_at(s, pos):
        """Where a callout puts the enemy for the listeners: his zone, not the exact spot, on the floor he was on. A
        zone's centre is its lowest floor (maps.py): Construct's Mid centres on the pit, and every "Mid" sent the
        listeners down there. Off his floor: halfway from the centre to him, at his height."""
        c = s.zones.zone(pos).center
        if abs(c.z - pos.z) < 2.0:
            return c
        q = Vec((c.x + pos.x) / 2, (c.y + pos.y) / 2, pos.z)
        z = s.terrain().nav_z(q.x, q.y, pos.z)
        return Vec(q.x, q.y, z) if abs(z - pos.z) < 2.0 else pos

    # --- every tick
    def update(s, now, snap):
        for c in s.voice.update(now):
            c.pos_said = s.said_at(c.pos)            # listeners get the zone, not the exact spot
            # each teammate understands after the key words, by his own skill, later if fighting
            for b in s.bots.values():
                if b.id == c.speaker or not snap.player(b.id).alive:
                    continue
                busy = b.goal[0] in ("fight", "retreat")
                c.avail[b.id] = c.t_key if s.voice.legacy else (
                    c.t_key + (b.p.extra or {}).get("hear", TIMING[b.p.tier]["hear"]) + (LISTENER_BUSY if busy else 0.0))
            c.t_heard = min(c.avail.values()) if c.avail else c.t_key
            s.callouts.append(c)
            s.log.append((round(c.t_heard, 2), s.team, c.text, round(c.t_heard - c.t_event, 2), c.kind))
        s.callouts = [c for c in s.callouts if now - c.t_key < 6.0]
        s.track_events(now, snap)
        # score posture from the variant's own limit and clock (brain/match.py), and who the team is
        # shooting (team shot: guide 01 section 10, +30 threat for a target a teammate is on)
        # points a kill: the step the team scores move in (Halo 4 slayer 10, the others 1), so "about
        # to win" is kills from the limit, not points (600 of Infinity Slayer: at 550, not at 595)
        last = s.__dict__.setdefault("score_last", {})
        own = (snap.flags or {}).get(s.team)
        if own is not None and own.state != "home" and (snap.score or {}).get(s.team, 0) > last.get(s.team, 1 << 30):
            s.home_rule = False     # we scored with our flag out: this variant does not need it home
        for k, v in (snap.score or {}).items():
            if v > last.get(k, v):
                s.score_unit = math.gcd(getattr(s, "score_unit", 0), v - last[k])
            last[k] = v
        # who is alive, from the kill feed: ours against the most alive on another team (guide 19 SLAY-CORE-07); not
        # where the sides are uneven by design (Firefight's Covenant, Infection, Juggernaut)
        alive = {}
        for q in snap.players:
            alive[q.team] = alive.get(q.team, 0) + q.alive
        theirs = [v for k, v in alive.items() if k != s.team]
        up = alive.get(s.team, 0) - max(theirs) if theirs and snap.mode not in ("firefight", "infection", "juggernaut") \
            else 0
        p = posture(snap.score, s.team, snap.score_limit, snap.time_left, snap.mode, getattr(s, "score_unit", 0) or 1, up)
        if s.is_one_flag(snap):
            p = one_flag_posture(p, own is not None, snap.time_left)
        hist = s.__dict__.setdefault("score_hist", [])
        best = max(snap.score.values()) if snap.score else 0
        if not hist or hist[-1][1] != best or now - hist[-1][0] > 5:
            hist.append((now, best))
        while hist and now - hist[0][0] > 180:              # the leader's pace over the last 3 minutes
            hist.pop(0)
        span = now - hist[0][0] if hist else 0
        rate = (best - hist[0][1]) / (span / 60.0) if span > 30 else 99.0   # too early to judge: no push
        s.posture = tempo(p, rate, snap.time_left)
        s.posture_state = s.posture.state
        focus = {}
        for b in s.bots.values():
            if b.goal[0] == "fight" and snap.player(b.id) and snap.player(b.id).alive:
                focus[b.goal[1]] = focus.get(b.goal[1], 0) + 1
        hot = s.hot_spot(now)          # map brain MAP-10: what a bot at its post watches with nobody known (Bot.look_point)
        for b in s.bots.values():
            # Easy ignores the team: no team shot, no score posture (it plays the same at 0-10 and 10-0), no hot zone
            b.team_focus, b.posture, b.hot_spot = (focus, s.posture.value, hot) \
                if b.p.teamwork > 0 else ({}, 0.5, None)
        if now >= s.next_roles:
            s.next_roles = now + 2.0
            s.assign_roles(now, snap)
        s.blitz_tick(now, snap)
        s.wave_tick(now, snap)
        s.core_wave_tick(now, snap)

    def desperate(s, now, snap):
        """(where, why) when only everyone going in together saves the game, else None. BLITZ_MODES by the score posture:
        the last minute behind (all_in), far behind late, and in King and Headhunter the enemy one push from the limit:
        there standing back is losing. Its objective (blitz_target). Invasion attacking: the phase's last minute, or a
        wave wiped (INV_LAST_S, INV_WIPE_S), and a blitz on is seen through (the deaths age out). Not every wave: the
        pile-on already sends the whole team (the sim, Spire phase 3 the last minute: 4 of 6 games the same, one better,
        one worse), and a blitz with a rally from 20 s into each phase cut its pickups 6 of 6 -> 2 of 6. The other modes
        have their own all in: Slayer's posture push (slayer_slots, every bot a hunter from two fronts; the blitz's one
        point and leash cut the sim's last-minute kills 35 -> 19 in 3 games), Oddball's whole team on the ball or its
        carrier, Infection's survivors in one haven, Invasion's defenders on the carrier or the territory being taken;
        in Territories holding is the score (the sim, all in on one: our points 11 -> 8, theirs 4 -> 8). Never while the
        core or a flag is in our hands: that is the carrier's and his escorts' plan."""
        if any(p.team == s.team and p.alive and p.has_flag for p in snap.players):
            return None
        if snap.mode == "infection":
            # the infected, at survivors grouped and holding well (two or more together, standing): all rally, then
            # charge at once (issue #3: they came in one at a time)
            from .modes import zombie_team, survivor_clusters
            if zombie_team(snap) != s.team:
                return None
            for c, grp in survivor_clusters([p for p in snap.players if p.team != s.team]):
                if sum(q.vel.flat() for q in grp) / len(grp) < 1.0:
                    return c, "infection: they hold"
            return None
        if snap.mode == "invasion":
            if snap.inv_attackers != s.team:
                return None
            ours = [p for p in snap.players if p.team == s.team]
            lost = sum(1 for p in ours if now - s.died_at.get(p.id, -1e9) < INV_WIPE_S)
            if (not s.inv_late(snap) and lost < max(2, math.ceil(2 * len(ours) / 3))
                    and getattr(s, "blitz", None) is None):
                return None
            if snap.inv_phase == 3 and snap.inv_core is not None:
                return snap.inv_core, "the core"
            zones = snap.inv_zones or []
            if not zones:
                return None
            keep = getattr(s, "inv_target", None)
            # (the phase in the why: one taken ends its blitz, blitz_tick)
            return (next((z for z in zones if keep is not None and dist(z, keep) < 0.5), zones[0]),
                    f"the territory, phase {snap.inv_phase}")
        p = s.posture
        if snap.mode not in BLITZ_MODES or not (p.state == "all_in" or (p.state == "far_behind" and p.value >= 0.9)
                                                or (p.state == "enemy_near_win" and snap.mode in ("king", "headhunter"))):
            return None
        if snap.mode == "king" and not s.hill_contested(now, snap):
            return None     # (the whole team in the hill only to take it from a man in it: guide 19 KOTH-STATIC-01)
        team = [snap.player(b.id) for b in s.bots.values() if snap.player(b.id) and snap.player(b.id).alive]
        c = Vec(sum(q.pos.x for q in team) / len(team), sum(q.pos.y for q in team) / len(team),
                sum(q.pos.z for q in team) / len(team)) if team else None
        target = s.blitz_target(snap, c)
        return (target, p.state) if target is not None else None

    @staticmethod
    def inv_late(snap):
        """An Invasion phase's last minute, by the game's own clock where it is read (snap.time_left: match 214711 read it
        down to 0 at 243 s and the round ran 110 s of overtime on it), else by the brain's (INV_PHASE_S from the phase's
        start)."""
        left = snap.time_left
        return (left is not None and left <= INV_LAST_S) or snap.inv_phase_t >= INV_PHASE_S - INV_LAST_S

    @staticmethod
    def overtime(snap):
        """Invasion's overtime (the game's clock at 0, the phase still on: it lasts only while an attacker stands in the
        territory): the attack is every second, no gathering and no pause between pushes (blitz_tick)."""
        return snap.mode == "invasion" and snap.time_left is not None and snap.time_left <= 0.5

    def blitz_target(s, snap, c):
        """The objective a blitz goes at: straight_objective's, but in Assault and Stockpile the nearest one we may
        take (Bot.loose_point; the first listed was theirs, or a flag already in our goal)."""
        if snap.mode in ("assault", "stockpile"):
            return Bot.loose_point(PlayerState(-1, s.team, "", c), snap) if c is not None else None
        return s.straight_objective(snap, c)

    def blitz_holds(s, snap, team):
        """Who stays back in a blitz, {bot id: post}: in Stockpile the two nearest our goal while a flag lies in it
        (the enemy takes them from there)."""
        goal = next(iter(snap.obj_goals.get(s.team) or []), None) if snap.mode == "stockpile" else None
        if goal is None or not any(it["carrier"] is None and dist(it["pos"], goal) < 2.0 for it in snap.obj_items or []):
            return {}
        near = sorted(team, key=lambda b: dist(snap.player(b.id).pos, goal))[:2]
        return {b.id: s.spread(goal, k, 3.0) for k, b in enumerate(near)}

    def blitz_team(s, snap):
        """Who goes: every bot that plays for the team (not Easy), alive, on foot, not carrying, not on its way to a
        vehicle's seat (a gun, a seat, a driver's job: vehicle_orders, which the blitz no longer shuts out)."""
        out = []
        for b in s.bots.values():
            p = snap.player(b.id)
            if (p is not None and p.alive and not p.has_flag and p.vehicle in (None, -1) and b.p.teamwork > 0
                    and b.order.role not in ("ride", "board", "drive")):
                out.append(b)
        return out

    def blitz_tick(s, now, snap):
        """The team's blitz: when desperate, the team (blitz_team) rallies BLITZ_RALLY_D short of the objective on its own
        side, BLITZ_GATHER_S at most or until BLITZ_READY of it is there (none when it is that near already), then all
        go in at once, half by each of two prongs (blitz_prongs), BLITZ_GO_S at most, each with a core rush's urgency
        (Bot.blitz_until: keep_role). Over when the danger is, when the objective moved on, or at the time; then
        BLITZ_COOL_S of the normal plan."""
        bz = getattr(s, "blitz", None)
        want = s.desperate(now, snap)
        if bz is not None:
            if want is not None and want[1] == bz["why"]:
                bz["target"] = want[0]            # (the same job, where it is now: the ball's carrier, the next territory)
            if want is None or want[1] != bz["why"] or (now - bz["t0"] > BLITZ_GATHER_S + BLITZ_GO_S and not s.overtime(snap)):
                s.blitz, s.blitz_cool, s.next_roles = None, now + BLITZ_COOL_S, now
                for b in s.bots.values():
                    b.blitz_until = 0.0
                s.event(now, "blitz", "blitz over")
                return
        else:
            # (in overtime no pause between pushes: match 214711's 15 s cool-downs and 4 s rallies there, 243-353 s,
            # each left the territory to its defenders, and the round ended on one)
            ot = s.overtime(snap)
            if want is None or (now < getattr(s, "blitz_cool", 0.0) and not ot):
                return
            team = s.blitz_team(snap)
            if len(team) < 2:
                return
            target, why = want
            pos = [snap.player(b.id).pos for b in team]
            c = Vec(sum(q.x for q in pos) / len(pos), sum(q.y for q in pos) / len(pos), sum(q.z for q in pos) / len(pos))
            rally = s.blitz_rally(c, target)
            # a rally only for a team strung out (one BLITZ_SPREAD from the rest: respawned, far behind); together it
            # goes at once (the sim, Spire phase 3: a 6 s rally of a team already together cut pickups 6 of 6 -> 3 of 6)
            # (the infected gather unless already together: from 25 u apart they came in one at a time, issue #3)
            spread = INF_SPREAD if snap.mode == "infection" else BLITZ_SPREAD
            near = ot or (c - target).flat() < BLITZ_RALLY_D + 6.0 or max((q - c).flat() for q in pos) < spread
            bz = s.blitz = dict(t0=now, target=target, rally=rally, why=why, go=now if near else None,
                                prongs=s.blitz_prongs(rally, target))
            s.event(now, "blitz", f"blitz ({why}): {'go' if near else 'rally'}")
        team = sorted(s.blitz_team(snap), key=lambda b: b.id)
        bz["ids"] = {b.id for b in team}
        hold = s.blitz_holds(snap, team)
        for b in team:
            if b.id in hold:
                b.set_order(Order("defender", hold[b.id]), sure=True)
                s.roles[b.id] = "defender"
        goers = [b for b in team if b.id not in hold]
        ahead = dist(bz["rally"], bz["target"]) + 2.0
        if bz["go"] is None:
            at = sum(1 for b in goers if dist(snap.player(b.id).pos, bz["rally"]) < 8.0
                     or dist(snap.player(b.id).pos, bz["target"]) <= ahead)
            if now - bz["t0"] >= (INF_GATHER_S if snap.mode == "infection" else BLITZ_GATHER_S) or \
                    at >= BLITZ_READY * len(goers):
                bz["go"] = now
                s.event(now, "blitz", "blitz: go")
        role, used, climbs_used = s.blitz_role(snap), {}, {}
        # (Invasion phase 3, attacking a core on high: the goers spread over its ways up as the normal plan's runners do,
        # climb_via. The blitz gave them none, the nav's cheapest each: live Spire 20261106-225937, the Spartans in a
        # blitz 89% of phase 3, 24 climbs by lift 1, 8 by lift 2, 1 by a man cannon)
        climbing = role == "runner" and snap.mode == "invasion" and snap.inv_phase == 3 and snap.inv_attackers == s.team
        held = s.regather(now, snap, bz, goers) if bz["go"] is not None else {}
        for b in goers:
            # (one already nearer the objective than the rally is in: never called back to gather. The sim, Spire
            # phase 3: each wave's rally took the attackers on the top back down to the foot, pickups 6 of 6 -> 1 of 6)
            if bz["go"] is None and dist(snap.player(b.id).pos, bz["target"]) > ahead:
                b.set_order(Order("defender", bz["rally"]), sure=True)
                s.roles[b.id] = "defender"
            elif b.id in held:
                b.set_order(Order("defender", held[b.id]), sure=True)
                s.roles[b.id] = "defender"
            else:
                via = (s.climb_via(b, snap, bz["target"], climbs_used) if climbing else ()) or \
                    s.prong_via(b, snap, bz["target"], bz["prongs"], used)
                b.set_order(Order(role, bz["target"], via=via), sure=True)
                s.roles[b.id] = role
            b.blitz_until = now + 0.5             # (refreshed each tick while the blitz lasts)

    def core_wave_tick(s, now, snap):
        """The core's waves (regather) when no blitz runs: the normal plan's runners (invasion_slots, the whole team on
        the core) wait for their wave at the regather point too."""
        if getattr(s, "blitz", None) is not None or not (snap.mode == "invasion" and snap.inv_phase == 3
                                                          and snap.inv_core is not None and snap.inv_core_carrier is None):
            s.core_wave = None
            return
        cw = getattr(s, "core_wave", None)
        if cw is None or dist(cw["target"], snap.inv_core) > 3.0:
            cw = s.core_wave = dict(target=snap.inv_core)
        goers = [b for b in s.blitz_team(snap) if s.roles.get(b.id) == "runner" or b.id in cw.get("waits", {})]
        for bid, pt in s.regather(now, snap, cw, goers).items():
            b = s.bots[bid]
            b.set_order(Order("defender", pt), sure=True)
            s.roles[bid] = "defender"

    def regather(s, now, snap, bz, goers):
        """Invasion phase 3, the core loose or on its stand, the blitz going: a goer coming from its respawn (farther than
        REGATHER_D from the core) waits at the regather point REGATHER_D short of it toward the team until REGATHER_N of
        the goers are there or REGATHER_S s, then all of them go in together. Live Boneyard B14 / B18: the blitz went at
        the phase's start and every respawned attacker went in alone from 50 u: 34 deaths in 248 s, the median 13 u from
        the core, 37 s a life, no pickup, the defenders 136-155 bot-s on the core. {bot id: where it waits}."""
        if not (snap.mode == "invasion" and snap.inv_phase == 3 and snap.inv_core is not None
                and snap.inv_core_carrier is None and not snap.inv_armed and snap.inv_attackers == s.team):
            return {}
        target = bz["target"]
        if "regather" not in bz:
            pos = [snap.player(b.id).pos for b in goers] or [target]
            c = Vec(sum(q.x for q in pos) / len(pos), sum(q.y for q in pos) / len(pos), sum(q.z for q in pos) / len(pos))
            bz["regather"], bz["waits"] = s.blitz_rally(c, target, REGATHER_D), {}
        pt, waits = bz["regather"], bz["waits"]
        alive = {b.id for b in goers}
        for k in [k for k in waits if k not in alive]:
            del waits[k]                          # (dead: its next life regathers again)
        at = [b for b in goers if dist(snap.player(b.id).pos, pt) < 8.0]
        out = {}
        for b in goers:
            d = dist(snap.player(b.id).pos, target)
            w = waits.get(b.id)
            if d <= REGATHER_D - 4.0 and w is None:
                waits[b.id] = -1.0               # in already (it never came from behind): it goes on
                continue
            if w is None:
                w = waits[b.id] = now
            if w < 0:
                continue                          # released: in with its wave
            if len(at) >= min(REGATHER_N, len(goers)) or now - w >= REGATHER_S:
                for g in goers:                   # the wave goes: everyone waiting goes with it
                    if waits.get(g.id, -1.0) >= 0:
                        waits[g.id] = -1.0
                s.event(now, "blitz", f"core wave: go ({len(at)} at the regather point)")
                return {}
            out[b.id] = pt
        return out

    @staticmethod
    def prong_via(b, snap, target, prongs, used):
        """A goer's prong for a blitz or a wave: the one it has for the whole push (a new goer the less used one; used:
        {prong: goers on it}), none once it is nearer the target than the prong (Bot.objective_point passes it then). By
        its place in the list the prong changed as men died or held, every change sent the bot back out to the other
        one: live Spire 20261105-011146, the core loose 200 s, the attackers' choices 17,400 on the two prongs 10 u off
        it against 9,400 on it, no pickup."""
        if not prongs:
            return ()
        had = getattr(b, "prong", None)
        p = had if had in prongs else min(prongs, key=lambda q: used.get(q, 0))
        if p is not had:
            b.prong_passed = False
        b.prong = p
        used[p] = used.get(p, 0) + 1
        me = snap.player(b.id)
        # (passed once, never given back this push: a prong on the floor under Boneyard's territories, the way up from
        # it leads away from the target first and the prong came back, the bot sent down again; live 20261105-014814)
        if me is None or b.prong_passed or dist(me.pos, target) <= dist(p, target) or dist(me.pos, p) < 5.0:
            b.prong_passed = me is not None
            return ()
        return (p,)

    def wave_tick(s, now, snap):
        """CTF's attack as a wave, the normal plan (wave 2: the sim's runners on The Pit died one by one 6-18 u from the
        stand, 50 lives in 200 s, none within 5 u; carries died at the stand with 6-7 of theirs within 15 u and none of
        ours within 10): with their flag home and none of ours carrying, the attackers (runners, escorts, pushers)
        gather WAVE_GATHER_S at most at the blitz's rally short of their base (blitz_rally), then all go in together,
        each by one of two prongs, with the blitz's urgency (Bot.blitz_until), WAVE_GO_S at most. Over at the pickup
        (the carry play takes over), when the flag is not home, or at the time; WAVE_COOL_S before the next. The
        defenders stay home. Not while a blitz runs."""
        w = getattr(s, "wave", None)
        theirs = (snap.flags or {}).get(1 - s.side) if snap.mode == "ctf" else None
        carrying = any(p.team == s.team and p.alive and p.has_flag for p in snap.players)
        live = WAVE and theirs is not None and theirs.state == "home" and not carrying and getattr(s, "blitz", None) is None
        if w is not None and (not live or now - w["t0"] > WAVE_GATHER_S + WAVE_GO_S):
            for b in s.bots.values():
                if b.id in w.get("ids", ()):
                    b.blitz_until = 0.0
            s.wave, s.wave_cool, s.next_roles = None, now + WAVE_COOL_S, now
            return
        if not live or (w is None and now < getattr(s, "wave_cool", 0.0)):
            return
        # (whoever the team's plan makes an attacker this cycle: a bot it moves to a defender's post drops out, so
        # home is held as before)
        team = [b for b in s.blitz_team(snap) if s.roles.get(b.id) in ("runner", "escort", "mid")]
        if w is None:
            if len(team) < 2:
                return
            pos = [snap.player(b.id).pos for b in team]
            c = Vec(sum(q.x for q in pos) / len(pos), sum(q.y for q in pos) / len(pos), sum(q.z for q in pos) / len(pos))
            rally = s.blitz_rally(c, theirs.pos)
            near = (c - theirs.pos).flat() < BLITZ_RALLY_D + 6.0
            w = s.wave = dict(t0=now, rally=rally, target=theirs.pos, go=now if near else None,
                              prongs=s.blitz_prongs(rally, theirs.pos))
            s.event(now, "wave", f"attack wave: {'go' if near else 'gather'}")
        team = sorted(team, key=lambda b: b.id)
        w["ids"] = {b.id for b in team}
        ahead = dist(w["rally"], w["target"]) + 2.0
        if w["go"] is None:
            at = sum(1 for b in team if dist(snap.player(b.id).pos, w["rally"]) < 8.0
                     or dist(snap.player(b.id).pos, w["target"]) <= ahead)
            if now - w["t0"] >= WAVE_GATHER_S or at >= BLITZ_READY * len(team):
                w["go"] = now
                s.event(now, "wave", "attack wave: go")
        if w["go"] is None:
            for b in team:                      # gathering: to the rally, one already nearer stays where it is
                if dist(snap.player(b.id).pos, w["target"]) > ahead:
                    b.set_order(Order("mid", w["rally"]))
                    if b.order.role == "mid":
                        s.roles[b.id] = "mid"
            return
        used = {}
        for b in team:
            via = s.prong_via(b, snap, w["target"], w["prongs"], used)
            b.set_order(Order("runner", w["target"], via=via))
            if b.order.role == "runner":
                s.roles[b.id] = "runner"
                b.blitz_until = now + 0.5

    @staticmethod
    def blitz_role(snap):
        """The role that does the objective at the target: take it (a flag, a bomb, the core) or stand in it (the hill,
        a drop point, a territory)."""
        if snap.mode in ("ctf", "assault", "stockpile") or (snap.mode == "invasion" and snap.inv_phase == 3):
            return "runner"
        if snap.mode == "infection":
            return "hunter"                       # (the infected's charge: at them, not a post among them)
        return "defender"

    def blitz_rally(s, c, target, d=BLITZ_RALLY_D):
        """Where the team gathers: BLITZ_RALLY_D short of the target toward the team, on the team's own floor (a target
        on a tower's top: at its foot, by the ways up), the nearest floor anyone can stand on."""
        v = Vec(c.x - target.x, c.y - target.y, 0.0)
        n = v.flat()
        x, y = (target.x + v.x / n * d, target.y + v.y / n * d) if n > 1e-6 else (c.x, c.y)
        z = c.z if target.z - c.z > 6.0 else target.z
        return s.floor_near(Vec(x, y, z))

    def floor_near(s, p):
        """The nearest floor anyone can reach to p (maps.py's snap), or p outside the nav."""
        T = s.terrain()
        if not T.inside(p.x, p.y):
            return p
        l, j, i = T._node(p)
        return T._center(*T._reachable_node(l, j, i, p.z))

    def push_lanes(s, snap, target):
        """The attack's ways into an Invasion territory: the straight way, and a flank either side, a point LANE_R from the
        territory LANE_ANGLE off the team's line in, on a floor the team reaches, the way round at most BLITZ_DETOUR of
        the straight one. Each attacker takes one in turn (assign_roles). Kept LANE_KEEP_S for a territory; alone with
        the team at it already or above it (Spire's core: blitz_prongs)."""
        team = [p for p in (snap.player(b.id) for b in s.bots.values()) if p is not None and p.alive]
        if not team:
            return [()]
        c = Vec(sum(p.pos.x for p in team) / len(team), sum(p.pos.y for p in team) / len(team),
                sum(p.pos.z for p in team) / len(team))
        straight = (c - target).flat()
        if straight < LANE_R + 4.0 or target.z - c.z > 8.0:
            return [()]
        key = (round(target.x, 1), round(target.y, 1))
        kept = getattr(s, "_lanes", None)
        if kept is not None and kept[0] == key and snap.time - kept[1] < LANE_KEEP_S:
            return kept[2]
        T, base, lanes = s.terrain(), math.atan2(c.y - target.y, c.x - target.x), [()]
        for sgn in (1, -1):
            a = base + sgn * LANE_ANGLE
            q = s.floor_near(Vec(target.x + math.cos(a) * LANE_R, target.y + math.sin(a) * LANE_R, target.z))
            if (abs(q.z - target.z) < 4.0 and dist(c, q) + dist(q, target) <= BLITZ_DETOUR * straight
                    and T.inside(q.x, q.y) and T.reaches(c, q)):
                lanes.append((q,))
        s._lanes = (key, snap.time, lanes)
        return lanes

    def blitz_prongs(s, rally, target):
        """Two ways in, half the team by each: two points 8 u to either side of the line, 60% of the way in (prong_pair:
        not a long way round). () when there are none, and for a target well above the rally (Spire's core): the nav's
        own choice of its ways up already spreads the team (launches priced by time aloft), and a via forced every
        bot up the middle lift into its defenders (the sim, Spire phase 3: pickups 6 of 6 -> 2 of 6)."""
        if target.z - rally.z > 8.0:
            return ()
        d = Vec(target.x - rally.x, target.y - rally.y, 0.0)
        n = d.flat()
        if n < 4.0:
            return ()
        mid = Vec(rally.x + d.x * 0.6, rally.y + d.y * 0.6, rally.z)
        side = Vec(-d.y / n * 8.0, d.x / n * 8.0, 0.0)
        a, b = (s.floor_near(Vec(mid.x + side.x * k, mid.y + side.y * k, mid.z)) for k in (1, -1))
        return s.prong_pair(rally, target, a, b, s.nav_way(rally, target))

    def nav_way(s, rally, target):
        """way(q): the walk rally -> q -> target by the nav's costs (people's jumps and routes on, as bots go), or None
        outside the nav (prong_pair then goes by straight lines)."""
        T = s.terrain()
        if not all(T.inside(p.x, p.y) for p in (rally, target)):
            return None
        to_target = T._field(target, human=True)
        from_rally = T._field(rally, human=True)          # (rally -> q = q -> rally: the walking graph is near symmetric)
        return lambda q: float(from_rally[T._node(q)] + to_target[T._node(q)]) if T.inside(q.x, q.y) else math.inf

    @staticmethod
    def prong_pair(rally, target, a, b, way=None):
        """Both prongs when the longer way (rally -> prong -> target) is at most BLITZ_DETOUR times the shorter, else the
        shorter alone (the sim, Spire phase 3 when its ways up were prongs: half the team sent the long way round by the
        middle cannon, pickups 6 of 6 -> 4 of 6). way: the nav's (nav_way); a prong whose way is over PRONG_NAV_DETOUR
        times the nav's own from the rally is none: one on another level (Boneyard, a rally on phase 1's platform, a
        prong 6 u under it on the floor: 110 against 20, live 20261105-022641 attackers' near time spent down there) or
        behind a wall or a gate (914: through the laser gate)."""
        if way is None:
            way = lambda q: dist(rally, q) + dist(q, target)
        else:
            best = way(rally)
            a, b = (q if way(q) <= PRONG_NAV_DETOUR * best else None for q in (a, b))
            if a is None or b is None:
                return tuple(q for q in (a, b) if q is not None)
        short, long_ = sorted((a, b), key=way)
        return (short, long_) if way(long_) <= BLITZ_DETOUR * way(short) else (short,)

    def power_runs(s, now, snap):
        """A power weapon lying loose (the map's items of value 0.8 or more: the sniper, the rockets) gets one fetcher on
        the team: highest-priority eligible difficulty, then nearest, holding none (40 u normally, 80 Legendary/Demon).
        Not the carrier, not a man in a vehicle,
        not Easy (no plans), not a defender while the core is at stake (Bot.urgent). Bot.fetch = (where, name, until);
        dropped once it is gone from there or the time is up."""
        power = {it["name"] for it in s.map.get("items", []) if it["kind"] == "weapon" and it["value"] >= 0.8}
        power |= set(s.map.get("ordnance_power", ()))   # (custom: Halo 4's random drops, maps.ordnance_power)
        lying = [(n, q) for n, q in (snap.ground_weapons or ()) if n in power]
        # ... and its spawn when the team's timer has it coming back within POWER_EARLY s. Only a known timer: item_up 0
        # is "never seen taken", not "up" (it sent the bot whose sniper had just been taken straight back to its spawn,
        # tools/test_invasion_pileon.py 9); a gun lying on its spawn is a loose gun above
        due = {}
        for i, it in enumerate(s.map.get("items", [])):
            back = s.item_up.get(i, 0.0)
            if (it["kind"] == "weapon" and it["value"] >= 0.8 and back > 0.0 and back - POWER_EARLY <= now < back + POWER_WAIT
                    and not any(dist(q, it["pos"]) < 1.5 for _, q in lying)):
                due[i] = (it["name"], it["pos"], back + POWER_WAIT)
        # (custom, Nov 8) a fixed Legendary or Demon with a power vehicle's job (crew_orders) is sent on no weapon run: the
        # vehicle comes first
        kinds = {v["handle"]: v["kind"] for v in snap.vehicles}
        driving = {cb for h, (cb, _t) in getattr(s, "crews", {}).items()
                   if h in kinds and s.power_kind(kinds[h]) and cb in s.bots and profiles.fixed_high(s.bots[cb].p)}
        for b in s.bots.values():
            f = getattr(b, "fetch", None)
            if f is None:
                continue
            spawn = len(f) > 3 and f[3] is not None
            p = snap.player(b.id)
            if b.id in driving or now >= f[2] or (spawn and f[3] not in due) or (not spawn and not any(
                    n == f[1] and dist(q, f[0]) < 1.5 for n, q in lying)) or (
                    p is not None and b.pressing(p, snap) and not s.press_fetch_ok(p, f[0], snap)):
                b.fetch = None
        targets = [(n, q, now + 25.0, None) for n, q in lying] + [(n, q, until, i) for i, (n, q, until) in due.items()]
        for n, q, until, spawn in targets:
            timed = spawn is not None             # (a spawn's timer is map knowledge: Heroic and up, map_iq 0.7+)
            if any(getattr(b, "fetch", None) is not None and dist(b.fetch[0], q) < 1.5 for b in s.bots.values()):
                continue
            near = []
            for b in s.bots.values():
                p = snap.player(b.id)
                if (p is None or not p.alive or p.has_flag or p.vehicle not in (None, -1) or b.p.teamwork <= 0
                        or getattr(b, "fetch", None) is not None or b.id in driving
                        or any(w in power for w in p.weapons) or p.weapon in power or b.urgent(p, snap)
                        or (timed and b.p.map_iq < 0.6)):
                    continue
                if b.pressing(p, snap) and not s.press_fetch_ok(p, q, snap):
                    continue
                fixed_high = profiles.fixed_high(b.p)
                radius = LEGENDARY_POWER_RUN_R if fixed_high else POWER_RUN_R
                distance = dist(p.pos, q)
                if distance < radius and abs(p.pos.z - q.z) < 6.0:
                    if fixed_high and not s.fetch_reachable(p.pos, q):
                        continue        # (custom) no run at a gun it has no way to: it stood under it
                    near.append((distance, b, fixed_high))
            if near:
                distance, fetcher, fixed_high = min(near, key=lambda x: (profiles.resource_priority(x[1].p), x[0]))
                if fixed_high and spawn is None:
                    # Use the pickup ETA's nominal walking speed plus a travel margin.
                    # Farther calls must not expire after 25 s before the bot can arrive.
                    until = max(until, now + distance / 2.3 + 10.0)
                fetcher.fetch = (q, n, until, spawn)

    def fetch_reachable(s, a, q):
        """(Custom: fixed Legendary and Demon fetchers.) A way from a to the gun at q by the nav, people's jumps and rides
        included (Terrain.reaches human=True, as a bot that jumps walks). Live Headlong 20261107-032305: of 282 Demon
        runs 25 got the gun; 83 times a Demon stood 2+ u under its gun, 20 of them under rockets no spawn reaches. No
        terrain (a test's bare director): no check."""
        try:
            T = s.terrain()
        except Exception:
            return True
        try:
            return not T.inside(q.x, q.y) or bool(T.reaches(a, q, human=True))
        except Exception:
            return True

    def press_fetch_ok(s, p, q, snap):
        """May an attacker on the clock (Bot.pressing) go for a power weapon at q? Only one right by it (POWER_PRESS_R) or
        on its way to the objective (POWER_DETOUR more than the straight way), and never in the phase's last minute, its
        overtime or a blitz (runs 56 u off the way took 48% of the attackers' choices at 300-320 s, overtime, and the
        phase was lost; match 221404: "No spartans have made an attempt to grab this sniper?", a sniper 5 u off the
        way)."""
        if s.inv_late(snap) or getattr(s, "blitz", None) is not None:
            return False
        if dist(p.pos, q) <= POWER_PRESS_R:
            return True
        goal = getattr(s, "inv_target", None) or (snap.inv_core if snap.inv_phase == 3 else None) or \
            next(iter(snap.inv_zones or []), None)
        return goal is not None and dist(p.pos, q) + dist(q, goal) - dist(p.pos, goal) <= POWER_DETOUR

    def assign_roles(s, now, snap):
        alive = [b for b in s.bots.values() if snap.player(b.id).alive]
        bz = getattr(s, "blitz", None)
        blitzing = []
        if bz is not None:                       # (the blitz's own orders: blitz_tick)
            blitzing = [b for b in alive if b.id in bz.get("ids", ())]
            alive = [b for b in alive if b.id not in bz.get("ids", ())]
        # Easy plays for itself: no place in the team's plan or the commander's orders. Slayer: it wanders the
        # map; objective games: straight at the objective (a flag carrier still runs home, below)
        # (Firefight: every teammate goes with the person, Easy too: they follow the player around)
        for b in [b for b in alive if b.p.teamwork <= 0 and not snap.player(b.id).has_flag and snap.mode != "firefight"]:
            alive.remove(b)
            point = s.straight_objective(snap, snap.player(b.id).pos)
            s.roles[b.id] = "runner" if point is not None else "free"
            b.order, b.via_left = (Order("runner", point) if point is not None else Order("free")), []
        if not alive:
            s.power_runs(now, snap)
            if blitzing:                         # (the whole team in the blitz: its vehicles still get their crews)
                s.vehicle_orders(now, snap, blitzing)
            return
        slots = s.role_slots(now, snap, len(alive))
        free = list(alive)
        carrier = next((b for b in alive if snap.player(b.id).has_flag), None)
        if carrier:   # the carrier always runs home; no rogue moments with the flag
            free.remove(carrier)
            s.roles[carrier.id] = "runner"
            home = s.carry_point(snap)
            # map brain MAP-09 (every CTF return route is a lane): home by the lane the threat map rates safest
            # (pick_route, the other way), kept while home stays put; it ran home straight, back through the fight it
            # took the flag out of
            if snap.mode != "ctf" or carrier.order.point != home or not carrier.order.via:
                via = s.pick_route(now, carrier, [], home=True) if snap.mode == "ctf" else ()
                carrier.order, carrier.via_left = Order("runner", home, via=via), list(via)
            slots = [sl for sl in slots if not (sl[0] == "runner" and sl[1] == s.capture_point(snap))]
        for b, zone in s.hh_bankers(now, snap, free):
            # (custom, Nov 12) Headhunter: a bot carrying skulls enough to bank runs them to the drop point, as a carrier
            # runs home: no rogue moment (brain/headhunter.should_bank)
            free.remove(b)
            s.roles[b.id] = "runner"
            if b.order.role != "runner" or b.order.point != zone:
                b.order, b.via_left = Order("runner", zone), []
                s.event(now, "objective", f"{snap.player(b.id).name}: banking "
                                          f"{snap.skulls_held.get(b.id, 0)} skulls")
        vip = next((v for v in snap.vips if snap.player(v) is not None and snap.player(v).team == s.team), None)
        vb = next((b for b in free if b.id == vip), None)
        if vb is not None:     # our VIP (a bot): its own play, never an escort of itself
            free.remove(vb)
            s.roles[vb.id] = "free"
            vb.set_order(Order("free"))
        used = []
        runner = None             # the bot that took the first runner slot: no-carrier escorts go with it
        runners, escorts = [], 0
        lanes, lane_k = None, 0   # an Invasion push's ways in (push_lanes)
        climbs_used = {}          # an Invasion core on high: runners per way up this pass (climb_via)
        # (phase 1 the straight rush, phase 2 the flanks from its start: the sim, Spire 6 seeds, flanks in both phases
        # took phase 2 in 4 of 6 against 1 of 6 without, but phase 1's median 48 -> 94 s; flanks only after 45 s did
        # nothing, the team was already inside the flank points by then)
        pushing = (snap.mode == "invasion" and snap.inv_attackers == s.team and snap.inv_phase in LANE_PHASES
                   and getattr(s, "inv_target", None) is not None)
        high_alt = getattr(s, "high_alt", {}) if snap.mode == "slayer" else {}
        for slot_i, (role, point, fit) in enumerate(slots):
            if not free:
                break

            def cost(b):
                pos = snap.player(b.id).pos
                c = dist(pos, point) / 30.0
                c += 0.0 if s.roles.get(b.id) == role else 0.5      # role inertia
                if fit == "anchor":
                    priority = 0 if profiles.fixed_demon(b.p) else {"camper": 1, "sniper": 2}.get(b.p.personality, 3)
                    return priority, c
                if fit == "low_tier":   # (custom) CTF's one defender: the lowest difficulty, not Easy; then the nearest
                    return profiles.defend_priority(b.p), c
                if isinstance(fit, tuple):   # (custom) a CTF cut-off worked out for one bot (intercepts): it, else the nearest
                    return (0 if b.id == fit[1] else 1), c
                c -= 0.8 * getattr(b.p, fit, 0.5)                    # personality fit
                return c
            b = min(free, key=cost)
            free.remove(b)
            if slot_i in high_alt and profiles.high_ground(b.p):
                # (custom, Nov 10) Team Slayer's support or sweep, Legendary / Blind / Scaling / Demon: its high spot,
                # held (Bot.slayer_post). Heroic and below keep the upstream hunt
                role, point = "mid", high_alt[slot_i]
            s.roles[b.id] = role
            via = ()
            if role == "runner" and point != s.capture_point(snap) and snap.mode == "ctf":
                if b.order.role == "runner" and b.order.via:
                    via = b.order.via           # keep the route it already took
                else:
                    via = s.pick_route(now, b, used)
                used.append(via)
            elif pushing and role in ("defender", "escort", "mid") and point is not None and \
                    dist(point, s.inv_target) < LANE_NEAR:
                lanes = lanes if lanes is not None else s.push_lanes(snap, s.inv_target)
                # (one kept while its lanes stand: a new pick every role pass turned bots round mid-way)
                via = b.order.via if b.order.via and b.order.via in lanes else lanes[lane_k % len(lanes)]
                lane_k += 1
            elif role == "runner" and point is not None and snap.mode == "invasion" and snap.inv_attackers == s.team \
                    and snap.inv_phase == 3:
                via = s.climb_via(b, snap, point, climbs_used)
            if role == "runner" and runner is None:
                runner = b.id
            if role == "runner":
                runners.append(b.id)
            if role == "escort" and not carrier and vip is None and getattr(s, "split", False) and runners:
                runner = runners[escorts % len(runners)]      # a split attack: each runner its own escort
                escorts += 1
            holder = carrier.id if carrier else next(
                (p.id for p in snap.players if p.team == s.team and p.has_flag and p.alive), None)   # a person too
            lead = (holder if holder is not None else vip if vip is not None else
                    getattr(s, "ff_lead", None) if snap.mode == "firefight" else runner) if role == "escort" else None
            o = Order(role, point, via=via, target=-1 if lead is None else lead)
            if snap.mode == "firefight":    # the person's teammates: no rogue rounds off on their own, Easy too
                b.via_left = list(o.via) if o.role != b.order.role or o.via != b.order.via else b.via_left
                b.order = o
            else:
                b.set_order(o, sure=fit == "anchor")
            if role == "cutoff":
                s.__dict__.setdefault("_cuts", {})[b.id] = point   # (kept while it still beats him there: intercepts)
        for b in free:
            s.roles[b.id] = "free"
            b.set_order(Order("free"))
        s.backup_orders(now, snap, alive)
        # Reserve weapon fetchers before any new vehicle/gunner calls.
        s.power_runs(now, snap)        # every mode, as before
        # the blitz's goers too: a landed aircraft's or a horn's call, a power vehicle's driver, a gun. Shut out, the whole
        # team in a blitz left a person's landed Falcon unmanned 24 s with five of them 4-12 u off, a bot's Falcon took off
        # gunnerless and an empty Banshee stood 79 s (live Spire 20261106-225937). Called, one leaves the blitz
        # (blitz_team: not while on its way to a seat)
        s.vehicle_orders(now, snap, alive + blitzing)
        s.infantry_patrol_orders(now, snap, alive)
        s.pair_orders(now, snap, alive)

    def hh_bankers(s, now, snap, free):
        """(custom, Nov 12) Headhunter: [(bot, drop point)] the bots of free carrying skulls enough to bank them now
        (headhunter.should_bank: 5 always, 3 within 45 u of the drop point, 1 within 12 u, or enough to win)."""
        from .headhunter import should_bank
        hh = getattr(snap, "hh", None)
        if snap.mode != "headhunter" or hh is None:
            return []
        need = None
        if snap.score_limit and s.team in (snap.score or {}):
            need = snap.score_limit - snap.score[s.team]
        out = []
        for b in free:
            p = snap.player(b.id)
            n = snap.skulls_held.get(b.id, 0)
            zone = hh.bank_zone(p.pos, now) if p is not None and n > 0 else None
            if zone is not None and should_bank(n, dist(p.pos, zone), need):
                out.append((b, zone))
        return out

    PAIR_ROLES = ("mid", "hunter", "free")   # (custom) the Slayer jobs a Demon's partner shares (pair_orders)
    PAIR_GAP = 3.0                           # u: the partner's spot off the lead's point (spread's ring)

    def demon_pairs(s, alive):
        """(custom) Team Slayer: each fixed Demon with a partner, (lead, mate): another Demon first, else a fixed
        Legendary; the pairs kept while both live (the lower id of two Demons leads). The owner's ask, Nov 8: a Demon
        and a Legendary, or two Demons, in a party of two, on the same routes and patrols (live Blood Crash
        20261108-024522: its two Demons within 8 u of each other 18% of the match, median 17.6 u apart)."""
        ids = {b.id: b for b in alive}
        kept = [(a, m) for a, m in getattr(s, "pairs", ()) if a in ids and m in ids
                and profiles.fixed_demon(ids[a].p) and profiles.fixed_high(ids[m].p)]
        used = {k for pair in kept for k in pair}
        free = lambda b: b.id not in used
        demons = sorted((b for b in alive if profiles.fixed_demon(b.p) and free(b)), key=lambda b: b.id)
        legends = sorted((b for b in alive if profiles.fixed_high(b.p) and not profiles.fixed_demon(b.p) and free(b)),
                         key=lambda b: b.id)
        while demons:
            lead = demons.pop(0)
            mate = demons.pop(0) if demons else legends.pop(0) if legends else None
            if mate is not None:
                kept.append((lead.id, mate.id))
        s.pairs = kept
        return [(ids[a], ids[m]) for a, m in kept]

    def pair_orders(s, now, snap, alive):
        """(custom) Team Slayer pairs (demon_pairs): the mate takes its lead's job, its point PAIR_GAP off the lead's
        (spread) by the same way (via), and the lead's patrol (infantry_patrol_orders), sure (set_order: no rogue moment).
        Not while either rides, carries, is on a power run, or the lead's job is another (a vehicle's, an objective's);
        a mate with a patrol its lead has not leaves it (it walked off alone)."""
        if snap.mode != "slayer":
            return
        for lead, mate in s.demon_pairs(alive):
            lp, mp = snap.player(lead.id), snap.player(mate.id)
            if (lp is None or mp is None or lp.vehicle not in (None, -1) or mp.vehicle not in (None, -1)
                    or lp.has_flag or mp.has_flag or getattr(lead, "fetch", None) is not None
                    or getattr(mate, "fetch", None) is not None or lead.order.role not in s.PAIR_ROLES
                    or s.roles.get(mate.id, "free") not in s.PAIR_ROLES or lead.id in snap.vips or mate.id in snap.vips):
                continue
            o = lead.order
            point = s.spread(o.point, 1, s.PAIR_GAP) if o.point is not None else None
            mine = mate.order
            if not (mine.role == o.role and mine.via == o.via and mine.point is not None and point is not None
                    and dist(mine.point, point) < 1.0):
                mate.set_order(Order(o.role, point, via=o.via, target=o.target), sure=True)
            s.roles[mate.id] = s.roles.get(lead.id, o.role)
            patrol = getattr(lead, "infantry_patrol", None)
            if patrol is not None:
                mate.infantry_patrol = patrol
                if mate not in getattr(s, "infantry_patrollers", []):
                    s.infantry_patrollers = list(getattr(s, "infantry_patrollers", [])) + [mate]
            elif getattr(mate, "infantry_patrol", None) is not None:
                mate.infantry_patrol = None
                s.infantry_patrollers = [b for b in getattr(s, "infantry_patrollers", []) if b is not mate]

    def infantry_patrol_orders(s, now, snap, alive):
        """Send up to three available infantry bots to a lightly visited map position."""
        points = [point for point, team in s.map.get("infantry_patrols", ()) if team is None or team == s.team]
        if not points or snap.mode == "invasion":
            return
        visits = s.__dict__.setdefault("infantry_patrol_visits", {})
        for point in points:
            if any(p.alive and p.team == s.team and p.vehicle in (None, -1)
                   and dist(p.pos, point) < 4.0 for p in snap.players):
                visits[point] = now

        roles = ("free", "mid", "hunter") if snap.mode == "slayer" else ("free", "mid")

        def eligible(bot, point):
            p = snap.player(bot.id)
            order = bot.order
            # (custom, Nov 10) not a Slayer post held on high by Legendary / Blind / Scaling / Demon (Bot.slayer_post)
            if snap.mode == "slayer" and order.role == "mid" and profiles.high_ground(bot.p):
                return False
            return (s.roles.get(bot.id) in roles and order.role in roles and bot.id not in snap.vips
                    and p.vehicle in (None, -1) and not p.has_flag and getattr(bot, "fetch", None) is None
                    and (snap.mode == "slayer" or order.point is None or dist(order.point, point) <= 25.0)
                    and getattr(bot, "goal_ban", {}).get(bot._goal_key(("patrol", point)), 0) <= now)

        patrollers = []
        for bot in getattr(s, "infantry_patrollers", ()):
            point, until = bot.infantry_patrol
            if (point in points and now < until and bot in alive and eligible(bot, point)
                    and dist(snap.player(bot.id).pos, point) >= 4.0):
                patrollers.append(bot)
            else:
                if now >= until:
                    visits[point] = now
                bot.infantry_patrol = None
        s.infantry_patrollers = patrollers
        if patrollers:
            return

        for point in sorted(points, key=lambda p: visits.get(p, -math.inf)):
            if now - visits.get(point, -math.inf) < 25.0:
                continue
            # (custom) a Demon's Slayer partner takes its lead's patrol, never one of its own (pair_orders)
            mates = {m for _, m in getattr(s, "pairs", ())} if snap.mode == "slayer" else set()
            nearby = [(dist(snap.player(b.id).pos, point), b) for b in alive if eligible(b, point) and b.id not in mates]
            for distance, bot in sorted(nearby, key=lambda pair: pair[0]):
                if distance > 35.0:
                    break
                pos = snap.player(bot.id).pos
                terrain = s.terrain()
                if terrain.inside(point.x, point.y) and terrain.reaches(pos, point):
                    bot.infantry_patrol = (point, now + 40.0)
                    patrollers.append(bot)
                    # Roll once after assigning the first bot to decide whether to fill a trio.
                    if len(patrollers) == 3 or (len(patrollers) == 1 and s.rng.random() >= 0.5):
                        break
            if patrollers:
                return

    BACKUP_R, BACKUP_REACH, BACKUP_MAX = 12.0, 40.0, 3   # u: enemies this near a post we hold; helpers this far; at most
    BACKUP = True                                        # (False: the play before, for A/B)
    # where holding is the score (sim, 4v4 Legendary, 180 s games, backup on / off: Territories on Settlement 3 games,
    # points 49 / 47; Invasion on Spire 3 games the same; Assault on Settlement 6 games, bomb pickups 49 / 39 but plants
    # 3 / 7: guarded goals score less, so not in Assault, Stockpile or CTF, where the attack scores)
    BACKUP_MODES = ("territories", "king", "invasion")

    def backup_orders(s, now, snap, alive):
        """Holding with intent, in the modes where holding scores (BACKUP_MODES): a post we hold (our defenders' points: a
        territory, the hill, the core) with as many enemies seen by any of us in the last 3 s within BACKUP_R of it as
        holders there is contested: a holder calls "Need backup" (callouts kind backup) and the nearest teammates with
        no fixed job (pushers, free bots; escorts while nobody of ours carries), within BACKUP_REACH, go to it as its
        defenders, one more than the enemies outnumber us, BACKUP_MAX at most. Each cycle (2 s) while it is contested."""
        if not s.BACKUP or snap.mode not in s.BACKUP_MODES:
            return
        posts = []
        for b in alive:
            if b.order.role == "defender" and b.order.point is not None and \
                    not any(dist(b.order.point, q) < 8.0 for q in posts):
                posts.append(b.order.point)
        if not posts:
            return
        known = {}
        for b in s.bots.values():
            for k, bel in b.per.beliefs.items():
                if isinstance(k, int) and bel.seen and now - bel.t < 3.0:
                    p = snap.player(k)
                    if p is not None and p.alive and p.team != s.team:
                        known[k] = bel.pos
        carrying = any(p.team == s.team and p.alive and p.has_flag for p in snap.players)
        said = s.__dict__.setdefault("backup_said", {})
        free = [b for b in alive if s.roles.get(b.id) in (("mid", "free") if carrying else ("mid", "free", "escort"))
                and snap.player(b.id) is not None and snap.player(b.id).vehicle == -1 and not snap.player(b.id).has_flag]
        for q in posts:
            foes = [k for k, pos in known.items() if dist(pos, q) < s.BACKUP_R]
            holders = [b for b in alive if b.order.role == "defender" and b.order.point is not None
                       and dist(b.order.point, q) < 8.0 and dist(snap.player(b.id).pos, q) < s.BACKUP_R]
            if not foes or not holders or len(foes) < len(holders):
                continue
            need = min(s.BACKUP_MAX, len(foes) - len(holders) + 1)
            for b in sorted((b for b in free if dist(snap.player(b.id).pos, q) < s.BACKUP_REACH),
                            key=lambda b: dist(snap.player(b.id).pos, q))[:need]:
                b.set_order(Order("defender", q))
                if b.order.role == "defender":
                    s.roles[b.id] = "defender"
                    free.remove(b)
            key = (round(q.x), round(q.y))
            if now - said.get(key, -99.0) > 8.0:
                said[key] = now
                h = holders[0]
                s.report(now, h.id, "backup", q, count=len(foes))
                s.event(now, "backup", f"{snap.player(h.id).name}: need backup, {s.zones.name(q)} ({len(foes)} on it)")

    def vehicle_orders(s, now, snap, alive):
        """Vehicle teamwork. A vehicle of ours whose gun seat is empty (a Warthog, Falcon or Elephant with only its
        driver, a bot's or a person's): the nearest teammate on foot with no objective job within 25 u is sent to it
        ("hop on the gun"), and a bot driver waits for him. Our flag carrier on foot far from home: the nearest bot
        driving a vehicle with a free seat within 45 u picks him up and runs him home (ferry); a carrier bot within 10
        u of that vehicle gets in."""
        from . import vehicles
        if snap.mode == "infection":
            return      # survivors hold their rooms, the infected run on foot (live Rat's Nest: zombies sent to drive
                        # Mongooses 584 of 618 order rows; issue #3)
        players = {b.id: snap.player(b.id) for b in alive}
        # (our objective carrier's escorts stay on him: live Spire at 417 s four of his six escorts were sent to a
        # Warthog's gun or waited at a wheel as he dropped off the top with the core, 0 of his within 25 u)
        s.carrying = any(p.team == s.team and p.alive and p.has_flag for p in snap.players)
        foot = [b for b in alive if players[b.id] is not None and players[b.id].vehicle == -1
                and not players[b.id].has_flag and s.roles.get(b.id) not in ("runner", "defender", "ride", "board")
                and not (s.carrying and s.roles.get(b.id) == "escort")]
        # (a power vehicle by a bot on an objective job: its pool, crew_orders)
        busy = [b for b in alive if b not in foot and players[b.id] is not None and players[b.id].alive
                and players[b.id].vehicle == -1 and not players[b.id].has_flag and b.p.tier != "novice"
                and s.roles.get(b.id) not in ("ride", "board", "ferry") and not b.urgent(players[b.id], snap)]
        # (Firefight: the person's escorts stay with him, no vehicle of their own; his empty gun still calls one, below.
        # Live Beachhead s172: 3175 of their order rows "drive", to Mongooses 20-40 u off, 724 escort)
        ff = snap.mode == "firefight"
        # (custom, Nov 8) fixed Legendary and Demon riding a gun or a passenger seat: a power vehicle calls them out
        seated = [b for b in alive if players[b.id] is not None and players[b.id].alive
                  and players[b.id].vehicle not in (None, -1) and not players[b.id].has_flag
                  and profiles.fixed_high(b.p) and getattr(b, "seat", None) in ("gunner", "passenger")
                  and s.roles.get(b.id) not in ("ferry", "escort") and not b.urgent(players[b.id], snap)]
        s.crew_orders(now, snap, players, [b for b in foot if not ff or s.roles.get(b.id) != "escort"],
                      [] if ff else busy, [] if ff else seated)
        # A Demon takes an eligible power-vehicle job before an empty gun calls it.
        s.honk_orders(now, snap, alive, players)
        foot = [b for b in foot if s.roles.get(b.id) not in ("drive", "ride", "board") and s.gunner_available(b)]
        for v in snap.vehicles:
            if v.get("team") != s.team or not vehicles.needs_gunner(v, snap):
                continue
            vp = Vec(*v["pos"])
            if any(b.order.role == "ride" and b.order.target == v["handle"] for b in alive):
                continue
            near = min((b for b in foot if dist(players[b.id].pos, vp) <= 25.0),
                       key=lambda b: (profiles.gunner_priority(b.p), dist(players[b.id].pos, vp)), default=None)
            if near is None or dist(players[near.id].pos, vp) > 25.0:
                continue
            near.set_order(Order("ride", vp, target=v["handle"]))
            s.roles[near.id] = "ride"
            foot.remove(near)
            for b in alive:                      # our bot at the wheel waits for him
                if players[b.id] is not None and players[b.id].vehicle == v["handle"] and getattr(b, "seat", "") == "driver" \
                        and not (s.carrying and s.roles.get(b.id) == "escort"):
                    b.order = Order("driver_wait", vp)
            s.event(now, "vehicle", f"{players[near.id].name}: hop on the gun ({v['kind']})")
        s.wheel_calls(now, snap, alive, players)
        s.rider_calls(now, snap, alive, players)
        s.ferry_orders(now, snap, alive, players)
        s.vehicle_jobs(now, snap, alive, players)

    CALL_R, CALL_TRIP = 12.0, 25.0     # u: a teammate this near a vehicle of ours, his objective this far, is called aboard

    @staticmethod
    def gunner_available(b):
        """Do not divert Demon from a reserved weapon or vehicle to a new seat."""
        return b.order.role != "drive" and (not profiles.fixed_demon(b.p) or getattr(b, "fetch", None) is None)

    def rider_calls(s, now, snap, alive, players):
        """Drivers call riders ("this guy with the warthog has no gunner or passenger or anything",; "flagging down other
        bots to get in your warthog or on your mongoose"): a vehicle of ours with a driver (bot or person) and a seat
        free calls the bots on foot within CALL_R whose objective is CALL_TRIP or more off, runners and escorts too (hop
        on the gun took only bots with no objective job, within 25 u): the gun first, then the passenger seats, nearest
        first. A defender only onto the gun of one at his post or bound for it (a manned Warthog there is a turret: live
        Spire at 683 s, "Sentinel doesnt have a gunner on his warthog": he drove alone to the Elites' posts, every
        teammate a defender). Not our carrier (ferry), not Easy (it never plans). The driver waits for them
        (Bot.crew_coming)."""
        from . import vehicles
        called, last = s.__dict__.setdefault("aboard_calls", {}), {}   # vehicle handle -> who it called last pass
        s.aboard_calls = last
        for v in snap.vehicles:
            sp = vehicles.spec(v["kind"])
            if (v.get("team") != s.team or sp is None or sp["move"] == "none" or not v.get("riders", 0)
                    or v.get("dead") or v.get("riders", 0) >= len(sp["seats"])):
                continue
            h, vp = v["handle"], Vec(*v["pos"])
            if any(b.order.role == "ferry" and players[b.id] is not None and players[b.id].vehicle == h for b in alive):
                continue                         # (its free seat is the carrier's)
            # a transport aircraft (the Falcon: two guns) calls from farther, its gunners run in from the spawn and
            # the open ground (live Spire 352-383 s: its pilot flew 30 s alone, nobody within 12 u when he got in)
            call_r = s.CALL_R * (AIR_CALL if sp["move"] == "air" else 1.0)
            coming = [b for b in alive if b.order.target == h and b.order.role in ("ride", "board")]
            free = len(sp["seats"]) - v.get("riders", 0) - len(coming)
            if vehicles.wheel_open(v, snap):
                free -= 1                        # (custom: the empty wheel is a driver's, wheel_calls; not a passenger's)
            gun_free = vehicles.needs_gunner(v, snap) and not any(b.order.role == "ride" for b in coming)
            drv = next((b for b in alive if players[b.id] is not None and players[b.id].vehicle == h
                        and getattr(b, "seat", "") == "driver"), None)
            bound = [q for q in (vp, getattr(drv, "drive_to", None)) if q is not None]
            # (one called last pass and still on his way keeps the call, whatever his role pass made him: each pass's
            # roles reset his order, and the call again was a fresh choice, a rogue roll and the trip rule. Live Spire
            # 20261105-143525: at 1029.3 s Cyber117 took the Falcon's gun, walked to 6 u of it, and at 1033.3 s the
            # pass made him a runner 17 u from the core and nobody called him again)
            # (a bot driver's wait for them ends 6 s from the call, 12 s in an aircraft: Bot.crew_coming; then so does this)
            t_call = (getattr(drv, "called_aboard", {}).get(h) or ((), -99.0))[1] if drv is not None else now
            was = called.get(h, ()) if now - t_call < (12.0 if sp["move"] == "air" else 6.0) else ()

            # (a person at its wheel drives where they like, so a defender takes the gun wherever its post is. Live
            # Spire 20261105-201917, 113-215 s: a player drove a Warthog among the team's defenders, two of them 1-9 u
            # off it for 20 s each, posts 35-60 u away, and nobody took its empty gun; Oct 31 230307 at 354 s the same)
            person = drv is None and any(p.vehicle == h and p.alive and not p.is_bot and not getattr(p, "gunner_seat", False)
                                         for p in snap.players)

            def wanted(b):
                return b.id in was or s.rider_ok(b, players, gun_free, bound, person)
            cands = sorted((b for b in alive if b not in coming and b.p.teamwork > 0 and players[b.id] is not None
                            and players[b.id].vehicle == -1 and not players[b.id].has_flag and s.gunner_available(b)
                            and dist(players[b.id].pos, vp) < call_r and wanted(b)),
                           key=lambda b: (b.id not in was, dist(players[b.id].pos, vp)))
            while cands:
                # Keep earlier commitments; prioritize difficulty for new gun seats only.
                if gun_free:
                    b = min(cands, key=lambda b: (b.id not in was, profiles.gunner_priority(b.p),
                                                 dist(players[b.id].pos, vp)))
                    cands.remove(b)
                else:
                    b = cands.pop(0)
                if free <= 0:
                    break
                if s.roles.get(b.id) == "defender" and not gun_free and b.id not in was:
                    continue                     # (a defender rides the gun only)
                seat = "ride" if gun_free else "board" if "passenger" in sp["seats"] else None
                if seat is None:
                    break
                gun_free = gun_free and seat != "ride"
                b.set_order(Order(seat, vp, target=h), sure=b.id in was or person)   # (a person's call, as a honk)
                if b.order.role == seat:
                    s.roles[b.id], free = seat, free - 1
                    if b.id not in was:
                        s.event(now, "vehicle", f"{players[b.id].name}: called "
                                                f"{'onto the gun' if seat == 'ride' else 'aboard'} ({v['kind']})")
            # its bot driver waits for them (Bot.crew_coming), 6 s from the first call of these riders
            ids = tuple(b.id for b in alive if b.order.target == h and b.order.role in ("ride", "board"))
            last[h] = ids
            if drv is not None and ids:
                old = getattr(drv, "called_aboard", {}).get(h)
                drv.called_aboard = {h: (ids, old[1] if old and set(old[0]) >= set(ids) else now)}
                if not old or not set(old[0]) >= set(ids):     # flagging them down ("Get in, <zone>!")
                    s.report(now, drv.id, "pickup", vp, count=len(ids))
            elif drv is not None:
                # nobody coming any more: no waiting for them (the same match, 1033-1040 s: the Falcon sat 7 s more for
                # the man no longer called)
                getattr(drv, "called_aboard", {}).pop(h, None)

    WHEEL_R, WHEEL_GIVE_UP = 30.0, 15.0   # u, s: (custom) a driver for a person on a driverless gun comes from this near;
                                          # one not in it after this long is skipped for 30 s (wheel_calls)

    def wheel_calls(s, now, snap, alive, players):
        """(custom, Nov 12) A person rides the gun of a vehicle of ours with nobody at its wheel (vehicles.wheel_open):
        the bot on foot within WHEEL_R best to drive it (profiles.driver_priority: Normal and Heroic first; never a Demon
        at a Warthog's or a Mongoose's wheel) is sent to drive (Order "drive" on that vehicle, as a honk: sure). The one
        sent keeps the job while the wheel stays open, up to WHEEL_GIVE_UP s, then another is tried. Once in, he drives as
        every bot at a wheel does (vehicle_jobs). Not our flag carrier, not Easy. The owner's Blood Crash CTF report
        ("Why are they not driving me", 20261112-164125)."""
        from . import vehicles
        sent = s.__dict__.setdefault("wheel_sent", {})       # vehicle handle -> (bot id, since)
        skip = s.__dict__.setdefault("wheel_skip", {})       # (bot id, handle) -> not before
        open_now = set()
        for v in snap.vehicles:
            h = v["handle"]
            if v.get("team") != s.team or not vehicles.wheel_open(v, snap):
                continue
            if not any(p.vehicle == h and p.alive and not p.is_bot for p in snap.players):
                continue                          # (a person aboard only)
            open_now.add(h)
            vp = Vec(*v["pos"])
            bid, since = sent.get(h, (None, now))
            b = s.bots.get(bid) if bid is not None else None
            if b is not None and (b not in alive or players.get(b.id) is None or players[b.id].vehicle != -1
                                  or now - since > s.WHEEL_GIVE_UP):
                skip[(bid, h)] = now + 30.0
                b = None
            if b is None:
                cands = [x for x in alive if players.get(x.id) is not None and players[x.id].alive
                         and players[x.id].vehicle == -1 and not players[x.id].has_flag and x.p.teamwork > 0
                         and x.p.tier != "novice" and skip.get((x.id, h), 0.0) <= now
                         and s.roles.get(x.id) not in ("ferry", "ride", "board", "drive")
                         and x.may_drive(v, snap) and not x.urgent(players[x.id], snap)
                         and dist(players[x.id].pos, vp) <= s.WHEEL_R]
                b = min(cands, key=lambda x: (profiles.driver_priority(x.p), dist(players[x.id].pos, vp)), default=None)
                if b is None:
                    sent.pop(h, None)
                    continue
                since = now
                s.event(now, "vehicle", f"{players[b.id].name}: to the wheel, a teammate on the gun ({v['kind']})")
            b.set_order(Order("drive", vp, target=h), sure=True)
            s.roles[b.id] = "drive"
            sent[h] = (b.id, since)
        for h in [h for h in sent if h not in open_now]:
            del sent[h]

    def rider_ok(s, b, players, gun_free, bound, person=False):
        """A bot rider_calls may call to a vehicle whose places (where it is, where it goes) are bound. A defender only
        onto the gun of one at his post or bound for it, or of one a person drives (person); the others with a trip of
        CALL_TRIP or more (a mid by his post stays there)."""
        role = s.roles.get(b.id)
        if role == "defender":
            return gun_free and (person or b.order.point is not None and any(dist(q, b.order.point) < 15.0 for q in bound))
        return (role in ("runner", "mid", "free", "hunter") + (() if getattr(s, "carrying", False) else ("escort",))
                and (b.order.point is None or dist(players[b.id].pos, b.order.point) >= s.CALL_TRIP))

    PICKUP_R, PICKUP_WAIT = 60.0, 8.0   # u, s: a lone driver goes for a gunner this near; gives one up after waiting this long
    PICKUP_WAIT_AIR = 20.0              # s: ... an aircraft, set down by him (gunner_pickup)
    PICKUP_DETOUR = 25.0                # u: on a trip (goal), a gunner fetched only this far off its way (gunner_pickup)

    def gunner_pickup(s, now, b, me, snap, alive, players, goal=None):
        """Where a bot at the wheel of a gun vehicle with its gun seat empty and no job goes: to the nearest teammate on
        foot rider_calls would put on the gun there (live Spire 230307, 69-95 s: a defender drove his Warthog alone to
        his post for 26 s, no job, every teammate posted farther than CALL_R off it, then chased men to run them over).
        On a trip to goal (a runner's) only one PICKUP_DETOUR or less off the way. A teammate he waited PICKUP_WAIT s by
        without boarding is skipped for 30 s. None: nobody to fetch."""
        skip = b.__dict__.setdefault("pickup_skip", {})
        at = getattr(b, "pickup_at", None)       # (the teammate, since when the driver has been by him)
        from . import vehicles
        v = next((q for q in snap.vehicles if q["handle"] == me.vehicle), None)
        air = v is not None and (vehicles.spec(v["kind"]) or {}).get("move") == "air"
        # (an aircraft sets down by a person and waits longer: a player's Falcon pickups sat 16-25 s on the floor 3-6 u
        # from the gunner, Nov 6; the bot pilot left after 8 s with the gunner 6-12 u off, live Spire 20261106-185412 at
        # 1038 s)
        if at and at[1] is not None and now - at[1] > (s.PICKUP_WAIT_AIR if air else s.PICKUP_WAIT):
            skip[at[0]], b.pickup_at, at = now, None, None
        # an aircraft's way is over the ground, height costs it little: its detour is measured flat, and on a trip one
        # on the way is fetched however far (live Spire 20261105-201917 at 296.7 s: the Falcon's runner pilot took off
        # alone from the pad, his whole team 100 u off at the spire's foot right under the core he flew to, 32 u of
        # detour by the 3-d way and over PICKUP_R; "not trying to pick up any teammates")
        way = (lambda p, q: (p - q).flat()) if air else dist
        cands = [(dist(me.pos, players[x.id].pos), x) for x in alive if x is not b and players[x.id] is not None
                 and players[x.id].vehicle == -1 and not players[x.id].has_flag and x.p.teamwork > 0
                 and x.p.tier != "novice" and now - skip.get(x.id, -99.0) > 30.0 and s.gunner_available(x)
                 and x.order.role not in ("ride", "board", "ferry")
                 and s.rider_ok(x, players, True, [players[x.id].pos])
                 and (goal is None or way(me.pos, players[x.id].pos) + way(players[x.id].pos, goal) - way(me.pos, goal)
                      <= s.PICKUP_DETOUR)]
        d, x = min((c for c in cands if c[0] <= s.PICKUP_R or air and goal is not None),
                   key=lambda c: (profiles.gunner_priority(c[1].p), c[0]), default=(None, None))
        if x is None or d > s.PICKUP_R and not (air and goal is not None):
            b.pickup_at = None
            return None
        since = at[1] if at and at[0] == x.id else None
        b.pickup_at = (x.id, (since or now) if dist(me.pos, players[x.id].pos) < 8.0 else None)
        return players[x.id].pos

    def vehicle_jobs(s, now, snap, alive, players):
        """Every bot at a wheel drives with a job: hunt their carrier (our flag or core taken: an armed or gunned vehicle),
        escort ours, taxi its riders to their objective (a runner at the wheel to his), anti-vehicle (a tank or
        anti-vehicle gun at an enemy vehicle one of us knows), else its role's patrol (Bot.patrol_point). The job is the
        bot's vjob and its drive_to; escorting, hunting and anti-vehicle work never end in getting out (Bot.drive)."""
        from . import vehicles
        theirs = next((p for p in snap.players if p.team != s.team and p.alive and p.has_flag), None) \
            if snap.mode in ("ctf", "assault", "stockpile", "oddball") else None
        if snap.mode == "invasion" and snap.inv_core_carrier is not None:
            c = snap.player(snap.inv_core_carrier)
            theirs = c if c is not None and c.alive and c.team != s.team else None
        ours = next((p for p in snap.players if p.team == s.team and p.alive and p.has_flag), None)
        if snap.mode == "invasion" and snap.inv_core_carrier is not None:
            c = snap.player(snap.inv_core_carrier)
            ours = c if c is not None and c.alive and c.team == s.team else None
        getaway = None
        # (custom, Nov 13) Wheelmen first: the getaway ride, one a team, is the first free driver's (profiles.wheelman)
        for b in sorted(alive, key=lambda b: not profiles.wheelman(b.p)):
            me = players[b.id]
            v = next((x for x in snap.vehicles if me is not None and x["handle"] == me.vehicle), None)
            sp = vehicles.spec(v["kind"]) if v else None
            if v is None or vehicles.kind_of(v["kind"]) != "mongoose":
                b.mongoose_trip = None
            if (sp is None or sp["move"] == "none" or getattr(b, "seat", "") != "driver"
                    or (b.order.role == "ferry" and vehicles.kind_of(v["kind"]) != "mongoose")):
                b.vjob = None
                continue
            kind, fights = vehicles.kind_of(v["kind"]), sp["gun"] is not None
            aboard = [x for x in snap.players if x.alive and x.vehicle == v["handle"] and x.id != b.id]
            job = None
            # (their carrier away in a vehicle: anything of ours that drives goes after him, guide 17 PUR rules)
            if kind == "mongoose":
                job = s.mongoose_job(now, b, me, snap, aboard, getaway_available=getaway is None)
                if job[0] == "getaway":
                    getaway = b
            elif theirs is not None and (fights or theirs.vehicle not in (None, -1)) and theirs.vehicle != v["handle"]:
                job = ("hunt", theirs.pos)
            elif ours is not None and ours.id != b.id and fights and ours.vehicle != v["handle"] and kind not in vehicles.TANKS:
                job = ("escort", ours.pos)
            elif b.order.role == "runner" and b.order.point is not None and vehicles.taxi_ok(v["kind"]):
                # (a power vehicle is no taxi: its job below, vehicles.taxi_ok). Alone at the wheel of a gun it cannot
                # fire itself (a Falcon, a Warthog): a gunner on its way first (gunner_pickup, PICKUP_DETOUR). Live
                # Spire 20261105-143525, 963-1024 s: a runner flew his Falcon alone 100 u to the core, AtomicBeast 37-48
                # u off its way there, then 40 s over the fight with nobody on its guns
                mate = s.gunner_pickup(now, b, me, snap, alive, players, goal=b.order.point) if (
                    vehicles.needs_gunner(v, snap) and not vehicles.driver_armed(v) and not aboard
                    and b.p.tier != "novice") else None
                job = ("pickup", mate) if mate is not None else ("taxi", b.order.point)
            elif aboard and kind not in vehicles.TANKS:
                goals = [s.bots[x.id].order.point for x in aboard if x.id in s.bots and s.bots[x.id].order.point is not None
                         and s.bots[x.id].order.role in ("runner", "escort", "mid")]
                pt = goals[0] if goals else s.straight_objective(snap, me.pos)
                job = ("taxi", pt) if pt is not None else None
            elif GETAWAY and getaway is None and s.ferry_seat(v) and b.order.role != "runner":
                park = s.getaway_park(snap, me.pos)
                if park is not None:            # (one a team: the first free transport driver)
                    job, getaway = ("getaway", park), b
            if job is None and (kind in vehicles.TANKS or "anti_vehicle" in vehicles.roles_of(v["kind"])):
                ev = b.enemy_vehicle(now, me, snap)
                job = ("anti_vehicle", ev[0]) if ev is not None else None
            if job is None and vehicles.needs_gunner(v, snap) and b.p.tier != "novice" and not aboard:
                mate = s.gunner_pickup(now, b, me, snap, alive, players)
                job = ("pickup", mate) if mate is not None else None
            if job is None and profiles.wheelman(b.p) and kind != "mongoose" and b.order.role not in ("runner", "ferry"):
                # (custom, Nov 13) nothing carried, nobody to fetch: a Wheelman drives to the objective (their flag,
                # the hill, the ball, the bomb, a drop point) to be by it when a ride is wanted; Slayer: its patrol
                pt = s.straight_objective(snap, me.pos)
                job = ("objective", pt) if pt is not None else None
            was = getattr(b, "vjob", None)
            b.vjob = job[0] if job else None
            if job and job[1] is not None:
                b.drive_to = job[1]
            if b.vjob != was and b.vjob is not None:
                s.event(now, "vehicle", f"{me.name}: {b.vjob.replace('_', '-')} ({v['kind']})")

    MONGOOSE_PICKUP_WAIT = 8.0
    MONGOOSE_GETAWAY_WAIT = 20.0

    def mongoose_job(s, now, b, me, snap, aboard, *, getaway_available=True):
        """A finite transport trip, with stable deadlines across the director's role passes."""
        if snap.mode == "race":
            b.mongoose_trip = None
            return ("taxi", snap.race_next.get(b.id) or b.order.point or me.pos)
        trip = getattr(b, "mongoose_trip", None)
        if trip is None or trip["vehicle"] != me.vehicle:
            trip = b.mongoose_trip = dict(vehicle=me.vehicle, key=None, carrier=None,
                                          wait_since=None, done=None)
        if trip["done"] is not None:
            return ("dismount", me.pos)

        if b.order.role == "ferry":
            trip["carrier"] = b.order.target
        carrier = snap.player(trip["carrier"])
        flag = (snap.flags or {}).get(1 - s.side) if snap.mode == "ctf" else None
        objective = (snap.mode, snap.inv_phase, flag.state if flag else None, flag.carrier if flag else None)
        job, point, reason = None, None, None
        if trip["carrier"] is not None:
            if (carrier is None or not carrier.alive or not carrier.has_flag or carrier.team != me.team
                    or carrier.vehicle not in (-1, me.vehicle) or snap.mode not in ("ctf", "assault", "stockpile")):
                reason = "carrier pickup no longer needed"
            else:
                home = s.carry_point(snap)
                point = home if carrier.vehicle == me.vehicle else carrier.pos
                job = "taxi" if carrier.vehicle == me.vehicle else "pickup"
                # Role assignment runs again every two seconds, so retain this carrier explicitly.
                b.order = Order("ferry", home, target=carrier.id)
        else:
            rider_goals = [s.bots[p.id].order.point for p in aboard if p.id in s.bots
                           and s.bots[p.id].order.role in ("runner", "escort", "mid")
                           and s.bots[p.id].order.point is not None]
            point = b.order.point if b.order.role != "drive" else None
            if point is None:
                point = getattr(b, "drive_to", None)
            if rider_goals:
                point = rider_goals[0]
            if aboard:
                carrier = next((p for p in aboard if p.has_flag), None)
                if carrier is not None and snap.mode in ("ctf", "assault", "stockpile"):
                    trip["carrier"] = carrier.id
                    point = s.carry_point(snap)
                    b.order = Order("ferry", point, target=carrier.id)
                job, point = "taxi", point or s.straight_objective(snap, me.pos)
            else:
                park = s.getaway_park(snap, me.pos) if GETAWAY and getaway_available and b.order.role != "runner" else None
                if park is not None:
                    job, point = "getaway", park
                elif point is not None and (dist(me.pos, point) > VEHICLE_TRIP or trip["key"] == ("taxi", point)):
                    job = "taxi"
            if trip["key"] is not None and trip["key"][0] == "getaway" and trip.get("objective") != objective:
                reason = "getaway objective changed"
            if job == "getaway" and flag is not None and flag.state == "carried":
                runner = snap.player(flag.carrier)
                if runner is None or not runner.alive:
                    reason = "getaway carrier unavailable"

        key = ("ferry", trip["carrier"]) if trip["carrier"] is not None else (job, point)
        if reason is None and (job is None or point is None):
            reason = "no useful transport trip"
        if reason is None:
            if trip["key"] != key:
                trip.update(key=key, wait_since=None, objective=objective)
                trip.setdefault("until", now + max(60.0, dist(me.pos, point) / 3.0 + 30.0))
            waiting = (job == "pickup" and dist(me.pos, point) < 6.0
                       or job == "getaway" and (me.pos - point).flat() < GETAWAY_PARK_R)
            if waiting and trip["wait_since"] is None:
                trip["wait_since"] = now
            elif not waiting:
                trip["wait_since"] = None
            wait_limit = s.MONGOOSE_PICKUP_WAIT if job == "pickup" else s.MONGOOSE_GETAWAY_WAIT
            if waiting and now - trip["wait_since"] >= wait_limit:
                reason = "transport wait expired"
            elif now >= trip["until"]:
                reason = "transport trip expired"
            elif job == "taxi" and dist(me.pos, point) < 6.0:
                reason = "transport destination reached"
        if reason is not None:
            trip["done"] = reason
            return ("dismount", me.pos)
        return (job, point)

    @staticmethod
    def ferry_seat(v):
        """A seat for our carrier in v: a passenger's, never a tank's (guide 18 ODST-OBJ-01)."""
        from . import vehicles
        sp, k = vehicles.spec(v["kind"]), vehicles.kind_of(v["kind"])
        return (sp is not None and sp["move"] == "ground" and k not in vehicles.TANKS and v.get("riders", 0) < len(sp["seats"])
                and ("passenger" in sp["seats"] or bool(vehicles.REACH_SEATS.get(k, {}).get("passenger"))))

    def getaway_park(s, snap, start):
        """Where the getaway ride waits (CTF, their flag on its stand with our runners going for it, or ours carrying
        it not yet aboard): on the vehicles' way from their stand home (Terrain.vnav, which starts on the vehicle ground
        nearest their stand: Avalanche's stands sit inside the bases, off it), the first point GETAWAY_D u or more from
        their stand; None outside CTF, or where the map has no vehicle ground. Cached per map."""
        if snap.mode != "ctf" or s.is_one_flag(snap):
            return None
        theirs = (snap.flags or {}).get(1 - s.side)
        if theirs is None or theirs.state == "dropped":
            return None
        cache = s.__dict__.setdefault("_getaway", {})
        if "park" not in cache:
            eh, home = s.map["flags"][1 - s.side], s.map["flags"][s.side]
            T = s.terrain()
            cache["park"] = None
            q = eh
            for _ in range(80):
                w = T.vnav(q, home) if hasattr(T, "vnav") else None
                # (a step straight down onto the vehicle ground is progress: with the live-learned Avalanche data its
                # first step from the stand drops 3.6 u under the platform, 0.13 u across)
                if w is None or dist(w, q) < 0.05 or dist(w, home) < 4.0:
                    break
                q = w
                if (q - eh).flat() >= GETAWAY_D:
                    cache["park"] = q
                    break
            if cache["park"] is None:
                cache["park"] = s.drivable_near(eh + (home - eh) * ((GETAWAY_D + 1.5) / max(dist(eh, home), 1.0)))
        return cache["park"]

    def drivable_near(s, p):
        """The vehicle ground's cell nearest p across (Terrain.vroomy), its centre; None where the map has none."""
        import numpy as np
        from .terrain import NAV_CELL
        T = s.terrain()
        if getattr(T, "graph_v", None) is None and hasattr(T, "_build_vnav"):
            T._build_vnav()
        vg = getattr(T, "vroomy", None)
        if vg is None or not vg.any():
            return None
        ls, js, is_ = np.nonzero(vg)
        d = (T.x0 + (is_ + 0.5) * NAV_CELL - p.x) ** 2 + (T.y0 + (js + 0.5) * NAV_CELL - p.y) ** 2
        m = int(np.argmin(d))
        return T._center(int(ls[m]), int(js[m]), int(is_[m]))

    def ferry_orders(s, now, snap, alive, players):
        """Our flag carrier on foot far from home: the nearest bot driving a vehicle with a free seat within 45 u picks
        him up and runs him home (ferry); a carrier bot within 10 u of that vehicle gets in."""
        from . import vehicles
        carrier = next((p for p in snap.players if p.team == s.team and p.alive and p.has_flag and p.vehicle == -1), None)
        if carrier is None or snap.mode not in ("ctf", "assault", "stockpile"):
            return
        home = s.carry_point(snap)
        if dist(carrier.pos, home) < 30.0:
            return
        cb = s.bots.get(carrier.id)
        if cb is not None and s.person_pickup(now, snap, carrier, cb):
            return
        drivers = []
        for b in alive:
            p = players[b.id]
            v = next((x for x in snap.vehicles if p is not None and x["handle"] == p.vehicle), None)
            sp = vehicles.spec(v["kind"]) if v else None
            # (a seat for him: a passenger's, never a tank's gun, guide 18 ODST-OBJ-01: a Wraith or Scorpion took the job)
            k = vehicles.kind_of(v["kind"]) if v else None
            seat_ok = sp is not None and k not in vehicles.TANKS and (
                "passenger" in sp["seats"] or bool(vehicles.REACH_SEATS.get(k, {}).get("passenger")))
            if (v and seat_ok and getattr(b, "seat", "") == "driver" and v.get("riders", 0) < len(sp["seats"])
                    and not (k == "mongoose" and getattr(b, "vjob", None) == "dismount")):
                drivers.append((dist(Vec(*v["pos"]), carrier.pos), b, v))
        if not drivers:
            return
        d, b, v = min(drivers, key=lambda x: x[0])
        ride = next((x for x in drivers if getattr(x[1], "vjob", None) == "getaway"), None)
        # (custom, Nov 13) a Wheelman at a wheel (profiles.wheelman): before a nearer driver, from WHEEL_CREW_REACH
        wheel = min((x for x in drivers if profiles.wheelman(x[1].p) and x[0] <= s.WHEEL_CREW_REACH),
                    key=lambda x: x[0], default=None)
        if ride is not None:                 # the getaway ride waiting for him goes, whatever the distance
            d, b, v = ride
        elif wheel is not None:
            d, b, v = wheel
        elif d > 45.0:
            return
        if b.order.role != "ferry":
            s.event(now, "vehicle", f"{players[b.id].name}: picking up the carrier ({v['kind']})")
        b.order = Order("ferry", home, target=carrier.id)
        cb = s.bots.get(carrier.id)
        if cb is not None and d < 10.0:          # our carrier is a bot: in he gets
            cb.order = Order("board", Vec(*v["pos"]), target=v["handle"])   # (a passenger seat, not the gun)
            s.roles[cb.id] = "board"

    PERSON_PICKUP_R = 8.0   # u: (custom) our carrier bot gets into a person's vehicle with a passenger seat free this near

    def person_pickup(s, now, snap, carrier, cb):
        """(custom, Nov 12) A person of ours at the wheel of a ground vehicle with a passenger seat free pulls up within
        PERSON_PICKUP_R of our carrier bot (flag or bomb, on foot, far from where he scores): the carrier gets in, Easy
        too (its order set outright, as ferry's; set_order lets Easy refuse every call). True: he was sent. The owner:
        "bots don't get in a warthog or mongooses passenger when carrying the bomb or flag"; live Breakpoint
        20261112-193700, 306-321 s, his Warthog stood 1-4 u from our Easy bomb carrier, who never got in. A person on a
        gun is not at the wheel (gunner_seat); one in a passenger seat cannot be told from a driver."""
        from . import vehicles
        for v in snap.vehicles:
            sp = vehicles.spec(v["kind"])
            k = vehicles.kind_of(v["kind"])
            if (v.get("team") != s.team or sp is None or sp["move"] not in ("ground", "hover") or k in vehicles.TANKS
                    or v.get("dead") or not ("passenger" in sp["seats"]
                                             or vehicles.REACH_SEATS.get(k, {}).get("passenger"))):
                continue
            aboard = [p for p in snap.players if p.alive and p.vehicle == v["handle"]]
            if not any(not p.is_bot and not getattr(p, "gunner_seat", False) for p in aboard):
                continue
            if v.get("riders", 0) >= len(sp["seats"]) or dist(Vec(*v["pos"]), carrier.pos) > s.PERSON_PICKUP_R:
                continue
            if cb.order.role != "board" or cb.order.target != v["handle"]:
                s.event(now, "vehicle", f"{carrier.name}: into the passenger seat, a teammate's {v['kind']}")
            cb.order = Order("board", Vec(*v["pos"]), target=v["handle"])
            s.roles[cb.id] = "board"
            return True
        return False

    CREW_REACH = 45.0      # u: how far a bot is sent on foot to drive a vehicle its team wants (crew_orders)
    WHEEL_CREW_REACH = 70.0   # u: (custom, Nov 13) a Wheelman's (profiles.wheelman)
    POWER_R = 15.0         # u: a bot on an objective job takes a free power vehicle this near it (crew_orders)
    # (custom, Nov 8; Halo 4) a bot within POWER_R of an empty power vehicle, ranked as high as the one on its way
    # (profiles.resource_priority), takes the job from it when POWER_HANDOVER u or more nearer: a Legendary who respawns by
    # Redoubt's Wraith, while the one sent runs from 45 u (the job stayed his 20 s; first driver 23-37 s after each spawn)
    POWER_HANDOVER = 15.0

    def power_handover(s, v, bid, players, pools, skip, now, may_drive):
        """Halo 4: whether the power vehicle v bot bid is on its way to has a teammate of the pools ranked as high, within
        POWER_R of it and POWER_HANDOVER u or more nearer than bid: that one takes the job (crew_orders)."""
        from . import vehicles
        if (not str(s.map.get("name", "")).startswith("h4_") or vehicles.taxi_ok(v["kind"]) or players.get(bid) is None
                or bid not in s.bots):
            return False
        vp = Vec(*v["pos"])
        far, rank = dist(players[bid].pos, vp), profiles.resource_priority(s.bots[bid].p)
        return any(c != bid and players.get(c) is not None and skip.get((c, v["handle"]), 0.0) <= now
                   and may_drive(b, v) and profiles.resource_priority(b.p) <= rank
                   and dist(players[c].pos, vp) <= s.POWER_R and dist(players[c].pos, vp) + s.POWER_HANDOVER <= far
                   for pool in pools for c, b in pool.items())

    @staticmethod
    def power_kind(kind):
        """A power vehicle fixed Legendary and Demon are called to over weapon runs and gun seats (custom, Nov 8): one
        taken for a job (vehicles.taxi_ok), a Demon may drive (no gun Warthog: Normal and Heroic drive those)."""
        from . import vehicles
        return not vehicles.taxi_ok(kind) and not vehicles.demon_no_drive(kind)

    def crew_orders(s, now, snap, players, foot, busy=(), seated=()):
        """Vehicles picked by role. Roles in the order one anti-air, one anti-vehicle, one transport (CTF and Assault: the
        transport first; King and Territories: the anti-vehicle gun first), then every harasser: a role none of ours
        fills gets the empty vehicle of that role nearest a bot of ours on foot with no objective job (foot), within
        CREW_REACH, that bot as its driver (Order "drive"; its gunner is called once it is in: needs_gunner). The bot
        keeps the job until it is in, the vehicle is taken or 30 s pass (then not that vehicle for 60 s). Easy is never
        sent: it never plans."""
        from . import vehicles
        crews = s.__dict__.setdefault("crews", {})          # vehicle handle -> (bot id, since)
        skip = s.__dict__.setdefault("crew_skip", {})       # (bot id, handle) -> not before
        filled = set()
        for v in snap.vehicles:
            r = vehicles.roles_of(v["kind"])
            if r and v["occupied"] and v.get("team") == s.team:
                filled.add(next((x for x in r if x not in filled), r[0]))
        # (no wreck, nothing on its side, no vehicle bots stood by without getting in: vehicles.usable)
        duds = s.map.get("_vehicle_duds", {})
        empty = {v["handle"]: v for v in snap.vehicles if not v["occupied"] and vehicles.roles_of(v["kind"])
                 and vehicles.usable(v, now, duds)}
        free = {b.id: b for b in foot if not (profiles.fixed_demon(b.p) and getattr(b, "fetch", None) is not None)}
        near = {b.id: b for b in busy if not (profiles.fixed_demon(b.p) and getattr(b, "fetch", None) is not None)}
        # (custom, Nov 8: the owner) a power vehicle comes before a power weapon and a gun seat for fixed Legendary and
        # Demon: one on a weapon run (its run is dropped once it has the job), or riding a gun or a passenger seat (it
        # gets out: Bot.drive), is called to one too, from CREW_REACH. They go first by rank (resource_priority)
        power_pool = dict(free)
        power_pool.update({b.id: b for b in foot if profiles.fixed_high(b.p)})
        power_pool.update({b.id: b for b in seated if profiles.fixed_high(b.p) and players.get(b.id) is not None})
        mongoose_goals = {bid: (getattr(b, "drive_to", None) if b.order.role == "drive" else b.order.point)
                          for bid, b in free.items()}
        def may_drive(b, v):
            # (custom: no Demon at the wheel of a Warthog or a Mongoose, vehicles.DEMON_NO_DRIVE; Race laps excepted)
            return snap.mode == "race" or not (profiles.fixed_demon(b.p) and vehicles.demon_no_drive(v["kind"]))

        def pool_for(v):
            # who may be sent to v: a transport or a Ghost the free bots; a power vehicle the busy ones near it too, and
            # (power_kind) fixed Legendary and Demon on a weapon run or in a seat of another vehicle
            if vehicles.taxi_ok(v["kind"]):
                return free
            extra = power_pool if s.power_kind(v["kind"]) else free
            return {**near, **{bid: b for bid, b in extra.items() if players[bid].vehicle != v["handle"]}}

        def reach_of(bid, v):
            if bid in free and profiles.wheelman(free[bid].p):
                return s.WHEEL_CREW_REACH          # (custom, Nov 13: a Wheelman from farther)
            return s.CREW_REACH if bid in free or (bid in power_pool and s.power_kind(v["kind"])) else s.POWER_R

        def leave(b):
            for pool in (free, near, power_pool):      # (the bot called this pass leaves every pool)
                pool.pop(b.id, None)

        def drop_run(b, v):
            if s.power_kind(v["kind"]) and profiles.fixed_high(b.p):
                b.fetch = None                         # (custom: its job is the power vehicle now, not the weapon run)

        for h, (bid, since) in list(crews.items()):
            mine = h in empty and bid in pool_for(empty[h])
            if mine and now - since < 30.0 and s.power_handover(empty[h], bid, players, (free, near), skip, now, may_drive):
                del crews[h]                     # (custom: a nearer teammate takes it, below; no wait for the far one)
                continue
            if (mine and now - since < 30.0
                    and may_drive(s.bots[bid], empty[h])
                    and not (vehicles.kind_of(empty[h]["kind"]) == "mongoose"
                             and now < getattr(s.bots[bid], "vehicle_retry_at", 0.0))):
                b, v = pool_for(empty[h])[bid], empty.pop(h)
                leave(b)
                drop_run(b, v)
                b.set_order(Order("drive", Vec(*v["pos"]), target=h), sure=True)   # (it took the job)
                s.roles[bid] = "drive"
                r = vehicles.roles_of(v["kind"])
                filled.add(next((x for x in r if x not in filled), r[0]))
            else:
                if now - since >= 30.0:
                    skip[(bid, h)] = now + 60.0
                del crews[h]
        first = vehicles.ROLE_FIRST.get(snap.mode)
        # what they field picks our first (guide 19 VC-01 / VC-02): anti-air while one of their aircraft is known, else
        # anti-vehicle while one of their tanks is
        theirs = s.enemy_vehicles(snap)
        if any(vehicles.spec(k) and vehicles.spec(k)["move"] == "air" for k in theirs):
            first = "anti_air"
        elif any(vehicles.kind_of(k) in vehicles.TANKS for k in theirs):
            first = "anti_vehicle"
        for role in ([first] if first else []) + [r for r in vehicles.ROLE_ORDER if r != first]:
            while role == "harasser" or role not in filled:
                pairs = [(dist(players[bid].pos, Vec(*v["pos"])), b, v) for v in empty.values()
                         if role in vehicles.roles_of(v["kind"])
                         for bid, b in pool_for(v).items()
                         if skip.get((bid, v["handle"]), 0.0) <= now and may_drive(b, v)
                         and (vehicles.kind_of(v["kind"]) != "mongoose" or (
                             now >= getattr(b, "vehicle_retry_at", 0.0) and mongoose_goals.get(bid) is not None
                             and Bot.trip_ok(v, players[bid], mongoose_goals[bid])
                             and (snap.mode == "race" or dist(players[bid].pos, mongoose_goals[bid]) > VEHICLE_TRIP)))
                         and dist(players[bid].pos, Vec(*v["pos"])) <= reach_of(bid, v)]
                d, b, v = min(pairs, key=lambda x: x[0], default=(None, None, None))
                if d is None or d > (s.WHEEL_CREW_REACH if any(profiles.wheelman(x[1].p) for x in pairs) else s.CREW_REACH):
                    break
                if not vehicles.taxi_ok(v["kind"]):
                    d, b, v = min((x for x in pairs if x[2]["handle"] == v["handle"]),
                                  key=lambda x: (profiles.resource_priority(x[1].p), x[0]))
                elif vehicles.demon_no_drive(v["kind"]) and snap.mode != "race":
                    # (custom: a Warthog or a Mongoose goes to a Normal or Heroic bot in reach first, then the nearest:
                    # profiles.driver_priority; the owner's ask Nov 7)
                    d, b, v = min((x for x in pairs if x[2]["handle"] == v["handle"]),
                                  key=lambda x: (profiles.driver_priority(x[1].p), x[0]))
                leave(b)
                b.set_order(Order("drive", Vec(*v["pos"]), target=v["handle"]))
                if b.order.role != "drive":      # a rogue moment: it plays on its own this round
                    skip[(b.id, v["handle"])] = now + 10.0
                    continue
                drop_run(b, v)
                if vehicles.kind_of(v["kind"]) == "mongoose":
                    b.drive_to = mongoose_goals[b.id]
                del empty[v["handle"]]
                crews[v["handle"]] = (b.id, now)
                s.roles[b.id] = "drive"
                filled.add(role)
                s.event(now, "vehicle", f"{players[b.id].name}: driving the {v['kind']} ({role.replace('_', '-')})")
        # a power vehicle (vehicles.taxi_ok: a Banshee, a tank ...) nobody of ours took, by a bot on an objective job
        # (busy: Invasion has no other kind): the nearest one within POWER_R takes it to work it (Bot.drive: its role's
        # patrol, never left at a trip's end), whatever role we fill. Live Spire 20261105-201917: three Banshees stood
        # on their pad 274-505 s, attackers 1-9 u off it all the while, no bot ever in one ("they dont touch the banshee
        # at all"); since 811e5a1 (no taxi in a power vehicle) only bots with no objective job were sent to one
        for h, v in list(empty.items()):
            if vehicles.taxi_ok(v["kind"]):
                continue
            vp = Vec(*v["pos"])
            # (a rocket or gauss Warthog: Normal and Heroic first, never a Demon, profiles.driver_priority)
            order = (profiles.driver_priority if vehicles.demon_no_drive(v["kind"]) and snap.mode != "race"
                     else profiles.resource_priority)
            d, b = min(((dist(players[bid].pos, vp), b) for bid, b in near.items()
                        if skip.get((bid, h), 0.0) <= now and dist(players[bid].pos, vp) <= s.POWER_R and may_drive(b, v)),
                       key=lambda x: (order(x[1].p), x[0]), default=(None, None))
            if d is None or d > s.POWER_R:
                continue
            leave(b)
            b.set_order(Order("drive", vp, target=h))
            if b.order.role != "drive":
                skip[(b.id, h)] = now + 10.0
                continue
            drop_run(b, v)
            del empty[h]
            crews[h] = (b.id, now)
            s.roles[b.id] = "drive"
            s.event(now, "vehicle", f"{players[b.id].name}: taking the {v['kind']} (power vehicle by him)")

    def enemy_vehicles(s, snap, within=20.0):
        """The kinds of the vehicles men of theirs ride that one of our bots has seen in the last within s."""
        out = []
        for b in s.bots.values():
            for k, bel in b.per.beliefs.items():
                p = snap.player(k) if isinstance(k, int) else None
                if p is None or p.team == s.team or p.vehicle in (None, -1) or not bel.seen or snap.time - bel.t > within:
                    continue
                v = next((x for x in snap.vehicles if x["handle"] == p.vehicle), None)
                if v is not None:
                    out.append(v["kind"])
        return out

    def landed_aircraft(s, now, snap):
        """Handles of our aircraft with someone in and a seat free, set down: under LANDED_H over the floor under it and
        under LANDED_V u/s over its last half second (tracked here: the vehicle reads carry no speed)."""
        from . import vehicles
        track = s.__dict__.setdefault("air_track", {})
        out = []
        for v in snap.vehicles:
            sp = vehicles.spec(v["kind"])
            if sp is None or sp["move"] != "air" or v.get("team") != s.team:
                continue
            h, p = v["handle"], Vec(*v["pos"])
            hist = [e for e in track.get(h, []) if now - e[0] <= 0.6] + [(now, p)]
            track[h] = hist
            if not v.get("riders", 0) or v.get("riders", 0) >= len(sp["seats"]) or v.get("dead"):
                continue
            t0, p0 = hist[0]
            slow = now - t0 >= 0.3 and (p - p0).flat() / (now - t0) < LANDED_V
            T = s.terrain()
            if slow and T is not None and T.height_over(p.x, p.y, p.z) < LANDED_H:
                out.append(h)
        return out

    def honk_orders(s, now, snap, alive, players):
        """A teammate in a vehicle honks at us: the nearest bot on foot within 20 u takes the gun, then the passenger
        seats go to our objective holders first, then to the next nearest bots. A bot passenger gives its seat up
        when our objective holder on foot is beside a vehicle with no seat left for him."""
        from . import vehicles
        honks = list(getattr(snap, "honks", ()))
        picks = getattr(snap, "honk_at", None) or {}
        # a honk (live_bots: a person stopped by us, or their horn) calls from 20 u; an aircraft of ours set down calls
        # those within LAND_CALL_R (Nov 6: bots get in an aircraft that lands
        # close to them; a player's Falcon pickups: down on the floor 3-6 u from the gunner, 16-25 s)
        # (custom, Nov 12) a person's aircraft set down calls from LAND_CALL_R_PERSON: live Forge World 20261112-200003,
        # the owner's Falcon sat down 6 s at 596-602 s, the nearest teammates able to come 11-17 u off, nobody called
        person_in = {v["handle"] for v in snap.vehicles
                     if any(p.vehicle == v["handle"] and p.alive and not p.is_bot for p in snap.players)}
        calls = [(h, picks.get(h), 20.0) for h in honks] + [
            (h, None, LAND_CALL_R_PERSON if h in person_in else LAND_CALL_R)
            for h in s.landed_aircraft(now, snap) if h not in honks]
        for h, picked, reach in calls:
            v = next((x for x in snap.vehicles if x["handle"] == h and x.get("team") == s.team), None)
            sp = vehicles.spec(v["kind"]) if v else None
            if sp is None:
                continue
            vp = Vec(*v["pos"])
            # the bot his horn picked (live_bots.horn_call: his view on him) comes first, from up to the horn's reach
            coming = [b for b in alive if b.order.target == h and b.order.role in ("ride", "board")]
            free = len(sp["seats"]) - v.get("riders", 0) - len(coming)
            foot = sorted((b for b in alive if b not in coming and players[b.id] is not None and players[b.id].alive
                           and players[b.id].vehicle == -1
                           and dist(players[b.id].pos, vp) < (HORN_CALL_R if b.id == picked else reach) and s.gunner_available(b)),
                          key=lambda b: (b.id != picked, not players[b.id].has_flag, dist(players[b.id].pos, vp)))
            holders = [b for b in foot if players[b.id].has_flag]
            others = [b for b in foot if not players[b.id].has_flag]
            took = 0
            if free > 0 and vehicles.needs_gunner(v, snap) and not any(b.order.role == "ride" for b in coming) and others:
                b = min(others, key=lambda b: (profiles.gunner_priority(b.p), dist(players[b.id].pos, vp)))
                others.remove(b)
                b.set_order(Order("ride", vp, target=h), sure=True)
                s.roles[b.id], free, took = "ride", free - 1, 1
                s.event(now, "vehicle", f"{players[b.id].name}: on the gun (honked)")
            # every gun seat on a craft whose other seats are all guns (the Falcon's two side guns): the rest of them too
            guns = sp["seats"].count("gunner") - sum(1 for b in coming if b.order.role == "ride") - took - max(
                0, v.get("riders", 0) - 1)
            while "passenger" not in sp["seats"] and free > 0 and others and guns > 0:
                b = others.pop(0)
                b.set_order(Order("ride", vp, target=h), sure=True)
                s.roles[b.id], free, guns = "ride", free - 1, guns - 1
                s.event(now, "vehicle", f"{players[b.id].name}: on the other gun (honked)")
            if "passenger" in sp["seats"]:
                for b in holders + others:
                    if free <= 0:
                        break
                    b.set_order(Order("board", vp, target=h), sure=True)
                    s.roles[b.id], free = "board", free - 1
                    s.event(now, "vehicle", f"{players[b.id].name}: in the passenger seat (honked)")
        holder = next((p for p in snap.players if p.team == s.team and p.alive and p.has_flag and p.vehicle == -1), None)
        if holder is None:
            return
        for v in snap.vehicles:
            sp = vehicles.spec(v["kind"])
            if (v.get("team") != s.team or not sp or "passenger" not in sp["seats"]
                    or v.get("riders", 0) < len(sp["seats"]) or dist(Vec(*v["pos"]), holder.pos) > 6.0):
                continue
            seated = [b for b in alive if players[b.id] is not None and players[b.id].vehicle == v["handle"]
                      and getattr(b, "seat", "") == "passenger" and not players[b.id].has_flag]
            if seated and seated[0].order.role != "give_seat":
                seated[0].order = Order("give_seat", Vec(*v["pos"]))
                s.event(now, "vehicle", f"{players[seated[0].id].name}: seat for the objective holder")
                hb = s.bots.get(holder.id)
                if hb is not None:
                    hb.order = Order("board", Vec(*v["pos"]), target=v["handle"])
                    s.roles[hb.id] = "board"

    def straight_objective(s, snap, at=None):
        """What an Easy bot runs at in an objective game: the enemy flag where it is, the hill, the ball (or its
        carrier). None in Slayer: it wanders."""
        if snap.mode == "ctf":
            f = (snap.flags or {}).get(1 - s.side)
            own = (snap.flags or {}).get(s.team)
            if f is None and own is not None:     # One Flag defence: their flag does not exist; ours is the job (
                return own.pos                    # an Easy bot ran 96% of a round to their empty stand)
            return f.pos if f is not None else s.map["flags"][1 - s.side]
        if snap.mode == "king" and snap.hill is not None:
            return snap.hill
        if snap.mode in ("territories", "headhunter", "infection") and snap.obj_zones:
            return min((z for z, r, o in snap.obj_zones if o != s.team), key=lambda z: dist(z, s.map["points"]["mid"]),
                       default=snap.obj_zones[0][0])
        if snap.mode in ("assault", "stockpile") and snap.obj_items:
            return snap.obj_items[0]["pos"]
        if snap.mode == "invasion":
            if snap.inv_phase == 3 and snap.inv_core is not None:
                carrier = snap.player(snap.inv_core_carrier) if snap.inv_core_carrier is not None else None
                return carrier.pos if carrier is not None and carrier.team != s.team else snap.inv_core
            return min(snap.inv_zones, key=lambda z: dist(z, at or snap.player(next(iter(s.bots))).pos)) \
                if snap.inv_zones and s.bots else None      # (the nearest to this bot: all used the first bot's)
        if snap.mode == "oddball" and snap.ball is not None:
            carrier = snap.player(snap.ball_carrier) if snap.ball_carrier is not None else None
            return carrier.pos if carrier is not None else snap.ball
        return None

    def pick_route(s, now, b, used, home=False):
        """Route to the enemy flag by skill (home: a carrier's way back, the same routes the other way). Novices run
        straight in. Better players spread over the side lanes; the best prefer sneaky routes and avoid areas where the
        team keeps dying or seeing enemies (the director's threat map)."""
        r = b.p.routes
        if r < 0.15:
            return ()
        options = [((p,), False) for p in s.map.get("lanes", [])]
        options += [(tuple(route[::-1] if home else route), True) for route in s.map.get("sneak", {}).get(s.side, [])]
        if not options:
            return ()

        def threat(route):
            total = 0.0
            for p in route:
                lvl, t = s.threat.get(s.zones.name(p), (0, now))
                total += max(0.0, lvl - (now - t) / 6.0)   # threat fades over about a minute
            return total

        def score(opt):
            route, sneaky = opt
            return (-r * 0.5 * threat(route) + (0.9 * r * r if sneaky else 0.0)   # sneaking is a top-player habit
                    - ((3.0 if getattr(s, "split", False) else 0.6) if route in used else 0.0)   # split: another lane
                    + s.rng.uniform(0, 1.0 - 0.5 * r))
        return max(options, key=score)[0]

    def role_slots(s, now, snap, n):
        """Ordered list of (role, point, preferred trait)."""
        enemy = 1 - s.side                 # CTF: two teams, team == side
        home = s.map["flags"][s.side]
        holds = s.map["holds"][s.side]
        mid = s.map["points"]["mid"]
        if snap.mode == "firefight":
            # teammates of the people: stay with the nearest human, fight whatever comes
            people = [p for p in snap.players if p.team == s.team and p.alive and not p.is_bot]
            if people:
                s.ff_last, s.ff_lead = people[0].pos, people[0].id   # (assign_roles: the escorts' lead, Bot.lead)
                return [("escort", people[0].pos, "aggression")] * n
            s.ff_lead = None
            # the player is down (Nov 6: when the player dies they roam or find a safe spot): they hold the map's safe
            # spots nearest where the player fell (its holds and named points), two spots so they are not stacked, and
            # fight from there until the player is back (they ran into the open middle before)
            last = getattr(s, "ff_last", None) or mid
            spots = sorted([q for h in s.map["holds"].values() for q in h] + list(s.map["points"].values()),
                           key=lambda q: dist(q, last))
            if not spots:
                return [("defender", last, "camping")] * n
            a, b = spots[0], spots[1] if len(spots) > 1 else spots[0]
            return [("defender", a, "camping") if i % 2 == 0 else ("defender", b, "camping") for i in range(n)]
        if snap.mode == "king" and snap.hill is not None:
            # theirs on it (guide 19 KOTH-STATIC-04, the contested hill): we take it, one more of us inside than of them
            # (two at least), the rest on the spots that see it shooting in, held TAKE_HOLD s past the last sighting.
            # The sim's difficulty pyramid (docs/oct31/sims.md): Easy, running everyone onto the hill, out-held Heroic
            # 123-15 and Legendary 121-8 hill seconds while losing the kills 2 to 1: one scorer on overlooks gave the
            # hill to a team standing on it
            take = s.king_take(now, snap) if KING_TAKE else 0
            if take:
                return ([("defender", snap.hill, "objective")] * take
                        + [("mid", q, "camping") for q in s.overlooks(snap.hill, n)])
            # one on the hill, the rest on spots around it that see it (docs/research/12 section 4.1: "it only takes one
            # person to accrue time atop the hill; more ... only gives your enemy a fatter target"); was n-1 inside
            post = snap.hill
            if s.posture.state == "hide_and_hold" and snap.hill_r:
                # ahead with the clock running out (guide 19 KOTH-STATIC-11): the scorer holds the hill's edge on our
                # side, not its middle, and the rest stay on the spots that see it
                c = s.team_centre(snap)
                if c is not None and (c - snap.hill).flat() > 0.5:
                    way = c - snap.hill
                    post = snap.hill + way * (max(0.0, snap.hill_r - 0.75) / way.flat())
            return [("defender", post, "camping")] + [("mid", q, "camping") for q in s.overlooks(snap.hill, n)]
        if snap.mode == "invasion":
            return s.invasion_slots(now, snap, n)
        if snap.mode == "race" and snap.race_next:
            # each racer at its own next gate (brain/modes.py Race; Bot.race_gate keeps it to the tick): no posts, no
            # escorts, kills score nothing (RACE-01)
            return [("runner", snap.race_next[b.id], "objective") for b in s.bots.values() if b.id in snap.race_next]
        if snap.mode in ("territories", "assault", "stockpile", "headhunter", "infection", "regicide"):
            return s.mode_slots(now, snap, n)
        if snap.mode == "oddball":
            ball = snap.ball or mid
            carrier = snap.player(snap.ball_carrier) if snap.ball_carrier is not None else None
            if carrier and carrier.team == s.team:     # ours: two guards on him, the rest watch from around him
                # (research 12 section 4.2: two guards at their own angles, not the whole team on one man)
                return [("escort", carrier.pos, "aggression")] * 2 + [("mid", q, "aggression")
                                                                      for q in s.overlooks(carrier.pos, n)]
            if carrier:                                # theirs: the game marks him for everyone
                return [("hunter", carrier.pos, "aggression")] * n
            return [("runner", ball, "objective")] * 2 + [("hunter", ball, "aggression")] * n
        if snap.mode == "vip" and snap.vips:
            # guide 07 VIP: ours plays like a flag carrier with a gun, two escorts with him; one hunts theirs (the
            # game marks him)
            mine = [p for p in map(snap.player, snap.vips) if p is not None and p.team == s.team]
            theirs = [p for p in map(snap.player, snap.vips) if p is not None and p.team != s.team]
            slots = [("escort", mine[0].pos, "teamwork")] * 2 if mine else []
            slots += [("hunter", theirs[0].pos, "aggression")] if theirs else []
            return slots + s.slayer_slots(now, snap, n)
        if snap.mode != "ctf":
            return s.slayer_slots(now, snap, n)
        own, theirs = snap.flags.get(s.team), snap.flags.get(enemy)
        if own is None and theirs is None:      # no flag of ours or theirs read (a neutral stand): play Slayer
            return s.slayer_slots(now, snap, n)
        if s.is_one_flag(snap):                 # One Flag: the flag keeps its stand while the sides swap each round
            home = s.capture_point(snap)        # attackers score on the other stand; defenders post at the flag
        slots = []
        carrier = next((p for p in snap.players if p.team == s.team and p.has_flag), None)
        # split attacks: decided per attack cycle, two runners on different lanes, each with its own escort, and
        # the pushers spread over the lanes (which also walks the parts of the map the single push left out: 9% of
        # his time was in spots no bot reached, the upper walks over Mid)
        if now >= getattr(s, "split_until", 0.0):
            s.split_until = now + s.rng.uniform(40, 70)
            s.split = s.rng.random() < SPLIT_CHANCE
        split = getattr(s, "split", False)
        # a standoff: both flags out, and no capture until ours is home (Reach "Flag at home: Yes", CE and Halo 2 the
        # same). Live, Boardwalk CTF: our carrier stood on our stand 2 min with both escorts while our flag lay 15 u
        # from their base, nobody went for it. Now everyone but one escort (four or more of us) gets it back
        standoff = carrier is not None and own is not None and own.state != "home" and s.home_rule
        # desperate with their flag in our hands (guide 19 CTF-MULTI-16): the blitz ends at the pickup (desperate), so
        # the carry is the all in: no defender stays home, everyone else screens the carrier
        all_in_carry = carrier is not None and not standoff and s.posture.state in ("all_in", "far_behind")
        if carrier:   # our runner has their flag: bring it home, escort it
            if carrier.id in s.bots:      # (a person carrying it runs it himself: no bot runner home, the escorts on him;
                slots.append(("runner", home, "objective"))   # Boardwalk: they escorted a bot "runner", 25-46 u off)
            esc = (1 if n >= 4 else 0) if standoff else min(2, n - 1)
            if not standoff and CARRY_PLAY:
                # a carry is the team's (the sim on The Pit, 8v8: carriers dead 3-6 s after the pull at the stand, 6-7 of
                # theirs within 15 u and 0-0.4 of ours within 10): three on him from six of us
                esc = max(esc, min(3 if n >= 6 else 2, n - 1))
            if all_in_carry:
                esc = n - 1
            slots += [("escort", carrier.pos, "aggression")] * max(0, esc)
        if own is not None and own.state != "home":   # our flag is out: hunt the carrier or return it
            # research 12 section 3.5: an enemy carrying ours home while theirs is home: everyone but one defender
            # collapses on him (nothing blocks his capture). Live, Boardwalk the empty stand and a runner still
            # going the other way
            collapse = own.state == "carried" and not carrier and (theirs is None or theirs.state == "home")
            k = n - 1 if standoff or collapse else 2
            # (custom, Nov 10, the owner: "hunt the flag carrier, but without back tracking. Like cutting them off";
            # live Adrift, the hunters went back through their base to reach him on the top lane) the cut-offs go to
            # the first point on his way home each beats him to, one per way (intercepts, a slot for that bot); the rest
            # chase him. Before: one straight-line point 10 u ahead with three or more hunters, its point then swapped
            # for the flag's by the bot (Bot.live_point), so every hunter chased
            cuts = s.intercepts(snap, own, k) if CUTOFF and own.state == "carried" else []
            for q, bid in cuts:
                slots.append(("cutoff", q, ("bot", bid)))
            slots += [("hunter", own.pos, "aggression")] * (k - len(cuts))
        else:
            s._cuts = {}
        # (custom, Nov 9, the owner: "Only have a defender if the winning team is up by 2 or more flag captures, and
        # defender count should never be higher than 1 ... always make it the lower difficulty player, Excluding easy")
        # The lead in captures (the score's step: score_unit) is the only thing that decides defending: tied or behind,
        # nobody defends and everyone attacks; up by one, nobody; up by two or more, one defender, the team's lowest
        # difficulty bot that is not Easy (assign_roles, fit "low_tier"), while our flag is home. The team-size count,
        # the plan's "defenders", the extra one after a death at the flag and the turtle at +2 (no runners) are gone.
        # Hunters for a taken flag, the standoff and the collapse on their carrier are unchanged.
        unit = getattr(s, "score_unit", 0) or 1
        lead = s.posture.lead // unit
        # One Flag (one flag in the match, sides swap each round; research 12 O3.13): attacking, there is no flag of
        # ours to defend, so nobody defends; defending, everyone but a forward pair holds it ("push the offense back").
        # Its sides are the round's, not the score's: unchanged
        if s.is_one_flag(snap) and own is not None and not all_in_carry:
            for q in s.defend_posts(own.home if getattr(own, "home", None) is not None else s.map["flags"][s.side],
                                    n - min(2, n // 2)):
                slots.append(("defender", q, "camping"))
        elif own is not None and own.state == "home" and lead >= CTF_DEFEND_LEAD and n >= 2 and not all_in_carry:
            # the area round the flag, from cover, never the stand; first in the list, so no escort or hunter slot
            # takes the lowest tier bot before it (slots are filled in order)
            q = s.defend_posts(own.home if getattr(own, "home", None) is not None else s.map["flags"][s.side], 1)[0]
            slots.insert(0, ("defender", q, "low_tier"))
        if theirs is not None and not carrier:
            rest = n - len(slots)
            nr = 2 if rest >= 5 or (split and rest >= 4) else 1
            slots += [("runner", theirs.pos, "objective")] * nr
            # and two go in with the runner (guide 07's 4v4: runner, lead escort, rear escort, defender; Halopedia:
            # clear the defenders, then grab). Live: lone runners pulled 3 times in 134 s, each carrier dead within
            # 6 s on their stand with nobody inside 10 u (assign_roles points these at the runner)
            slots += [("escort", theirs.pos, "aggression")] * min(2, max(0, rest - nr))
        # everyone else pushes up behind the runners (or holds mid when turtling or resetting)
        eh = theirs.home if theirs is not None else s.map["flags"][enemy]
        push = mid if s.plan.get("stance") == "turtle" else eh + (mid - eh) * 0.45
        lanes = s.map.get("lanes", [])
        if carrier is not None and not standoff and CARRY_PLAY:
            # the carry's screen: one between him and their base holding the chase off his back, the rest a stretch
            # ahead of him on his way home clearing it (not on to their base: there is nothing left to take there)
            way = home - carrier.pos
            d = max(way.flat(), 0.1)
            back = carrier.pos + (eh - carrier.pos) * min(1.0, SCREEN_BACK / max((eh - carrier.pos).flat(), 0.1))
            slots.append(("screen", back, "aggression"))
            push = carrier.pos + way * min(1.0, SCREEN_AHEAD / d)
            split = False
        if split and lanes:
            slots += [("mid", lanes[k % len(lanes)], "aggression") for k in range(n)]
        else:
            slots += [("mid", push, "aggression")] * n
        return slots

    def king_take(s, now, snap):
        """How many of us go into the hill to take it: one more than the men of theirs any of us saw in it (or by
        its edge, 1 u out) in the last 3 s, two at least, all of us at most; kept KING_TAKE_HOLD s after the last such
        sighting (people clear a hill, then hold it); 0 while none of theirs is on it (one scorer, the rest watching)."""
        r = (snap.hill_r or 3.0) + 1.0
        seen = set()
        for b in s.bots.values():
            for k, bel in b.per.beliefs.items():
                p = snap.player(k) if isinstance(k, int) else None
                if (p is not None and p.alive and p.team != s.team and bel.seen and now - bel.t < 3.0
                        and (bel.pos - snap.hill).flat() < r):
                    seen.add(k)
        n = sum(1 for b in s.bots.values() if snap.player(b.id) is not None and snap.player(b.id).alive)
        if seen:
            s.king_on = (now, len(seen))
        last = getattr(s, "king_on", None)
        if last is None or now - last[0] > KING_TAKE_HOLD:
            return 0
        return max(1, min(n, max(2, last[1] + 1)))

    def team_centre(s, snap):
        """Where our living players are on average (None: nobody)."""
        mine = [p.pos for p in snap.players if p.team == s.team and p.alive]
        if not mine:
            return None
        return Vec(sum(q.x for q in mine) / len(mine), sum(q.y for q in mine) / len(mine), sum(q.z for q in mine) / len(mine))

    def intercepts(s, snap, own, k):
        """(custom, Nov 10) Cut-offs on the enemy carrying our flag: [(point, bot id)], at most k (one fewer while one of
        us is within CUT_CHASE_R of him: that one chases). Each of his likely ways home (carrier_routes) gets the bot
        that cuts him off soonest on it: the first point CUT_STEP apart from CUT_MIN_AHEAD on that it reaches CUT_MARGIN_S
        before him (cut_on), by its own walk (a Dijkstra from it, the nav's forward edges, so one-way drops count);
        then other bots on points CUT_SPREAD from those. A bot keeps its point while it still beats him there. Points
        behind him are never on his way, so no cut-off walks back after him. []: nobody can beat him anywhere, he is
        nearly home, or no way is known (all chase, as before)."""
        c = snap.player(own.carrier) if own.carrier not in (None, -1) else None
        side = 1 - s.side
        goal = (s.map.get("returns") or {}).get(side) or s.map["flags"].get(side)
        if c is None or not c.alive or goal is None or dist(c.pos, goal) < CUT_NEAR_GOAL or k <= 0:
            return []
        T = s.terrain()
        routes = s.carrier_routes(c, goal)
        if not routes:
            return []
        blitz = set((getattr(s, "blitz", None) or {}).get("ids", ()))
        mates = []
        for b in s.bots.values():
            p = snap.player(b.id)
            if (p is not None and p.alive and not p.has_flag and b.p.teamwork > 0 and b.id not in blitz
                    and b.id not in snap.vips):
                mates.append((dist(p.pos, c.pos), b.id, p.pos))
        mates.sort(key=lambda m: m[0])
        want = k
        far = max(r[-1][1] for r in routes) + 10.0
        from scipy.sparse.csgraph import dijkstra
        reach = {}
        for d, bid, pos in mates[:CUT_CANDIDATES]:      # (the one by him too: the chaser is whoever is left)
            l, j, i = T._node(pos)
            reach[bid] = dijkstra(T.graph, directed=True, indices=(l * T.nh + j) * T.nw + i, limit=far)
        old = getattr(s, "_cuts", {}) or {}
        out, taken = [], []
        for r in routes:
            best = None
            for bid, rc in reach.items():
                if any(bid == o[1] for o in out):
                    continue
                hit = s.cut_on(T, r, rc, old.get(bid))
                if hit is not None and (best is None or (hit[1], -hit[2]) < (best[1], -best[2])):
                    best = (hit[0], hit[1], hit[2], bid)
            if best is not None:
                out.append((best[0], best[3]))
                taken.append(best[0])
            if len(out) >= want:
                break
        for bid, rc in reach.items():            # more of us than ways: further cut-offs, apart from those
            if len(out) >= want:
                break
            if any(bid == o[1] for o in out):
                continue
            for r in routes:
                hit = s.cut_on(T, r, rc, old.get(bid), avoid=taken)
                if hit is not None:
                    out.append((hit[0], bid))
                    taken.append(hit[0])
                    break
        cut_ids = {bid for _, bid in out}
        if len(out) >= k and any(d < CUT_CHASE_R and bid not in cut_ids for d, bid, _ in mates):
            out = out[:k - 1]      # one of us right by him and not cutting: a hunter slot left for it to chase
        return out

    def cut_on(s, T, route, reach, prev=None, avoid=()):
        """Where a bot whose walk costs are reach waits for him on route (carrier_routes: (point, how far he runs to
        it)): the spot nearest it within CUT_NEAR (on that point's floor) of the first point every CUT_STEP that it gets
        in range of CUT_MARGIN_S before him, as (spot, his run there, the bot's time to spare); prev, its spot from
        before, while it still is in time there; none within CUT_SPREAD of avoid. None: it is in time nowhere on it."""
        import numpy as np
        margin = CUT_MARGIN_S * CUT_RUN
        nxt = CUT_MIN_AHEAD
        last = len(route) - 1
        cost = reach.reshape(T.L, T.nh, T.nw)
        if prev is not None and not any(dist(prev, a) < CUT_SPREAD for a in avoid):
            # its spot from before, while a point of his way ahead within CUT_NEAR of it (its floor) is still one it is
            # in range of first: kept (a new pick every re-plan turned bots round mid-way)
            dp = float(cost[T._node(prev)])
            for q, dc in route:
                if (dc >= CUT_MIN_AHEAD and dist(q, prev) <= CUT_NEAR and abs(q.z - prev.z) < CUT_LEVEL_DZ
                        and math.isfinite(dp) and dp + margin <= dc / CARRIER_PACE):
                    return (prev, dc, (dc / CARRIER_PACE - dp) / CUT_RUN)
        from .terrain import NAV_CELL
        r = int(round(CUT_NEAR / getattr(T, "CELL", NAV_CELL)))     # (in cells; a test's grid has its own size)
        for k, (q, dc) in enumerate(route):
            if dc < nxt and k != last:
                continue
            nxt = dc + CUT_STEP
            if dc < CUT_MIN_AHEAD:
                continue
            # the nearest spot to the bot within CUT_NEAR of q on q's floor: where it waits for him in range
            _, j, i = T._node(q)
            j0, j1, i0, i1 = max(0, j - r), min(T.nh, j + r + 1), max(0, i - r), min(T.nw, i + r + 1)
            with np.errstate(invalid="ignore"):
                ok = T.lwalk[:, j0:j1, i0:i1] & (np.abs(T.lz[:, j0:j1, i0:i1] - q.z) < CUT_LEVEL_DZ)
            jj, ii = np.mgrid[j0:j1, i0:i1]
            ok &= ((jj - j) ** 2 + (ii - i) ** 2 <= r * r)[None]
            sub = np.where(ok, cost[:, j0:j1, i0:i1], np.inf)
            m = int(np.argmin(sub))
            db = float(sub.ravel()[m])
            if not math.isfinite(db) or db + margin > dc / CARRIER_PACE:
                continue
            ml, mj, mi = np.unravel_index(m, sub.shape)
            spot = T._center(int(ml), int(mj) + j0, int(mi) + i0)
            if any(dist(spot, a) < CUT_SPREAD for a in avoid):
                continue
            return (spot, dc, (dc / CARRIER_PACE - db) / CUT_RUN)
        return None

    def carrier_routes(s, c, goal):
        """The ways an enemy carrying our flag (c) may take to goal, each [(point, how far he runs to it)]: the shortest
        from where he is (the nav's field to goal), then, kept per goal for the match, the next shortest from our stand
        (alt_routes) and the enemy's sneak routes reversed (theirs run from their base to our flag), each one he is on
        (CUT_ON_ROUTE), at most CUT_DETOUR the shortest, not CUT_OVERLAP the same as one already in. His is the length
        run, not the nav's cost: the nav prices a drop for us (Adrift, a 1.8 u drop off the top lane costs 28.8) and a
        person just drops; ours stays the cost, so a cut-off it takes is one it surely makes"""
        T = s.terrain()
        if not math.isfinite(float(T._field(goal)[T._node(c.pos)])):
            return []
        pts = [c.pos] + T.path_ahead(c.pos, goal, n=CUT_MAX_STEPS)
        if len(pts) < 2:
            return []
        live = s.line_costs(pts)
        routes = [live]
        for way in s.alt_routes(goal):
            rest = s.route_from(way, c.pos)
            if rest is None or rest[-1][1] > CUT_DETOUR * live[-1][1] + 4.0:
                continue
            if any(s.route_overlap(rest, r) > CUT_OVERLAP for r in routes):
                continue
            routes.append(rest)
        return routes

    @staticmethod
    def line_costs(pts, start=0.0):
        """[(point, the length run to it along pts)], from start."""
        out, d = [], start
        for k, q in enumerate(pts):
            if k:
                d += dist(pts[k - 1], q)
            out.append((q, d))
        return out

    def route_from(s, way, pos):
        """The rest of way (points) from its point nearest pos (height weighs double), as line_costs; None: pos is more
        than CUT_ON_ROUTE off it."""
        best = min(range(len(way)), key=lambda k: (way[k] - pos).flat() + 2.0 * abs(way[k].z - pos.z))
        off = (way[best] - pos).flat() + 2.0 * abs(way[best].z - pos.z)
        if off > CUT_ON_ROUTE or best >= len(way) - 1:
            return None
        return s.line_costs(way[best:], start=dist(way[best], pos))

    @staticmethod
    def route_overlap(a, b):
        """The share of a's points (every CUT_STEP u) within CUT_ALT_R of one of b's (height weighs double)."""
        samp = [q for k, (q, _) in enumerate(a) if k % max(1, int(CUT_STEP / 0.25)) == 0]
        bq = [q for q, _ in b]
        near = sum(1 for q in samp if any((q - o).flat() + 2.0 * abs(q.z - o.z) < CUT_ALT_R for o in bq[::4]))
        return near / max(1, len(samp))

    def alt_routes(s, goal):
        """Other ways from our stand to goal, worked out once per goal: the shortest with every edge within CUT_ALT_R
        of the shortest's own floor costing CUT_ALT_COST times (a second way: Adrift's other level), and the enemy's
        hand-drawn sneak routes reversed, a point a unit."""
        key = (round(goal.x, 1), round(goal.y, 1), round(goal.z, 1))
        cache = s.__dict__.setdefault("_alt_routes", {})
        if key in cache:
            return cache[key]
        ways = []
        stand = s.map["flags"].get(s.side)
        T = s.terrain()
        try:
            first = T.path_ahead(stand, goal, n=CUT_MAX_STEPS) if stand is not None else []
            if len(first) > 8:
                ways.append(s.penalised_way(T, stand, goal, first))
        except Exception:            # (a map with no nav, a test's bare director: no second way)
            pass
        for r in (s.map.get("sneak") or {}).get(1 - s.side, []):
            r = list(reversed(r))
            pts = [r[0]]
            for a, b in zip(r, r[1:]):
                n = max(1, int(dist(a, b)))
                pts += [a + (b - a) * (t / n) for t in range(1, n + 1)]
            if len(pts) >= 2:
                ways.append(pts)
        cache[key] = [w for w in ways if w]
        return cache[key]

    @staticmethod
    def penalised_way(T, stand, goal, first):
        import numpy as np
        from scipy.sparse.csgraph import dijkstra
        mask = np.zeros((T.L, T.nh, T.nw), dtype=bool)
        r = int(CUT_ALT_R / 0.25)
        for q in first[::4]:
            j, i = T._cell(q)
            j0, j1, i0, i1 = max(0, j - r), min(T.nh, j + r + 1), max(0, i - r), min(T.nw, i + r + 1)
            with np.errstate(invalid="ignore"):
                mask[:, j0:j1, i0:i1] |= np.abs(T.lz[:, j0:j1, i0:i1] - q.z) < 1.5
        flat = mask.ravel()
        g = T.graph_to.copy()
        rows = np.repeat(np.arange(g.shape[0]), np.diff(g.indptr))
        g.data = np.where(flat[rows] | flat[g.indices], g.data * CUT_ALT_COST, g.data)
        l, j, i = T._node(goal)
        l, j, i = T._reachable_node(l, j, i, goal.z)
        cost = dijkstra(g, directed=True, indices=(l * T.nh + j) * T.nw + i).reshape(T.L, T.nh, T.nw)
        n = T._node(stand)
        if not np.isfinite(cost[n]):
            return []
        return [T._center(*q) for q in T._down(*n, cost, CUT_MAX_STEPS)]

    def defend_posts(s, home, n):
        """n posts round our flag stand: LiDAR cover spots (the floor in front of a wall) 3-11 u off it on its floor that
        see it, the ones near 6 u first, 3 u apart; then overlooks(); the stand itself only if nothing else is there."""
        key = (round(home.x, 1), round(home.y, 1), n)
        cache = s.__dict__.setdefault("_posts", {})
        if key in cache:
            return cache[key]
        T, eye, out = s.terrain(), Vec(0, 0, 0.6), []
        cs = getattr(T, "cover_spots", None)
        if cs is not None and len(cs):
            for c in sorted(cs.tolist(), key=lambda c: abs(math.hypot(c[0] - home.x, c[1] - home.y) - 6.0)):
                q = Vec(c[0], c[1], c[2])
                if len(out) >= n or abs(math.hypot(q.x - home.x, q.y - home.y) - 6.0) > 5.0:
                    break
                if (3.0 <= dist(q, home) <= 11.0 and abs(q.z - home.z) < 2.0 and T.los(q + eye, home + eye)
                        and all(dist(q, o) >= 3.0 for o in out)):
                    out.append(q)
        out += [q for q in s.overlooks(home, n + 4) if dist(q, home) >= 3.0 and all(dist(q, o) >= 3.0 for o in out)]
        cache[key] = (out + [home] * n)[:n]
        return cache[key]

    def mode_slots(s, now, snap, n):
        """Roles for brain/modes.py's game types (Reach). Territories: two take the nearest zone not ours (the one
        with the fewest enemies seen), one holds each zone we own while we have the numbers, the rest cover the
        target. Assault / Stockpile: our carriers run (assign_roles), two escort; a loose object gets two runners
        and an escort; their carrier gets hunters; two hold our goal. Headhunter (custom, Nov 12): a bot carrying skulls
        enough banks them (hh_bankers; counts estimated, brain/headhunter.py), an enemy seen carrying 3 or more is
        hunted, two take the loose skulls near us, some cover the drop point, the rest hunt. Infection: survivors hold rooms with few ways in, in
        groups (Reach's Safe Haven: the haven); the infected hunt the nearest survivor, a third wait round the corners of
        the survivors' holds."""
        from .modes import zombie_team, holds, pick_holds
        mid = s.map["points"]["mid"]
        foes = [p for p in snap.players if p.team != s.team and p.alive]
        mine = [p for p in snap.players if p.team == s.team and p.alive]
        seen = lambda z: sum(1 for p in foes if dist(p.pos, z) < 12.0)
        centre = lambda: Vec(sum(p.pos.x for p in mine) / len(mine), sum(p.pos.y for p in mine) / len(mine),
                             sum(p.pos.z for p in mine) / len(mine)) if mine else mid
        slots = []
        if snap.mode == "territories":
            zones = snap.obj_zones or [(mid, 3.0, -1)]
            ours = [(z, r) for z, r, o in zones if o == s.team]
            todo = [(z, r) for z, r, o in zones if o != s.team] or ours
            c = centre()
            target, tr = min(todo, key=lambda zr: (seen(zr[0]), dist(zr[0], c)))
            if s.posture.state == "hide_and_hold" and 2 * len(ours) > len(zones):
                # ahead with the clock running out, holding the majority (guide 19 TERR-SYM-07): no new zone is taken,
                # every one we own is held from inside and covered from around
                for k in range(n):
                    z, r = ours[k % len(ours)]
                    slots.append(("defender", s.spread(z, k // len(ours), 0.6 * r), "camping"))
                return slots + [("mid", q, "camping") for q in s.overlooks(ours[0][0], n)]
            slots += [("defender", s.spread(target, k, 0.6 * tr), "objective") for k in range(2)]
            for z, r in ours[:max(0, n - 3)]:
                slots.append(("defender", z, "camping"))
            slots += [("escort", target, "aggression")]
            slots += [("mid", q, "aggression") for q in s.overlooks(target, n)]
            return slots
        if snap.mode in ("assault", "stockpile"):
            items = snap.obj_items
            goals = snap.obj_goals.get(s.team) or []
            enemy_goals = snap.obj_goals.get(1 - s.team) or []
            ours_carried = [it for it in items if it["carrier"] is not None and snap.player(it["carrier"]) is not None
                            and snap.player(it["carrier"]).team == s.team]
            theirs_carried = [it for it in items if it["carrier"] is not None and it not in ours_carried]
            # loose ones we may take: ours or the neutral one (Assault: their bomb sits on their goal until they run it)
            loose = [it for it in items if it["carrier"] is None and it.get("team", 8) in (8, s.team)
                     and it.get("armed") is None]
            if snap.mode == "stockpile":          # a flag already in our goal stays there: only the others are loose
                loose = [it for it in loose if not any(dist(it["pos"], g) < 2.0 for g in goals)]
            # an armed bomb (modes.Watch): theirs on our goal draws all but one onto it to disarm it (guide 19
            # ASS-MULTI-09: "Enemy plants: everyone alive goes to the bomb ... three bots on the bomb disarm it before
            # the fuse"); ours on theirs gets one on it and the rest round it from cover (ASS-MULTI-03: "keep every
            # enemy off the bomb ... Stand on the bomb")
            for it in [it for it in items if it.get("armed") == s.team][:1]:
                slots += [("runner", it["pos"], "objective")] * max(1, n - 1)
            for it in [it for it in items if it.get("armed") == 1 - s.team][:1]:
                slots += [("defender", it["pos"], "camping")] + \
                         [("defender", q, "camping") for q in s.guard_spots(it["pos"], max(1, n - 1))]
            state = s.posture.state
            late_ahead, late_behind = state == "hide_and_hold", state == "all_in"
            if late_ahead and goals and not ours_carried:
                # ahead with the clock running out (guide 19 ASS-MULTI-11: two defenders and no carrier; STOCK-05: all
                # guard): no new run, our goal held (their carrier still hunted)
                for it in theirs_carried:
                    slots += [("hunter", it["pos"], "aggression")] * 2
                k = 2 if snap.mode == "assault" else n
                slots += [("defender", s.spread(goals[0], j, 3.0), "camping") for j in range(k)]
                return slots + [("defender", q, "camping") for q in s.guard_spots(goals[0], n)]
            for it in ours_carried:
                # (the last minute behind, ASS-MULTI-12: the blitz ends at the pickup, so the plant push is the all in)
                slots += [("escort", snap.player(it["carrier"]).pos, "aggression")] * (n - 1 if late_behind else 2)
            for it in theirs_carried:
                slots += [("hunter", it["pos"], "aggression")] * 2
            c = centre()
            for it in sorted(loose, key=lambda it: dist(it["pos"], c))[:2]:
                slots += [("runner", it["pos"], "objective")] * (2 if snap.mode == "assault" else 1)
                slots += [("escort", it["pos"], "aggression")]
            hold = goals if snap.mode == "stockpile" else goals     # Assault: they plant on our goal
            # Assault: no defender the last minute behind (ASS-MULTI-12), one while ours runs the bomb (ASS-NEUT-02: the
            # carrying side's second defender goes up to mid)
            keep = 2 if snap.mode == "stockpile" else 0 if late_behind else 1 if ours_carried else 2
            for g in hold[:1]:
                slots += [("defender", s.spread(g, k, 3.0), "camping") for k in range(keep)]
            if snap.mode == "assault" and enemy_goals:
                slots += [("mid", q, "aggression") for q in s.overlooks(enemy_goals[0], n)]
            slots += [("mid", q, "aggression") for q in s.overlooks(mid, n)]
            return slots
        if snap.mode == "headhunter":
            from .headhunter import HUNT_SKULLS
            drops = [z for z, r, o in (snap.obj_zones or [])] or [mid]
            c = centre()
            hh = getattr(snap, "hh", None)
            near = (hh.bank_zone(c, now) if hh is not None else None) or min(drops, key=lambda z: dist(z, c))
            # (custom, Nov 12) an enemy carrying HUNT_SKULLS or more that one of ours saw in the last 8 s is hunted
            # first: his death drops them all (Reach shows every carrier's count over his head)
            known = {}
            for b in s.bots.values():
                for k, bl in b.per.beliefs.items():
                    if isinstance(k, int) and now - bl.t < 8.0 and (k not in known or bl.t > known[k].t):
                        known[k] = bl
            rich = sorted((p for p in foes if p.id in known and snap.skulls_held.get(p.id, 0) >= HUNT_SKULLS),
                          key=lambda p: -snap.skulls_held.get(p.id, 0))
            for p in rich[:2]:
                slots += [("hunter", known[p.id].pos, "aggression")] * (2 if n >= 4 else 1)
            for sk in sorted((it for it in snap.obj_items if dist(it["pos"], c) < 40.0),
                             key=lambda it: dist(it["pos"], c))[:2]:   # skulls lying where men died
                slots.append(("runner", sk["pos"], "objective"))
            # the drop point covered: those who will bank find it held (the bankers run on their own: hh_bankers)
            slots += [("mid", q, "aggression") for q in s.overlooks(near, max(1, n // 4))]
            return slots + s.slayer_slots(now, snap, n)
        if snap.mode == "infection":
            infected = zombie_team(snap)
            havens = [z for z, r, o in (snap.obj_zones or [])]
            if infected == s.team:
                # (issue #3: run directly at players, or wait around corners for unsuspecting prey; the
                # rally and charge at a group holding well is desperate's / blitz_tick's)
                ambush = [q for q in s.ambush_spots(snap, foes, n // 3) if s.ambush_fresh(now, q)]
                slots += [("defender", q, "camping") for q in ambush]
                for p in sorted((p for p in foes), key=lambda p: dist(p.pos, centre()))[:n]:
                    slots.append(("hunter", p.pos, "aggression"))
                return slots + [("hunter", mid, "aggression")] * n
            if havens:                      # Reach's Safe Haven: the game's own haven
                haven = min(havens, key=lambda z: dist(z, centre()))
                return [("defender", s.spread(haven, k, 2.5), "camping") for k in range(n)]
            # survivors: in groups of 2-3, each in its own hold (a room with the fewest ways in, modes.find_holds),
            # far apart ("for better fun ... separate groups in their own respective areas of the map")
            picked = pick_holds(holds(s.terrain(), s.map["name"]), max(1, round(n / 2.5)))
            if not picked:                  # (still being found: the first seconds of the match)
                return [("defender", s.spread(mid, k, 2.5), "camping") for k in range(n)]
            return [("defender", s.spread(picked[k % len(picked)]["pos"], k // len(picked), 1.0), "camping")
                    for k in range(n)]
        if snap.mode == "regicide":
            # the King (modes.Watch.mark_king, in snap.vips; the game shows him to everyone): hunted by the rest
            # (SLAY-REG-01: his bounty is the best kill on the map); the King himself plays his own game (assign_roles:
            # our VIP is never sent anywhere) and holds back from far fights (Bot: a VIP's)
            king = next((p for p in map(snap.player, snap.vips) if p is not None and p.alive and p.team != s.team), None)
            if king is not None:
                return [("hunter", king.pos, "aggression")] + s.slayer_slots(now, snap, n)
        return s.slayer_slots(now, snap, n)

    def ambush_fresh(s, now, q):
        """A corner is waited at AMBUSH_S at most, then left AMBUSH_S to the hunt (Flood playtests: waits of
        53-279 s, the longest whole rounds, at corners nobody came round)."""
        key = (round(q.x), round(q.y))
        t0 = s.__dict__.setdefault("_ambush_t", {}).get(key)
        if t0 is None or now - t0 > 2 * AMBUSH_S:
            s._ambush_t[key] = t0 = now
        return now - t0 < AMBUSH_S

    def ambush_spots(s, snap, foes, k):
        """Up to k corners to wait round for survivors (the infected; issue #3: wait around corners for
        unsuspecting prey): the ways into the hold a survivor is in (modes.find_holds doors, HOLD_R by walk from its
        middle) that the hold's middle does not see, never two within 2 u."""
        if k <= 0 or not foes:
            return []
        from .modes import holds
        T, eye = s.terrain(), Vec(0, 0, 0.6)
        hs, out = holds(T, s.map["name"]), []
        for p in foes:
            h = min(hs, key=lambda h: dist(h["pos"], p.pos), default=None)
            if h is None or dist(h["pos"], p.pos) > 6.0:
                continue
            for door in h["doors"]:
                if len(out) >= k:
                    return out
                # the door itself, else the nearest floor by it (1.5-3.5 u) out of the middle's sight: round the corner
                for q in [door] + [Vec(door.x + math.cos(a) * r, door.y + math.sin(a) * r, door.z)
                                   for r in (1.5, 2.5, 3.5) for a in (x * math.pi / 4 for x in range(8))]:
                    z = T.nav_z(q.x, q.y, door.z)
                    q = Vec(q.x, q.y, z)
                    if (abs(z - door.z) < 0.6 and T.ground_ok(q.x, q.y, q.z, drop=0.6) and not T.los(h["pos"] + eye, q + eye)
                            and dist(q, h["pos"]) > 3.0 and all(dist(q, o) > 2.0 for o in out)):
                        out.append(q)
                        break
        return out

    def climb_via(s, b, snap, point, used):
        """A runner's way up to a phase 3 core on high (invasion.CLIMBS: a Spire playtest's ways up): its via,
        the start of the least-used way, then the nearest to it, among those no farther from the core than it is (a via
        behind it is dropped at once: Bot.objective_point). Kept while it is still one of them. () where none."""
        from . import invasion
        me = snap.player(b.id)
        climbs = invasion.climbs_for(s.map.get("name"))
        if me is None or not climbs or point.z - min(c.z for c in climbs) < invasion.CLIMB_UP or \
                me.pos.z > point.z - 5.0:
            return ()
        keep = b.order.via[0] if b.order.role == "runner" and b.order.via else None
        k = next((i for i, c in enumerate(climbs) if keep is not None and dist(keep, c) < 0.5), None)
        if k is not None:
            used[k] = used.get(k, 0) + 1
            return b.order.via
        cands = [i for i, c in enumerate(climbs) if dist(c, point) < dist(me.pos, point) - 1.0] or \
            list(range(len(climbs)))
        k = min(cands, key=lambda i: (used.get(i, 0), dist(me.pos, climbs[i])))
        used[k] = used.get(k, 0) + 1
        return (climbs[k],)

    def invasion_slots(s, now, snap, n):
        """Reach Invasion roles (brain/invasion.py). Attackers, phases 1-2: most of the team takes one territory
        together (the one fewer defenders were seen at), two stand in it, the rest cover it from around; with five
        or more one goes to the other territory to split the defence. Phase 3: two go for the core, the carrier
        runs it to the delivery point (assign_roles), the rest escort him (the even ones ahead, clearing the way).
        Defenders: posts at every territory of the phase (the nearer one gets the extra man), hunters on anyone
        inside one; phase 3 the core's stand, hunters on the carrier, a post at the delivery point."""
        zones = snap.inv_zones or [s.map["points"]["mid"]]
        attacking = snap.inv_attackers == s.team
        foes = [p for p in snap.players if p.team != s.team and p.alive]
        seen = lambda z: sum(1 for p in foes if dist(p.pos, z) < 12.0)
        slots = []
        if snap.inv_phase == 3 and snap.inv_core is not None and snap.inv_armed:
            # Breakpoint's bomb armed: the attackers guard it from around it (guide 07, standing-still objectives: the
            # attackers turn purely defensive once it arms), the defenders all go to disarm it
            if attacking:
                return [("defender", s.spread(snap.inv_core, i + 1, 4.0), "camping") for i in range(n)]
            return [("hunter", snap.inv_core, "aggression")] * n
        if snap.inv_phase == 3 and snap.inv_core is not None:
            core, carrier = snap.inv_core, snap.player(snap.inv_core_carrier) if snap.inv_core_carrier is not None else None
            goal = snap.inv_delivery or zones[0]
            # the pile-on: the whole team on the core run, both sides
            if attacking:
                if carrier is not None and carrier.team == s.team:
                    # (the even ones lead toward the delivery point, clearing it: Bot.live_point)
                    slots += [("escort", carrier.pos, "aggression")] * max(2, n - 1)
                else:
                    # the whole team goes for the core together (the pile-on): two runners and the rest covering them
                    # from the cover round it never took it back from its campers (live Spire: it lay loose 176 s; the
                    # sim, Spire with the core dropped where it fell: 0-1 pickups in 4 x 150 s, the runners 8-16 u off
                    # waiting for company, five defenders 2-10 u from it)
                    slots += [("runner", core, "objective")] * n
            else:
                if carrier is not None and carrier.team != s.team:
                    slots += [("hunter", carrier.pos, "aggression")] * max(2, n - 1) + [("defender", goal, "camping")]
                else:
                    # one on the core, the rest on the spots that cover it from around
                    slots += [("defender", core, "camping")]
                    slots += [("defender", q, "camping") for q in s.guard_spots(core, max(1, n - 2))]
                    slots += [("defender", goal, "camping")]
            return slots
        if attacking:
            # one territory per push: kept until the phase moves on or the other one has clearly fewer defenders (it
            # flipped with every sighting and the bots turned round halfway, sim)
            best = min(zones, key=lambda z: (seen(z), dist(z, s.map["points"]["mid"])))
            keep = getattr(s, "inv_target", None)
            keep = next((z for z in zones if keep is not None and dist(z, keep) < 0.5), None)
            radius = lambda z: next((r for q, r in zip(snap.inv_zones, snap.inv_zone_r) if q is z), 2.5)
            inside = lambda z: any(p.team == s.team and p.alive and dist(p.pos, z) <= radius(z) + 0.5
                                   for p in snap.players)
            # a push is seen through: kept while one of us is taking it, and for INV_COMMIT s after it was picked, then
            # while the other has no clear edge in defenders (the sightings were weighed first, so the defence's pile-on
            # turned the attack round mid-capture and it went back and forth between the two: review)
            # ... and while the attack is AT it: one of us within 8 u of it in the last INV_STALL s. The defence piles
            # onto the territory being attacked, so the other always looked emptier: live Boneyard B20 R2, the Spartans'
            # target flipped six times in 250 s (every 20-50 s), 17.9 s in a zone, phase 1 lost; B19 R2 kept one all
            # round and took it (logs/tmp/invasion_regress/targets.py). A stalled attack (none of us near) still moves
            if keep is not None and any(p.team == s.team and p.alive and dist(p.pos, keep) < 8.0 for p in snap.players):
                s.inv_near_t = now
            at_it = keep is not None and now - getattr(s, "inv_near_t", -99.0) < INV_STALL
            if keep is not None and (inside(keep) or now - getattr(s, "inv_target_t", -99.0) < INV_COMMIT
                                     or seen(keep) <= seen(best) + 1 or at_it):
                target = keep
            else:
                target, s.inv_target_t = best, now
            s.inv_target = target
            other = [z for z in zones if z is not target]
            # taking a territory is standing in it: the post role (keep_role holds them inside it), the second bot
            # inside its boundary too (Boneyard's territories are boxes of about 1.75 x 2.5 u)
            tr = radius(target)
            slots += [("defender", s.spread(target, k, 0.6 * tr), "objective") for k in range(2)]
            # the pile-on: a teammate already taking it, or the phase running on, and everyone goes in; once on, it
            # stays on for this territory (the one inside dying turned the team round before 60 s)
            taking = inside(target)
            if taking:
                s.inv_push = target
            if taking or snap.inv_phase_t > PUSH_AFTER or getattr(s, "inv_push", None) is target:
                slots += [("defender", s.spread(target, k + 2, 0.6 * tr), "objective") for k in range(max(0, n - 2))]
                return slots
            if n >= 5 and other:
                slots += [("defender", other[0], "objective")]
            slots += [("escort", target, "aggression")] * 2
            slots += [("mid", q, "aggression") for q in s.overlooks(target, n)]
            return slots
        # defending: hunters on anyone standing in a territory (that contests it), posts on all of them from around
        # it, never on it (live, Boneyard: a defender posted on the centre stood inside all round, median 0.5 u,
        # and no attack ever took a phase: people cover a territory from angles and step in to contest) (all but a
        # post at each other territory pile onto one being taken: two hunters left it to fall)
        taken = [z for z, r in zip(zones, snap.inv_zone_r or [2.5] * len(zones)) if any(dist(p.pos, z) < r + 1.5 for p in foes)]
        for z in taken:
            slots += [("hunter", z, "aggression")] * max(2, (n - (len(zones) - len(taken))) // len(taken))
        per = max(1, n // max(1, len(zones)))
        for i, z in enumerate(sorted(zones, key=lambda z: -seen(z))):
            # from the cover round it (guard_spots), as the core's guards: rings 5 u out with no cover check stood them
            # in the open (review)
            slots += [("defender", q, "camping") for q in s.guard_spots(z, per + (1 if i == 0 else 0), 3.0, 11.0)]
        for z in zones:
            slots += [("mid", q, "camping") for q in s.overlooks(z, n)]
        return slots

    def positions(s):
        """The map's power positions (maps/<map>/positions.json from tools/power_positions.py: height,
        sightlines, cover, escape; guide 01 section 7), else the team's hold spots and mid."""
        pts = s.map.get("positions") or []
        if not pts:
            pts = list(s.map["holds"][s.side]) + [s.map["points"]["mid"], s.map["points"]["mid_hill"]]
        return pts

    def spread(s, point, k, ring=4.0):
        """The k-th bot's own spot near a team point: teammates never share one point (blobs, doorway jams).
        Walkable floor that sees the point, at about `ring` units; else the point."""
        if k == 0:
            return point
        T = s.terrain()
        for tries in range(8):
            a = (k * 2.4 + tries * 0.8) % (2 * math.pi)
            r = ring * (1.0 + 0.25 * (tries % 3))
            q = Vec(point.x + math.cos(a) * r, point.y + math.sin(a) * r, point.z)
            z = T.nav_z(q.x, q.y, q.z)
            # on the point's own floor: Boneyard's territories sit on a platform 2.3 u over another floor, and a spot
            # "beside" one landed under it (the sim's attackers walked to the floor below and gave up)
            if abs(z - point.z) < 0.6 and T.ground_ok(q.x, q.y, q.z, drop=0.6) and \
                    T.los(point + Vec(0, 0, 0.6), q + Vec(0, 0, 0.6)):
                return Vec(q.x, q.y, z)
        return point

    def terrain(s):
        if getattr(s, "_T", None) is None:
            from .maps import terrain
            s._T = terrain(s.map)
        return s._T

    def overlooks(s, point, n):
        """n spots covering a point from outside it (King of the Hill's ring, Oddball's watchers): the map's power
        positions 4-16 u off that see it, nearest first, then spread() rings of 9, 6 and 4 u, never two within 2 u of
        each other (spread gave Boardwalk's hills the same spot twice). Short of spots, the rest go to the point."""
        T, eye = s.terrain(), Vec(0, 0, 0.6)
        out = sorted((q for q in s.positions() if 4.0 <= dist(q, point) <= 16.0 and T.los(q + eye, point + eye)),
                     key=lambda q: dist(q, point))[:n]
        for ring in (9.0, 6.0, 4.0):
            for k in range(1, 7):
                if len(out) >= n:
                    return out
                q = s.spread(point, k, ring)
                if dist(q, point) > 1.0 and all(dist(q, o) > 2.0 for o in out):
                    out.append(q)
        return (out + [point] * n)[:n]

    def guard_spots(s, point, n, near=4.0, far=12.0):
        """n spots guarding a point from around it, on about its floor (1.5 u), that see it: LiDAR's cover spots (floor in
        front of upright walls) first, then rings of 5-11 u; never two within 2.5 u; short of spots, the overlooks."""
        key = (round(point.x, 1), round(point.y, 1), round(point.z, 1), n, near, far)
        cache = s.__dict__.setdefault("_guard", {})
        if key in cache:                                   # (each tick turned all the map's cover spots into Vecs)
            return list(cache[key])
        T, eye = s.terrain(), Vec(0, 0, 0.6)
        sees = lambda q: T.los(q + eye, point + eye)
        cs = getattr(T, "cover_spots", None)
        cover = []
        if cs is not None and len(cs):
            import numpy as np
            d = np.hypot(cs[:, 0] - point.x, cs[:, 1] - point.y)
            cover = [Vec(float(cs[k][0]), float(cs[k][1]), float(cs[k][2]))
                     for k in np.nonzero((d >= near) & (d <= far) & (np.abs(cs[:, 2] - point.z) < 1.5))[0]]
        cand = sorted((q for q in cover if near <= dist(q, point) <= far and sees(q)), key=lambda q: dist(q, point))
        for r in (5.0, 7.0, 9.0, 11.0):
            for k in range(16):
                a = k * math.pi / 8
                x, y = point.x + r * math.cos(a), point.y + r * math.sin(a)
                q = Vec(x, y, T.nav_z(x, y, point.z))
                if abs(q.z - point.z) < 1.5 and T.ground_ok(x, y, q.z, drop=0.6) and sees(q):
                    cand.append(q)
        out = []
        for q in cand:
            if len(out) >= n:
                break
            if all(dist(q, o) > 2.5 for o in out):
                out.append(q)
        if len(out) < n:
            out += s.overlooks(point, n - len(out))
        cache[key] = list(out)
        return out

    def hot_spot(s, now):
        """Where the enemy last was in the zone the team's threat map rates hottest (seen and died in, a level fading 1
        per 5 s), reported in the last 20 s; else None. Where the team last saw him in that zone, not its centre:
        Construct's Mid, most of the map, centres on the pit floor, and every hunter went down there."""
        hot = max(s.threat, key=lambda a: s.threat[a][0] - (now - s.threat[a][1]) / 5, default=None)
        return s.threat_at.get(hot) if hot is not None and now - s.threat[hot][1] < 20 else None

    def likely_enemy(s, now, pts, snap):
        """Where to look for the enemy with no fresh fight to go to (guide 06 spawn rules: they respawn
        near their living teammates and away from us): the newest callout the team heard, else where
        they will spawn (spawn_guess), else the power position nearest their side, else a sweep. Team
        knowledge only, never true positions."""
        heard = [c for c in s.callouts if c.kind in ("seen", "died", "died_at_flag") and now - c.t_event < 25]
        if heard:
            return max(heard, key=lambda c: c.t_event).pos_said
        their = s.map["flags"].get(1 - s.side)
        if getattr(s, "look_their_side", True):
            q = s.spawn_guess(now, snap)
            if q is not None:
                return q
            if their is not None and pts:
                return min(pts, key=lambda q: dist(q, their))
        return s.sweep

    def spawn_guess(s, now, snap):
        """Map brain MAP-08 / CALL-04 and guide 06 ("the enemy will reappear near their living teammates ... and away
        from where the bot's team is standing"): of their spawn points for the mode (all of them on a map whose spawns
        carry no team: Construct's 135 are team 0), the one nearest the living enemies our bots but Easy know of (seen,
        heard, on radar in the last 10 s; the kill feed says who is alive) and far from us, that none of us stands within 5 u
        of or sees from within 40 u. Hunters used to go to the power position nearest their flag. None: no spawns.
        ponytail: one point, not a weighted cluster; the game's spawn weights (guide 06's table) when that matters."""
        sp = s.map["spawns"]["ctf" if snap.mode == "ctf" else "slayer"]
        pool = sp[1 - s.side] if len(sp[1 - s.side]) >= 4 else sp[0] + sp[1]
        us = [p.pos for p in snap.players if p.team == s.team and p.alive]
        alive = {p.id for p in snap.players if p.team != s.team and p.alive}
        them = {}
        for b in s.bots.values():
            if b.p.teamwork <= 0:
                continue           # Easy plays for itself: it calls nothing out, so its eyes are its own
            for k, bl in b.per.beliefs.items():
                if k in alive and now - bl.t < 10.0 and (k not in them or bl.t > them[k].t):
                    them[k] = bl
        T = s.terrain()

        def score(q):
            return min((dist(q, u) for u in us), default=0.0) - 1.5 * min((dist(q, b.pos) for b in them.values()),
                                                                          default=0.0)
        for q in sorted(pool, key=score, reverse=True):
            if all((q - u).flat() > 5.0 and (dist(q, u) > 40.0 or not T.los(u, q)) for u in us):
                return q
        return None

    def slayer_slots(s, now, snap, n):
        """Team Slayer roles and points by score posture (guide 07 Slayer, 01 sections 8 and 12):
        - hold (posture <= 0.35: protecting a lead, enemy about to win, last minute ahead): pairs hold two
          adjacent power positions and let the enemy come; nobody hunts alone.
        - standard: up to two anchors hold nearby power positions; a slayer and his support (a few units behind him)
          go where the fight is; a floater takes the other side (a second position or a sweep).
        - push (posture >= 0.65: behind, all-in): two pairs converge on the fight from two sides.
        Every bot gets its own spot (spread()), so the team never stacks on one point."""
        pts = s.positions()
        heat = s.hot_spot(now)
        slayer = snap.mode == "slayer"
        s.high_alt = {}                   # (custom) slot index -> the high-ground tiers' own spot (assign_roles)
        lost = None
        if slayer and getattr(s, "post", None) is not None:
            # (custom, Nov 10) a post working for the high-ground tiers is held on (POST_EXTEND); one losing us men, left
            if s.post_lost(now):
                lost, s.post_until = s.post, now
            elif now >= s.post_until and s.post_working(now, snap):
                s.post_until = now + POST_EXTEND
        if now >= getattr(s, "post_until", 0.0):
            s.post_until = now + s.rng.uniform(25, 45)
            s.post_since = now
            # map brain MAP-06 / MAP-05: the anchor's post by its score (tools/power_positions.py: floor seen, height,
            # items), twice as likely where it sees the hot zone (where the enemy is now); a flat pick held the 8th
            # spot as often as the best, wherever the fights were
            info = s.map.get("position_info") or []
            w = [i["score"] for i in info] if len(info) == len(pts) else [1.0] * len(pts)
            T = s.terrain()
            w = [max(0.05, v) * (2.0 if heat is not None and T.los(q, heat) else 1.0) for v, q in zip(w, pts)]
            if lost is not None:          # (custom) not straight back to the post we just lost men on
                w = [v * (0.2 if dist(q, lost) < 1.0 else 1.0) for v, q in zip(w, pts)]
            s.post = s.rng.choices(pts, weights=w)[0]
            zones = [z.center for z in s.zones.zones] or [s.map["points"]["mid"]]
            s.sweep = s.rng.choice(zones + list(pts))     # (a zone centre is its lowest floor: the power spots too)
            s.sweep_high = s.rng.choices(pts, weights=w)[0]   # (custom: the high-ground tiers' sweep, a power position)
            s.look_their_side = s.rng.random() < 0.7     # decided per rotation: no flip-flopping
        target = heat if heat is not None else s.likely_enemy(now, pts, snap)
        p = s.posture.value
        post = s.post
        # the score posture picks the formation: careful holds the post and the one beside it, bold pushes in pairs
        second = min((q for q in pts if q != post), key=lambda q: dist(q, post), default=post)
        anchors = snap.mode == "slayer"
        if anchors and n > 1 and second == post and p < 0.65:
            second = s.spread(post, 1)
        if p <= 0.35:
            spots = [post, second]
            count = 2 if second != post else 1
            return [("mid", s.spread(spots[i % len(spots)], i // len(spots)),
                     "anchor" if anchors and i < count else "camping") for i in range(n)]
        if p >= 0.65:
            side = Vec(-(target.y - post.y), target.x - post.x, 0).norm() * 6.0
            fronts = [target + side, target - side]
            return [("hunter", s.spread(fronts[i % 2], i // 2, 3.0), "aggression") for i in range(n)]
        back = (post - target).norm() * 5.0 if dist(post, target) > 1 else Vec(5, 0, 0)
        slots = [("mid", post, "anchor" if anchors else "camping")]
        if anchors and n > 1 and second != post:
            slots.append(("mid", second, "anchor"))
        slots += [("hunter", target, "aggression"), ("hunter", s.spread(target + back, 1, 2.0), "teamwork")]
        perch = s.perch(target) if slayer else None
        if perch is not None:
            s.high_alt[len(slots) - 1] = perch            # (custom) the support, one of the high tiers: from above
        far = max(pts, key=lambda q: min(dist(q, post), dist(q, target)))
        floats = [far, s.sweep]
        for i in range(max(0, n - len(slots))):
            if slayer and i % 2 == 1:     # (custom) the sweep, one of the high tiers: a power position, held
                high = s.sweep if s.sweep in pts else getattr(s, "sweep_high", s.sweep)
                s.high_alt[len(slots)] = s.spread(high, i // 2)
            slots.append(("hunter", s.spread(floats[i % 2], i // 2), "aggression"))
        return slots[:n] if n >= 1 else slots

    def post_working(s, now, snap):
        """(custom, Nov 10) The team's Slayer post still worth holding: held POST_HOLD_MAX s at most, one of the
        high-ground tiers posted on it stands there (ANCHOR_R, not under its floor) and has seen a man in the last
        POST_QUIET s."""
        from .bot import ANCHOR_R, ANCHOR_DZ
        if now - getattr(s, "post_since", now) >= POST_HOLD_MAX:
            return False
        for b in s.bots.values():
            p = snap.player(b.id)
            if (p is None or not p.alive or not profiles.high_ground(b.p) or b.order.role != "mid"
                    or b.order.point is None or dist(b.order.point, s.post) > ANCHOR_R):
                continue
            if ((p.pos - s.post).flat() <= ANCHOR_R and p.pos.z >= s.post.z - ANCHOR_DZ
                    and now - max(b.per.last_seen.values(), default=-1e9) < POST_QUIET):
                return True
        return False

    def post_lost(s, now):
        """(custom, Nov 10) Two of ours fell within POST_LOSS_R u of the post in the last POST_LOSS_S s, since it was
        taken: it is costing us, move on."""
        since = max(getattr(s, "post_since", 0.0), now - POST_LOSS_S)
        return sum(1 for t, q in getattr(s, "fell_at", ()) if t >= since and dist(q, s.post) < POST_LOSS_R) >= 2

    def perch(s, target):
        """(custom, Nov 10) Where to take a fight at target from above: the map's power position nearest it within
        PERCH_MIN-PERCH_MAX u, PERCH_DZ u or more over it, that sees it. None: none such."""
        T, eye = s.terrain(), Vec(0, 0, 0.6)
        return min((q for q in s.positions() if PERCH_MIN <= dist(q, target) <= PERCH_MAX and q.z >= target.z + PERCH_DZ
                    and T.los(q + eye, target + eye)), key=lambda q: dist(q, target), default=None)

    def is_one_flag(s, snap):
        """One Flag CTF: never two flags in this match (the flag keeps its stand while the sides swap each round). In
        CTF both flags stand at the start, and a capture leaves one for a moment: that is not One Flag."""
        n = len(snap.flags or {})
        s.max_flags = max(getattr(s, "max_flags", 0), n)
        return snap.mode == "ctf" and n == 1 and s.max_flags == 1

    def capture_point(s, snap):
        """Where our carrier scores: our flag return where the map has one (Halo 3: Sandtrap's rides its Elephant, 1.2 u
        behind the stand on the bay floor; the carrier stood under the stand 80 s and never scored), else our stand; One
        Flag (one flag in the match) the one away from the flag's own stand (Boardwalk One Flag: the flag stayed on
        red's stand both rounds, blue captured on its own stand)."""
        flags = list((snap.flags or {}).values())
        rets = s.map.get("returns", {})
        if s.is_one_flag(snap) and 0 in s.map["flags"] and 1 in s.map["flags"]:
            t = max((0, 1), key=lambda k: dist(s.map["flags"][k], flags[0].home))
            return rets.get(t) or s.map["flags"][t]
        return rets.get(s.side) or s.map["flags"][s.side]

    def carry_point(s, snap):
        """Where a carrier goes: CTF home (our flag out and the variant needs it home: the base's post farthest from
        where our flag is, off the open stand, until it is back); Oddball a team hold spot far from the enemies seen;
        Invasion the core's delivery point."""
        if snap.mode == "invasion":
            return snap.inv_delivery or s.map["points"]["mid"]
        if snap.mode in ("assault", "stockpile"):
            from .modes import carry_goal
            me = next((p for p in snap.players if p.team == s.team and p.has_flag), None)
            g = carry_goal(snap.mode, snap, s.team, me.pos if me else s.map["points"]["mid"])
            return g or s.map["points"]["mid"]
        if snap.mode != "oddball":
            own = (snap.flags or {}).get(s.team)
            posts = s.map["holds"][s.side][1:]
            if own is not None and own.state != "home" and s.home_rule and posts:
                return max(posts, key=lambda h: dist(h, own.pos))
            return s.capture_point(snap)
        foes = [p.pos for p in snap.players if p.team != s.team and p.alive]
        if s.posture.state == "hide_and_hold" and getattr(s, "odd_spot", None) is not None:
            return s.odd_spot      # ahead, the clock running out: one spot held, no more moves (guide 19 ODD-CORE-11)
        s.odd_spot = max(s.map["holds"][s.side] + [s.map["points"]["mid"]],
                         key=lambda h: min((dist(h, f) for f in foes), default=0.0))
        return s.odd_spot

    # --- the coach (brain/coach.py; guide 10 sections 4, 6, 9): events, the report, asking, applying
    def cid(s, p):
        """A player's id in the coach's report: b<index> for our bots, human1.. for people (6.6: no names)."""
        if p.id in s.bots:
            return f"b{p.id}"
        return f"human{s.human_ids.setdefault(p.id, len(s.human_ids) + 1)}"

    def event(s, now, kind, text):
        s.events.append((now, kind, text))
        del s.events[:-60]

    def tally(s, what, key, n=1):
        if key:
            d = s.match.setdefault(what, {})
            d[key] = d.get(key, 0) + n

    def track_events(s, now, snap):
        """What every player sees: the kill feed, respawns and our flag runs (the report's EVENTS and the
        staleness rules of 9.3), and the match phase (4.4). The announcer's flag events come via report()."""
        last = s.__dict__.setdefault("last_pos", {})
        flags = s.__dict__.setdefault("had_flag", {})
        for p in snap.players:
            ours = p.team == s.team
            was = s.alive_was.get(p.id)
            s.alive_was[p.id] = p.alive
            if p.alive:
                last[p.id] = p.pos
            if ours and p.has_flag and not flags.get(p.id):
                s.event(now, "flag_pulled", f"{s.cid(p)} took their flag")
            flags[p.id] = p.has_flag
            if was is None or was == p.alive:
                continue
            who = s.cid(p) if ours else "enemy"
            if not p.alive:
                s.died_at[p.id] = now
                where = s.zones.name(last[p.id]) if ours and p.id in last else s.belief_zone(p.id, now)
                s.event(now, "death", f"{who} died" + (f" at {where}" if where else ""))
                if ours:
                    s.tally("our_deaths", where)
                    s.tally("bot_deaths", who)
                    if p.id in last:          # (custom: where ours fell lately, post_working)
                        s.__dict__.setdefault("fell_at", []).append((now, last[p.id]))
                        del s.fell_at[:-20]
                else:                                  # a kill: where, and the bot that was fighting him
                    s.tally("our_kills", where)
                    killer = next((b for b in s.bots.values() if b.goal[0] == "fight" and b.goal[1] == p.id), None)
                    if killer:
                        s.tally("bot_kills", f"b{killer.id}")
            else:
                s.event(now, "respawn", f"{who} respawned")
        s.mine_pos = [p.pos for p in snap.players if p.team == s.team and p.alive]    # (item_taken)
        lanes = s.__dict__.setdefault("veh_seen", {})  # their vehicles' lanes: a seen man in a vehicle, a zone every 5 s
        for b in s.bots.values():
            for k, x in b.per.beliefs.items():
                q = snap.player(k) if isinstance(k, int) else None
                if q is not None and x.seen and now - x.t < 0.5 and q.vehicle not in (None, -1):
                    z = s.zones.name(x.pos)
                    if now - lanes.get(z, -99.0) >= 5.0:
                        lanes[z] = now
                        s.tally("enemy_vehicles", z)
        samples = s.match["samples"]                   # the score each minute
        if now >= 60.0 * (len(samples) + 1):
            samples.append((now, *s.score_pair()))
        s.track_objective(now, snap)
        ph = s.match_phase(now, snap)
        if ph != s.phase:
            s.event(now, "phase", f"phase {s.phase} -> {ph}")
            s.phase = ph

    def belief_zone(s, eid, now, within=3.0):
        bs = [b.per.beliefs[eid] for b in s.bots.values() if eid in b.per.beliefs and now - b.per.beliefs[eid].t < within]
        return s.zones.name(max(bs, key=lambda x: x.t).pos) if bs else ""

    def match_phase(s, now, snap):
        """4.4: opening (first 20 s), objective crisis (our flag out, their ball carrier), endgame (last 60 s
        or two kills from the limit), else mid-game."""
        if now < 20:
            return "opening"
        f = snap.flags.get(s.team) if snap.mode == "ctf" else None
        bc = snap.player(snap.ball_carrier) if snap.mode == "oddball" and snap.ball_carrier is not None else None
        if (f and f.state != "home") or (bc and bc.team != s.team):
            return "objective crisis"
        # the six modes: the enemy carries the core, a bomb or a flag, or their bomb is armed on our goal
        if snap.mode in NEW_MODES and any("carried by the enemy" in st or "armed on our goal" in st
                                          for n, q, st in s.objective_points(now, snap)):
            return "objective crisis"
        top = max(snap.score.values()) if snap.score else 0
        unit = getattr(s, "score_unit", 0) or 1
        if (snap.time_left is not None and snap.time_left <= 60) or (snap.score_limit and snap.score_limit - top <= 2 * unit):
            return "endgame"
        return "mid-game"

    def score_pair(s):
        last = getattr(s, "score_last", {}) or {}
        return last.get(s.team, 0), max((v for k, v in last.items() if k != s.team), default=0)

    def sighting(s, now, within=5.0):
        """Where the team saw an enemy last, within `within` seconds (the bots' own beliefs)."""
        bs = [x for b in s.bots.values() for x in b.per.beliefs.values() if now - x.t < within]
        return max(bs, key=lambda x: x.t).pos if bs else None

    def hill_contested(s, now, snap):
        """An enemy the team's bots saw in the hill in the last 4 s: only then does the whole team go in (one scorer is
        enough on an empty hill; two in it is one more death to a grenade for no more points)."""
        return snap.hill is not None and any(
            isinstance(k, int) and now - x.t < 4.0 and dist(x.pos, snap.hill) < max(snap.hill_r, 1.0)
            for b in s.bots.values() for k, x in b.per.beliefs.items())

    def seen_near(s, now, z, r=12.0, within=8.0):
        """Enemies the team's bots believe within r of z in the last `within` s (team knowledge: the report and the
        plays' preconditions never read where the enemy really is)."""
        return len({k for b in s.bots.values() for k, x in b.per.beliefs.items()
                    if isinstance(k, int) and now - x.t < within and dist(x.pos, z) < r})

    def objective_points(s, now, snap):
        """The objective's named points for the commander: the report's OBJECTIVE line and its order targets (V4:
        "push territory 2", "hold our goal"). [(name, pos, state words)], team knowledge only (enemies by belief)."""
        from .modes import zombie_team
        m, out = snap.mode, []
        seen = lambda z: f"enemy seen {s.seen_near(now, z)}"
        team_of = lambda pid: snap.player(pid).team if pid is not None and snap.player(pid) else None
        if m == "invasion":
            if snap.inv_phase == 3 and snap.inv_core is not None:
                t = team_of(snap.inv_core_carrier)
                out.append(("core", snap.inv_core, "armed" if snap.inv_armed else "carried by us" if t == s.team else
                            "carried by the enemy" if t is not None else "on its stand or loose"))
                if snap.inv_delivery is not None:
                    out.append(("delivery", snap.inv_delivery, "where the core is delivered"))
            else:
                out += [(f"territory {k + 1}", z, seen(z)) for k, z in enumerate(snap.inv_zones or [])]
        elif m in ("territories", "headhunter", "infection"):
            word = {"territories": "territory", "headhunter": "drop", "infection": "haven"}[m]
            for k, (z, r, o) in enumerate(snap.obj_zones or []):
                own = ("ours, " if o == s.team else "neutral, " if o == -1 else "theirs, ") if m == "territories" else ""
                out.append((f"{word} {k + 1}", z, own + seen(z)))
            if m == "headhunter":
                out += [(f"skulls {k + 1}", it["pos"], "lying") for k, it in enumerate(snap.obj_items or [])]
        elif m in ("assault", "stockpile"):
            word, goals = ("bomb" if m == "assault" else "flag"), snap.obj_goals.get(s.team) or []
            for k, it in enumerate(snap.obj_items or []):
                t = team_of(it["carrier"])
                st = ("armed on our goal" if it.get("armed") == s.team else "armed on their goal"
                      if it.get("armed") is not None else "carried by us" if t == s.team else "carried by the enemy"
                      if t is not None else "in our goal" if m == "stockpile" and any(dist(it["pos"], g) < 2.0 for g in goals)
                      else "loose")
                out.append((f"{word} {k + 1}", it["pos"],
                            ("theirs, " if m == "assault" and it.get("team", 8) not in (8, s.team) else "") + st))
            out += [("our goal", g, "") for g in goals[:1]]
            out += [("their goal", g, "") for g in (snap.obj_goals.get(1 - s.team) or [])[:1]]
        return out

    def track_objective(s, now, snap):
        """An objective event for the six modes (the team's event log): Invasion's phase or core changing hands, a
        territory flipping, a bomb or flag taken or armed."""
        if snap.mode not in NEW_MODES:
            return
        sig = tuple(f"{n}: {st.split(', enemy seen')[0]}" for n, q, st in s.objective_points(now, snap)
                    if st and not st.startswith("enemy seen")) + ((snap.inv_phase, snap.inv_attackers) if snap.mode == "invasion" else ())
        old = getattr(s, "obj_sig", None)
        s.obj_sig = sig
        if old is not None and old != sig:
            s.event(now, "objective", ("objective: " + "; ".join(x for x in sig if isinstance(x, str)))[:111])

    @staticmethod
    def band(x):
        return "full" if x >= 0.9 else "half" if x >= 0.4 else "low" if x > 0.05 else "none"

    @staticmethod
    def ago(sec):
        return f"{int(sec // 60)}:{int(sec % 60):02d}"

"""Equipment, armor abilities and powerups: when a bot uses its own and how it works around the
enemy's..

Rules: guide 08 (use-now, hold and bait tables, each item's counter), guide 01 section 6, guide 02
(Halo 3 equipment plays, Reach and Halo 4 abilities), guide 07 (modes). Tier ladder, guide 09 "Act:
abilities": obvious cues only (novice) -> use-now triggers (average) -> use-now and hold rules plus
bait rules (strong) -> all plus sneaky uses (top). A novice's uses are the bad ones guide 02 names
(armor lock at full shield in the open, sprinting into rooms, a hologram at a man already looking).

A bot knows what a player sees: an armor lock's glow, a dome, a beeping mine, a sprinter's speed, a
jetpacker hanging in the air, the radar static of a camo user nearby, a runner that never shoots.
Ability timings (activation mode, energy drain and recharge) come from the editing kits' own tags
(brain/equipment_tags.json from tools/equipment_types.py); radii and durations of Halo 3 equipment
are the guide's "about" values (its kit holds no equipment tags here)."""
import json
import math
import os

from .core import Vec, angles_to, dist, eye, wrap

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = json.load(open(os.path.join(HERE, "equipment_tags.json")))

# kind -> (where it deploys, seconds it lasts, radius in world units). Guide 08: bubble "about 15 ft
# across", power drain "a 15 ft radius" for about 4 s, regenerator 15 ft for about 15 s, trip mine
# "never stand within 20 ft", flare about 3 s, jammer about 15 s, Reach camo jams radar 10 units
# (its tag's noise radius), drop shield "like the Halo 3 Bubble Shield", about 15 s
ITEM = {
    # Halo 3 equipment: single-use pickups, one slot
    "bubble_shield": ("feet", 20.0, 0.75), "power_drain": ("throw", 4.0, 1.5), "regenerator": ("feet", 15.0, 0.75),
    "trip_mine": ("feet", 600.0, 2.0), "deployable_cover": ("front", 600.0, 0.5), "radar_jammer": ("throw", 15.0, 8.0),
    "flare": ("throw", 3.0, 3.0), "grav_lift": ("front", 15.0, 0.5),
    # Reach and Halo 4 armor abilities (recharge)
    "armor_lock": ("self", 5.0, 1.5), "sprint": ("self", 4.0, 0.0), "jetpack": ("self", 4.0, 0.0),
    "active_camo": ("self", 30.0, 10.0), "hologram": ("aim", 10.0, 0.0), "drop_shield": ("feet", 15.0, 0.75),
    "evade": ("dash", 0.4, 0.0), "thruster": ("dash", 0.4, 0.0), "promethean_vision": ("self", 2.0, 12.0),
    "hardlight_shield": ("self", 5.0, 0.0), "regen_field": ("feet", 10.0, 0.6), "autosentry": ("front", 8.0, 8.0),
}
TRIP_KEEP = 3.0     # u off an enemy trip mine (Kit.avoid): live Rat's Nest s178, one went off on a bot at 2.0 u
HEALS = {"regenerator", "drop_shield", "regen_field"}           # heal shields inside (both teams)
DOMES = {"bubble_shield", "drop_shield"}                         # shots do not cross the dome
TEAM_ITEMS = {"regenerator", "drop_shield", "deployable_cover", "regen_field"}   # hold them for the regroup
DEFENSIVE = {"armor_lock", "bubble_shield", "hardlight_shield", "thruster", "evade"}
EXPLOSIVE_AIMED = {"rockets", "spartan_laser", "fuelrod", "incineration_cannon", "railgun", "plasma_launcher",
                   "missile_pod", "binary_rifle"}
SNIPERS = {"sniper", "beam_rifle", "binary_rifle", "focus_rifle"}
LUNGERS = {"sword", "gravity_hammer"}
# a Flood survivor's hardlight shield (the owner, Nov 5): short blocks, the gun between them
SURV_BLOCK_S = 0.6       # one block
SURV_SHOOT_S = 1.2       # the gun before the next block
SURV_MELEE_R = 1.8       # the melee on the let-go reaches him
CORNER_R, CORNER_SIDES = 1.3, 5   # walls within this on at least this many of 8 sides: backed into a corner
CQB = {"shotgun", "sword", "gravity_hammer", "scattershot", "excavator"}
INFECTED_DASH_R = 11.0   # u: an infected thrusts / evades in at a survivor it fights from this near (6.5 u up)
THRUST_REACH = 3.5      # u a thruster dash carries a Spartan (H4; the evade's 3.0-3.4 u): its end point
NADE_BLAST = 3.0         # u: a frag's blast a bot gets out of (guide 08 "never stand within 20 ft" of a mine, the frag less)
NADE_FUSE_SEEN = 1.5     # s a grenade seen landing is still to go off (a frag's fuse about 1.5-2 s)
OS_PUSH = 20.0          # s of overshield push (EQ-OS-02: the first decay step, then back to balanced)
REGEN_REACH = 4.0        # u: an enemy this near walks into our regenerator's mist (EQ-REGEN-03)
THROW_RANGE = 4.5        # Halo 3 equipment "deploys in front of the player with a short throw" (guide 08)
PLACED = {"autosentry", "regen_field", "drop_shield", "hologram", "thruster", "evade"}   # no second tap to stop
# held down while in use whatever the tag says: Reach's sprint tag reads "toggle", but the game sprints only while the
# button is down
HELD = {"sprint"}
JET_RISE = 5.3      # u: the player's jetpack climb from standing (Reach: 5.3 u in 3.9 s; 7.6 with a jump first)
# the tank a flight starts on (Kit.plan), an emergency excepted: a person lets the pack refill. Live Spire 20261105-143525,
# 930-970 s: bots 2, 4 and 8 pressed "jetpack up the ledge" 0.6-0.7 s after each 4 s hold, on the tag's 0.1 minimum
# (0.09-0.11 in the model), the game's on-state up 27-36 of ~105 ticks, 0.1-1.5 u climbed (owner: "not allowing their
# jetpack to recharge before using it"); 66 of the match's 275 presses under half a tank. Refill from empty: 6 s (0.15/s)
JET_FULL = 0.9

# How each kind takes its button, per game (the player: "be able to differentiate between equipment you press once to
# activate and the ones you have to hold, like armor lock and jet packs"):
#   "tap"   one tick: on with one press, off with another (the tag's toggle mode) or it runs out on its own
#   "press" held this many seconds, then let go: the game starts it on the press and it runs on its own (the player's taps
#           of his ability key, Reach collector files-31, logs/tmp/owner_presses.py: evade median 0.17 s (10-90%
#           0.14-0.21) and on 0.73 s after; hologram 0.21 s; drop shield 0.19 s; Halo 3 equipment: one press, press-only
#           in maps/_inputs/h3.json)
#   "hold"  held as long as the use lasts: the jetpack to the height or the touchdown, armor lock until the danger passes
#           or the meter ends, sprint while its reason lasts, the hardlight shield while shot
# Live (Reach, the player's Spire match 012320, logs/tmp/eq_trace.py): the tap kinds came on (camo 36 of 37
# presses within 0.5 s, sprint 71 of 164); every kind whose tag says "hold" never did (armor lock 0 of 50, evade 0 of 183,
# hologram 0 of 135, jetpack 0 of 27, drop shield 0 of 3): those need the hold bit (act.ability), below.
H3_KINDS = ("bubble_shield", "power_drain", "regenerator", "trip_mine", "deployable_cover", "radar_jammer", "flare",
            "grav_lift", "invisibility", "auto_turret")
USE = {
    "h3": {k: ("press", 0.1) for k in H3_KINDS},
    "reach": {"sprint": ("hold", 0.0), "jetpack": ("hold", 0.0), "armor_lock": ("hold", 0.0),
              "active_camo": ("tap", 0.0), "drop_shield": ("press", 0.25), "evade": ("press", 0.2),
              "hologram": ("press", 0.2)},
    "h4": {"thruster": ("press", 0.2), "jetpack": ("hold", 0.0), "hardlight_shield": ("hold", 0.0),
           "promethean_vision": ("tap", 0.0), "autosentry": ("tap", 0.0), "regen_field": ("tap", 0.0),
           "hologram": ("press", 0.2), "active_camo": ("tap", 0.0)},
    "h2a": {"active_camo": ("tap", 0.0)},
}


def use_of(game, kind):
    """("tap" | "press" | "hold", seconds a press is held) for a kind in a game (USE); a kind not listed by its tag's
    activation mode (toggle: tap; hold: hold), else a press. A press of a hold-mode kind lasts its tag's warmup and 0.2
    s more: let go before the warmup ends and the game stops it unstarted (FUN_18047fda8 stops an ability whose bit 8
    clears). the player's drop shield (warmup 0.5 s; collector, logs/tmp/owner_press_detail.py): held 1.06 and 1.44 s it
    read on 0.49 / 0.51 s and went down; of his 0.16-0.21 s taps three read on only while held and three never, and at
    621.0 s (184455) he tapped, then 0.3 s later pressed again and held 1.32 s"""
    u = USE.get(game, {}).get(kind)
    if not u:
        mode = TAGS.get(game, {}).get(kind, {}).get("activation_mode")
        u = ("tap", 0.0) if mode == "toggle" else ("hold", 0.0) if mode == "hold" else ("press", 0.1)
    if u[0] == "press" and hold_bit(game, kind):
        u = ("press", max(u[1], TAGS[game][kind].get("warmup_time", 0.0) + 0.2))
    return u


def hold_bit(game, kind):
    """Whether the game reads this kind's button as a held level as well as the press (Reach: action +0x08 bit 8, which
    the game's own input sets only for abilities whose tag is in hold mode, ghidra/hr_ability_input.c FUN_18005df80; the
    unit runs the ability while that bit is set, FUN_18047fda8). Sent as act.ability (maps/_inputs/reach.json "ability")."""
    return TAGS.get(game, {}).get(kind, {}).get("activation_mode") == "hold"


# jetpack fall brake
JET_BRAKE = 1.4     # u/s^2 the jetpack takes off a fall: the player's lift on it (Reach Spire 184455, 403.5-404.9 s:
                    # 0.43 -> 2.23 u/s up in 1.3 s, collector); INFERRED the same while falling (thrust less gravity)
SAFE_LAND = 5.0     # u/s down at touchdown taken as safe: the nav's own 3 u drop (MAX_DROP) at Reach's 4.1 u/s^2
JET_FLY = 2.3       # u/s across while jetting: the player's 2-3 u forward in a 1.0-1.5 s climb


FIGHT_JETS = ("jetpack after him", "jetpack to the high ground", "jetpack up and over to cover", "brake the fall",
              "jetpack up out of the lunge")   # flights a man in sight does not cut short


def brake_speed(h):
    """The fastest fall (u/s down) the jetpack can still brake to SAFE_LAND in h units of height left."""
    return math.sqrt(SAFE_LAND * SAFE_LAND + 2.0 * JET_BRAKE * max(0.0, h))


def jet_hold(rise):
    """Seconds to hold the jetpack to climb `rise` units, at the player's rate (0.7 s a unit, 0.6-4 s)."""
    return max(0.6, min(4.0, 0.7 * rise + 0.2))
RUN_SPEED = 2.25                 # guide 06: Halo 3 / H2 run 2.25 units a second (Reach / H4 2.2)
LONG_WALK = 15.0                 # an Easy bot's sprint: a goal this far (Reach's sprint lasts 4 s, about 14 u, by its tag)

# H3 equipment pickup priority (guide 08 table: a bot carrying a higher one does not swap down)
PICKUP_RANK = {"bubble_shield": 7, "power_drain": 6, "regenerator": 5, "trip_mine": 4, "grav_lift": 3,
               "deployable_cover": 2, "flare": 1, "radar_jammer": 1}
# Halo 3 equipment tag names (map placements) -> kind
NAMES = {"bubbleshield_equipment": "bubble_shield", "powerdrain_equipment": "power_drain",
         "regenerator_equipment": "regenerator", "tripmine_equipment": "trip_mine", "gravlift_equipment": "grav_lift",
         "deployable_cover": "deployable_cover", "superflare_equipment": "flare", "jammer_equipment": "radar_jammer"}


def game_of(map_name):
    """The title from our map folder names (maps/h3_*, reach_*, ...; CE maps have no prefix)."""
    for g in ("h2a", "h2", "h3", "odst", "reach", "h4"):
        if map_name.startswith(g + "_"):
            return g
    return "ce"


def level(prof):
    """Guide 09 tier ladder for abilities, by the tier's tactics: 0 obvious cues, 1 use-now
    triggers, 2 plus hold and bait rules, 3 plus sneaky uses."""
    t = prof.tactics
    return 0 if t < 0.15 else 1 if t < 0.6 else 2 if t < 0.9 else 3


class Energy:
    """An armor ability's charge from its tag: activation costs, drain while on, recharge after
    the recovery time. Halo 3 equipment: one use (the slot empties)."""
    def __init__(s, game, kind):
        t = TAGS.get(game, {}).get(kind, {})
        s.mode = t.get("activation_mode", "hold")
        s.cost = -t.get("activation_energy_cost", -1.0)
        s.drain = -t.get("active_energy_rate", 0.0)
        s.charge = t.get("inactive_energy_rate", 0.1)
        s.need = t.get("minimum_activation_energy", 1.0)
        s.recovery = t.get("energy_recovery_time", 2.0)
        s.level, s.on, s.off_at = 1.0, False, -9.0

    def ready(s):
        return s.level >= max(s.need, 0.01)

    def tick(s, now, dt, on):
        if on and not s.on:
            s.level -= max(0.0, s.cost)
        if on:
            s.level -= s.drain * dt
            if s.level <= 0.0:
                s.level, on, s.off_at = 0.0, False, now    # run dry: the recovery time runs from here (Halo 4's 1 s)
        elif s.on:
            s.off_at = now
        elif now - s.off_at >= s.recovery:
            s.level = min(1.0, s.level + s.charge * dt)
        s.on = on
        return on


def facing_me(e, me, tol):
    yaw, pitch = angles_to(eye(e), me.pos + Vec(0, 0, 0.35))
    return math.hypot(wrap(yaw - e.yaw), pitch - e.pitch) < tol


class Kit:
    """One bot's equipment brain: its own item (use planner, energy) and what it makes of the
    enemy's (perceived states, counters). bot.py calls perceive() first each tick, act() after the
    goal's movement and aim are set, and threat_mod / can_shoot / grenade_spot inside the fight."""
    def __init__(s, prof, game):
        s.p, s.game, s.lvl = prof, game, level(prof)
        s.kind, s.energy = "", None
        s.hold_until, s.press = 0.0, None     # a held ability: until when; the plan being carried out
        s.cool = {}                           # kind -> not again before (Halo 3 throws, our own pacing)
        s.still_since = {}                    # enemy id -> since when it has not moved (stationary enemy)
        s.straight = {}                       # enemy id -> (direction, since): a runner that never turns
        s.shot_decoy = {}                     # enemy id -> when we shot the suspected decoy once
        s.decoys = set()                      # ids we know are decoys (shot once and it vanished, or PV)
        s.real_until = {}                     # enemy id -> a suspect that took the shot and stayed: real
        s.toggled = False                     # a toggle ability we switched on
        s.attacker = None                     # who is shooting us (Perception.hurt_by): no decoy, that one
        # the game receives our equipment button / Halo 4's sprint button (live: only where decoded,
        # tools/live_bots.py sets these; the simulator models every ability). Without the button a planned
        # armor lock only froze the bot in the open, no lock, no shots (the player's Reach game: 32 locks,
        # 98% of those ticks standing still and silent)
        s.pressable, s.sprint_ok = True, True
        # holograms can be among the players (the simulator). The live readers list players only, so
        # there every "decoy" is a man: the one-shot test only cost top bots shots (tools/live_bots.py)
        s.decoys_listed = True
        s.blind_until = 0.0                   # a flare in the eyes
        s.jammed_until = 0.0                  # radar full of fakes (jammer, a camo user near)
        s.why = None                          # the last use, for the observer
        s.os_from = None                      # since when our own shield reads over full (an overshield)
        s.unread = set()                      # kinds whose on-state live_bots stopped trusting (ABILITY_READ["bad"])

    # ------------------------------------------------------------------ what the bot sees
    def perceive(s, bot, now, me, snap):
        """Enemy states a player can read, and the tells: a flare going off in view, radar static,
        a decoy (runs straight, never shoots; or it vanished at the first hit)."""
        if me.equipment != s.kind:
            s.kind = me.equipment
            s.energy = Energy(s.game, s.kind) if s.kind in TAGS.get(s.game, {}) else None
        s.attacker = getattr(bot.per, "attacker_id", None)
        for d in snap.deployed:
            if d["team"] == me.team:
                continue
            end = d["t"] + ITEM.get(d["kind"], ("", 0.0, 0.0))[1]
            if d["kind"] == "flare" and dist(me.pos, d["pos"]) < ITEM["flare"][2] and now < end:
                yaw, _ = angles_to(me.pos, d["pos"])
                if abs(wrap(yaw - me.yaw)) < 0.6:
                    # looked into it: blind while it burns; a strong player turns away after the first
                    # second (guide 08: "turn away, back into cover, listen for footsteps")
                    s.blind_until = max(s.blind_until, end if s.lvl < 2 else min(end, d["t"] + 1.0))
            if d["kind"] == "radar_jammer" and dist(me.pos, d["pos"]) < ITEM["radar_jammer"][2] and now < end:
                s.jammed_until = now + 0.5
                if s.lvl == 0 and me.tracker and ("fake", id(d)) not in bot.per.beliefs:
                    # the fake red dots: a novice goes after one (guide 08: "trust line of sight")
                    from .bot import Belief
                    a = bot.rng.uniform(0, 2 * math.pi)
                    bot.per.beliefs[("fake", id(d))] = Belief(d["pos"] + Vec(math.cos(a), math.sin(a), 0) * 4.0,
                                                              Vec(), now, False, "radar")
        for e in snap.players:
            if e.team == me.team or not e.alive:
                continue
            if (s.game in ("reach", "h4", "h2a") and e.equipment == "active_camo" and e.ability_on
                    and dist(e.pos, me.pos) < ITEM["active_camo"][2]):
                s.jammed_until = now + 0.5            # Reach / H4 camo jams nearby radar: the tell
                if s.lvl >= 2:
                    # the static centres on him: stop and look there, grenade or melee the spot (guide 08)
                    from .bot import Belief
                    j = Vec(bot.rng.uniform(-1.5, 1.5), bot.rng.uniform(-1.5, 1.5), 0)
                    bot.per.beliefs[("static", e.id)] = Belief(e.pos + j, Vec(), now, False, "static")
            moving = e.vel.flat() > 0.3
            if moving:
                s.still_since.pop(e.id, None)
            else:
                s.still_since.setdefault(e.id, now)
            if moving and e.vel.flat() > 1.5:
                ang = math.atan2(e.vel.y, e.vel.x)
                d0 = s.straight.get(e.id)
                if d0 is None or abs(wrap(ang - d0[0])) > 0.25:
                    s.straight[e.id] = (ang, now)
            else:
                s.straight.pop(e.id, None)
        for k in list(s.shot_decoy):                  # shot once: gone = a hologram, still there = real
            e = snap.player(k)
            if e is None:
                s.decoys.add(k)
                del s.shot_decoy[k]
            elif not e.alive or now - s.shot_decoy[k] > 0.6:
                # dead is a man who died (a hologram leaves no body, it vanishes). Taking the dead for
                # holograms stopped bots shooting that player for the rest of the match (the player's Reach
                # game: the 3 bots fighting him when he died at 175 s never fired at him again, 0 of 251)
                s.real_until[k] = now + 10.0
                del s.shot_decoy[k]
        if me.equipment == "promethean_vision" and me.ability_on:
            from .bot import Belief
            for e in snap.players:                    # PV: walls do not hide them, decoys show as decoys
                if e.team != me.team and e.alive and dist(e.pos, me.pos) < ITEM["promethean_vision"][2]:
                    if e.decoy:
                        s.decoys.add(e.id)
                    elif not (e.id in bot.per.beliefs and bot.per.beliefs[e.id].seen):
                        bot.per.beliefs[e.id] = Belief(e.pos, e.vel, now, False, "pv")

    def posture(s, now, me, post):
        """The posture this bot decides by: AGGRESSIVE (0.9) for OS_PUSH s from its own overshield coming on (EQ-OS-02:
        "use it immediately ... the first 20 s it accepts 1v2 fights at close range"), then the team's (post) again.
        Easy too: it is the game's shield, not a plan."""
        if me.shield > 1.05:
            if s.os_from is None:
                s.os_from = now
        else:
            s.os_from = None
        return max(post, 0.9) if s.os_from is not None and now - s.os_from < OS_PUSH else post

    def decoy_suspect(s, now, e):
        """A runner holding one line for 1.5 s that has not hurt us: what guide 08 calls a hologram
        (strong bots read it; novices chase every one). Only where holograms exist (Reach, Halo 4)."""
        if e.id in s.decoys:
            return True
        if (s.game not in ("reach", "h4") or s.lvl < 2 or not s.decoys_listed or e.has_flag
                or s.real_until.get(e.id, 0.0) >= now):
            return False
        if e.id == s.attacker:
            return False                              # it shot us: a man, not a hologram
        st = s.straight.get(e.id)
        return st is not None and now - st[1] > 1.5

    def state(s, now, e, snap):
        """What the bot reads off an enemy it sees."""
        inside = next((d["kind"] for d in snap.deployed if d["kind"] in HEALS | DOMES
                       and dist(e.pos, d["pos"]) < ITEM[d["kind"]][2]), None)
        return dict(locked=e.equipment == "armor_lock" and e.ability_on,
                    hardlight=e.equipment == "hardlight_shield" and e.ability_on,
                    sprinting=e.vel.flat() > RUN_SPEED * 1.3 and e.vehicle == -1,
                    flying=e.equipment == "jetpack" and e.ability_on,
                    os=e.shield > 1.05, inside=inside, decoy=s.decoy_suspect(now, e))

    # ------------------------------------------------------------------ counters (fight)
    def threat_mod(s, bot, now, me, e, snap):
        """Guide 08 bait rules and counters as threat weights: an armor-locked enemy is a timer, not a
        target; a decoy is shot once and ignored; a sprinter cannot shoot (shoot him first); a
        jetpacker cannot strafe (an easy kill); a hardlight user cannot shoot back (flank, not a
        threat now); an overshield is not an even trade alone. Novices weigh none of it."""
        if s.lvl == 0:
            return 1.0
        st = s.state(now, e, snap)
        v = 1.0
        if st["locked"]:
            v *= 0.1
        if st["decoy"]:
            v *= 0.05 if e.id in s.decoys or e.id in s.shot_decoy else 0.6
        if st["sprinting"] and facing_me(e, me, 0.6):
            v *= 1.4
        if st["flying"]:
            v *= 1.3
        if st["hardlight"]:
            v *= 0.5
        if st["os"] and s.lvl >= 2:
            v *= 0.7
        return v

    def can_shoot(s, now, me, e, snap):
        """No shots that cannot hurt: at an armor-locked enemy (strong and up hold fire at once, an
        average bot after a second of wasted bullets), into a dome from outside it (shots do not
        cross), at a decoy already shot once."""
        if s.lvl == 0:
            return True
        st = s.state(now, e, snap)
        if st["locked"]:
            first = s.__dict__.setdefault("locked_seen", {}).setdefault(e.id, now)
            if s.lvl >= 2 or now - first > 1.0:
                return False
        else:
            getattr(s, "locked_seen", {}).pop(e.id, None)
        for d in snap.deployed:
            if d["kind"] in DOMES:
                r = ITEM[d["kind"]][2]
                if (dist(e.pos, d["pos"]) < r) != (dist(me.pos, d["pos"]) < r):
                    # the dome stops the shot. A Reach drop shield breaks under fire, so an average
                    # bot shoots it down; strong and up walk in instead (fight_move); the Halo 3
                    # bubble never breaks: nobody shoots it from outside (guide 08)
                    return s.lvl == 1 and d["kind"] == "drop_shield"
        if e.id in s.decoys or (e.id in s.shot_decoy and now - s.shot_decoy[e.id] > 0.1):
            return False                      # a decoy: one shot to test it, then wait and see
        if st["decoy"]:
            s.shot_decoy.setdefault(e.id, now)
        return True

    def fight_move(s, bot, now, me, e, snap, act):
        """Where to stand against what he used: back off to Medium band from an armor lock (never
        stand next to it, reload, wait for the end), walk into a dome to melee him (strong and up:
        never shoot it from outside), step out of a power drain, never step into a heal field he
        holds from outside Short band (bait rule). Returns a note or None."""
        d = dist(me.pos, e.pos)
        for dp in snap.deployed:
            # inside our own dome and he is outside: the dome stops our shots too. Recharge, melee
            # whoever walks in, and step out to shoot once the shield is back (guide 02: "walk out of
            # the shield to shoot, never shoot from inside")
            r = ITEM.get(dp["kind"], ("", 0, 0))[2]
            if (dp["kind"] in DOMES and dp["team"] == me.team and dist(me.pos, dp["pos"]) < r
                    and dist(e.pos, dp["pos"]) >= r and s.lvl >= 1):
                if me.shield > 0.95:
                    # shields full: out on the side away from him (EQ-BUBBLE-03; it stepped out toward him before, and at
                    # 0.6 shield, into his sights half charged)
                    bot.steer(me, dp["pos"] - (e.pos - dp["pos"]).norm() * (r + 0.4), act, True)
                    return "own dome: step out away from him"
                act.forward, act.strafe = 0.0, 0.0
                return "own dome: recharge inside"
        if s.lvl == 0:
            return None
        st = s.state(now, e, snap)
        if st["locked"]:
            if d < 5.0:
                away = (me.pos - e.pos).norm()
                bot.steer(me, me.pos + away * 6.0, act, True)
            act.reload = True
            return "armor lock: back off and reload"
        for dp in snap.deployed:
            r = ITEM.get(dp["kind"], ("", 0, 0))[2]
            if dp["kind"] == "power_drain" and dp["team"] != me.team and dist(me.pos, dp["pos"]) < r + 0.3:
                away = (me.pos - dp["pos"]).norm()
                bot.steer(me, me.pos + away * 4.0, act, True)
                return "power drain: step out of it"
            if dp["kind"] in DOMES and dp["team"] != me.team and dist(e.pos, dp["pos"]) < r:
                if s.lvl >= 2 and d < 5.0:
                    bot.steer(me, dp["pos"], act, True)        # walk in: melee him inside (guide 08)
                    if d < 1.3:
                        act.melee = True
                    return f"{dp['kind']}: walk in and melee"
        return None

    def grenade_spot(s, now, me, e, snap):
        """Grenade counters (strong and up): one beside an armor lock (it will not stick, the splash
        lands when the lock ends), one into the heal field or regenerator he stands in, one at a
        hardlight user's feet."""
        if s.lvl < 2:
            return None
        st = s.state(now, e, snap)
        if st["locked"] or st["hardlight"] or st["inside"] in HEALS:
            return e.pos
        return None

    def avoid(s, me, snap):
        """Spots to keep out of when moving: enemy trip mines (beeping), a power drain going off."""
        if s.lvl == 0:
            return []
        # a power drain takes everyone's shields, ours too ("throw and back out of the radius"); a trip mine is kept
        # TRIP_KEEP off (live Rat's Nest s178: one went off on a bot 2.0 u from it)
        return [(d["pos"], TRIP_KEEP if d["kind"] == "trip_mine" else ITEM[d["kind"]][2]) for d in snap.deployed
                if d["kind"] == "power_drain" or d["kind"] == "trip_mine" and d["team"] != me.team]

    def hazards(s, me, snap):
        """avoid() for the route planner (Terrain.nav hazards): ((x, y, z, r), ...), rounded so routes are cached."""
        return tuple((round(p.x, 1), round(p.y, 1), round(p.z, 1), r) for p, r in s.avoid(me, snap))

    # ------------------------------------------------------------------ using our own
    @staticmethod
    def cornered(bot, me):
        """Backed into a corner: walls within CORNER_R on CORNER_SIDES of 8 sides (no room to strafe out of a lunge)."""
        try:
            T = bot.air_terrain()
            return sum(T.clearance(me.pos, k * math.pi / 4, far=CORNER_R + 0.2) < CORNER_R for k in range(8)) >= CORNER_SIDES
        except Exception:                      # (no level data: a bot in a test, a map without a heightmap)
            return False

    def situation(s, bot, now, me, snap):
        seen = [snap.player(k) for k in bot.per.visible_enemies()]
        seen = [e for e in seen if e is not None and e.alive and not (e.id in s.decoys)]
        mates = [p for p in snap.players if p.team == me.team and p.alive and p.id != me.id and dist(p.pos, me.pos) < 10]
        hit = now - getattr(bot, "hit_at", -9.0) < 0.8
        x = dict(seen=seen, mates=mates, hit=hit, cracked=me.shield < 0.3,
                 incoming=next((e for e in seen if e.weapon in EXPLOSIVE_AIMED and 4.0 < dist(e.pos, me.pos) < 30.0
                                and facing_me(e, me, 0.12)), None),
                 lunge=next((e for e in seen if e.weapon in LUNGERS and dist(e.pos, me.pos) < 4.5 and facing_me(e, me, 0.5)), None),
                 splatter=next((e for e in snap.players if e.team != me.team and e.alive and e.vehicle != -1
                                and dist(e.pos, me.pos) < 7.0 and (me.pos - e.pos).norm().x * e.vel.x
                                + (me.pos - e.pos).norm().y * e.vel.y > 3.0), None),
                 sniper=next((e for e in seen if e.weapon in SNIPERS and dist(e.pos, me.pos) > 12.0 and facing_me(e, me, 0.15)), None),
                 still=next((e for e in seen if now - s.still_since.get(e.id, now) > 2.0), None),
                 os=next((e for e in seen if e.shield > 1.05), None))
        # a grenade about to go off by us: one seen landing (snap.grenades: the simulator's; live none are read) or our own
        # (Bot.own_grenade's spot), any team's (they hurt everyone)
        nades = [g["pos"] for g in snap.grenades if now - g["t"] < NADE_FUSE_SEEN]
        own = getattr(bot, "nade_at", None)
        if own is not None and now < own[1]:
            nades.append(own[0])
        x["nade"] = min((p for p in nades if (p - me.pos).flat() < NADE_BLAST and abs(p.z - me.pos.z) < 2.0),
                        key=lambda p: (p - me.pos).flat(), default=None)
        goal, arg = bot.goal
        known = [b for k, b in bot.per.beliefs.items() if not (isinstance(k, int) and b.seen) and now - b.t < 6.0]
        x["push"] = (not seen and goal in ("hunt", "objective") and isinstance(arg, Vec)
                     and any(dist(b.pos, me.pos) < 12.0 for b in known))
        x["push_at"] = min((b.pos for b in known), key=lambda q: dist(q, me.pos), default=None)
        x["holding"] = goal in ("hold", "objective") and isinstance(arg, Vec) and dist(me.pos, arg) < 4.0 and (
            goal == "hold" or bot.order.role == "defender")
        x["carrying"] = me.has_flag
        x["fight"] = goal == "fight" and bot.per.beliefs.get(arg) is not None
        tgt = snap.player(arg) if goal == "fight" else None
        x["target"] = tgt
        x["losing"] = bool(tgt and (len(seen) > 1 or tgt.shield + tgt.health > me.shield + me.health + 0.3))
        x["winning"] = bool(tgt and len(seen) == 1 and tgt.shield + tgt.health < me.shield + me.health - 0.3)
        x["watched"] = any(facing_me(e, me, 0.3) for e in seen)
        x["moving"] = goal in ("objective", "item", "roam", "hunt") and not x["holding"]
        # (a man remembered past 25 u is no reason to walk: any memory at all, a radar dot or a callout across the map,
        # blocked 64% of the moving sprint decisions in Spire, guide 20 review)
        x["travel"] = x["moving"] and not seen and not any(dist(b.pos, me.pos) < 25.0 for b in known)
        return x

    def plan(s, bot, now, me, snap):
        """(kind, how, point, hold seconds, why) to use now, or None. Survival triggers first, then
        the tactical ones (guide 08 use-now table), each gated by the tier ladder."""
        k = s.kind
        if not s.pressable or not k or k not in ITEM or now < s.cool.get(k, 0.0):
            return None
        if bot.p.tier == "novice" and k != "sprint":
            return None            # Easy uses no equipment or armor ability; it sprints a long walk
        if s.energy is not None and not s.energy.ready():
            return None
        x = s.situation(bot, now, me, snap)
        lvl = s.lvl
        cover = None
        low = k == "jetpack" and s.energy is not None and s.energy.level < JET_FULL   # only an emergency flies (JET_FULL)

        def no_cover(within=None):
            """No cover near enough: the bot's reach (as decide()'s retreat), or a set distance (guide
            08: a bubble "only when no cover is within 10 ft", one unit)."""
            nonlocal cover
            if cover is None:
                threats = [e.pos for e in x["seen"]] or [me.pos]
                c = bot.cover_from(me, threats)
                cover = c if c is not None else False
            reach = within if within is not None else 1.5 + 2.5 * bot.p.tactics
            return cover is False or dist(me.pos, cover) > reach

        def side(e):
            """Square to the line from e to us: where a dash leaves his aim."""
            to = (e.pos - me.pos).norm()
            return me.pos + Vec(-to.y, to.x, 0) * 3.0

        def dash(e):
            """Where a dash out of e's aim ends: evade, the square step (EQ-EVADE-02); a thruster only into cover within
            a thrust (THRUST_REACH) of us, the end point the cover itself (EQ-THRUST-02: "only thrusts when the end point
            has cover within 1 m of it; a thrust into open ground is a slow strafe"), else None."""
            if k != "thruster":
                return side(e)
            return None if no_cover(THRUST_REACH) else cover

        def mist_ours():
            """No enemy in sight near enough to walk into the mist (EQ-REGEN-03)."""
            return not any(dist(e.pos, me.pos) < REGEN_REACH for e in x["seen"])

        # Infection survivor (INF-SURV-05, Halopedia): never armor lock against the infected, it only waits for the pack
        survivor = snap.mode == "infection" and snap.infected >= 0 and me.team != snap.infected

        goal, arg = bot.goal
        if k == "sprint":                              # Reach's sprint is an armor ability
            # held to 4 s while its reason lasts (the player's 9 Reach sprints: Shift held 1.6-4.0 s, median 2.4,
            # 3.2-3.4 u/s to his 2.3 run; a 1 s hold, then the 1 s cool, pressed bots' sprints 2-5 times in 6 s)
            why = s.sprint_wish(bot, x, me)
            return (k, "self", None, 4.0, why) if why else None
        # novices: obvious cues only, and the bad uses (guide 02: "locking at full shield in the open")
        if lvl == 0:
            if x["hit"] and k in ("armor_lock", "bubble_shield", "drop_shield", "regenerator", "regen_field",
                                  "hardlight_shield") and not (survivor and k in ("armor_lock", "hardlight_shield")):
                return (k, ITEM[k][0], None, 2.0, "shot at: used it")
            if k == "active_camo" and (x["travel"] or x["fight"]):
                return (k, "self", None, 3.0, "camo on, running")
            if k == "hologram" and x["seen"]:
                return (k, "aim", x["seen"][0].pos, 0.1, "hologram at a man who sees it")
            wp = getattr(bot, "wp", None)
            if k == "jetpack" and not low and (x["fight"] or wp is not None and wp.z - me.pos.z > 0.8
                                   and (wp - me.pos).flat() < 3.0):
                return (k, "self", None, 1.0, "jetpack in the open")
            return None
        # 0. a grenade by us: dash out of the blast, up out of it, or lock (EQ-EVADE-01 "grenade at feet", EQ-JET-01
        # "escape a grenade ... by going up"; a thruster too: the blast, not the open, is the danger here)
        if x["nade"] is not None:
            off = me.pos - x["nade"]
            off = off.norm() if off.flat() > 0.2 else Vec(math.cos(me.yaw + math.pi), math.sin(me.yaw + math.pi), 0)
            if k in ("evade", "thruster"):
                return (k, "dash", me.pos + Vec(off.x, off.y, 0) * 3.0, 0.1, "dash out of the grenade")
            if k == "jetpack":
                return (k, "self", None, 1.0, "jetpack up out of the grenade")
            if k == "armor_lock" and not survivor and (x["nade"] - me.pos).flat() < 2.0:
                return (k, "self", None, 1.5, "armor lock: grenade at my feet")
        # 1. survive: rocket or laser aimed at us, a vehicle about to hit us, a sword or hammer lunge
        danger = x["incoming"] or x["splatter"] or x["lunge"]
        if danger is not None:
            if k == "jetpack" and (x["lunge"] is not None or survivor and x["seen"]):
                # up out of the charge (EQ-JET-01: "escape ... a melee charge by going up"; INF-SURV-05: the survivor's
                # escape, fly up and shoot down)
                return (k, "self", None, 1.2, "jetpack up out of the lunge")
            if k == "armor_lock" and not survivor:
                return (k, "self", None, 2.0 if x["lunge"] is None else 1.2, "armor lock: " + (
                    "rocket / laser" if x["incoming"] else "vehicle" if x["splatter"] else "lunge"))
            # (a survivor never shields a lunge: the Flood lunge all game, and a shield up is a gun down. Live, the
            # owner's Blood Cavern Flood 20261105-225014: "using the hardlight shield more than shooting", 104 blocks;
            # it shoots the lunger, as armor lock's rule for survivors already said)
            if k == "hardlight_shield" and x["splatter"] is None and (
                    x["lunge"] is None and x["incoming"] is not None or x["lunge"] is not None and lvl >= 2 and not survivor):
                # (not against a vehicle: EQ-HLS-04, "a Hardlight Shield does not stop a Warthog; the bot steps aside")
                return (k, "self", None, 1.5, "hardlight: block it")
            if k == "hardlight_shield" and survivor and x["lunge"] is not None and x["splatter"] is None:
                # a survivor shoots the Flood; a short block (SURV_BLOCK_S, then SURV_SHOOT_S of gun before the next)
                # only in the owner's three cases (Nov 5): reloading or out of ammo ("shield block > melee": the melee
                # comes on the let-go, Kit.act), swarmed by 2+ lunging Flood ("looking for openings to shoot"), or
                # backed into a corner
                i = me.weapons.index(me.weapon) if me.weapon in (me.weapons or []) else -1
                empty = 0 <= i < len(me.mag or []) and me.mag[i] == 0 or 0 <= i < len(me.ammo or []) and me.ammo[i] == 0
                swarm = sum(1 for e in x["seen"] if e.weapon in LUNGERS and dist(e.pos, me.pos) < 4.5) >= 2
                if empty:
                    return (k, "self", None, SURV_BLOCK_S, "survivor: block, then melee")
                if swarm:
                    return (k, "self", None, SURV_BLOCK_S, "survivor: swarmed, block and shoot the gaps")
                if s.cornered(bot, me):
                    return (k, "self", None, SURV_BLOCK_S, "survivor: cornered, block")
            if k in ("thruster", "evade") and dash(danger) is not None:
                return (k, "dash", dash(danger), 0.1, "dash out of the line")
            if k == "thruster" and x["lunge"] is not None:
                # a sword or prongs lunging at us: a thrust sideways out of it, cover or not (the cover rule is for a
                # gunfight: open ground is no danger from a lunge). Live, the owner's Flood games: survivors with
                # thrusters met a Flood within 4.5 u for 162-231 s a game and never thrust away
                return (k, "dash", side(x["lunge"]), 0.1, "thrust out of the lunge")
            if k == "bubble_shield" and x["lunge"] is None:
                return (k, "feet", None, 0.1, "bubble: blocks it")
            if k == "deployable_cover" and x["incoming"] is not None:
                return (k, "front", x["incoming"].pos, 0.1, "cover toward the rocket")
        if low:
            return None              # the grenade and the lunge above; the fall brake is jet_brake's (JET_FULL)
        # Armor Lock is a melee-weapon proximity response, independent of our shields or recent damage.
        if (k == "armor_lock" and not survivor and any(
                e.weapon in LUNGERS and dist(e.pos, me.pos) <= 6.0 for e in x["seen"])):
            return (k, "self", None, 2.0, "armor lock: sword or hammer within 6 units")
        # 2. Shield popped while being shot: dash out of his aim or into cover; with no cover near,
        # a heal field, bubble or regenerator.
        if x["cracked"] and x["hit"]:
            close = next((e for e in x["seen"] if dist(e.pos, me.pos) < 8.0), None)
            if k == "thruster" and not no_cover():
                return (k, "dash", cover, 0.1, "thruster to cover")
            if k == "evade" and close is not None:
                return (k, "dash", side(close), 0.1, "dash out of his aim, shield down")
            if k == "bubble_shield" and no_cover(1.0):
                return (k, "feet", None, 0.1, "shield down, no cover within 10 ft: bubble")
            if no_cover():
                if k in ("drop_shield", "regen_field"):
                    return (k, "feet", None, 0.6, "shield down, no cover: heal field")
                if k == "regenerator" and (x["winning"] or x["mates"] or lvl < 2) and mist_ours():
                    return (k, "feet", None, 0.1, "regenerator: winning the trade")
        if k == "evade" and x["hit"] and me.shield < 0.6:
            # the player's evades under fire (7 of 27 at shield 0.6 or less, a man 1.6-9 u off, sideways or back)
            close = next((e for e in x["seen"] if dist(e.pos, me.pos) < 9.0), None)
            if close is not None:
                return (k, "dash", side(close), 0.1, "evade out of the fire")
        if k == "bubble_shield":
            flag = next((f for t, f in snap.flags.items() if t != me.team and f.state != "carried"
                         and dist(f.pos, me.pos) < 3.0), None)
            if flag is not None and (x["seen"] or x["hit"]):
                # down before the grab, under fire (H3-CTF-07: it "buys time for a Mongoose or Warthog to arrive")
                return (k, "feet", None, 0.1, "bubble before the grab")
            if x["seen"] and any(m.shield < 0.2 and dist(m.pos, me.pos) < 2.0 for m in x["mates"]):
                return (k, "feet", None, 0.1, "bubble over a teammate, shield down")    # EQ-BUBBLE-01 (a)
        if k == "power_drain":
            ride = next((e for e in snap.players if e.team != me.team and e.alive and e.vehicle != -1
                         and dist(e.pos, me.pos) < THROW_RANGE + 1.0 and e.id in bot.per.beliefs), None)
            if ride is not None:
                return (k, "throw", ride.pos, 0.1, "drain the vehicle, board it")         # EQ-DRAIN-01 (a)
            grp = next((e for e in x["seen"] if dist(e.pos, me.pos) < THROW_RANGE
                        and sum(1 for o in x["seen"] if dist(o.pos, e.pos) < 6.0) >= 2
                        and not any(dist(m.pos, e.pos) < ITEM[k][2] for m in x["mates"])), None)
            if grp is not None:
                return (k, "throw", grp.pos, 0.1, "drain the group")                     # EQ-DRAIN-01 (b)
        # (hold rules, strong and up: team items are not dropped alone, they wait for the regroup; armor lock, thruster
        # and bubble are kept for the moments above and below. Below the broken-shield rules: above them it kept a
        # strong bot's drop shield, regen field and regenerator for a regroup it did not live to see, guide 20 review)
        if lvl >= 2 and k in TEAM_ITEMS and not x["mates"] and not x["holding"]:
            return None
        # 3. about to push a held room: drain, flare, jammer, a hologram first, PV
        if x["push"] and x["push_at"] is not None:
            p = x["push_at"]
            toss = dist(me.pos, p) < THROW_RANGE           # Halo 3 equipment is a short throw
            if (k == "power_drain" and toss
                    and not any(dist(m.pos, p) < ITEM["power_drain"][2] for m in x["mates"])):
                return (k, "throw", p, 0.1, "power drain the room first")
            if k == "flare" and toss and (lvl < 2 or x["mates"]):
                return (k, "throw", p, 0.1, "flare before the push")
            if k == "radar_jammer" and toss and (lvl < 2 or x["mates"]):
                return (k, "throw", p, 0.1, "jam their radar for the push")
            if k == "hologram" and not x["watched"]:
                return (k, "aim", p, 0.1, "hologram round the corner first")
            if k == "promethean_vision":
                return (k, "self", None, 2.0, "PV before the corner")    # (guide 02: a 2 s pulse)
            if k == "active_camo" and not me.tracker:
                # moving in only where nobody has radar (EQ-RCAMO-02: the jam is the tell; radar on, camo goes on in
                # position, below): SWAT and other no-radar variants
                return (k, "self", None, 6.0, "camo for the approach")
        # 4. a sniper on our lane
        if x["sniper"] is not None:
            if k == "flare":
                # thrown his way: it flashes in his scope. (Only "within 4.5 u", a sniper 12 u off or more: never)
                return (k, "throw", x["sniper"].pos, 0.1, "flare the sniper")
            if k == "deployable_cover":
                return (k, "front", x["sniper"].pos, 0.1, "cover across the sniper lane")
            if k == "hologram":
                return (k, "aim", x["sniper"].pos, 0.1, "hologram to bait the sniper")
            if k == "thruster" and dash(x["sniper"]) is not None:
                return (k, "dash", dash(x["sniper"]), 0.1, "thruster across the lane")
        # 5. holding an objective: regenerator, a mine on the route, drop shield, regen field, sentry
        if x["holding"] and (x["seen"] or x["hit"]):
            # the drop shield goes down in the objective as the fight there starts; the other heals once the shield is
            # down to 0.6
            if k == "drop_shield" or (k == "regen_field" or k == "regenerator" and mist_ours()) and me.shield < 0.6:
                return (k, "feet", None, 0.6, "shield the hold" if k == "drop_shield" else "heal the hold")
            if k == "autosentry":
                return (k, "front", x["seen"][0].pos if x["seen"] else None, 0.1, "sentry on the flank")
            if k == "armor_lock" and not survivor and any(dist(e.pos, me.pos) < 2.0 for e in x["seen"]):
                return (k, "self", None, 2.0, "armor lock on the stand")
        if k == "trip_mine" and not x["seen"] and any(
                e.team != me.team and e.alive and e.vehicle != -1 and e.id in bot.per.beliefs for e in snap.players):
            # they drive: the mine on a route people drove (guide 08: "mines on vehicle routes"; the player's flag, Halo
            # 3: bots to use all equipment); maps/<map>/rides.json's drive cells
            road = s.road_near(bot, me)
            if road is not None:
                return (k, "front", road, 0.1, "trip mine on their vehicle route")
        if x["holding"] and k == "trip_mine" and not x["seen"]:
            route = x["push_at"] or (me.pos + Vec(math.cos(me.yaw), math.sin(me.yaw), 0) * 2.0)
            return (k, "front", route, 0.1, "trip mine on their route")
        # 6. carrying the flag
        if x["carrying"]:
            if k == "bubble_shield" and x["hit"]:
                return (k, "feet", None, 0.1, "bubble on the run")
            if (k == "thruster" and not x["seen"] and isinstance(arg, Vec) and goal == "objective"
                    and 1.5 < (arg - me.pos).flat() < THRUST_REACH):
                # the last metres onto the capture point (EQ-THRUST-03), not whenever unseen
                return (k, "dash", arg, 0.1, "thruster with the flag onto the point")
        # 7. a stationary enemy in sight (sneaky ones are for the best: grav lift under him)
        if x["still"] is not None:
            e = x["still"]
            if k == "grav_lift" and lvl >= 3 and dist(e.pos, me.pos) < 3.0:
                return (k, "front", e.pos, 0.1, "grav lift under him")
            if k == "hologram" and not x["watched"] and dist(e.pos, me.pos) > 6.0:
                return (k, "aim", e.pos, 0.1, "hologram to pull him out")
            if k == "autosentry":
                return (k, "front", e.pos, 0.1, "sentry to pin him")
        # 8. an overshield: drain it
        if x["os"] is not None and k == "power_drain" and dist(x["os"].pos, me.pos) < THROW_RANGE:
            return (k, "throw", x["os"].pos, 0.1, "drain his overshield")
        # 9. in a fight: the regenerator while winning up close; hardlight when shot and losing; past 6 u a hologram
        # while he looks elsewhere (EQ-HOLO-01) and a sentry on him (EQ-SENTRY-01)
        if x["fight"] and x["target"] is not None:
            d = dist(x["target"].pos, me.pos)
            if k == "regenerator" and x["winning"] and d < 12.0 and mist_ours():
                # (EQ-REGEN-03: never where the enemy can also stand in it; before, it went down with him within 4 u)
                return (k, "feet", None, 0.1, "regenerator: winning, out of his reach")
            if k == "hardlight_shield" and x["losing"] and len(x["seen"]) == 1 and x["hit"] and 4.0 < d < 20.0:
                # one man in front only (EQ-HLS-02: "never hold it in a fight with enemies on two sides")
                return (k, "self", None, 1.5, "hardlight: shot and losing")
            if (k in ("evade", "thruster") and 3.0 < d < 6.5 and x["lunge"] is None
                    and x["target"].weapon not in LUNGERS     # (never in onto a sword: survivors with shotguns dashed
                    and (me.weapon in CQB or x["target"].shield <= 0.05)):   # into the Flood, live Blood Cavern)
                # in to close: our close-range gun, or his shield down for the melee finish (EQ-THRUST-01's melee
                # finish; the player's evades forward)
                return (k, "dash", me.pos + (x["target"].pos - me.pos).norm() * 3.0, 0.1, "dash in to close")
            if (k in ("thruster", "evade") and 6.5 <= d < (14.0 if x["hit"] else INFECTED_DASH_R)
                    and snap.mode == "infection" and me.weapon in LUNGERS):
                # the infected run a survivor down with every dash they have (owner, Nov 4: "the flood should use their
                # thrusters a little more"; live, his three Flood games: 13-21 thrusts in 16-20 Flood bot-minutes
                # while 213-274 s were spent 4-14 u from a survivor and closing). Shot at: in, across his aim; else
                # straight at him from INFECTED_DASH_R; the dash-in above takes the last metres. The charge paces it
                # (Halo 4's thruster needs a full one: ~5 s apart)
                to = (x["target"].pos - me.pos).norm()
                across = Vec(-to.y, to.x, 0) * (1.0 if getattr(bot, "strafe_dir", 1) > 0 else -1.0) if x["hit"] else Vec()
                return (k, "dash", me.pos + (to + across).norm() * 3.0, 0.1,
                        "Flood: thrust in, across his aim" if x["hit"] else "infected: dash in at him")
            if k == "hologram" and d > 6.0 and not x["watched"]:
                return (k, "aim", x["target"].pos, 0.1, "hologram to draw his eyes")
            if k == "autosentry" and d > 6.0:
                return (k, "front", x["target"].pos, 0.1, "sentry on him")
        if k == "jetpack" and lvl >= 1:
            fj = s.fight_jet(bot, now, x, me, arg)
            if fj is not None:
                return (k, "fly", fj[0], min(4.0, jet_hold(fj[0].z - me.pos.z) + 0.3), fj[1])
        # 10. unseen on the way: camo for a run to an objective 15+ u off (Invasion attackers, runners: EQ-RCAMO-04),
        # Promethean Vision with a man remembered within 20 u (EQ-PV-01), the jetpack up to a goal 2+ u up within 15 u
        if (k == "active_camo" and not x["seen"] and not me.tracker and goal == "objective" and isinstance(arg, Vec)
                and dist(arg, me.pos) > 15.0
                and (bot.order.role == "runner" or snap.mode == "invasion" and snap.inv_attackers == me.team)):
            return (k, "self", None, 6.0, "camo for the objective run")
        if (k == "promethean_vision" and not x["seen"] and x["push_at"] is not None
                and dist(x["push_at"], me.pos) < 20.0):
            return (k, "self", None, 2.0, "PV: where is he")
        # jetpack: up a ledge the route climbs (skip the ramp), short pulses, and not where anyone can see us (guide 02:
        # "pulses it in short bursts to stay low and behind cover"; a flyer cannot strafe, so guide 08's counter shoots
        # him). Novices fly in the open held for the height to climb, as the player holds it (Reach: 1.6 u in 1.0 s, 1.9
        # in 1.2-1.5, 2.4 in 1.3, moving forward 2-3 u; 5.3 u straight up in 3.9 s, 7.6 with a jump first): 0.7 s a
        # unit, 0.6-4 s. The 0.5 s pulse before lifted a bot a fraction of a ledge
        wp = getattr(bot, "wp", None)
        if (k == "jetpack" and not x["seen"] and wp is not None and wp.z - me.pos.z > 0.8
                and (wp - me.pos).flat() < 3.0):
            return (k, "self", None, jet_hold(wp.z - me.pos.z), "jetpack up the ledge")
        if (k == "jetpack" and lvl >= 1 and not x["seen"] and x["moving"] and not me.has_flag and s.energy is not None
                and s.energy.level >= 0.9 and (wp is None or wp.z > me.pos.z - 2.0)):
            dn = s.descent(bot, me, arg)
            if dn is not None:
                # off the edge toward the goal below with a full pack, kept for the last of the fall; not when the walk
                # is already on its way down (its next point 2 u or more under us)
                s.descent_land = dn[1]
                return (k, "descend", dn[0], 6.0, "jetpack down off the top")
        fly = s.fly_to(bot, x, me, arg)
        if fly is not None:
            # straight up and over to a goal the walk winds round to (stairs, a hill, a ramp). Steered at it (act
            # "fly"); the hold is the climb or the flight across, whichever is longer
            rise, d = arg.z - me.pos.z, (arg - me.pos).flat()
            return (k, "fly", fly, min(4.0, max(jet_hold(rise), d / JET_FLY + 0.3)), "jetpack over the stairs")
        if (k == "jetpack" and x["travel"] and isinstance(arg, Vec) and 2.0 <= arg.z - me.pos.z <= JET_RISE
                and (arg - me.pos).flat() < 15.0):
            return (k, "self", None, jet_hold(arg.z - me.pos.z), "jetpack up to the goal")
        if (k == "active_camo" and me.tracker and not x["seen"] and goal in ("hold", "objective") and isinstance(arg, Vec)
                and dist(arg, me.pos) < 1.5 and me.vel.flat() < 0.5 and x["push_at"] is not None
                and dist(x["push_at"], me.pos) < 25.0):
            # radar on: on only once in position and still (EQ-RCAMO-02, the jam shows only when it is too late), and
            # kept while it stands there (EQ-RCAMO-03, still, the meter nearly frozen): Kit.act ends it when it moves off
            return (k, "self", None, 30.0, "camo in position")
        # evade to cover ground (the player's: 20 of 27 at full shield with nobody within 12 u, straight ahead,
        # 3.0-3.4 u in 0.7 s): on a clear way, the floor all along it, a while since the last
        if k == "evade" and x["travel"] and not x["seen"] and not x["hit"] and now >= s.cool.get("evade_way", 0.0):
            way = s.evade_way(bot, me)
            if way is not None:
                s.cool["evade_way"] = now + bot.rng.uniform(4.0, 12.0)
                return (k, "dash", way, 0.1, "evade along the way")
        return None

    def fly_to(s, bot, x, me, arg):
        """The goal to jet straight to, or None: a jetpack on the move with nobody in sight, the goal 1 u to JET_RISE up
        and within what a full jetpack flies across (4 s at JET_FLY), the walk to it winding round (its next waypoint
        over 0.8 rad off the goal's way: stairs, a ramp, round a hill), and clear air up from here and across to it."""
        if s.kind != "jetpack" or not isinstance(arg, Vec) or not x["moving"] or x["seen"]:
            return None
        rise, d = arg.z - me.pos.z, (arg - me.pos).flat()
        if not (1.0 <= rise <= JET_RISE and 0.5 < d <= 4.0 * JET_FLY - 1.0):
            return None
        wp = getattr(bot, "wp", None)
        if wp is None or (wp - me.pos).flat() < 0.3:
            return None
        if abs(wrap(math.atan2(wp.y - me.pos.y, wp.x - me.pos.x) - math.atan2(arg.y - me.pos.y, arg.x - me.pos.x))) < 0.8:
            return None                                       # the walk heads there already
        return arg if s.air_ok(bot, me, arg) else None

    @staticmethod
    def air_ok(bot, me, dest):
        """A jetpack flight from here to dest (on a floor 1 u to JET_RISE up, within a full pack's 4 s at JET_FLY) is
        clear: up first, then over (the ledge's lip under the line), no floor overhead up to that height, and a clear
        line across at its height (los from a point over our head: a ray straight up reads as through a man's feet)."""
        rise, d = dest.z - me.pos.z, (dest - me.pos).flat()
        if not (1.0 <= rise <= JET_RISE and 0.5 < d <= 4.0 * JET_FLY - 1.0):
            return False
        T = bot.T()
        j, i = T._cell(me.pos)
        if any(math.isfinite(z) and me.pos.z + 1.0 < z < dest.z + 1.5 for z in T.lz[:, j, i]):
            return False
        return bool(T.los(Vec(me.pos.x, me.pos.y, dest.z + 0.4), dest))

    def fight_jet(s, bot, now, x, me, arg):
        """A jetpack flight in a fight, or None: (point, why). After a man who runs from us up a ledge (he looks away, 1
        u to JET_RISE up within reach); up and over to the cover a retreat heads for when it stands up there; Heroic
        and up take the high ground: a floor 2 u to JET_RISE up within 6 u that sees him, while he looks elsewhere,
        past 6 u from him, our shield over half."""
        if s.kind != "jetpack" or me.vehicle != -1 or me.has_flag:
            return None
        goal, tgt = bot.goal[0], x["target"]
        if goal == "fight" and tgt is not None and tgt.alive and not facing_me(tgt, me, 0.5):
            up = tgt.pos.z - me.pos.z
            if 1.0 <= up <= JET_RISE and s.air_ok(bot, me, tgt.pos):
                return tgt.pos, "jetpack after him"
            if (s.lvl >= 2 and up < 1.0 and dist(tgt.pos, me.pos) > 6.0 and me.shield > 0.5
                    and now >= s.cool.get("high_ground", 0.0)):
                hg = s.high_ground(bot, me, tgt)
                if hg is not None:
                    return hg, "jetpack to the high ground"
                s.cool["high_ground"] = now + 2.0             # (a search of 24 spots: not every tick)
        if goal == "retreat" and isinstance(arg, Vec) and s.air_ok(bot, me, arg):
            return arg, "jetpack up and over to cover"
        return None

    def high_ground(s, bot, me, tgt):
        """The nearest floor 2 u to JET_RISE over us, 3-6 u off, a bot can stand on, that sees tgt, with a clear flight
        to it (air_ok); None."""
        T = bot.T()
        for d in (3.0, 4.5, 6.0):
            for k in range(8):
                a = k * math.pi / 4
                x, y = me.pos.x + d * math.cos(a), me.pos.y + d * math.sin(a)
                if not T.inside(x, y):
                    continue
                j, i = T._cell(Vec(x, y, me.pos.z))
                for l in range(T.L):
                    z = float(T.lz[l, j, i])
                    if not (math.isfinite(z) and 2.0 <= z - me.pos.z <= JET_RISE and T.lwalk[l, j, i]):
                        continue
                    p = Vec(x, y, z)
                    if T.los(p, tgt.pos) and s.air_ok(bot, me, p):
                        return p
        return None

    @staticmethod
    def descent(bot, me, arg):
        """the player's way off a height ("people can jump off spire and jet back almost near the floor and let down
        safely"): (take-off, landing) for a walk off the edge toward a goal 8 u or more below, the jetpack held near the
        ground (jet_brake), or None. The edge lies within 10 u, the goal's way or up to 90 deg off it (the nearest to it
        first: Spire's top has a rim and the core stand in the way on most lines), floor all the way to it and a clear
        line, 8-40 u of drop there (a full pack brakes 36 u: tools/test_ability_hold.py), and the floor below within 6 u
        of the goal's height, one a bot can stand on."""
        if not isinstance(arg, Vec) or me.pos.z - arg.z < 8.0 or (arg - me.pos).flat() < 3.0:
            return None
        T = bot.T()
        way = math.atan2(arg.y - me.pos.y, arg.x - me.pos.x)
        for off_deg in (0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90):
            a = way + math.radians(off_deg)
            to = Vec(math.cos(a), math.sin(a), 0.0)
            for k in range(1, 21):
                p = Vec(me.pos.x + to.x * 0.5 * k, me.pos.y + to.y * 0.5 * k, me.pos.z)
                h = T.height_over(p.x, p.y, me.pos.z)
                on = T.ground_ok(p.x, p.y, me.pos.z, drop=1.0)
                if on and h <= 1.0:
                    continue                                   # still on the floor
                if (on or not (8.0 <= h <= 40.0) or abs(me.pos.z - h - arg.z) > 6.0
                        or T.clearance(me.pos, a, far=0.5 * k) < 0.5 * k - 0.3):
                    break                                      # a wall, a short drop, the wrong level, a rail in the way
                lx, ly = p.x + to.x * 3.0, p.y + to.y * 3.0
                land = Vec(lx, ly, me.pos.z - T.height_over(lx, ly, me.pos.z))   # (the floor under it, not under p)
                n = T._node_at(land.x, land.y, land.z, tol=1.0)
                if n is None or not T.lwalk[n] or abs(land.z - arg.z) > 6.0:
                    break                                      # (a gap in the top, the top again past it: no way down)
                return Vec(p.x + to.x, p.y + to.y, me.pos.z), Vec(land.x, land.y, float(T.lz[n]))
        return None

    @staticmethod
    def road_near(bot, me):
        """The nearest spot 1.5-3 u off that people drove over (Terrain.drive_paint: rides.json and painted drive
        cells), or None (no rides recorded on this map, or none that near)."""
        T = bot.T()
        cells = T.__dict__.get("_drive_set")
        if cells is None:
            cells = T._drive_set = set(getattr(T, "drive_paint", ()))
        if not cells:
            return None
        for d in (1.5, 2.0, 2.5, 3.0):
            for k in range(8):
                a = me.yaw + k * math.pi / 4
                p = Vec(me.pos.x + d * math.cos(a), me.pos.y + d * math.sin(a), me.pos.z)
                n = T._node_at(p.x, p.y, p.z, tol=0.6)
                if n is not None and n in cells:
                    return Vec(p.x, p.y, float(T.lz[n]))
        return None

    def flying(s, now):
        """A jetpack flight (fly_to, fight_jet) or a planned descent is under way: Bot.edge_guard leaves its stick alone."""
        return (s.press is not None and s.press[1] in ("fly", "descend") and now < s.hold_until
                or now < getattr(s, "descent_until", 0.0))

    def jet_brake(s, bot, now, me):
        """Falling faster than the jetpack can still brake to a safe landing in the height left (brake_speed): hold it
        (a fall off Spire's top, a missed heat vent, a knock off a ledge). Once on it stays on until the fall is 1 u/s
        under that speed, or the floor; the energy decides the rest. Not Easy (no ability use), not in a seat."""
        if s.kind != "jetpack" or me.vehicle != -1 or bot.p.tier == "novice" or s.energy is None:
            return False
        braking = s.press is not None and s.press[4] == "brake the fall" and now < s.hold_until
        if not (s.energy.level > 0.0 if braking else s.energy.ready()):
            return False
        down = -me.vel.z
        if down < SAFE_LAND * 0.8:
            return False
        h = bot.T().height_over(me.pos.x, me.pos.y, me.pos.z)
        return 0.3 < h and down > brake_speed(h) - (1.0 if braking else 0.0)

    @staticmethod
    def evade_way(bot, me):
        """The point 3.4 u on along the way the bot walks (its next waypoint's way) for a dash, or None: the waypoint
        too near to tell the way, a wall within 3.6 u, or the floor not there all along it (an evade off a ledge)."""
        wp = getattr(bot, "wp", None)
        if wp is None or (wp - me.pos).flat() < 0.6 or abs(wp.z - me.pos.z) > 0.6:
            return None
        yaw = math.atan2(wp.y - me.pos.y, wp.x - me.pos.x)
        T = bot.T()
        if T.clearance(me.pos, yaw, 3.6) < 3.6:
            return None
        c, sn = math.cos(yaw), math.sin(yaw)
        if not all(T.ground_ok(me.pos.x + c * d, me.pos.y + sn * d, me.pos.z + 0.4, drop=0.8) for d in (1.0, 2.0, 3.0, 3.6)):
            return None
        return me.pos + Vec(c, sn, 0) * 3.4

    def sprint_wish(s, bot, x, me):
        """Guide 01 section 6 / 02: sprint closes the gap with a close-range gun (let go about a unit out, then melee),
        rotates on clear routes, runs the flag, escapes once out of sight; it cannot shoot, so it stops before Medium
        band of an enemy, and strong players stop before any corner an enemy might be behind. It chases a man out of our
        gun's reach who looks away, and runs from a lost fight with the shield down. Easy sprints only a long walk with
        nobody about."""
        tgt = x["target"]
        # (5 u: guide 20 EQ-SPRINT-03; from 15 u a shotgun sprinted 45 m at a man it could not shoot meanwhile)
        if x["fight"] and tgt is not None and me.weapon in CQB and 1.2 < dist(tgt.pos, me.pos) < 5.0:
            return "sprint to close the gap"
        if s.lvl == 0:
            arg = bot.goal[1]
            far = not isinstance(arg, Vec) or dist(arg, me.pos) > LONG_WALK
            return "sprint the long walk" if x["travel"] and far else None
        from .bot import WEAPON_RANGE
        if (x["fight"] and tgt is not None and not facing_me(tgt, me, 0.3)
                and dist(tgt.pos, me.pos) > max(8.0, WEAPON_RANGE.get(me.weapon, (5.0, 25.0))[1])):
            return "sprint after him"                  # out of our gun's reach, looking away: close in (EQ-SPRINT-01)
        if bot.goal[0] == "retreat" and x["cracked"]:
            return "sprint away, shield down"          # seen or not: escape a losing fight (EQ-SPRINT-01)
        if x["seen"]:
            return None
        if bot.goal[0] == "retreat":
            return "sprint away out of sight"
        if x["carrying"]:
            return "run the flag"
        near = x["push_at"] is not None and dist(x["push_at"], me.pos) < 12.0
        if x["travel"] and not (near and s.lvl >= 2):
            return "sprint the clear route"
        return None

    def act(s, bot, now, dt, me, snap, act):
        """Carry out the plan: aim where it goes (one tick), press; a held ability stays pressed, a
        toggle one is tapped on and tapped off; a dash steers its direction. Halo 4's sprint is
        everyone's, its own button. Returns the note for the observer, or None."""
        note = None
        if me.has_flag and s.game == "reach":
            # never with an objective in hand: in Reach the press drops it (Spire, live: the core carrier's
            # "sprint the clear route" emptied its third slot, a second after each pickup, for 15 s)
            s.press, s.hold_until, s.toggled = None, 0.0, False
            return None
        if s.game == "h4" and s.sprint_ok and me.vehicle == -1:
            why = s.sprint_wish(bot, s.situation(bot, now, me, snap), me)
            if why:
                act.sprint = True
                act.fire = act.fire and not s.sprinting(now, me, "h4_sprint_t0")
                s.run_away(bot, dt, me, act)
                s.sprint_steer(dt, me, act)
            else:
                s.h4_sprint_t0 = None
        toggle = s.energy is not None and use_of(s.game, s.kind)[0] == "tap"
        holding = now < s.hold_until and s.press is not None
        if holding and s.press[0] == "sprint" and not s.sprint_wish(bot, s.situation(bot, now, me, snap), me):
            # its reason went (an enemy came into sight): let go and shoot, not out the plan's second (guide 20 audit:
            # Sword Base, 330 held ticks in fights, 119 within 5 u, the gun silent)
            s.hold_until, holding = now, False
        if (holding and s.press[0] == "jetpack" and s.press[4] not in FIGHT_JETS and s.press[1] != "descend"
                and s.lvl >= 2 and bot.per.visible_enemies()):
            # watched mid-climb: down (guide 02: a flyer cannot strafe; the hold is the whole climb now, not 0.5 s). A
            # flight in the fight itself, a brake or a descent goes on
            s.hold_until, holding = now, False
        if holding and s.press[1] == "descend":
            s.descent_until = now + 0.5
        if now < getattr(s, "descent_until", 0.0) and (
                bot.T().height_over(me.pos.x, me.pos.y, me.pos.z) > 0.6 or me.vel.z < -1.0):
            s.descent_until = now + 0.5                        # off the edge: the fall is part of the descent
        if s.jet_brake(bot, now, me):
            # before any plan and whoever watches: a fall that would kill or hurt (Kit.jet_brake)
            if not (holding and s.press[4] == "brake the fall"):
                s.press, s.why = ("jetpack", "self", None, 0.0, "brake the fall"), "brake the fall"
                s.press_t0, s.press_hp = now, (me.shield, me.health)
                note = "jetpack: brake the fall"
            s.hold_until, holding = now + 0.15, True
        if holding and s.press[0] == "jetpack" and s.energy is not None and s.energy.level <= 0.0:
            s.hold_until, holding = now, False      # the tank is dry: let go, not held on empty (JET_FULL's trace)
        if not holding:
            if s.toggled and s.energy is not None and s.energy.on and s.kind not in PLACED:
                act.equipment = True                   # the run is over: tap it off
                # (not on again in the same tick: the one tap would switch it off, and the next "off" tap back on)
                s.cool[s.kind] = max(s.cool.get(s.kind, 0.0), now + 0.3)
            s.toggled = False
            use = s.plan(bot, now, me, snap)
            if use:
                k, how, point, hold, why = use
                kind_use, secs = use_of(s.game, k)
                if kind_use == "press":
                    hold = secs                        # the player's tap, not the plan's guess (USE)
                    use = (k, how, point, hold, why)
                s.press, s.hold_until, s.why = use, now + hold, why
                s.press_t0, s.press_hp = now, (me.shield, me.health)
                # (Promethean Vision: a pulse every 10 s at most, EQ-PV-02; its unseen trigger would pulse it nonstop)
                s.cool[k] = now + (10.0 if k == "promethean_vision" else 1.0 if s.energy is not None else 2.0)
                if why.startswith("survivor:"):
                    s.cool[k] = now + hold + SURV_SHOOT_S        # the gun again between blocks (the owner's openings)
                note = f"{k}: {why}"
                holding = True
        if holding:
            k, how, point, hold, why = s.press
            if how == "feet":
                act.pitch = -1.2                       # drop it at our feet
                bot.att = ["gear", k, round(me.pos.x, 1), round(me.pos.y, 1)]
            elif how in ("throw", "front", "aim") and point is not None:
                act.yaw, act.pitch = angles_to(eye(me), point)
                bot.att = ["gear", k, round(point.x, 1), round(point.y, 1)]
                if how == "front":
                    act.pitch = max(act.pitch, -0.6)
            elif how == "dash" and point is not None:
                to = (point - me.pos).norm()
                c, sn = math.cos(me.yaw), math.sin(me.yaw)
                act.forward, act.strafe = to.x * c + to.y * sn, -to.x * sn + to.y * c   # strafe +1 = left
            elif how == "fly" and point is not None:
                if (point - me.pos).flat() < 0.2:
                    act.forward = act.strafe = 0.0             # over it: let the jetpack set it down
                else:
                    bot.steer(me, point, act, True, arrive=0.0)
            elif how == "descend" and point is not None:
                if bot.T().height_over(me.pos.x, me.pos.y, me.pos.z) > 0.6:
                    s.hold_until = now                         # off the edge: the fall steering below takes over
                    bot.fall_steer(me, s.descent_land, act)
                else:
                    bot.steer(me, point, act, True, arrive=0.0)   # walk off the edge (Bot.edge_guard lets it: flying())
            # (a descent walks off with the pack unpressed: jet_brake holds it for the last of the fall)
            act.equipment = (not s.toggled if toggle else True) and how != "descend"
            # a hold-mode ability also needs the held bit (Reach +0x08 bit 8, hold_bit): without it no armor lock, evade,
            # jetpack, hologram or drop shield ever came on live (USE)
            act.ability = act.equipment and hold_bit(s.game, k)
            s.toggled = toggle
            if k == "sprint":
                act.fire = act.fire and not s.sprinting(now, me)
                s.run_away(bot, dt, me, act)
                s.sprint_steer(dt, me, act)
                if act.forward < 0.9:
                    # still turning to the way (sprint_steer's half stick): the button waits for the full stick; a
                    # sprint pressed at half stick never came on (live Boardwalk 060423: 25 of 34 presses not on within
                    # 0.5 s, the misses at forward 0-0.5 or strafing; logs/tmp/press_misses.py)
                    act.equipment = False
                if me.vel.flat() > 1.5:
                    s.ran = now                                # (a body that runs: live, the simulator; not a test's still one)
                if now - s.press_t0 > 0.6 and me.vel.flat() < 1.2 and getattr(s, "ran", None) is not None:
                    # held 0.6 s and not running: a wall, a wedge, the unstuck code's wiggle has the stick (it runs after
                    # this): let go (the same match: misses at 0.0-1.0 u/s, "wall ahead: stepping around", "unstuck")
                    s.hold_until, s.cool[k] = now, now + 2.0
                    act.equipment = False
                    note = "sprint: blocked, let go"
            if k == "armor_lock" and me.ability_on:
                s.press_on = s.press_t0                        # it locked (this press)
                s.seen_on = True                               # the reader shows ours: a lock that never comes on is refused
            hp0 = getattr(s, "press_hp", None)
            locked = getattr(s, "press_on", None) == s.press_t0
            hurt = hp0 is not None and (me.shield < hp0[0] - 0.02 or me.health < hp0[1] - 0.02)
            read = getattr(s, "seen_on", False) and k not in s.unread
            if k == "armor_lock" and not locked and (hurt and now - s.press_t0 > 0.15 or read and now - s.press_t0 > 0.55):
                # it never locked: hurt in it, or not on past its warmup and the reader's lag (0.15 + 0.4 s; one came on
                # 0.30 s in, stepping down a ledge, live Boardwalk at 241.1 s). The game refused it: its meter is
                # emptier than our model's (the same match at 244.7 s, the fourth lock in 28 s, 0.5 s pressed, health
                # 1.0 -> 0.22). Fight on, not a statue (live Spire, match 220515: NovaHunter held it 3 s standing,
                # health 0.73 -> 0.15, "just sitting there dying"), and the model's meter empty: no press until it fills
                s.hold_until, s.cool[k] = now, now + 8.0
                if s.energy is not None:
                    s.energy.level = 0.0
                act.equipment = act.ability = False
                note = f"{k}: did not lock, fighting on"
            elif k in ("armor_lock", "hardlight_shield") and why.startswith("survivor:"):
                # a survivor's short block: never stretched by the danger (Flood are always near: the stretch held the
                # shield up all game, the owner's Blood Cavern 225014); its let-go a melee when it came for an empty gun
                act.fire, act.forward, act.strafe = False, 0.0, 0.0
                if now >= s.hold_until - 0.04:
                    s.hold_until = now
                    act.equipment = act.ability = False
                    if "melee" in why and any(dist(e.pos, me.pos) < SURV_MELEE_R for e in snap.players
                                              if e.team != me.team and e.alive):
                        act.melee = True
                        note = "survivor: let go, melee"
            elif k in ("armor_lock", "hardlight_shield"):
                act.fire, act.forward, act.strafe = False, 0.0, 0.0
                if now - s.press_t0 > 0.5 and s.energy is not None:
                    # held while the danger lasts, to the meter's end; let go once it passed (the plan's 2 s was a guess:
                    # a lock held past the rocket only gave the shooter time, one let go under fire died)
                    x = s.situation(bot, now, me, snap)
                    near = any(dist(e.pos, me.pos) < 3.0 for e in x["seen"])
                    # (a grenade still at its feet too: let go at 0.6 s with it there, the lock came on again 0.35 s
                    # later, three times in 3 s)
                    feet = x["nade"] is not None and (x["nade"] - me.pos).flat() < 2.5
                    # (a man seen within 12 u and a teammate on his way in, 3-20 u off and running at us: held for him
                    # to arrive)
                    backup = any(dist(e.pos, me.pos) < 12.0 for e in x["seen"]) and any(
                        p.team == me.team and p.alive and p.id != me.id and 3.0 < dist(p.pos, me.pos) < 20.0
                        and p.vel.flat() > 0.5 and (me.pos.x - p.pos.x) * p.vel.x + (me.pos.y - p.pos.y) * p.vel.y > 0
                        for p in snap.players)
                    if x["incoming"] or x["splatter"] or x["lunge"] or x["hit"] or near or feet or backup:
                        if s.energy.level > 0.05:
                            s.hold_until = max(s.hold_until, now + 0.3)
                    else:
                        s.hold_until = min(s.hold_until, now + 0.1)
                if k == "armor_lock" and s.lvl >= 3 and any(
                        dist(e.pos, me.pos) < 1.2 for e in snap.players if e.team != me.team and e.alive):
                    s.hold_until = now                 # sneaky: let go next to a meleeing enemy (EMP, melee back)
                    act.melee = True
            if k == "active_camo":
                act.crouch = True                      # crouch-walk keeps camo (guide 08)
                if why == "camo in position" and (me.vel.flat() > 1.0 or bot.goal[0] not in ("hold", "objective")):
                    s.hold_until = now                 # off the ambush spot: the run is over (EQ-RCAMO-03)
        else:
            s.press, s.sprint_t0 = None, None
        walk_off = holding and s.press[1] == "descend"
        land = getattr(s, "descent_land", None)
        if now < getattr(s, "descent_until", 0.0) and land is not None and not walk_off:
            bot.fall_steer(me, land, act)                     # falling: onto the landing, the brake holds the pack
        if s.energy is not None:
            s.energy.tick(now, dt, holding and not walk_off)
        s.steer_clear(me, snap, act)
        return note

    @staticmethod
    def run_away(bot, dt, me, act):
        """A sprint on a retreat: turn and run at the next waypoint, until a unit from the cover (there it watches out
        again, Bot.look_point). A sprint goes forward only (Reach, Halo 4); backing off still facing the man (Bot.think's
        retreat) held the button for nothing. The turn is a person's swing to run, 6 rad/s (Aim.step's quick turn; the
        aim itself keeps flicking back onto the man it fights, so its step cannot turn the bot away)."""
        wp, (goal, arg) = getattr(bot, "wp", None), bot.goal
        if goal == "retreat" and wp is not None and isinstance(arg, Vec) and (arg - me.pos).flat() > 1.0:
            want = math.atan2(wp.y - me.pos.y, wp.x - me.pos.x)
            act.yaw = me.yaw + max(-6.0 * dt, min(6.0 * dt, wrap(want - me.yaw)))
            bot.steer(me, wp, act, True, arrive=0.02)
            act.fire = act.grenade = act.melee = False

    @staticmethod
    def sprint_steer(dt, me, act):
        """A sprint is forward and steer: the view turns to the way it goes, a person's swing (6 rad/s, run_away's), and
        the stick pushes forward only, at half while the view is still more than 0.6 rad off the way."""
        mag = min(1.0, math.hypot(act.forward, act.strafe))
        if mag < 0.3:
            return
        way = act.yaw + math.atan2(act.strafe, act.forward)       # (strafe +1 = left)
        act.yaw = me.yaw + max(-6.0 * dt, min(6.0 * dt, wrap(way - me.yaw)))
        act.forward, act.strafe = mag * (1.0 if abs(wrap(way - act.yaw)) < 0.6 else 0.5), 0.0

    def sprinting(s, now, me, key="sprint_t0"):
        """Whether a sprint asked for is running, so the gun goes quiet: its first half second, then only while the body
        moves faster than a run (a sprint the game does not take, Reach's held input or Halo 4's undecoded button, left
        the gun silent for nothing; guide 20 audit). key: its start time (Reach's ability, Halo 4's own button)."""
        if getattr(s, key, None) is None:
            setattr(s, key, now)
        return now - getattr(s, key) < 0.5 or me.vel.flat() > RUN_SPEED * 1.3

    def steer_clear(s, me, snap, act):
        """Step round an enemy trip mine or power drain when the next step goes into it (guide 08:
        "never walk a known vehicle route without checking the ground"; "step out of the radius")."""
        # (the step is taken along the facing this command asks: the body's facing was used, and a bot turning as it
        # backed toward a mine sidestepped the wrong way)
        c, sn = math.cos(act.yaw), math.sin(act.yaw)
        wx, wy = act.forward * c - act.strafe * sn, act.forward * sn + act.strafe * c   # strafe +1 = left
        if math.hypot(wx, wy) < 0.2:
            return
        for pos, r in s.avoid(me, snap):
            off = Vec(me.pos.x - pos.x, me.pos.y - pos.y, 0.0)
            if off.flat() < r and abs(me.pos.z - pos.z) < 1.5:
                # already inside: straight out, whatever the way asks (live Rat's Nest s178: a bot pushing into a wall slid
                # along it onto a mine, its commanded step pointing away the whole time)
                n = off.flat() or 1.0
                act.forward, act.strafe = (off.x * c + off.y * sn) / n, (-off.x * sn + off.y * c) / n
                return
            ahead = Vec(me.pos.x + wx * 0.8, me.pos.y + wy * 0.8, me.pos.z)
            if dist(ahead, pos) >= r or dist(me.pos, pos) > r + 3.0:
                continue
            to = (pos - me.pos).norm()
            left = Vec(-to.y, to.x, 0)
            side = left if left.x * wx + left.y * wy >= 0 else left * -1.0
            act.forward, act.strafe = side.x * c + side.y * sn, -side.x * sn + side.y * c
            return

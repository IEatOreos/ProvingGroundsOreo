"""Skill tiers and personalities. Starting values come from docs/research/01 section 7
(synthesized from CS, TF2, Quake III and Laird, not measured in Halo: tune against a
skilled player's play once telemetry exists)."""
from dataclasses import dataclass, replace
import math
import random

DEMON = "demon"

# Hands: a good human's. Reaction, tracking, lead and aim error (live: a Spartan is 0.0125 rad wide at 20 units);
# difficulty lives mostly in what a bot knows and decides (memory, radar, teamwork, CRAFT below).
HANDS = dict(reaction=0.22, track=0.10, lead=0.8, decide=0.10, overshoot=0.30, aim_err=0.009, lag=0.09, flick=1.0)
# ... except reaction, as time against a good human's 0.22 s. Easy reacts at the human's speed to a man in its
# face (Perception.react_time). (custom, Nov 12, owner: "make all difficulties from easy to heroic react faster ...
# keep their accuracy settings") Easy 1.25 -> 1.0 (a good human's 0.22 s), Normal 1.0 -> 0.88, Heroic 0.85 -> 0.78;
# Legendary, Demon, Blind unchanged, Tactician pinned (TACTICIAN_REACTION). Aim, hands and turn speed unchanged
REACTION = {"novice": 1.0, "average": 0.88, "strong": 0.78, "top": 0.70}
# ... and Heroic's and Legendary's hands: lag, the aim's pursuit time constant (Aim.step: 0.09 s trailed a man
# strafing at arm's length by 9 degrees), flick, the Fitts time factor of a flick onto a man, a tighter sampled error
# and a quicker re-read of his motion. Easy and Normal keep a good human's hands Heroic a third of the way on toward
# Legendary's hands (supervisor: "tune Heroic if it is still even"; live Construct Team Slayer, both sides: Heroic
# took 0.52 of the bot kills against Normal over 179, its aim on a man in 0.27 s to Normal's 0.54, on the body 89% to
# 85%; was lag 0.065, flick 0.85, aim_err 0.0075, track 0.09)
SHARP = {"novice": {}, "average": {},
         "strong": dict(lag=0.058, flick=0.80, aim_err=0.0068, track=0.085),
         "top": dict(lag=0.045, flick=0.7, aim_err=0.006, track=0.08)}
# A looser trigger on Easy, Normal and Heroic, Legendary unchanged. the player keeps 68% of his trigger time on a
# body, bots 81-87%. Of his other 32%: 14% follow-through (still firing up to 0.6 s after the man left his view), 7%
# just off him, 6% further off, 3% before he shows; bots 5-8% follow-through, 2% just off: they fired only at a man
# seen in the last 0.25 s, and only once the swing onto him was done (logs/tmp/offbody.py, his Cyberdyne matches and
# Halo 3 ones). follow: s more the trigger stays on where the man went; early: the end share of a swing onto him
# already firing. Off: LOOSE_AIM = False here, or "aim_loose": "off" in logs/test_override.json (test matches)
LOOSE_AIM = True
LOOSE = {"novice": dict(follow=0.35, early=0.4), "average": dict(follow=0.3, early=0.35),
         "strong": dict(follow=0.25, early=0.3)}
# Turn speed, rad/s: the most the view turns, like a player's look sensitivity. Normal at a skilled player's flicks
# onto a man (435 deg/s, p95 of his Cyberdyne acquisitions, Aim.step); (custom, Nov 10, owner) Heroic and Legendary
# 650 deg/s (Legendary was 1000), Demon 700 (was 480).
# Not jittered (make_profile): one more random draw would shift every seeded bot's other values
TURN = {k: math.radians(v) for k, v in dict(novice=270, average=435, strong=650, top=650).items()}
# Intent to kill (bot.Bot.press_on): the share of fights a bot walks in on the man it fights inside its gun's band rather
# than holding its ground to strafe. A skilled player's Halo 3 matches against Legendary (tools/intent.py, game memory
# only): he walked toward the man in view 47% of the in-view time and held 39%, Legendary 33% and 63%; he came inside
# melee reach in 18% of fights, Legendary 10%. Heroic half of Legendary's; Easy and Normal hold as before. Not jittered,
# like TURN
PRESS = {"novice": 0.0, "average": 0.0, "strong": 0.5, "top": 1.0}
TIERS = {
    #           memory s, uses motion tracker, teamwork: follows the team's plan, shoots who the team
    #           shoots (focus fire) (+ HANDS). Easy goes it alone
    # Easy plays for itself: no motion sensor, no team plan, no team shot
    "novice":  dict(HANDS, reaction=HANDS["reaction"] * REACTION["novice"], memory=4, radar=0.0, teamwork=0.0),
    "average": dict(HANDS, reaction=HANDS["reaction"] * REACTION["average"], memory=6, radar=0.5, teamwork=0.55),
    "strong":  dict(HANDS, **SHARP["strong"], reaction=HANDS["reaction"] * REACTION["strong"], memory=8, radar=0.8,
                    teamwork=0.8),
    "top":     dict(HANDS, **SHARP["top"], reaction=HANDS["reaction"] * REACTION["top"], memory=10, radar=1.0,
                    teamwork=0.95),
}
# Movement and map craft by tier: the easiest bots never jump and run straight at the objective;
# the hardest take sneaky routes, jump shot, juke when shot at and track power-weapon timers. 0 =
# never, 1 = like a top player.
CRAFT = {
    #          jump: jumps at all / jump shots   strafe: strafes in a fight   juke: dodges when hit
    #          routes: side and sneaky lanes, avoids fights   map_iq: knows spawns and timers
    #          tactics: uses cover in a losing fight, recharges behind cover after one, backs off when
    #          outnumbered (0: fights it out in the open and walks on cracked into the next one, the
    #          bad spots an easy bot puts itself in)
    #          aware: keeps its eyes on known threats while it moves, checks a radar dot or a hit from a
    #          man it has not seen even mid-fight (0: looks where it walks and tunnels on its target)
    # strafe raised (Normal bots stood still in 59% of their standing time in
    # fights, tools/fluidity.py): Easy 0.15 -> 0.3, Normal 0.5 -> 0.7 (Easy still never jumps). Easy 0.3 -> 0.9
    # (the player: yes to Easy toward 70%; it strafed 5-16% of its fight time live, the player 70%; sim 0.14 -> 0.39)
    "novice":  dict(jump=0.0,  strafe=0.9,  juke=0.0, routes=0.0, map_iq=0.0, tactics=0.0,  aware=0.0),
    # Normal jump 0.25 -> 0.5: 4.4-6.0 jumps a minute live (5.1 presses, Boardwalk CTF), the player 9.1; Heroic (0.7)
    # 7.5-9.2
    "average": dict(jump=0.5,  strafe=0.7,  juke=0.1, routes=0.3, map_iq=0.3, tactics=0.4,  aware=0.35),
    "strong":  dict(jump=0.7,  strafe=0.85, juke=0.6, routes=0.7, map_iq=0.7, tactics=0.75, aware=0.75),
    "top":     dict(jump=1.0,  strafe=1.0,  juke=1.0, routes=1.0, map_iq=1.0, tactics=1.0,  aware=1.0),
}

# Explicit Demon settings: later edits to Legendary's rows must not change Demon.
REACTION[DEMON] = 0.70
SHARP[DEMON] = dict(lag=0.045, flick=0.7, aim_err=0.006, track=0.08)
TURN[DEMON] = math.radians(700)
PRESS[DEMON] = 1.0
TIERS[DEMON] = dict(HANDS, lag=0.045, flick=0.7, aim_err=0.006, track=0.08,
                    reaction=0.154, memory=10, radar=1.0, teamwork=0.95)
CRAFT[DEMON] = dict(jump=1.0, strafe=1.0, juke=1.0, routes=1.0, map_iq=1.0, tactics=1.0, aware=1.0)

DEMON_AIM = dict(aim_err=0.0, lag=0.001, track=0.001, overshoot=0.0,
                 lead=0.0, flick=0.05)
# An independent protected exception: future Demon tuning must not alter Legendary's retained aim.
LEGENDARY_AIM = dict(aim_err=0.0, lag=0.001, track=0.001, overshoot=0.0,
                     lead=0.0, flick=0.05)   # (Nov 10) turn: Legendary's own TURN (was 1000 deg/s here)


# (custom, Nov 10, owner) Blind: Legendary (tier "top", extra None, label "blind": every Legendary rule) whose aim and
# hands are each drawn per bot between Legendary's base and BLIND_TOWARD of the way on to Demon's, a real player's
# uneven strengths. Its own hands aim everywhere: no protected head/turret precision, no DMR/sniper head snap (aim_own)
BLIND = "blind"
BLIND_TOWARD = 0.85
BLIND_HANDS = ("reaction", "aim_err", "lag", "track", "flick", "overshoot", "decide")   # and turn (TURN)


# (custom, Nov 10, owner) Tactician: "make its stats between legendary and heroic". Legendary's game sense and decisions
# (tier "top", extra None, label "tactician": every Legendary rule: memory, radar, teamwork, routes, map timing,
# tactics, awareness, high ground), its aim and hands halfway between Heroic's and Legendary's (TACTICIAN_HANDS,
# TACTICIAN_TOWARD of the way from Heroic on), jittered as every tier's are. Like Blind its own hands aim everywhere:
# no protected head/turret precision, no DMR/sniper head snap (protected_aim). It wins by where it is, not by its aim
TACTICIAN = "tactician"
TACTICIAN_TOWARD = 0.5
TACTICIAN_HANDS = ("reaction", "aim_err", "lag", "track", "flick", "overshoot")   # (decide, lead, turn: the same)
# (custom, Nov 12) its reaction kept where it was before Heroic's got quicker: halfway from Heroic's old 0.85 to 0.70
TACTICIAN_REACTION = HANDS["reaction"] * (0.85 + 0.70) / 2


def arc_spot(prof):
    """(custom, Nov 12, owner) Easy, Normal and Heroic find the man hurting them without the off-to-the-side delay, as a
    player follows the HUD's damage arc (Perception.hurt_by, update); others at the screen's edge keep it. Legendary,
    Demon, Blind, Tactician and Scaling unchanged."""
    return prof.extra is None and prof.tier in ("novice", "average", "strong")


def fixed_blind(prof):
    return prof.label == BLIND and prof.extra is None


def fixed_tactician(prof):
    return prof.label == TACTICIAN and prof.extra is None


def own_hands(prof):
    """Fixed Legendary whose hands are its own, not Legendary's protected aim: Blind and Tactician."""
    return fixed_blind(prof) or fixed_tactician(prof)


def protected_aim(prof):
    """Fixed Legendary's protected precision, DMR/sniper head snap and unerring lead; Demon's own, not Blind's or
    Tactician's."""
    return fixed_high(prof) and not own_hands(prof)


def fixed_high(prof):
    """Fixed Legendary or Demon; Scaling's top tier is excluded."""
    return prof.tier in ("top", DEMON) and prof.extra is None


def fixed_demon(prof):
    return prof.tier == DEMON and prof.extra is None


def high_ground(prof):
    """(custom, Nov 10, owner) Team Slayer's high-ground play (Bot.slayer_post, Director.slayer_slots): Legendary, Blind
    and Scaling (all tier "top") and Demon. Heroic and below keep the upstream play."""
    return prof.tier in ("top", DEMON)


def resource_priority(prof):
    """Power calls: Demon, Legendary, Heroic/Scaling, Normal, Easy."""
    if prof.extra is not None:
        return 2
    return {DEMON: 0, "top": 1, "strong": 2, "average": 3}.get(prof.tier, 5)


def defend_priority(prof):
    """(custom, Nov 9) Who the director makes CTF's one defender, the lowest difficulty first, never Easy: Normal,
    Heroic and Scaling (Scaling counted as Heroic, as resource_priority does), Legendary, Demon; Easy last (it plays
    for itself and is never given a team role anyway: assign_roles)."""
    if prof.tier == "novice":
        return 9
    if prof.extra is not None:
        return 1
    return {"average": 0, "strong": 1, "top": 2, DEMON: 3}.get(prof.tier, 9)


def driver_priority(prof):
    """Who the director sends to drive a Warthog or a Mongoose (vehicles.DEMON_NO_DRIVE): Normal and Heroic first, then
    Scaling and Legendary, then Easy; Demon never (None). (custom, Nov 13) A Wheelman before all of them."""
    if fixed_demon(prof):
        return None
    if wheelman(prof):
        return -1
    if prof.extra is not None:
        return 1
    return {"average": 0, "strong": 0, "top": 1}.get(prof.tier, 2)


def gunner_priority(prof):
    """Legendary, Heroic and Scaling share the same gunner-call weight."""
    priority = resource_priority(prof)
    return 1 if priority == 2 else priority


def precision_profile(prof):
    """Keep Legendary's established head/turret aim without changing its base attributes."""
    return replace(prof, **LEGENDARY_AIM) if protected_aim(prof) and not fixed_demon(prof) else prof

# Traits are 0..1. Personalities only change *what* a bot prefers, never how well it aims.
PERSONALITIES = {
    "rusher":   dict(aggression=0.9, caution=0.2, camping=0.0, jumpy=0.6, crouchy=0.2, grenades=0.5, grudge=0.5, objective=0.4),
    "camper":   dict(aggression=0.3, caution=0.7, camping=0.9, jumpy=0.1, crouchy=0.7, grenades=0.3, grudge=0.3, objective=0.3),
    "flanker":  dict(aggression=0.6, caution=0.5, camping=0.1, jumpy=0.4, crouchy=0.5, grenades=0.4, grudge=0.4, objective=0.5),
    "objector": dict(aggression=0.5, caution=0.4, camping=0.1, jumpy=0.3, crouchy=0.3, grenades=0.4, grudge=0.2, objective=0.95),
    "spammer":  dict(aggression=0.7, caution=0.3, camping=0.2, jumpy=0.5, crouchy=0.2, grenades=0.95, grudge=0.4, objective=0.4),
    "grudger":  dict(aggression=0.7, caution=0.3, camping=0.2, jumpy=0.4, crouchy=0.4, grenades=0.5, grudge=0.95, objective=0.3),
    "sniper":   dict(aggression=0.3, caution=0.8, camping=0.7, jumpy=0.1, crouchy=0.8, grenades=0.2, grudge=0.3, objective=0.3),
    # (custom, Nov 13, owner: "a personality that always wants to drive warthogs ... call it wheelman") on foot a flanker;
    # its own rules are wheelman() below. Only when picked: not dealt to "any" (tools/play.py's list)
    "wheelman": dict(aggression=0.6, caution=0.4, camping=0.0, jumpy=0.3, crouchy=0.3, grenades=0.4, grudge=0.3, objective=0.5),
}


def wheelman(prof):
    """(custom, Nov 13) The Wheelman play style: goes for the nearest vehicle it may drive (a Warthog first) from WHEEL_SEEK_R,
    first in line for the team's Warthog and Mongoose wheels (driver_priority) and from farther (director.crew_orders),
    and keeps its vehicle where others get out at a trip's end (Bot.drive). The existing rules stand: a Demon never takes
    a Warthog's, Mongoose's or Ghost's wheel, Easy is never sent to drive a person on a gun nor takes that wheel itself."""
    return prof.personality == "wheelman"


@dataclass
class Profile:
    tier: str
    personality: str
    reaction: float
    track: float
    lead: float
    decide: float
    overshoot: float
    memory: float
    radar: float
    teamwork: float
    aim_err: float
    lag: float
    flick: float
    aggression: float
    caution: float
    camping: float
    jumpy: float
    crouchy: float
    grenades: float
    grudge: float
    objective: float
    jump: float
    strafe: float
    juke: float
    routes: float
    map_iq: float
    tactics: float
    aware: float
    turn: float              # rad/s: the most its view turns (TURN; Bot.think)
    # Scaling difficulty's own settings for what the brain otherwise looks up by tier (head_aim, ram_err, loose_follow,
    # loose_early: brain/scaling.py); None on the tiers
    extra: dict = None
    # Optional displayed label; Demon now also has its own real tier.
    label: str = None


def make_profile(tier, personality, rng=random):
    """Build stock tier attributes; Demon retains our former fixed Legendary overrides."""
    if tier == BLIND:
        return blind_profile(personality, rng)
    if tier == TACTICIAN:
        return tactician_profile(personality, rng)
    vals ={**TIERS[tier], **CRAFT[tier], **PERSONALITIES[personality]}
    jit = {k: v * rng.uniform(0.9, 1.1) for k, v in vals.items()}
    if tier == "top":
        jit["overshoot"] = 0.0

    if tier == DEMON:
        jit.update(DEMON_AIM, reaction=0.0, decide=0.01)

    return Profile(
        tier=tier,
        personality=personality,
        turn=TURN[tier],
        label=DEMON if tier == DEMON else None,
        **jit,
    )


def blind_ranges():
    """{stat: (Legendary's base, the ceiling BLIND_TOWARD of the way to Demon's)} for Blind's drawn hands."""
    leg = dict(TIERS["top"], overshoot=0.0, turn=TURN["top"])
    dem = dict(TIERS[DEMON], **DEMON_AIM, reaction=0.0, decide=0.01, turn=TURN[DEMON])
    return {k: (leg[k], leg[k] + BLIND_TOWARD * (dem[k] - leg[k])) for k in BLIND_HANDS + ("turn",)}


def blind_profile(personality, rng=random):
    """Legendary's profile (its game sense, jittered as ever), its aim and hands each drawn on its own between
    Legendary's base and the ceiling (blind_ranges): one Blind is quick but loose, the next slow and dead on."""
    prof = make_profile("top", personality, rng)
    drawn = {k: rng.uniform(min(a, b), max(a, b)) for k, (a, b) in blind_ranges().items()}
    return replace(prof, label=BLIND, **drawn)


def tactician_hands():
    """{stat: Tactician's base}: TACTICIAN_TOWARD of the way from Heroic's base to Legendary's (overshoot: Legendary's 0);
    reaction pinned (TACTICIAN_REACTION)."""
    her, leg = TIERS["strong"], dict(TIERS["top"], overshoot=0.0)
    mid = {k: her[k] + TACTICIAN_TOWARD * (leg[k] - her[k]) for k in TACTICIAN_HANDS}
    mid["reaction"] = TACTICIAN_REACTION
    return mid


def tactician_profile(personality, rng=random):
    """Legendary's profile (its game sense, jittered as ever) with its hands set between Heroic's and Legendary's, each
    jittered 0.9-1.1 as make_profile jitters every tier's."""
    prof = make_profile("top", personality, rng)
    hands = {k: v * rng.uniform(0.9, 1.1) for k, v in tactician_hands().items()}
    return replace(prof, label=TACTICIAN, **hands)


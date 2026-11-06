"""Skill tiers and personalities. Starting values come from docs/research/01 section 7
(synthesized from CS, TF2, Quake III and Laird, not measured in Halo: tune against a
skilled player's play once telemetry exists)."""
from dataclasses import dataclass, replace
import math
import random

# Hands: a good human's. Reaction, tracking, lead and aim error (live: a Spartan is 0.0125 rad wide at 20 units);
# difficulty lives mostly in what a bot knows and decides (memory, radar, teamwork, CRAFT below).
HANDS = dict(reaction=0.22, track=0.10, lead=0.8, decide=0.10, overshoot=0.30, aim_err=0.009, lag=0.09, flick=1.0)
# ... except reaction, as time against a good human's 0.22 s. Easy reacts at the human's speed to a man in its
# face (Perception.react_time)
REACTION = {"novice": 1.25, "average": 1.0, "strong": 0.85, "top": 0.70}
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
# onto a man (435 deg/s, p95 of his Cyberdyne acquisitions, Aim.step); Legendary 1000 deg/s, a 180 in about 0.27 s.
# Not jittered (make_profile): one more random draw would shift every seeded bot's other values
TURN = {k: math.radians(v) for k, v in dict(novice=270, average=435, strong=650, top=1000).items()}
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

# Traits are 0..1. Personalities only change *what* a bot prefers, never how well it aims.
PERSONALITIES = {
    "rusher":   dict(aggression=0.9, caution=0.2, camping=0.0, jumpy=0.6, crouchy=0.2, grenades=0.5, grudge=0.5, objective=0.4),
    "camper":   dict(aggression=0.3, caution=0.7, camping=0.9, jumpy=0.1, crouchy=0.7, grenades=0.3, grudge=0.3, objective=0.3),
    "flanker":  dict(aggression=0.6, caution=0.5, camping=0.1, jumpy=0.4, crouchy=0.5, grenades=0.4, grudge=0.4, objective=0.5),
    "objector": dict(aggression=0.5, caution=0.4, camping=0.1, jumpy=0.3, crouchy=0.3, grenades=0.4, grudge=0.2, objective=0.95),
    "spammer":  dict(aggression=0.7, caution=0.3, camping=0.2, jumpy=0.5, crouchy=0.2, grenades=0.95, grudge=0.4, objective=0.4),
    "grudger":  dict(aggression=0.7, caution=0.3, camping=0.2, jumpy=0.4, crouchy=0.4, grenades=0.5, grudge=0.95, objective=0.3),
    "sniper":   dict(aggression=0.3, caution=0.8, camping=0.7, jumpy=0.1, crouchy=0.8, grenades=0.2, grudge=0.3, objective=0.3),
}


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


def make_profile(tier, personality, rng=random):
    """Tier + personality, each value jittered +-10% so no two bots are identical."""
    vals = {**TIERS[tier], **CRAFT[tier], **PERSONALITIES[personality]}
    jit = {k: v * rng.uniform(0.9, 1.1) for k, v in vals.items()}
    return Profile(tier=tier, personality=personality, turn=TURN[tier], **jit)


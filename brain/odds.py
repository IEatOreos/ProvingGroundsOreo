"""(custom, Nov 8) Halo 4 Demon's fight odds: will it win the fight in front of it?

The owner, Nov 8: Demons "die in silly ways, they play recklessly they pursue losing fights, they challenge another
player even when one shot". 398 Halo 4 Demon deaths over 16 of his matches (scratchpad demon_autopsy): 55% with two or
more enemies firing on it, 17% fighting on with its shield gone and its body under 70%, 12% chasing a man out of sight
while hurt. In the median 2.0 s it had after the second shooter opened up, it chose a fight 55% and a hunt 24% of the
time, a retreat 11%, though one was scored in half of those deaths.

The model, by the SHIELD (the owner, Nov 8: "In Halo you break their shields and then they become one shot to the head.
So I think we should make them judge fights based on shield pools instead of a health pool"):
- a precision gun (BR, DMR, Light Rifle, Carbine, Magnum) kills by stripping the shield and one headshot: his shield's
  share of the strip time plus the finishing shot (FINISH); the body does not count. With no shields (SWAT), the
  finishing shot alone;
- an automatic or a spray (AR, Storm Rifle, Suppressor, Needler, SAW, Plasma Pistol), no headshot kill in Halo 4: the
  pool, shield 70 and body 45 (a Spartan's), its share of the gun's time from full;
- a power gun or a blade (snipers, rockets, laser, sword, hammer, shotguns in reach): its fixed time, whatever is left.
Each man who can shoot it kills it at that pace over his accuracy (ACC); one not aware of it starts UNAWARE_S late. It
kills them one at a time, the quickest first, at its own pace over DEMON_ACC. Their shares of the kill on it add up
(each one's time on it alone); the odds are 1 over the share it takes before the last of them falls: 1 an even trade,
over 1 it wins.
"""
import math

H4_SHIELD, H4_BODY = 70.0, 45.0
# gun: (s from full, every shot landing, at its best range; reach in u; how it kills: "precision" / "pool" / "fixed")
H4_GUNS = {
    "battle_rifle": (1.35, 30.0, "precision"), "dmr": (1.2, 40.0, "precision"), "lightrifle": (1.3, 45.0, "precision"),
    "covenant_carbine": (1.35, 30.0, "precision"), "magnum": (1.5, 20.0, "precision"),
    "storm_rifle": (1.7, 12.0, "pool"), "assault_rifle": (1.8, 12.0, "pool"), "suppressor": (1.6, 10.0, "pool"),
    "plasma_pistol": (2.6, 10.0, "pool"), "needler": (1.6, 12.0, "pool"), "lmg": (1.2, 20.0, "pool"),
    "concussion_rifle": (1.6, 20.0, "pool"), "boltshot": (1.2, 4.0, "pool"),
    "shotgun": (0.25, 3.0, "fixed"), "scattershot": (0.3, 4.0, "fixed"), "sniper": (0.6, 80.0, "fixed"),
    "beam_rifle": (0.6, 60.0, "fixed"), "binary_rifle": (0.4, 80.0, "fixed"), "railgun": (0.5, 30.0, "fixed"),
    "rockets": (0.7, 30.0, "fixed"), "fuelrod": (0.8, 25.0, "fixed"), "incineration_cannon": (0.6, 15.0, "fixed"),
    "spartan_laser": (0.8, 60.0, "fixed"), "sticky_detonator": (1.0, 25.0, "fixed"),
    "sword": (0.2, 3.0, "fixed"), "gravity_hammer": (0.2, 2.5, "fixed"),
}
GUN_DEFAULT = (1.6, 20.0, "pool")    # a gun not in the table
# s: a precision gun's finishing shot, the headshot once the shield is down (about a shot's or a burst's interval:
# the BR's fifth burst, the DMR's fifth round, the Light Rifle's fourth scoped round)
FINISH = {"battle_rifle": 0.3, "dmr": 0.3, "lightrifle": 0.45, "covenant_carbine": 0.25, "magnum": 0.3}
REACH_PENALTY = 3.0
MELEE = {"sword", "gravity_hammer", "shotgun", "scattershot", "boltshot"}   # past reach: next to nothing
RIDER_TTK = 1.0                 # s from full: a man in a vehicle's seat on us (a chaingun, a Ghost's cannons): the pool
RIDER_HARD = 2.0                # x: our time on a man riding (his vehicle takes the rounds), anti-vehicle guns aside
ANTI_VEHICLE = {"rockets", "spartan_laser", "railgun", "sticky_detonator", "fuelrod", "incineration_cannon",
                "plasma_pistol"}
# a person / a bot: his share of the table's pace; Demon's own. The replay calibration (scratchpad odds_replay.py, 5
# Halo 4 matches, 135 Demon deaths, 215 Demon kills; Bot ODDS_BREAK / ODDS_PERSIST): by the shield, a bot 0.15, a person
# 0.8 and Demon 1.0 separated best (the pool model's best: the same values). The owner killed Demons in a median 1.08 s
# from his first hit in 22 one-on-one wins
ACC = {True: 0.8, False: 0.15}
DEMON_ACC = 1.0
UNAWARE_S = 0.45                # s: a man not aware of it takes this long to turn and shoot (a person's reaction)
ODDS_CAP = 9.0
ONE_SHOT = 0.05                 # shield at or under this: one headshot from dead


def remaining(p, shieldless=False):
    """The share of a Spartan's full pool p has left (shield 70, body 45; without shields the body alone): how an
    automatic sees him."""
    if p is None:
        return 0.0
    if shieldless:
        return max(0.0, min(1.0, p.health))
    return max(0.0, (H4_SHIELD * max(0.0, p.shield) + H4_BODY * max(0.0, p.health)) / (H4_SHIELD + H4_BODY))


def shield_left(p, shieldless=False):
    """What stands between p and a headshot: his shield (without shields: nothing, 0)."""
    return 0.0 if p is None or shieldless else max(0.0, min(1.0, p.shield))


def one_shot(p, shieldless=False):
    """p dies to the next headshot from a precision gun: his shield is gone."""
    return shield_left(p, shieldless) <= ONE_SHOT


def kill_time(weapon, d, victim, shieldless=False):
    """s for `weapon` at d u to kill `victim` as he is now, every shot landing (precision: his shield's share of the
    strip, then the headshot; pool: his pool's share; fixed: its time). None or unknown gun: never."""
    if weapon in (None, "none", "flag", "ball", "unknown"):
        return math.inf
    t, r, how = H4_GUNS.get(weapon, GUN_DEFAULT)
    if d > r:
        if weapon in MELEE:
            return math.inf
        t *= REACH_PENALTY
    if how == "precision":
        fin = FINISH.get(weapon, 0.3) * (REACH_PENALTY if d > r else 1.0)
        return shield_left(victim, shieldless) * max(0.0, t - fin) + fin
    if how == "pool":
        return remaining(victim, shieldless) * t
    return t


def threat(me, my_weapon, e, aware, shieldless=False, riding=False, unseen_late=0.0):
    """One man for simulate(): (s we need to kill him, s he needs to kill us alone, s before he shoots)."""
    d = math.dist((me.pos.x, me.pos.y, me.pos.z), (e.pos.x, e.pos.y, e.pos.z))
    ours = kill_time(my_weapon, d, e, shieldless) / DEMON_ACC
    if riding and my_weapon not in ANTI_VEHICLE:
        ours *= RIDER_HARD
    his = RIDER_TTK * remaining(me, shieldless) if riding else kill_time(e.weapon, d, me, shieldless)
    his = his / ACC[not getattr(e, "is_bot", True)] if math.isfinite(his) else math.inf
    late = (0.0 if aware else UNAWARE_S) + unseen_late
    return ours, his, late


def simulate(threats):
    """threats: [(s we need on him, s he needs on us alone, s before he shoots)]. We kill them one at a time, quickest
    first; each one alive adds his time's share of a kill on us. The odds: 1 over the share taken before the last
    falls (ODDS_CAP when nothing reaches us)."""
    if not threats:
        return ODDS_CAP
    jobs = sorted(threats, key=lambda j: j[0])
    t = taken = 0.0
    alive = list(jobs)
    for kill_t, _, _ in jobs:
        if not math.isfinite(kill_t):
            kill_t = 60.0                    # (nothing of ours reaches him: a minute of his fire)
        end = t + kill_t
        for _, his, late in alive:
            if math.isfinite(his):
                taken += (max(0.0, end - max(t, late)) / his) if his > 1e-6 else (1e9 if end > late else 0.0)
        t = end
        alive.pop(0)
    if taken <= 1e-9:
        return ODDS_CAP
    return min(ODDS_CAP, 1.0 / taken)


def with_help(ours, helpers):
    """s to kill a man with teammates on him too: our pace and each teammate's (helpers: their s on him alone) add up.
    (Custom, Nov 8: the owner, "The demon bots can beat me in a 1v1 but in a team enviroment they struggle".)"""
    rate = (1.0 / ours if math.isfinite(ours) and ours > 1e-6 else 0.0) + \
        sum(1.0 / h for h in helpers if math.isfinite(h) and h > 1e-6)
    return 1.0 / rate if rate > 0 else math.inf


def time_left(threats):
    """s we live under the aware men's fire (their late start 0), all of them on us: 1 over their summed rates."""
    rate = sum(1.0 / his for _, his, late in threats if late == 0.0 and math.isfinite(his) and his > 1e-6)
    return 1.0 / rate if rate > 0 else ODDS_CAP

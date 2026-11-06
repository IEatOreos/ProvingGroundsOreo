"""Loadouts (Reach, Halo 4, H2A)..

The game keeps each player's requested slot and hands out that loadout at the next spawn (the
host's player_loadout_request handler writes it: Reach player +0x3E4, Halo 4 +0x944; see
docs/HANDOFF.md). What a slot holds depends on the gametype, so the team learns it from its own
spawns: slot -> the guns a bot holds a moment after spawning with it. When three or more slots all
give the same guns the gametype offers no choice (or loadouts are off) and the bots stop asking.

Each bot keeps how its recent lives ended (record_death) and, while it waits to respawn, asks for
the slot that answers the problem it keeps meeting (want_slot):
- outranged: killed from 8+ units by a gun that reaches further than its own -> the slot with the
  longest-reaching primary;
- out-gunned up close: killed under 4 units by a gun better up close -> the slot with the best
  Short band primary (an automatic first);
- vehicles: killed by a driver or gunner -> a slot with an anti-vehicle gun (plasma pistol, rockets).
Each slot's armor ability counts too (ABILITY_FIT: armor lock against vehicles, a hologram or camo
against the sniper who outranges us, evade / thruster / armor lock up close).
A slot not seen yet scores in the middle, so a bot with no known answer tries one (and the team
learns it); slots this bot already died that way with score lower. Difficulty is behaviour: a
novice never changes (its bad spot: the wrong gun for the fight); the tactics level sets how many
deaths of one kind it takes (1 top, 2 strong, 3 average), counted again from each change."""
import collections
import random
import zlib

from .bot import ANTI_VEHICLE, AUTO, WEAPON_RANGE
from .core import dist

SLOTS = 5                    # the loadout menus offer five (the request carries 3 bits)
LONG, SHORT = 8.0, 4.0       # guide 01 bands: Medium from 4 units; outranged = killed from 8+
DEFAULT_RANGE = (5.0, 25.0)  # as Bot.threat for a gun with no entry


def reach(weapon):
    return WEAPON_RANGE.get(weapon, DEFAULT_RANGE)


# how much each armor ability answers each problem (guide 08 use-now table and loadout priorities:
# a hologram baits the sniper and camo crosses his lane unseen; sprint, evade, thruster, armor lock and
# hardlight win or dodge the fight up close and the sword lunge; armor lock EMPs the vehicle that hits
# it, hardlight stops light vehicles, a thruster dashes out of their line)
ABILITY_FIT = {
    "outranged": {"hologram": 0.6, "active_camo": 0.5, "jetpack": 0.3, "thruster": 0.3, "promethean_vision": 0.3,
                  "sprint": 0.2},
    "close": {"evade": 0.5, "thruster": 0.5, "armor_lock": 0.5, "hardlight_shield": 0.5, "sprint": 0.4,
              "active_camo": 0.3},
    "vehicle": {"armor_lock": 0.9, "hardlight_shield": 0.6, "thruster": 0.4, "drop_shield": 0.3},
}


class Palette:
    """What each slot gives in this match, learned from spawns and shared by the team: the guns,
    and the armor ability it comes with."""
    def __init__(s):
        s.seen = {}          # slot -> (primary, secondary)
        s.ability = {}       # slot -> armor ability kind ("" none)
        s.off = False        # the game refused a request (botcore without SET_LOADOUT)
        s.sides = {}         # key -> the Palette of one side's kits (side())

    def side(s, key):
        """The palette one side's spawns teach (key None: this one). Invasion's attackers and defenders have their own
        slots (live Boneyard B27: slot 1 the Spartans' DMR + AR and the Elites' needle rifle + plasma pistol; one palette
        for both kept the last spawn's). The species goes with the role on a map, so the key is the role."""
        if key is None:
            return s
        p = s.sides.setdefault(key, Palette())
        p.off = p.off or s.off
        return p

    def learn(s, slot, weapons, ability=""):
        guns = tuple(w for w in weapons[:2] if w not in ("none", "unknown"))
        if slot is not None and 0 <= slot < SLOTS and guns:
            s.seen[slot] = guns
            s.ability[slot] = ability if ability != "unknown" else ""

    def choice(s):
        kits = {(g, s.ability.get(k, "")) for k, g in s.seen.items()}
        return not s.off and not (len(s.seen) >= 3 and len(kits) == 1)


def record_death(bot, now, snap):
    """How this life ended: who most likely killed it (the enemy that hurt it in the last 2 s, else
    the one it fought), from how far, with what, from a vehicle or not, and its own slot and gun."""
    per = bot.per
    k = getattr(per, "attacker_id", None) if now - getattr(per, "attacker_t", -9.0) < 2.0 else None
    if k is None and bot.goal[0] == "fight":
        k = bot.goal[1]
    e = snap.player(k) if k is not None else None
    at = getattr(bot, "last_pos", None)
    bot.deaths = (getattr(bot, "deaths", []) + [dict(
        t=now, slot=getattr(bot, "slot", None), mine=getattr(bot, "last_weapon", None),
        theirs=e.weapon if e else None, vehicle=bool(e and e.vehicle != -1),
        d=dist(at, e.pos) if e and at else None)])[-8:]


def death_kind(d):
    """outranged / close / vehicle, or None: a fair fight lost, which no loadout fixes."""
    if d["vehicle"]:
        return "vehicle"
    if d["d"] is None or d["theirs"] is None:
        return None
    mine, theirs = reach(d["mine"]), reach(d["theirs"])
    if d["d"] >= LONG and theirs[1] > mine[1]:
        return "outranged"
    if d["d"] < SHORT and theirs[0] < mine[0]:
        return "close"
    return None


def fit(guns, kind, ability=""):
    if not guns:
        return 0.5                                    # not seen yet: worth a try
    if kind == "outranged":
        v = min(1.0, reach(guns[0])[1] / 40.0)
    elif kind == "close":
        v = max(0.0, 1.0 - reach(guns[0])[0] / 6.0) + (0.3 if guns[0] in AUTO else 0.0)
    else:
        v = 1.0 if set(guns) & ANTI_VEHICLE else 0.2
    return v + 0.6 * ABILITY_FIT.get(kind, {}).get(ability, 0.0)


# a player's favourite primary: every bot had kept slot 1, which held the DMR there. Weights: what people take
# most (guide 03)
LIKED = (("battle_rifle", 35), ("dmr", 30), ("assault_rifle", 20), ("covenant_carbine", 7), ("lightrifle", 5),
         ("needle_rifle", 3))


def liked_guns(name):
    """The primaries a bot likes, most liked first, drawn once from its name (the same every match)."""
    rng, pool, out = random.Random(f"{name.lower()}:liked"), list(LIKED), []
    while pool:
        pick = rng.choices(pool, weights=[w for _, w in pool])[0]
        out.append(pick[0])
        pool.remove(pick)
    return out


def liked_slot(bot, palette, current, carried=()):
    """The slot with the gun this bot likes most of those the gametype offers; while its favourite has not turned up, an
    unseen slot to look in (the team learns each slot from the spawns: tools/live_bots.py loadout_check). None to
    stay. Only until a problem made it change (want_slot): then it plays the answer. Slots alike in the gun: the one
    whose armor ability the team carries least (carried: its teammates' kinds now), else the one it has, so a team's
    kits vary (guide 20 review: 103 of 105 requests were "liked", and a tie always went to the lowest slot)."""
    liked = getattr(bot, "liked", None)
    if not liked or getattr(bot, "fixed_slot", False) or not palette.choice():
        return None
    rank = {g: k for k, g in enumerate(liked)}
    known = {k: rank.get(g[0], len(liked)) for k, g in palette.seen.items() if g}
    best = min(known.values(), default=len(liked))
    unseen = [k for k in range(SLOTS) if k not in palette.seen]
    if unseen and best > 0:
        slot = unseen[zlib.crc32(f"{getattr(bot, 'id', 0)}:{liked[0]}".encode()) % len(unseen)]
    elif best < len(liked):
        n = collections.Counter(carried)
        slot = min((k for k, r in known.items() if r == best),
                   key=lambda k: (n[palette.ability.get(k, "")], k != current, k))
    else:
        return None
    return slot if slot != current else None


def want_slot(bot, palette, current, now, carried=()):
    """(slot, problem, deaths) to ask for while dead, or None to keep the current slot. No problem: the slot with the
    gun it likes (liked_slot; problem "liked")."""
    fix = _problem_slot(bot, palette, current, now)
    if fix:
        bot.fixed_slot = True
        return fix
    slot = liked_slot(bot, palette, current, carried)
    return (slot, "liked", 0) if slot is not None else None


def _problem_slot(bot, palette, current, now):
    t = bot.p.tactics
    if t < 0.15 or not palette.choice():
        return None
    need = 1 if t >= 0.9 else 2 if t >= 0.6 else 3
    since = getattr(bot, "switched_at", -1.0)
    deaths = getattr(bot, "deaths", [])
    kinds = collections.Counter(k for k in (death_kind(d) for d in deaths if d["t"] > since) if k)
    if not kinds:
        return None
    kind, n = kinds.most_common(1)[0]
    if n < need:
        return None

    def score(slot):
        mine = sum(1 for d in deaths if d["slot"] == slot and death_kind(d) == kind)
        return fit(palette.seen.get(slot), kind, palette.ability.get(slot, "")) - 0.3 * mine, slot == current

    best = max(range(SLOTS), key=score)
    if best == current:
        return None
    bot.switched_at = now                             # the next change needs fresh deaths
    return best, kind, n

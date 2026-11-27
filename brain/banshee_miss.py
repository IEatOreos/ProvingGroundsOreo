"""(custom, Nov 26) Bots miss DMR shots at a Banshee's pilot, by tier and by the Banshee flipping. The owner: "right now
they all laser beam even the lower levels because how big the hit box is. And for the higher difficulty bots they can
only miss when the banshee is backflipping with a percentage.. You can make the rest miss with a base chance on flips.
and Normal and easy can just have a base chance to miss the banshee completely. (Dmr shots)"; "Use your numbers".

Each DMR press at a man flying a Banshee, from a bot on foot, is a miss with its tier's chance (MISS: no flip, flipping);
a miss sends that round just past the Banshee (MISS_R off its middle, a random way across the line to it), after the
aim and the shot correction, so it whiffs by the craft as a person's does. Flipping: the craft tipped past 60 degrees
(vehicles.upright) within FLIP_HOLD s (a backflip is upside down only part of the way round). Legendary and up
(profiles.fixed_high: Legendary, Blind, Tactician, Mythic, Demon, Noble) miss only while it flips; Heroic too, more;
Normal and Easy at any time, more while it flips. Scaling keeps its own aim (excluded: prof.extra)."""
import math

from .core import Vec, angles_to, eye
from . import profiles
from . import vehicles

# tier -> (miss chance, miss chance while the Banshee flips)
MISS = {"high": (0.0, 0.25), "strong": (0.0, 0.5), "average": (0.35, 0.6), "novice": (0.5, 0.75)}
FLIP_HOLD = 0.6    # s: a tip past 60 degrees this recent is still the flip
MISS_R = 1.6       # u off the craft's middle: past its wings (about 0.7 u each side) and its body


def tier_key(prof):
    if prof.extra is not None:
        return None                                   # (Scaling: its own aim)
    return "high" if profiles.fixed_high(prof) else prof.tier


def flipping(bot, now, v):
    """The Banshee v tipped past 60 degrees within FLIP_HOLD s (each bot's own watch)."""
    seen = bot.__dict__.setdefault("banshee_tipped", {})
    if not vehicles.upright(v):
        seen[v.get("handle")] = now
    return now - seen.get(v.get("handle"), -99.0) <= FLIP_HOLD


def target_banshee(bot, snap):
    """(the man it shoots at, his Banshee's row) when that man flies a Banshee, else None."""
    part = getattr(bot, "shot_part", None)
    tid = part[0] if part is not None else (bot.goal[1] if bot.goal[0] == "fight" else None)
    e = snap.player(tid) if isinstance(tid, int) else None
    if e is None or not e.alive or e.vehicle in (None, -1):
        return None
    v = next((x for x in (getattr(snap, "vehicles", None) or ()) if x.get("handle") == e.vehicle), None)
    if v is None or vehicles.kind_of(v.get("kind", "")) != "banshee":
        return None
    return e, v


def miss_point(me, c, rng):
    """A point MISS_R from c across the line from our eye to it, a random way round."""
    o = eye(me)
    los = c - o
    n = los.length() or 1.0
    f = Vec(los.x / n, los.y / n, los.z / n)
    side = Vec(-f.y, f.x, 0.0)
    if side.length() < 1e-3:
        side = Vec(1.0, 0.0, 0.0)
    side = side * (1.0 / side.length())
    upv = Vec(f.y * side.z - f.z * side.y, f.z * side.x - f.x * side.z, f.x * side.y - f.y * side.x)
    a = rng.uniform(0.0, 2.0 * math.pi)
    return c + (side * math.cos(a) + upv * math.sin(a)) * MISS_R


def apply(bot, now, me, snap, act):
    """Bot.think, after the turn cap and the shot correction: this tick's DMR press at a Banshee's pilot goes wide with
    its tier's chance. Returns True when it did."""
    was = getattr(bot, "banshee_fire_was", False)
    bot.banshee_fire_was = bool(act.fire)
    key = tier_key(bot.p)
    if key not in MISS or me.weapon != "dmr" or me.vehicle not in (None, -1):
        return False
    got = target_banshee(bot, snap)
    if got is None:
        return False
    e, v = got
    flip = flipping(bot, now, v)                      # (watched every tick: a press just after the flip still counts)
    if not act.fire or was:
        return False
    base, on_flip = MISS[key]
    if bot.rng.random() >= (on_flip if flip else base):
        return False
    q = v.get("pos")
    c = q if isinstance(q, Vec) else Vec(*q[:3])
    act.yaw, act.pitch = angles_to(eye(me), miss_point(me, c, bot.rng))
    bot.banshee_missed_t = now
    if getattr(bot, "notes", None) is not None:
        bot.notes.append("banshee: the shot goes wide" + (" (it flips)" if flip else ""))
    return True

"""(custom, Nov 27) Mongooses only for the objective. The owner: "We have to do something about making Mongoose less
used. Not totally but theyre just not practical. They just always have too many riders, and they always seem to die
really easy ... Like only use them when escorting a bomb carrier, or flag carrier?"; "Dont have bots use mongoose in
slayer or koth". Four of his games (Nov 26, Tempest, Forge World twice, Boneyard): 165 rides of 7 s on average, about
10 of them got where they were going, 105 ended in the Nov 25 bail, and 31 of those riders died within 10 s of getting
off in the open.

A bot takes a Mongoose (its wheel or its back seat) only:
  - in a race (every racer rides), or with the objective in hand;
  - in a game with a carrier (MODES: CTF, Assault, Stockpile), for the carrier: to fetch our carrier on foot far from
    home and run him in (director.ferry_orders), our runner on his way to their flag or bomb site, or the CTF getaway
    ride parked by their base; and at most SLOTS Mongooses of ours at a time on a trip without our carrier aboard.
Never in Slayer, King of the Hill or any other game. The director's own Mongoose orders (drive, ferry, a call aboard)
are checked here before they are given; a bot's own pick (a long trip, a Wheelman's ride) is checked by Bot.veh_banned.

The bail (Bot.goose_flee): shot, or an enemy on radar, a Mongoose driver first drives away from him at full speed and
gets off once out of his sight (behind cover), with an enemy within CLOSE_R, after FLEE_MAX s, or stopped; a passenger
stays aboard while it runs (over RUN_SPEED), off as it slows."""
from .core import Vec, dist

MODES = ("ctf", "assault", "stockpile")   # games with a carrier to ride a Mongoose for
SLOTS = 1                # Mongooses of ours at once on a trip without our carrier aboard
CARRIER_FAR = 30.0       # u: our carrier on foot this far from where he scores is fetched
CLOSE_R = 5.0            # u: an enemy this near, off and fight (no outrunning him)
FLEE_MAX = 3.0           # s: the longest drive away before getting off
FLEE_D = 20.0            # u: how far off the threat the drive away aims
HIDDEN_AFTER = 1.0       # s of driving away before out of sight counts as behind cover ...
HIDDEN_FOR = 0.5         # s: ... with no enemy in its view this long
RUN_SPEED = 4.0          # u/s: a Mongoose this fast is running (a passenger stays on; a driver this slow has stalled)


def is_goose(v):
    from . import vehicles
    return v is not None and vehicles.kind_of(v.get("kind", "")) == "mongoose"


def carrier_aboard(snap, h):
    return any(p.alive and p.vehicle == h and p.has_flag for p in snap.players)


def busy(snap, team, but=None):
    """Mongooses of ours (a teammate aboard, not `but`) on a trip without our carrier aboard."""
    out = set()
    for v in snap.vehicles or ():
        if not is_goose(v):
            continue
        h = v["handle"]
        if carrier_aboard(snap, h):
            continue
        if any(p.alive and p.team == team and p.vehicle == h and p.id != but for p in snap.players):
            out.add(h)
    return out


def slot_free(snap, team, but=None, h=None):
    """A Mongoose of ours may go on a trip without our carrier: fewer than SLOTS out (h: the one asked about, already
    out, keeps its place)."""
    b = busy(snap, team, but)
    return h in b or len(b) < SLOTS


def our_carrier_far(snap, team, home):
    """Our carrier on foot CARRIER_FAR or more from home (where he scores): the man to fetch, else None."""
    c = next((p for p in snap.players if p.team == team and p.alive and p.has_flag and p.vehicle in (None, -1)), None)
    if c is None or home is None or dist(c.pos, home) < CARRIER_FAR:
        return None
    return c


def self_ok(snap, me, role, v):
    """A bot's own pick of Mongoose v (not the director's order): a race, the objective in hand, or our runner in a
    carrier game with a slot free."""
    if snap.mode == "race" or me.has_flag or getattr(snap, "inv_core_carrier", None) == me.id:
        return True
    if snap.mode not in MODES or role != "runner":
        return False
    return slot_free(snap, me.team, me.id, v["handle"] if v is not None else None)


def rider_ok(snap, role, h):
    """A call onto Mongoose h's back seat (director.rider_calls): a race, or our runner in a carrier game."""
    if snap.mode == "race":
        return True
    return snap.mode in MODES and role == "runner"


def away_point(me_pos, threat, d=FLEE_D):
    """A point d u straight away from threat, at our height."""
    dx, dy = me_pos.x - threat.x, me_pos.y - threat.y
    n = (dx * dx + dy * dy) ** 0.5
    if n < 1e-3:
        dx, dy, n = 1.0, 0.0, 1.0
    return Vec(me_pos.x + dx / n * d, me_pos.y + dy / n * d, me_pos.z)

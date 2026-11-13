"""(custom, Nov 12) Reach Headhunter: how many skulls each player carries, and which drop point banks them.

The owner asked for bots that play Headhunter. Before this, a third of the team ran to the drop point nearest its
middle whatever it carried, and nobody knew who held skulls (director.mode_slots).

Nothing in the game's memory is read for this; it is worked out from what the snapshot already holds:
- A skull lying loose (brain/modes.py, Reach's skull weapon objects with no parent) that is gone the next read with a
  living player standing on it was picked up by the nearest such player: +1 for him.
- A player who dies drops all he carries: 0.
- A team score that goes up while a player of that team carrying skulls stands in a drop point banked them there: 0,
  and that drop point is the live one.
- Skulls carried, a drop point stood in BANK_WAIT s, no score: that drop point is not live (Reach moves its drop point
  in some variants). It is skipped DEAD_FOR s. With no score to read for his team (Reach's free-for-all scores are
  not decoded: brain/live.py match_state reads the two team scores only) he is taken to have banked there.

All counts are estimates; a skull picked up out of the reads' sight (between two reads 0.25 s apart, by two men on
it at once) can be missed or given to the wrong man."""
from .core import Vec, dist

PICK_R, PICK_DZ = 1.6, 2.0   # u: who picked a vanished skull up: a living player this near it (flat) and this level
GONE_R = 0.75                # u: a skull read again within this of where it was is the same skull (it rolls)
ZONE_PAD = 0.5               # u: a drop point's boundary, a little generous
BANK_WAIT = 3.0              # s in a drop point with skulls and no score before it is taken as not live
DEAD_FOR = 45.0              # s a drop point found not live is skipped
LIVE_KEEP = 90.0             # s a drop point seen banking is taken as the live one


class Skulls:
    def __init__(s):
        s.held = {}          # player id -> skulls carried (estimate)
        s.prev = None        # the loose skulls last read [Vec]
        s.score = {}         # team -> score last read
        s.live = None        # (zone index, when) the last bank was seen at
        s.dead = {}          # zone index -> skipped until
        s.inside = {}        # player id -> (zone index, since)
        s.zones = []         # [(Vec, radius)]
        s.banked = []        # [(t, player id, zone index, skulls)] for the trace and the tests

    def zone_of(s, q):
        for k, (z, r) in enumerate(s.zones):
            if (q - z).flat() <= r + ZONE_PAD and abs(q.z - z.z) < 2.5:
                return k
        return None

    def update(s, now, snap, zones, loose):
        """zones: the drop points [(Vec, radius)]; loose: the skulls lying loose now [Vec]."""
        s.zones = list(zones)
        for p in snap.players:
            if not p.alive:
                s.held.pop(p.id, None)
                s.inside.pop(p.id, None)
        alive = [p for p in snap.players if p.alive]
        if s.prev is not None:
            for q in s.prev:
                if any(dist(q, r) < GONE_R for r in loose):
                    continue
                on = [(dist(p.pos, q), p.id) for p in alive
                      if (p.pos - q).flat() < PICK_R and abs(p.pos.z - q.z) < PICK_DZ]
                if on:
                    pid = min(on)[1]
                    s.held[pid] = s.held.get(pid, 0) + 1
        s.prev = list(loose)
        score = dict(snap.score or {})
        rose = {t for t, v in score.items() if v > s.score.get(t, v)}
        for p in alive:
            k = s.zone_of(p.pos)
            if k is None:
                s.inside.pop(p.id, None)
                continue
            was = s.inside.get(p.id)
            since = was[1] if was and was[0] == k else now
            s.inside[p.id] = (k, since)
            n = s.held.get(p.id, 0)
            if p.team in rose:
                s.bank(now, p.id, k, n)
                s.live = (k, now)
                s.dead.pop(k, None)
            elif n > 0 and now - since >= BANK_WAIT:
                if p.team in score:
                    s.dead[k] = now + DEAD_FOR          # stood in it with skulls, no score: not live
                    if s.live and s.live[0] == k:
                        s.live = None
                    s.inside[p.id] = (k, now)           # (judged once a BANK_WAIT)
                    if all(s.dead.get(j, 0.0) > now for j in range(len(s.zones))):
                        # every drop point "dead": the score is not moving for anyone (not read in this variant), so
                        # it tells nothing: taken as banked, and the drop points all tried again
                        s.dead.clear()
                        s.bank(now, p.id, k, n)
                else:
                    s.bank(now, p.id, k, n)             # no score to read: taken as banked
        s.score = score

    def bank(s, now, pid, k, n):
        s.held[pid] = 0
        s.banked.append((now, pid, k, n))
        del s.banked[:-50]

    def bank_zone(s, q, now):
        """The drop point to bank at from q: the live one while it is known, else the nearest not found dead (all
        found dead: the nearest of all). None: no drop points."""
        if not s.zones:
            return None
        if s.live is not None and now - s.live[1] <= LIVE_KEEP and s.dead.get(s.live[0], 0.0) <= now:
            return s.zones[s.live[0]][0]
        ok = [z for k, (z, r) in enumerate(s.zones) if s.dead.get(k, 0.0) <= now] or [z for z, r in s.zones]
        return min(ok, key=lambda z: dist(z, q))


# who banks (director.hh_bankers): this many skulls always; fewer with the drop point near
BANK_ALWAYS, BANK_NEAR, BANK_NEAR_R, BANK_ONE_R = 5, 3, 45.0, 12.0
HUNT_SKULLS = 3              # an enemy carrying this many is hunted (director.mode_slots)


def should_bank(n, d, need=None):
    """A carrier of n skulls, d u from the drop point, the team need more to win (None: not known): bank now."""
    if n <= 0:
        return False
    if need is not None and 0 < need <= n:
        return True                                     # a winning bank
    return n >= BANK_ALWAYS or (n >= BANK_NEAR and d <= BANK_NEAR_R) or d <= BANK_ONE_R

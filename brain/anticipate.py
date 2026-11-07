"""Demon's read of where a man went once he is out of sight (custom; see CUSTOMIZATIONS.md).

A belief holds where he was last seen, heard or on the motion tracker, and which way he was moving then. A good
player does not hunt that spot: he reasons about where the man got to since. predict() weighs a few places he
could have reached in the time since along the real walkable paths (straight on the way he was going, the
nearest cover that hides him from us, standing still) and returns the likeliest. It uses only what a player could
know (the last sighting, its heading, the map), never his live position.

Terrain interface used (brain/terrain.Terrain): path_ahead(a, b, n=, limit=), los(a, b), walkable(p),
cover_spots (rows x, y, z, dx, dy). Missing pieces degrade to the last known position.
"""
from .core import Vec, dist

RUN_SPEED = 2.25        # u/s a Spartan runs (bot.decide's cover reach uses the same)
QUIET_SPEED = 1.0       # u/s at most while off the tracker in its range: crouch-walking (or standing still)
MAX_BUDGET = 14.0       # u: farther than this he could be anywhere; the guess stops growing
QUIET_MARGIN = 3.0      # u inside the tracker's range: a dot that vanished here went quiet, it did not walk out
FRESH = 0.15            # s: a trace this fresh is where he is
COVER_PICK = 6          # nearest cover spots weighed


def _flat(v):
    return Vec(v.x, v.y, 0.0)


def _reach(T, start, goal, budget):
    """The farthest point of the walkable way from start toward goal within budget units; None: no way."""
    if budget <= 0.25:
        return start
    path_ahead = getattr(T, "path_ahead", None)
    if path_ahead is None:
        return None
    try:
        steps = path_ahead(start, goal, n=max(1, int(budget / 0.25)), limit=budget * 1.6 + 4.0)
    except Exception:
        return None
    return steps[-1] if steps else None


def _hidden(T, me_pos, p):
    los = getattr(T, "los", None)
    if los is None:
        return False
    try:
        return not los(me_pos, p)
    except Exception:
        return False


def candidates(T, me_pos, b, budget):
    """(label, point) places he could be: on along his heading, behind cover near him, where he was."""
    out = [("stayed", b.pos)]
    heading = _flat(b.vel)
    if heading.flat() > 0.3:
        ahead = b.pos + heading.norm() * budget
        p = _reach(T, b.pos, ahead, budget)
        if p is not None:
            out.append(("heading", p))
    cs = getattr(T, "cover_spots", None)
    if cs is not None and len(cs):
        import numpy as np
        cs = np.asarray(cs, dtype=float)
        d = np.hypot(cs[:, 0] - b.pos.x, cs[:, 1] - b.pos.y)
        ok = np.nonzero((d > 0.5) & (d <= budget + 2.0) & (np.abs(cs[:, 2] - b.pos.z) <= 2.0))[0]
        for k in ok[np.argsort(d[ok])][:COVER_PICK]:
            spot = Vec(float(cs[k, 0]), float(cs[k, 1]), float(cs[k, 2]))
            if _hidden(T, me_pos, spot):
                p = _reach(T, b.pos, spot, budget)
                if p is not None:
                    out.append(("cover", p))
    return out


def score(T, me_pos, b, label, p, quiet):
    heading = _flat(b.vel)
    off = _flat(p - b.pos)
    v = 0.0
    if heading.flat() > 0.3 and off.flat() > 0.5:
        # going on the way he was going: a man rarely turns back on himself
        v += 1.2 * (heading.x * off.x + heading.y * off.y) / (heading.flat() * off.flat())
    if label != "stayed" and _hidden(T, me_pos, p):
        v += 0.8                  # he broke sight to be out of it: he went where we cannot see him
    if label == "cover":
        v += 0.3                  # and a man who just lost sight of us takes the wall by him
    if label == "stayed":
        v += 1.6 if quiet else (0.6 if heading.flat() <= 0.3 else 0.0)   # he stopped (off the tracker, close)
    return v


def predict(T, me_pos, b, now, tracker=False, radar_range=25.0):
    """The likeliest place now of the man belief b describes."""
    unseen = max(0.0, now - b.t)
    if unseen < FRESH or T is None:
        return b.pos
    # off the tracker well inside its range: he did not walk out of it, he stopped or crouched (a good player's
    # first read of a dot that disappears)
    quiet = b.source == "radar" and tracker and dist(me_pos, b.pos) < radar_range - QUIET_MARGIN
    budget = min((QUIET_SPEED if quiet else RUN_SPEED) * unseen, MAX_BUDGET)
    best, best_v = b.pos, -9.0
    for label, p in candidates(T, me_pos, b, budget):
        v = score(T, me_pos, b, label, p, quiet)
        if v > best_v:
            best, best_v = p, v
    return best

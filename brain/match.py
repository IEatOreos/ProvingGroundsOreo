"""Score posture: how safe or how bold a team plays, from the score against the VARIANT'S score limit
and the time left.

Posture runs from 0 (hide) to 1 (all-in), default 0.5 (guide 01 section 10). Nothing here is a
constant kill count: "about to win" is a window of the limit (a few points of a kill game, a tenth of a
timed game), "far ahead" a share of the limit. With no limit known (a reader not decoded yet) only
the lead matters and nobody is ever treated as about to win.
"""
from dataclasses import dataclass, replace

TIME_SCORED = {"oddball", "king"}      # the score is seconds held, not kills or captures


def near_win_window(limit, mode, unit=1):
    """Points from the limit that count as 'one more push and it is over'. Kill and capture games:
    a tenth of the limit, at least 1 and at most 5 kills (50 -> 5: the enemy at 45; 100 -> 5: at 95;
    25 -> 2; 3 flags -> 1), in points: `unit` points a kill (Halo 4 Infinity Slayer / SWAT: 10, so
    600 -> 50, the enemy at 550). Timed games (Oddball, King): a tenth of the limit, at least 10 s."""
    if not limit or limit <= 0:
        return None
    if mode in TIME_SCORED:
        return max(10, round(0.1 * limit))
    unit = max(1, unit)
    return unit * max(1, min(5, round(0.1 * limit / unit)))


@dataclass
class Posture:
    value: float           # 0 hide .. 1 all-in
    state: str             # why: even, ahead, far_ahead, behind, far_behind, enemy_near_win, we_near_win,
                           # hide_and_hold, all_in, unknown
    lead: int = 0          # our score minus the best enemy score
    ours: int = 0
    theirs: int = 0
    limit: int = 0         # 0 = not known
    window: object = None  # near_win_window(), None when the limit is not known


def posture(score, team, limit=0, time_left=None, mode="slayer", unit=1, up=0):
    """score: {team: points} (free for all: one entry per player's team). time_left: seconds or None. unit: points a
    kill (director: the step the scores move in; Halo 4 10). up: our players alive minus the most alive on another
    team (the kill feed): two up pushes (guide 19 SLAY-CORE-07: "if we have 2+ more alive than the enemy, posture
    temporarily becomes AGGRESSIVE ... before they respawn"), value at least 0.7; two down holds (SLAY-ELIM-05:
    "outnumbered ... hold it; make the enemy come to us"), at most 0.3. the player's score rules (enemy about to win,
    the last minute) stand as they are."""
    p = by_score(score, team, limit, time_left, mode, unit)
    if p.state in ("enemy_near_win", "hide_and_hold", "all_in") or abs(up) < 2:
        return p
    return replace(p, value=max(p.value, 0.7) if up > 0 else min(p.value, 0.3))


def by_score(score, team, limit, time_left, mode, unit):
    """The posture from the score and the clock alone."""
    if not score or team not in score:
        return Posture(0.5, "unknown")
    ours = score[team]
    theirs = max((v for k, v in score.items() if k != team), default=0)
    lead = ours - theirs
    w = near_win_window(limit, mode, unit)
    p = dict(lead=lead, ours=ours, theirs=theirs, limit=limit or 0, window=w)
    late = time_left is not None and time_left <= 60
    if late and lead > 0:
        return Posture(0.15, "hide_and_hold", **p)       # a kill does nothing now; a death might
    if late and lead < 0:
        return Posture(0.9, "all_in", **p)               # only kills matter now
    if w is not None:
        if limit - theirs <= w:
            return Posture(0.2, "enemy_near_win", **p)   # one more death can end the game: 2v1 only
        if limit - ours <= w:
            return Posture(0.35, "we_near_win", **p)     # hold power positions, let them come
        share = lead / limit
    else:
        share = lead / 50.0                              # no limit known: a 50-point game's sense of a lead
    if share >= 0.2:
        return Posture(0.3, "far_ahead", **p)
    if share >= 0.1:
        return Posture(0.4, "ahead", **p)
    if share <= -0.2:
        late_game = time_left is not None and time_left <= 180
        return Posture(0.9 if late_game else 0.7, "far_behind", **p)
    if share <= -0.1:
        return Posture(0.6, "behind", **p)
    return Posture(0.5, "even", **p)


def one_flag_posture(p, defending, time_left=None):
    """One Flag (research 12 O3.13): one capture ends the round, so its limit (1) has both teams read "the enemy is one
    capture from winning" (live, Boardwalk: that rule turned the attackers' every pull_flag into defend_flag, and
    blue, with no flag to defend, held mid for a whole round). The side decides: defenders, the enemy is always one
    capture from the round; attackers have no flag to lose and the clock is their enemy: behind (we need the capture),
    all in for the last minute."""
    if defending:
        return replace(p, value=0.2, state="enemy_near_win")
    late = time_left is not None and time_left <= 60
    return replace(p, value=0.9 if late else 0.6, state="all_in" if late else "behind")


def tempo(p, leader_rate, time_left):
    """the player: games should end on the score limit, not on the clock. If the leader's pace (points a
    minute, recent) will not reach the limit before time runs out, both teams raise the tempo (more
    hunting, fewer holds: guide 07 "pressure"). The team the enemy is about to beat stays careful (the
    player's rule) and a losing team in the last minute is all in already. A leader near the win
    (we_near_win, or hide_and_hold in the last minute with the limit inside the near-win window) closes
    the game out instead of holding when its pace will not get there in time: with the other team careful
    too, both holding stopped the kills (Lockdown 45-36 for the whole last minute)."""
    if p.state in ("enemy_near_win", "all_in", "unknown") or not p.limit:
        return p
    if p.state == "hide_and_hold" and p.limit - p.ours > (p.window or 0):
        return p                                         # the limit is out of reach: protect the lead
    if time_left is None or time_left <= 0:
        return p
    need = p.limit - max(p.ours, p.theirs)
    if leader_rate <= 0 or need / leader_rate * 60.0 > time_left:
        state = "close_out" if p.state in ("we_near_win", "hide_and_hold") else "tempo_push"
        return Posture(max(p.value, 0.7), state, p.lead, p.ours, p.theirs, p.limit, p.window)
    return p


def selftest():
    # the player's example: conservative at 45 of 50, but not at 45 of 100; at 95 of 100 it
    # is
    assert posture({0: 30, 1: 45}, 0, 50).state == "enemy_near_win"
    assert posture({0: 30, 1: 45}, 0, 100).state != "enemy_near_win"
    assert posture({0: 80, 1: 95}, 0, 100).state == "enemy_near_win"
    assert posture({0: 80, 1: 94}, 0, 100).state != "enemy_near_win"
    assert posture({0: 46, 1: 30}, 0, 50).state == "we_near_win"
    assert posture({0: 2, 1: 1}, 0, 3, mode="ctf").state == "we_near_win"          # 3 flags: one to go
    assert posture({0: 1, 1: 1}, 0, 3, mode="ctf").state == "even"
    assert posture({0: 30, 1: 18}, 0, 50).state == "far_ahead"
    assert posture({0: 18, 1: 30}, 0, 50).value > 0.5
    assert posture({0: 10, 1: 12}, 0, 50, time_left=40).state == "all_in"
    assert posture({0: 12, 1: 10}, 0, 50, time_left=40).state == "hide_and_hold"
    assert posture({0: 100, 1: 180}, 0, 200, mode="oddball").state == "enemy_near_win"   # 20 s of 200
    assert posture({0: 10, 1: 10}, 0, 0).state == "even" and posture({0: 10, 1: 10}, 0, 0).window is None
    assert posture({3: 9, 5: 14, 7: 2}, 3, 15).state == "enemy_near_win"                  # free for all
    assert posture({}, 0, 50).state == "unknown"
    # numbers (SLAY-CORE-07): two up pushes, two down holds; the player's score rules
    # stand
    assert posture({0: 14, 1: 14}, 0, 50, up=2).value >= 0.7 and posture({0: 14, 1: 14}, 0, 50, up=2).state == "even"
    assert posture({0: 14, 1: 14}, 0, 50, up=-2).value <= 0.3 and posture({0: 14, 1: 14}, 0, 50, up=1).value == 0.5
    assert posture({0: 30, 1: 45}, 0, 50, up=3).value == 0.2 and posture({0: 10, 1: 12}, 0, 50, 40, up=-3).value == 0.9
    slow = posture({0: 14, 1: 14}, 0, 50)
    assert tempo(slow, 2.3, 280).state == "tempo_push"          # 36 to go at 2.3/min: 15 min > 4.7 min
    assert tempo(slow, 9.0, 280).state == "even"                # 4 min to go: it will end on score
    assert tempo(posture({0: 40, 1: 46}, 0, 50), 1.0, 100).state == "enemy_near_win"
    assert tempo(posture({0: 14, 1: 14}, 0, 0), 1.0, 100).state == "even"   # no limit known: no tempo
    # Lockdown 45-36 of 50, the leader too slow for the time left: it closes out, the trailer stays careful
    assert tempo(posture({0: 45, 1: 36}, 0, 50), 3.0, 90).state == "close_out"
    assert tempo(posture({0: 45, 1: 36}, 0, 50), 6.0, 90).state == "we_near_win"     # it gets there holding
    assert tempo(posture({0: 46, 1: 36}, 0, 50, time_left=50), 3.0, 50).state == "close_out"
    assert tempo(posture({0: 30, 1: 20}, 0, 50, time_left=50), 3.0, 50).state == "hide_and_hold"   # 20 to go
    assert tempo(posture({0: 36, 1: 45}, 0, 50), 3.0, 90).state == "enemy_near_win"
    # Halo 4 Infinity Slayer 600, 10 a kill: the enemy at 550 is five kills from winning
    assert posture({0: 400, 1: 550}, 0, 600, unit=10).state == "enemy_near_win"
    assert posture({0: 400, 1: 540}, 0, 600, unit=10).state != "enemy_near_win"
    assert near_win_window(50, "slayer", 1) == 5 and near_win_window(3, "ctf") == 1
    # One Flag: 0-0 of 1 reads "enemy near win" for both; the side decides
    even = posture({0: 0, 1: 0}, 0, 1, mode="ctf")
    assert even.state == "enemy_near_win"
    assert one_flag_posture(even, True).state == "enemy_near_win"
    assert one_flag_posture(even, False, 150).state == "behind" and one_flag_posture(even, False, 40).state == "all_in"
    print("match self-check OK")


if __name__ == "__main__":
    selftest()

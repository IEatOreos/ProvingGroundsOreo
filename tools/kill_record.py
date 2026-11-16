"""Every kill of a Halo: Reach match, as the game itself keeps it (custom, Nov 15), for the Service Record's Weapons,
Enemies and Heatmaps pages (tools/service_record.py). Nothing is guessed: the game writes who it credits with a death
into the dead player's row and what killed him into his body, and those are read the tick he dies (brain/live.py
LiveReach.kill_watch: the fields and how they were found). Read-only, in Python: no botcore change.

tools/live_bots.py keeps one Watch for a recorded Reach match and writes into the match's recording:

  {"t", "kill_record": 2}        once, at the start: this recording has kill rows (a match without it was recorded
                                 before they were written: "not recorded yet", never zeros). The number is VERSION
  {"t", "kill": {...}}           one a death:
      "v"     who died (the player's index in the game, as every id in the recording)
      "k"     the player the game credits with it; None: nobody
      "new"   that credit was written at this death (False: the row held the same player before it)
      "o"     the player whose damage reached the body last; None: no player's
      "c"     the damage type that killed (a number: tools/service_record_site/weapons.json), "m" its modifier; None:
              the body was gone before it could be read
      "hits"  [[player or None, damage type, modifier, body damage, shield damage, game ticks before the death], ...]
              who damaged him lately, newest first, 4 at most (the game's own list)
      "vt", "kt" teams; "vb", "kb" 1 for a bot; "vp", "kp" [x, y, z] where each stood (kp: where the killer last
              stood alive; None: never seen)
      "gt"    the game's tick; "st" the engine's state when he was last seen alive, a pass before (1: the match is
              played, 2: it is over). Version 1 wrote the state read after the death, which is 2 for the kill that
              wins the match: live Powerhouse 20261115-203100, MCC's report counted that kill and not the melee
              kill 6 s later (tools/service_record.py read_kills puts a version 1 recording right)

No names are written (people's gamertags stay out of the recording); the Service Record names the ids from MCC's
report. read() says what a row counts as; both tools use it, so there is one reading of the facts.

    python\\python.exe tools\\kill_record.py        self-check ("kill record OK")
"""
import math
import struct

NONE = 0xFFFFFFFF
VERSION = 2
OVER = 2            # the engine's state once the match is over: deaths from then on are not in MCC's report


def parse_body(body, who, tick, death_at, owner_at, hits_at, n, size):
    """(the damage type that killed, its modifier, who damaged it last, hits) from a dead body's bytes; who: {player
    handle: index}. (None, None, None, []) when the body was not read."""
    if not body or len(body) < hits_at + n * size:
        return None, None, None, []
    hits = []
    for k in range(n):
        t, hurt, shield, unit, player, kind, mod = struct.unpack_from("<iffIIBB", body, hits_at + k * size)
        if (unit == NONE and player == NONE) or not (math.isfinite(hurt) and math.isfinite(shield)):
            continue                                        # (an unused entry; a float no damage ever is)
        hits.append([who.get(player), kind, mod, round(hurt, 3), round(shield, 3),
                     max(0, tick - t) if tick is not None else 0])
    hits.sort(key=lambda h: h[5])
    return body[death_at], body[death_at + 1], who.get(struct.unpack_from("<I", body, owner_at)[0]), hits


def place(p):
    return [round(p[0], 2), round(p[1], 2), round(p[2], 2)] if p is not None else None


class Watch:
    """One for a match. tick(snap) once a pass of the brain: the rows of everyone who died since the last one."""

    def __init__(s, live):
        s.live = live
        s.was = {}          # index -> (salt, unit, credited killer's handle) at the last pass
        s.at = {}           # index -> where he last stood alive
        s.state = None      # the engine's state at the last pass

    def tick(s, snap):
        live = s.live
        now_state, rows = live.kill_watch()
        # the state he died in is the last pass's: the kill that wins a match turns the state to "over" in its own tick
        state, s.state = (s.state if s.state is not None else now_state), now_state
        who = {(r[0] << 16) | i: i for i, r in rows.items()}
        here = {p.id: p for p in snap.players}
        for p in snap.players:
            if p.alive:
                s.at[p.id] = (p.pos.x, p.pos.y, p.pos.z)
        out = []
        for v, (salt, unit, body, killer) in rows.items():
            was = s.was.get(v)
            s.was[v] = (salt, unit, killer)
            # died: he had a unit at the last pass, and it is his dead body now (a player who leaves has none)
            if not was or was[0] != salt or was[1] == NONE or unit == was[1] or body != was[1]:
                continue
            try:
                tick, data = live.death_bytes(body)
            except Exception:           # a read racing the game: the death still counts, without what the body said
                tick, data = None, None
            cause, mod, owner, hits = parse_body(data, who, tick, live.DEATH_AT, live.OWNER_AT, live.HITS_AT,
                                                 live.HITS, live.HIT_SIZE)
            k = who.get(killer)
            pv, pk = here.get(v), here.get(k)
            out.append(dict(v=v, k=k, new=killer != was[2], o=owner, c=cause, m=mod, hits=hits,
                            vt=pv.team if pv else None, kt=pk.team if pk else None,
                            vb=int(bool(pv and pv.is_bot)), kb=int(bool(pk and pk.is_bot)),
                            vp=place(s.at.get(v)), kp=place(s.at.get(k)), gt=tick, st=state))
        for v in [v for v in s.was if v not in rows]:
            del s.was[v]
        return out


def _int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _place(p):
    return (isinstance(p, list) and len(p) == 3 and
            all(isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in p))


def read(k, teams=True):
    """What one kill row counts as: (kind, killer, weapon), or None for a row that is not one or does not count (the
    match was over). kind "kill": the credited player killed him; "betrayal": the credited player is on his team
    (teams: the match has teams); "death": no other player is credited (a fall, his own grenade, the level, an AI).
    killer None for a death. weapon: the damage type of the credited player's last damage on him, else the one that
    killed; None when the body was not read.

    The game leaves its credit as it was when nobody earns one, so a credit not written at this death ("new" false)
    counts only with a sign of that player on the body (his damage in the list, or the last to reach it)."""
    try:
        v, kk, cause = k["v"], k.get("k"), k.get("c")
        if not _int(v) or v < 0 or not (kk is None or (_int(kk) and kk >= 0)) or not (cause is None or _int(cause)):
            return None
        if not _place(k["vp"]) or not (k.get("kp") is None or _place(k["kp"])):
            return None
        hits = k.get("hits") or []
        if not isinstance(hits, list) or not all(isinstance(h, list) and len(h) >= 6 and _int(h[1]) for h in hits):
            return None
    except (KeyError, TypeError):
        return None
    if k.get("st") == OVER:
        return None
    mine = [h for h in hits if h[0] == kk]
    credited = kk is not None and kk != v and (bool(k.get("new")) or cause is None or kk == k.get("o") or bool(mine))
    if not credited:
        return "death", None, cause
    same = teams and k.get("kt") is not None and k.get("kt") == k.get("vt")
    return ("betrayal" if same else "kill"), kk, (mine[0][1] if mine else cause)


def selftest():
    """A made-up game: three players' rows and one body, through Watch as the brain runs it."""
    DEATH_AT, OWNER_AT, HITS_AT, HITS, HIT_SIZE = 0x290, 0xF0, 0x4DC, 4, 0x18

    class P:
        def __init__(s, i, team, bot, pos, alive=True):
            s.id, s.team, s.is_bot, s.alive = i, team, bot, alive
            s.pos = type("V", (), dict(x=pos[0], y=pos[1], z=pos[2]))()

    class Snap:
        def __init__(s, players):
            s.players = players

    def body(cause, owner, entries):
        b = bytearray(HITS_AT + HITS * HIT_SIZE)
        b[DEATH_AT], b[DEATH_AT + 1] = cause, 1
        struct.pack_into("<I", b, OWNER_AT, owner)
        for k in range(HITS):
            struct.pack_into("<iffIIBB", b, HITS_AT + k * HIT_SIZE, *(entries[k] if k < len(entries) else
                                                                    (-1, 0.0, 0.0, NONE, NONE, 0, 0)))
        return bytes(b)

    class Game:
        def __init__(s):
            s.state, s.rows, s.bodies = 1, {}, {}
            s.DEATH_AT, s.OWNER_AT, s.HITS_AT, s.HITS, s.HIT_SIZE = DEATH_AT, OWNER_AT, HITS_AT, HITS, HIT_SIZE

        def kill_watch(s):
            return s.state, dict(s.rows)

        def death_bytes(s, handle):
            return 1000, s.bodies.get(handle)

    H = lambda i: (0xEC70 + i) << 16 | i                      # noqa: E731  (a player's handle: salt, index)
    g = Game()
    g.rows = {0: (0xEC70, 0xA0, NONE, NONE), 1: (0xEC71, 0xA1, NONE, NONE), 2: (0xEC72, 0xA2, NONE, H(0))}
    w = Watch(g)
    alive = [P(0, 0, False, (1, 2, 3)), P(1, 1, True, (10, 20, 30)), P(2, 1, True, (5, 5, 5))]
    assert w.tick(Snap(alive)) == []                           # the first pass: nobody had a unit before it
    # player 1 dies to player 0's DMR (type 6) after player 2's (a teammate's) grenade: the credit is written
    g.bodies[0xA1] = body(11, H(2), [(940, 0.0, 0.6, 0xA0, H(0), 6, 0), (999, 1.0, 0.4, 0xA2, H(2), 11, 0)])
    g.rows[1] = (0xEC71, NONE, 0xA1, H(0))
    rows = w.tick(Snap([alive[0], P(1, 1, True, (0, 0, 0), alive=False), alive[2]]))
    assert len(rows) == 1, rows
    r = rows[0]
    assert (r["v"], r["k"], r["new"], r["o"], r["c"], r["m"]) == (1, 0, True, 2, 11, 1), r
    assert r["vp"] == [10, 20, 30] and r["kp"] == [1, 2, 3] and (r["vt"], r["kt"], r["vb"], r["kb"]) == (1, 0, 1, 0), r
    assert r["hits"] == [[2, 11, 0, 1.0, 0.4, 1], [0, 6, 0, 0.0, 0.6, 60]], r["hits"]
    assert read(r) == ("kill", 0, 6), read(r)                  # (the credited player's own weapon, not the last hit's)
    assert w.tick(Snap(alive)) == []                           # dead, not dying again
    # player 2 falls: the game leaves its old credit (player 0), nothing of his is on the body: nobody's kill
    g.bodies[0xA2] = body(41, NONE, [])
    g.rows[2] = (0xEC72, NONE, 0xA2, H(0))
    r = w.tick(Snap(alive))[0]
    assert (r["k"], r["new"], r["hits"]) == (0, False, []) and read(r) == ("death", None, 41), (r, read(r))
    # the same credit again with his damage on the body is a kill; on a teammate a betrayal, or a kill without teams
    r2 = dict(r, hits=[[0, 8, 1, 1.0, 0.2, 2]])
    assert read(r2) == ("kill", 0, 8) and read(dict(r2, kt=1)) == ("betrayal", 0, 8)
    assert read(dict(r2, kt=1), teams=False) == ("kill", 0, 8)
    # a melee kill leaves no entry: the credit was written, the body says what killed
    assert read(dict(r, new=True, c=43)) == ("kill", 0, 43)
    # the kill that wins the match turns the engine's state to "over" in its own tick: it counts (the state he was
    # last seen alive in); a death after it does not
    g.rows[1], g.rows[2] = (0xEC71, 0xC1, NONE, H(0)), (0xEC72, 0xC2, NONE, H(0))
    assert w.tick(Snap(alive)) == []
    g.state = OVER
    g.bodies[0xC1] = body(6, H(0), [(999, 1.0, 1.0, 0xA0, H(0), 6, 1)])
    g.rows[1] = (0xEC71, NONE, 0xC1, H(0))
    r = w.tick(Snap(alive))[0]
    assert r["st"] == 1 and read(r) == ("kill", 0, 6), r
    g.bodies[0xC2] = body(43, H(0), [(999, 1.0, 1.0, 0xA0, H(0), 43, 0)])
    g.rows[2] = (0xEC72, NONE, 0xC2, H(0))
    r = w.tick(Snap(alive))[0]
    assert r["st"] == OVER and read(r) is None, r
    g.state = 1
    # a player who leaves the game (his unit goes, no body), a death after the match is over, rows that are not rows
    g.rows[0] = (0xEC70, NONE, NONE, NONE)
    assert w.tick(Snap(alive)) == []
    assert read(dict(r2, st=OVER)) is None
    for bad in ({}, dict(r2, v="1"), dict(r2, vp=[1, 2]), dict(r2, vp=[1, 2, float("nan")]), dict(r2, hits=[[0]]),
                dict(r2, k=True), dict(r2, c="6"), None):
        assert read(bad) is None, bad
    # a body gone before the read: the credit stands, the weapon is not known
    g.rows[1] = (0xEC71, 0xB1, NONE, H(0))
    w.tick(Snap(alive))
    g.rows[1] = (0xEC71, NONE, 0xB1, H(0))
    r = w.tick(Snap(alive))[0]
    assert (r["c"], r["hits"], r["new"]) == (None, [], False) and read(r) == ("kill", 0, None), (r, read(r))
    print("kill record OK")


if __name__ == "__main__":
    selftest()

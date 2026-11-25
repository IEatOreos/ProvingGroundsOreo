"""(custom, Nov 24, the owner) The kills each enemy Banshee and Falcon has made, by the team of the man who died, for the
bots' hold fire on aircraft (brain/bot.py Bot.air_hold, brain/profiles.py air_hold_kills; docs/AIRCRAFT_HOLD_FIRE_DESIGN.md).

Live matches only: tools/live_bots.py keeps one AirKills and hands its table to the bots as snap.air_kills each pass.
Reach's kills come from the game's own record (tools/kill_record.py: the credited killer, people's deaths too); where
there is none, a bot's death as tools/live_bots.py events() credits it (a guess, bots only). Everyone aboard counts to
the aircraft: its pilot and a Falcon's gunners (live_bots folds a gun seat onto its carrier). An aircraft's count goes
when it reads destroyed or leaves the vehicle list (prune).

    python\\python.exe -I -m unittest discover -s tools -p test_air_hold.py
"""
import kill_record
from brain import vehicles as V

AIR_KINDS = {"banshee", "falcon"}


class AirKills:
    def __init__(s):
        s.kills = {}        # aircraft handle -> {victim's team: kills}

    def aircraft(s, killer, snap, before=None):
        """The handle of the Banshee or Falcon player killer rides (this pass, else the last: a trade), or None."""
        for p in (snap.player(killer) if killer is not None else None,
                  (before or {}).get(killer) if killer is not None else None):
            h = getattr(p, "vehicle", -1) if p is not None else -1
            if h in (None, -1):
                continue
            v = next((x for x in snap.vehicles if x.get("handle") == h), None)
            if v is not None and V.kind_of(v.get("kind")) in AIR_KINDS:
                return h
        return None

    def add(s, killer, victim_team, snap, before=None):
        """One kill by player killer on a man of victim_team: counted when killer rode an aircraft. True if counted."""
        h = s.aircraft(killer, snap, before)
        if h is None or victim_team is None:
            return False
        by = s.kills.setdefault(h, {})
        by[victim_team] = by.get(victim_team, 0) + 1
        return True

    def row(s, row, snap, teams, before=None):
        """A kill record row (tools/kill_record.py Watch.tick): counted when it reads as a kill (not a betrayal, a
        suicide or after the match) by a man aboard an aircraft. True if counted."""
        rec = kill_record.read(row, teams)
        if rec is None or rec[0] != "kill":
            return False
        return s.add(rec[1], row.get("vt"), snap, before)

    def prune(s, snap):
        """Drop each aircraft that reads destroyed or is no longer in the vehicle list: its count is 0 again."""
        alive = {v.get("handle") for v in snap.vehicles if not v.get("dead")}
        for h in [h for h in s.kills if h not in alive]:
            del s.kills[h]

    def table(s):
        return {h: dict(by) for h, by in s.kills.items()}

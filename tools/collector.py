"""Data collector (the BOTS panel's "Data collector"; the Observer then shows, tools/player_stats.py). tools/live_bots.py
keeps one per match when botcore.ini has collector=1 (tools/play.py passes --collect on) and it writes
logs/collect_<map>_<date>-<time>.jsonl:

  {"t", "collect": "start", "map", "game"}                                                       once
  {"t", "p": [[id, team, alive, x, y, z, yaw, pitch, shield, health, riding, flag, bot, (people only:) crosshair,
              ride], ...]}                                   everyone, every tick (brain/tracefmt.py crosshair, seat_of)
  {"t", "id", "wpn", "inv", "ammo", "mag", "eq", "ab", "uz"}    a person's guns, rounds, equipment, zoom: on change

Everything comes from the game's own memory (where everyone is, where they look, their guns and rounds). No keyboard,
mouse or controller is read: shots fired are told by the magazine going down.
"""
import json
import os


class Collector:
    def __init__(s, path, map_name, game, clock, seconds=None):
        """seconds: the longest recording, its last that many seconds kept (tools/recording.py); None: all of it."""
        s.path, s.clock = path, clock
        os.makedirs(os.path.dirname(path), exist_ok=True)
        from recording import RollingFile           # (tools/ is on the path where a collector runs)
        s.out = RollingFile(path, seconds, encoding="utf-8")
        s.last = {}                                  # person -> the last guns / equipment line written
        s.out.write(json.dumps(dict(t=round(clock(), 3), collect="start", map=map_name, game=game)) + "\n")

    def tick(s, now, players, zoom=None, aims=None):
        """players: brain.core.PlayerState list (the tick's snapshot); zoom(id) -> the unit's zoom byte or None;
        aims: person id -> (crosshair, ride), appended to that person's row (tools/live_bots.py)."""
        rows = [[p.id, p.team, int(p.alive), round(p.pos.x, 2), round(p.pos.y, 2), round(p.pos.z, 2),
                 round(p.yaw, 3), round(p.pitch, 3), round(p.shield, 2), round(p.health, 2), int(p.vehicle != -1),
                 int(p.has_flag), int(p.is_bot)] + list((aims or {}).get(p.id, ())) for p in players]
        lines = [dict(t=round(now, 3), p=rows)]
        for p in players:
            if p.is_bot:
                continue
            g = dict(wpn=p.weapon, inv=list(p.weapons), ammo=list(p.ammo), mag=list(p.mag), eq=p.equipment,
                     ab=int(p.ability_on), uz=zoom(p.id) if zoom else None)
            if s.last.get(p.id) != g:
                s.last[p.id] = g
                lines.append(dict(t=round(now, 3), id=p.id, **g))
        s.out.write("".join(json.dumps(x) + "\n" for x in lines))
        s.out.tick(now)

    def close(s):
        s.out.close()


def without_keys(text):
    """A collect file's text without what version 0.1.0 also recorded, the person's keys and controller buttons (its
    "key" rows and the start line's "keys"): everything shared goes through this."""
    out = []
    for line in text.splitlines(keepends=True):
        if '"key' in line:
            try:
                d = json.loads(line)
            except ValueError:
                d = None
            if isinstance(d, dict):
                if "key" in d:
                    continue
                if d.pop("keys", None) is not None:
                    line = json.dumps(d) + "\n"
        out.append(line)
    return "".join(out)


if __name__ == "__main__":
    old = ('{"t": 0, "collect": "start", "map": "m", "game": "h3", "keys": {"1": "fire"}}\n'
           '{"t": 0.1, "p": [[0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0]]}\n{"t": 0.2, "key": "fire", "vk": 1, "down": 1}\n')
    assert without_keys(old) == ('{"t": 0, "collect": "start", "map": "m", "game": "h3"}\n'
                                 '{"t": 0.1, "p": [[0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0]]}\n'), without_keys(old)
    print("collector OK")

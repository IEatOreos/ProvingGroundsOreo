"""The Proving Grounds Service Record (custom, Nov 15): a stats site for the bots, laid out like a 2010 service record
(the owner's brief: docs/SERVICE_RECORD_SITE_BRIEF.md). One build reads what the mod already records and writes a
folder of static pages, logs/service_record/index.html, that opens straight from the folder (no server).

Read, never written: the career ledger (native/bin/career/ledger.json, tools/bot_career.py: which matches count, who
won, the bots' restart), MCC's post-game reports (logs/trace_*.carnage.xml and MCC's own current one), the bots'
profiles, looks, saved difficulties and emblems (native/bin), each recorded match's kill rows (logs/trace_*.jsonl,
tools/kill_record.py: who the game credits with each death, with what, where both stood) and the maps' top-down
pictures (maps/<id>/topdown.png, heightmap.npz). Written: this tool's own store, native/bin/service_record/matches.json
(each report's detail kept once by its GameUniqueId, because the recording rotation deletes the reports) and kills.json
(each recording's kill rows, for the same reason), and the site in logs/service_record. All game data: not in git.

Weapons, Enemies and Heatmaps come from the kill rows only. A match recorded before they were written has none and
adds nothing to those pages (they say so; they never show a zero for it).

Who is listed (the owner, Nov 15): the bots only. Every bot of bot_profiles.ini and of Bot Matchmaking's pool
(bot_pool.txt, Nov 17), at 0 from the start, and any other bot once it has a match that counts. People are listed only when named in native/bin/service_record/people.json (Nov 17,
the owner: "Yes just me for now"; this PC only, never in git); anyone else is not, though a match's scoreboard still
shows every gamertag.
Which matches (Nov 17, the owner: "Matchmaking only"): the ones Proving Grounds started, named by MCC's GameUniqueId
in native/bin/service_record/matchmaking.txt (native/proving_grounds.cpp writes a line once each match's report is
written). A custom game played without Proving Grounds is not on the site; bot_career still counts it in totals.txt
(the bots' MCC Career pages).
Of those, a match counts by bot_career's rules (its person played 60 s or more; a bot's row of a match from before the
bots' restart does not), so over the same matches the leaderboard equals native/bin/career/totals.txt.

Credits and ranks: service_record_site/ranks.json. A player's credits are a pure function of their counted Reach
matches (each game, win, kill, assist and medal is worth what "credits" says), so a rank can always be rebuilt.

usage: python -I service_record.py                    build, then print what was built
       python -I service_record.py --quiet            build only (tools/play.py, in the background, as a match starts)
       python -I service_record.py --wait-ledger 20   first wait up to 20 s for bot_career.py to add the reports on disk
       python -I service_record.py --check-kills      also print each recorded match's kill rows against MCC's report
       --ledger FILE --logs DIR --store DIR --out DIR  other places (tests, a preview from another ledger)
"""
import datetime
import glob
import hashlib
import html
import importlib.util
import json
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SITE = os.path.join(HERE, "service_record_site")
BIN = os.path.join(ROOT, "native", "bin")
NAME = "Proving Grounds Service Record"
DEFAULT_GAME = "reach"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


career = _load("bot_career")      # (the counting rules live there: one copy)
kill_record = _load("kill_record")   # (what a kill row counts as: one reading, the recorder's own)


class Paths:
    """Where everything is read from and written to; a test or a preview names other places."""

    def __init__(s, **kw):
        s.logs = os.path.join(ROOT, "logs")
        s.ledger = os.path.join(BIN, "career", "ledger.json")
        s.store = os.path.join(BIN, "service_record")
        s.out = os.path.join(ROOT, "logs", "service_record")
        s.profiles = os.path.join(BIN, "bot_profiles.ini")
        s.looks = os.path.join(BIN, "bot_looks.ini")
        s.pool = os.path.join(BIN, "bot_pool_saved.ini")
        s.bot_pool = os.path.join(BIN, "bot_pool.txt")           # Bot Matchmaking's pool: every bot listed (Nov 17)
        s.botcore = os.path.join(BIN, "botcore.ini")             # the BOTS panel's lobby list (bot= lines, Nov 18)
        # Proving Grounds' matches, the only ones on the site (Nov 17); None: every match (the tests of what counts)
        s.matchmaking = os.path.join(BIN, "service_record", "matchmaking.txt")
        s.emblems = os.path.join(BIN, "emblems")
        s.look_names = os.path.join(ROOT, "native", "look_names.h")
        s.maps = os.path.join(ROOT, "maps")
        s.mcc_report = career.MCC_REPORT
        s.snap = os.path.join(BIN, "figure_snap.exe")         # native/build_figure_snap.bat: each bot's Reach figure
        s.models = os.path.join(BIN, "models")                # tools/make_models.py: the game's own models
        for k, v in kw.items():
            if not hasattr(s, k):
                raise TypeError(f"no such path: {k}")
            setattr(s, k, v)


# ---------------------------------------------------------------- games, maps, game types

# a trace is named trace_<game>_<map>_<date>-<time>; MCC's own report names the game by number (1, 3 and 6 checked
# against the trace names of 50 reports, Nov 15; the others are MCC's order of its games)
GAME_NAMES = {"reach": "Reach", "h4": "Halo 4", "h2": "Halo 2", "h3": "Halo 3", "ce": "Halo: CE",
              "h2a": "Halo 2: Anniversary", "odst": "Halo 3: ODST", "other": "Other"}
GAME_ENUM = {0: "ce", 1: "h2", 2: "h3", 3: "h4", 4: "h2a", 5: "odst", 6: "reach"}

# game type name -> its family (the tabs and the Games Played ring); the first rule that fits, lower case
FAMILIES = [
    ("headhunter", ("headhunter",)),
    ("stockpile", ("stockpile",)),
    ("invasion", ("invasion",)),
    ("firefight", ("firefight",)),
    ("infection", ("infection", "flood", "zombie", "safe haven", "living dead")),
    ("ctf", ("ctf", "capture the flag", "flag")),
    ("assault", ("assault", "bomb", "grifball")),
    ("territories", ("territor", "land grab", "dominion")),
    ("koth", ("king", "koth", "hill")),
    ("oddball", ("oddball", "ball", "ricochet")),
    ("juggernaut", ("juggernaut",)),
    ("race", ("race", "rally")),
    ("slayer", ("slayer", "rumble", "swat", "snipers", "regicide", "team dmr", "doubles")),
]
FAMILY_NAMES = {"slayer": "Slayer", "ctf": "CTF", "assault": "Assault", "territories": "Territories",
                "stockpile": "Stockpile", "oddball": "Oddball", "koth": "King of the Hill", "invasion": "Invasion",
                "headhunter": "Headhunter", "firefight": "Firefight", "infection": "Infection",
                "juggernaut": "Juggernaut", "race": "Race", "other": "Other", "unknown": "Unknown"}
FAMILY_ORDER = list(FAMILY_NAMES)


def family(type_name):
    """A report's GameTypeName -> its family key; "unknown" for a match with no report left, "other" for a name no
    rule fits."""
    if not type_name:
        return "unknown"
    t = type_name.lower()
    for key, words in FAMILIES:
        if any(w in t for w in words):
            return key
    return "other"


# Reach's maps by the names the game shows (the map ids are the folders of maps/); any other map shows by its id,
# tidied, never by a guessed name
MAP_NAMES = {
    "reach_20_sword_slayer": "Sword Base", "reach_30_settlement": "Powerhouse", "reach_35_island": "Spire",
    "reach_45_aftship": "Zealot", "reach_45_launch_station": "Countdown", "reach_50_panopticon": "Boardwalk",
    "reach_52_ivory_tower": "Reflection", "reach_70_boneyard": "Boneyard", "reach_forge_halo": "Forge World",
    "reach_dlc_slayer": "Anchor 9", "reach_dlc_invasion": "Breakpoint", "reach_dlc_medium": "Tempest",
    "reach_condemned": "Condemned", "reach_trainingpreserve": "Highlands", "reach_cex_damnation": "Penance",
    "reach_cex_beaver_creek": "Battle Canyon", "reach_cex_timberland": "Ridgeline",
    "reach_cex_headlong": "Breakneck", "reach_cex_hangemhigh": "High Noon", "reach_cex_prisoner": "Solitary",
}


def map_name(map_id):
    """ "reach_70_boneyard" -> "Boneyard"; "h4_ca_blood_crash" -> "Blood Crash" (its id without the game and the
    kit's prefixes)."""
    if map_id in MAP_NAMES:
        return MAP_NAMES[map_id]
    words = [w for w in map_id.split("_")[1:] if w not in ("ca", "dlc", "cex") and not re.fullmatch(r"[a-z]?\d+", w)]
    return " ".join(w.capitalize() for w in words) or map_id or "Unknown map"


FILE_MAP = re.compile(r"^trace_(.+)_(\d{8})-(\d{6})\.carnage\.xml$")


def file_parts(name):
    """("reach", "reach_forge_halo", "20261115-184329") from a kept report's file name, or ("", "", "")."""
    m = FILE_MAP.match(name or "")
    if not m:
        return "", "", ""
    return m.group(1).split("_")[0], m.group(1), f"{m.group(2)}-{m.group(3)}"


# ---------------------------------------------------------------- MCC's post-game report, in full

ATTR = re.compile(r'(\w+)="([^"]*)"')
PLAYER = re.compile(r"<Player ([^>]*)>(.*?)</Player>", re.S)
MEDAL = re.compile(r'<Medal mId="(\d+)" mCount="(\d+)"')


def _int(a, key, missing=0):
    try:
        return int(a.get(key, str(missing)))
    except ValueError:
        return missing


def read_report(path):
    """(GameUniqueId, the match in full) from one carnage report, or (None, None) when it is not one. Names are kept
    as the report writes them (the ledger's rows are matched by them)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            x = f.read()
    except OSError:
        return None, None
    gid = re.search(r'GameUniqueId="([^"]+)"', x)
    if not gid:
        return None, None
    k = x.find("<Player ")
    head = dict(ATTR.findall(x[:k] if k >= 0 else x))
    players = []
    for m in PLAYER.finditer(x):
        a = dict(ATTR.findall(m.group(1)))
        is_bot = bool(career.BOT_ID.match(a.get("mXboxUserId", "")))
        try:                                             # (a bot's made-up Xbox id ends in its index in the game: the
            index = int(a.get("mXboxUserId", ""), 16) & 0xFFFFFFFF if is_bot else None   # id the kill rows know it by)
        except ValueError:
            index = None
        players.append({
            "name": a.get("mGamertagText", ""),
            "bot": is_bot, "idx": index,
            "clan": a.get("ClantagText", ""),
            "team": _int(a, "mTeamId"), "standing": _int(a, "mStanding"), "score": _int(a, "Score"),
            "kills": _int(a, "mKills"), "deaths": _int(a, "mDeaths"), "assists": _int(a, "mAssists"),
            "betrayals": _int(a, "mBetrayals"), "suicides": _int(a, "mSuicides"),
            "spree": _int(a, "mMostKillsInARow"), "alive": _int(a, "mSecondsAlive"),
            "seconds": _int(a, "mSecondsPlayed"),
            "completed": _int(a, "mCompletedGame", 1),   # (Nov 17: played to the end; kept reports before it: 1)
            "kw": _int(a, "mKillsWeapon"), "kg": _int(a, "mKillsGrenade"), "km": _int(a, "mKillsMelee"),
            "ko": _int(a, "mKillsOther"),
            "medal_total": _int(a, "mTotalMedalCount"),
            "medals": {i: int(c) for i, c in MEDAL.findall(m.group(2)) if c != "0"},
            "_most": (_int(a, "mKilledMostPlayerIndex"), _int(a, "mKilledMostPlayerCount")),
            "_by": (_int(a, "mMostKilledByPlayerIndex"), _int(a, "mMostKilledByPlayerCount")),
        })
    if not players:
        return None, None
    for p in players:                                    # (the two rivals are named by their row in this report)
        for key, out in (("_most", "killed_most"), ("_by", "killed_by")):
            i, n = p.pop(key)
            p[out] = [players[i]["name"], n] if n > 0 and 0 <= i < len(players) else None
    game, map_id, start = file_parts(os.path.basename(path))
    return gid.group(1), {
        "file": os.path.basename(path),
        "game": game or GAME_ENUM.get(_int(head, "mGameEnum"), "other"),
        "map": map_id, "start": start,
        "type": html.unescape(head.get("GameTypeName", "")),
        "teams": head.get("IsTeamsEnabled") == "true",
        "players": players,
    }


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, path)


def update_store(store, paths):
    """Every report on disk not kept yet, added to the store (a report MCC's own file gave first is kept again once
    it stands beside its trace: that name has the map). Returns how many matches were added or bettered."""
    files, matches = store.setdefault("files", {}), store.setdefault("matches", {})
    on_disk = sorted(glob.glob(os.path.join(paths.logs, "trace_*.carnage.xml"))) + [paths.mcc_report]
    changed = 0
    for path in on_disk:
        try:
            st = os.stat(path)
        except OSError:
            continue
        key, sig = os.path.basename(path), [int(st.st_mtime), st.st_size]
        if files.get(key) == sig:
            continue
        files[key] = sig
        gid, match = read_report(path)
        if not gid:
            continue
        old = matches.get(gid)
        if old is None or (not old.get("map") and match["map"]):
            matches[gid] = match
            changed += 1
    names = {os.path.basename(p) for p in on_disk}
    for key in [k for k in files if k not in names]:         # (rotated away: its match stays, its file entry goes)
        del files[key]
        changed += 1
    return changed


# ---------------------------------------------------------------- the kill rows of each recording

TRACE_NAME = re.compile(r"^trace_(.+_\d{8}-\d{6})\.jsonl$")


def read_kills(path):
    """One recording's kill rows as written (tools/kill_record.py): {"v": the recorder's version, "rows": [{...,
    "t": seconds into the match}]}, or None when it was recorded without them (no kill_record line among its first
    lines) or cannot be read. Read-only. The store keeps this as it is; kill_rows reads it."""
    try:
        with open(path, "rb") as f:
            mark = re.search(rb'"kill_record": (\d+)', f.read(1 << 18))
            if not mark:
                return None
            f.seek(0)
            rows = []
            for line in f:
                if b'"kill": ' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue                                # (a line cut short: the brain was stopped mid-write)
                k = d.get("kill") if isinstance(d, dict) else None
                if isinstance(k, dict):
                    rows.append(dict(k, t=d.get("t")))
            return {"v": int(mark.group(1)), "rows": rows}
    except OSError:
        return None


def kill_rows(entry):
    """A stored recording's kill rows as version 2 of the recorder writes them. entry: what read_kills gave, or the
    bare list of rows the store kept on its first day (version 1, as written).

    Version 1 wrote the engine's state as read after each death, so the kill that won the match reads as "over" (live
    Powerhouse 20261115-203100: MCC's report counted that kill; it did not count the kill 6 s later, whose credit the
    game never wrote). Its first "over" row is "played" when the game wrote its credit at that death. Done here, each
    time the rows are used, so what the store keeps stays what the recording said."""
    version, rows = (entry.get("v", 1), entry.get("rows", [])) if isinstance(entry, dict) else (1, entry)
    rows = [k for k in rows if isinstance(k, dict)] if isinstance(rows, list) else []
    if version == 1:
        over = [k for k in rows if k.get("st") == kill_record.OVER and isinstance(k.get("t"), (int, float))]
        last = min(over, key=lambda k: k["t"], default=None)
        if last is not None and last.get("new") is True:
            rows = [dict(k, st=1) if k is last else k for k in rows]
    return rows


def update_kills(store, paths):
    """Every finished recording's kill rows not kept yet, added to the store under its map and start time
    ("reach_70_boneyard_20261115-195851", as its report's file is named). Finished: its report stands beside it.
    Returns how many recordings were read or dropped from the list of files."""
    files, kills = store.setdefault("files", {}), store.setdefault("kills", {})
    changed, names = 0, set()
    for rep in sorted(glob.glob(os.path.join(paths.logs, "trace_*.carnage.xml"))):
        path = rep[:-len(".carnage.xml")] + ".jsonl"
        m = TRACE_NAME.match(os.path.basename(path))
        try:
            st = os.stat(path)
        except OSError:
            continue
        if not m:
            continue
        key, sig = os.path.basename(path), [int(st.st_mtime), st.st_size]
        names.add(key)
        if files.get(key) == sig:
            continue
        files[key] = sig
        changed += 1
        entry = read_kills(path)
        if entry is not None:
            kills[m.group(1)] = entry
    for key in [k for k in files if k not in names]:         # (rotated away: its rows stay)
        del files[key]
        changed += 1
    return changed


def kill_names(detail, rows):
    """{player id: the name in MCC's report} for a match's kill rows, which know players by their index in the game.
    A bot: the report row whose made-up Xbox id ends in that index. A person: the one report row of a person on their
    team whose kills and deaths are nearest the rows'; left out when two fit as well."""
    names = {p["idx"]: p["name"] for p in detail["players"] if p.get("bot") and p.get("idx") is not None}
    seen = {}                                               # person id -> [team, kills, deaths] by the rows
    for k in rows:
        f = kill_record.read(k, detail.get("teams", True))
        if not f:
            continue
        if not k.get("vb"):
            seen.setdefault(k["v"], [k.get("vt"), 0, 0])[2] += 1
        if f[0] == "kill" and not k.get("kb"):
            seen.setdefault(f[1], [k.get("kt"), 0, 0])[1] += 1
    people = [p for p in detail["players"] if not p.get("bot")]
    for pid, (team, kills, deaths) in sorted(seen.items()):
        fits = [p for p in people if team is None or p["team"] == team] or people
        ranked = sorted(fits, key=lambda p: abs(p["kills"] - kills) + abs(p["deaths"] - deaths))
        if len(ranked) == 1 or (len(ranked) > 1 and abs(ranked[0]["kills"] - kills) + abs(ranked[0]["deaths"] - deaths)
                                < abs(ranked[1]["kills"] - kills) + abs(ranked[1]["deaths"] - deaths)):
            names[pid] = ranked[0]["name"]
            people = [p for p in people if p is not ranked[0]]
    return names


UNNAMED = "Unknown player"


def kill_tally(detail, rows):
    """{name: {"weapons": {damage type: [kills, deaths]}, "versus": {name: [kills on, deaths to]}, "k": [x, y, ...],
    "d": [x, y, ...]}} for one match: every row that counts, summed for both players of it. A kill is one the game
    credits to a player of the other team (kill_record.read); a death is any way of dying."""
    who, out = kill_names(detail, rows), {}

    def side(name):
        return out.setdefault(name, {"weapons": {}, "versus": {}, "k": [], "d": []})

    for k in rows:
        f = kill_record.read(k, detail.get("teams", True))
        if not f:
            continue                                        # (not a row, or written after the match was over)
        kind, killer, weapon = f
        key = "?" if weapon is None else str(weapon)
        victim, by = who.get(k["v"]), who.get(killer) if killer is not None else None
        if victim is not None:
            s = side(victim)
            s["weapons"].setdefault(key, [0, 0])[1] += 1
            s["d"] += [round(k["vp"][0], 1), round(k["vp"][1], 1)]
            if kind == "kill":
                s["versus"].setdefault(by or UNNAMED, [0, 0])[1] += 1
        if kind == "kill" and by is not None:
            s = side(by)
            s["weapons"].setdefault(key, [0, 0])[0] += 1
            s["versus"].setdefault(victim or UNNAMED, [0, 0])[0] += 1
            if k.get("kp"):
                s["k"] += [round(k["kp"][0], 1), round(k["kp"][1], 1)]
    return out


def kill_feed(detail, rows, game):
    """[[seconds into the match, killer, victim, "<game>:<damage type>", kind], ...] oldest first: a match's carnage
    report's kill feed, every row that counts (kill_record.read; kind "kill", "betrayal" or "death", a death having no
    killer). A player the rows cannot name is "Unknown player"; a seconds the recording lacks is None."""
    who, feed = kill_names(detail, rows), []
    for k in rows:
        f = kill_record.read(k, detail.get("teams", True))
        if not f:
            continue
        kind, killer, weapon = f
        t = k.get("t")
        feed.append([round(t, 1) if isinstance(t, (int, float)) and not isinstance(t, bool) else None,
                     html.unescape(who.get(killer, UNNAMED)) if killer is not None else None,
                     html.unescape(who.get(k["v"], UNNAMED)), f"{game}:{'?' if weapon is None else weapon}", kind])
    feed.sort(key=lambda r: (r[0] is None, r[0] or 0))
    return feed


def feed_feats(feed, winners):
    """{name: {"first": 1, "closer": 1, "grudge": n}} from one match's kill feed (kill_feed, oldest first): who got its
    first kill, who got its last kill when that player's side won the match (winners: the names that won), and for
    each player how many enemies they killed 5 times or more (the Proving Grounds commendations). Kills only: a
    betrayal or a death with no killer is not one."""
    kills = [r for r in feed if r[4] == "kill" and r[1] and r[1] != UNNAMED]
    out = {}
    if kills:
        out.setdefault(kills[0][1], {})["first"] = 1
        if kills[-1][1] in winners:
            out.setdefault(kills[-1][1], {})["closer"] = 1
    pairs = {}
    for r in kills:
        pairs[(r[1], r[2])] = pairs.get((r[1], r[2]), 0) + 1
    for (killer, _), n in pairs.items():
        if n >= 5:
            out.setdefault(killer, {})["grudge"] = out.get(killer, {}).get("grudge", 0) + 1
    return out


def kill_check(detail, rows):
    """[(name, kills by the rows, kills in MCC's report, deaths by the rows, deaths in the report)] for every player
    of a match's report: how its kill rows compare with MCC's own numbers (--check-kills)."""
    who, kills, deaths = kill_names(detail, rows), {}, {}
    for k in rows:
        f = kill_record.read(k, detail.get("teams", True))
        if not f:
            continue
        if k["v"] in who:
            deaths[who[k["v"]]] = deaths.get(who[k["v"]], 0) + 1
        if f[0] == "kill" and f[1] in who:
            kills[who[f[1]]] = kills.get(who[f[1]], 0) + 1
    return [(html.unescape(p["name"]), kills.get(p["name"], 0), p["kills"], deaths.get(p["name"], 0), p["deaths"])
            for p in detail["players"]]


# ---------------------------------------------------------------- the bots' own files

def read_profiles(path):
    """{name: clan tag} for every bot of bot_profiles.ini, in its order."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("bot="):
                    parts = line[4:].rstrip("\r\n").split(",", 3)
                    if parts[0]:
                        out[parts[0]] = parts[2] if len(parts) > 2 else ""
    except OSError:
        pass
    return out


def read_pool(path):
    """{name: (difficulty, play style)} from bot_pool_saved.ini (saved=<difficulty>,<style>,<name>)."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("saved="):
                    parts = line[6:].rstrip("\r\n").split(",", 2)
                    if len(parts) == 3 and parts[2]:
                        out[parts[2]] = (parts[0], parts[1])
    except OSError:
        pass
    return out


def pool_name(name):
    """A name as the BOTS panel keeps it (bots_panel.cpp pool_clean): leading blanks, characters outside printable
    ASCII and commas dropped, cut to 15, trailing spaces dropped. The panel matches names without case."""
    out = "".join(c for c in name.lstrip(" \t") if " " <= c <= "~" and c != ",")[:15]
    return out.rstrip(" ")


LOBBY_DIFFICULTY = ("Easy", "Normal", "Heroic", "Legendary", "Mixed", "Scaling", "Demon", "Blind", "Tactician", "Mythic")


def read_lobby(path):
    """(Nov 18) The BOTS panel's lobby (botcore.ini): its "for everyone" difficulty's name (difficulty=, shared.h:
    0..3 the ranks, 4 Mixed, 5 Scaling, 6 Demon, 7 Blind, 8 Tactician, 9 Mythic; "" when not read) and {lower name:
    tier key} of the bots on its lists (bot=<team>,<tier>,<style>,<name>; ffbot= Firefight's, the bot= line first)."""
    level, tiers = "", {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if line.startswith("difficulty=") and line[11:].strip().isdigit():
                    d = int(line[11:].strip())
                    level = LOBBY_DIFFICULTY[d] if d < len(LOBBY_DIFFICULTY) else ""
                for key in ("bot=", "ffbot="):
                    parts = line[len(key):].split(",", 3) if line.startswith(key) else []
                    if len(parts) == 4 and pool_name(parts[3]):
                        tiers.setdefault(pool_name(parts[3]).lower(), parts[1].strip().lower())
    except OSError:
        pass
    return level, tiers


def read_pool_names(path):
    """[name] of Bot Matchmaking's pool (bot_pool.txt, BOTS panel > Settings): one a line in queue order, cut to 15,
    a repeat (or Name*N, one clan member however many times it is queued) once, # and ; lines notes."""
    out, seen = [], set()
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                name = re.sub(r"\*\s*\d+\s*$", "", line.strip()).strip()[:15]
                if name and name[0] not in "#;" and name not in seen:
                    seen.add(name)
                    out.append(name)
    except OSError:
        pass
    return out


def read_look_names(path):
    """{"ED_REACH_HELMET": {0: "Mark V [B]", ...}, ...} from native/look_names.h (its generator is not in the repo)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return {}
    out = {}
    for name, body in re.findall(r"static const piece (ED_\w+)\[\] = \{(.*?)\};", text, re.S):
        out[name] = {int(i): s.replace('\\"', '"') for i, s in re.findall(r'\{(\d+), "((?:[^"\\]|\\.)*)"\}', body)}
    return out


REACH_PIECES = [("helmet", "Helmet", "ED_REACH_HELMET"), ("left_shoulder", "Left shoulder", "ED_REACH_LEFT_SHOULDER"),
                ("right_shoulder", "Right shoulder", "ED_REACH_RIGHT_SHOULDER"), ("chest", "Chest", "ED_REACH_CHEST"),
                ("wrist", "Wrist", "ED_REACH_WRIST"), ("utility", "Utility", "ED_REACH_UTILITY"),
                ("knees", "Knee guards", "ED_REACH_KNEES"), ("visor", "Visor colour", "ED_REACH_VISOR"),
                ("armor_effect", "Armor effect", "ED_REACH_ARMOR_EFFECT")]


def read_looks(path, names):
    """{bot: {"species": "Spartan" | "Elite", "pieces": [[label, name], ...]}}: each bot's Reach look as rolled
    (bot_looks.ini, its own-species line), every piece by the Armory's name. A value the tables do not name is left
    out, never guessed."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return out
    for line in lines:
        parts = line.rstrip("\r\n").split("|", 3)
        if len(parts) != 4 or parts[1] != "reach" or parts[2] != "own":
            continue
        kv = dict(x.split("=", 1) for x in parts[3].split(";") if "=" in x)
        elite = kv.get("species") == "1"                    # (brain/looks.py: 0 Spartan, 1 Elite)
        pieces = []
        wanted = [("elite_armor", "Armor", "ED_REACH_ELITE_ARMOR")] if elite else REACH_PIECES
        for key, label, table in wanted:
            v = kv.get(key, "")
            if v.isdigit() and int(v) in names.get(table, {}):
                pieces.append([label, names[table][int(v)]])
        if elite and kv.get("armor_effect", "").isdigit():
            v = names.get("ED_REACH_ARMOR_EFFECT", {}).get(int(kv["armor_effect"]))
            if v:
                pieces.append(["Armor effect", v])
        body = "elite" if elite else "spartan_female" if kv.get("gender") == "1" else "spartan"
        out[parts[0]] = {"species": "Elite" if elite else "Spartan", "pieces": pieces, "body": body}
    return out


def png(width, height, rgba):
    """An RGBA picture as PNG bytes (the standard library only)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    row = width * 4
    raw = b"".join(b"\0" + rgba[y * row:(y + 1) * row] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def export_emblem(name, paths):
    """The bot's emblem (native/bin/emblems/<name>.rgba: width, height, RGBA) as emblems/<hash>.png in the site;
    the site-relative path, or None when there is no picture of it."""
    src = os.path.join(paths.emblems, name + ".rgba")
    if not os.path.exists(src):                             # (the game's spelling of the name: "Name " is "Name")
        src = os.path.join(paths.emblems, pool_name(html.unescape(name)) + ".rgba")
    rel = "emblems/" + hashlib.md5(name.encode("utf-8")).hexdigest()[:12] + ".png"
    dst = os.path.join(paths.out, *rel.split("/"))
    try:
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            return rel
        with open(src, "rb") as f:
            data = f.read()
        w, h = struct.unpack_from("<II", data)
        if not 0 < w <= 1024 or not 0 < h <= 1024 or len(data) < 8 + w * h * 4:
            return None
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst + ".tmp", "wb") as f:
            f.write(png(w, h, data[8:8 + w * h * 4]))
        os.replace(dst + ".tmp", dst)
        return rel
    except (OSError, struct.error):
        return None


def make_emblems(names, paths):
    """(Nov 18, the owner: "distribute an emblem to every bot on the site so they have one show on the leaderboards")
    the emblem picture of each bot here that has none yet (native/bin/emblems/<name>.rgba and its lobby numbers,
    <name>.ids): the one it would get when first seated in a lobby (brain/emblems.py export: its pick, else the roll of
    its seed), so a bot never in a lobby has one too. Only into the mod's own emblem folder (a test's paths elsewhere:
    nothing), names the folder can hold. Returns how many pictures were made."""
    want = sorted({pool_name(n) for n in names if not os.path.exists(os.path.join(paths.emblems, n + ".rgba"))})
    want = [n for n in want if n and not re.search(r'[\\/:*?"<>|]', n)   # (the game's spelling: "Name " is "Name")
            and not os.path.exists(os.path.join(paths.emblems, n + ".rgba"))]
    if not want:
        return 0
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from brain import emblems, looks
        if os.path.normcase(os.path.abspath(emblems.OUT)) != os.path.normcase(os.path.abspath(paths.emblems)):
            return 0
        return emblems.export([(n, looks.seed_of(n)) for n in want])
    except (ImportError, OSError, ValueError):
        return 0


def map_frame(path):
    """[x0, y0, width, height]: the part of the level a map's top-down picture shows, in the level's units, from its
    heightmap.npz (tools/heightmap.py draws the picture from that grid: x0, y0 its corner, cell its step, north up);
    None when the file is not there or not one. Read without numpy: only the arrays' headers and three numbers."""
    def head(z, name):
        f = z.open(name + ".npy")
        if f.read(6) != b"\x93NUMPY":
            raise ValueError(name)
        major = f.read(2)[0]
        n = struct.unpack("<H" if major == 1 else "<I", f.read(2 if major == 1 else 4))[0]
        text = f.read(n).decode("latin-1")
        descr = re.search(r"'descr':\s*'([^']+)'", text).group(1)
        shape = [int(x) for x in re.search(r"'shape':\s*\(([^)]*)\)", text).group(1).split(",") if x.strip()]
        return f, descr, shape

    def number(z, name):
        f, descr, shape = head(z, name)
        fmt = {"<f8": "<d", "<f4": "<f", "<i8": "<q", "<i4": "<i"}[descr]
        if shape:
            raise ValueError(name)
        return float(struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0])

    try:
        with zipfile.ZipFile(path) as z:
            rows, cols = head(z, "top")[2]
            x0, y0, cell = number(z, "x0"), number(z, "y0"), number(z, "cell")
        if not (rows > 0 and cols > 0 and cell > 0):
            return None
        return [round(x0, 3), round(y0, 3), round(cols * cell, 3), round(rows * cell, 3)]
    except (OSError, KeyError, ValueError, AttributeError, struct.error, zipfile.BadZipFile):
        return None


PIECES_DRAWN = 2                  # (the overlay's own version: a change to how pieces are drawn redraws every picture)


def map_pieces(map_id, variant, paths):
    """[(pos, (forward, left, up), lo, hi, name, faces or None)]: the solid things the level's own top-down picture
    lacks. A Forge layout (variant: its id under maps/<map>/variants): every piece the mod read in its match
    (variant.json "pieces", brain/forge.block: energy, holograms and markers left out). The base map: its scenario's
    placed objects, crates, barriers and the like (objects.json, brain/placed.static_boxes). Each with its collision
    faces when the editing kit has them (maps/_shapes/reach_faces.json), else its box. [] when nothing can be read."""
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from brain import forge, placed
    except ImportError:
        return []
    out = []
    try:
        if variant:
            v = load_json(os.path.join(paths.maps, map_id, "variants", variant, "variant.json"), {})
            for p in v.get("pieces", []):
                if not (isinstance(p, list) and len(p) == 13 and isinstance(p[0], str)):
                    continue
                b = forge.block(p[0], tuple(p[1:4]), (tuple(p[4:7]), tuple(p[7:10]), tuple(p[10:13])))
                if b:
                    out.append(b if len(b) == 6 else b + (None,))
        else:
            objs = load_json(os.path.join(paths.maps, map_id, "objects.json"), {})
            faces = forge._faces("reach")
            seen = set()
            for b in placed.static_boxes(objs):
                key = (b[4], b[0])                          # (a rolled object comes twice, once per roll sense)
                if key not in seen:
                    seen.add(key)
                    out.append(b + (faces.get(b[4]),))
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return []
    return out


def draw_pieces(img, frame, pieces):
    """The pieces drawn from above onto a top-down picture (a PIL image showing `frame` [x0, y0, width, height], north
    up): every face that is not a wall filled, lighter the higher it stands, walls as their edge, low first so a piece's
    top covers what is under it; a piece with no faces known is its box's top."""
    from PIL import ImageDraw
    W, H = img.size
    x0, y0, fw, fh = frame

    def px(x, y):
        return ((x - x0) / fw * W, (1 - (y - y0) / fh) * H)

    polys = []
    for pos, (f, l, u), lo, hi, name, faces in pieces:
        def world(a, b, c):
            return (pos[0] + a * f[0] + b * l[0] + c * u[0], pos[1] + a * f[1] + b * l[1] + c * u[1], pos[2] + a * f[2] + b * l[2] + c * u[2])
        shapes = []
        if faces:
            for mat, flat in faces:
                if any(m in mat for m in ("energy", "hologram")) or len(flat) < 9:
                    continue
                shapes.append([world(*flat[k:k + 3]) for k in range(0, len(flat) - 2, 3)])
        else:
            shapes.append([world(a, b, hi[2]) for a, b in ((lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1]))])
        for pts in shapes:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts[0], pts[1], pts[2]
            nz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)       # (twice the face's area seen from above)
            area = abs(sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts))))
            wall = area < 0.02 or abs(nz) < 1e-6
            polys.append((sum(p[2] for p in pts) / len(pts), wall, [px(p[0], p[1]) for p in pts]))
    if not polys:
        return img
    zs = sorted(z for z, wall, _ in polys if not wall) or [0.0]
    lo_z, hi_z = zs[len(zs) // 20], zs[-1 - len(zs) // 20]           # (the colours over the middle 90% of heights)
    layer = img.copy()
    d = ImageDraw.Draw(layer)
    for z, wall, pts in sorted(polys, key=lambda q: q[0]):
        if wall:
            d.line(pts + [pts[0]], fill=(20, 32, 44, 255), width=1)
            continue
        t = 0.0 if hi_z <= lo_z else min(1.0, max(0.0, (z - lo_z) / (hi_z - lo_z)))
        fill = tuple(int(a + (b - a) * t) for a, b in zip((96, 112, 132), (226, 234, 244))) + (255,)
        d.polygon(pts, fill=fill, outline=(28, 40, 54, 255))
    return layer


def variant_title(map_id, variant, paths):
    """A Forge layout's name for the page: its own name, else its map variant file's (hr_forgeWorld_pinnacle.mvar ->
    Pinnacle), else its id."""
    v = load_json(os.path.join(paths.maps, map_id, "variants", variant, "variant.json"), {})
    name = v.get("name") or ""
    if name and not name.startswith("$"):
        return name
    stem = os.path.splitext((v.get("mvar") or {}).get("file") or "")[0]
    stem = re.sub(r"^(hr_)?(forge_?world_?|forgeworld_?)", "", stem, flags=re.I)
    if stem:
        return stem.replace("_", " ").strip().title()
    seen = v.get("first_seen", "")
    try:
        return "Forge layout from " + time.strftime("%b %d", time.strptime(seen[:10], "%Y-%m-%d")).replace(" 0", " ")
    except ValueError:
        return "Forge layout"


def match_variant(map_id, start, spots, paths):
    """The Forge layout (its id) a match was played on, or None for the map itself: of the layouts filed under the map
    (maps/<map>/variants/*/variant.json) the ones seen around the match's start (first_seen ... last_seen, to the
    minute), and of those the one whose window holds most of the match's kill and death spots (spots: [x, y, ...])."""
    folder = os.path.join(paths.maps, map_id or "", "variants")
    if not map_id or not start or not os.path.isdir(folder):
        return None
    try:
        when = time.strftime("%Y-%m-%d %H:%M", time.strptime(start, "%Y%m%d-%H%M%S"))
    except ValueError:
        return None
    pts = list(zip(spots[0::2], spots[1::2]))
    best = None
    for vid in sorted(os.listdir(folder)):
        v = load_json(os.path.join(folder, vid, "variant.json"), {})
        if not v.get("pieces") or not (v.get("first_seen", "9") <= when <= v.get("last_seen", "")):
            continue
        w = v.get("window") or [0, 0, 0, 0]
        inside = sum(1 for x, y in pts if w[0] <= x <= w[2] and w[1] <= y <= w[3])
        score = (inside, v.get("last_seen", ""))
        if pts and inside < 0.6 * len(pts):
            continue                                        # (its window is elsewhere on the map)
        if best is None or score > best[0]:
            best = (score, vid)
    return best[1] if best else None


def export_map(map_id, paths, variant=None):
    """A map's top-down picture for the Heatmaps page: {"img": site path, "frame": [x0, y0, width, height]}, written into
    the site (maps/<id>.png, game-derived, never in git) with what the level's own picture lacks drawn on: the base
    map's placed objects, or a Forge layout's pieces (variant: then the picture is cut to the layout's window, at the
    picture's own sharpness). None when this PC has no picture of the map or its frame cannot be read: the page then
    plots on a plain panel."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", map_id or "") or (variant and not re.fullmatch(r"v[0-9a-f]{8}", variant)):
        return None
    src = os.path.join(paths.maps, map_id, "topdown.png")
    frame = map_frame(os.path.join(paths.maps, map_id, "heightmap.npz"))
    if not frame or not os.path.isfile(src):
        return None
    name = map_id + ("__" + variant if variant else "")
    dst = os.path.join(paths.out, "maps", name + ".png")
    extra = os.path.join(paths.maps, map_id, "variants", variant, "variant.json") if variant else os.path.join(paths.maps, map_id, "objects.json")
    stamp = os.path.join(paths.out, "maps", name + ".drawn")
    try:
        newest = max(os.path.getmtime(p) for p in (src, extra, os.path.abspath(__file__)) if os.path.exists(p))
        fresh = os.path.exists(dst) and os.path.getmtime(dst) >= newest and load_json(stamp, {}).get("v") == PIECES_DRAWN
        if variant:
            w = load_json(extra, {}).get("window") or []
            if len(w) != 4:
                return None
            m = 12.0                                        # (room round the layout's window, inside the level's picture)
            fx1, fy1 = frame[0] + frame[2], frame[1] + frame[3]
            x0, y0 = max(frame[0], w[0] - m), max(frame[1], w[1] - m)
            x1, y1 = min(fx1, w[2] + m), min(fy1, w[3] + m)
            if x1 - x0 < 4 or y1 - y0 < 4:
                return None
            frame = [round(v, 3) for v in (x0, y0, x1 - x0, y1 - y0)]
        if not fresh:
            from PIL import Image
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with Image.open(src) as im:
                img = im.convert("RGBA")
            full = map_frame(os.path.join(paths.maps, map_id, "heightmap.npz"))
            if variant:                                     # (the layout's part of the level's picture)
                W, H = img.size
                box = (int((frame[0] - full[0]) / full[2] * W), int((1 - (frame[1] + frame[3] - full[1]) / full[3]) * H),
                       int((frame[0] + frame[2] - full[0]) / full[2] * W), int((1 - (frame[1] - full[1]) / full[3]) * H))
                img = img.crop(box)
            img = draw_pieces(img, frame, map_pieces(map_id, variant, paths))
            img.convert("RGB").save(dst + ".tmp.png", "PNG", optimize=True)
            os.replace(dst + ".tmp.png", dst)
            save_json(stamp, {"v": PIECES_DRAWN})
    except (OSError, ValueError, ImportError):
        return None
    return {"img": "maps/" + name + ".png", "frame": frame}


def load_weapons(path=os.path.join(SITE, "weapons.json")):
    """{game: ({damage type: name}, {types matched live})} from the site's table of what each number is."""
    table = load_json(path, {})
    return {g: ({str(k): str(v) for k, v in t.get("names", {}).items()}, {str(k) for k in t.get("checked", [])})
            for g, t in table.items() if isinstance(t, dict)}


# ---------------------------------------------------------------- credits and ranks

def load_ranks(path=os.path.join(SITE, "ranks.json")):
    """(credits {game, win, kill, assist, medal}, steps [[label, rank, grade, credits], ...] lowest first)."""
    with open(path, encoding="utf-8") as f:
        table = json.load(f)
    steps = []
    for r in table["ranks"]:
        for grade, cr in enumerate(r["cr"]):
            steps.append([r["rank"] + (f" Grade {grade}" if grade else ""), r["rank"], grade, cr])
    if any(b[3] <= a[3] for a, b in zip(steps, steps[1:])) or steps[0][3] != 0:
        raise ValueError("ranks.json: the credits must start at 0 and rise")
    return table["credits"], steps


DEEDS = ("mvp", "game_changer", "positive", "loyal")
OBJECTIVE_FAMILIES = {"ctf", "assault", "koth", "oddball", "headhunter", "stockpile", "territories"}


def match_deeds(p, d, cat, top):
    """(Nov 17, the owner's four: "Mvp, Game Changer, Positive thinking, Loyal soldier") what one player's match counts
    towards them: MVP, the most points (MCC's Score; ties too) in a Slayer game; Game Changer, the same in an objective
    game (CTF, Assault, King, Oddball, Headhunter, Stockpile, Territories: its Score is the objective's points);
    Positive Thinking, more kills than deaths in a game played to the end; Loyal Soldier, a game played to the end.
    p: the ledger's row, d: MCC's report's row (None: no report kept; the points ones need it, a game then counts as
    played to the end), cat: the match's family, top: its highest Score."""
    finished = not d or d.get("completed", 1) != 0
    best = bool(d) and top > 0 and d.get("score", 0) == top
    return {"mvp": int(best and cat == "slayer"), "game_changer": int(best and cat in OBJECTIVE_FAMILIES),
            "positive": int(finished and p["kills"] > p["deaths"]), "loyal": int(finished)}


def stockpile_flags(d, cat):
    """(Nov 19, Mission First) the flags one player brought home in a Stockpile game: MCC's Score there, which no medal
    says (the store's three Stockpile games of Nov 16-18: 0 to 4 a player, 10 for the team that won to 10). 0 in any
    other game and with no report kept. d: MCC's report's row, cat: the match's family."""
    return max(0, int(d.get("score", 0))) if d and cat == "stockpile" else 0


def load_commendations(path=os.path.join(SITE, "commendations.json")):
    """(tier names, [commendation, ...]) from the site's table; a commendation whose tiers do not rise is left out."""
    table = load_json(path, {})
    tiers = table.get("tiers") or ["Iron", "Bronze", "Silver", "Gold", "Onyx", "Max"]
    good = []
    for c in table.get("commendations", []):
        need, cr = c.get("need", []), c.get("cr", [])
        if (len(need) == len(cr) == len(tiers) and all(isinstance(x, int) and x >= 0 for x in need + cr)
                and all(b > a for a, b in zip(need, need[1:])) and isinstance(c.get("count"), dict)):
            good.append(c)
    return tiers, good


def commendation_counts(g, comms, medal_info):
    """{commendation key: its count, or None when it cannot be counted yet}: one player's Reach record (g: its "reach"
    game of collect) against the table. Medals by MCC's id (medal_info: art/medals.json; without it, medal ones are
    None); report numbers over every counted match; weapon and vehicle kills from the kill record (None when no match of
    the player has kill rows: not recorded, never 0)."""
    medals, s, weapons = g.get("medals", {}), g.get("cats", {}).get("all") or blank(), g.get("weapons", {})
    ids = {info.get("key"): str(i) for i, info in medal_info.items() if isinstance(info, dict)}
    group = {str(i): medal_group(info) for i, info in medal_info.items() if isinstance(info, dict)}
    vehicles = set(vehicle_keys())
    out = {}
    for c in comms:
        how = c["count"]
        n = None
        if "group" in how and medal_info:
            n = sum(v for i, v in medals.items() if group.get(str(i)) == how["group"])
        elif "medals" in how and medal_info:
            n = sum(medals.get(ids[k], 0) for k in how["medals"] if k in ids)
        elif "stat" in how:
            n = int(s.get(how["stat"], 0))
        elif "feed" in how and g.get("kill_games"):            # (first kills, closers, grudges: the kill record)
            n = int(g.get("feats", {}).get(how["feed"], 0))
        elif "deed" in how:                                      # (Nov 17: MVP, Game Changer, Positive, Loyal)
            n = int(g.get("deeds", {}).get(how["deed"], 0))
        elif how.get("distinct_medals"):                         # (kinds of medal earned at least once)
            n = sum(1 for v in medals.values() if v)
        elif ("weapons" in how or "vehicles" in how) and g.get("kill_games"):
            keys = vehicles if how.get("vehicles") else {f"reach:{w}" for w in how.get("weapons", [])}
            n = sum(v[0] for k, v in weapons.items() if k in keys)
        if n is not None and how.get("plus_deed"):               # (Nov 19, Mission First: Stockpile's flags, a count
            n += int(g.get("deeds", {}).get(how["plus_deed"], 0))    # of the matches' own beside the medals)
        out[c["key"]] = n
    return out


TIER_FILES = ("iron", "bronze", "silver", "gold", "onyx", "max")
BANNER_BLUE = (64, 95, 128)        # the commendation banners' flat blue


def tier_banners(keys, paths):
    """{commendation: [None, iron banner, bronze ..., max]}: each Reach banner (art/commendations/<key>.png) with its
    grey emblem swapped for the owner's emblem of that tier (art/commendations/tiers/<tier>/<key>_<tier>.png, 448 x 448
    on transparency, Nov 16), written into the site (commendations/<key>_<tier>.png, not in git) and redrawn when either
    picture is newer. The old emblem is found as the banner's not-blue pixels on its blue end and painted over with the
    blue; the new one goes where it stood, at its size. A tier with no emblem of the owner's is left out (the page keeps
    the banner as it is)."""
    out = {}
    art = os.path.join(paths.store, "art", "commendations")
    for key in keys:
        base = os.path.join(art, key + ".png")
        if not os.path.exists(base) or not re.fullmatch(r"[a-z0-9_]+", key):
            continue
        row = [None] * (len(TIER_FILES) + 1)
        banner = box = None
        for i, tier in enumerate(TIER_FILES, 1):
            emb = os.path.join(art, "tiers", tier, f"{key}_{tier}.png")
            dst = os.path.join(paths.out, "commendations", f"{key}_{tier}.png")
            if not os.path.exists(emb):
                continue
            frame_pic = os.path.join(art, "frames", tier + ".png")
            try:
                newest = max(os.path.getmtime(p) for p in (emb, base, os.path.abspath(__file__), frame_pic) if os.path.exists(p))
                if not os.path.exists(dst) or os.path.getmtime(dst) < newest:
                    from PIL import Image, ImageFilter
                    if banner is None:
                        banner, box = clean_banner(base)
                    with Image.open(emb) as e:
                        e = e.convert("RGBA")
                        e = e.crop(e.getbbox() or (0, 0, e.width, e.height))
                    bw, bh = box[2] - box[0], box[3] - box[1]
                    s = min(bw / e.width, bh / e.height) * 1.04
                    e = e.resize((max(1, round(e.width * s)), max(1, round(e.height * s))), Image.LANCZOS)
                    img = banner.copy()
                    img.alpha_composite(e, (box[0] + (bw - e.width) // 2, box[1] + (bh - e.height) // 2))
                    img = framed(img, tier, art)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    img.save(dst + ".tmp.png")
                    os.replace(dst + ".tmp.png", dst)
                row[i] = f"commendations/{key}_{tier}.png"
            except (OSError, ValueError):
                continue
        if any(row):
            out[key] = row
    return out


TIER_RGB = {"iron": (142, 149, 157), "bronze": (192, 132, 76), "silver": (207, 219, 230), "gold": (232, 178, 60),
            "onyx": (155, 92, 217), "max": (216, 50, 58)}     # (style.css --tier-*: the owner's tier colours)
STRIP = (238, 77, 274, 86)         # the banner's small blue progress strip (x0, y0, x1, y1)


def framed(img, tier, art):
    """A tier banner in its tier's outline (the owner asked for "the colored outlines for each rank", Nov 16): its
    progress strip in the tier colour, then the owner's frame of that tier around it (art/commendations/frames/<tier>.png
    with frames.json {tier: [x0, y0, x1, y1]}, the frame's opening, made by cutting his frame sheet), else a glowing
    outline of the tier colour drawn round it."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    col = TIER_RGB.get(tier, (142, 149, 157))
    a = np.asarray(img).copy()
    x0, y0, x1, y1 = STRIP
    part = a[y0:y1, x0:x1].astype(np.int16)
    blue = (part[..., 2] - (part[..., 0] + part[..., 1]) // 2) > 20
    part[blue, :3] = col
    a[y0:y1, x0:x1] = part.astype(np.uint8)
    img = Image.fromarray(a, "RGBA")
    pic = os.path.join(art, "frames", tier + ".png")
    box = load_json(os.path.join(art, "frames", "frames.json"), {}).get(tier)
    if os.path.exists(pic) and isinstance(box, list) and len(box) == 4:
        with Image.open(pic) as f:
            frame = f.convert("RGBA")
        ow, oh = box[2] - box[0], box[3] - box[1]
        s = min(ow / img.width, oh / img.height)
        inner = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
        out = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        out.alpha_composite(inner, (box[0] + (ow - inner.width) // 2, box[1] + (oh - inner.height) // 2))
        out.alpha_composite(frame)
        if out.width > 420:
            out = out.resize((420, round(out.height * 420 / out.width)), Image.LANCZOS)
        return out
    pad = 7
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    glow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((3, 3, out.width - 4, out.height - 4), radius=6, outline=col + (220,), width=3)
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
    out.alpha_composite(img, (pad, pad))
    ImageDraw.Draw(out).rounded_rectangle((2, 2, out.width - 3, out.height - 3), radius=6, outline=col + (255,), width=2)
    return out


def clean_banner(path):
    """(banner without its emblem, the emblem's box (x0, y0, x1, y1)): a Reach commendation banner whose emblem (the
    not-blue pixels of its blue end) is painted over with its blue."""
    import numpy as np
    from PIL import Image, ImageFilter
    with Image.open(path) as im:
        img = im.convert("RGBA")
    a = np.asarray(img).astype(np.float32)
    rgb = a[:, :140, :3]
    blue = rgb[..., 2] - (rgb[..., 0] + rgb[..., 1]) / 2
    near = np.linalg.norm(rgb - np.array(BANNER_BLUE, np.float32), axis=2)
    mask = (blue < 30) & (near > 30)
    ys, xs = np.nonzero(mask[6:-6, 6:134])
    if not len(xs):
        return img, (20, 6, 120, 84)
    box = (int(xs.min()) + 6, int(ys.min()) + 6, int(xs.max()) + 7, int(ys.max()) + 7)
    grown = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    region = np.zeros(a.shape[:2], bool)
    region[box[1] - 3:box[3] + 3, max(0, box[0] - 3):box[2] + 3] = True
    paint = np.zeros(a.shape[:2], bool)
    paint[:, :140] = grown
    paint &= region
    a[paint, :3] = BANNER_BLUE
    return Image.fromarray(a.astype(np.uint8), "RGBA"), box


def commendation_source(how):
    """Where a commendation's count comes from, as its card says: "kills" (the kill record, from 15 November 2026),
    "report" (MCC's post-game reports) or "matches" (every counted match)."""
    if "weapons" in how or "vehicles" in how or "feed" in how:
        return "kills"
    if how.get("deed") in ("positive", "loyal"):
        return "matches"
    return "matches" if how.get("stat") in ("assists", "wins") else "report"


def load_badges(path=os.path.join(SITE, "commendations.json")):
    """The one-time badges of the commendations table (no tiers, no credits)."""
    return [b for b in load_json(path, {}).get("badges", []) if isinstance(b, dict) and b.get("key")]


def badge_counts(g, badges):
    """{badge key: progress} for one player's Reach record: Map Master, how many of its maps the player has won a game
    on (unlocked at all of them). Hometown Hero is worked out by the page, from the state leaderboards."""
    out = {}
    for b in badges:
        if b.get("maps"):
            won = {m for m, s in g.get("maps", {}).items() if s.get("wins")}
            out[b["key"]] = sorted(m for m in b["maps"] if m in won)
    return out


def commendation_tier(n, need):
    """How many of the tiers a count reaches (0: not Iron yet, len(need): Max)."""
    return sum(1 for x in need if n is not None and n >= x)


def commendation_credits(counts, comms):
    """The credits a player's commendation tiers award: each tier reached, its cr."""
    by = {c["key"]: c for c in comms}
    return sum(sum(by[k]["cr"][:commendation_tier(n, by[k]["need"])]) for k, n in counts.items() if k in by)


def commendation_progress(counts, comms):
    """(Nov 17) a player's Overall Commendation Progress, percent: each commendation's count against its last tier
    (at most whole), summed over the table; one not countable yet adds 0. The site's Commendations page and the game's
    player card both show this one number."""
    if not comms:
        return 0.0
    whole = sum(min(1.0, counts[c["key"]] / c["need"][-1]) for c in comms
                if counts.get(c["key"]) is not None and c["need"][-1] > 0)
    return round(100.0 * whole / len(comms), 1)


def credits(s, worth):
    """A stats bucket's credits: only what the matches recorded."""
    return (s["games"] * worth["game"] + s["wins"] * worth["win"] + s["kills"] * worth["kill"] +
            s["assists"] * worth["assist"] + s["medals"] * worth["medal"])


def rank_index(cr, steps):
    """The highest step these credits reach."""
    i = 0
    while i + 1 < len(steps) and cr >= steps[i + 1][3]:
        i += 1
    return i


# ---------------------------------------------------------------- home states (the state leaderboards)

def load_states(path=os.path.join(SITE, "states.json")):
    """(regions [[key, name], ...], states [[code, name, region, weight], ...]) from the site's table."""
    table = load_json(path, {})
    regions = [list(r) for r in table.get("regions", [])]
    states = [list(s) for s in table.get("states", [])]
    keys = {r[0] for r in regions}
    if not states or any(s[2] not in keys or not isinstance(s[3], int) or s[3] <= 0 for s in states):
        raise ValueError("states.json: every state needs a listed region and a weight above 0")
    return regions, states


def home_state(name, states):
    """A bot's home state: picked from its name alone (sha256), weighted by population, so it never moves and a new
    bot gets one the first time it is listed. Procedural, not where anyone lives."""
    total = sum(s[3] for s in states)
    at = int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "big") % total
    for s in states:
        if at < s[3]:
            return s[0]
        at -= s[3]
    return states[-1][0]


def load_home_states(paths, states):
    """(Nov 18, the owner) the home states set by hand in edit mode (native/bin/service_record/home_states.json):
    {name: state code}, only codes the table lists. Everyone else keeps the state its name picks (home_state)."""
    raw = load_json(os.path.join(paths.store, "home_states.json"), {})
    codes = {s[0] for s in states}
    return {n: c for n, c in raw.items() if isinstance(n, str) and c in codes} if isinstance(raw, dict) else {}


def save_home_state(paths, name, code):
    """A bot's or player's home state set by hand ("" goes back to the one its name picks). Returns its state now."""
    _, states = load_states()
    if not isinstance(name, str) or not name or len(name) > 64:
        raise ValueError("not a name on the site")
    if not isinstance(code, str) or (code and code not in {s[0] for s in states}):
        raise ValueError("not a state")
    picks = load_home_states(paths, states)
    if code:
        picks[name] = code
    else:
        picks.pop(name, None)
    save_json(os.path.join(paths.store, "home_states.json"), picks)
    return picks.get(name) or home_state(name, states)


# ---------------------------------------------------------------- the numbers

SUMS = ("games", "wins", "kills", "deaths", "assists", "seconds",            # the ledger: every counted match
        "detailed", "alive", "betrayals", "suicides", "medals", "kw", "kg", "km", "ko", "score")   # its report


def blank():
    return dict.fromkeys(SUMS, 0) | {"spree": 0}


def playtime(seconds):
    """13d 3h 36m"""
    m = int(seconds) // 60
    return f"{m // 1440}d {m % 1440 // 60}h {m % 60}m"


def rates(s):
    """What the pages print beside a bucket's sums: 2 places; None where there is nothing to divide by (a player with
    no deaths has a K/D of their kills, as bot_career's leaderboard)."""
    def per(a, b):
        return round(a / b, 2) if b else None
    hours = s["seconds"] / 3600
    return {"kd": round(career.kd(s), 2), "kpg": per(s["kills"], s["games"]), "dpg": per(s["deaths"], s["games"]),
            "apg": per(s["assists"], s["games"]), "kph": per(s["kills"], hours), "dph": per(s["deaths"], hours),
            "mpg": per(s["medals"], s["detailed"]), "mph": per(s["medals"], hours) if s["detailed"] else None,
            "win": per(100 * s["wins"], s["games"]), "playtime": playtime(s["seconds"])}


def match_time(detail, ledger_match):
    """(seconds since 1970, "2026-11-15 18:43"): the match's start from its trace's name, else when its report was
    first seen."""
    t = None
    if detail and detail.get("start"):
        try:
            t = time.mktime(time.strptime(detail["start"], "%Y%m%d-%H%M%S"))
        except (ValueError, OverflowError):
            t = None
    if t is None:
        t = float(ledger_match.get("time", 0))
    return t, time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def load_people(paths):
    """The people the owner lists (native/bin/service_record/people.json: a list of gamertags, this PC only): {name}."""
    data = load_json(os.path.join(paths.store, "people.json"), [])
    return {n.strip() for n in data if isinstance(n, str) and n.strip()} if isinstance(data, list) else set()


def load_matchmaking(path):
    """(Nov 17, the owner: "Matchmaking only") {GameUniqueId} of the matches Proving Grounds started: its list
    (native/bin/service_record/matchmaking.txt, native/proving_grounds.cpp), one a line, the id first, # lines notes.
    No file yet: none. path None: None, every match counts."""
    if path is None:
        return None
    out = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                gid = line.split("\t", 1)[0].strip()
                if gid and not gid.startswith("#"):
                    out.add(gid)
    except OSError:
        pass
    return out


def load_matchmaking_playlists(path):
    """{GameUniqueId: playlist title} from matchmaking.txt's third column ("ARENA", "BIG TEAM BATTLE")."""
    out = {}
    if not path:
        return out
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.rstrip("\r\n").split("\t")
                if len(parts) >= 3 and parts[0] and not parts[0].startswith("#"):
                    out[parts[0]] = parts[2]
    except OSError:
        pass
    return out


def today_block(matches, worth, playlists, now):
    """(Nov 17, the owner's site extras with the bot simulation: "Daily Top 5, Playlist activity") today's five best
    games by the credits each earned (ranks.json's worth: the game, the win, kills, assists, medals), yours included,
    and how busy the playlists were: today's games by playlist, who played most, the last seven days. matches: collect's,
    newest first; playlists: load_matchmaking_playlists."""
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    week = [time.strftime("%Y-%m-%d", time.localtime(now - 86400 * i)) for i in range(6, -1, -1)]
    per_day = dict.fromkeys(week, 0)
    games, by_pl, busy = [], {}, {}
    for m in matches:
        d = (m.get("when") or "")[:10]
        if d in per_day:
            per_day[d] += 1
        if d != day or m.get("game") != DEFAULT_GAME:
            continue
        pl = playlists.get(m["id"], "")
        by_pl[pl] = by_pl.get(pl, 0) + 1
        for r in m["rows"]:
            if not r.get("listed"):
                continue
            busy[r["n"]] = busy.get(r["n"], 0) + 1
            md = int(r.get("md", 0))
            cr = worth["game"] + worth["win"] * int(r["won"]) + worth["kill"] * r["k"] + worth["assist"] * r["a"] \
                + worth["medal"] * md
            games.append({"n": r["n"], "id": m["id"], "map": m["map"], "type": m.get("type", ""), "k": r["k"],
                          "d": r["d"], "a": r["a"], "md": md, "won": bool(r["won"]), "cr": cr, "pl": pl})
    games.sort(key=lambda g: (-g["cr"], -g["k"], g["d"], g["n"].lower()))
    return {"day": day, "top": games[:5], "games": sum(by_pl.values()),
            "playlists": sorted(([k or "Other", v] for k, v in by_pl.items()), key=lambda x: -x[1]),
            "players": len(busy), "busiest": sorted(busy.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:5],
            "week": [[d, per_day[d]] for d in week]}


def person_names(ledger, people):
    """The ledger's names of people (a row not a bot's, in any match, counted or not) that `people` names."""
    return {p["name"] for m in ledger.values() for p in m.get("players", [])
            if p.get("name") and not p.get("bot") and html.unescape(p["name"]) in people}


def collect(ledger, store_matches, roster, kills=None, paths=None, people=(), bots=(), matchmaking=None):
    """(players {name: record}, matches [newest first]) for the site: every counted row of a listed name summed by
    game and family. Listed: the roster, every bot of `bots` (the matchmaking pool, read_pool_names: at 0 until it
    plays, Nov 17 the owner: every pool bot), every name bot_career's totals call a bot, and the people named in
    `people` (load_people) that the ledger has as people. kills: the store's kill rows
    by recording ({"<map>_<start>": [rows]}); a match with none adds nothing to weapons, versus and heat, and
    kill_games says how many of a player's matches had them. matchmaking: the ids of the only matches shown
    (load_matchmaking: Proving Grounds' own), None every match."""
    every = ledger
    if matchmaking is not None:                             # (Nov 17, "Matchmaking only": a custom game adds nobody)
        ledger = {gid: m for gid, m in ledger.items() if gid in matchmaking}
    totals = career.totals(ledger)
    listed = set(roster) | {n for n, t in totals.items() if t["bot"]}
    listed |= person_names(every, people)                   # (at 0 too, after --reset-all)
    listed |= set(bots) - person_names(every, set(bots))    # (the pool's bots, at 0 too; never a person's name)
    players = {n: {"name": n, "g": {}, "chal": []} for n in listed}   # (chal: challenge_row, each Reach match)
    matches = []
    for gid, m in ledger.items():
        rows = m.get("players", [])
        if not (career.counts(rows) or m.get("sim")):       # (a simulated match has no person: it counts anyway)
            continue
        reset = bool(m.get("bots_reset"))
        if m.get("all_reset"):
            continue                                        # (bot_career --reset-all, Nov 17: nobody's counts)
        counting = [p for p in rows if p["name"] and not (p["bot"] and reset)]
        if not any(p["name"] in listed for p in counting):
            continue                                        # (nobody listed has this match: not on the site)
        detail = store_matches.get(gid)
        by_name = {p["name"]: p for p in detail["players"]} if detail else {}
        game = (detail or {}).get("game") or file_parts(m.get("file", ""))[0] or "other"
        if game not in GAME_NAMES:
            game = "other"
        map_id = (detail or {}).get("map") or file_parts(m.get("file", ""))[1]
        t, when = match_time(detail, m)
        draw = all(p["standing"] == 0 for p in rows)
        out_rows = []
        for p in rows:
            d = by_name.get(p["name"])
            row = {"n": html.unescape(p["name"]), "bot": p["bot"], "listed": p["name"] in listed and p in counting,
                   "team": p["team"], "st": p["standing"], "k": p["kills"], "d": p["deaths"], "a": p["assists"],
                   "sec": p["seconds"], "won": p["standing"] == 0 and not draw}
            if d:
                row.update(score=d["score"], bt=d["betrayals"], su=d["suicides"], md=d["medal_total"],
                           spree=d["spree"], clan=html.unescape(d["clan"]),
                           medals={str(i): n for i, n in d["medals"].items()})   # (this match's, by MCC's number)
            out_rows.append(row)
        out_rows.sort(key=lambda r: (r["st"], -r.get("score", 0), -r["k"]))
        match = {"id": gid, "t": t, "when": when, "game": game, "map": map_id,
                 "type": (detail or {}).get("type", ""), "cat": family((detail or {}).get("type", "")),
                 "teams": bool(detail and detail["teams"]), "report": bool(detail), "rows": out_rows}
        matches.append(match)
        entry = (kills or {}).get(f"{map_id}_{detail['start']}") if detail and map_id and detail.get("start") else None
        tally = kill_tally(detail, kill_rows(entry)) if entry is not None else None
        match["kills"] = tally is not None
        # (Nov 17, the owner's MVP, Game Changer, Positive Thinking, Loyal Soldier) this match's top score: MCC's own
        # Score, an objective game's objective points
        top = max((x["score"] for x in detail["players"]), default=0) if detail else 0
        feats = {}                                          # (name -> {"first", "closer", "grudge"} in this match)
        if entry is not None:
            match["feed"] = kill_feed(detail, kill_rows(entry), game)
            feats = feed_feats(match["feed"], {html.unescape(p["name"]) for p in rows if p["standing"] == 0 and not draw})
        # its heatmap: the map itself, or the Forge layout it was played on ("<map>@<layout id>", export_map)
        heat_key = map_id
        if tally:
            spots_all = [c for t in tally.values() for c in t["k"] + t["d"]]
            variant = (detail or {}).get("layout") or (   # (a simulated match names its layout: bot_sim.py)
                match_variant(map_id, (detail or {}).get("start"), spots_all, paths) if paths else None)
            if variant:
                heat_key = f"{map_id}@{variant}"
        match["heat"] = heat_key
        for p in counting:
            if p["name"] not in listed:
                continue
            d = by_name.get(p["name"])
            won = p["standing"] == 0 and not draw
            if game == DEFAULT_GAME:                        # (Nov 17: this Reach match's numbers for the challenges)
                players[p["name"]]["chal"].append(challenge_row(p, d, t, match["cat"], map_id, won, detail, tally))
            for gkey in ("all", game):
                g = players[p["name"]]["g"].setdefault(gkey, {"cats": {}, "types": {}, "maps": {}, "medals": {},
                                                               "killed": {}, "killed_by": {}, "results": [],
                                                               "weapons": {}, "versus": {}, "heat": {}, "kill_games": 0,
                                                               "feats": {"first": 0, "closer": 0, "grudge": 0},
                                                               "deeds": dict.fromkeys(DEEDS, 0)})
                g["results"].append((t, gid, won))
                for k, n in match_deeds(p, d, match["cat"], top).items():
                    g["deeds"][k] += n
                g["deeds"]["stockpile"] = g["deeds"].get("stockpile", 0) + stockpile_flags(d, match["cat"])
                if tally is not None:                       # (this match has its kill rows)
                    g["kill_games"] += 1
                    for k, n in feats.get(html.unescape(p["name"]), {}).items():
                        g["feats"][k] += n
                    mine = tally.get(p["name"])
                    if mine:
                        for key, n in mine["weapons"].items():      # a damage type is a number of its own game's
                            e = g["weapons"].setdefault(f"{game}:{key}", [0, 0])
                            e[0], e[1] = e[0] + n[0], e[1] + n[1]
                        for name, n in mine["versus"].items():
                            e = g["versus"].setdefault(html.unescape(name), [0, 0])
                            e[0], e[1] = e[0] + n[0], e[1] + n[1]
                        spots = g["heat"].setdefault(heat_key, {"k": [], "d": []})
                        spots["k"] += mine["k"]
                        spots["d"] += mine["d"]
                buckets = [g["cats"].setdefault("all", blank()), g["cats"].setdefault(match["cat"], blank()),
                           g["types"].setdefault(match["type"] or "Unknown", blank()),
                           g["maps"].setdefault(map_id or "unknown", blank())]
                for s in buckets:
                    s["games"] += 1
                    s["wins"] += int(won)
                    for k in ("kills", "deaths", "assists", "seconds"):
                        s[k] += p[k]
                    if d:
                        s["detailed"] += 1
                        s["medals"] += d["medal_total"]
                        for k in ("alive", "betrayals", "suicides", "kw", "kg", "km", "ko", "score"):
                            s[k] += d[k]
                        s["spree"] = max(s["spree"], d["spree"])
                if d:
                    for i, n in d["medals"].items():
                        g["medals"][str(i)] = g["medals"].get(str(i), 0) + n
                    for key in ("killed", "killed_by"):
                        rival = d["killed_most" if key == "killed" else "killed_by"]
                        if rival and rival[0]:
                            e = g[key].setdefault(html.unescape(rival[0]), [0, 0])
                            e[0] += 1
                            e[1] += rival[1]
    matches.sort(key=lambda x: x["t"], reverse=True)
    index = {x["id"]: i for i, x in enumerate(matches)}
    for rec in players.values():
        for g in rec["g"].values():
            results = sorted(g.pop("results"))
            g["matches"] = [index[gid] for _, gid, _ in reversed(results)]
            streaks, run = [], 0
            for _, _, won in results:                       # (each run of wins, oldest first)
                if won:
                    run += 1
                elif run:
                    streaks.append(run)
                    run = 0
            g["streak"] = {"best": max(streaks + [run]), "current": run, "runs": (streaks + ([run] if run else []))[-20:]}
            g["first"], g["last"] = results[0][0], results[-1][0]
            for group in ("cats", "types", "maps"):
                for s in g[group].values():
                    s["r"] = rates(s)
    return players, matches


# ---------------------------------------------------------------- challenges (Nov 17)
# The owner: "Add these to the achievements page, But rename it to challenges. And we will make a plethora of daily and
# weekly challenges"; their cR counts toward the rank (ranks.json challenge_credits), 4 dailies and 1 weekly at a time.
# service_record_site/challenges.json is the list. A day is local midnight to midnight, a week Monday to Monday; which
# challenges a day or week has is decided by its date alone (challenge_pick), so every past day's can be worked out
# again from the record and the credits are a pure function of the counted matches.
CHALLENGE_STATS = {"medals": "medals_n"}                     # (a stat named apart from the row's medal counts)


def load_challenges(path=os.path.join(SITE, "challenges.json")):
    """The table: {"daily": [...], "weekly": [...], "daily_count", "weekly_count"} (challenges.json)."""
    data = load_json(path, {})
    return {"daily": data.get("daily", []), "weekly": data.get("weekly", []),
            "daily_count": int(data.get("daily_count", 4)), "weekly_count": int(data.get("weekly_count", 1))}


def challenge_row(p, d, t, cat, map_id, won, detail, tally):
    """What one counted Reach match of a player gives the challenges: p its ledger row, d its report row (None: no
    report kept), tally the match's kill record by name (None: not recorded)."""
    top = max((x["score"] for x in detail["players"]), default=0) if detail else 0
    mine = (tally or {}).get(p["name"])
    return {"t": t, "cat": cat, "map": map_id or "", "games": 1, "wins": int(won), "kills": p["kills"],
            "deaths": p["deaths"], "assists": p["assists"], "plus": p["kills"] - p["deaths"],
            "medals_n": d["medal_total"] if d else 0, "kg": d["kg"] if d else 0, "km": d["km"] if d else 0,
            "score": d["score"] if d else 0, "spree": d["spree"] if d else 0,
            "top": int(bool(d) and top > 0 and d["score"] == top),
            "medal": {str(i): n for i, n in d["medals"].items()} if d else {},
            "weapons": {f"{DEFAULT_GAME}:{k}": n[0] for k, n in mine["weapons"].items()} if mine else {}}


def challenge_value(c, row, ids, groups, vehicles):
    """What one match row adds to challenge c (challenges.json count)."""
    how = c["count"]
    if (how.get("cat") and row["cat"] not in how["cat"]) or (how.get("map") and row["map"] not in how["map"]):
        return 0
    if "stat" in how:
        n = row.get(CHALLENGE_STATS.get(how["stat"], how["stat"]), 0)
    elif "medals" in how:
        n = sum(row["medal"].get(ids[k], 0) for k in how["medals"] if k in ids)
    elif "group" in how:
        n = sum(v for i, v in row["medal"].items() if groups.get(i) == how["group"])
    elif "weapons" in how:
        keys = {f"{DEFAULT_GAME}:{w}" for w in how["weapons"]}
        n = sum(v for k, v in row["weapons"].items() if k in keys)
    elif how.get("vehicles"):
        n = sum(v for k, v in row["weapons"].items() if k in vehicles)
    else:
        n = 0
    return int(n >= how["at_least"]) if "at_least" in how else int(n)


def challenge_starts(t):
    """(the day, the week) a moment falls in, as their first dates: "2026-11-17", "2026-11-16" (local time)."""
    day = datetime.date.fromtimestamp(t)
    return day.isoformat(), (day - datetime.timedelta(days=day.weekday())).isoformat()


def challenge_pick(period, start, pool, n):
    """The keys of the challenges a day or week has ("daily"/"weekly", its first date): drawn from its list by the date
    alone, the same for everyone and every build."""
    seed = int(hashlib.sha256(f"{period}:{start}".encode("utf-8")).hexdigest(), 16)
    return random.Random(seed).sample([c["key"] for c in pool], min(n, len(pool)))


def challenge_progress(rows, table, medal_info, now):
    """One player's challenges: {"cr": credits of every one finished, "daily_done", "weekly_done": how many,
    "now": {key: progress} for today's and this week's}."""
    ids = {info.get("key"): str(i) for i, info in medal_info.items() if isinstance(info, dict)}
    groups = {str(i): medal_group(info) for i, info in medal_info.items() if isinstance(info, dict)}
    vehicles = set(vehicle_keys())
    windows = {}
    for r in rows:
        day, week = challenge_starts(r["t"])
        windows.setdefault(("daily", day), []).append(r)
        windows.setdefault(("weekly", week), []).append(r)
    today, this_week = challenge_starts(now)
    out = {"cr": 0, "daily_done": 0, "weekly_done": 0, "now": {}}
    for (period, start), rs in windows.items():
        pool = table[period]
        by_key = {c["key"]: c for c in pool}
        for key in challenge_pick(period, start, pool, table[period + "_count"]):
            c = by_key[key]
            n = sum(challenge_value(c, r, ids, groups, vehicles) for r in rs)
            if n >= c["need"]:
                out["cr"] += int(c["cr"])
                out[period + "_done"] += 1
            if start == (today if period == "daily" else this_week):
                out["now"][key] = n
    return out


def challenge_table(table, now, credits_on):
    """The page's side: every challenge, and today's and this week's with when they end (seconds since 1970)."""
    today, this_week = challenge_starts(now)
    ends = lambda start, days: datetime.datetime.combine(datetime.date.fromisoformat(start) + datetime.timedelta(days=days),
                                                         datetime.time.min).timestamp()
    return {"credits": credits_on,
            "daily": {"start": today, "ends": ends(today, 1), "keys": challenge_pick("daily", today, table["daily"], table["daily_count"])},
            "weekly": {"start": this_week, "ends": ends(this_week, 7),
                       "keys": challenge_pick("weekly", this_week, table["weekly"], table["weekly_count"])},
            "list": [{k: c[k] for k in ("key", "name", "what", "need", "cr", "icon")} | {"period": period}
                     for period in ("daily", "weekly") for c in table[period]]}


# ---------------------------------------------------------------- clan rewards (Nov 18)
# The owner: make people and bots want to join a big clan (a clan's cR stays its members' added up), "add everything",
# each one changeable in edit mode to test. service_record_site/clan_rewards.json: the rewards with the clan ranks that
# unlock them, and the clan weekly challenges; the owner's changes in native/bin/service_record/clan_settings.json
# (rewards on or off and their unlocks, a week's challenge picked by hand, each clan's emblem). Everything else is
# worked out from the counted Reach matches at each build, so a reset takes it away too.
CLAN_SCALE = 10                         # (app.js CLAN_SCALE: a clan's ladder is the players' with every step x10)
CLAN_GAMES = (100, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000)   # (the history's games played milestones)


def load_clan_table(path=os.path.join(SITE, "clan_rewards.json")):
    """{"rewards": [...], "challenges": [...]} (clan_rewards.json)."""
    data = load_json(path, {})
    return {"rewards": list(data.get("rewards", [])), "challenges": list(data.get("challenges", []))}


def load_clan_settings(paths):
    """The owner's changes (clan_settings.json): {"rewards": {key: {"on", "at"}}, "weeks": {week: challenge key},
    "emblems": {clan key: member name}}, each part a dict."""
    raw = load_json(os.path.join(paths.store, "clan_settings.json"), {})
    raw = raw if isinstance(raw, dict) else {}
    return {k: raw[k] if isinstance(raw.get(k), dict) else {} for k in ("rewards", "weeks", "emblems")}


def rank_names(steps):
    """The ladder's rank names, lowest first (load_ranks steps)."""
    return [s[1] for s in steps if s[2] == 0]


def clan_rewards(table, settings, steps):
    """Every reward with the owner's change laid over it: "on" a bool, "at" (the ranks unlocking each level) the same
    number of rank names, none lower than the one before. A change that is not that is left out."""
    names = rank_names(steps)
    out = []
    for r in table["rewards"]:
        r = {k: r[k] for k in ("key", "group", "name", "what", "on", "at", "levels") if k in r}
        mine = settings["rewards"].get(r["key"])
        if isinstance(mine, dict):
            if isinstance(mine.get("on"), bool):
                r["on"] = mine["on"]
            at = mine.get("at")
            if "at" in r and isinstance(at, list) and len(at) == len(r["at"]) and all(a in names for a in at) \
                    and all(names.index(a) <= names.index(b) for a, b in zip(at, at[1:])):
                r["at"] = list(at)
        out.append(r)
    return out


def save_clan_rewards(paths, changes, steps=None):
    """The edit mode's reward settings ({key: {"on", "at"}}; {} puts every reward back as clan_rewards.json has it).
    Returns the rewards as they now are. ValueError for anything that is not a reward or a good change."""
    steps = steps or load_ranks()[1]
    table = load_clan_table()
    known = {r["key"]: r for r in table["rewards"]}
    if not isinstance(changes, dict) or any(k not in known or not isinstance(v, dict) for k, v in changes.items()):
        raise ValueError("not a reward")
    settings = load_clan_settings(paths)
    kept = {}
    for key, v in changes.items():
        change = {}
        if isinstance(v.get("on"), bool):
            change["on"] = v["on"]
        if "at" in v:
            change["at"] = v["at"]
        got = clan_rewards({"rewards": [known[key]]}, {"rewards": {key: change}}, steps)[0]
        if "at" in change and got.get("at") != change["at"]:
            raise ValueError(f"{known[key]['name']}: each unlock a rank, none lower than the one before")
        kept[key] = change
    settings["rewards"] = kept
    save_json(os.path.join(paths.store, "clan_settings.json"), settings)
    return clan_rewards(table, settings, steps)


def save_clan_week(paths, key, now=None):
    """This week's clan challenge picked by hand ("" goes back to the one its date draws). Returns this week's key."""
    table = load_clan_table()
    if key and key not in {c["key"] for c in table["challenges"]}:
        raise ValueError("not a clan challenge")
    week = challenge_starts(time.time() if now is None else now)[1]
    settings = load_clan_settings(paths)
    if key:
        settings["weeks"][week] = key
    else:
        settings["weeks"].pop(week, None)
    save_json(os.path.join(paths.store, "clan_settings.json"), settings)
    return clan_week_pick(table["challenges"], settings, week)


def save_clan_emblem(paths, clan, name):
    """A clan's emblem: one of its members' (the editor checks the member), "" its top member's again."""
    key = clan_key(clan)
    if not CLAN_KEY.fullmatch(key) or not isinstance(name, str) or len(name) > 32:
        raise ValueError("not a clan member")
    settings = load_clan_settings(paths)
    if name:
        settings["emblems"][key] = name
    else:
        settings["emblems"].pop(key, None)
    save_json(os.path.join(paths.store, "clan_settings.json"), settings)
    return name


def clan_week_pick(pool, settings, week):
    """A week's clan challenge: the owner's pick for it, else one drawn by its date (challenge_pick)."""
    mine = settings["weeks"].get(week)
    if mine in {c["key"] for c in pool}:
        return mine
    return (challenge_pick("clan", week, pool, 1) or [None])[0]


def match_credits(r, worth):
    """One match row's credits (challenge_row's numbers; ranks.json worth): the game, the win, kills, assists, medals."""
    return (worth["game"] + worth["win"] * r["wins"] + worth["kill"] * r["kills"] + worth["assist"] * r["assists"]
            + worth["medal"] * r["medals_n"])


def clan_block(out_players, rows_by_name, table, settings, rewards, medal_info, worth, steps, now):
    """({clan key: {"bonus", "done", "now", "mvp", "history", "emblem"}}, the week's clan challenge for the page).
    out_players: site_data's (name, clan, cr, emblem); rows_by_name: each player's challenge_row rows.
    bonus: the cR of every week's clan challenge the clan finished (the owner's "challenge" reward on), added to its cR;
    mvp: [the member with the most credits from this week's matches, those credits]; history: [[t, kind, value]] newest
    first: "first" (its first match), "rank" (a rank reached), "games" (a games played milestone), "top" (the week it
    earned the most credits of every clan). A rank's date: the clan's cR as it grew match by match, the commendations'
    and members' challenges' share spread over the matches alike, so its last step is the rank it has now."""
    on = {r["key"]: r.get("on", True) for r in rewards}
    pool = table["challenges"]
    by_key = {c["key"]: c for c in pool}
    ids = {info.get("key"): str(i) for i, info in medal_info.items() if isinstance(info, dict)}
    groups = {str(i): medal_group(info) for i, info in medal_info.items() if isinstance(info, dict)}
    vehicles = set(vehicle_keys())
    this_week = challenge_starts(now)[1]
    week_end = lambda w: datetime.datetime.combine(datetime.date.fromisoformat(w) + datetime.timedelta(days=7),
                                                   datetime.time.min).timestamp()
    named = [(s[1], s[3] * CLAN_SCALE) for s in steps if s[2] == 0][1:]
    members = {}
    for p in out_players:
        if str(p.get("clan") or "").strip():
            members.setdefault(clan_key(p["clan"]), []).append(p)
    out, week_cr = {}, {}
    for key, ms in members.items():
        events, by_week, mvp = [], {}, {}
        for p in ms:
            for r in rows_by_name.get(p["name"], []):
                cr = match_credits(r, worth)
                events.append((r["t"], cr))
                w = challenge_starts(r["t"])[1]
                by_week.setdefault(w, []).append(r)
                week_cr.setdefault(w, {})[key] = week_cr.get(w, {}).get(key, 0) + cr
                if w == this_week:
                    mvp[p["name"]] = mvp.get(p["name"], 0) + cr
        bonus, done, progress, extra = 0, 0, 0, []
        for w, rs in by_week.items():
            c = by_key.get(clan_week_pick(pool, settings, w)) if on.get("challenge") else None
            if not c:
                continue
            n = 0
            for r in sorted(rs, key=lambda x: x["t"]):
                n += challenge_value(c, r, ids, groups, vehicles)
                if n >= c["need"]:
                    bonus += int(c["cr"])
                    done += 1
                    extra.append((r["t"], int(c["cr"])))           # (finished in this match)
                    week_cr[w][key] += int(c["cr"])
                    break
            if w == this_week:
                progress = sum(challenge_value(c, r, ids, groups, vehicles) for r in rs)
        total = sum(p.get("cr") or 0 for p in ms) + bonus
        timeline = sorted(events + extra)
        base = sum(c for _, c in timeline)
        scale = total / base if base else 0
        history = [[timeline[0][0], "first", ""]] if events else []
        run, i = 0.0, 0
        for t, c in timeline:
            run += c * scale
            while i < len(named) and run >= named[i][1] - 0.5:
                history.append([t, "rank", named[i][0]])
                i += 1
        for n, (t, _) in enumerate(sorted(events), 1):
            if n in CLAN_GAMES:
                history.append([t, "games", n])
        best = max(mvp.items(), key=lambda kv: (kv[1], kv[0].lower()), default=None)
        names = {p["name"] for p in ms if p.get("emblem")}
        pick = settings["emblems"].get(key)
        out[key] = {"bonus": bonus, "done": done, "now": progress, "mvp": list(best) if best and best[1] > 0 else None,
                    "history": history, "emblem": pick if pick in names else None}
    for w, by in week_cr.items():                           # (each week gone by: the clan that earned the most)
        if w >= this_week or not by:
            continue
        key, cr = sorted(by.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if cr > 0:
            out[key]["history"].append([week_end(w) - 1, "top", w])
    for c in out.values():
        c["history"] = [e for _, e in sorted(enumerate(c["history"]), key=lambda ie: (ie[1][0], ie[1][1] != "first", ie[0]),
                                                reverse=True)][:60]      # (newest first; a match's ranks highest first)
    pick = clan_week_pick(pool, settings, this_week) if pool else None
    week = {"start": this_week, "ends": week_end(this_week), "key": pick, "picked": settings["weeks"].get(this_week) == pick and pick is not None,
            "list": [{k: c[k] for k in ("key", "name", "what", "need", "cr", "icon")} for c in pool]}
    return out, week


def site_data(ledger, store_matches, paths, now=None, kills=None):
    """Everything the pages show, as one dict (data.js)."""
    worth, steps = load_ranks()
    regions, states = load_states()
    homes = load_home_states(paths, states)                 # (Nov 18: the states set by hand in edit mode)
    roster = read_profiles(paths.profiles)
    pool = {pool_name(k).lower(): v for k, v in read_pool(paths.pool).items()}   # (as the panel matches: no case)
    lobby_level, lobby_tiers = read_lobby(paths.botcore)
    people = load_people(paths)
    players, matches = collect(ledger, store_matches, roster, kills, paths, people, read_pool_names(paths.bot_pool),
                               load_matchmaking(paths.matchmaking))
    persons = person_names(ledger, people)
    make_emblems([html.unescape(n) for n in players if n not in persons], paths)   # (Nov 18: every bot its emblem)
    looks_file = all_looks(paths, [html.unescape(n) for n in players])   # (pool bots' looks worked out too)
    looks = read_looks(looks_file, read_look_names(paths.look_names))
    clans = {}
    for m in reversed(matches):                             # (a pool bot's clan tag: its newest report's)
        for r in m["rows"]:
            if r.get("clan"):
                clans[r["n"]] = r["clan"]
    medal_names = load_json(os.path.join(paths.store, "art", "medals.json"), {})
    figures = bot_figures(paths, looks_file)
    tiers, comms = load_commendations()
    badges = load_badges()
    with_comms = bool(load_json(os.path.join(SITE, "ranks.json"), {}).get("commendation_credits"))
    challenges = load_challenges()                          # (Nov 17: the dailies and weeklies, their cR in the rank)
    with_chal = bool(load_json(os.path.join(SITE, "ranks.json"), {}).get("challenge_credits"))
    when = time.time() if now is None else now
    used = set()
    out_players = []
    for name in sorted(players, key=str.lower):
        rec = players[name]
        reach = rec["g"].get(DEFAULT_GAME, {}).get("cats", {}).get("all") or blank()
        counts = commendation_counts(rec["g"][DEFAULT_GAME], comms, medal_names) if DEFAULT_GAME in rec["g"] else {}
        comm_cr = commendation_credits(counts, comms) if with_comms else 0
        cr = credits(reach, worth) + comm_cr                # (the rank: its matches, and its commendations' tiers)
        chal = challenge_progress(rec["chal"], challenges, medal_names, when)
        cr += chal["cr"] if with_chal else 0                # (and its finished challenges, Nov 17)
        for g in rec["g"].values():
            used.update(g["medals"])
        key = pool_name(html.unescape(name)).lower()
        diff, style = pool.get(key, ("", ""))
        out_players.append({
            "lobby_tier": "" if diff else lobby_tiers.get(key, ""),   # (Nov 18: no saved one: its seat in the lobby list)
            "name": html.unescape(name), "roster": name in roster, "person": name in persons,   # (a person: people.json)
            "clan": roster[name] if name in roster else clans.get(html.unescape(name), ""),   # (its profile's, "" too)
            "difficulty": diff, "style": style, "emblem": export_emblem(name, paths),
            "looks": looks.get(name), "cr": cr, "rank": rank_index(cr, steps), "comm": counts, "comm_cr": comm_cr,
            "chal": chal,                                   # (Nov 17: cr, daily_done, weekly_done, now {key: n})
            "comm_pct": commendation_progress(counts, comms),
            "badges": badge_counts(rec["g"][DEFAULT_GAME], badges) if DEFAULT_GAME in rec["g"] else {},
            "state": homes.get(html.unescape(name)) or home_state(html.unescape(name), states),
            "state_set": html.unescape(name) in homes, "figure": figures.get(name), "g": rec["g"],
        })
    clan_table, clan_settings = load_clan_table(), load_clan_settings(paths)   # (Nov 18: the clan rewards)
    rewards = clan_rewards(clan_table, clan_settings, steps)
    clans_out, clan_week = clan_block(out_players, {html.unescape(n): r["chal"] for n, r in players.items()}, clan_table,
                                      clan_settings, rewards, medal_names, worth, steps, when)
    medals = {}
    for i in sorted(used, key=int):
        info = medal_names.get(i) or {}
        icon = None
        if info.get("icon"):
            src = os.path.join(paths.store, "art", "medals", info["icon"])
            if os.path.exists(src):
                dst = os.path.join(paths.out, "medals", info["icon"])
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                    shutil.copyfile(src, dst)
                icon = "medals/" + info["icon"]
        medals[i] = {"name": info.get("name") or f"Medal {i}", "icon": icon, "cat": medal_group(info)}
    # what killed, by name: [name, matched live] for every damage type a listed player's rows have; a map's picture
    # for every map they have a spot on
    table, weapons, heat_maps = load_weapons(), {}, {}
    keys = {key for rec in players.values() for g in rec["g"].values() for key in g["weapons"]}
    keys |= {r[3] for m in matches for r in m.get("feed", [])}     # (a carnage report's kill feed names its own)
    arsenal = arsenal_keys()
    keys |= {k for kind in arsenal.values() for k in kind}         # (Nov 17: every weapon and vehicle, used or not)
    for key in keys:
        game_key, _, kind = key.partition(":")
        names, checked = table.get(game_key, ({}, set()))
        weapons[key] = ["Not read" if kind == "?" else names.get(kind) or f"Damage type {kind}",
                        kind == "?" or kind in checked or kind not in names]
    for rec in players.values():
        for g in rec["g"].values():
            for map_id in g["heat"]:
                if map_id not in heat_maps:
                    base, _, variant = map_id.partition("@")          # (a Forge layout: "<map>@<layout id>")
                    heat_maps[map_id] = export_map(base, paths, variant or None)
    games = sorted({m["game"] for m in matches} | {DEFAULT_GAME}, key=list(GAME_NAMES).index)
    cats = sorted({m["cat"] for m in matches}, key=FAMILY_ORDER.index)
    now = time.time() if now is None else now
    ranks, number = [], 0
    for label, _, grade, cr in steps:                       # [label, credits, the rank's number, its Grade]
        number += grade == 0
        ranks.append([label, cr, number, grade])
    return {
        "site": NAME, "built": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)), "stamp": str(int(now)),
        "default_game": DEFAULT_GAME,
        "games": [["all", "All games"]] + [[g, GAME_NAMES[g]] for g in games],
        "cats": [[c, FAMILY_NAMES[c]] for c in cats],
        "ranks": ranks, "credits": worth,
        "commendations": {"tiers": tiers, "credits": with_comms, "list": [
            {k: c[k] for k in ("key", "name", "what", "need", "cr")} | {"from": commendation_source(c["count"]), "set": c.get("set", "mp")}
            for c in comms],
            "badges": [{k: b[k] for k in ("key", "name", "what", "maps") if k in b} for b in badges],
            "tier_art": tier_banners([c["key"] for c in comms], paths),
            # (a badge's own emblem, the owner's, Nov 16: art/badges/<key>.png, never in git)
            "badge_art": {n[:-4]: src for n, src in menu_pictures("badges", {b["key"] + ".png" for b in badges}, paths).items()},
            "art": {name[:-4]: src for name, src in menu_pictures(
                "commendations", {c["key"] + ".png" for c in comms} | {b["key"] + ".png" for b in badges}, paths).items()}},
        "maps": dict(MAP_NAMES) | {m["map"]: map_name(m["map"]) for m in matches if m["map"]}   # (every Reach map: Map Master)
                | {m["heat"]: map_name(m["map"]) + ": " + variant_title(m["map"], m["heat"].split("@")[1], paths)
                   for m in matches if "@" in (m.get("heat") or "")},
        "players": out_players, "matches": matches, "medals": medals,
        "today": today_block(matches, worth, load_matchmaking_playlists(paths.matchmaking), now),   # (Nov 17)
        "medal_art": bool(medal_names),
        "weapons": weapons, "heat_maps": {k: v for k, v in heat_maps.items() if v},
        "weapon_art": weapon_pictures(weapons, paths),
        # the owner's own header and sidebar pictures (Nov 16), kept on this PC only; the site's drawing without them
        "backdrops": menu_pictures("backdrops", {"header.jpg", "sidebar.jpg", "player.jpg"}, paths),   # (player.jpg: the player pages's own, Nov 16)
        # the landing page's background: MCC's Noble main-menu movie as MP4 and its still (service_record_art.py video)
        "video": menu_pictures("video", {"noble.mp4", "noble.png"}, paths),
        # the owner's neon icons (Nov 16), cut from his two sheets into art/icons; the site's own drawn ones without them
        "icons": menu_pictures("icons", {n + ".png" for n in ICON_NAMES}, paths),
        # the game type families' icons (the owner's sheet, cut into art/modes; service_record_site/modes.json says which)
        "mode_art": mode_pictures(paths),
        "figure_art": menu_pictures("figures", {(x.get("body") or "spartan") + ".png" for x in looks.values()} | {"spartan.png"}, paths),
        "map_art": {m: f for m in {x["map"] for x in matches if x["map"]}
                    for f in [menu_pictures("maps", {preview_name(m)}, paths).get(preview_name(m))] if f},
        "vehicles": vehicle_keys(),
        "arsenal": arsenal,
        "regions": regions, "states": {s[0]: [s[1], s[2]] for s in states},
        "lobby_difficulty": lobby_level,                    # (Nov 18: the BOTS panel's "for everyone" difficulty)
        "clan_names": load_clan_names(paths),        # (the owner's full names for the clans, by clan_key)
        "clan_about": load_clan_about(paths),        # (and his short description of each)
        "challenges": challenge_table(challenges, when, with_chal),   # (Nov 17: today's and this week's)
        "clans": clans_out, "clan_week": clan_week, "clan_rewards": rewards,   # (Nov 18: the clan rewards)
    }


ICON_NAMES = ("home", "clock", "share", "bars", "star", "helmet", "rising", "controller",
              "pin", "medal", "rifle", "skull", "folder", "film", "picture", "camera",
              # his second set (Nov 16): the Overview's stat list, Achievements, the kills box
              "s_clock", "s_skull", "s_medal", "s_crosshair", "s_layers", "s_star", "s_hex", "s_calendar", "s_controller",
              # (Nov 16: his DMR drawing for Weapons, his Perfection medal for Medals)
              "s_dmr", "s_perfection")


def preview_name(map_id):
    """A map's preview picture in the art store (tools/service_record_art.py pictures): its name, lower-case, without
    spaces or signs. "Forge World" -> forgeworld.jpg."""
    return re.sub(r"[^a-z0-9]", "", map_name(map_id).lower()) + ".jpg"


def menu_pictures(kind, names, paths):
    """{file: "<kind>/<file>"} for each of `names` the art store has under art/<kind> (MCC's own pictures, made on
    this PC by service_record_art.py pictures, never in git), copied into the site; a missing one is left out and
    the page draws its own."""
    out = {}
    for name in names:
        if not re.fullmatch(r"[a-z0-9_]+\.(png|jpg|webp|mp4)", name):
            continue
        src = os.path.join(paths.store, "art", kind, name)
        dst = os.path.join(paths.out, kind, name)
        try:
            if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
        except OSError:
            continue
        out[name] = kind + "/" + name
    return out


FIGURE_SIZE = ("480", "640", "0.35", "24")   # each drawing's width, height, first turn (radians; the bots panel's own
                                             # 0.35) and its angles round the turntable


CLAN_KEY = re.compile(r"[^\x00-\x1f|]{1,16}")
CLAN_NAME_MAX = 40


def clan_key(tag):
    """A clan's key: its tag, its letters alike whatever their case (app.js clanKey)."""
    return str(tag).strip().lower()


def load_clan_names(paths):
    """{clan key: the full name the owner gave it} (native/bin/service_record/clan_names.json, written by the site's edit
    mode through tools/service_record_edit.py; never in git), bad entries left out."""
    raw = load_json(os.path.join(paths.store, "clan_names.json"), {})
    out = {}
    for k, v in (raw.items() if isinstance(raw, dict) else []):
        name = clean_clan_name(v)
        if isinstance(k, str) and CLAN_KEY.fullmatch(k) and name:
            out[k] = name
    return out


def clean_clan_name(name):
    """A clan name as kept: text, its spaces tidied, no control characters, at most CLAN_NAME_MAX characters; "" for
    anything else (which clears the name)."""
    if not isinstance(name, str):
        return ""
    name = " ".join("".join(ch for ch in name if ch.isprintable()).split())
    return name[:CLAN_NAME_MAX]


def save_clan_name(paths, key, name):
    """Give a clan its full name ("" or blank clears it): the edit mode's one write. Returns the names as kept. Raises
    ValueError for a key that is not a clan tag's."""
    key = clan_key(key)
    if not CLAN_KEY.fullmatch(key):
        raise ValueError("not a clan tag")
    names = load_clan_names(paths)
    name = clean_clan_name(name)
    if name:
        names[key] = name
    else:
        names.pop(key, None)
    save_json(os.path.join(paths.store, "clan_names.json"), names)
    return names


CLAN_ABOUT_MAX = 280


def clean_clan_about(text):
    """A clan description as kept: text, line breaks kept (two at most in a row), no other control characters, its
    spaces tidied, at most CLAN_ABOUT_MAX characters; "" for anything else (which clears it)."""
    if not isinstance(text, str):
        return ""
    lines = [" ".join("".join(ch for ch in ln if ch.isprintable()).split()) for ln in text.replace("\r", "").split("\n")]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return out[:CLAN_ABOUT_MAX].rstrip()


def load_clan_about(paths):
    """{clan key: the owner's short description of it} (native/bin/service_record/clan_about.json, the edit mode's;
    never in git), bad entries left out."""
    raw = load_json(os.path.join(paths.store, "clan_about.json"), {})
    return {k: clean_clan_about(v) for k, v in (raw.items() if isinstance(raw, dict) else [])
            if isinstance(k, str) and CLAN_KEY.fullmatch(k) and clean_clan_about(v)}


def save_clan_about(paths, key, text):
    """Give a clan its description ("" clears it). Returns the descriptions as kept; ValueError for a key that is not
    a clan tag's."""
    key = clan_key(key)
    if not CLAN_KEY.fullmatch(key):
        raise ValueError("not a clan tag")
    about = load_clan_about(paths)
    text = clean_clan_about(text)
    if text:
        about[key] = text
    else:
        about.pop(key, None)
    save_json(os.path.join(paths.store, "clan_about.json"), about)
    return about


BOT_CLAN = re.compile(r"[^\s,;=\[\]|]{1,4}")      # (the bots panel's Clan tag box: 4 at most, no blanks, none of ,;=[]|)
MCC_EXE = "MCC-Win64-Shipping.exe"


def reset_everyone(running=None):
    """The edit mode's Reset all (Nov 17, the owner: "a reset all button so I don't ask you everytime"): bot_career
    --reset-all, everyone's numbers (people's too) from 0, the matches kept and marked. A copy of the ledger as it was is
    kept beside it first (ledger.before_reset_all_<date-time>.json). Refused while MCC runs (tools/play.py runs
    bot_career as a match starts; two writers of the ledger at once could lose the mark). Returns how many matches were
    marked."""
    if (mcc_running() if running is None else running):
        raise PermissionError("close MCC first: the game updates the stats while it runs")
    ledger = os.path.join(career.OUT, "ledger.json")
    if os.path.exists(ledger):
        shutil.copyfile(ledger, os.path.join(career.OUT, time.strftime("ledger.before_reset_all_%Y-%m-%d_%H%M%S.json")))
    if career.main(["--reset-all", "--quiet"]) != 0:
        raise OSError("the reset did not finish")
    return len(load_json(ledger, {}))


def mcc_running():
    """Whether MCC is running on this PC (tasklist). While it runs, botcore holds the bots' profiles in memory and
    writes the whole file back when its panel saves: an edit to bot_profiles.ini then would be lost."""
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {MCC_EXE}", "/NH", "/FO", "CSV"], capture_output=True,
                             text=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.SubprocessError):
        return True                                     # (cannot tell: treat it as running, write nothing)
    return MCC_EXE.lower() in out.lower()


def set_bot_clan(paths, name, clan, running=None):
    """The owner's edit mode (Nov 16: "add them to clans through the edit mode on the website ... it saves in game"): a
    bot's clan tag written where the game reads it, its line in native/bin/bot_profiles.ini (bot=<name>,<seed>,<clan>
    [,<looks set by hand>], as native/bots_panel.cpp profiles_save writes it; brain/looks.py and botcore read it), the
    rest of the file as it was. A bot with no line gets one as the panel's profile_ensure makes it: the look seed it
    already wears (brain/looks.py seed_of), so its look is unchanged. "" takes it out of its clan. Refused while MCC
    runs (botcore reads the file at MCC's start and would write over it); worn in game from MCC's next start. A copy
    of the file as it was is kept beside it (bot_profiles.ini.before_site_edit). Returns the tag as written."""
    clan = (clan or "").strip()
    if clan and not BOT_CLAN.fullmatch(clan):
        raise ValueError("a clan tag is up to 4 letters or numbers, no spaces or , ; = [ ] |")
    if not isinstance(name, str) or not re.fullmatch(r"[^,\r\n=]{1,15}", name):
        raise ValueError("not a bot's name")
    if (mcc_running() if running is None else running):
        raise PermissionError("close MCC first: it holds the bots' profiles while it runs and would write over the change")
    try:
        with open(paths.profiles, encoding="utf-8", errors="strict", newline="") as f:
            text = f.read()
    except FileNotFoundError:
        raise ValueError("this PC has no bot_profiles.ini yet (MCC with the mod makes it)")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    for i, line in enumerate(lines):
        if not line.startswith("bot="):
            continue
        fields = line[4:].split(",", 3)
        if len(fields) >= 2 and fields[0].lower() == name.lower():
            fields = (fields + [""])[:max(3, len(fields))]
            fields[2] = clan
            if len(fields) == 4 and not fields[3]:
                fields = fields[:3]
            lines[i] = "bot=" + ",".join(fields)
            break
    else:
        seed = zlib.crc32(name.lower().encode("utf-8")) or 1    # (brain/looks.py seed_of, botcore name_look_seed)
        at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
        lines.insert(at, f"bot={name},{seed},{clan}")
    shutil.copyfile(paths.profiles, paths.profiles + ".before_site_edit")
    with open(paths.profiles + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines))
    os.replace(paths.profiles + ".tmp", paths.profiles)
    return clan


# the bots panel's difficulty keys (native/bots_panel.cpp TIER_KEY, in its order)
TIER_KEYS = ("novice", "average", "strong", "top", "scaling", "demon", "blind", "tactician", "mythic")
NO_WHEELMAN = ("demon", "mythic")   # (Nov 18) no Wheelman style: Demon's rules (bots_panel.h hb_style_fits)
POOL_HEADER = ("; Bot Matchmaking (BOTS panel): the queue positions in bot_pool_4v4.txt and bot_pool_8v8.txt, the clans'\n"
               "; reshuffle, and each bot's saved difficulty and play style (saved=<difficulty>,<style>,<name>). A bot with\n"
               "; no line here takes the defaults.\n")


def _rewrite(path, lines, nl):
    shutil.copyfile(path, path + ".before_site_edit")
    with open(path + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines))
    os.replace(path + ".tmp", path)


def set_bot_difficulty(paths, name, tier, running=None):
    """(Nov 18, the owner: "edit a bot's difficulty on the website and have it change in the game") a bot's saved
    difficulty, written as the BOTS panel writes it when its difficulty is changed (bots_panel.cpp bot_pool_remember):
    its saved=<difficulty>,<style>,<name> line in native/bin/bot_pool_saved.ini, which Bot Matchmaking seats it with,
    its play style kept (Demon and Mythic never Wheelman, NO_WHEELMAN: then any), and its tier in the lobby list's bot=/ffbot= lines of
    botcore.ini when it is on that list. "" takes its saved line out (it takes the lobby's difficulty again; the lobby
    list is left as it is). Refused while MCC runs (botcore holds both files and writes them back); in game from MCC's
    next start. A copy of each file as it was is kept beside it (.before_site_edit). Names match as the panel matches
    them (pool_name, no case). Returns the tier key as saved."""
    tier = (tier or "").strip().lower()
    if tier and tier not in TIER_KEYS:
        raise ValueError("not a difficulty")
    if not isinstance(name, str) or len(name) > 32 or not pool_name(name):
        raise ValueError("not a bot's name")
    name = pool_name(name)                                  # (as the panel keeps it: "Name " is "Name")
    if (mcc_running() if running is None else running):
        raise PermissionError("close MCC first: it holds the bots' difficulties while it runs and would write over the change")
    try:
        with open(paths.pool, encoding="utf-8", errors="strict", newline="") as f:
            text = f.read()
    except FileNotFoundError:
        if not tier:
            return ""
        with open(paths.pool, "w", encoding="utf-8", newline="") as f:
            f.write(POOL_HEADER)
        text = POOL_HEADER
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    style, at = "any", None
    for i, line in enumerate(lines):
        parts = line[6:].split(",", 2) if line.startswith("saved=") else []
        if len(parts) == 3 and pool_name(parts[2]).lower() == name.lower():
            style, at, name = parts[1], i, pool_name(parts[2])   # (its line's own spelling kept)
            break
    if tier in NO_WHEELMAN and style == "wheelman":
        style = "any"
    if tier:
        new = f"saved={tier},{style},{name}"
        if at is None:
            lines.insert(len(lines) - 1 if lines and lines[-1] == "" else len(lines), new)
        else:
            lines[at] = new
    elif at is not None:
        del lines[at]
    if tier or at is not None:
        _rewrite(paths.pool, lines, nl)
    if tier and os.path.exists(paths.botcore):
        with open(paths.botcore, encoding="utf-8", errors="strict", newline="") as f:
            text = f.read()
        nl = "\r\n" if "\r\n" in text else "\n"
        lines, hit = text.split(nl), False
        for i, line in enumerate(lines):
            key = "ffbot=" if line.startswith("ffbot=") else "bot=" if line.startswith("bot=") else None
            parts = line[len(key):].split(",", 3) if key else []
            if len(parts) == 4 and pool_name(parts[3]).lower() == name.lower():
                parts[1] = tier
                if tier in NO_WHEELMAN and parts[2] == "wheelman":
                    parts[2] = "any"
                lines[i], hit = key + ",".join(parts), True
        if hit:
            _rewrite(paths.botcore, lines, nl)
    return tier


def all_looks(paths, names):
    """The looks file the site draws from: bot_looks.ini (the bots panel's: the profile bots) and, for every listed bot
    that has no Reach look there (a matchmaking pool bot with no profile), the Reach look it wears in game, worked out
    the mod's own way (brain/looks.py armory_view: a bot's look comes from its name alone, the seed native/pool_test.cpp
    holds botcore to). Written to this tool's store (service_record/bot_looks_site.ini) only when it changes, so the
    figures are redrawn only then; bot_looks.ini itself is only read. Falls back to bot_looks.ini when the looks code
    cannot be loaded."""
    try:
        with open(paths.looks, encoding="utf-8", errors="replace") as f:
            base = f.read()
    except OSError:
        base = ""
    have = {line.split("|", 1)[0] for line in base.splitlines() if "|reach|own|" in line}
    missing = [n for n in names if n and n not in have and "|" not in n and "\n" not in n]
    extra = []
    if missing:
        try:
            if ROOT not in sys.path:
                sys.path.insert(0, ROOT)
            from brain import looks as brain_looks
            for n in sorted(missing):
                views = brain_looks.armory_view(n, "reach", path=paths.profiles)
                extra += [f"{n}|reach|{view}|{kv}" for view, kv in zip(("own", "other"), views) if kv]
        except (ImportError, OSError, ValueError, KeyError, TypeError):
            return paths.looks
    text = base.rstrip("\n") + "\n" + "".join(line + "\n" for line in extra)
    out = os.path.join(paths.store, "bot_looks_site.ini")
    try:
        with open(out, encoding="utf-8") as f:
            if f.read() == text:
                return out
    except OSError:
        pass
    os.makedirs(paths.store, exist_ok=True)
    with open(out + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(out + ".tmp", out)
    return out


def bot_figures(paths, looks_file=None):
    """{bot: {"src": "figures/bots/<file>.webp", "n": angles, "w": an angle's width, "h": height}}: each bot's Reach
    figure as the bots panel draws it, its own armor pieces and colours, turned round in 24 steps (native/
    figure_snap.exe, the panel's model_view.cpp on a device of its own: MCC need not run), the angles side by side in
    one picture. Drawn again into the art store when bot_looks.ini or the program is newer than the last drawing,
    kept as WebP (a twentieth of the PNG), then copied into the site; nothing when the program, the models or a bot's
    Reach look is missing (its page shows MCC's drawing instead)."""
    folder = os.path.join(paths.store, "art", "figures", "bots")
    index = os.path.join(folder, "figures.tsv")
    drawn_file = os.path.join(folder, "drawn.json")      # {bot: the Reach look line its figure was drawn from}
    looks_file = looks_file or paths.looks
    try:
        with open(looks_file, encoding="utf-8", errors="replace") as f:
            lines = {ln.split("|", 1)[0]: ln.rstrip("\r\n") for ln in f if "|reach|own|" in ln}
        program = os.path.getmtime(paths.snap)
    except OSError:
        lines, program = {}, None
    drawn = load_json(drawn_file, {}) if os.path.exists(index) else {}
    if program and drawn.get("_program") != program:
        drawn = {}                                      # (a new figure_snap: every figure again)
    todo = {n: ln for n, ln in lines.items() if drawn.get(n) != ln}
    if todo and program and os.path.isdir(paths.models):
        # only the bots that are new or whose look changed, drawn into a folder of their own, then merged
        tmp = os.path.join(folder, "_new")
        os.makedirs(tmp, exist_ok=True)
        part = os.path.join(tmp, "looks.ini")
        with open(part, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(ln + "\n" for ln in todo.values()))
        try:
            subprocess.run([paths.snap, part, paths.models, tmp, *FIGURE_SIZE], capture_output=True, timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with open(os.path.join(tmp, "figures.tsv"), encoding="utf-8", errors="replace") as f:
                new_rows = [line.rstrip("\r\n").split("\t") for line in f if line.strip()]
            old_rows = []
            if os.path.exists(index):
                with open(index, encoding="utf-8", errors="replace") as f:
                    old_rows = [line.rstrip("\r\n").split("\t") for line in f if line.strip()]
            done = {r[0] for r in new_rows}
            for r in new_rows:
                if len(r) >= 2 and re.fullmatch(r"[a-z0-9_]+\.png", r[1]):
                    os.replace(os.path.join(tmp, r[1]), os.path.join(folder, r[1]))
            rows = [r for r in old_rows if r[0] not in done] + new_rows
            with open(index + ".tmp", "w", encoding="utf-8", newline="\n") as f:
                f.write("".join("\t".join(r) + "\n" for r in rows))
            os.replace(index + ".tmp", index)
            drawn.update({n: todo[n] for n in done if n in todo})
            drawn["_program"] = program
            save_json(drawn_file, drawn)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        shutil.rmtree(tmp, ignore_errors=True)
    out = {}
    try:
        with open(index, encoding="utf-8", errors="replace") as f:
            rows = [line.rstrip("\r\n").split("\t") for line in f]
    except OSError:
        return out
    files = {}
    for r in rows:
        if len(r) < 6 or not re.fullmatch(r"[a-z0-9_]+\.png", r[1]) or not all(x.isdigit() and int(x) > 0 for x in r[3:6]):
            continue
        png_path, web = os.path.join(folder, r[1]), r[1][:-4] + ".webp"
        web_path = os.path.join(folder, web)
        try:                                            # (the PNG, 4 MB a bot, goes once its WebP is written)
            if os.path.exists(png_path) and (not os.path.exists(web_path) or os.path.getmtime(web_path) < os.path.getmtime(png_path)):
                from PIL import Image
                with Image.open(png_path) as im:
                    im.save(web_path + ".tmp", "WEBP", quality=84, method=4)
                os.replace(web_path + ".tmp", web_path)
            if os.path.exists(png_path) and os.path.exists(web_path):
                os.remove(png_path)
        except (OSError, ImportError, ValueError):
            pass
        if not os.path.exists(web_path):
            continue
        files[r[0]] = (web, int(r[3]), int(r[4]), int(r[5]))
    got = menu_pictures(os.path.join("figures", "bots"), {f[0] for f in files.values()}, paths)
    return {name: {"src": got[f[0]].replace("\\", "/"), "n": f[1], "w": f[2], "h": f[3]}
            for name, f in files.items() if f[0] in got}


def mode_pictures(paths, table=os.path.join(SITE, "modes.json")):
    """{family: "modes/<n>.png"}: each game type family's icon from the owner's sheet, for the ones modes.json names and
    this PC has (never in git); a family without one keeps the site's drawn badge."""
    icons = load_json(table, {}).get("icons", {})
    files = {k: f"{n}.png" for k, n in icons.items() if isinstance(n, int) and 1 <= n <= 99}
    got = menu_pictures("modes", set(files.values()), paths)
    return {k: got[f] for k, f in files.items() if f in got}


def vehicle_keys(path=os.path.join(SITE, "weapons.json")):
    """["reach:24", ...]: the damage types that are a vehicle (its gun, its bomb or the vehicle itself), from the
    site's table; the state leaderboards rank these on a board of their own."""
    table = load_json(path, {})
    return sorted(f"{g}:{k}" for g, t in table.items() if isinstance(t, dict) for k in t.get("vehicles", []))


def arsenal_keys(path=os.path.join(SITE, "weapons.json")):
    """{"weapons": ["reach:4", ...], "vehicles": [...]}: everything a game's multiplayer kills with, in the table's
    order (its "arsenal" and "vehicles"). The owner (Nov 17): "all weapons and vehicles to be on the site pages
    correlating to them even if the player has no kills with it": the Weapons page and the state boards list these
    whether or not any bot has a kill with one."""
    table = load_json(path, {})
    out = {"weapons": [], "vehicles": []}
    for g, t in table.items():
        if isinstance(t, dict):
            out["weapons"] += [f"{g}:{k}" for k in t.get("arsenal", [])]
            out["vehicles"] += [f"{g}:{k}" for k in t.get("vehicles", [])]
    return out


MEDAL_GROUPS = ("multikill", "spree", "kill", "style", "assist", "objective", "legendary", "other")
MULTIKILL = re.compile(r"medal_(double|triple|overkill|killtacular|killtrocity|killimanjaro|killtastrophe|killpocalypse"
                       r"|killionaire)")


def medal_group(info):
    """A medal's group on the Medals page, as the old service record grouped them, from MCC's own type for it
    (careerdb.xml, service_record_art.py): Spree's multikills (double ... killionaire) apart from its sprees, kill
    streaks and role sprees with the sprees, mode medals as objective. "other" when MCC's type is not known."""
    kind, key = info.get("kind", ""), info.get("key", "")
    if kind == "Spree" and MULTIKILL.match(key):
        return "multikill"
    return {"Spree": "spree", "KillStreak": "spree", "RoleKillSpree": "spree", "Kill": "kill", "Style": "style",
            "AssistSupport": "assist", "ModeSpecific": "objective", "Legendary": "legendary"}.get(kind, "other")


def weapon_pictures(keys, paths):
    """{"reach:6": "weapons/pgcr_dmr.png", ...}: the picture of each damage type the pages name, copied into the site
    from this PC's art store (tools/service_record_art.py weapons: MCC's own pictures, never in git). A damage type
    with no picture there is left out, and its card shows the site's own placeholder."""
    index = load_json(os.path.join(paths.store, "art", "weapons.json"), {})
    out = {}
    for key in keys:
        game_key, _, kind = key.partition(":")
        name = index.get(game_key, {}).get(kind) if isinstance(index.get(game_key), dict) else None
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]+\.png", name):
            continue
        src = os.path.join(paths.store, "art", "weapons", name)
        dst = os.path.join(paths.out, "weapons", name)
        try:
            if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
        except OSError:
            continue
        out[key] = "weapons/" + name
    return out


def write_game_ranks(data, paths):
    """(Nov 17, the owner: "add whatever rank we are from our service record website to beside our names like in the
    original halo reach") <out>/ranks.txt, each player's Reach rank as the site shows it, for the game's own rows
    (native/proving_grounds.cpp reads it and the site's ranks/<step>.png beside it). The one rank table stays
    ranks.json and the credits stay this file's: the game reads the result, never a sum of its own.
    (Nov 17, the owner's Reach roster pictures: a player picked in the list shows their card) then the card's numbers,
    the site's own: Reach games played, kills per death, the share won, Overall Commendation Progress, the credits, and
    the daily and weekly challenges completed (as Reach's card listed them); empty where the site has none (the card
    shows "...")."""
    lines = ["# made from tools/service_record_site/ranks.json by tools/service_record.py; do not edit",
             "# name<TAB>rank step (0 = Recruit, the site's ranks/<step>.png)<TAB>rank<TAB>games<TAB>K/D<TAB>win %"
             "<TAB>commendation progress %<TAB>credits<TAB>daily challenges completed<TAB>weekly"]
    for p in data["players"]:
        step = int(p.get("rank") or 0)
        label = data["ranks"][step][0] if 0 <= step < len(data["ranks"]) else ""
        name = str(p["name"]).replace("\t", " ").replace("\n", " ")
        s = (p["g"].get(DEFAULT_GAME, {}).get("cats", {}).get("all") or blank()) if isinstance(p.get("g"), dict) else blank()
        games = int(s["games"])
        kd = f"{career.kd(s):.2f}" if games else ""
        win = str(round(100 * s["wins"] / games)) if games else ""
        chal = p.get("chal") if isinstance(p.get("chal"), dict) else {}
        daily, weekly = chal.get("daily_done", ""), chal.get("weekly_done", "")
        lines.append(f"{name}\t{step}\t{label}\t{games}\t{kd}\t{win}\t{p.get('comm_pct', 0.0):.1f}\t{int(p.get('cr') or 0)}"
                     f"\t{daily}\t{weekly}")
    tmp = os.path.join(paths.out, "ranks.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(paths.out, "ranks.txt"))


def write_game_challenges(data, paths):
    """(Nov 17, docs: the challenges in game, and the owner's Bungie.net Reach Challenges picture) <out>/challenges.txt,
    the live challenges as this build drew them (challenge_table) and each listed person's progress on them
    (challenge_progress), for Proving Grounds' Challenges page (native/proving_grounds.cpp). The game reads this and
    works nothing out: the site and the game show the same numbers."""
    C = data.get("challenges") or {}
    by = {c["key"]: c for c in C.get("list", [])}
    clean = lambda s: str(s).replace("\t", " ").replace("\n", " ")
    lines = ["# made by tools/service_record.py with the site (challenge_table, challenge_progress); do not edit",
             "# period<TAB>daily|weekly<TAB>its first date<TAB>when it ends (seconds since 1970)",
             "# challenge<TAB>period<TAB>key<TAB>name<TAB>what to do<TAB>need<TAB>cR<TAB>icon (the live ones, in order)",
             "# person<TAB>name<TAB>daily completed<TAB>weekly completed<TAB>challenge cR; progress<TAB>name<TAB>key<TAB>n"]
    for period in ("weekly", "daily"):
        w = C.get(period)
        if not w:
            continue
        lines.append(f"period\t{period}\t{w['start']}\t{int(w['ends'])}")
        for k in w["keys"]:
            c = by.get(k)
            if c:
                lines.append(f"challenge\t{period}\t{k}\t{clean(c['name'])}\t{clean(c['what'])}\t{int(c['need'])}"
                             f"\t{int(c['cr'])}\t{clean(c.get('icon', ''))}")
    for p in data["players"]:
        if not p.get("person"):
            continue
        ch = p.get("chal") if isinstance(p.get("chal"), dict) else {}
        name = clean(p["name"])
        lines.append(f"person\t{name}\t{int(ch.get('daily_done', 0))}\t{int(ch.get('weekly_done', 0))}\t{int(ch.get('cr', 0))}")
        lines += [f"progress\t{name}\t{k}\t{int(n)}" for k, n in (ch.get("now") or {}).items()]
    tmp = os.path.join(paths.out, "challenges.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(paths.out, "challenges.txt"))


def write_game_commendations(data, paths):
    """(Nov 19, the owner's picture of Halo: Reach's Service Record: Commendations, "add it to ours with its own menu
    option, and keep it connected to the service record site") <out>/commendations.txt for Proving Grounds' Commendations
    page (native/proving_grounds.cpp): the site's table and banners (each tier's own where the site has it), and each
    listed person's counts with the tier reached as the site's Commendations page counts it (app.js commState: the tiers
    whose need the count reaches), their Overall Commendation Progress, credits, rank and the next rank. The game works
    nothing out: the page and the site show the same numbers."""
    C = data.get("commendations") or {}
    comms, tiers = C.get("list") or [], C.get("tiers") or []
    art, tier_art = C.get("art") or {}, C.get("tier_art") or {}
    ranks = data.get("ranks") or []
    clean = lambda s: str(s).replace("\t", " ").replace("\n", " ")
    lines = ["# made by tools/service_record.py with the site (its commendations table, commendation_counts); do not edit",
             "# tiers<TAB>Iron<TAB>Bronze ...",
             "# commendation<TAB>key<TAB>set (mp, pg)<TAB>name<TAB>what to do<TAB>needs (comma)<TAB>cR (comma)<TAB>banner"
             "<TAB>each tier's banner (comma, empty where none; paths under this folder)",
             "# person<TAB>name<TAB>commendation progress %<TAB>credits<TAB>rank<TAB>next rank<TAB>its credits",
             "# count<TAB>name<TAB>key<TAB>n (empty: not recorded yet)<TAB>tiers reached",
             "tiers\t" + "\t".join(clean(t) for t in tiers)]
    for c in comms:
        row = (tier_art.get(c["key"]) or [None])[1:]
        lines.append(f"commendation\t{clean(c['key'])}\t{clean(c.get('set', 'mp'))}\t{clean(c['name'])}\t{clean(c['what'])}"
                     f"\t{','.join(str(int(x)) for x in c['need'])}\t{','.join(str(int(x)) for x in c['cr'])}"
                     f"\t{clean(art.get(c['key']) or '')}\t{','.join(clean(x or '') for x in row)}")
    for p in data["players"]:
        if not p.get("person"):
            continue
        name, step = clean(p["name"]), int(p.get("rank") or 0)
        label = ranks[step][0] if 0 <= step < len(ranks) else ""
        nxt = ranks[step + 1] if 0 <= step + 1 < len(ranks) else None
        lines.append(f"person\t{name}\t{float(p.get('comm_pct') or 0):.1f}\t{int(p.get('cr') or 0)}\t{clean(label)}"
                     f"\t{clean(nxt[0]) if nxt else ''}\t{int(nxt[1]) if nxt else ''}")
        counts = p.get("comm") or {}
        for c in comms:
            n = counts.get(c["key"])
            lines.append(f"count\t{name}\t{clean(c['key'])}\t{'' if n is None else int(n)}"
                         f"\t{commendation_tier(n, c['need'])}")
    tmp = os.path.join(paths.out, "commendations.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(paths.out, "commendations.txt"))


def write_game_locations(data, paths):
    """(Nov 19, the owner: Proving Grounds' Psych Profile page, "a static heat map of the service websites player
    locations") <out>/locations.txt: how many of the site's listed players (bots and people) have each home state, as
    the site shows them (states.json's pick from the name, or the one set in edit mode), and each person's own state.
    The game draws the heat over its world map (native/proving_grounds_reach.inc, native/world_map.h)."""
    _, states = load_states()
    counts = {s[0]: 0 for s in states}
    people = []
    for p in data["players"]:
        code = p.get("state")
        if code in counts:
            counts[code] += 1
            if p.get("person"):
                people.append((str(p["name"]).replace("\t", " ").replace("\n", " "), code))
    lines = ["# made by tools/service_record.py with the site's home states (states.json, edit mode); do not edit",
             "# state<TAB>code<TAB>name<TAB>players (bots and people) with it as their home state",
             "# person<TAB>name<TAB>code"]
    lines += [f"state\t{s[0]}\t{s[1]}\t{counts[s[0]]}" for s in states]
    lines += [f"person\t{n}\t{c}" for n, c in people]
    tmp = os.path.join(paths.out, "locations.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(paths.out, "locations.txt"))


def write_last_match(data, paths):
    """(Nov 17, the owner: "add this level up bar after each game showing what earned you your xp", after the carnage
    report) <out>/last_match.txt: what the newest match on the site (a Proving Grounds match) earned each listed person
    in it, for Proving Grounds' credits screen when its lobby comes back (native/proving_grounds.cpp). Their credits
    before and after; a line for each kind of credit by ranks.json's worth (the game played, the win, kills, assists,
    medals), then the rest of the difference: Challenges (as their credits grew since the last build) and Commendations
    (tiers reached); the rank steps the bar runs through.
    "Before" is what the last build had (<store>/credits_seen.json), so the bar starts where the site stood; a match
    already reported is not reported again (the file keeps its last report). A newest match no listed person played
    gets its match line alone, so the game does not wait for a report that will not come."""
    matches = data.get("matches") or []
    seen_path = os.path.join(paths.store, "credits_seen.json")
    seen = load_json(seen_path, {})
    seen = seen if isinstance(seen, dict) else {}
    persons = {p["name"]: p for p in data["players"] if p.get("person")}
    ranks, worth = data["ranks"], data["credits"]
    # (Nov 17, the bot simulation) the newest match a person played: simulated ones beside it have bots alone
    m = next((x for x in matches if any(not r["bot"] for r in x["rows"])), matches[0] if matches else None)
    lines = []
    for r in (m["rows"] if m else []):
        p = persons.get(r["n"])
        prev = seen.get(r["n"]) if isinstance(seen.get(r["n"]), dict) else {}
        if not p or not r.get("listed") or prev.get("match") == m["id"]:
            continue
        after = int(p.get("cr") or 0)
        parts = []
        if m["game"] == DEFAULT_GAME:                       # (credits come from Reach matches only)
            md = int(r.get("md", 0))
            parts = [("Game Completed", 1, worth["game"]), ("Victory", int(r["won"]), int(r["won"]) * worth["win"]),
                     ("Kills", r["k"], r["k"] * worth["kill"]), ("Assists", r["a"], r["a"] * worth["assist"]),
                     ("Medals", md, md * worth["medal"])]
            parts = [x for x in parts if x[0] == "Game Completed" or x[1]]
        earned = sum(x[2] for x in parts)
        before = prev.get("cr") if isinstance(prev.get("cr"), int) else after - earned
        rest = after - before - earned
        if rest < 0:                                        # (a reset since, or no last build: the match's own only)
            before, rest = after - earned, 0
        chal = 0                                            # (the rest: challenges finished, by how their credits grew
        if rest and isinstance(prev.get("chal"), int):      # since the last build; commendation tiers the remainder)
            chal = max(0, min(rest, int((p.get("chal") or {}).get("cr", 0)) - prev["chal"]))
        if rest - chal:
            parts.append(("Commendations", "", rest - chal))
        if chal:
            parts.append(("Challenges", "", chal))
        lo, hi = rank_index(max(before, 0), [[0, 0, 0, x[1]] for x in ranks]), int(p.get("rank") or 0)
        name = str(r["n"]).replace("\t", " ")
        lines.append(f"person\t{name}\t{before}\t{after}")
        lines += [f"line\t{name}\t{label}\t{n}\t{cr}" for label, n, cr in parts]
        lines += [f"step\t{name}\t{s}\t{ranks[s][0]}\t{ranks[s][1]}" for s in range(lo, min(hi + 2, len(ranks)))]
    for name, p in persons.items():                         # (where each person's credits stand now)
        in_m = bool(m) and any(r["n"] == name for r in m["rows"])
        old = seen.get(name) if isinstance(seen.get(name), dict) else {}
        seen[name] = {"match": m["id"] if in_m else old.get("match"), "cr": int(p.get("cr") or 0),
                      "chal": int((p.get("chal") or {}).get("cr", 0))}
    os.makedirs(paths.store, exist_ok=True)
    save_json(seen_path, seen)
    path = os.path.join(paths.out, "last_match.txt")
    try:
        with open(path, encoding="utf-8") as f:
            had = next((l.rstrip("\n").split("\t")[1] for l in f if l.startswith("match\t")), None)
    except OSError:
        had = None
    if lines or (m and had != m["id"]):                    # (a match nobody listed played: its line alone, so the
                                                            # game knows there is nothing to show)
        text = ["# made by tools/service_record.py with the site: what the newest Proving Grounds match earned; do not edit",
                "# match<TAB>id; person<TAB>name<TAB>credits before<TAB>after; line<TAB>name<TAB>what<TAB>count<TAB>credits;",
                "# step<TAB>name<TAB>rank step<TAB>rank<TAB>its credits (the steps the bar runs through, and the next)",
                f"match\t{m['id']}"] + lines
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(text) + "\n")
        os.replace(tmp, path)


def write_site(data, paths):
    """The pages (copied as they are) and data.js; stamp.js last, the sign an open page watches for a new build."""
    os.makedirs(paths.out, exist_ok=True)
    for name in ("index.html", "style.css", "app.js", "backdrop.svg"):
        shutil.copyfile(os.path.join(SITE, name), os.path.join(paths.out, name))
    art = os.path.join(paths.store, "art", "ranks")
    if os.path.isdir(art):                                  # (rank insignia made on this PC, when there are any)
        os.makedirs(os.path.join(paths.out, "ranks"), exist_ok=True)
        have = []
        for f in os.listdir(art):
            if re.fullmatch(r"\d+\.png", f):
                shutil.copyfile(os.path.join(art, f), os.path.join(paths.out, "ranks", f))
                have.append(int(f[:-4]))
        data["rank_art"] = sorted(have)
    write_game_ranks(data, paths)
    write_last_match(data, paths)
    write_game_challenges(data, paths)
    write_game_commendations(data, paths)                    # (Nov 19: the game's Commendations page)
    write_game_locations(data, paths)                        # (Nov 19: the heat on the game's Psych Profile map)
    for name, text in (("data.js", "window.SR_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n"),
                       ("stamp.js", f'window.SR_STAMP && window.SR_STAMP("{data["stamp"]}");\n')):
        tmp = os.path.join(paths.out, name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, os.path.join(paths.out, name))


def waiting_report(paths, ledger, never):
    """Whether a report on disk is one bot_career.py would add and has not yet. `never` collects the files it never
    adds (not a report, or one with no player rows), so they are read in full once."""
    for path in glob.glob(os.path.join(paths.logs, "trace_*.carnage.xml")) + [paths.mcc_report]:
        if path in never:
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                m = re.search(r'GameUniqueId="([^"]+)"', f.read(4096))     # (its first lines are enough)
        except OSError:
            continue
        if m and m.group(1) in ledger:
            continue
        gid, players = career.read_report(path)
        if gid and players:
            return True
        never.add(path)
    return False


def wait_ledger(paths, seconds):
    """Wait until the ledger has every report on disk (tools/play.py starts bot_career.py beside this build), at most
    `seconds`. Whether it caught up."""
    end, never = time.time() + seconds, set()
    while waiting_report(paths, load_json(paths.ledger, {}), never):
        if time.time() >= end:
            return False
        time.sleep(1)
    return True


def build(paths):
    """Read, keep, write. Returns the site's data."""
    ledger = load_json(paths.ledger, {})
    store_path = os.path.join(paths.store, "matches.json")
    store = load_json(store_path, {})
    if update_store(store, paths):
        save_json(store_path, store)
    kills_path = os.path.join(paths.store, "kills.json")
    kills = load_json(kills_path, {})
    if not isinstance(kills, dict):
        kills = {}
    if update_kills(kills, paths):
        save_json(kills_path, kills)
    matches, kill_rows_all = store.get("matches", {}), kills.get("kills", {})
    if HERE not in sys.path:                                # (python -I leaves this folder off sys.path: without it
        sys.path.insert(0, HERE)                            # the import below failed and no simulated match showed)
    try:                                                    # (Nov 17, the bot simulation: tools/bot_sim.py's matches,
        import bot_sim                                      # shown as the real ones are; never saved into these files)
        sim_ledger, sim_matches, sim_kills = bot_sim.site_entries(paths)
    except Exception:
        sim_ledger = sim_matches = sim_kills = {}
    if sim_ledger:
        ledger = {**ledger, **sim_ledger}
        matches = {**matches, **sim_matches}
        kill_rows_all = {**kill_rows_all, **sim_kills}
    data = site_data(ledger, matches, paths, kills=kill_rows_all)
    write_site(data, paths)
    return data


def main(argv):
    kw = {}
    for flag in ("ledger", "logs", "store", "out"):
        if "--" + flag in argv:
            i = argv.index("--" + flag)
            if i + 1 >= len(argv):
                sys.exit(f"--{flag} needs a value")
            kw[flag] = os.path.abspath(argv[i + 1])
    paths = Paths(**kw)
    if "--wait-ledger" in argv:
        i = argv.index("--wait-ledger")
        try:
            wait_ledger(paths, float(argv[i + 1]))
        except (IndexError, ValueError):
            sys.exit("--wait-ledger needs a number of seconds")
    t0 = time.time()
    data = build(paths)
    if "--check-kills" in argv:              # each recorded match's kill rows against MCC's report, player by player
        matches = load_json(os.path.join(paths.store, "matches.json"), {}).get("matches", {})
        kills = load_json(os.path.join(paths.store, "kills.json"), {}).get("kills", {})
        for m in sorted(matches.values(), key=lambda m: m.get("start", "")):
            entry = kills.get(f"{m.get('map')}_{m.get('start')}")
            if entry is None:
                continue
            rows = kill_rows(entry)
            lines = kill_check(m, rows)
            off = [x for x in lines if x[1] != x[2] or x[3] != x[4]]
            print(f"{m['map']} {m['start']} ({m.get('type', '')}): {len(rows)} rows, "
                  + ("every player's kills and deaths equal MCC's report" if not off else f"{len(off)} of {len(lines)} players differ"))
            for name, k, rk, d, rd in off:
                print(f"    {name}: kills {k} (report {rk}), deaths {d} (report {rd})")
    if "--quiet" in argv:
        return 0
    played = sum(1 for p in data["players"] if p["g"])
    print(f"{NAME}: {len(data['players'])} bots ({played} with a counted match), {len(data['matches'])} matches "
          f"({sum(1 for m in data['matches'] if m['kills'])} with kill rows), "
          f"{len(data['medals'])} medals named; built in {time.time() - t0:.1f} s")
    print(os.path.join(paths.out, "index.html"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

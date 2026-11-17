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

Who is listed (the owner, Nov 15): the bots only. Every bot of bot_profiles.ini, at 0 from the start, and any other
bot once it has a match that counts. People are never listed; a match's scoreboard still shows every gamertag.
A match counts by bot_career's rules (its person played 60 s or more; a bot's row of a match from before the bots'
restart does not), so with every game shown the leaderboard equals native/bin/career/totals.txt.

Credits and ranks: service_record_site/ranks.json. A player's credits are a pure function of their counted Reach
matches (each game, win, kill, assist and medal is worth what "credits" says), so a rank can always be rebuilt.

usage: python -I service_record.py                    build, then print what was built
       python -I service_record.py --quiet            build only (tools/play.py, in the background, as a match starts)
       python -I service_record.py --wait-ledger 20   first wait up to 20 s for bot_career.py to add the reports on disk
       python -I service_record.py --check-kills      also print each recorded match's kill rows against MCC's report
       --ledger FILE --logs DIR --store DIR --out DIR  other places (tests, a preview from another ledger)
"""
import glob
import hashlib
import html
import importlib.util
import json
import os
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


def _int(a, key):
    try:
        return int(a.get(key, "0"))
    except ValueError:
        return 0


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
        elif how.get("distinct_medals"):                         # (kinds of medal earned at least once)
            n = sum(1 for v in medals.values() if v)
        elif ("weapons" in how or "vehicles" in how) and g.get("kill_games"):
            keys = vehicles if how.get("vehicles") else {f"reach:{w}" for w in how.get("weapons", [])}
            n = sum(v[0] for k, v in weapons.items() if k in keys)
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
            try:
                if not os.path.exists(dst) or os.path.getmtime(dst) < max(os.path.getmtime(emb), os.path.getmtime(base)):
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
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    img.save(dst + ".tmp.png")
                    os.replace(dst + ".tmp.png", dst)
                row[i] = f"commendations/{key}_{tier}.png"
            except (OSError, ValueError):
                continue
        if any(row):
            out[key] = row
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


def collect(ledger, store_matches, roster, kills=None, paths=None):
    """(players {name: record}, matches [newest first]) for the site: every counted row of a listed name summed by
    game and family. Listed: the roster and every name bot_career's totals call a bot. kills: the store's kill rows
    by recording ({"<map>_<start>": [rows]}); a match with none adds nothing to weapons, versus and heat, and
    kill_games says how many of a player's matches had them."""
    totals = career.totals(ledger)
    listed = set(roster) | {n for n, t in totals.items() if t["bot"]}
    players = {n: {"name": n, "g": {}} for n in listed}
    matches = []
    for gid, m in ledger.items():
        rows = m.get("players", [])
        if not career.counts(rows):
            continue
        reset = bool(m.get("bots_reset"))
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
        feats = {}                                          # (name -> {"first", "closer", "grudge"} in this match)
        if entry is not None:
            match["feed"] = kill_feed(detail, kill_rows(entry), game)
            feats = feed_feats(match["feed"], {html.unescape(p["name"]) for p in rows if p["standing"] == 0 and not draw})
        # its heatmap: the map itself, or the Forge layout it was played on ("<map>@<layout id>", export_map)
        heat_key = map_id
        if tally:
            spots_all = [c for t in tally.values() for c in t["k"] + t["d"]]
            variant = match_variant(map_id, (detail or {}).get("start"), spots_all, paths) if paths else None
            if variant:
                heat_key = f"{map_id}@{variant}"
        match["heat"] = heat_key
        for p in counting:
            if p["name"] not in listed:
                continue
            d = by_name.get(p["name"])
            won = p["standing"] == 0 and not draw
            for gkey in ("all", game):
                g = players[p["name"]]["g"].setdefault(gkey, {"cats": {}, "types": {}, "maps": {}, "medals": {},
                                                               "killed": {}, "killed_by": {}, "results": [],
                                                               "weapons": {}, "versus": {}, "heat": {}, "kill_games": 0,
                                                               "feats": {"first": 0, "closer": 0, "grudge": 0}})
                g["results"].append((t, gid, won))
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


def site_data(ledger, store_matches, paths, now=None, kills=None):
    """Everything the pages show, as one dict (data.js)."""
    worth, steps = load_ranks()
    regions, states = load_states()
    roster = read_profiles(paths.profiles)
    pool = read_pool(paths.pool)
    looks = read_looks(paths.looks, read_look_names(paths.look_names))
    players, matches = collect(ledger, store_matches, roster, kills, paths)
    clans = {}
    for m in reversed(matches):                             # (a pool bot's clan tag: its newest report's)
        for r in m["rows"]:
            if r.get("clan"):
                clans[r["n"]] = r["clan"]
    medal_names = load_json(os.path.join(paths.store, "art", "medals.json"), {})
    figures = bot_figures(paths)
    tiers, comms = load_commendations()
    badges = load_badges()
    with_comms = bool(load_json(os.path.join(SITE, "ranks.json"), {}).get("commendation_credits"))
    used = set()
    out_players = []
    for name in sorted(players, key=str.lower):
        rec = players[name]
        reach = rec["g"].get(DEFAULT_GAME, {}).get("cats", {}).get("all") or blank()
        counts = commendation_counts(rec["g"][DEFAULT_GAME], comms, medal_names) if DEFAULT_GAME in rec["g"] else {}
        comm_cr = commendation_credits(counts, comms) if with_comms else 0
        cr = credits(reach, worth) + comm_cr                # (the rank: its matches, and its commendations' tiers)
        for g in rec["g"].values():
            used.update(g["medals"])
        diff, style = pool.get(name, ("", ""))
        out_players.append({
            "name": html.unescape(name), "roster": name in roster,
            "clan": roster.get(name) or clans.get(html.unescape(name), ""),
            "difficulty": diff, "style": style, "emblem": export_emblem(name, paths),
            "looks": looks.get(name), "cr": cr, "rank": rank_index(cr, steps), "comm": counts, "comm_cr": comm_cr,
            "badges": badge_counts(rec["g"][DEFAULT_GAME], badges) if DEFAULT_GAME in rec["g"] else {},
            "state": home_state(html.unescape(name), states), "figure": figures.get(name), "g": rec["g"],
        })
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
        "medal_art": bool(medal_names),
        "weapons": weapons, "heat_maps": {k: v for k, v in heat_maps.items() if v},
        "weapon_art": weapon_pictures(weapons, paths),
        # the owner's own header and sidebar pictures (Nov 16), kept on this PC only; the site's drawing without them
        "backdrops": menu_pictures("backdrops", {"header.jpg", "sidebar.jpg"}, paths),
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
        "regions": regions, "states": {s[0]: [s[1], s[2]] for s in states},
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


def bot_figures(paths):
    """{bot: {"src": "figures/bots/<file>.webp", "n": angles, "w": an angle's width, "h": height}}: each bot's Reach
    figure as the bots panel draws it, its own armor pieces and colours, turned round in 24 steps (native/
    figure_snap.exe, the panel's model_view.cpp on a device of its own: MCC need not run), the angles side by side in
    one picture. Drawn again into the art store when bot_looks.ini or the program is newer than the last drawing,
    kept as WebP (a twentieth of the PNG), then copied into the site; nothing when the program, the models or a bot's
    Reach look is missing (its page shows MCC's drawing instead)."""
    folder = os.path.join(paths.store, "art", "figures", "bots")
    index = os.path.join(folder, "figures.tsv")
    try:
        stale = not os.path.exists(index) or max(os.path.getmtime(paths.looks), os.path.getmtime(paths.snap)) > os.path.getmtime(index)
    except OSError:
        stale = False
    if stale and os.path.isdir(paths.models):
        os.makedirs(folder, exist_ok=True)
        try:
            subprocess.run([paths.snap, paths.looks, paths.models, folder, *FIGURE_SIZE], capture_output=True, timeout=180,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError):
            pass
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
    data = site_data(ledger, store.get("matches", {}), paths, kills=kills.get("kills", {}))
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

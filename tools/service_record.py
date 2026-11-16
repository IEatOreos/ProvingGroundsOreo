"""The Proving Grounds Service Record (custom, Nov 15): a stats site for the bots, laid out like a 2010 service record
(the owner's brief: docs/SERVICE_RECORD_SITE_BRIEF.md). One build reads what the mod already records and writes a
folder of static pages, logs/service_record/index.html, that opens straight from the folder (no server).

Read, never written: the career ledger (native/bin/career/ledger.json, tools/bot_career.py: which matches count, who
won, the bots' restart), MCC's post-game reports (logs/trace_*.carnage.xml and MCC's own current one), the bots'
profiles, looks, saved difficulties and emblems (native/bin). Written: this tool's own store, native/bin/service_record
/matches.json (each report's detail kept once by its GameUniqueId, because the recording rotation deletes the reports),
and the site in logs/service_record. Both are game data: not in git.

Who is listed (the owner, Nov 15): the bots only. Every bot of bot_profiles.ini, at 0 from the start, and any other
bot once it has a match that counts. People are never listed; a match's scoreboard still shows every gamertag.
A match counts by bot_career's rules (its person played 60 s or more; a bot's row of a match from before the bots'
restart does not), so with every game shown the leaderboard equals native/bin/career/totals.txt.

Credits and ranks: service_record_site/ranks.json. A player's credits are a pure function of their counted Reach
matches (each game, win, kill, assist and medal is worth what "credits" says), so a rank can always be rebuilt.

usage: python -I service_record.py                    build, then print what was built
       python -I service_record.py --quiet            build only (tools/play.py, in the background, as a match starts)
       python -I service_record.py --wait-ledger 20   first wait up to 20 s for bot_career.py to add the reports on disk
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
import sys
import time
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
        s.mcc_report = career.MCC_REPORT
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
        players.append({
            "name": a.get("mGamertagText", ""),
            "bot": bool(career.BOT_ID.match(a.get("mXboxUserId", ""))),
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
        out[parts[0]] = {"species": "Elite" if elite else "Spartan", "pieces": pieces}
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


def collect(ledger, store_matches, roster):
    """(players {name: record}, matches [newest first]) for the site: every counted row of a listed name summed by
    game and family. Listed: the roster and every name bot_career's totals call a bot."""
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
                           spree=d["spree"], clan=html.unescape(d["clan"]))
            out_rows.append(row)
        out_rows.sort(key=lambda r: (r["st"], -r.get("score", 0), -r["k"]))
        match = {"id": gid, "t": t, "when": when, "game": game, "map": map_id,
                 "type": (detail or {}).get("type", ""), "cat": family((detail or {}).get("type", "")),
                 "teams": bool(detail and detail["teams"]), "report": bool(detail), "rows": out_rows}
        matches.append(match)
        for p in counting:
            if p["name"] not in listed:
                continue
            d = by_name.get(p["name"])
            won = p["standing"] == 0 and not draw
            for gkey in ("all", game):
                g = players[p["name"]]["g"].setdefault(gkey, {"cats": {}, "types": {}, "maps": {}, "medals": {},
                                                               "killed": {}, "killed_by": {}, "results": []})
                g["results"].append((t, gid, won))
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


def site_data(ledger, store_matches, paths, now=None):
    """Everything the pages show, as one dict (data.js)."""
    worth, steps = load_ranks()
    roster = read_profiles(paths.profiles)
    pool = read_pool(paths.pool)
    looks = read_looks(paths.looks, read_look_names(paths.look_names))
    players, matches = collect(ledger, store_matches, roster)
    clans = {}
    for m in reversed(matches):                             # (a pool bot's clan tag: its newest report's)
        for r in m["rows"]:
            if r.get("clan"):
                clans[r["n"]] = r["clan"]
    medal_names = load_json(os.path.join(paths.store, "art", "medals.json"), {})
    used = set()
    out_players = []
    for name in sorted(players, key=str.lower):
        rec = players[name]
        reach = rec["g"].get(DEFAULT_GAME, {}).get("cats", {}).get("all") or blank()
        cr = credits(reach, worth)
        for g in rec["g"].values():
            used.update(g["medals"])
        diff, style = pool.get(name, ("", ""))
        out_players.append({
            "name": html.unescape(name), "roster": name in roster,
            "clan": roster.get(name) or clans.get(html.unescape(name), ""),
            "difficulty": diff, "style": style, "emblem": export_emblem(name, paths),
            "looks": looks.get(name), "cr": cr, "rank": rank_index(cr, steps), "g": rec["g"],
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
        medals[i] = {"name": info.get("name") or f"Medal {i}", "icon": icon}
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
        "maps": {m["map"]: map_name(m["map"]) for m in matches if m["map"]},
        "players": out_players, "matches": matches, "medals": medals,
        "medal_art": bool(medal_names),
    }


def write_site(data, paths):
    """The pages (copied as they are) and data.js; stamp.js last, the sign an open page watches for a new build."""
    os.makedirs(paths.out, exist_ok=True)
    for name in ("index.html", "style.css", "app.js"):
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
    data = site_data(ledger, store.get("matches", {}), paths)
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
    if "--quiet" in argv:
        return 0
    played = sum(1 for p in data["players"] if p["g"])
    print(f"{NAME}: {len(data['players'])} bots ({played} with a counted match), {len(data['matches'])} matches, "
          f"{len(data['medals'])} medals named; built in {time.time() - t0:.1f} s")
    print(os.path.join(paths.out, "index.html"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

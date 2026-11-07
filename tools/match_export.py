"""Export one recorded match as a single shareable file: everything recorded for it, every player marked a person or a
bot, so other players can share how they play and others (people or their AI tools) can study it to make bots better.

The zip (logs/exports/match_<map>_<date>-<time>.zip) holds:
  manifest.json          what the match was (game, map, modes, score, length, mod version), every player marked
                         "human" or "bot" (bots with name, difficulty and play style), each file with its row formats,
                         and what was removed for privacy. Start here.
  trace.jsonl            the brain's recording: everyone 4 times a second, every bot every tick (position, aim, goal,
                         the buttons it pressed), every bot decision with its scores, callouts, bot profiles,
                         loadout changes
  collect.jsonl          the Data collector, when it was on: everyone every tick, people's guns, rounds, equipment
                         and zoom (no keys: those of older recordings are left out)
  carnage_report.xml     MCC's own post-game report (kills, deaths, medals per player), when it is this match's
  objective_report.txt   objective play (tools/objective_report.py), player_stats.json the people's numbers
                         (tools/player_stats.py): the analyses the Observer shows
  README.txt             how to read it all

Privacy (the file is meant to be shared): Xbox user ids are removed; people's gamertags, clan tags and service tags
become "Player 1", "Player 2" ... (--keep-names keeps them; the Xbox ids go regardless); the Windows user folder in
any path becomes "<home>".

usage: python -I match_export.py <trace file or match stamp> [--keep-names] [--out <zip>]
       python -I match_export.py --list           the matches there are to export
"""
import datetime
import glob
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
LOGS = os.path.join(ROOT, "logs")
OUT_DIR = os.path.join(LOGS, "exports")
MCC_TEMP = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "MCC", "Temporary")
FORMAT = 1                  # bump when the layout of the zip or of a file in it changes
BOT_XUID = "0xB07B07B0"     # botcore's player identifiers for bots (native/reach.cpp and the other games' adds)

# the row formats, for whoever reads the data (brain/tracefmt.py, tools/live_bots.py, tools/collector.py)
FORMATS = {
    "trace.jsonl": {
        "meta": '{"t", "meta": {"map", "game", "bot": {"id", "name", "team", "tier", "pers"}}}: once per bot. tier: '
                'novice = Easy, average = Normal, strong = Heroic, top = Legendary; pers = play style',
        "world": '{"t", "mode", "score", "limit", "time_left", "posture", "world": [row per player], "deployed", "flags", '
                 '"hill", "ball"}: 4 a second. Row: 0 player id, 1 team, 2 alive, 3-5 x y z, 6 shield, 7 health, '
                 '8 BOT (true = a bot, false = a person), 9 carrying the flag, 10 yaw, 11 pitch, 12 seconds standing '
                 'still, 13 ids of teammates formed up within 8 units, 14 the enemy in its sights (-1 nobody). flags: '
                 '{team: [state, x, y, z, carrier id]}; hill: [x, y, z, radius]; ball: [x, y, z, carrier id]',
        "bot": '{"t", "id", "pos", "yaw", "pitch", "goal", "arg", "veh", "wpn", "wp", "foes", "cmd", ["fx"], ["att"], '
               '["notes"], ["eq"], ["inv"], "hp"}: every bot every tick. goal: what it is doing (fight, objective, '
               'item, hunt, roam, retreat, hold ...), arg its target; veh: vehicle handle (-1 on foot); wp: next path '
               'point; foes: [enemy id, shield, health]; cmd: [forward, strafe, yaw, buttons, pitch] it sent, buttons '
               'bits: 1 fire, 2 jump, 4 crouch, 8 grenade, 16 melee, 32 use, 64 reload, 128 equipment, 2048 sprint, '
               'bits 8-10 weapon slot + 1, bits 12-13 zoom; att: [kind, what, x, y] where it looks and why; eq: '
               '[equipment, active]; inv: its guns; hp: [shield, health]',
        "think": '{"t", "id", "think": [[goal, arg, score] x6], "chose", "flags", "order", "posture", "beliefs"}: every '
                 'decision a bot makes, its top choices with scores; order: the team director\'s role for it; '
                 'beliefs: [enemy id, x, y, z, seen 0/1, source, age s]',
        "call": '{"t", "call", "team", "kind", "speaker", "zone", "pos", "heard"}: every callout, once',
        "loadout": '{"t", "id", "loadout", "why", "n", "guns"}: a bot asking for another loadout and why',
    },
    "collect.jsonl": {
        "start": '{"t", "collect": "start", "map", "game"}: once',
        "p": '{"t", "p": [row per player]}: every tick. Row: 0 id, 1 team, 2 alive, 3-5 x y z, 6 yaw, 7 pitch, '
             '8 shield, 9 health, 10 riding a vehicle, 11 carrying the flag, 12 BOT (1 = a bot, 0 = a person)',
        "gear": '{"t", "id", "wpn", "inv", "ammo", "mag", "eq", "ab", "uz"}: a person\'s guns, rounds, equipment, '
                'armor ability and zoom, on change (a shot: the magazine of the gun in hand going down)',
    },
}


def match_info(trace):
    """(map, stamp, start datetime) of a recorded match, or (None, None, None) for a hand-named trace."""
    m = re.search(r"trace_(.+)_(\d{8}-\d{6})\.jsonl$", os.path.basename(trace))
    if not m:
        return None, None, None
    return m.group(1), m.group(2), datetime.datetime.strptime(m.group(2), "%Y%m%d-%H%M%S")


def match_files(trace, logs=LOGS, mcc_temp=MCC_TEMP):
    """{part: path} of everything recorded for this match: the trace, its Data collector file (the same stamp) and
    MCC's post-game report when its time fits."""
    out = {"trace.jsonl": trace}
    mp, stamp, _ = match_info(trace)
    if mp:
        c = os.path.join(logs, f"collect_{mp}_{stamp}.jsonl")
        if os.path.exists(c):
            out["collect.jsonl"] = c
    end = os.path.getmtime(trace)
    for rep in glob.glob(os.path.join(mcc_temp, "*carnagereport*.xml")):
        if "campaign" not in os.path.basename(rep) and -120 <= os.path.getmtime(rep) - end <= 600:
            out["carnage_report.xml"] = rep
            break
    return out


def summary(trace):
    """What the match was and who played it: game, map, modes, score, length, players (human or bot)."""
    meta, bots, seen, modes, last = {}, {}, {}, Counter(), {}
    with open(trace, encoding="utf-8") as f:
        for line in f:
            if '"meta"' in line:
                d = json.loads(line)["meta"]
                meta.setdefault("map", d.get("map"))
                meta.setdefault("game", d.get("game"))
                if d.get("bot"):
                    bots[d["bot"]["id"]] = d["bot"]
            elif '"world"' in line:
                d = json.loads(line)
                modes[d.get("mode")] += 1
                last = d
                for r in d["world"]:
                    seen.setdefault(r[0], dict(team=r[1], bot=bool(r[8])))
                    seen[r[0]]["bot"] = seen[r[0]]["bot"] or bool(r[8])
    tier = {"novice": "Easy", "average": "Normal", "strong": "Heroic", "top": "Legendary", "demon": "Demon"}
    players, people = [], 0
    for pid in sorted(set(seen) | set(bots)):
        b = bots.get(pid)
        if b or seen.get(pid, {}).get("bot"):
            players.append(dict(id=pid, kind="bot", name=(b or {}).get("name", f"bot {pid}"), team=(b or seen[pid]).get("team"),
                                difficulty=tier.get((b or {}).get("tier"), (b or {}).get("tier")), play_style=(b or {}).get("pers")))
        else:
            people += 1
            players.append(dict(id=pid, kind="human", name=f"Player {people}", team=seen[pid]["team"]))
    return dict(game=meta.get("game"), map=meta.get("map"), modes=dict(modes), final_score=last.get("score"),
                score_limit=last.get("limit"), seconds=last.get("t"), players=players)


def scrub(text, names):
    """The shared copy of a text: the Windows user folder in paths -> <home>, each name in `names` -> its stand-in."""
    home = os.path.expanduser("~")
    for h in {home, home.replace("\\", "/"), home.replace("\\", "\\\\")}:
        text = text.replace(h, "<home>")
    for real, alias in names.items():
        if real:
            text = text.replace(real, alias)
    return text


def scrub_carnage(xml, keep_names=False):
    """MCC's post-game report with people made anonymous: Xbox ids removed; gamertag, clan tag and service tag
    "Player N" / "" unless keep_names. Bots (botcore's 0xB07B07B0 ids) stay as they are. Returns (xml, {gamertag: alias})."""
    names, n = {}, 0

    def one(m):
        nonlocal n
        tag = m.group(0)
        xuid = re.search(r'mXboxUserId="([^"]*)"', tag)
        if xuid and xuid.group(1).upper().startswith(BOT_XUID.upper()):
            return tag
        n += 1
        tag = re.sub(r'mXboxUserId="[^"]*"', 'mXboxUserId="0x0"', tag)
        if not keep_names:
            gt = re.search(r'mGamertagText="([^"]*)"', tag)
            if gt and gt.group(1):
                names[gt.group(1)] = f"Player {n}"
            tag = re.sub(r'mGamertagText="[^"]*"', f'mGamertagText="Player {n}"', tag)
            tag = re.sub(r'ClantagText="[^"]*"', 'ClantagText=""', tag)
            tag = re.sub(r'ServiceId="[^"]*"', 'ServiceId=""', tag)
        return tag
    return re.sub(r"<Player\b[^>]*>", one, xml), names


def git_version():
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%h %cs"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


README = """Project Proving Grounds: one recorded match, exported for sharing (format {fmt}).

Read manifest.json first: the match (game, map, modes, score, length), every player marked "human" (a person) or
"bot" (an AI bot of the mod, with its difficulty and play style), every file in this zip and the format of each row.
In the recordings a player is a person or a bot by the "bot" column (trace.jsonl world rows: column 8; collect.jsonl
"p" rows: column 12).

trace.jsonl: what every player did 4 times a second and what every bot did, decided and said every tick.
collect.jsonl: the people's movement, aim, guns and rounds (present when the Data collector was on; no keys).
carnage_report.xml: MCC's own post-game numbers. objective_report.txt, player_stats.json: the Observer's analyses.

People's Xbox ids are removed and their names replaced ("Player 1" ...) unless the exporter kept them.
Made with tools/match_export.py of the mod, version {ver}.
"""


def export(trace, out=None, keep_names=False, logs=LOGS, mcc_temp=MCC_TEMP):
    """Write the match's zip; returns its path."""
    files = match_files(trace, logs, mcc_temp)
    info = summary(trace)
    names, removed = {}, ["Xbox user ids"]
    carnage = None
    if "carnage_report.xml" in files:
        carnage, names = scrub_carnage(open(files["carnage_report.xml"], encoding="utf-8", errors="replace").read(), keep_names)
    if not keep_names:
        removed += ["people's gamertags, clan tags and service tags (now Player 1, Player 2 ...)"]
    removed.append("the Windows user folder in paths (now <home>)")
    analyses, errors = {}, {}
    sys.path.insert(0, HERE)
    import collector
    try:
        import objective_report
        analyses["objective_report.txt"] = "\n".join(objective_report.report(trace)) + "\n"
    except Exception as e:                       # an analysis failing must not stop the export
        errors["objective_report.txt"] = f"{type(e).__name__}: {e}"
    try:
        import player_stats
        analyses["player_stats.json"] = json.dumps(player_stats.page(player_stats.analyze(files.get("collect.jsonl", trace))), indent=1)
    except Exception as e:
        errors["player_stats.json"] = f"{type(e).__name__}: {e}"
    mp, stamp, _ = match_info(trace)
    name = f"match_{mp}_{stamp}" if mp else "match_" + os.path.basename(trace).replace(".jsonl", "")
    out = out or os.path.join(OUT_DIR, name + ("_names" if keep_names else "") + ".zip")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    ver = git_version()
    contents = {k: os.path.getsize(v) for k, v in files.items()}
    manifest = dict(format=FORMAT, made=datetime.datetime.now().isoformat(timespec="seconds"), mod_version=ver,
                    match=dict(stamp=stamp, complete=time.time() - os.path.getmtime(trace) > 15,   # still being written?
                               **{k: v for k, v in info.items() if k != "players"}), players=info["players"],
                    files={k: dict(bytes=contents.get(k), source=os.path.basename(files[k]) if k in files else "made by the exporter")
                           for k in list(files) + list(analyses)},
                    formats={k: v for k, v in FORMATS.items() if k in files}, removed_for_privacy=removed,
                    analysis_errors=errors, names_kept=keep_names)
    tmp = out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
        z.writestr("README.txt", README.format(fmt=FORMAT, ver=ver))
        for part, path in files.items():
            text = carnage if part == "carnage_report.xml" else open(path, encoding="utf-8", errors="replace").read()
            if part == "collect.jsonl":
                text = collector.without_keys(text)
            z.writestr(part, scrub(text, {} if keep_names else names))
        for part, text in analyses.items():
            z.writestr(part, scrub(text, {} if keep_names else names))
    os.replace(tmp, out)
    return out


IMPORT_PARTS = ("manifest.json", "trace.jsonl", "collect.jsonl", "carnage_report.xml", "objective_report.txt",
                "player_stats.json", "README.txt")
IMPORT_MAX = 2 << 30          # bytes unpacked at most (a long recorded match is a few hundred MB)


def import_game(data, logs=LOGS):
    """Unpacks an exported game (the zip's bytes) into logs/imported/<map>_<stamp>/, where the Observer lists it.
    Only the parts an export holds are taken, under their own names (nothing else in the zip is written). Returns the
    trace's path; ValueError when the zip is not an export."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("not a zip file")
    names = set(z.namelist())
    if not {"manifest.json", "trace.jsonl"} <= names:
        raise ValueError("not an exported game (no manifest.json and trace.jsonl)")
    if sum(i.file_size for i in z.infolist() if i.filename in IMPORT_PARTS) > IMPORT_MAX:
        raise ValueError("too big to be an exported game")
    man = json.loads(z.read("manifest.json"))
    match = man.get("match") or {}
    mp = re.sub(r"[^A-Za-z0-9_]", "", str(match.get("map") or "map"))[:40] or "map"
    stamp = str(match.get("stamp") or "")
    stamp = stamp if re.fullmatch(r"\d{8}-\d{6}", stamp) else time.strftime("%Y%m%d-%H%M%S")
    base = os.path.join(logs, "imported", f"{mp}_{stamp}")
    out, n = base, 1
    while os.path.exists(out):
        n += 1
        out = f"{base}_{n}"
    os.makedirs(out)
    for part in IMPORT_PARTS:
        if part in names:
            dst = f"trace_{mp}_{stamp}.jsonl" if part == "trace.jsonl" else part
            with open(os.path.join(out, dst), "wb") as f:
                f.write(z.read(part))
    return os.path.join(out, f"trace_{mp}_{stamp}.jsonl")


def selftest():
    """A tiny match: one person, one bot, a callout naming a path in the user's folder, a post-game report with a real
    Xbox id."""
    import tempfile
    d = tempfile.mkdtemp()
    logs, temp = os.path.join(d, "logs"), os.path.join(d, "temp")
    os.makedirs(logs)
    os.makedirs(temp)
    home = os.path.expanduser("~")
    tr = os.path.join(logs, "trace_testmap_20261024-120000.jsonl")
    with open(tr, "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 0.0, "meta": {"map": "testmap", "game": "reach", "bot": {"id": 1, "name": "Hawk", "team": 1,
                                                                                    "tier": "strong", "pers": "rusher"}}}) + "\n")
        f.write(json.dumps({"t": 0.1, "mode": "slayer", "score": {"0": 0, "1": 1}, "limit": 50, "world": [
            [0, 0, True, 1, 2, 3, 1, 1, False, False, 0, 0, 0, [], -1], [1, 1, True, 4, 5, 6, 1, 1, True, False, 0, 0, 0, [], 0]]}) + "\n")
        f.write(json.dumps({"t": 0.2, "call": "enemy", "team": 1, "kind": "sighting", "speaker": 1,
                            "note": os.path.join(home, "x")}) + "\n")
    open(os.path.join(temp, "mpcarnagereport1_3528_0_0.xml"), "w").write(
        '<Players><Player mXboxUserId="0x0009000012345678" mGamertagText="RealPerson" ClantagText="ABC" ServiceId="X42" mKills="5">'
        '</Player><Player mXboxUserId="0xB07B07B000000001" mGamertagText="Hawk" ServiceId="H" mKills="1"></Player></Players>')
    z = zipfile.ZipFile(export(tr, os.path.join(d, "out.zip"), logs=logs, mcc_temp=temp))
    names = set(z.namelist())
    assert {"manifest.json", "README.txt", "trace.jsonl", "carnage_report.xml"} <= names, names
    man = json.loads(z.read("manifest.json"))
    kinds = {p["id"]: p["kind"] for p in man["players"]}
    assert kinds == {0: "human", 1: "bot"} and man["players"][1]["difficulty"] == "Heroic", man["players"]
    xml = z.read("carnage_report.xml").decode()
    assert "0x0009000012345678" not in xml and "RealPerson" not in xml and 'mGamertagText="Player 1"' in xml, xml
    assert "0xB07B07B000000001" in xml and 'mGamertagText="Hawk"' in xml, "the bot's row was changed"
    tr_text = z.read("trace.jsonl").decode()
    assert '"call": "enemy"' in tr_text and home.replace("\\", "\\\\") not in tr_text and "<home>" in tr_text
    kept = zipfile.ZipFile(export(tr, os.path.join(d, "kept.zip"), keep_names=True, logs=logs, mcc_temp=temp))
    xml = kept.read("carnage_report.xml").decode()
    assert "RealPerson" in xml and "0x0009000012345678" not in xml, "--keep-names kept the Xbox id or lost the name"
    # import: an export comes back as a game in logs/imported, twice side by side; a zip that is not one is refused
    data = open(os.path.join(d, "out.zip"), "rb").read()
    a, b = import_game(data, logs), import_game(data, logs)
    assert os.path.basename(a) == "trace_testmap_20261024-120000.jsonl" and a != b and os.path.exists(b), (a, b)
    assert open(a, encoding="utf-8").read() == z.read("trace.jsonl").decode(), "the imported trace changed"
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as w:
        w.writestr("../evil.txt", "x")
    for junk in (b"not a zip", bad.getvalue()):
        try:
            import_game(junk, logs)
            raise AssertionError("a zip that is not an export was imported")
        except ValueError:
            pass
    assert not os.path.exists(os.path.join(d, "evil.txt"))


def main():
    selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--list" in sys.argv or not args:
        for p in sorted(glob.glob(os.path.join(LOGS, "trace_*_*.jsonl")), key=os.path.getmtime, reverse=True):
            if match_info(p)[0]:
                print(os.path.basename(p), f"{os.path.getsize(p) >> 20} MB", ", ".join(match_files(p)))
        return
    t = args[0]
    path = t if os.path.exists(t) else next(iter(glob.glob(os.path.join(LOGS, f"trace_*_{t}.jsonl"))), None)
    if not path:
        sys.exit(f"no match {t}")
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    t0 = time.time()
    z = export(path, out, keep_names="--keep-names" in sys.argv)
    print(f"exported {z} ({os.path.getsize(z) >> 10} KB, {time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()

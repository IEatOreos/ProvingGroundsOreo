"""Career totals for you and every bot from MCC's own post-game reports (custom, Nov 13: the owner wants a leaderboard,
"me and the bots. Kills, Deaths, Assists, K/d", and the bots' MCC Career pages to show their numbers).

Sources: every logs/trace_*.carnage.xml (tools/play.py keeps MCC's report beside each match's trace) and MCC's own
current report (%USERPROFILE%/AppData/LocalLow/MCC/Temporary/mpcarnagereport1_3528_0_0.xml). Each match is kept once,
by its GameUniqueId, in a ledger (native/bin/career/ledger.json), so the totals outlive the recording rotation that
deletes old traces with their reports. A match counts when its person (the row that is not a bot) played at least
60 s of it (a quick quit does not). A player wins a match when they finish first (mStanding 0) and not everyone does
(a draw).

Writes native/bin/career/totals.txt, one player a line: name<TAB>games<TAB>won<TAB>kills<TAB>deaths<TAB>assists<TAB>bot
(botcore's career.cpp shows a bot's on its MCC Career page). Game data: native/bin, not in git.

(custom, Nov 15) The owner: "reset all the bots stats. For a fresh restart of stats", the bots only (the owner's
totals kept). --reset-bots marks every match known so far (the ledger, after reading every report still on disk) "bots_reset":
the bots' rows of those matches no longer count, the person's still do. The matches stay in the ledger so the reports
still in logs/ are not counted again.

(custom, Nov 17) The owner: "purge the stats. Including mine ... I want everyone to start at zero". --reset-all marks
every match known so far "all_reset": no row of it counts, a person's included. The matches stay in the ledger, as with
--reset-bots, so nothing is counted again and taking the mark off would bring them back.

usage: python -I bot_career.py               update, then print the leaderboard (by K/D; --by kills|deaths|assists|games)
       python -I bot_career.py --quiet       update only (tools/play.py, in the background, as a match starts)
       python -I bot_career.py --reset-bots  update, then every bot's numbers start again from 0
       python -I bot_career.py --reset-all   update, then everyone's numbers (people's too) start again from 0
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LOGS = os.path.join(ROOT, "logs")
OUT = os.path.join(ROOT, "native", "bin", "career")
MCC_REPORT = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "LocalLow", "MCC", "Temporary",
                          "mpcarnagereport1_3528_0_0.xml")
MIN_SECONDS = 60
BOT_ID = re.compile(r"0x0*B07B07B[01]", re.I)
ATTR = re.compile(r'(\w+)="([^"]*)"')


def read_report(path):
    """(game id, [player dict]) from one carnage report, or (None, []) when it is not one."""
    try:
        x = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None, []
    gid = re.search(r'GameUniqueId="([^"]+)"', x)
    if not gid:
        return None, []
    players = []
    for m in re.finditer(r"<Player ([^>]*)>", x):
        a = dict(ATTR.findall(m.group(1)))
        try:
            players.append({
                "name": a.get("mGamertagText", ""),
                "bot": bool(BOT_ID.match(a.get("mXboxUserId", ""))),
                "team": int(a.get("mTeamId", "0")),
                "standing": int(a.get("mStanding", "0")),
                "kills": int(a.get("mKills", "0")),
                "deaths": int(a.get("mDeaths", "0")),
                "assists": int(a.get("mAssists", "0")),
                "seconds": int(a.get("mSecondsPlayed", "0")),
            })
        except ValueError:
            continue
    return gid.group(1), players


def counts(players):
    """A match counts when its person played MIN_SECONDS or more of it."""
    people = [p for p in players if not p["bot"]]
    return bool(people) and max(p["seconds"] for p in people) >= MIN_SECONDS


def update(ledger):
    """Every report not in the ledger yet, added. Returns how many were added."""
    added = 0
    paths = glob.glob(os.path.join(LOGS, "trace_*.carnage.xml")) + [MCC_REPORT]
    for path in paths:
        gid, players = read_report(path)
        if not gid or gid in ledger or not players:
            continue
        ledger[gid] = {"file": os.path.basename(path), "time": os.path.getmtime(path), "players": players}
        added += 1
    return added


def totals(ledger):
    """{name: {games, won, kills, deaths, assists, bot}} over the matches that count."""
    out = {}
    for match in ledger.values():
        players = match["players"]
        if not counts(players) or match.get("all_reset"):       # (--reset-all: before everyone's restart)
            continue
        draw = all(p["standing"] == 0 for p in players)
        for p in players:
            if not p["name"] or (p["bot"] and match.get("bots_reset")):   # (--reset-bots: before the bots' restart)
                continue
            t = out.setdefault(p["name"], {"games": 0, "won": 0, "kills": 0, "deaths": 0, "assists": 0,
                                           "bot": p["bot"]})
            t["games"] += 1
            t["won"] += int(p["standing"] == 0 and not draw)
            for k in ("kills", "deaths", "assists"):
                t[k] += p[k]
            t["bot"] = t["bot"] and p["bot"]          # (a name a person also played under counts as a person)
    return out


def kd(t):
    return t["kills"] / t["deaths"] if t["deaths"] else float(t["kills"])


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    ledger_path = os.path.join(OUT, "ledger.json")
    try:
        ledger = json.load(open(ledger_path, encoding="utf-8"))
    except (OSError, ValueError):
        ledger = {}
    added = update(ledger)
    reset = "--reset-bots" in argv
    reset_all = "--reset-all" in argv
    if reset or reset_all:
        for match in ledger.values():
            match["all_reset" if reset_all else "bots_reset"] = True
    if added or reset or reset_all:
        tmp = ledger_path + ".tmp"
        json.dump(ledger, open(tmp, "w", encoding="utf-8"))
        os.replace(tmp, ledger_path)
    tot = totals(ledger)
    tmp = os.path.join(OUT, "totals.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for name, t in sorted(tot.items()):
            f.write(f"{name}\t{t['games']}\t{t['won']}\t{t['kills']}\t{t['deaths']}\t{t['assists']}\t{int(t['bot'])}\n")
    os.replace(tmp, os.path.join(OUT, "totals.txt"))
    if reset:
        print(f"bots' numbers reset: {len(ledger)} matches so far no longer count for any bot")
    if reset_all:
        print(f"everyone's numbers reset: {len(ledger)} matches so far no longer count for anyone")
    if "--quiet" in argv:
        return 0
    by = argv[argv.index("--by") + 1] if "--by" in argv and argv.index("--by") + 1 < len(argv) else "kd"
    key = kd if by == "kd" else (lambda t: t[by])
    rows = sorted(tot.items(), key=lambda kv: key(kv[1]), reverse=True)
    counted = sum(1 for m in ledger.values() if counts(m["players"]))
    print(f"{counted} matches ({len(ledger)} kept, {added} new); by {by}")
    print(f"{'#':>3}  {'Player':<16} {'Games':>5} {'Won':>4} {'Kills':>6} {'Deaths':>6} {'Assists':>7} {'K/D':>5}")
    for i, (name, t) in enumerate(rows, 1):
        print(f"{i:>3}  {name + ('' if t['bot'] else ' *'):<16} {t['games']:>5} {t['won']:>4} {t['kills']:>6} "
              f"{t['deaths']:>6} {t['assists']:>7} {kd(t):>5.2f}")
    print("* a person")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

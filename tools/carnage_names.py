"""Bots' names, service tags and teams in MCC's carnage report.

MCC's post-game screen and the lobby's Carnage Report read %USERPROFILE%/AppData/LocalLow/MCC/Temporary/
mpcarnagereport1_3528_0_0.xml (a fresh MCC shows the last match from it), and MCC fills each player's gamertag,
tags and team there from its own records by Xbox id: a bot's made-up id (botcore: 0xB07B07B0000000<player index>)
gives a blank name, clan tag UNSC, service id 117 and team 0 (Reach, every row red). This writes the bot's name,
its in-game service tag (botcore's hr_bot_tag) and its team from the match's trace (bot ids are player indexes),
in the player's row format (gamertag, no clan tag, service tag). Other rows are left as they are.

usage: python -I carnage_names.py [trace.jsonl] [report.xml] [--wait S]   (defaults: the newest trace, MCC's report;
       --wait: up to S seconds for MCC to write this match's report, newer than the trace; tools/play.py after a match)

Seen: a fresh MCC's Carnage Report shows the names and team colours from the file; a running MCC keeps its own copy
from the match (still blank until MCC restarts: its in-memory records are not patched yet).
"""
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
REPORT = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "LocalLow", "MCC", "Temporary",
                      "mpcarnagereport1_3528_0_0.xml")
BOT_ID = re.compile(r'mXboxUserId="0xB07B07B0([0-9A-Fa-f]{8})"')


def bot_tag(name):
    """botcore's hr_bot_tag: capitals and digits (4 at most), topped up to 3 with the letters after the first."""
    tag = [c for c in name if c.isupper() or c.isdigit()][:4]
    for c in name[1:]:
        if len(tag) >= 3:
            break
        if c.islower():
            tag.append(c.upper())
    return "".join(tag)


def bots_of(trace):
    out = {}
    with open(trace) as f:
        for line in f:
            if '"meta"' not in line:
                if out and '"world"' in line:
                    break
                continue
            b = json.loads(line)["meta"].get("bot")
            if b:
                out[b["id"]] = (b["name"], b["team"])
    return out


def fix(xml, bots, clan_of=lambda name: ""):
    """Bot rows MCC left blank get their name, clan tag (clan_of), service tag and team; a row MCC named already
    (botcore's hooks fill names, tags and emblems in the match: native/report.cpp) stays as MCC wrote it."""
    def one(m):
        tag = m.group(0)
        idx = BOT_ID.search(tag)
        if not idx or int(idx.group(1), 16) not in bots or 'mGamertagText=""' not in tag:
            return tag
        name, team = bots[int(idx.group(1), 16)]
        for attr, value in (("mGamertagText", name), ("ClantagText", clan_of(name)), ("ServiceId", bot_tag(name)),
                            ("mTeamId", str(team))):
            tag = re.sub(rf'{attr}="[^"]*"', f'{attr}="{value}"', tag, count=1)
        return tag
    return re.sub(r"<Player [^>]*>", one, xml)


def main():
    wait = float(sys.argv[sys.argv.index("--wait") + 1]) if "--wait" in sys.argv else 0.0
    args = [a for k, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[k - 1] != "--wait"]
    trace = args[0] if args else max(glob.glob(os.path.join(ROOT, "logs", "trace_*.jsonl")), key=os.path.getmtime)
    report = args[1] if len(args) > 1 else REPORT
    t0 = time.time()
    while wait and not (os.path.exists(report) and os.path.getmtime(report) > os.path.getctime(trace)):
        if time.time() - t0 > wait:
            print("no report for this match (quit before the end?): nothing to change")
            return
        time.sleep(1)
    bots = bots_of(trace)
    xml = open(report, encoding="utf-8").read()
    sys.path.insert(0, ROOT)
    from brain import looks
    new = fix(xml, bots, looks.clan_of)
    if new != xml:
        open(report, "w", encoding="utf-8", newline="").write(new)
    print(f"{len(BOT_ID.findall(xml))} bot rows, {len(bots)} names from {os.path.basename(trace)}: "
          + ("rewritten" if new != xml else "nothing to change"))


if __name__ == "__main__":
    main()

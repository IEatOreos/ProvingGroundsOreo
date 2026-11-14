"""tools/bot_career.py: the ledger keeps each match once, quick quits do not count, wins and draws, the totals file."""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bot_career", os.path.join(HERE, "bot_career.py"))
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


def report(gid, rows):
    players = "".join(
        f'<Player mXboxUserId="{xid}" mGamertagText="{name}" mTeamId="{team}" Score="0" mStanding="{standing}" '
        f'mKills="{k}" mDeaths="{d}" mAssists="{a}" mSecondsPlayed="{sec}">\n</Player>\n'
        for xid, name, team, standing, k, d, a, sec in rows)
    return (f'<?xml version="1.0"?>\n<MultiplayerCarnageReport>\n<GameUniqueId GameUniqueId="{gid}"/>\n'
            f"<Players>\n{players}</Players>\n</MultiplayerCarnageReport>\n")


ME = "0x0009000000000001"


def bot(i):
    return f"0xB07B07B00000000{i}"


def run(files):
    with tempfile.TemporaryDirectory() as tmp:
        logs, out = os.path.join(tmp, "logs"), os.path.join(tmp, "out")
        os.makedirs(logs)
        for name, text in files.items():
            open(os.path.join(logs, name), "w", encoding="utf-8").write(text)
        bc.LOGS, bc.OUT, bc.MCC_REPORT = logs, out, os.path.join(tmp, "none.xml")
        assert bc.main(["--quiet"]) == 0
        rows = {}
        for line in open(os.path.join(out, "totals.txt"), encoding="utf-8"):
            name, *n = line.rstrip("\n").split("\t")
            rows[name] = list(map(int, n))
        return rows


def test_totals_wins_and_quick_quits():
    a = report("g1", [(ME, "Me", 0, 0, 10, 4, 2, 600), (bot(1), "Wheezy", 1, 1, 4, 10, 1, 600)])
    b = report("g2", [(ME, "Me", 0, 1, 3, 5, 0, 300), (bot(1), "Wheezy", 1, 0, 5, 3, 2, 300)])
    quit_ = report("g3", [(ME, "Me", 0, 0, 0, 0, 0, 6), (bot(1), "Wheezy", 1, 0, 0, 0, 0, 6)])
    draw = report("g4", [(ME, "Me", 0, 0, 1, 1, 0, 120), (bot(1), "Wheezy", 1, 0, 1, 1, 0, 120)])
    rows = run({"trace_a.carnage.xml": a, "trace_b.carnage.xml": b, "trace_c.carnage.xml": quit_,
                "trace_d.carnage.xml": draw, "trace_a2.carnage.xml": a})       # (the same match twice: kept once)
    # games, won, kills, deaths, assists, bot
    assert rows["Me"] == [3, 1, 14, 10, 2, 0], rows
    assert rows["Wheezy"] == [3, 1, 10, 14, 3, 1], rows


def test_ledger_outlives_deleted_reports():
    a = report("g1", [(ME, "Me", 0, 0, 7, 2, 1, 600), (bot(2), "Oreo", 1, 1, 2, 7, 0, 600)])
    with tempfile.TemporaryDirectory() as tmp:
        logs, out = os.path.join(tmp, "logs"), os.path.join(tmp, "out")
        os.makedirs(logs)
        path = os.path.join(logs, "trace_a.carnage.xml")
        open(path, "w", encoding="utf-8").write(a)
        bc.LOGS, bc.OUT, bc.MCC_REPORT = logs, out, os.path.join(tmp, "none.xml")
        bc.main(["--quiet"])
        os.remove(path)                                                        # (the recording rotation took it)
        bc.main(["--quiet"])
        text = open(os.path.join(out, "totals.txt"), encoding="utf-8").read()
        assert "Oreo\t1\t0\t2\t7\t0\t1" in text, text


if __name__ == "__main__":
    test_totals_wins_and_quick_quits()
    test_ledger_outlives_deleted_reports()
    print("ok")

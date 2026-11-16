"""tools/service_record.py: the leaderboard equals bot_career's totals, the bots' restart, who is listed, the rates and
their formats, the rank table and credits, game type families, a report kept in full after the rotation, bad reports."""
import importlib.util
import json
import os
import struct
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("service_record", os.path.join(HERE, "service_record.py"))
sr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sr)
bc = sr.career

ME = "0x0009000000000001"
FRIEND = "0x0009000000000002"


def bot(i):
    return f"0xB07B07B0000000{i:02d}"


def row(xid, name, team, standing, k, d, a, sec, **more):
    return dict(xid=xid, name=name, team=team, standing=standing, k=k, d=d, a=a, sec=sec, **more)


def report(gid, rows, gametype="TU TEAM SLAYER DMR", game=6):
    players = ""
    for r in rows:
        most, by = r.get("most", (0, 0)), r.get("by", (0, 0))
        medals = "".join(f'<Medal mId="{i}" mCount="{n}"/>' for i, n in r.get("medals", {}).items())
        players += (
            f'<Player mXboxUserId="{r["xid"]}" mGamertagText="{r["name"]}" ClantagText="{r.get("clan", "")}" '
            f'mTeamId="{r["team"]}" Score="{r.get("score", 0)}" mStanding="{r["standing"]}" '
            f'mTotalMedalCount="{sum(r.get("medals", {}).values())}" mKills="{r["k"]}" mDeaths="{r["d"]}" '
            f'mAssists="{r["a"]}" mBetrayals="{r.get("betrayals", 0)}" mSuicides="0" '
            f'mMostKillsInARow="{r.get("spree", 0)}" mSecondsAlive="{r["sec"]}" mKillsWeapon="{r["k"]}" '
            f'mKillsGrenade="0" mKillsMelee="0" mKillsOther="0" mSecondsPlayed="{r["sec"]}" '
            f'mKilledMostPlayerIndex="{most[0]}" mKilledMostPlayerCount="{most[1]}" '
            f'mMostKilledByPlayerIndex="{by[0]}" mMostKilledByPlayerCount="{by[1]}">\n'
            f"<MedalsCount><Medal mId=\"0\" mCount=\"0\"/>{medals}</MedalsCount>\n</Player>\n")
    return (f'<?xml version="1.0"?>\n<MultiplayerCarnageReport>\n<GameEnum mGameEnum="{game}"/>\n'
            f'<IsTeamsEnabled IsTeamsEnabled="true"/>\n<GameTypeName GameTypeName="{gametype}"/>\n'
            f'<GameUniqueId GameUniqueId="{gid}"/>\n<Players>\n{players}</Players>\n</MultiplayerCarnageReport>\n')


class World:
    """A made-up install in a temporary folder: logs with reports, the career ledger, this tool's store and site."""

    def __init__(s, tmp):
        s.logs, s.career_out = os.path.join(tmp, "logs"), os.path.join(tmp, "career")
        os.makedirs(s.logs)
        s.paths = sr.Paths(logs=s.logs, ledger=os.path.join(s.career_out, "ledger.json"),
                           store=os.path.join(tmp, "store"), out=os.path.join(tmp, "site"),
                           profiles=os.path.join(tmp, "bot_profiles.ini"), looks=os.path.join(tmp, "bot_looks.ini"),
                           pool=os.path.join(tmp, "bot_pool_saved.ini"), emblems=os.path.join(tmp, "emblems"),
                           look_names=os.path.join(tmp, "look_names.h"), mcc_report=os.path.join(tmp, "none.xml"))

    def write(s, name, text):
        with open(os.path.join(s.logs, name), "w", encoding="utf-8") as f:
            f.write(text)

    def career(s, *args):
        bc.LOGS, bc.OUT, bc.MCC_REPORT = s.logs, s.career_out, s.paths.mcc_report
        assert bc.main(["--quiet", *args]) == 0

    def totals(s):
        rows = {}
        with open(os.path.join(s.career_out, "totals.txt"), encoding="utf-8") as f:
            for line in f:
                name, *n = line.rstrip("\n").split("\t")
                rows[name] = list(map(int, n))
        return rows

    def build(s):
        sr.build(s.paths)
        with open(os.path.join(s.paths.out, "data.js"), encoding="utf-8") as f:
            text = f.read()
        assert text.startswith("window.SR_DATA = ") and text.rstrip().endswith(";"), text[:40]
        return json.loads(text[len("window.SR_DATA = "):].rstrip().rstrip(";"))


def player(data, name):
    return next(p for p in data["players"] if p["name"] == name)


def test_leaderboard_equals_totals():
    """Every listed player's games, wins, kills, deaths and assists over every game equal totals.txt; people are in
    totals.txt and not on the site; a quick quit and a draw count as bot_career counts them."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600), row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600),
            row(bot(2), "Oreo", 0, 0, 6, 0, 3, 600)]))
        w.write("trace_h4_wraparound_20261115-181500.carnage.xml", report("g2", [
            row(ME, "Me", 0, 1, 3, 5, 0, 300), row(bot(1), "Wheezy", 1, 0, 5, 3, 2, 300)], "Infinity Slayer", 3))
        w.write("trace_reach_forge_halo_20261115-183000.carnage.xml", report("g3", [      # a quick quit: not counted
            row(ME, "Me", 0, 0, 0, 0, 0, 6), row(bot(1), "Wheezy", 1, 0, 9, 9, 9, 6)]))
        w.write("trace_reach_forge_halo_20261115-184500.carnage.xml", report("g4", [      # a draw: nobody wins
            row(ME, "Me", 0, 0, 1, 1, 0, 120), row(bot(1), "Wheezy", 0, 0, 1, 1, 0, 120)]))
        w.career()
        data, totals = w.build(), w.totals()
        assert "Me" in totals and [p["name"] for p in data["players"]] == ["Oreo", "Wheezy"], data["players"]
        for p in data["players"]:
            s = p["g"]["all"]["cats"]["all"]
            got = [s["games"], s["wins"], s["kills"], s["deaths"], s["assists"]]
            assert got == totals[p["name"]][:5] and totals[p["name"]][5] == 1, (p["name"], got, totals[p["name"]])
        wheezy = player(data, "Wheezy")
        assert wheezy["g"]["reach"]["cats"]["all"]["games"] == 2 and wheezy["g"]["h4"]["cats"]["all"]["games"] == 1
        assert [g[0] for g in data["games"]] == ["all", "reach", "h4"], data["games"]
        assert len(data["matches"]) == 3 and data["matches"][0]["id"] == "g4", [m["id"] for m in data["matches"]]


def test_zero_deaths_and_rate_formats():
    """A player with no deaths has a K/D of their kills; the rates have 2 places; playtime reads 13d 3h 36m."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600, medals={8: 3, 111: 2})]))
        w.career()
        s = player(w.build(), "Oreo")["g"]["reach"]["cats"]["all"]
        assert s["deaths"] == 0 and s["r"]["kd"] == 7.0, s["r"]
        assert s["r"]["kpg"] == 7.0 and s["r"]["dpg"] == 0.0 and s["r"]["kph"] == 42.0 and s["r"]["mph"] == 30.0, s["r"]
        assert s["r"]["playtime"] == "0d 0h 10m" and s["r"]["mpg"] == 5.0 and s["r"]["win"] == 100.0, s["r"]
    assert sr.playtime(13 * 86400 + 3 * 3600 + 36 * 60 + 59) == "13d 3h 36m"
    third = sr.blank() | {"games": 3, "kills": 10, "deaths": 3, "seconds": 0}
    assert sr.rates(third)["kd"] == 3.33 and sr.rates(third)["kph"] is None, sr.rates(third)
    assert sr.rates(sr.blank())["kd"] == 0.0 and sr.rates(sr.blank())["kpg"] is None


def test_bots_restart_and_roster():
    """A bot's row from before the restart is not on the site (its match neither, when no listed row of it counts);
    every bot of bot_profiles.ini is listed at 0; a pool bot appears with its first counted match."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        with open(w.paths.profiles, "w", encoding="utf-8") as f:
            f.write("; bots\nexperience=original\nbot=Wheezy,123,AYS\nbot=Skillful,456,Im,h4.primary=17\n")
        with open(w.paths.pool, "w", encoding="utf-8") as f:
            f.write("next=3\nsaved=demon,objector,Wheezy\n")
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600), row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600)]))
        w.career("--reset-bots")
        data = w.build()
        assert [p["name"] for p in data["players"]] == ["Skillful", "Wheezy"] and data["matches"] == [], data
        wheezy = player(data, "Wheezy")
        assert wheezy["g"] == {} and wheezy["cr"] == 0 and wheezy["rank"] == 0 and wheezy["roster"], wheezy
        assert (wheezy["clan"], wheezy["difficulty"], wheezy["style"]) == ("AYS", "demon", "objector"), wheezy
        w.write("trace_reach_70_boneyard_20261115-190000.carnage.xml", report("g2", [
            row(ME, "Me", 0, 1, 3, 5, 0, 300), row(bot(1), "Wheezy", 1, 0, 5, 3, 2, 300),
            row(bot(7), "PoolBot", 1, 0, 2, 2, 0, 300, clan="WAVE")]))
        w.career()
        data = w.build()
        assert [p["name"] for p in data["players"]] == ["PoolBot", "Skillful", "Wheezy"]
        s = player(data, "Wheezy")["g"]["all"]["cats"]["all"]
        assert [s["games"], s["wins"], s["kills"]] == w.totals()["Wheezy"][:3] == [1, 1, 5], s
        pool = player(data, "PoolBot")
        assert not pool["roster"] and pool["clan"] == "WAVE" and len(data["matches"]) == 1, pool


def test_people_stay_off_the_lists():
    """Gamertags are on a match's scoreboard, never in the player list; only a listed row links to a record."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600), row(FRIEND, "A Friend", 0, 0, 2, 2, 2, 600),
            row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600)]))
        w.career()
        data = w.build()
        assert [p["name"] for p in data["players"]] == ["Wheezy"]
        rows = {r["n"]: r for r in data["matches"][0]["rows"]}
        assert set(rows) == {"Me", "A Friend", "Wheezy"}, rows
        assert rows["Wheezy"]["listed"] and not rows["Me"]["listed"] and not rows["A Friend"]["listed"], rows
        assert rows["Me"]["won"] and not rows["Wheezy"]["won"]


def test_rank_table_and_credits():
    worth, steps = sr.load_ranks()
    by = {s[0]: s[3] for s in steps}
    assert by["Brigadier"] - by["Colonel Grade 3"] == 220000, (by["Colonel Grade 3"], by["Brigadier"])
    assert by["Eclipse"] - by["Noble"] == 1500000
    assert steps[sr.rank_index(0, steps)][0] == "Recruit" and steps[sr.rank_index(7499, steps)][0] == "Recruit"
    assert steps[sr.rank_index(7500, steps)][0] == "Private" and steps[sr.rank_index(15000, steps)][0] == "Corporal Grade 1"
    assert steps[sr.rank_index(20000000, steps)][0] == "Inheritor" == steps[-1][0]
    assert steps[sr.rank_index(19999999, steps)][0] == "Reclaimer" and steps[sr.rank_index(10 ** 9, steps)][0] == "Inheritor"
    assert by["General Grade 4"] == 2650000 and len(steps) == 50 and len({s[1] for s in steps}) == 22, len(steps)
    assert worth == {"game": 1000, "win": 1000, "kill": 100, "assist": 50, "medal": 25}, worth
    s = sr.blank() | {"games": 3, "wins": 2, "kills": 40, "assists": 10, "medals": 12, "deaths": 99}
    assert sr.credits(s, worth) == 3000 + 2000 + 4000 + 500 + 300


def test_rank_from_reach_matches_only():
    """Credits come from the counted Reach matches (a Halo 4 match earns none): 1 game, 1 win, 7 kills, 3 assists,
    5 medals."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600, medals={8: 3, 111: 2})]))
        w.write("trace_h4_wraparound_20261115-181500.carnage.xml", report("g2", [
            row(ME, "Me", 0, 1, 0, 50, 0, 600), row(bot(2), "Oreo", 1, 0, 50, 0, 0, 600)], "Infinity Slayer", 3))
        w.career()
        data = w.build()
        oreo = player(data, "Oreo")
        assert oreo["cr"] == 1000 + 1000 + 700 + 150 + 125 and data["ranks"][oreo["rank"]][0] == "Recruit", oreo["cr"]
        assert oreo["g"]["all"]["cats"]["all"]["kills"] == 57


def test_families():
    for name, want in (("TU TEAM SLAYER DMR", "slayer"), ("TEAM SLAYER", "slayer"), ("Infinity Slayer", "slayer"),
                       ("Infinity Rumble", "slayer"), ("Capture The Flag", "ctf"), ("TU MULTI FLAG CTF", "ctf"),
                       ("LAND GRAB", "territories"), ("TU CRAZY KING", "koth"), ("Flood", "infection"),
                       ("HEADHUNTER", "headhunter"), ("TU STOCKPILE", "stockpile"), ("ODDBALL", "oddball"),
                       ("ONE BOMB ASSAULT", "assault"), ("INVASION SLAYER", "invasion"), ("Something New", "other"),
                       ("", "unknown")):
        assert sr.family(name) == want, (name, sr.family(name))
    assert set(k for k, _ in sr.FAMILIES) | {"other", "unknown"} == set(sr.FAMILY_NAMES)
    for map_id, want in (("reach_forge_halo", "Forge World"), ("reach_70_boneyard", "Boneyard"),
                         ("h4_ca_blood_crash", "Blood Crash"), ("h4_z05_cliffside", "Cliffside"),
                         ("h2_burial_mounds", "Burial Mounds"), ("", "Unknown map")):
        assert sr.map_name(map_id) == want, (map_id, sr.map_name(map_id))


def test_report_kept_after_the_rotation():
    """A report's detail (medals, rivals by name, map, game type) is kept in the store by its GameUniqueId and still
    on the site after the recording rotation deleted the report."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        name = "trace_reach_70_boneyard_20261115-180000.carnage.xml"
        w.write(name, report("g1", [
            row(ME, "Me", 0, 1, 2, 9, 0, 600, most=(1, 2), by=(1, 6)),
            row(bot(1), "Wheezy", 1, 0, 9, 2, 1, 600, score=9, spree=6, betrayals=1, medals={8: 1, 111: 4},
                most=(0, 6), by=(0, 2))], "TU CRAZY KING"))
        w.career()
        first = w.build()
        os.remove(os.path.join(w.logs, name))                  # (the recording rotation took it)
        w.career()
        data = w.build()
        assert data["matches"] == first["matches"] and len(data["matches"]) == 1
        m = data["matches"][0]
        assert (m["game"], m["map"], m["type"], m["cat"], m["report"], m["when"]) == (
            "reach", "reach_70_boneyard", "TU CRAZY KING", "koth", True, "2026-11-15 18:00"), m
        g = player(data, "Wheezy")["g"]["reach"]
        s = g["cats"]["koth"]
        assert (s["medals"], s["betrayals"], s["spree"], s["score"], s["detailed"]) == (5, 1, 6, 9, 1), s
        assert g["medals"] == {"8": 1, "111": 4} and g["killed"] == {"Me": [1, 6]} and g["killed_by"] == {"Me": [1, 2]}, g
        assert g["maps"]["reach_70_boneyard"]["games"] == 1 and g["types"]["TU CRAZY KING"]["wins"] == 1
        assert g["streak"] == {"best": 1, "current": 1, "runs": [1]} and g["matches"] == [0], g["streak"]
        assert set(data["medals"]) == {"8", "111"} and data["medals"]["8"] == {"name": "Medal 8", "icon": None}


def test_bad_reports_and_no_ledger():
    """Something that is not a report, a report cut short and a missing ledger: skipped, the site still builds."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        data = w.build()                                       # (no ledger, no reports)
        assert data["players"] == [] and data["matches"] == [] and data["games"] == [["all", "All games"], ["reach", "Reach"]]
        w.write("trace_reach_forge_halo_20261115-170000.carnage.xml", "not xml at all")
        w.write("trace_reach_forge_halo_20261115-171000.carnage.xml",
                '<MultiplayerCarnageReport><GameUniqueId GameUniqueId="cut"/><Players><Player mGamertagText="Hal')
        good = report("g1", [row(ME, "Me", 0, 0, 1, 0, 0, 90), row(bot(1), "Wheezy", 1, 1, 0, 1, 0, 90)])
        w.write("trace_reach_forge_halo_20261115-172000.carnage.xml", good)
        w.career()
        data = w.build()
        assert [m["id"] for m in data["matches"]] == ["g1"] and [p["name"] for p in data["players"]] == ["Wheezy"]
        assert sr.read_report(os.path.join(w.logs, "nothing_here.xml")) == (None, None)
        for name in ("index.html", "style.css", "app.js", "data.js", "stamp.js"):
            assert os.path.getsize(os.path.join(w.paths.out, name)) > 0, name
        assert sr.wait_ledger(w.paths, 0) is True
        w.write("trace_reach_forge_halo_20261115-173000.carnage.xml", good.replace("g1", "g9"))
        assert sr.wait_ledger(w.paths, 0) is False             # (a report bot_career has not added yet)


def test_looks_by_piece_name():
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        with open(w.paths.look_names, "w", encoding="utf-8") as f:
            f.write('static const piece ED_REACH_HELMET[] = { {0, "Mark V [B]"}, {62, "EVA[C] / CNM"},\n'
                    '    {4, "CQC / CBRN"} };\nstatic const int ED_REACH_HELMET_ORIGINAL = 3;\n'
                    'static const piece ED_REACH_VISOR[] = { {0, "Default"}, {2, "Blue"} };\n'
                    'static const piece ED_REACH_ELITE_ARMOR[] = { {5, "General"} };\n')
        with open(w.paths.looks, "w", encoding="utf-8") as f:
            f.write("; looks\nLilWraith|ce|own|color=2\n"
                    "LilWraith|reach|own|species=0;helmet=62;visor=2;chest=99;pieces=arms:female\n"
                    "LilWraith|reach|other|species=1;helmet=4;elite_armor=5\n"
                    "Zealot|reach|own|species=1;helmet=4;elite_armor=5\n")
        names = sr.read_look_names(w.paths.look_names)
        assert names["ED_REACH_HELMET"] == {0: "Mark V [B]", 62: "EVA[C] / CNM", 4: "CQC / CBRN"}, names
        looks = sr.read_looks(w.paths.looks, names)
        assert looks["LilWraith"] == {"species": "Spartan", "pieces": [["Helmet", "EVA[C] / CNM"], ["Visor colour", "Blue"]]}
        assert looks["Zealot"] == {"species": "Elite", "pieces": [["Armor", "General"]]}, looks


def test_png():
    data = sr.png(2, 1, bytes([255, 0, 0, 255, 0, 0, 255, 128]))
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", data[16:24]) == (2, 1)
    n = struct.unpack(">I", data[33:37])[0]
    assert data[37:41] == b"IDAT" and zlib.decompress(data[41:41 + n]) == b"\0" + bytes([255, 0, 0, 255, 0, 0, 255, 128])


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
    sys.exit(0)

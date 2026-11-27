"""tools/service_record.py: the leaderboard equals bot_career's totals, the bots' restart, who is listed, the rates and
their formats, the rank table and credits, game type families, a report kept in full after the rotation, bad reports;
the kill rows (tools/kill_record.py) summed per weapon, per opponent and per map, kept after the rotation, a match
without them, bad rows, a long recording's trim, a map picture's frame; the bots' home states."""
import glob
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
                           pool=os.path.join(tmp, "bot_pool_saved.ini"), bot_pool=os.path.join(tmp, "bot_pool.txt"),
                           emblems=os.path.join(tmp, "emblems"),
                           look_names=os.path.join(tmp, "look_names.h"), mcc_report=os.path.join(tmp, "none.xml"),
                           maps=os.path.join(tmp, "maps"), snap=os.path.join(tmp, "no_figure_snap.exe"),
                           matchmaking=None)                # (every match: test_matchmaking_only has the list)

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


def test_home_states():
    """Each bot's home state (the state leaderboards) comes from its name alone: the same name always lands in the same
    state (pinned, so a change to states.json or the picking that would move the bots fails here), the picks follow
    the population weights, every state has one of the four regions, and the site names every bot's state and the
    vehicle damage types."""
    regions, states = sr.load_states()
    assert [r[0] for r in regions] == ["northeast", "midwest", "south", "west"] and len(states) == 50, regions
    assert len({s[0] for s in states}) == 50 and {s[2] for s in states} == {r[0] for r in regions}
    pinned = {"Oreo": "CO", "OutlawMarine": "AZ", "LilWraith": "KY", "Lord117": "CA", "Ice": "IL", "V4nt4R1ot": "IA"}
    assert {n: sr.home_state(n, states) for n in pinned} == pinned
    picks = [sr.home_state(f"Bot{i}", states) for i in range(20000)]
    total = sum(s[3] for s in states)
    for code, weight in (("CA", 39538), ("TX", 29146), ("WY", 577)):
        share = picks.count(code) / len(picks)
        assert abs(share - weight / total) < 0.012, (code, share, weight / total)
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600)]))
        w.career()
        data = w.build()
        assert player(data, "Oreo")["state"] == "CO" and data["states"]["CO"] == ["Colorado", "west"], data["states"]["CO"]
        assert all(p["state"] in data["states"] for p in data["players"])
        assert data["regions"] == regions and "reach:29" in data["vehicles"] and "reach:6" not in data["vehicles"]
    names = sr.load_weapons()["reach"][0]
    assert all(k.split(":")[1] in names for k in sr.vehicle_keys()), sr.vehicle_keys()


def test_match_medals_and_groups():
    """Each row of a match keeps the medals its player earned in it (the carnage report's strip), and every medal the
    site names carries the old service record's group: Spree's multikills apart from its sprees, MCC's types else."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600, medals={8: 1}), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600, medals={62: 2, 111: 3})]))
        os.makedirs(os.path.join(w.paths.store, "art"))
        with open(os.path.join(w.paths.store, "art", "medals.json"), "w", encoding="utf-8") as f:
            json.dump({"62": {"name": "Double Kill", "icon": "", "kind": "Spree", "key": "medal_double_kill"},
                       "111": {"name": "Headshot", "icon": "", "kind": "Kill", "key": "medal_headshot"},
                       "8": {"name": "Assist", "icon": "", "kind": "AssistSupport", "key": "medal_assist"}}, f)
        w.career()
        data = w.build()
        rows = {r["n"]: r for r in data["matches"][0]["rows"]}
        assert rows["Oreo"]["medals"] == {"62": 2, "111": 3} and rows["Me"]["medals"] == {"8": 1}, rows
        assert data["medals"]["62"]["cat"] == "multikill" and data["medals"]["111"]["cat"] == "kill", data["medals"]
    group = sr.medal_group
    assert group({"kind": "Spree", "key": "medal_killing_spree"}) == "spree"
    assert group({"kind": "Spree", "key": "medal_killionaire"}) == "multikill"
    assert group({"kind": "KillStreak"}) == "spree" and group({"kind": "ModeSpecific"}) == "objective"
    assert group({"kind": "Style"}) == "style" and group({}) == "other" and group({"kind": "Legendary"}) == "legendary"


def test_commendations():
    """The 14 multiplayer commendations: the table reads whole (six tiers rising, six credits), a bot's counts come
    from its medals (by MCC's id and by group), its report numbers and its kill rows (None, not 0, without them),
    each tier reached adds its credits, and the rank counts them when ranks.json says so."""
    tiers, comms = sr.load_commendations()
    mp = [c for c in comms if c.get("set", "mp") == "mp"]
    assert tiers == ["Iron", "Bronze", "Silver", "Gold", "Onyx", "Max"] and len(mp) == 14, (tiers, len(mp))
    assert {c["key"] for c in comms} >= {"any_spree", "assistant", "crack_shot", "jack_of_all_trades", "one_shot", "trigger_man"}
    by = {c["key"]: c for c in comms}
    assert by["crack_shot"]["need"] == [100, 500, 4000, 10000, 20000, 32000] and by["crack_shot"]["cr"] == [300, 1000, 2000, 3000, 3000, 0]
    info = {"62": {"key": "medal_double_kill", "kind": "Spree"}, "136": {"key": "medal_killing_spree", "kind": "Spree"},
            "111": {"key": "medal_headshot", "kind": "Kill"}, "114": {"key": "medal_hijack", "kind": "Style"},
            "184": {"key": "medal_revenge", "kind": "Style"}}
    g = {"medals": {"62": 12, "136": 7, "111": 60, "114": 2, "184": 3},
         "cats": {"all": sr.blank() | {"assists": 55, "kg": 30}},
         "weapons": {"reach:6": [80, 3], "reach:8": [25, 1], "reach:5": [4, 9], "reach:29": [26, 0]}, "kill_games": 2}
    n = sr.commendation_counts(g, comms, info)
    assert (n["multikill"], n["any_spree"], n["one_shot"], n["jack_of_all_trades"]) == (12, 7, 60, 5), n
    assert (n["assistant"], n["grenadier"], n["crack_shot"], n["trigger_man"], n["mobile_asset"]) == (55, 30, 105, 4, 26), n
    assert sr.commendation_tier(105, by["crack_shot"]["need"]) == 1 and sr.commendation_tier(99, by["crack_shot"]["need"]) == 0
    assert sr.commendation_tier(32000, by["crack_shot"]["need"]) == 6
    # Iron for: Multikill (250), Any Spree (250), One Shot (150), Assistant (150), Grenadier (100), Crack Shot (300),
    # Mobile Asset (100)
    assert sr.commendation_credits(n, comms) == 250 + 250 + 150 + 150 + 100 + 300 + 100, sr.commendation_credits(n, comms)
    none = sr.commendation_counts(dict(g, kill_games=0), comms, {})
    assert none["crack_shot"] is None and none["one_shot"] is None and none["assistant"] == 55, none   # (not recorded: None)
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 60, 600, medals={111: 50})]))
        os.makedirs(os.path.join(w.paths.store, "art"))
        with open(os.path.join(w.paths.store, "art", "medals.json"), "w", encoding="utf-8") as f:
            json.dump({"111": {"name": "Headshot", "icon": "", "kind": "Kill", "key": "medal_headshot"}}, f)
        w.career()
        data = w.build()
        oreo = player(data, "Oreo")
        worth, _ = sr.load_ranks()
        base = sr.credits(oreo["g"]["reach"]["cats"]["all"], worth)
        # One Shot (50 headshots) and Assistant (60 assists) reach Iron: 150 + 150
        assert oreo["comm"]["one_shot"] == 50 and oreo["comm"]["assistant"] == 60 and oreo["comm_cr"] == 300, oreo["comm"]
        # (and, Nov 17, the challenges its match finished on that day and week)
        assert oreo["cr"] == base + 300 + oreo["chal"]["cr"] and data["commendations"]["credits"] is True, (oreo["cr"], base)
        assert len(data["commendations"]["list"]) == 25 and data["commendations"]["list"][0]["from"] in ("report", "matches", "kills")
        assert oreo["comm"]["loyal_soldier"] == 1 and oreo["comm"]["mvp"] == 0, oreo["comm"]   # (Nov 17: one game to the end)
        assert sum(c["set"] == "mp" for c in data["commendations"]["list"]) == 14 and len(data["commendations"]["badges"]) == 2


def test_proving_grounds_commendations():
    """First Blood: the match's first kill; Closer: its last kill when the killer's side won; Grudge Match: each enemy
    one player killed 5 times or more in the match. Betrayals, deaths and unnamed killers never count. Map Master
    counts the maps of its list won on. The five tiered ones are in the table with the 14 of Reach."""
    U = sr.UNNAMED
    feed = [[1, "A", "B", "reach:6", "kill"], [2, "B", "A", "reach:6", "kill"]] + [[3 + i, "A", "C", "reach:6", "kill"] for i in range(5)] + \
           [[9, "C", "A", "reach:11", "betrayal"], [10, None, "B", "reach:41", "death"], [11, "B", "C", "reach:5", "kill"]]
    assert sr.feed_feats(feed, {"B"}) == {"A": {"first": 1, "grudge": 1}, "B": {"closer": 1}}, sr.feed_feats(feed, {"B"})
    assert sr.feed_feats(feed, {"A"}) == {"A": {"first": 1, "grudge": 1}}                 # (B's last kill: B lost)
    assert sr.feed_feats([[1, U, "B", "reach:6", "kill"], [2, "B", "A", "reach:6", "kill"]], {"B"}) == {"B": {"first": 1, "closer": 1}}
    assert sr.feed_feats([], {"A"}) == {}
    _, comms = sr.load_commendations()
    keys = [c["key"] for c in comms]
    assert len(comms) == 25 and keys[14:19] == ["victor", "first_blood", "closer", "grudge_match", "medal_collector"], keys
    assert keys[19:23] == ["mvp", "game_changer", "positive_thinking", "loyal_soldier"], keys   # (Nov 17, the owner's four)
    assert keys[23:] == ["mission_first", "denied"], keys                                       # (Nov 19, the objective two)
    g = {"medals": {"8": 2, "9": 0, "111": 5}, "cats": {"all": sr.blank() | {"wins": 12, "medals": 7}}, "weapons": {}, "kill_games": 1,
         "feats": {"first": 6, "closer": 0, "grudge": 2}, "maps": {"reach_70_boneyard": {"wins": 2}, "reach_forge_halo": {"wins": 0}, "x": {"wins": 1}}}
    n = sr.commendation_counts(g, comms, {})
    assert (n["victor"], n["first_blood"], n["closer"], n["grudge_match"], n["medal_collector"]) == (12, 6, 0, 2, 7), n   # (Nov 19: every medal earned, not kinds)
    by = {c["key"]: c for c in comms}
    assert by["medal_collector"]["need"] == [250, 1000, 5000, 20000, 50000, 100000] and sr.commendation_source(by["medal_collector"]["count"]) == "report"
    assert sr.commendation_counts(dict(g, kill_games=0), comms, {})["first_blood"] is None
    badges = sr.load_badges()
    assert [b["key"] for b in badges] == ["map_master", "hometown_hero"] and len(badges[0]["maps"]) == 20
    assert set(badges[0]["maps"]) == set(sr.MAP_NAMES)
    assert sr.badge_counts(g, badges) == {"map_master": ["reach_70_boneyard"]}


def test_mvp_game_changer_positive_loyal():
    """(Nov 17) MVP: the most points in a Slayer game, ties too; Game Changer: the same in an objective game (not in
    Slayer, nor Invasion or Infection); Positive Thinking: more kills than deaths in a game played to the end; Loyal
    Soldier: a game played to the end. Points need MCC's report; without one a game counts as played to the end. The
    counts reach the commendations, from the reports (the points ones) or every counted match."""
    row = {"kills": 10, "deaths": 4}
    assert sr.match_deeds(row, {"score": 25, "completed": 1}, "slayer", 25) == {"mvp": 1, "game_changer": 0, "positive": 1, "loyal": 1}
    assert sr.match_deeds(row, {"score": 25, "completed": 1}, "ctf", 25)["game_changer"] == 1
    assert sr.match_deeds(row, {"score": 25, "completed": 1}, "invasion", 25)["game_changer"] == 0
    assert sr.match_deeds(row, {"score": 24, "completed": 1}, "slayer", 25)["mvp"] == 0             # (not the top)
    assert sr.match_deeds(row, {"score": 0, "completed": 1}, "koth", 0)["game_changer"] == 0        # (nobody scored)
    quit_ = sr.match_deeds(row, {"score": 25, "completed": 0}, "slayer", 25)
    assert quit_["positive"] == 0 and quit_["loyal"] == 0 and quit_["mvp"] == 1
    assert sr.match_deeds({"kills": 3, "deaths": 3}, {"score": 3}, "slayer", 9) == {"mvp": 0, "game_changer": 0, "positive": 0, "loyal": 1}
    assert sr.match_deeds(row, None, "slayer", 0) == {"mvp": 0, "game_changer": 0, "positive": 1, "loyal": 1}
    _, comms = sr.load_commendations()
    g = {"medals": {}, "cats": {"all": sr.blank()}, "weapons": {}, "kill_games": 0,
         "deeds": {"mvp": 3, "game_changer": 1, "positive": 7, "loyal": 30}}
    n = sr.commendation_counts(g, comms, {})
    assert (n["mvp"], n["game_changer"], n["positive_thinking"], n["loyal_soldier"]) == (3, 1, 7, 30), n
    src = {c["key"]: sr.commendation_source(c["count"]) for c in comms}
    assert (src["mvp"], src["game_changer"], src["positive_thinking"], src["loyal_soldier"]) == ("report", "report", "matches", "matches")


def test_mission_first_and_denied():
    """(Nov 19, the owner: "Do mission first, and Denied") Mission First: flags captured, bombs planted and Headhunter's
    10-skull banks by MCC's medals, plus the flags brought home in Stockpile, which is MCC's Score there (no medal says
    it). Denied: flag and bomb carrier kills by MCC's medals; a kill made with the flag is neither. Both come from the
    reports: None, not 0, while MCC's medal list has not been read. A Score outside Stockpile adds nothing."""
    assert sr.stockpile_flags({"score": 4}, "stockpile") == 4 and sr.stockpile_flags({"score": 4}, "ctf") == 0
    assert sr.stockpile_flags(None, "stockpile") == 0 and sr.stockpile_flags({"score": -1}, "stockpile") == 0
    assert sr.stockpile_flags({}, "stockpile") == 0
    _, comms = sr.load_commendations()
    by = {c["key"]: c for c in comms}
    info = {"77": {"key": "medal_flag_captured"}, "38": {"key": "medal_bomb_planted"}, "268": {"key": "medal_skullamanjaro"},
            "78": {"key": "medal_flag_carrier_kill"}, "33": {"key": "medal_bomb_carrier_kill"}, "83": {"key": "medal_flag_kill"}}
    g = {"medals": {"77": 3, "38": 2, "268": 1, "78": 9, "33": 4, "83": 6}, "cats": {"all": sr.blank()}, "weapons": {},
         "kill_games": 0, "deeds": {"stockpile": 7}}
    n = sr.commendation_counts(g, comms, info)
    assert (n["mission_first"], n["denied"]) == (3 + 2 + 1 + 7, 9 + 4), n
    assert sr.commendation_counts(dict(g, deeds={}), comms, info)["mission_first"] == 6
    none = sr.commendation_counts(g, comms, {})
    assert none["mission_first"] is None and none["denied"] is None, none
    for key in ("mission_first", "denied"):
        c = by[key]
        assert c["set"] == "pg" and sr.commendation_source(c["count"]) == "report", c
        assert c["need"] == [5, 25, 100, 500, 1500, 3000] and c["cr"] == [150, 400, 1000, 2000, 2000, 0], c
        assert sr.commendation_tier(n[key], c["need"]) == 1, (key, n[key])
    # through the build: a Stockpile game's Score is counted, a CTF game's is not (its captures are the medals)
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261119-180000.carnage.xml", report("s1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600),
            row(bot(2), "Oreo", 1, 0, 7, 0, 0, 600, score=3, medals={78: 2})], "TU STOCKPILE"))
        w.write("trace_reach_forge_halo_20261119-183000.carnage.xml", report("c1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600),
            row(bot(2), "Oreo", 1, 0, 7, 0, 0, 600, score=2, medals={77: 2, 33: 1})], "TU MULTI FLAG CTF"))
        os.makedirs(os.path.join(w.paths.store, "art"))
        with open(os.path.join(w.paths.store, "art", "medals.json"), "w", encoding="utf-8") as f:
            json.dump({i: {"name": v["key"], "icon": "", "kind": "ModeSpecific", "key": v["key"]} for i, v in info.items()}, f)
        w.career()
        oreo = player(w.build(), "Oreo")
        assert oreo["g"]["reach"]["deeds"]["stockpile"] == 3, oreo["g"]["reach"]["deeds"]
        assert (oreo["comm"]["mission_first"], oreo["comm"]["denied"]) == (3 + 2, 2 + 1), oreo["comm"]


def test_forge_layouts_and_tier_banners():
    """A match on a map with Forge layouts gets the one seen around its start whose window holds its spots (not one
    seen only at other times, not one elsewhere on the map); layouts are named by their own name, else their file,
    else when first seen. A commendation banner's grey emblem is swapped for the owner's tier emblem."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        paths = sr.Paths(maps=os.path.join(tmp, "maps"), store=os.path.join(tmp, "store"), out=os.path.join(tmp, "site"))
        def layout(vid, first, last, window, name="", mvar=None):
            d = os.path.join(tmp, "maps", "m", "variants", vid)
            os.makedirs(d)
            with open(os.path.join(d, "variant.json"), "w", encoding="utf-8") as f:
                json.dump({"first_seen": first, "last_seen": last, "window": window, "name": name, "mvar": mvar or {},
                           "pieces": [["block_1x1", 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]]}, f)
        layout("v00000001", "2026-11-01 10:00", "2026-11-16 18:30", [0, 0, 50, 50], "$Title", {"file": "hr_forgeWorld_pinnacle.mvar"})
        layout("v00000002", "2026-11-10 09:00", "2026-11-16 18:30", [100, 100, 150, 150], "HEMORRHAGE btb")
        layout("v00000003", "2026-11-01 10:00", "2026-11-02 10:00", [0, 0, 50, 50], "$X")
        assert sr.match_variant("m", "20261116-181500", [10, 10, 20, 30, 40, 40], paths) == "v00000001"
        assert sr.match_variant("m", "20261116-181500", [110, 120, 140, 130], paths) == "v00000002"
        assert sr.match_variant("m", "20261101-120000", [10, 10], paths) == "v00000001"          # (both seen then: v1 newer)
        assert sr.match_variant("m", "20261020-120000", [10, 10], paths) is None                  # (none seen yet)
        assert sr.match_variant("m", "20261116-181500", [300, 300], paths) is None                # (no window holds it)
        assert sr.match_variant("other", "20261116-181500", [10, 10], paths) is None
        assert sr.variant_title("m", "v00000001", paths) == "Pinnacle"
        assert sr.variant_title("m", "v00000002", paths) == "HEMORRHAGE btb"
        assert sr.variant_title("m", "v00000003", paths) == "Forge layout from Nov 1"
        # a banner: flat blue, a grey square emblem on its blue end; the owner's gold emblem: a solid gold disc
        art = os.path.join(paths.store, "art", "commendations")
        os.makedirs(os.path.join(art, "tiers", "gold"))
        banner = Image.new("RGBA", (286, 90), sr.BANNER_BLUE + (255,))
        banner.paste((120, 120, 120, 255), (40, 20, 90, 70))
        banner.paste((50, 50, 50, 255), (140, 0, 286, 90))
        banner.save(os.path.join(art, "x_test.png"))
        Image.new("RGBA", (448, 448), (232, 178, 60, 255)).save(os.path.join(art, "tiers", "gold", "x_test_gold.png"))
        got = sr.tier_banners(["x_test", "missing"], paths)
        assert got == {"x_test": [None, None, None, None, "commendations/x_test_gold.png", None, None]}, got
        out = Image.open(os.path.join(paths.out, "commendations", "x_test_gold.png")).convert("RGB")
        p = 7                                                   # (the drawn tier outline round it: no frame picture here)
        assert out.size == (286 + 2 * p, 90 + 2 * p) and out.getpixel((65 + p, 45 + p)) == (232, 178, 60), out.size  # (the new emblem)
        assert out.getpixel((10 + p, 45 + p)) == sr.BANNER_BLUE and out.getpixel((200 + p, 45 + p)) == (50, 50, 50)  # (the rest kept)
        assert out.getpixel((p + 143, 2)) == sr.TIER_RGB["gold"]                                                  # (the gold outline)


def test_clan_names_and_the_editor():
    """The owner's clan names: kept by the clan's tag whatever its case, tidied, cut to 40 characters, blank clears one;
    a key that is not a tag is refused. The editor takes a save only from the site on this PC (its Origin)."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = sr.Paths(store=os.path.join(tmp, "store"))
        assert sr.save_clan_name(paths, "XvX", "  Xtreme \t Velocity ") == {"xvx": "Xtreme Velocity"}
        assert sr.save_clan_name(paths, "cod", "C" * 60)["cod"] == "C" * 40
        assert sr.save_clan_name(paths, "COD", "Call\x07 of Duty")["cod"] == "Call of Duty"
        assert sr.save_clan_name(paths, "xvx", "   ") == {"cod": "Call of Duty"}
        assert sr.load_clan_names(paths) == {"cod": "Call of Duty"}
        for bad in ("", "a|b", "x" * 17):
            try:
                sr.save_clan_name(paths, bad, "name")
                raise AssertionError(f"{bad!r} taken")
            except ValueError:
                pass
        with open(os.path.join(paths.store, "clan_names.json"), "w", encoding="utf-8") as f:
            json.dump({"ok": "Fine", "bad|key": "x", "n": 5}, f)
        assert sr.load_clan_names(paths) == {"ok": "Fine"}
        # a description: line breaks kept (two in a row at most), spaces tidied, cut to 280, blank clears it
        assert sr.save_clan_about(paths, "COD", "  Slayers   only.\n\n\n\nNo  mercy. ") == {"cod": "Slayers only.\n\nNo mercy."}
        assert len(sr.save_clan_about(paths, "cod", "x" * 400)["cod"]) == 280
        assert sr.save_clan_about(paths, "cod", " \n ") == {} and sr.load_clan_about(paths) == {}
    spec2 = importlib.util.spec_from_file_location("service_record_edit", os.path.join(HERE, "service_record_edit.py"))
    ed = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(ed)
    assert ed.allowed_origin("http://localhost:8766", 8766) and ed.allowed_origin("http://127.0.0.1:8766", 8766)
    assert ed.allowed_origin(None, 8766)
    assert not ed.allowed_origin("https://evil.example", 8766) and not ed.allowed_origin("http://localhost:9999", 8766)
    assert not ed.allowed_origin("null", 8766)                       # (a page from a file or a sandbox)


def test_bot_clan_saved_in_game():
    """A bot's clan tag from the edit mode goes into bot_profiles.ini as the bots panel writes it: the bot's own line
    (its seed and looks set by hand kept), a new line for a bot without one (the seed it already wears), every other
    line as it was (line ends too), a copy of the file kept; a bad tag refused, and nothing written while MCC runs."""
    import zlib
    with tempfile.TemporaryDirectory() as tmp:
        prof = os.path.join(tmp, "bot_profiles.ini")
        before = "; note\r\nexperience=original\r\nbot=Ace,123,WAVE\r\nbot=Bo,9,,h3.model=1;reach.seed=2\r\n"
        with open(prof, "w", encoding="utf-8", newline="") as f:
            f.write(before)
        paths = sr.Paths(profiles=prof)
        assert sr.set_bot_clan(paths, "ace", " AYS ", running=False) == "AYS"
        assert sr.set_bot_clan(paths, "Bo", "Q", running=False) == "Q"
        assert sr.set_bot_clan(paths, "Newbie", "XvX", running=False) == "XvX"
        text = open(prof, encoding="utf-8", newline="").read()
        seed = zlib.crc32(b"newbie")
        assert text == ("; note\r\nexperience=original\r\nbot=Ace,123,AYS\r\nbot=Bo,9,Q,h3.model=1;reach.seed=2\r\n"
                        f"bot=Newbie,{seed},XvX\r\n"), text
        assert open(prof + ".before_site_edit", encoding="utf-8", newline="").read().count("bot=") == 2   # (as it was before the last edit)
        assert sr.set_bot_clan(paths, "Ace", "", running=False) == ""
        assert "bot=Ace,123,\r\n" in open(prof, encoding="utf-8", newline="").read()
        assert sr.read_profiles(prof)["Ace"] == "" and sr.read_profiles(prof)["Bo"] == "Q"
        for bad in ("TOOLONG", "a b", "x,y", "[q]", "a|b", "a=b", "a;b"):
            try:
                sr.set_bot_clan(paths, "Ace", bad, running=False)
                raise AssertionError(f"{bad!r} taken")
            except ValueError:
                pass
        kept = open(prof, encoding="utf-8", newline="").read()
        try:
            sr.set_bot_clan(paths, "Ace", "UNC", running=True)
            raise AssertionError("written while MCC runs")
        except PermissionError:
            pass
        assert open(prof, encoding="utf-8", newline="").read() == kept


def test_mode_icons():
    """Each family modes.json names gets its icon from the art store, copied into the site; a number this PC has no
    picture for, or one that is not a number, is left out (the page keeps its drawn badge)."""
    with tempfile.TemporaryDirectory() as tmp:
        store, site = os.path.join(tmp, "store"), os.path.join(tmp, "site")
        os.makedirs(os.path.join(store, "art", "modes"))
        for n in (12, 13):
            with open(os.path.join(store, "art", "modes", f"{n}.png"), "wb") as f:
                f.write(sr.png(1, 1, bytes(4)))
        table = os.path.join(tmp, "modes.json")
        with open(table, "w", encoding="utf-8") as f:
            json.dump({"icons": {"ctf": 12, "slayer": 13, "koth": 8, "oddball": "x"}}, f)
        got = sr.mode_pictures(sr.Paths(store=store, out=site), table)
        assert got == {"ctf": "modes/12.png", "slayer": "modes/13.png"}, got
        assert sorted(os.listdir(os.path.join(site, "modes"))) == ["12.png", "13.png"]
    real = json.load(open(os.path.join(HERE, "service_record_site", "modes.json"), encoding="utf-8"))
    assert set(real["icons"]) <= set(sr.FAMILY_NAMES) and set(real["sure"]) <= set(real["icons"]), real


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


def test_a_person_the_owner_lists():
    """(Nov 17) A gamertag named in the store's people.json is listed like a bot, as a person; anyone else is not, and
    the editor never takes a person for a bot (its clan editing writes bot_profiles.ini)."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600, clan="ME"), row(FRIEND, "A Friend", 0, 0, 2, 2, 2, 600),
            row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600)]))
        w.career()
        os.makedirs(w.paths.store, exist_ok=True)
        with open(os.path.join(w.paths.store, "people.json"), "w", encoding="utf-8") as f:
            json.dump(["Me", "Nobody Here"], f)
        data = w.build()
        assert [p["name"] for p in data["players"]] == ["Me", "Wheezy"]
        me = player(data, "Me")
        assert me["person"] and not player(data, "Wheezy")["person"] and me["clan"] == "ME"
        s = me["g"]["reach"]["cats"]["all"]
        assert (s["games"], s["wins"], s["kills"], s["deaths"]) == (1, 1, 10, 4) and me["cr"] > 0
        assert {r["n"]: r["listed"] for r in data["matches"][0]["rows"]} == {"Me": True, "A Friend": False, "Wheezy": True}
        spec = importlib.util.spec_from_file_location("service_record_edit", os.path.join(HERE, "service_record_edit.py"))
        ed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ed)
        assert ed.listed_bots(w.paths) == {"Wheezy"}


def test_everyone_restarts_at_zero():
    """(Nov 17) bot_career --reset-all: no row of a match from before counts, a listed person's neither; the roster and
    the listed person stay on the site at 0, the totals game file empties, and a new match counts again."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        with open(w.paths.profiles, "w", encoding="utf-8") as f:
            f.write("bot=Wheezy,123,AYS\n")
        os.makedirs(w.paths.store, exist_ok=True)
        with open(os.path.join(w.paths.store, "people.json"), "w", encoding="utf-8") as f:
            json.dump(["Me"], f)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600), row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600),
            row(bot(7), "PoolBot", 1, 1, 2, 2, 0, 600)]))
        w.career("--reset-all")
        assert w.totals() == {}
        data = w.build()
        assert [p["name"] for p in data["players"]] == ["Me", "Wheezy"] and data["matches"] == [], data
        for p in data["players"]:
            assert p["g"] == {} and p["cr"] == 0 and p["rank"] == 0, p
        assert player(data, "Me")["person"]
        w.write("trace_reach_70_boneyard_20261115-190000.carnage.xml", report("g2", [
            row(ME, "Me", 0, 0, 3, 5, 0, 300), row(bot(1), "Wheezy", 1, 1, 5, 3, 2, 300)]))
        w.career()
        data = w.build()
        assert w.totals()["Me"][:3] == [1, 1, 3] and w.totals()["Wheezy"][:3] == [1, 0, 5]
        s = player(data, "Me")["g"]["all"]["cats"]["all"]
        assert (s["games"], s["kills"]) == (1, 3) and len(data["matches"]) == 1
        # (Nov 17) every bot of the matchmaking pool listed, at 0 until it plays: one line each however it is queued
        with open(w.paths.bot_pool, "w", encoding="utf-8") as f:
            f.write("# Bot Matchmaking's pool\nWheezy\nQuietRider\nQuietRider\nClanMate*3\n; a note\nAVeryLongBotNameIndeed\n\n")
        assert sr.read_pool_names(w.paths.bot_pool) == ["Wheezy", "QuietRider", "ClanMate", "AVeryLongBotNam"]
        data = w.build()
        assert [p["name"] for p in data["players"]] == ["AVeryLongBotNam", "ClanMate", "Me", "QuietRider", "Wheezy"]
        assert player(data, "QuietRider")["g"] == {} and not player(data, "QuietRider")["person"]
        # the edit mode's Reset all: refused while MCC runs, else a copy of the ledger kept and everyone at 0 again
        try:
            sr.reset_everyone(running=True)
            assert False, "reset while MCC runs"
        except PermissionError:
            pass
        assert w.totals()["Me"][0] == 1
        assert sr.reset_everyone(running=False) == 2 and w.totals() == {}
        copies = glob.glob(os.path.join(w.career_out, "ledger.before_reset_all_*.json"))
        assert len(copies) == 1 and len(json.load(open(copies[0], encoding="utf-8"))) == 2
        assert not json.load(open(copies[0], encoding="utf-8"))["g2"].get("all_reset")
        assert w.build()["matches"] == []


def test_matchmaking_only():
    """(Nov 17, the owner: "Matchmaking only") the site shows only the matches Project Noble named in its list: a
    custom game counts in totals.txt but adds no match, no stats and no bot to the site; no list yet, no matches. The
    game writes the list where the site reads it, by MCC's GameUniqueId."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.paths.matchmaking = os.path.join(w.paths.store, "matchmaking.txt")
        w.write("trace_reach_forge_halo_20261117-180000.carnage.xml", report("pg-1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600), row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600)]))
        w.write("trace_reach_70_boneyard_20261117-183000.carnage.xml", report("custom-1", [
            row(ME, "Me", 0, 0, 9, 1, 0, 600), row(bot(1), "Wheezy", 1, 1, 1, 9, 0, 600),
            row(bot(3), "CustomOnly", 1, 1, 0, 0, 0, 600)]))
        w.career()
        assert w.totals()["Wheezy"][0] == 2 and "CustomOnly" in w.totals()
        data = w.build()
        assert data["matches"] == [] and data["players"] == [], data["players"]
        os.makedirs(w.paths.store, exist_ok=True)
        with open(w.paths.matchmaking, "w", encoding="utf-8") as f:
            f.write("# The matches Project Noble started\npg-1\t2026-11-17 18:00\tARENA\n\n")
        assert sr.load_matchmaking(w.paths.matchmaking) == {"pg-1"} and sr.load_matchmaking(None) is None
        data = w.build()
        assert [m["id"] for m in data["matches"]] == ["pg-1"] and [p["name"] for p in data["players"]] == ["Wheezy"]
        s = player(data, "Wheezy")["g"]["all"]["cats"]["all"]
        assert (s["games"], s["kills"], s["deaths"]) == (1, 4, 10), s
    with open(os.path.join(HERE, "..", "native", "proving_grounds.cpp"), encoding="utf-8") as f:
        cpp = f.read()
    assert 'L"%s\\\\service_record"' in cpp and 'L"%s\\\\matchmaking.txt"' in cpp and "GameUniqueId=" in cpp
    assert sr.Paths().matchmaking == os.path.join(sr.BIN, "service_record", "matchmaking.txt")


def test_game_reads_the_sites_challenges():
    """(Nov 17, the challenges in game: "They have to be connected") <site>/challenges.txt holds what data.js holds:
    this week's weekly then today's dailies in the site's order with their names, targets, cR, icons and ends, and each
    listed person's completed counts, challenge cR and progress on the live ones; the game reads it where it is written."""
    import time as _time
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        os.makedirs(w.paths.store, exist_ok=True)
        with open(os.path.join(w.paths.store, "people.json"), "w", encoding="utf-8") as f:
            json.dump(["Me"], f)
        w.write(f"trace_reach_forge_halo_{_time.strftime('%Y%m%d-%H%M%S')}.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 25, 2, 4, 600), row(bot(1), "Wheezy", 1, 1, 2, 25, 0, 600)]))
        w.career()
        data = w.build()
        with open(os.path.join(w.paths.out, "challenges.txt"), encoding="utf-8") as f:
            rows = [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    C, me = data["challenges"], player(data, "Me")
    by = {c["key"]: c for c in C["list"]}
    want = []
    for period in ("weekly", "daily"):
        want.append(["period", period, C[period]["start"], str(int(C[period]["ends"]))])
        want += [["challenge", period, k, by[k]["name"], by[k]["what"], str(by[k]["need"]), str(by[k]["cr"]), by[k]["icon"]]
                 for k in C[period]["keys"]]
    want.append(["person", "Me", str(me["chal"]["daily_done"]), str(me["chal"]["weekly_done"]), str(me["chal"]["cr"])])
    want += [["progress", "Me", k, str(n)] for k, n in me["chal"]["now"].items()]
    assert rows == want, (rows, want)
    assert any(r[0] == "progress" and r[3] != "0" for r in rows) or not me["chal"]["now"], rows   # (the match counted)
    with open(os.path.join(HERE, "..", "native", "proving_grounds.cpp"), encoding="utf-8") as f:
        cpp = f.read()
    assert "\\\\logs\\\\service_record\\\\challenges.txt" in cpp and "\\\\logs\\\\service_record\\\\icons\\\\%S.png" in cpp


def test_carnage_of_the_last_match():
    """(Nov 23, the owner's Reach carnage report after the credits) last_carnage.txt: the newest match a person played,
    the teams by place with their scores, each player's numbers, service tag and emblem from MCC's own report, the
    Headshot medals as headshots, the credits the match earned, who they killed most and were killed most by, their
    medals, and the three Top Medals; nothing when no person played."""
    def lines(w):
        with open(os.path.join(w.paths.out, "last_carnage.txt"), encoding="utf-8") as f:
            return [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261123-170000.carnage.xml", report("bots-only", [
            row(bot(1), "Wheezy", 1, 0, 4, 1, 1, 600), row(bot(2), "Oreo", 0, 1, 1, 4, 0, 600)]))
        w.career()
        w.build()
        assert not os.path.exists(os.path.join(w.paths.out, "last_carnage.txt"))   # (no person played it)
        text = report("pg-9", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600, score=50, spree=6, most=(1, 4), by=(1, 2), medals={111: 2, 135: 1, 8: 3}),
            row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600, score=20, most=(0, 2), by=(0, 4), medals={74: 1})])
        text = text.replace('mGamertagText="Wheezy"', 'mGamertagText="Wheezy" ServiceId="WZ" EmblemTexture0="5" '
                            'EmblemTexture1="505" EmblemColor0="2" EmblemColor1="31" EmblemColor2="9" '
                            'mCompletedGame="0"')     # (Nov 23: Wheezy quit, for the skill ratings)
        # (Nov 23) each medal's what-for, by its MCC key (the art store's medals.json) from medal_info.json
        os.makedirs(os.path.join(w.paths.store, "art"), exist_ok=True)
        with open(os.path.join(w.paths.store, "art", "medals.json"), "w", encoding="utf-8") as f:
            json.dump({"135": {"key": "medal_killing_frenzy", "name": "Killing Frenzy"},   # (no kinds: the order
                       "111": {"key": "medal_headshot", "name": "Headshot"},              # checked below is by count)
                       "8": {"key": "medal_assist", "name": "Assist"},
                       "74": {"key": "medal_not_written", "name": "First Strike"}}, f)
        w.write("trace_reach_forge_halo_20261123-180000.carnage.xml", text)
        w.career()
        data = w.build()
        got = lines(w)
        assert got[0] == ["match", "pg-9"] and got[1] == ["game", "TU TEAM SLAYER DMR", "1", "reach_forge_halo", "Forge World"], got[:2]
        assert [l for l in got if l[0] == "team"] == [["team", "0", "1", "50"], ["team", "1", "2", "20"]], got
        players = [l for l in got if l[0] == "player"]
        assert [p[2] for p in players] == ["Me", "Wheezy"], players
        me, wz = players
        worth = data["credits"]
        assert me[5:15] == ["1", "50", "10", "4", "2", "6", "6", "2",
                            str(worth["game"] + worth["win"] + 10 * worth["kill"] + 2 * worth["assist"] + 6 * worth["medal"]), "0"], me
        assert me[20:24] == ["Wheezy", "4", "Wheezy", "2"] and wz[20:24] == ["Me", "2", "Me", "4"], (me, wz)
        assert wz[3] == "WZ" and wz[15:20] == ["5", "505", "2", "31", "9"] and wz[14] == "1", wz
        assert me[24:27] == ["", "0", ""], me                  # (no kill record: no Tool of Destruction)
        assert len(me) == 28 and me[27] == "1" and wz[27] == "0", (me, wz)   # (Nov 23: finished, quit)
        assert [l[2] for l in got if l[0] == "medal" and l[1] == "0"] == ["135", "111", "8"], got
        assert [(l[1], l[3]) for l in got if l[0] == "top"] == [("74", "1"), ("135", "0"), ("111", "0")], got
        with open(os.path.join(HERE, "service_record_site", "medal_info.json"), encoding="utf-8") as f:
            what = json.load(f)["what"]
        frenzy = next(l for l in got if l[0] == "medal" and l[2] == "135")
        assert len(frenzy) == 7 and frenzy[6] == what["medal_killing_frenzy"] == "Kill 10 enemies without dying.", frenzy
        assert next(l for l in got if l[0] == "top" and l[1] == "74")[6] == "", got   # (a medal not written: no text)
        assert all(v.strip() and v.endswith(".") and "\t" not in v for v in what.values()) and len(what) >= 56
        # (the owner's 12 s test game) a game too short to count: the credits told at once, its carnage report shown
        w.write("trace_reach_forge_halo_20261123-190000.carnage.xml", report("quick", [
            row(ME, "Me", 0, 0, 1, 0, 0, 12, medals={74: 1}), row(bot(1), "Wheezy", 1, 1, 0, 1, 0, 12)]))
        w.career()
        data = w.build()
        assert not any(m["id"] == "quick" for m in data["matches"])
        with open(os.path.join(w.paths.out, "last_match.txt"), encoding="utf-8") as f:
            assert [l for l in f.read().splitlines() if not l.startswith("#")] == ["match\tquick", "uncounted\tshort"]
        got = lines(w)
        assert got[0] == ["match", "quick"] and [p[2] for p in got if p[0] == "player"] == ["Me", "Wheezy"], got
        assert all(p[13] == "0" for p in got if p[0] == "player"), got   # (no credits: it does not count)


def test_credits_of_the_last_match():
    """(Nov 17, the owner's level up bar after each game) last_match.txt: what the newest Project Noble match earned the
    listed person, from where the last build stood, each kind of credit by ranks.json's worth and the rest as
    Commendations; reported once; the next match starts from there."""
    def report_lines(w):
        with open(os.path.join(w.paths.out, "last_match.txt"), encoding="utf-8") as f:
            return [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.paths.matchmaking = os.path.join(w.paths.store, "matchmaking.txt")
        os.makedirs(w.paths.store, exist_ok=True)
        with open(os.path.join(w.paths.store, "people.json"), "w", encoding="utf-8") as f:
            json.dump(["Me"], f)
        with open(w.paths.matchmaking, "w", encoding="utf-8") as f:
            f.write("pg-1\npg-2\n")
        w.build()                                           # (a build before any match: where Me stands, 0)
        w.write("trace_reach_forge_halo_20261117-180000.carnage.xml", report("pg-1", [
            row(ME, "Me", 0, 0, 10, 4, 2, 600, medals={8: 3}), row(bot(1), "Wheezy", 1, 1, 4, 10, 1, 600)]))
        w.career()
        data = w.build()
        got = report_lines(w)
        me = player(data, "Me")
        assert got[0] == ["match", "pg-1"] and got[1] == ["person", "Me", "0", str(me["cr"])], got
        lines = {l[2]: (l[3], int(l[4])) for l in got if l[0] == "line"}
        assert lines["Game Completed"] == ("1", 1000) and lines["Victory"] == ("1", 1000), lines
        assert lines["Kills"] == ("10", 1000) and lines["Assists"] == ("2", 100) and lines["Medals"] == ("3", 75), lines
        assert sum(cr for _, cr in lines.values()) == me["cr"], (lines, me["cr"])
        steps = [l for l in got if l[0] == "step"]
        assert steps[0][2:4] == ["0", "Recruit"] and int(steps[-1][2]) == me["rank"] + 1, steps
        w.build()                                           # (no new match: the report stays as it was)
        assert report_lines(w) == got
        first = me["cr"]
        w.write("trace_reach_70_boneyard_20261117-183000.carnage.xml", report("pg-2", [
            row(ME, "Me", 0, 1, 1, 6, 0, 600), row(bot(1), "Wheezy", 1, 0, 6, 1, 0, 600)]))
        w.career()
        data = w.build()
        got = report_lines(w)
        assert got[0] == ["match", "pg-2"] and got[1] == ["person", "Me", str(first), str(player(data, "Me")["cr"])], got
        assert "Victory" not in {l[2] for l in got if l[0] == "line"}


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


def test_game_reads_the_sites_ranks():
    """(Nov 17) <site>/ranks.txt, the ranks Project Noble's rows show beside the names: each listed player's rank
    step and rank as the site has them (one table, one credits sum), people left off as on the site."""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600, medals={8: 3})]))
        w.career()
        data = w.build()
        out = os.path.join(tmp, "game")
        os.makedirs(out)
        sr.write_game_ranks(data, types.SimpleNamespace(out=out))
        with open(os.path.join(out, "ranks.txt"), encoding="utf-8") as f:
            text = f.read()
    assert "ranks.json" in text.splitlines()[0]
    rows = [l.split("\t") for l in text.splitlines() if not l.startswith("#")]
    assert [r[:3] for r in rows] == [[p["name"], str(p["rank"]), data["ranks"][p["rank"]][0]] for p in data["players"]], rows
    assert not any(r[0] == "Me" for r in rows)
    # (Nov 17) the player card's numbers, the site's: Reach games, K/D, win %, commendation progress, credits
    oreo = next(r for r in rows if r[0] == "Oreo")
    p = player(data, "Oreo")
    assert oreo[:8] == ["Oreo", "0", "Recruit", "1", "7.00", "100", f"{p['comm_pct']:.1f}", str(p["cr"])], oreo
    assert oreo[8:] == [str(p["chal"]["daily_done"]), str(p["chal"]["weekly_done"])], oreo   # (Reach's card: challenges)
    assert p["cr"] > 0 and 0 <= p["comm_pct"] <= 100
    assert sr.commendation_progress({"a": 5, "b": None}, [{"key": "a", "need": [1, 10]}, {"key": "b", "need": [1, 4]}]) == 25.0
    with open(os.path.join(HERE, "..", "native", "proving_grounds.cpp"), encoding="utf-8") as f:
        cpp = f.read()
    assert "\\\\logs\\\\service_record\\\\ranks.txt" in cpp and "\\\\logs\\\\service_record\\\\ranks\\\\%d.png" in cpp


def test_game_reads_the_sites_commendations():
    """(Nov 19) <site>/commendations.txt, Project Noble's Commendations page: the site's table, and each listed
    person's counts with the tier reached as the site counts it, their progress, credits, rank and the next rank."""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600, medals={8: 3})]))
        w.career()
        data = w.build()
        data["players"][0]["person"] = True                  # (the page is a person's: list one)
        out = os.path.join(tmp, "game")
        os.makedirs(out)
        sr.write_game_commendations(data, types.SimpleNamespace(out=out))
        with open(os.path.join(out, "commendations.txt"), encoding="utf-8") as f:
            rows = [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    C = data["commendations"]
    assert rows[0] == ["tiers"] + C["tiers"], rows[0]
    table = [r for r in rows if r[0] == "commendation"]
    assert [r[1] for r in table] == [c["key"] for c in C["list"]] and all(len(r) == 9 for r in table)
    first = C["list"][0]
    assert table[0][5] == ",".join(map(str, first["need"])) and table[0][6] == ",".join(map(str, first["cr"]))
    p = data["players"][0]
    person = next(r for r in rows if r[0] == "person")
    assert person[1] == p["name"] and person[2] == f"{p['comm_pct']:.1f}" and person[3] == str(p["cr"]), person
    assert person[4] == data["ranks"][p["rank"]][0] and person[5] == data["ranks"][p["rank"] + 1][0], person
    counts = [r for r in rows if r[0] == "count"]
    assert len(counts) == len(C["list"]) and all(r[1] == p["name"] for r in counts)
    for r, c in zip(counts, C["list"]):
        n = p["comm"].get(c["key"])
        assert r[3] == ("" if n is None else str(n)) and r[4] == str(sr.commendation_tier(n, c["need"])), r
    with open(os.path.join(HERE, "..", "native", "proving_grounds.cpp"), encoding="utf-8") as f:
        assert "\\\\logs\\\\service_record\\\\commendations.txt" in f.read()


def test_game_reads_the_sites_career():
    """(Nov 19) <site>/career.txt, the game's Service Record and Career pages: each person's matches (all of them
    Matchmaking), and those of the ARENA and BIG TEAM BATTLE playlists by matchmaking.txt; bots not listed."""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 2, 600), row(bot(2), "Oreo", 1, 0, 2, 7, 3, 600)]))
        w.career()
        data = w.build()
        me = data["players"][0]                          # (the listed player, made a person as people.json would)
        me["person"] = True
        mm = os.path.join(tmp, "matchmaking.txt")
        with open(mm, "w", encoding="utf-8") as f:
            f.write(f"# test\n{data['matches'][0]['id']}\t2026-11-19 12:00\tARENA\n")
        out = os.path.join(tmp, "game")
        os.makedirs(out)
        sr.write_game_career(data, types.SimpleNamespace(out=out, matchmaking=mm))
        with open(os.path.join(out, "career.txt"), encoding="utf-8") as f:
            rows = [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    by = {r[2]: r for r in rows}
    assert set(by) == {"matchmaking", "arena", "btb"} and all(r[1] == me["name"] for r in rows), rows
    r = next(x for x in data["matches"][0]["rows"] if x["n"] == me["name"])
    want = ["1", "1" if r["won"] else "0", str(r["k"]), str(r["d"]), str(r["a"]), str(r["sec"])]
    assert by["matchmaking"][3:] == want and by["arena"][3:] == want, (by, want)
    assert by["btb"][3:] == ["0"] * 6
    with open(os.path.join(HERE, "..", "native", "proving_grounds_reach.inc"), encoding="utf-8") as f:
        assert "\\\\logs\\\\service_record\\\\career.txt" in f.read()


def test_game_reads_the_sites_armory():
    """(Nov 19) <site>/armory.txt, Project Noble's Armory: the person's rank step and credits earned, every item of
    maps/_looks/reach_prices.json with its rank gate as a step of the one rank table (Reach's grade 7 is Major), and
    the customization table's pieces; the game reads it (native/armory.cpp) and works out no rank of its own."""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 2, 600), row(bot(2), "Oreo", 1, 0, 2, 7, 3, 600)]))
        w.career()
        data = w.build()
        me = data["players"][0]
        me["person"] = True
        out = os.path.join(tmp, "game")
        os.makedirs(out)
        sr.write_game_armory(data, types.SimpleNamespace(out=out))
        with open(os.path.join(out, "armory.txt"), encoding="utf-8") as f:
            rows = [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    ranks = data["ranks"]
    mine = [r for r in rows if r[0] == "me"]
    assert mine == [["me", me["name"], str(me["rank"]), ranks[me["rank"]][0], str(me["cr"])]], mine
    with open(sr.ARMORY_PRICES, encoding="utf-8") as f:
        prices = json.load(f)["items"]
    items = {r[1]: r for r in rows if r[0] == "item"}
    assert len(items) == len(prices) and all(len(r) == 12 for r in items.values())
    mark_v = items["helmet_13_base"]                     # (Reach's own: 130,000 cR at Major, grade 7)
    assert mark_v[2:9] == ["helmet", "13", "0", "Mark V", "130000", mark_v[7], "Major"], mark_v
    assert ranks[int(mark_v[7])][0] == "Major" and mark_v[11] == "88=39"
    assert items["helmet_01_base"][10] == "d" and items["elite_2"][10] == "a" and "o" in items["mcc_helmet_64"][10]
    assert items["helmet_01_a"][9] == "helmet_01_base"
    # a grade past a rank's last Grade: that rank's last step; a rank past the table: the last step
    major = [i for i, r in enumerate(ranks) if r[0].startswith("Major")]
    assert sr.armory_gate_step(ranks, 7, 1) == major[0] and sr.armory_gate_step(ranks, 7, 99) == major[-1]
    assert sr.armory_gate_step(ranks, 99, 1) == len(ranks) - 1
    pieces = [r for r in rows if r[0] == "piece"]
    assert ["piece", "88", "39", "head", "player_john117", "0"] in pieces
    assert ["bytes", "spartan", "88,89,90,91,92,93,94"] in rows and ["bytes", "elite", "95"] in rows
    assert any(r[:2] == ["base", "female"] for r in rows)
    with open(os.path.join(HERE, "..", "native", "armory.cpp"), encoding="utf-8") as f:
        assert "\\\\logs\\\\service_record\\\\armory.txt" in f.read()


def test_reach_price_list():
    """(Nov 19) maps/_looks/reach_prices.json (tools/reach_prices.py, from the Editing Kit's supply depot tag): every
    item sets its own slot's byte (maps/_looks/reach.json), one free default a slot, what an item needs is listed,
    MCC's additions priced by us, and the 2010 Armory's own prices as the tag has them."""
    with open(os.path.join(HERE, "..", "maps", "_looks", "reach_prices.json"), encoding="utf-8") as f:
        items = json.load(f)["items"]
    with open(os.path.join(HERE, "..", "maps", "_looks", "reach.json"), encoding="utf-8") as f:
        at = {fl["name"]: fl["at"] for fl in json.load(f)["fields"]}
    ids = {it["id"] for it in items}
    assert len(ids) == len(items)
    slot_byte = {"helmet": [at["helmet"]], "left_shoulder": [at["left_shoulder"]], "right_shoulder": [at["right_shoulder"]],
                 "chest": [at["chest"]], "wrist": [at["wrist"]], "utility": [at["utility"]], "visor": [at["visor"]],
                 "knees": [at["knees"]], "elite_armor": [at["elite_armor"]],
                 "armor_effect": [at["armor_effect"], at["armor_effect"] + 1]}
    for it in items:
        assert [int(o) for o in it["writes"]] == slot_byte[it["slot"]], it
        assert all(n in ids for n in it["needs"]) and 1 <= it["grade"] <= 21 and it["cost"] >= 0, it
    for slot in slot_byte:
        assert sum(it["default"] for it in items if it["slot"] == slot) == 1, slot
    by = {it["id"]: it for it in items}
    assert (by["helmet_13_base"]["cost"], by["helmet_13_base"]["grade"], by["helmet_13_base"]["source"]) == (130000, 7, "2010")
    assert by["helmet_14_c"]["needs"] and by["helmet_14_c"]["auto"]          # (Haunted: every other helmet first)
    mcc = [it for it in items if it["id"].startswith("mcc_")]
    assert mcc and all(it["source"] == "ours" for it in mcc)
    helmets = {list(it["writes"].values())[0] for it in items if it["slot"] == "helmet"}
    assert helmets == set(range(90))                                         # (all 90 of MCC's helmet table)


def test_the_persons_own_reach_look():
    """(Nov 19) the person's look on the site is the one botcore saved from their own configuration (my_look_reach.txt),
    each field read at its byte, not a look made up from their name; with no file, or another name, it is as before."""
    import types
    sys.path.insert(0, os.path.join(HERE, ".."))
    from brain import looks as brain_looks
    with open(os.path.join(HERE, "..", "maps", "_looks", "reach.json"), encoding="utf-8") as f:
        fields = {x["name"]: x["at"] for x in json.load(f)["fields"]}
    cfg = bytearray(0xA0)
    cfg[0x20:0x20 + 8] = "Me".encode("utf-16-le").ljust(8, b"\0")
    want = {"primary": 22, "secondary": 3, "gender": 0, "helmet": 7, "chest": 4, "visor": 2, "knees": 1}
    for k, v in want.items():
        cfg[fields[k]] = v
    views = brain_looks.armory_from_config(bytes(cfg))
    assert len(views) == 2 and views[0].startswith("species=0") and views[1].startswith("species=1")
    got = dict(kv.split("=", 1) for kv in views[0].split(";"))
    assert all(got[k] == str(v) for k, v in want.items()), got
    assert brain_looks.armory_from_config(b"\0" * 10) == []
    with tempfile.TemporaryDirectory() as tmp:
        store = os.path.join(tmp, "store")
        os.makedirs(store)
        looks_ini = os.path.join(tmp, "bot_looks.ini")
        with open(looks_ini, "w", encoding="utf-8") as f:
            f.write("; none\n")
        with open(os.path.join(store, "my_look_reach.txt"), "w", encoding="utf-8") as f:
            f.write(f"# test\nname\tMe\ntag\tA113\nconfig\t{bytes(cfg).hex()}\n")
        paths = types.SimpleNamespace(store=store, looks=looks_ini, profiles=os.path.join(tmp, "no_profiles.ini"))
        assert sr.load_my_look(paths) == ("Me", bytes(cfg))
        out = sr.all_looks(paths, ["Me"])
        with open(out, encoding="utf-8") as f:
            mine = [l for l in f.read().splitlines() if l.startswith("Me|reach|own|")]
        assert len(mine) == 1 and ";helmet=7;" in mine[0] and ";primary=22;" in mine[0], mine
        os.remove(os.path.join(store, "my_look_reach.txt"))
        assert sr.load_my_look(paths) is None


def test_game_reads_the_sites_home_states():
    """(Nov 19) <site>/locations.txt, the heat on Project Noble's Psych Profile map: every state of states.json with
    how many listed players have it as their home state (the site's own pick or the one set by hand), and each person's
    state; every code also on the game's built-in map (native/world_map.h)."""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 1, 0, 7, 0, 600), row(bot(2), "Oreo", 1, 0, 7, 0, 3, 600)]))
        w.career()
        data = w.build()
        data["players"][0]["person"] = True
        data["players"][0]["state"] = "WA"                  # (as edit mode sets it)
        out = os.path.join(tmp, "game")
        os.makedirs(out)
        sr.write_game_locations(data, types.SimpleNamespace(out=out))
        with open(os.path.join(out, "locations.txt"), encoding="utf-8") as f:
            rows = [l.split("\t") for l in f.read().splitlines() if not l.startswith("#")]
    _, states = sr.load_states()
    table = [r for r in rows if r[0] == "state"]
    assert [r[1] for r in table] == [s[0] for s in states] and all(len(r) == 4 for r in table)
    want = {s[0]: 0 for s in states}
    for p in data["players"]:
        want[p["state"]] += 1
    assert {r[1]: int(r[3]) for r in table} == want and sum(want.values()) == len(data["players"])
    assert [r for r in rows if r[0] == "person"] == [["person", data["players"][0]["name"], "WA"]], rows
    with open(os.path.join(HERE, "..", "native", "world_map.h"), encoding="utf-8") as f:
        header = f.read()
    assert all(f'{{"{s[0]}",' in header for s in states), "a state missing from the built-in map"
    with open(os.path.join(HERE, "..", "native", "proving_grounds_reach.inc"), encoding="utf-8") as f:
        assert "\\\\logs\\\\service_record\\\\locations.txt" in f.read()


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
        assert set(data["medals"]) == {"8", "111"} and data["medals"]["8"] == {"name": "Medal 8", "icon": None, "cat": "other"}


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
                    "LilWraith|reach|own|species=0;gender=1;helmet=62;visor=2;chest=99;pieces=arms:female\n"
                    "LilWraith|reach|other|species=1;helmet=4;elite_armor=5\n"
                    "Zealot|reach|own|species=1;gender=1;helmet=4;elite_armor=5\n"
                    "Plain|reach|own|species=0;gender=0\n")
        names = sr.read_look_names(w.paths.look_names)
        assert names["ED_REACH_HELMET"] == {0: "Mark V [B]", 62: "EVA[C] / CNM", 4: "CQC / CBRN"}, names
        looks = sr.read_looks(w.paths.looks, names)
        assert looks["LilWraith"] == {"species": "Spartan", "pieces": [["Helmet", "EVA[C] / CNM"], ["Visor colour", "Blue"]],
                                      "body": "spartan_female"}
        assert looks["Zealot"] == {"species": "Elite", "pieces": [["Armor", "General"]], "body": "elite"}, looks
        assert looks["Plain"]["body"] == "spartan", looks


def kill(v, k, cause, vp, kp=None, t=10.0, **more):
    """One line of a recording as tools/kill_record.py writes it: bot k of team 0 kills bot v of team 1."""
    row = dict(v=v, k=k, new=True, o=k, c=cause, m=0, hits=[], vt=1, kt=0, vb=1, kb=1, vp=list(vp),
               kp=list(kp) if kp else None, gt=600, st=1)
    row.update(more)
    return json.dumps({"t": t, "kill": row})


def npy(descr, shape, data):
    head = f"{{'descr': '{descr}', 'fortran_order': False, 'shape': {shape!r}, }}"
    head += " " * ((64 - (10 + len(head) + 1) % 64) % 64) + "\n"
    return b"\x93NUMPY\x01\x00" + struct.pack("<H", len(head)) + head.encode("latin-1") + data


def test_kills_by_weapon_opponent_and_map():
    """A match's kill rows summed for each bot: kills and deaths per weapon (the credited player's own weapon, not the
    last hit's), every opponent both ways, where it stood for each kill and where it died. A betrayal is a death, not
    a kill; a death nobody is credited with has no killer; a person is named from the report; a row after the match
    was over, a row that is not one and a line cut short are skipped. A match recorded without kill rows adds
    nothing (a bot with only that match has no numbers at all, not zeros). The rows outlive the rotation."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g0", [      # before the kill rows
            row(ME, "Me", 0, 0, 5, 1, 0, 600), row(bot(1), "Wheezy", 1, 1, 1, 4, 0, 600),
            row(bot(4), "Old", 1, 1, 0, 1, 0, 600)]))
        w.write("trace_reach_forge_halo_20261115-180000.jsonl",
                '{"t": 0.1, "meta": {"map": "reach_forge_halo"}}\n{"t": 1.0, "id": 1, "notes": ["a \\"kill\\": no"]}\n')
        name = "trace_reach_70_boneyard_20261115-190000"
        w.write(name + ".carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 1, 1, 0, 600), row(bot(1), "Wheezy", 1, 1, 3, 5, 0, 600),
            row(bot(2), "Oreo", 0, 0, 2, 2, 0, 600), row(bot(3), "Ice", 1, 1, 0, 0, 0, 600, betrayals=1)]))
        w.write(name + ".jsonl", "\n".join([
            '{"t": 0.0, "kill_record": 2}',
            '{"t": 0.5, "meta": {"map": "reach_70_boneyard", "bot": {"id": 1, "name": "Wheezy"}}}',
            kill(1, 2, 6, (10, 20, 0), (30, 40, 0)),                                # Oreo's DMR
            kill(1, 2, 11, (12, 22, 0), (31, 41, 0), hits=[[3, 11, 0, 1.0, 0.1, 1], [2, 8, 1, 0.0, 0.9, 40]]),
            kill(2, 1, 6, (50, 60, 0), (11, 21, 0), vt=0, kt=1),                    # Wheezy's DMR on Oreo
            kill(1, 0, 43, (13, 23, 0), (14, 24, 0), kb=0),                         # the person's melee
            kill(1, 3, 11, (15, 25, 0), (16, 26, 0), kt=1),                         # a teammate's grenade: a betrayal
            kill(1, 2, 41, (17, 27, 0), (32, 42, 0), new=False, o=None),            # a fall: Oreo's old credit left
            kill(0, 1, 6, (70, 80, 0), (18, 28, 0), vb=0, vt=0, kt=1),              # Wheezy's DMR on the person
            kill(2, 1, 99, (51, 61, 0), (19, 29, 0), vt=0, kt=1),                   # a damage type with no name
            kill(1, 2, 6, (1, 1, 0), (2, 2, 0), st=2),                              # after the match was over
            '{"t": 9, "kill": {"v": "x"}}', '{"t": 9, "kill": 7}', '{"t": 9.5, "kill": {"v": 1, "k": 2, "vp": [1, 2']) + "\n")
        os.makedirs(os.path.join(w.paths.maps, "reach_70_boneyard"))
        with sr.zipfile.ZipFile(os.path.join(w.paths.maps, "reach_70_boneyard", "heightmap.npz"), "w") as z:
            z.writestr("top.npy", npy("<f4", (4, 6), bytes(96)))
            z.writestr("x0.npy", npy("<f8", (), struct.pack("<d", 100.0)))
            z.writestr("y0.npy", npy("<f4", (), struct.pack("<f", 200.0)))
            z.writestr("cell.npy", npy("<f8", (), struct.pack("<d", 0.5)))
        with open(os.path.join(w.paths.maps, "reach_70_boneyard", "topdown.png"), "wb") as f:
            f.write(sr.png(1, 1, bytes(4)))
        w.career()
        data = w.build()
        assert [(m["id"], m["kills"]) for m in data["matches"]] == [("g1", True), ("g0", False)], data["matches"]
        g = player(data, "Wheezy")["g"]["reach"]
        assert g["kill_games"] == 1 and g["cats"]["all"]["games"] == 2, g["kill_games"]
        assert g["weapons"] == {"reach:6": [2, 1], "reach:8": [0, 1], "reach:43": [0, 1], "reach:11": [0, 1],
                                "reach:41": [0, 1], "reach:99": [1, 0]}, g["weapons"]
        assert g["versus"] == {"Oreo": [2, 2], "Me": [1, 1]}, g["versus"]
        assert g["heat"] == {"reach_70_boneyard": {"k": [11, 21, 18, 28, 19, 29],
                                                   "d": [10, 20, 12, 22, 13, 23, 15, 25, 17, 27]}}, g["heat"]
        assert player(data, "Wheezy")["g"]["all"]["weapons"] == g["weapons"]
        oreo = player(data, "Oreo")["g"]["reach"]
        assert oreo["weapons"] == {"reach:6": [1, 1], "reach:8": [1, 0], "reach:99": [0, 1]}, oreo["weapons"]
        assert oreo["versus"] == {"Wheezy": [2, 2]} and oreo["heat"]["reach_70_boneyard"]["k"] == [30, 40, 31, 41], oreo
        ice = player(data, "Ice")["g"]["reach"]                # (its grenade killed a teammate: no kill, no opponent)
        assert (ice["kill_games"], ice["weapons"], ice["versus"], ice["heat"]) == (1, {}, {}, {}), ice
        old = player(data, "Old")["g"]["reach"]                # (only the match from before the kill rows)
        assert (old["kill_games"], old["weapons"], old["versus"], old["heat"]) == (0, {}, {}, {}), old
        assert data["weapons"]["reach:6"] == ["DMR", True] and data["weapons"]["reach:99"] == ["Damage type 99", True]
        assert data["weapons"]["reach:43"] == ["Melee", True], data["weapons"]
        assert data["weapons"]["reach:41"] == ["Fall", False], data["weapons"]       # (named by the list, not seen live)
        # the carnage report's kill feed: every row that counts, in order, the person named, a death without a killer
        feed = next(m for m in data["matches"] if m["id"] == "g1")["feed"]
        assert feed == [[10.0, "Oreo", "Wheezy", "reach:6", "kill"], [10.0, "Oreo", "Wheezy", "reach:8", "kill"],
                        [10.0, "Wheezy", "Oreo", "reach:6", "kill"], [10.0, "Me", "Wheezy", "reach:43", "kill"],
                        [10.0, "Ice", "Wheezy", "reach:11", "betrayal"], [10.0, None, "Wheezy", "reach:41", "death"],
                        [10.0, "Wheezy", "Me", "reach:6", "kill"], [10.0, "Wheezy", "Oreo", "reach:99", "kill"]], feed
        assert all(r[3] in data["weapons"] for r in feed)
        assert "feed" not in next(m for m in data["matches"] if m["id"] == "g0")     # (recorded before the kill rows)
        assert data["heat_maps"] == {"reach_70_boneyard": {"img": "maps/reach_70_boneyard.png",
                                                           "frame": [100.0, 200.0, 3.0, 2.0]}}, data["heat_maps"]
        assert os.path.getsize(os.path.join(w.paths.out, "maps", "reach_70_boneyard.png")) > 0
        for gone in (name + ".carnage.xml", name + ".jsonl"):   # (the recording rotation took the match)
            os.remove(os.path.join(w.logs, gone))
        w.career()
        again = w.build()
        assert player(again, "Wheezy")["g"]["reach"] == g and again["matches"] == data["matches"]
    assert sr.map_frame(os.path.join(tmp, "nothing.npz")) is None
    assert sr.read_kills(os.path.join(tmp, "nothing.jsonl")) is None


def test_two_people_named_by_their_report_rows():
    """Kill rows know a player by index only. A person gets the report row of their team that their kills and deaths
    fit; two people the rows cannot tell apart are left unnamed, never guessed."""
    detail = {"teams": True, "players": [
        {"name": "Me", "bot": False, "idx": None, "team": 0, "kills": 2, "deaths": 0},
        {"name": "A Friend", "bot": False, "idx": None, "team": 0, "kills": 0, "deaths": 1},
        {"name": "Wheezy", "bot": True, "idx": 5, "team": 1, "kills": 1, "deaths": 2}]}
    rows = [json.loads(x)["kill"] for x in (
        kill(5, 0, 6, (1, 1, 0), (2, 2, 0), kb=0), kill(5, 0, 6, (1, 1, 0), (2, 2, 0), kb=0),
        kill(9, 5, 6, (3, 3, 0), (4, 4, 0), vb=0, vt=0, kt=1))]
    assert sr.kill_names(detail, rows) == {5: "Wheezy", 0: "Me", 9: "A Friend"}, sr.kill_names(detail, rows)
    assert sr.kill_check(detail, rows) == [("Me", 2, 2, 0, 0), ("A Friend", 0, 0, 1, 1), ("Wheezy", 1, 1, 2, 2)]
    tally = sr.kill_tally(detail, rows)
    assert tally["Wheezy"]["versus"] == {"Me": [0, 2], "A Friend": [1, 0]}, tally["Wheezy"]
    same = dict(detail, players=[dict(p, kills=1, deaths=1) if not p["bot"] else p for p in detail["players"]])
    assert sr.kill_names(same, rows) == {5: "Wheezy"}, sr.kill_names(same, rows)
    assert sr.kill_tally(same, rows)["Wheezy"]["versus"] == {sr.UNNAMED: [1, 2]}


def test_the_kill_that_wins_the_match_counts():
    """The first recordings (version 1) wrote the engine's state as read after each death: "over" for the kill that
    won the match. That row counts when the game wrote its credit at that death; the deaths after it do not, nor does
    a first "over" row whose credit is left from an earlier death. A version 2 recording is read as written."""
    detail = {"teams": True, "players": [
        {"name": "Oreo", "bot": True, "idx": 2, "team": 0, "kills": 2, "deaths": 0},
        {"name": "Wheezy", "bot": True, "idx": 1, "team": 1, "kills": 0, "deaths": 2}]}
    rows = [kill(1, 2, 6, (1, 1, 0), (2, 2, 0), t=5.0),
            kill(1, 2, 6, (3, 3, 0), (4, 4, 0), t=9.0, st=2),                       # the kill that won it
            kill(1, 2, 43, (5, 5, 0), (6, 6, 0), t=12.0, st=2),                     # after the match
            kill(1, 2, 43, (5, 5, 0), (6, 6, 0), t=15.0, st=2, new=False, hits=[[2, 43, 0, 1.0, 1.0, 2]])]
    with tempfile.TemporaryDirectory() as tmp:
        def counted(version, lines):
            path = os.path.join(tmp, f"trace_reach_70_boneyard_20261115-19000{version}.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join([json.dumps({"t": 0.0, "kill_record": version})] + lines) + "\n")
            return [(name, k, d) for name, k, _, d, _ in sr.kill_check(detail, sr.kill_rows(sr.read_kills(path)))]
        assert counted(1, rows) == [("Oreo", 2, 0), ("Wheezy", 0, 2)], counted(1, rows)
        assert counted(2, rows) == [("Oreo", 1, 0), ("Wheezy", 0, 1)], counted(2, rows)
        assert counted(1, [rows[0], rows[3]]) == [("Oreo", 1, 0), ("Wheezy", 0, 1)]   # (a left-over credit: not it)
        assert counted(1, list(reversed(rows))) == [("Oreo", 2, 0), ("Wheezy", 0, 2)]  # (by time, not by line)
        # the store keeps the rows as the recording said (version and all); the first day's store kept a version 1
        # recording as a bare list of rows, read the same way
        kept = sr.read_kills(os.path.join(tmp, "trace_reach_70_boneyard_20261115-190001.jsonl"))
        assert kept["v"] == 1 and [k["st"] for k in kept["rows"]] == [2, 2, 2, 1], kept
        bare = sr.kill_rows(kept["rows"])
        assert bare == sr.kill_rows(kept) and sorted(k["st"] for k in bare) == [1, 1, 2, 2], bare
        assert [k["st"] for k in kept["rows"]] == [2, 2, 2, 1]                        # (reading changes nothing kept)
        assert sr.kill_rows({"v": 2, "rows": kept["rows"]}) == kept["rows"] and sr.kill_rows({"v": 1}) == []


def test_a_long_recording_keeps_its_kill_rows():
    """The recording's time window (tools/recording.py) trims a long match's oldest rows; the kill rows and the line
    that says the recording has them stay, once each."""
    spec = importlib.util.spec_from_file_location("recording", os.path.join(HERE, "recording.py"))
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "trace_reach_70_boneyard_20261115-190000.jsonl")
        r = rec.RollingFile(path, 10.0)
        r.slack, r.due = 5.0, 15.0
        r.write('{"t": 0.0, "kill_record": 2}\n')
        for k in range(400):
            now = k / 10
            if k in (5, 120, 395):
                r.write(kill(1, 2, 6, (k, 0, 0), (0, k, 0), t=now) + "\n")
            r.write(json.dumps(dict(t=now, id=9, pos=[k, 0, 0], notes=["no kill here"])) + "\n")
            r.tick(now)
            if r.job is not None:
                r.job.join()
                r.tick(now)
        r.close()
        with open(path, encoding="utf-8") as f:
            times = [json.loads(x)["t"] for x in f if '"pos"' in x]
        assert times[0] > 20.0, times[0]                       # (the oldest rows are gone)
        rows = sr.kill_rows(sr.read_kills(path))
        assert [(k["t"], k["vp"][0]) for k in rows] == [(0.5, 5), (12.0, 120), (39.5, 395)], rows


def test_whole_arsenal_listed():
    """Every Reach weapon and vehicle is on the site (the Weapons page, the state boards) used or not: the table's
    arsenal and vehicles, named, none of them both, no vehicle among the weapons."""
    arsenal = sr.arsenal_keys()
    weapons, vehicles = arsenal["weapons"], arsenal["vehicles"]
    names, _ = sr.load_weapons()["reach"]
    assert len(weapons) >= 20 and len(vehicles) >= 10 and not set(weapons) & set(vehicles)
    assert vehicles == [k for k in sr.vehicle_keys() if k in vehicles] and set(vehicles) == set(sr.vehicle_keys())
    assert all(k.split(":")[1] in names for k in weapons + vehicles)
    by_name = {names[k.split(":")[1]] for k in weapons}
    assert {"DMR", "Magnum", "Energy Sword", "Focus Rifle", "Fuel Rod Gun"} <= by_name
    assert not by_name & {"Fall", "Suicide", "Guardians", "SMG", "Battle Rifle", "Brute Shot"}   # (not Reach weapons)


def test_daily_and_weekly_challenges():
    """(Nov 17) Challenges: each day's and week's drawn by its date alone; a match counts in its local day and its
    Monday week; one finished in its window adds its cR (ranks.json challenge_credits), today's and this week's
    progress shown; filters, one-match feats, medals, weapons; the list itself well formed."""
    import datetime as dt
    table = sr.load_challenges()
    keys = [c["key"] for c in table["daily"] + table["weekly"]]
    assert len(keys) == len(set(keys)) and len(table["daily"]) >= 40 and len(table["weekly"]) >= 15
    assert (table["daily_count"], table["weekly_count"]) == (4, 1)
    for c in table["daily"] + table["weekly"]:
        how = c["count"]
        assert c["need"] > 0 and c["cr"] > 0 and c["name"] and c["what"] and c["icon"], c
        assert sum(k in how for k in ("stat", "medals", "group", "weapons", "vehicles")) == 1, c
        assert how.get("stat") in (None, "kills", "assists", "wins", "games", "medals", "kg", "km", "score", "spree", "plus", "top"), c
    assert sr.challenge_pick("daily", "2026-11-17", table["daily"], 4) == sr.challenge_pick("daily", "2026-11-17", table["daily"], 4)
    assert sr.challenge_pick("daily", "2026-11-17", table["daily"], 4) != sr.challenge_pick("daily", "2026-11-18", table["daily"], 4)
    assert len(set(sr.challenge_pick("daily", "2026-11-17", table["daily"], 4))) == 4
    at = lambda y, mo, d, h: dt.datetime(y, mo, d, h).timestamp()
    assert sr.challenge_starts(at(2026, 11, 17, 23)) == ("2026-11-17", "2026-11-16")   # (a Tuesday: its Monday)
    assert sr.challenge_starts(at(2026, 11, 16, 0)) == ("2026-11-16", "2026-11-16")
    mine = {"daily": [{"key": "ten", "count": {"stat": "kills"}, "need": 10, "cr": 1000},
                      {"key": "big", "count": {"stat": "kills", "at_least": 15}, "need": 1, "cr": 500}],
            "weekly": [{"key": "wins", "count": {"stat": "wins"}, "need": 2, "cr": 5000}], "daily_count": 2, "weekly_count": 1}

    def crow(t, kills, won, **more):
        return {"t": t, "cat": "slayer", "map": "reach_70_boneyard", "games": 1, "wins": int(won), "kills": kills, "deaths": 3,
                "assists": 0, "plus": kills - 3, "medals_n": 0, "kg": 0, "km": 0, "score": 0, "spree": 0, "top": 0,
                "medal": {}, "weapons": {}} | more
    rows = [crow(at(2026, 11, 16, 20), 6, True), crow(at(2026, 11, 16, 21), 6, False),   # Monday: 12 kills, no big game
            crow(at(2026, 11, 17, 20), 16, True)]                                         # Tuesday: 16 kills in one
    got = sr.challenge_progress(rows, mine, {}, at(2026, 11, 17, 22))
    assert got == {"cr": 1000 + 1000 + 500 + 5000, "daily_done": 3, "weekly_done": 1, "now": {"ten": 16, "big": 1, "wins": 2}}, got
    nxt = sr.challenge_progress(rows, mine, {}, at(2026, 11, 23, 9))           # (next Monday: nothing now, credits kept)
    assert nxt["cr"] == got["cr"] and nxt["now"] == {}
    v = lambda how, r: sr.challenge_value({"count": how}, r, {"medal_headshot": "7"}, {"3": "multikill"}, {"reach:24"})
    r = crow(0, 12, True, cat="ctf", medal={"7": 4, "3": 2}, weapons={"reach:6": 5, "reach:24": 2})
    assert v({"stat": "kills", "cat": ["slayer"]}, r) == 0 and v({"stat": "kills", "cat": ["ctf"]}, r) == 12
    assert v({"stat": "wins", "map": ["reach_30_settlement"]}, r) == 0 and v({"stat": "kills", "map": ["reach_70_boneyard"]}, r) == 12
    assert v({"medals": ["medal_headshot"]}, r) == 4 and v({"group": "multikill"}, r) == 2
    assert v({"weapons": [6]}, r) == 5 and v({"vehicles": True}, r) == 2 and v({"stat": "plus", "at_least": 10}, r) == 0
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp)
        w.write("trace_reach_forge_halo_20261115-180000.carnage.xml", report("g1", [
            row(ME, "Me", 0, 0, 30, 4, 2, 600), row(bot(1), "Wheezy", 1, 1, 4, 30, 1, 600)]))
        w.career()
        data = w.build()
        C = data["challenges"]
        assert len(C["daily"]["keys"]) == 4 and len(C["weekly"]["keys"]) == 1 and C["credits"] is True
        assert len(C["list"]) == len(keys) and C["daily"]["ends"] > C["daily"]["ends"] - 86400
        wheezy = player(data, "Wheezy")
        assert set(wheezy["chal"]) == {"cr", "daily_done", "weekly_done", "now"}
        s = wheezy["g"]["reach"]["cats"]["all"]
        assert wheezy["cr"] == sr.credits(s, sr.load_ranks()[0]) + wheezy["comm_cr"] + wheezy["chal"]["cr"]


def test_clan_rewards():
    """(Nov 18) Clan rewards: the table well formed; a clan's weekly challenge counts every member's matches of its
    week together and adds its cR once; this week's MVP; the history (first match, ranks reached ending at the rank its
    cR has now, games milestones, the week's top clan); the owner's settings (a reward off, unlocks moved, a bad change
    refused, a week's challenge picked, an emblem) kept and laid over the defaults."""
    import datetime as dt
    worth, steps = sr.load_ranks()
    table = sr.load_clan_table()
    names = sr.rank_names(steps)
    keys = [r["key"] for r in table["rewards"]]
    assert keys == ["frame", "tag", "banner", "ribbon", "emblem", "challenge", "rivals", "hall", "history", "crown"]
    for r in table["rewards"]:
        assert r["name"] and r["what"] and isinstance(r["on"], bool), r
        if "at" in r:
            assert len(r["at"]) == len(r["levels"]) and all(a in names for a in r["at"]), r
            assert [names.index(a) for a in r["at"]] == sorted(names.index(a) for a in r["at"]), r
    for c in table["challenges"]:
        assert c["need"] > 0 and c["cr"] > 0 and c["name"] and c["what"] and c["icon"] and sum(
            k in c["count"] for k in ("stat", "medals", "group", "weapons", "vehicles")) == 1, c
    at = lambda d, h: dt.datetime(2026, 11, d, h).timestamp()

    def crow(t, kills, won):
        return {"t": t, "cat": "slayer", "map": "", "games": 1, "wins": int(won), "kills": kills, "deaths": 3, "assists": 0,
                "plus": kills - 3, "medals_n": 0, "kg": 0, "km": 0, "score": 0, "spree": 0, "top": 0, "medal": {}, "weapons": {}}
    mine = {"rewards": table["rewards"], "challenges": [{"key": "k30", "count": {"stat": "kills"}, "need": 30, "cr": 100000,
                                                          "name": "n", "what": "w", "icon": "kills"}]}
    rows = {"A": [crow(at(10, 20), 20, True), crow(at(16, 20), 10, True)],     # (last week: 20 + 15 kills together)
            "B": [crow(at(11, 20), 15, False), crow(at(17, 20), 5, False)],
            "C": [crow(at(12, 20), 2, False)]}
    out_players = [{"name": n, "clan": clan, "cr": sum(sr.match_credits(r, worth) for r in rows[n]), "emblem": "e.png"}
                   for n, clan in (("A", "RED"), ("B", "red "), ("C", "BLU"))]
    settings = {"rewards": {}, "weeks": {}, "emblems": {"red": "B", "blu": "Nobody"}}
    rewards = sr.clan_rewards(mine, settings, steps)
    clans, week = sr.clan_block(out_players, rows, mine, settings, rewards, {}, worth, steps, at(17, 22))
    red, blu = clans["red"], clans["blu"]
    assert (red["bonus"], red["done"], red["now"]) == (100000, 1, 15) and (blu["bonus"], blu["now"]) == (0, 0)
    assert red["mvp"] == ["A", sr.match_credits(rows["A"][1], worth)] and blu["mvp"] is None
    assert red["emblem"] == "B" and blu["emblem"] is None              # (a name not in the clan: none)
    kinds = [e[1] for e in red["history"]]
    assert kinds[-1] == "first" and "top" in kinds and "top" not in [e[1] for e in blu["history"]]
    total = sum(p["cr"] for p in out_players[:2]) + 100000
    reached = [e[2] for e in red["history"] if e[1] == "rank"]
    assert reached and reached[0] == steps[max(i for i, s in enumerate(steps) if s[2] == 0 and s[3] * 10 <= total)][1]
    assert week["start"] == "2026-11-16" and week["key"] == "k30" and week["picked"] is False
    off = sr.clan_rewards(mine, {"rewards": {"challenge": {"on": False}}, "weeks": {}, "emblems": {}}, steps)
    assert sr.clan_block(out_players, rows, mine, settings, off, {}, worth, steps, at(17, 22))[0]["red"]["bonus"] == 0
    moved = sr.clan_rewards(mine, {"rewards": {"tag": {"at": ["Recruit", "Recruit", "Hero"]},
                                               "frame": {"at": ["Hero", "Private", "Major"]}}, "weeks": {}, "emblems": {}}, steps)
    assert moved[1]["at"] == ["Recruit", "Recruit", "Hero"] and moved[0]["at"] == table["rewards"][0]["at"]   # (falling: kept)
    with tempfile.TemporaryDirectory() as tmp:
        paths = sr.Paths(store=tmp)
        got = sr.save_clan_rewards(paths, {"crown": {"on": False}, "ribbon": {"on": True, "at": ["Major"]}}, steps)
        assert [r["on"] for r in got if r["key"] == "crown"] == [False] and [r["at"] for r in got if r["key"] == "ribbon"] == [["Major"]]
        for bad in ({"nope": {"on": True}}, {"tag": {"at": ["Major"]}}, {"ribbon": {"at": ["General Grade 9"]}}, []):
            try:
                sr.save_clan_rewards(paths, bad, steps)
                raise AssertionError(bad)
            except ValueError:
                pass
        assert sr.load_clan_settings(paths)["rewards"]["crown"] == {"on": False}
        assert all(r["on"] for r in sr.save_clan_rewards(paths, {}, steps))   # (the defaults again)
        pick = table["challenges"][-1]["key"]
        assert sr.save_clan_week(paths, pick, at(17, 9)) == pick
        assert sr.load_clan_settings(paths)["weeks"] == {"2026-11-16": pick}
        sr.save_clan_week(paths, "", at(17, 9))
        assert sr.load_clan_settings(paths)["weeks"] == {}
        assert sr.save_clan_emblem(paths, "RED", "B") == "B" and sr.load_clan_settings(paths)["emblems"] == {"red": "B"}
        try:
            sr.save_clan_week(paths, "not_one", at(17, 9))
            raise AssertionError("a made-up challenge")
        except ValueError:
            pass


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

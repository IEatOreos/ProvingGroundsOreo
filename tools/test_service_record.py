"""tools/service_record.py: the leaderboard equals bot_career's totals, the bots' restart, who is listed, the rates and
their formats, the rank table and credits, game type families, a report kept in full after the rotation, bad reports;
the kill rows (tools/kill_record.py) summed per weapon, per opponent and per map, kept after the rotation, a match
without them, bad rows, a long recording's trim, a map picture's frame; the bots' home states."""
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
                           look_names=os.path.join(tmp, "look_names.h"), mcc_report=os.path.join(tmp, "none.xml"),
                           maps=os.path.join(tmp, "maps"), snap=os.path.join(tmp, "no_figure_snap.exe"))

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
        assert oreo["cr"] == base + 300 and data["commendations"]["credits"] is True, (oreo["cr"], base)
        assert len(data["commendations"]["list"]) == 19 and data["commendations"]["list"][0]["from"] in ("report", "matches", "kills")
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
    assert len(comms) == 19 and keys[-5:] == ["victor", "first_blood", "closer", "grudge_match", "medal_collector"], keys
    g = {"medals": {"8": 2, "9": 0, "111": 5}, "cats": {"all": sr.blank() | {"wins": 12}}, "weapons": {}, "kill_games": 1,
         "feats": {"first": 6, "closer": 0, "grudge": 2}, "maps": {"reach_70_boneyard": {"wins": 2}, "reach_forge_halo": {"wins": 0}, "x": {"wins": 1}}}
    n = sr.commendation_counts(g, comms, {})
    assert (n["victor"], n["first_blood"], n["closer"], n["grudge_match"], n["medal_collector"]) == (12, 6, 0, 2, 2), n
    assert sr.commendation_counts(dict(g, kill_games=0), comms, {})["first_blood"] is None
    badges = sr.load_badges()
    assert [b["key"] for b in badges] == ["map_master", "hometown_hero"] and len(badges[0]["maps"]) == 20
    assert set(badges[0]["maps"]) == set(sr.MAP_NAMES)
    assert sr.badge_counts(g, badges) == {"map_master": ["reach_70_boneyard"]}


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

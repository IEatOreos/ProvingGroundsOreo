"""tools/bot_sim.py and tools/sim_engine.py (the bot simulation, Nov 17-18): a seed plays the same match; a match's kill
rows are its scoreboard; every playlist gametype plays to its limits; people never play; clans line up together; the
pace averages what is asked; matches are stored and read back for the site and the career totals, a reset covers them;
the credits screen still takes the person's own match; limits come from real matches; the model learns from real
fights. Everything in a temporary folder: nothing of the real Service Record is read for matches or written."""
import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bot_sim  # noqa: E402
import kill_record  # noqa: E402
import service_record as sr  # noqa: E402
import sim_engine as se  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, ".."))
GAMETYPES = ["TU TEAM SLAYER DMR", "TU ONE FLAG CTF (4-10)", "TU MULTI FLAG CTF", "TU TEAM ODDBALL",
             "TU TEAM CRAZY KING (4-10)", "CTU 5-PLOT TERRITORIES", "TU ONE BOMB ASSAULT", "TU MULTI BOMB ASSAULT",
             "TU NEUTRAL BOMB ASSAULT (4-10)", "TU STOCKPILE"]


def spec_of(gametype, size=4, prefix="b"):
    return {"gametype": gametype, "size": size,
            "players": [{"name": f"{prefix}{i}", "team": i % 2, "tier": "top", "style": "any", "clan": ""}
                        for i in range(2 * size)]}


def countdown(fam="slayer"):
    info = se.load_map("reach_45_launch_station", fam=fam, root=ROOT)
    info.real_pairs = []
    return info


class World:
    """A made-up install: a pool with clans and saved tiers, an empty real record, the store and site folders."""

    def __init__(self, tmp, names=40, people=("Person One",)):
        self.tmp = tmp
        store = os.path.join(tmp, "store")
        os.makedirs(store)
        self.paths = sr.Paths(store=store, ledger=os.path.join(tmp, "career", "ledger.json"),
                              out=os.path.join(tmp, "site"), profiles=os.path.join(tmp, "bot_profiles.ini"),
                              pool=os.path.join(tmp, "bot_pool_saved.ini"), bot_pool=os.path.join(tmp, "bot_pool.txt"),
                              matchmaking=os.path.join(store, "matchmaking.txt"), logs=os.path.join(tmp, "logs"),
                              maps=os.path.join(ROOT, "maps"), snap=os.path.join(tmp, "none.exe"),
                              mcc_report=os.path.join(tmp, "none.xml"), emblems=os.path.join(tmp, "emblems"),
                              looks=os.path.join(tmp, "bot_looks.ini"), look_names=os.path.join(tmp, "none.h"))
        os.makedirs(os.path.dirname(self.paths.ledger))
        os.makedirs(self.paths.logs)
        self.names = [f"SimBot{i:03d}" for i in range(names)] + list(people)
        with open(self.paths.bot_pool, "w", encoding="utf-8") as f:
            f.write("# pool\n" + "\n".join(self.names) + "\n")
        with open(self.paths.profiles, "w", encoding="utf-8") as f:   # (three in clan ABC, two in XYZ)
            for i, n in enumerate(self.names):
                clan = "ABC" if i < 3 else "XYZ" if i < 5 else ""
                f.write(f"bot={n},{1000 + i},{clan}\n")
        with open(self.paths.pool, "w", encoding="utf-8") as f:
            f.write("saved=demon,any,SimBot000\nsaved=novice,wheelman,SimBot001\n")
        with open(os.path.join(store, "people.json"), "w", encoding="utf-8") as f:
            json.dump(list(people), f)
        self.playlists = {"arena": {"size": 4, "gametypes": [(g, 1) for g in GAMETYPES], "maps": ["Countdown", "Zealot"]},
                          "btb": {"size": 8, "gametypes": [("TU TEAM SLAYER DMR", 1)], "maps": ["Boneyard"]}}
        self.settings = dict(bot_sim.SETTINGS)

    def round(self, seed=7, pace=None):
        s = dict(self.settings)
        if pace is not None:
            s["pace"] = pace
        now = time.time()
        return bot_sim.play_round(self.paths, (now - 900, now - 600), seed, settings=s, playlists=self.playlists)


class Engine(unittest.TestCase):
    def test_rng_is_its_own(self):
        a, b = se.Rng(42), se.Rng(42)
        self.assertEqual([a.u64() for _ in range(5)], [b.u64() for _ in range(5)])
        self.assertEqual(se.Rng(1).u64(), 0x910A2DEC89025CC1)          # (splitmix64's first number from seed 1)

    def test_a_seed_plays_the_same_match(self):
        model, info, spec = se.Model(), countdown(), spec_of("TU TEAM SLAYER DMR")
        self.assertEqual(se.play(spec, model, info, 99), se.play(spec, model, info, 99))
        self.assertNotEqual(se.play(spec, model, info, 99)[1], se.play(spec, model, info, 100)[1])

    def test_kill_rows_are_the_scoreboard(self):
        model, info = se.Model(), countdown()
        for seed in range(5):
            report, rows, res = se.play(spec_of("TU TEAM SLAYER DMR"), model, info, seed)
            detail = {"players": report, "teams": True}
            self.assertTrue(all(kill_record.read(k, True) for k in rows))
            self.assertEqual([x for x in sr.kill_check(detail, rows) if x[1] != x[2] or x[3] != x[4]], [])
            score = {0: 0, 1: 0}
            for p in report:
                score[p["team"]] += p["score"]
                self.assertEqual(p["kw"] + p["kg"] + p["km"] + p["ko"], p["kills"])
                self.assertEqual(p["medal_total"], sum(p["medals"].values()))
            self.assertEqual({int(k): v for k, v in res["scores"].items()}, score)
            win = res["winner"]
            for p in report:
                self.assertEqual(p["standing"], 0 if win is None or p["team"] == win else 1)

    def test_every_playlist_gametype_plays_to_its_limits(self):
        model = se.Model()
        for gt in GAMETYPES:
            fam = sr.family(gt)
            info = countdown(fam)
            limit, secs = se.limits_of(model, gt, 4)
            if se.rounds_of(gt) > 1:
                limit, secs = None, se.ROUND_SECS * se.ROUNDS
            for seed in range(3):
                report, rows, res = se.play(spec_of(gt), model, info, seed)
                self.assertLessEqual(res["seconds"], secs, gt)
                self.assertTrue(any(p["kills"] for p in report), gt)
                if limit:
                    self.assertLessEqual(max(res["scores"].values()), limit + 4, gt)   # (5 territories at once)
                    self.assertTrue(max(res["scores"].values()) >= limit or res["seconds"] == secs, (gt, res))

    def test_vehicles_and_power_weapons_from_the_map(self):
        info = se.load_map("reach_70_boneyard", fam="slayer", root=ROOT)
        self.assertTrue(info.vehicles and any(dt in se.POWER for dt, _ in info.weapons))
        dts = set()
        for seed in range(4):
            _, rows, _ = se.play(spec_of("TU TEAM SLAYER DMR", 8), se.Model(), info, seed)
            dts |= {k["c"] for k in rows}
        self.assertTrue(dts & set(range(24, 41)), "no vehicle kill on Boneyard")
        self.assertTrue(dts & set(se.POWER), "no power weapon kill on Boneyard")

    def test_limits_from_real_matches(self):
        seen = [(300, {0: 50, 1: 30}), (420, {0: 50, 1: 44}), (720, {0: 40, 1: 38}), (90, {0: 3, 1: 0})]
        self.assertEqual(se.limits_from("TU TEAM SLAYER DMR", seen), (50, 720))
        self.assertEqual(se.limits_from("TU STOCKPILE", [(184, {0: 0, 1: 0})]), se.FAMILY_RULES["stockpile"])

    def test_the_model_learns_from_real_fights(self):
        rows, players = [], []
        for i in range(8):
            players.append({"name": f"r{i}", "bot": True, "idx": i, "team": i % 2, "kills": 0, "deaths": 0, "assists": 0,
                            "seconds": 600, "score": 0, "medals": {}})
        for n in range(60):                                 # (r0 kills a blue bot sixty times; nobody kills it)
            v = 1 + 2 * (n % 4)
            rows.append({"v": v, "k": 0, "new": True, "o": 0, "c": 6, "m": 0, "hits": [[0, 6, 0, 0, 0, 2]], "vt": 1,
                         "kt": 0, "vb": 1, "kb": 1, "vp": [1.0, 2.0, 3.0], "kp": [4.0, 5.0, 6.0], "gt": n, "st": 1, "t": n})
            players[0]["kills"] += 1
            players[v]["deaths"] += 1
        detail = {"players": players, "teams": True, "type": "TU TEAM SLAYER DMR", "map": "reach_45_launch_station"}
        m = se.fit([(detail, rows, None)], {f"r{i}": "strong" for i in range(8)})
        self.assertGreater(m.skill["r0"], se.TIER_SKILL["strong"] + 0.3)
        self.assertLess(m.skill["r1"], se.TIER_SKILL["strong"])
        self.assertEqual(m.weapons["r0"], {6: 60})
        # (Nov 19, the owner: simulated strength is the difficulty's alone: the fitted skill above changes nothing)
        self.assertEqual(m.inputs_of("r0", "strong")["s"], se.TIER_SKILL["strong"])
        self.assertEqual(m.inputs_of("r1", "demon")["s"], se.TIER_SKILL["demon"])


class Population(unittest.TestCase):
    def test_pace_averages_what_is_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=400)
            bots = bot_sim.population(w.paths, w.settings)
            self.assertEqual(len(bots), 400)                  # (the person left out)
            paced = [b for b in bots if b.tier not in bot_sim.EVERY_ROUND]   # (Demons: every round, pace 1)
            self.assertAlmostEqual(sum(b.pace for b in paced) / len(paced), w.settings["pace"], places=6)
            self.assertTrue(all(b.pace == 1.0 for b in bots if b.tier in bot_sim.EVERY_ROUND))
            top = [b for b in bots if b.tier in se.TOP_TIERS]
            rest = [b for b in bots if b.tier not in se.TOP_TIERS]
            if len(top) > 40 and len(rest) > 40:
                self.assertGreater(sum(b.grinder for b in top) / len(top), sum(b.grinder for b in rest) / len(rest))
            self.assertEqual(next(b for b in bots if b.name == "SimBot000").tier, "demon")
            self.assertEqual(next(b for b in bots if b.name == "SimBot001").style, "wheelman")

    def test_saved_difficulty_found_as_the_panel_finds_it(self):
        """A pool name with a trailing space or another case takes its saved line (the BOTS panel's pool_clean and no
        case), not a Mixed deal."""
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=4)
            with open(w.paths.bot_pool, "a", encoding="utf-8") as f:
                f.write("Moose Tail Cat Z\nDeath Adder\n")             # (cut to 15: "Moose Tail Cat ")
            with open(w.paths.pool, "a", encoding="utf-8") as f:
                f.write("saved=mythic,any,Moose Tail Cat\nsaved=scaling,objector,Death adder\n")
            bots = {b.name: b for b in bot_sim.population(w.paths, w.settings)}
            self.assertEqual(bots["Moose Tail Cat "].tier, "mythic")
            self.assertEqual((bots["Death Adder"].tier, bots["Death Adder"].style), ("scaling", "objector"))

    def test_demons_play_a_game_every_round(self):
        """(Nov 19, the owner: "all the demon difficulties ... play 1 game to my 1 game") Every Demon bot is entered
        every round; one a lobby could not seat plays first the next round; one in the owner's match sits that round
        out. Never two games a round."""
        rng = se.Rng(5)
        demon, other = bot_sim.Bot(), bot_sim.Bot()
        demon.tier, demon.pace, other.tier, other.pace = "demon", 1.0, "top", 0.0
        self.assertEqual([bot_sim.games_this_round(demon, rng) for _ in range(50)], [1] * 50)
        self.assertEqual([bot_sim.games_this_round(other, rng) for _ in range(50)], [0] * 50)
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=200)
            demons = {b.name for b in bot_sim.population(w.paths, w.settings) if b.tier == "demon"}
            self.assertIn("SimBot000", demons)
            rounds, played = 4, {n: 0 for n in demons}
            for r in range(rounds):
                got = w.round(seed=11 + r)
                _, details, _ = bot_sim.site_entries(w.paths)
                per_round = {}
                for gid, *_ in got:
                    for p in details[gid]["players"]:
                        per_round[p["name"]] = per_round.get(p["name"], 0) + 1
                self.assertLessEqual(max(per_round.values()), 1)          # (one game a round at most)
                for n in demons:
                    played[n] += per_round.get(n, 0)
            # (a Demon a short lobby holds changes places with a non-Demon of a full one; a clan party with no match
            # of its size can still miss a round: nearly all every round)
            self.assertGreaterEqual(sum(played.values()), 0.95 * rounds * len(demons), played)
            self.assertGreaterEqual(min(played.values()), rounds - 1, played)
            now = time.time()
            sat = bot_sim.play_round(w.paths, (now - 900, now - 600), 99, settings=dict(w.settings),
                                     playlists=w.playlists, sit_out=("SimBot000",))
            _, details, _ = bot_sim.site_entries(w.paths)
            self.assertTrue(sat)
            self.assertFalse(any(p["name"] == "SimBot000" for gid, *_ in sat for p in details[gid]["players"]))

    def test_a_round_people_clans_storage_and_the_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=80)
            got = w.round(pace=2.0)
            self.assertTrue(got)
            ledger, details, kills = bot_sim.site_entries(w.paths)
            self.assertEqual(set(ledger), {g for g, *_ in got})
            together = apart = 0
            for gid, d in details.items():
                names = {p["name"]: p for p in d["players"]}
                self.assertNotIn("Person One", names)
                self.assertTrue(all(p["bot"] for p in d["players"]))
                self.assertIn(f"{d['map']}_{d['start']}", kills)
                abc = [p["team"] for n, p in names.items() if n in ("SimBot000", "SimBot001", "SimBot002")]
                if len(abc) > 1:
                    together += len(set(abc)) == 1
                    apart += len(set(abc)) > 1
                self.assertTrue(ledger[gid]["sim"]["seed"])
            self.assertGreaterEqual(together, apart)
            with open(w.paths.matchmaking, encoding="utf-8") as f:
                listed = {l.split("\t")[0] for l in f if not l.startswith("#")}
            self.assertEqual(listed, set(ledger))
            # the site counts them like real matches, a reset covers them
            players, matches = sr.collect(ledger, details, {}, kills=kills, paths=w.paths, bots=w.names,
                                          matchmaking=listed)
            self.assertEqual(len(matches), len(ledger))
            played = sum(1 for d in details.values() for p in d["players"] if p["name"] == "SimBot010")
            self.assertEqual(players["SimBot010"]["g"].get("reach", {}).get("cats", {}).get("all", {}).get("games", 0),
                             played)
            self.assertEqual(sr.career.totals(ledger).get("SimBot010", {}).get("games", 0), played)
            self.assertEqual(bot_sim.mark_reset("bots", w.paths), len(ledger))
            after = bot_sim.ledger_entries(w.paths)
            self.assertTrue(all(m.get("bots_reset") for m in after.values()))
            self.assertEqual(sr.career.totals(after).get("SimBot010", {}).get("games", 0), 0)

    def test_stored_matches_play_again_from_their_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=40)
            got = w.round(seed=3, pace=1.0)
            self.assertTrue(got)
            con = bot_sim.connect(w.paths)
            gid, led, blob = con.execute("SELECT gid, ledger, data FROM matches LIMIT 1").fetchone()
            con.close()
            d = bot_sim.unpack(blob)
            gt = d["spec"]["gametype"]
            info, _, _ = bot_sim.map_info(d["map"], sr.family(gt), w.paths, se.Model(), bot_sim.forge_layouts(w.paths))
            info.real_pairs = []
            out, _, _ = se.play(d["spec"], se.model_from_slice(d["slice"], gt), info, json.loads(led)["sim"]["seed"],
                                d["inputs"])
            self.assertEqual([(r["name"], r["kills"], r["deaths"]) for r in out],
                             [(r["name"], r["kills"], r["deaths"]) for r in d["detail"]["players"]])


class Site(unittest.TestCase):
    def test_the_credits_screen_takes_the_persons_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = sr.Paths(store=os.path.join(tmp, "store"), out=os.path.join(tmp, "site"))
            os.makedirs(paths.out)
            worth = {"game": 1000, "win": 1000, "kill": 100, "assist": 50, "medal": 25}
            bot_row = {"n": "SimBot1", "bot": True, "listed": True, "k": 9, "d": 2, "a": 1, "won": True, "md": 3}
            me = {"n": "Me", "bot": False, "listed": True, "k": 5, "d": 5, "a": 2, "won": False, "md": 1}
            data = {"matches": [{"id": "sim-newer", "game": "reach", "rows": [bot_row]},
                                {"id": "mine", "game": "reach", "rows": [me, bot_row]}],
                    "players": [{"name": "Me", "person": True, "cr": 1550, "rank": 0, "chal": {"cr": 0}}],
                    "ranks": [["Recruit", 0, 0, 0], ["Private", 7500, 1, 0]], "credits": worth}
            sr.write_last_match(data, paths)
            with open(os.path.join(paths.out, "last_match.txt"), encoding="utf-8") as f:
                self.assertIn("match\tmine", f.read())

    def test_today_top_five_and_activity(self):
        now = time.time()
        today = time.strftime("%Y-%m-%d %H:%M", time.localtime(now))
        worth = {"game": 1000, "win": 1000, "kill": 100, "assist": 50, "medal": 25}

        def r(n, k, won):
            return {"n": n, "bot": True, "listed": True, "k": k, "d": 3, "a": 1, "won": won, "md": 0}
        matches = [{"id": f"g{i}", "when": today, "game": "reach", "map": "reach_45_aftship", "type": "TU TEAM SLAYER DMR",
                    "rows": [r(f"A{i}", 10 + i, True), r(f"B{i}", 2, False)]} for i in range(4)]
        t = sr.today_block(matches, worth, {"g0": "ARENA", "g1": "ARENA", "g2": "BIG TEAM BATTLE"}, now)
        self.assertEqual([g["n"] for g in t["top"]], ["A3", "A2", "A1", "A0", "B0"])
        self.assertEqual(t["top"][0]["cr"], 1000 + 1000 + 13 * 100 + 50)
        self.assertEqual(t["games"], 4)
        self.assertEqual(dict(t["playlists"]), {"ARENA": 2, "BIG TEAM BATTLE": 1, "Other": 1})
        self.assertEqual(t["week"][-1], [today[:10], 4])


class OneGameARound(unittest.TestCase):
    """(Nov 19, the owner) a bot plays one simulated game a round at most, however fast its pace, and the bots of the
    match of yours a round goes alongside sit that round out (a queued one keeps its place)."""

    def rosters(self, paths, got):
        con = bot_sim.connect(paths)
        out = {gid: [p["name"] for p in json.loads(led)["players"]]
               for gid, led in con.execute("SELECT gid, ledger FROM matches")}
        con.close()
        return [out[g] for g, *_ in got]

    def test_at_most_one_game_and_the_match_sits_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=120)
            s = dict(w.settings, pace=3.0)                     # (everyone fast: several games a round before)
            now = time.time()
            first = bot_sim.play_round(w.paths, (now - 900, now - 600), 5, settings=s, playlists=w.playlists)
            self.assertTrue(first)
            seats = [n for r in self.rosters(w.paths, first) for n in r]
            self.assertEqual(len(seats), len(set(seats)), "a bot in two matches of one round")
            con = bot_sim.connect(w.paths)
            queued = bot_sim.meta_get(con, "queue", [])
            con.close()
            mine = ["SimBot000", "SimBot001", "SimBot002"] + queued[:2]
            got = bot_sim.play_round(w.paths, (now - 500, now - 200), 6, settings=s, playlists=w.playlists,
                                     sit_out=[n.upper() for n in mine])   # (names match without case)
            seats = [n for r in self.rosters(w.paths, got) for n in r]
            self.assertTrue(seats)
            self.assertEqual(len(seats), len(set(seats)))
            self.assertFalse(set(mine) & set(seats), "a bot of your match played the round alongside it")
            con = bot_sim.connect(w.paths)
            queue = bot_sim.meta_get(con, "queue", [])
            con.close()
            self.assertEqual(queue[:len(queued[:2])], queued[:2], "a queued bot of your match lost its place")

    def test_bots_in_reads_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=10)
            with open(w.paths.ledger, "w", encoding="utf-8") as f:
                json.dump({"g1": {"players": [{"name": "Person One", "bot": False}, {"name": "SimBot003", "bot": True},
                                              {"name": "", "bot": True}]}}, f)
            self.assertEqual(bot_sim.bots_in(w.paths, "g1"), ["SimBot003"])
            self.assertEqual(bot_sim.bots_in(w.paths, "nope"), [])


if __name__ == "__main__":
    unittest.main()

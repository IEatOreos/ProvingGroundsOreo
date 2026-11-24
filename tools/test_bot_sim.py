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
        # (Nov 23: a fitted model's fights at SKILL_SCALE times the tier's gaps)
        self.assertEqual(m.inputs_of("r0", "strong")["s"], round(se.SKILL_SCALE * se.TIER_SKILL["strong"], 4))
        self.assertEqual(m.inputs_of("r1", "demon")["s"], round(se.SKILL_SCALE * se.TIER_SKILL["demon"], 4))


class Population(unittest.TestCase):
    def test_pace_averages_what_is_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=400)
            few = dict(w.settings, **{"grinder_" + t: 0.05 for t in bot_sim.GRINDER_CHANCE})
            bots = bot_sim.population(w.paths, few)
            self.assertEqual(len(bots), 400)                  # (the person left out)
            paced = [b for b in bots if b.tier not in bot_sim.EVERY_ROUND      # (Demons: every round, pace 1;
                     and b.tier not in bot_sim.FLIP_FLOP]                     # Heroic, Tactician: every other)
            self.assertAlmostEqual(sum(b.pace for b in paced) / len(paced), w.settings["pace"], places=6)
            self.assertTrue(all(b.pace == 1.0 for b in bots if b.tier in bot_sim.EVERY_ROUND))
            # (Nov 20, the owner, "make it bigger": many grinders keep their full pace and the round grows; the others
            # never drop under other_pace)
            bots = bot_sim.population(w.paths, w.settings)
            base = lambda b: __import__("math").exp(w.settings["spread"] * se.Rng(se.hash_of(b.name, 43)).gauss())
            paced = [b for b in bots if b.tier not in bot_sim.EVERY_ROUND and b.tier not in bot_sim.FLIP_FLOP]
            self.assertGreater(sum(b.grinder for b in paced), 50)
            for b in paced:
                want = w.settings["grinder_pace"] if b.grinder else w.settings["other_pace"]
                if b.grinder:
                    self.assertAlmostEqual(b.pace, base(b) * want, places=9, msg=b.name)
                else:
                    self.assertGreaterEqual(b.pace, base(b) * want - 1e-12, b.name)
            self.assertGreater(sum(b.pace for b in paced) / len(paced), w.settings["pace"])
            # (Nov 20, the owner: one roll a bot at its difficulty's chance, Demon 75% down to Easy 5%)
            for b in bots:
                self.assertEqual(b.grinder, se.hfloat(b.name, 41) < bot_sim.GRINDER_CHANCE[b.tier], b.name)
            self.assertEqual(bot_sim.grinder_chance("novice", w.settings), 0.05)
            self.assertEqual(bot_sim.grinder_chance("novice", dict(w.settings, grinder_novice=0.5)), 0.5)
            rates = {}
            for b in bots:
                rates.setdefault(b.tier, []).append(b.grinder)
            for t, gs in rates.items():
                if len(gs) >= 40:
                    self.assertAlmostEqual(sum(gs) / len(gs), bot_sim.GRINDER_CHANCE[t], delta=0.2, msg=t)
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

    def test_noble_plays_like_demon_and_btb_slayer_to_100(self):
        """(Nov 23, the owner: Noble "like demon"; BTB Slayer "to 100", the real matches' name in another case)"""
        for table in (se.TIER_SKILL, se.SWEAT, bot_sim.GRINDER_CHANCE):     # (Demon's base; its edge: skill_of)
            self.assertEqual(table["noble"], table["demon"])
        self.assertIn("noble", bot_sim.EVERY_ROUND)
        # (Nov 23, the owner: Nobles "5-10% better than demons": each wins 55-60% of even fights against a Demon, its
        # own fixed roll)
        wins = [se.sigmoid(se.skill_of(f"Noble{i}", "noble") - se.skill_of("x", "demon")) for i in range(300)]
        self.assertTrue(all(0.55 - 1e-9 <= w <= 0.60 + 1e-9 for w in wins))
        self.assertGreater(max(wins) - min(wins), 0.04)                  # (spread over the range)
        self.assertEqual(se.skill_of("A", "noble"), se.skill_of("A", "noble"))
        self.assertEqual(se.skill_of("A", "demon"), se.TIER_SKILL["demon"])
        self.assertEqual(se.Model().inputs_of("A", "noble")["s"], round(se.skill_of("A", "noble"), 4))
        self.assertIn("noble", se.TIERS)
        self.assertEqual(bot_sim.tier_of("Anyone", {"anyone": ("noble", "any")}, 4), "noble")
        self.assertEqual(bot_sim.tier_of("Anyone", {}, 10), "noble")
        m = se.Model()
        m.limits = {("TU BTB Team Slayer", 8): (50, 720), ("TU TEAM SLAYER DMR", 4): (50, 600)}
        self.assertEqual(se.limits_of(m, "TU BTB TEAM SLAYER", 8), (50, 720))      # (a stored slice's: as played)
        m.score_rules = dict(se.SCORE_RULES)                                         # (as fit sets it)
        self.assertEqual(se.limits_of(m, "TU BTB TEAM SLAYER", 8), (100, 720))
        self.assertEqual(se.limits_of(m, "TU TEAM SLAYER DMR", 4), (50, 600))      # (4v4 as it was)
        self.assertEqual(se.limits_of(se.Model(), "TU MULTI FLAG CTF", 8), (3, 720))

    def test_steeper_gaps_hunting_and_flip_flop(self):
        """(Nov 23, the owner: "Yes, flip flop + B") New matches' fights at twice TIER_SKILL's gaps with hunting, stored
        in the slice (an older slice: 1 and 0); a Noble still 55-60% against a Demon; Heroics and Tacticians every other
        round in two halves that take turns."""
        self.assertEqual(se.skill_of("A", "demon", 2.0), 2 * se.TIER_SKILL["demon"])
        edge = se.skill_of("A", "noble", 2.0) - se.skill_of("B", "demon", 2.0)
        self.assertTrue(0.55 - 1e-9 <= se.sigmoid(edge) <= 0.60 + 1e-9)
        m = se.Model()
        self.assertEqual((m.skill_scale, m.hunt), (1.0, 0.0))
        self.assertEqual(m.inputs_of("A", "demon")["s"], se.TIER_SKILL["demon"])    # (a bare model: as before)
        m.skill_scale, m.hunt = se.SKILL_SCALE, se.HUNT
        self.assertEqual(m.inputs_of("A", "demon")["s"], round(se.SKILL_SCALE * se.TIER_SKILL["demon"], 4))
        sl = se.model_slice(m, "TU TEAM SLAYER DMR", 4)
        self.assertEqual((sl["scale"], sl["hunt"]), (se.SKILL_SCALE, se.HUNT))
        back = se.model_from_slice(sl, "TU TEAM SLAYER DMR")
        self.assertEqual((back.skill_scale, back.hunt), (se.SKILL_SCALE, se.HUNT))
        del sl["scale"], sl["hunt"]
        old = se.model_from_slice(sl, "TU TEAM SLAYER DMR")
        self.assertEqual((old.skill_scale, old.hunt), (1.0, 0.0))
        # Demons against Heroics: hunting and the steeper gaps lift the Demons' K/D
        players = [{"name": f"d{j}", "team": 0, "tier": "demon", "style": "any", "clan": ""} for j in range(4)] + \
                  [{"name": f"h{j}", "team": 1, "tier": "strong", "style": "any", "clan": ""} for j in range(4)]
        spec = {"gametype": "TU TEAM SLAYER DMR", "size": 4, "players": players}

        def demon_kd(model):
            k = d = 0
            for i in range(10):
                rep, _, _ = se.play(spec, model, countdown(), 70 + i)
                k += sum(p["kills"] for p in rep if p["team"] == 0)
                d += sum(p["deaths"] for p in rep if p["team"] == 0)
            return k / max(1, d)
        self.assertGreater(demon_kd(m), demon_kd(se.Model()) * 1.5)
        # flip flop
        b = bot_sim.Bot()
        b.name, b.tier, b.pace = "Flipper", "tactician", 0.0
        rng = se.Rng(1)
        turns = [bot_sim.games_this_round(b, rng, r) for r in range(10)]
        self.assertEqual(turns, [int(bot_sim.flip_half("Flipper") == r % 2) for r in range(10)])
        self.assertEqual(sum(turns), 5)
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=200)
            bots = bot_sim.population(w.paths, w.settings)
            flips = [x for x in bots if x.tier in bot_sim.FLIP_FLOP]
            self.assertTrue(flips and all(x.pace == 0.5 for x in flips))
            halves = [bot_sim.flip_half(x.name) for x in flips]
            self.assertTrue(0 < sum(halves) < len(halves))                   # (both halves have bots)

    def test_multi_flag_as_the_owners_games(self):
        """(Nov 23, the owner: Multi Flag "to match" his Asylum game, captures about one a team every 25 minutes between
        even teams, more lopsided with a skill gap) The fitted model carries the rules, the stored slice too, an old
        slice without them plays as before."""
        m = se.Model()
        m.kpm_by, m.kpm_size = {"ctf": 1.29}, {("ctf", 4): 1.38}
        self.assertEqual(se.kpm_of(m, "ctf", 4, "TU MULTI FLAG CTF"), 1.38)         # (a bare Model: no rules)
        m.kpm_game, m.obj_rules = dict(se.KPM_RULES), dict(se.OBJ_RULES)
        self.assertEqual(se.kpm_of(m, "ctf", 4, "TU MULTI FLAG CTF"), 1.73)
        self.assertEqual(se.kpm_of(m, "ctf", 8, "TU MULTI FLAG CTF"), 1.29)         # (8v8: the real ones')
        self.assertEqual(se.kpm_of(m, "ctf", 4, "TU ONE FLAG CTF (4-10)"), 1.38)
        self.assertEqual(se.obj_rule_of(m, "TU MULTI FLAG CTF", "ctf"), se.OBJ_RULES["tu multi flag ctf"])
        self.assertEqual(se.obj_rule_of(m, "TU ONE FLAG CTF (4-10)", "ctf"), (se.OBJ_RATE["ctf"], 1.0))
        self.assertIsNone(se.obj_rule_of(m, "TU TEAM SLAYER DMR", "slayer"))
        sl = se.model_slice(m, "TU MULTI FLAG CTF", 4)
        self.assertEqual((sl["kpm"], sl["obj"]), (1.73, list(se.OBJ_RULES["tu multi flag ctf"])))
        back = se.model_from_slice(sl, "TU MULTI FLAG CTF")
        self.assertEqual(se.obj_rule_of(back, "TU MULTI FLAG CTF", "ctf"), se.OBJ_RULES["tu multi flag ctf"])
        self.assertEqual(se.kpm_of(back, "ctf", 4, "TU MULTI FLAG CTF"), 1.73)
        old = dict(sl)
        del old["obj"]
        self.assertEqual(se.obj_rule_of(se.model_from_slice(old, "TU MULTI FLAG CTF"), "TU MULTI FLAG CTF", "ctf"),
                         (se.OBJ_RATE["ctf"], 1.0))
        # even teams on Countdown: few captures, most games to time
        caps = mins = 0
        for i in range(12):
            players = [{"name": f"b{j}", "team": j % 2, "tier": "top", "style": "any", "clan": ""} for j in range(8)]
            _, _, res = se.play({"gametype": "TU MULTI FLAG CTF", "size": 4, "players": players}, m, countdown("ctf"),
                                40 + i)
            caps += sum(res["scores"].values())
            mins += res["seconds"] / 60
        self.assertLess(caps / 12, 2.0)
        self.assertGreater(mins / 12, 9.0)

    def test_a_clan_queues_as_one_group(self):
        """(Nov 20, the owner) A clan that queues together plays the round when any member would, every member, one
        playlist, one team: clan ABC's SimBot000 is a Demon (every round), so SimBot001 and SimBot002, at a pace that
        alone would almost never play, join it most rounds."""
        rng = se.Rng(3)
        self.assertEqual(bot_sim.clans_together([], rng), set())
        picks = [bot_sim.clans_together([type("B", (), {"clan": c})() for c in ("A", "a", "B")], rng)
                 for _ in range(400)]
        self.assertTrue(all(p <= {"a"} for p in picks))                 # (a clan of one never "queues together")
        self.assertAlmostEqual(sum("a" in p for p in picks) / 400, bot_sim.CLAN_TOGETHER, delta=0.06)
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=240)
            w.settings.update({"grinder_" + t: 0.0 for t in bot_sim.GRINDER_CHANCE}, other_pace=0.0)
            rounds, whole, apart = 12, 0, 0
            for r in range(rounds):
                got = w.round(seed=31 + r, pace=0.02)
                _, details, _ = bot_sim.site_entries(w.paths)
                for gid, *_ in got:
                    abc = [p["team"] for p in details[gid]["players"]
                           if p["name"] in ("SimBot000", "SimBot001", "SimBot002")]
                    whole += len(abc) == 3 and len(set(abc)) == 1         # (a party is on one team)
                    apart += len(set(abc)) > 1                            # (a round it queued alone: 15%)
            self.assertGreaterEqual(whole, rounds // 2)
            self.assertLessEqual(apart, rounds // 4)

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

    def test_last_match_says_how_it_ended_for_the_person(self):
        # (Nov 23, the owner's live points: +2 a win, -1 a loss; the game reads the result line)
        worth = {"game": 1000, "win": 1000, "kill": 100, "assist": 50, "medal": 25}
        for won, my_st, bot_st, want in ((True, 0, 1, "win"), (False, 1, 0, "loss"), (False, 0, 0, "tie")):
            with tempfile.TemporaryDirectory() as tmp:
                paths = sr.Paths(store=os.path.join(tmp, "store"), out=os.path.join(tmp, "site"))
                os.makedirs(paths.out)
                me = {"n": "Me", "bot": False, "listed": True, "k": 5, "d": 5, "a": 2, "won": won, "md": 1, "st": my_st}
                bot = {"n": "Bot", "bot": True, "listed": True, "k": 5, "d": 5, "a": 2, "won": not won and bot_st == 0,
                       "md": 1, "st": bot_st}
                data = {"matches": [{"id": "g1", "game": "reach", "rows": [me, bot]}],
                        "players": [{"name": "Me", "person": True, "cr": 2000, "rank": 0, "chal": {"cr": 0}}],
                        "ranks": [["Recruit", 0, 0, 0], ["Private", 7500, 1, 0]], "credits": worth}
                sr.write_last_match(data, paths)
                with open(os.path.join(paths.out, "last_match.txt"), encoding="utf-8") as f:
                    self.assertIn(f"result\tMe\t{want}\n", f.read())

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

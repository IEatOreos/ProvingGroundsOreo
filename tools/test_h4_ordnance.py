"""Halo 4 ordnance pickups (custom, Nov 8): a gun in its drop pod lies loose (LiveH4F.ground_weapons), the map's
initial drops are items that are gone once seen taken and back once seen again, a random drop's power gun gets the
team's run, and Halo 4 bots may pick guns up. H2A and the other games are unchanged."""
import os
import random
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import maps                                         # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402
from brain.director import Director                            # noqa: E402
from brain.live import NONE, LiveH4F, brain_name               # noqa: E402
from brain.profiles import make_profile                        # noqa: E402

ENTS = 0x1000


class Memory:
    def __init__(s):
        s.blocks = {}

    def put(s, addr, data):
        s.blocks[addr] = bytearray(data)

    def read(s, addr, n):
        for base, b in s.blocks.items():
            if base <= addr and addr + n <= base + len(b):
                return bytes(b[addr - base:addr - base + n])
        return bytes(n)


def reader(game="h4"):
    """A stand-in Halo 4 / H2A reader: a biped, a drop pod (type 6), a vehicle, and guns held by each or by nothing."""
    live = LiveH4F.__new__(LiveH4F)
    live.TAG_GAME, live.g, live._names = game, Memory(), {}
    things = [(0, None), (6, None), (1, None),            # 0 biped, 1 the pod, 2 a vehicle
              (2, 0), (2, 1), (2, None), (2, 2), (2, 1)]  # guns: held, in the pod, dropped, on the vehicle, empty pod gun
    names = {3: "battle_rifle", 4: "railgun", 5: "dmr", 6: "machinegun_mounted", 7: "sniper"}
    table = bytearray(len(things) * 0x18)
    for i, (typ, parent) in enumerate(things):
        addr = 0x10000 + i * 0x100
        struct.pack_into("<H", table, i * 0x18, 0x20 + i)
        table[i * 0x18 + 4] = typ
        struct.pack_into("<Q", table, i * 0x18 + 0x10, addr)
        obj = bytearray(0x100)
        struct.pack_into("<I", obj, live.PARENT_AT, NONE if parent is None else ((0x20 + parent) << 16) | parent)
        live.g.put(addr, obj)
    live.g.put(ENTS, table)
    handles = {i: ((0x20 + i) << 16) | i for i in range(len(things))}
    live._array = lambda off: (ENTS, len(things), 0)
    live.objects = lambda types=None: [(handles[i], 2, n, (float(i), 0.0, 0.0)) for i, n in names.items()]
    live.object = lambda h: 0x10000 + (h & 0xFFFF) * 0x100
    live.rounds = lambda h: (0, 0) if h & 0xFFFF == 7 else (10, 5)
    return live


class ReaderTests(unittest.TestCase):
    def test_a_gun_in_its_pod_lies_loose(self):
        self.assertEqual(sorted(n for n, q in reader().ground_weapons()), ["dmr", "railgun"])

    def test_h2a_unchanged(self):
        self.assertEqual([n for n, q in reader("h2a").ground_weapons()], ["dmr"])

    def test_names(self):
        self.assertEqual(brain_name("storm_forerunner_incineration_launcher"), "incineration_cannon")
        self.assertEqual(brain_name("storm_forerunner_sniper_rifle"), "binary_rifle")
        self.assertEqual(brain_name("storm_rail_gun"), "railgun")
        self.assertEqual(brain_name("storm_spread_gun"), "scattershot")


def place(item, ordnance, pos=(0.0, 0.0, 0.0)):
    return dict(item=item, pos=list(pos), spawn_time=0, ordnance=ordnance)


class MapTests(unittest.TestCase):
    objs = {"equipment": [place("rockets", "initial"), place("binary_rifle", "initial", (5, 0, 0)),
                          place("needler", "initial", (9, 0, 0)), place("railgun", "random", (20, 0, 0)),
                          place("rockets", "random", (30, 0, 0)), place("scattershot", "random", (40, 0, 0)),
                          place("needler", "random", (50, 0, 0))]}

    def test_initial_drops_are_items_gone_once_taken(self):
        items = maps.power_items(self.objs, h4=True)
        self.assertEqual([it["name"] for it in items], ["rockets", "binary_rifle"])
        for it in items:
            self.assertEqual(it["ordnance"], "initial")
            self.assertEqual(it["respawn"], maps.ORDNANCE_GONE)
        self.assertAlmostEqual(items[1]["value"], 0.85)

    def test_random_points_are_power_names_only(self):
        self.assertEqual(maps.ordnance_power(self.objs), ["railgun", "rockets"])

    def test_other_games_unchanged(self):
        items = maps.power_items(self.objs)
        self.assertEqual([it["name"] for it in items], ["rockets", "rockets"])
        self.assertTrue(all(it["respawn"] == 45 and "ordnance" not in it for it in items))

    @unittest.skipUnless(os.path.exists(os.path.join(maps.ROOT, "h4_ca_redoubt", "objects.json")), "no map data")
    def test_redoubt(self):
        m = maps.get_map("h4_ca_redoubt")
        self.assertEqual(sorted(it["name"] for it in m["items"]),
                         ["sniper", "sniper", "sticky_detonator", "sticky_detonator"])
        self.assertEqual(m["ordnance_power"], ["incineration_cannon", "railgun", "rockets", "sniper", "spartan_laser"])


class DirectorTests(unittest.TestCase):
    def test_a_random_drop_gets_a_run(self):
        prof = make_profile("strong", "rusher", random.Random(1))
        bot = SimpleNamespace(id=0, p=prof, urgent=lambda *a: False, pressing=lambda *a: False)
        me = PlayerState(0, 0, "me", Vec(10, 0, 0), weapon="battle_rifle", weapons=["battle_rifle", "magnum"])
        d = Director.__new__(Director)
        d.map, d.bots, d.item_up = {"items": [], "ordnance_power": ["railgun"]}, {0: bot}, {}
        d.power_runs(100.0, Snapshot(100.0, [me], ground_weapons=[("railgun", Vec(0, 0, 0))]))
        self.assertIsNotNone(bot.fetch)
        self.assertEqual(bot.fetch[1], "railgun")
        bot.fetch = None
        d.map["ordnance_power"] = []
        d.power_runs(100.0, Snapshot(100.0, [me], ground_weapons=[("railgun", Vec(0, 0, 0))]))
        self.assertIsNone(bot.fetch)


class BotTests(unittest.TestCase):
    def test_a_pod_gun_is_worth_the_walk(self):
        from brain.bot import Bot
        for gun in ("incineration_cannon", "binary_rifle", "railgun", "rockets"):
            b = Bot(0, 0, make_profile("strong", "rusher", random.Random(3)), {"name": "h4_ca_redoubt"},
                    random.Random(5))
            me = PlayerState(0, 0, "me", Vec(0, 0, 0.38), weapon="battle_rifle", weapons=["battle_rifle", "magnum"],
                             ammo=[60, 24], mag=[36, 8])
            q = Vec(6.0, 0.0, 0.6)                    # (a pod holds its gun a few tenths over the floor)
            self.assertEqual(b.upgrade_point(me, Snapshot(10.0, [me], ground_weapons=[(gun, q)]), reach=12.0), q, gun)


class ItemCheckTests(unittest.TestCase):
    def setUp(s):
        import live_bots
        s.lb = live_bots
        s.saved = live_bots.MAP, dict(live_bots.GROUND)

    def tearDown(s):
        s.lb.MAP = s.saved[0]
        s.lb.GROUND.clear()
        s.lb.GROUND.update(s.saved[1])

    def test_gone_then_back(self):
        lb = self.lb
        spot = Vec(0, 0, 0)
        lb.MAP = {"items": [dict(name="sniper", kind="weapon", value=0.8, pos=spot, respawn=maps.ORDNANCE_GONE,
                                 ordnance="initial")]}
        d = SimpleNamespace(item_up={0: 0.0}, bots={0: SimpleNamespace(id=0)})
        d.item_taken = lambda i, now, respawn: d.item_up.__setitem__(i, now + respawn)
        me = PlayerState(0, 0, "me", Vec(5, 0, 0))
        snap = Snapshot(10.0, [me])
        empty = SimpleNamespace(objects=lambda types: [])
        lb.item_check(empty, {0: d}, {}, snap, 10.0)
        self.assertEqual(d.item_up[0], 10.0 + maps.ORDNANCE_GONE)
        pod = SimpleNamespace(objects=lambda types: [(1, 2, "sniper", (0.0, 0.0, 0.3))])
        lb.GROUND["list"] = []                      # (held, not loose: not back)
        lb.item_check(pod, {0: d}, {}, snap, 20.0)
        self.assertGreater(d.item_up[0], 20.0)
        lb.GROUND["list"] = [("sniper", Vec(0.0, 0.0, 0.3))]
        lb.item_check(pod, {0: d}, {}, snap, 20.0)
        self.assertEqual(d.item_up[0], 0.0)

    def test_halo4_bots_pick_up(self):
        self.assertIn("h4", self.lb.PICKUP_GAMES)
        self.assertNotIn("h2a", self.lb.PICKUP_GAMES)


if __name__ == "__main__":
    unittest.main()

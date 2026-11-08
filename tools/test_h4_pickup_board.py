"""Halo 4 pickups and hijacks (custom, Nov 8). A bot on a gun holds Use (Halo 4 takes a gun only on a held press; the
other games keep the tap). A bot boarding an enemy vehicle asks botcore for a boarding / hijack spot
(vehicles.H4_BOARD_SEAT, native/h4f.cpp f_board), where Reach asks for its boarding seats and the rest for the driver's."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import profiles, vehicles                      # noqa: E402
from brain.bot import Bot, Order                          # noqa: E402
from brain.core import PlayerState, Snapshot, Vec         # noqa: E402

HERE = Path(__file__).resolve().parents[1]


class Flat:
    """Open level ground: every line clear, every way straight."""
    crouch_cells = ()

    def __getattr__(s, name):
        return lambda *a, **k: None

    def los(s, *a, **k):
        return True

    def point_los(s, *a, **k):
        return True

    def sees(s, *a, **k):
        return True

    def nav(s, a, b, *k, **kw):
        return b

    def vnav(s, a, b):
        return b

    def height_over(s, *a):
        return 0.0

    def inside(s, *a):
        return True

    def clearance(s, *a, **k):
        return 9.0


def make(game_map, tier="strong"):
    mapdata = dict(name=game_map, flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)},
                   holds={0: [Vec(90, 0, 0)], 1: [Vec(190, 0, 0)]}, items=[])
    b = Bot(0, 0, profiles.make_profile(tier, "rusher", random.Random(3)), mapdata, random.Random(5))
    b.order = Order("mid", Vec(80, 0, 0))
    b.notes = []
    b._terrain = Flat()
    b.T = lambda: b._terrain
    return b


def tick(b, now, me, snap, goal):
    b.goal, b.next_decide = goal, now + 99.0           # (the goal held: decide is not what is checked)
    return b.plan(now, 1 / 30, snap, lambda a, c: True, lambda a, c, **k: c, [])


class PickupTests(unittest.TestCase):
    def presses(self, game_map):
        b = make(game_map)
        gun = Vec(0.3, 0.0, 0.0)
        me = PlayerState(0, 0, "me", Vec(0, 0, 0), weapon="magnum", weapons=["battle_rifle", "magnum"],
                         ammo=[60, 24], mag=[36, 8])
        out = []
        for i in range(12):
            now = 10.0 + i / 30
            snap = Snapshot(now, [me], ground_weapons=[("rockets", gun)])
            try:
                act = tick(b, now, me, snap, ("item", gun))
            except Exception as e:                  # (a stand-in world: the press is what is checked)
                self.fail(f"plan failed: {e!r}")
            out.append(bool(act.action))
        return out

    def test_halo4_holds_use_on_a_gun(self):
        self.assertTrue(all(self.presses("h4_test")))

    def test_reach_still_taps(self):
        out = self.presses("reach_test")
        self.assertTrue(any(out))
        self.assertFalse(all(out))


class BoardTests(unittest.TestCase):
    def board(self, game_map, kind):
        b = make(game_map)
        v = dict(handle=30, kind=kind, pos=(1.0, 0.0, 0.0), fwd=(1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0), occupied=True,
                 team=1, riders=1, turrets=[], manned=[])
        me = PlayerState(0, 0, "me", Vec(0, 0, 0), weapon="battle_rifle", weapons=["battle_rifle"])
        driver = PlayerState(1, 1, "him", Vec(1.0, 0.0, 0.0), vehicle=30)
        seats = set()
        for i in range(60):
            now = 10.0 + i / 30
            act = tick(b, now, me, Snapshot(now, [me, driver], vehicles=[v]), ("board", 30))
            if act.action:
                seats.add((act.seat, act.turret))
        return seats

    def test_halo4_asks_for_a_boarding_spot(self):
        for kind in ("storm_ghost", "storm_warthog", "storm_mongoose", "storm_scorpion"):
            self.assertEqual(self.board("h4_test", kind), {(vehicles.H4_BOARD_SEAT, False)}, kind)

    def test_reach_keeps_its_boarding_seats(self):
        seats = self.board("reach_test", "warthog")
        self.assertTrue(seats)
        self.assertTrue(all(s[0] in vehicles.REACH_BOARD["warthog"] for s in seats), seats)


class NativeTests(unittest.TestCase):
    def test_the_seat_number_matches_botcore(self):
        text = (HERE / "native" / "shared.h").read_text(encoding="utf-8", errors="replace")
        self.assertIn(f"HB_SEAT_BOARD = {vehicles.H4_BOARD_SEAT};", text)
        self.assertLess(vehicles.H4_BOARD_SEAT, 15)        # (4 bits: seat + 1, tools/live_bots.py buttons)
        src = (HERE / "native" / "h4f.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("want == HB_SEAT_BOARD", src)


if __name__ == "__main__":
    unittest.main()

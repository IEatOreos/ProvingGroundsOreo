"""(custom, Nov 14) A flag or bomb carrier the director told to board a vehicle stays in its passenger seat. The board
order's point is where the vehicle stood, and the 'ferried home, out on our stand' rule read that as home: live Tempest
20261113-234604, a Demon bomb carrier got out of a Warthog's passenger seat 11 times in 90 s at one spot, a second after
each time it got in. On the run home (a runner order) the carrier still gets out by its stand."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import profiles                                 # noqa: E402
from brain.bot import Bot, Order                           # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from test_h4_pickup_board import Flat                      # noqa: E402

HOG = 20


def ride(game_map, order, tier="demon"):
    """A carrier 2 s into a Warthog's passenger seat at (10, 18), a teammate at the wheel: did it get out?"""
    mapdata = dict(name=game_map, flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)},
                   items=[])
    b = Bot(0, 0, profiles.make_profile(tier, "rusher", random.Random(3)), mapdata, random.Random(5))
    b.seat, b.seat_for, b.seat_since, b.notes = "passenger", HOG, 98.0, []
    b.order = order
    b._terrain = Flat()
    b.T = lambda b=b: b._terrain
    me = PlayerState(0, 0, "me", Vec(10, 18, 0), vehicle=HOG, has_flag=True)
    driver = PlayerState(1, 0, "driver", Vec(10, 18, 0), vehicle=HOG)
    hog = dict(handle=HOG, kind="warthog", pos=(10.0, 18.0, 0.0), occupied=True, team=0, riders=2, fwd=(1, 0, 0),
               up=(0, 0, 1))
    act = Action()
    b.drive(100.0, 1 / 30, me, Snapshot(100, [me, driver], vehicles=[hog], mode="assault"), act, lambda a, c: c)
    return act.action, b.notes


class BoardLoopTests(unittest.TestCase):
    def test_a_boarded_carrier_stays_in(self):
        for game_map in ("reach_dlc_medium", "h4_test"):
            for tier in ("demon", "top", "strong", "average"):
                out, notes = ride(game_map, Order("board", Vec(10, 18, 0), target=HOG), tier)
                self.assertFalse(out, (game_map, tier, notes))
                self.assertNotIn("vehicle: home with the flag, out", notes)

    def test_still_out_by_the_stand_on_the_run_home(self):
        for game_map in ("reach_dlc_medium", "h4_test"):
            out, notes = ride(game_map, Order("runner", Vec(12, 18, 0)))
            self.assertTrue(out, game_map)
            self.assertIn("vehicle: home with the flag, out", notes)

    def test_not_out_far_from_the_stand(self):
        out, notes = ride("reach_dlc_medium", Order("runner", Vec(80, 18, 0)))
        self.assertNotIn("vehicle: home with the flag, out", notes)


if __name__ == "__main__":
    unittest.main()

"""(custom, Nov 13) A Scorpion's or Wraith's driver: a man on foot within TANK_FOOT_R first, then a vehicle within
TANK_VEHICLE_R, then the best of the rest by the guide's score (Bot.vehicle_pick). The owner: "a tank driver, scorpion
or wraith prioritizes killing an enemy that's within so many units, then prioritizes vehicles", "we can try that"."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import profiles, vehicles                            # noqa: E402
from brain.bot import TANK_FOOT_R, TANK_VEHICLE_R, Belief, Bot  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402


def pick(kind, enemies, tier="strong", seat="driver"):
    """enemies: [(id, x, his vehicle kind or None, weapon)] straight ahead of a tank at the origin facing +x."""
    b = Bot(0, 0, profiles.make_profile(tier, "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
    me = PlayerState(0, 0, "bot", Vec(), vehicle=1)
    tank = dict(handle=1, kind=kind, pos=(0, 0, 0), occupied=True, team=0, riders=1, fwd=(1, 0, 0))
    players, vs = [me], [tank]
    for k, x, vk, gun in enemies:
        p = PlayerState(k, 1, f"e{k}", Vec(x, 0.0, 0.0), weapon=gun, vehicle=-1 if vk is None else 100 + k)
        players.append(p)
        if vk is not None:
            vs.append(dict(handle=100 + k, kind=vk, pos=(x, 0, 0), occupied=True, team=1, riders=1, fwd=(-1, 0, 0)))
        b.per.beliefs[k] = Belief(p.pos, Vec(), 0.0, True, "eyes")
    snap = Snapshot(0.0, players, vehicles=vs, mode="slayer")
    return b.vehicle_pick(me, tank, seat, [e[0] for e in enemies], snap)


class TankTargetTests(unittest.TestCase):
    def test_close_man_on_foot_first(self):
        for kind in ("scorpion", "wraith"):
            self.assertEqual(pick(kind, [(1, 25.0, "warthog", "pistol"), (2, TANK_FOOT_R - 2, None, "pistol")]), 2, kind)

    def test_then_a_vehicle_in_range_over_men_farther_off(self):
        enemies = [(1, 30.0, "mongoose", "pistol"), (2, 20.0, None, "pistol")]
        self.assertEqual(pick("scorpion", enemies), 1)
        self.assertEqual(pick("wraith", enemies), 1)

    def test_a_rocket_man_in_range_counts_with_the_vehicles(self):
        # (the owner: "change the one mongoose scenario") a man with rockets 20 u off over a Mongoose 30 u off
        enemies = [(1, 30.0, "mongoose", "pistol"), (2, 20.0, None, "rockets")]
        for kind in ("scorpion", "wraith"):
            self.assertEqual(pick(kind, enemies), 2, kind)
        far = [(1, 30.0, "mongoose", "pistol"), (2, TANK_VEHICLE_R + 5, None, "rockets")]
        self.assertEqual(pick("scorpion", far), 1)            # (past 40 u: one of the rest)

    def test_nearer_vehicle_band_by_score(self):
        self.assertEqual(pick("scorpion", [(1, 30.0, "mongoose", "pistol"), (2, 35.0, "banshee", "pistol")]),
                         pick("scorpion", [(2, 35.0, "banshee", "pistol"), (1, 30.0, "mongoose", "pistol")]))

    def test_beyond_both_ranges_as_before(self):
        far = [(1, TANK_VEHICLE_R + 10, "warthog", "pistol"), (2, 15.0, None, "pistol")]
        gun = vehicles.seat_gun("scorpion", "driver")
        score = {1: vehicles.target_score("reach", "scorpion", gun, "driver", "warthog", d=50.0) - 1e-4 * 50,
                 2: vehicles.target_score("reach", "scorpion", gun, "driver", None, d=15.0, in_ram=True) - 1e-4 * 15}
        self.assertEqual(pick("scorpion", far), max(score, key=score.get))   # (the plain score, as before)
        # nobody close, no vehicle in range: the plain score, the same pick a Mantis (not covered) makes
        self.assertEqual(pick("scorpion", [(2, 15.0, None, "pistol")]), 2)

    def test_close_man_over_a_vehicle_the_old_score_preferred(self):
        enemies = [(1, 15.0, "banshee", "pistol"), (2, 8.0, None, "pistol")]
        self.assertEqual(pick("mantis", enemies), 1)
        self.assertEqual(pick("scorpion", enemies), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""(custom, Nov 26) A Reach Banshee pilot's bomb goes on the man it can bomb now (Bot.air_bomb_man), and it sees men under
and beside its craft (Perception's 3D view cone for that pilot only), never through a wall.

tools/banshee_sim.py, Boneyard (Nov 26): with this and the nose-on release (Bot.bomb_release) the pilot got 13, 20, 14,
6, 8, 15, 8, 14 Banshee kills a game, against 3.8 a game for the pilot before (14 games). Its review: the 3D cone applied
to every aircraft pilot in every game (fixed: the Reach Banshee pilot only), and two helper calls that would have raised
NameError in the real file (fixed)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain.bot as B  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from test_banshee_bomb_aim import Air, banshee  # noqa: E402
from test_demon_vehicles import bot  # noqa: E402


def pilot(game="reach", kind="banshee", seat="driver"):
    b = bot("demon", name=game + "_test")
    b.seat, b.veh_kind, b.can_cycle = seat, kind, True
    b._terrain = Air()
    b.T = lambda: b._terrain
    b.air_terrain = lambda: b._terrain
    return b


def fresh(game="reach", veh=None, foe_at=Vec(-10.0, 0.0, 0.0), foe_veh=-1):
    b = pilot(game)
    me = PlayerState(0, 0, "bot", Vec(0, 0, 9.0), vel=Vec(-6, 0, 0), yaw=math.pi, pitch=-0.5, vehicle=77, weapon="banshee")
    foe = PlayerState(1, 1, "foe", foe_at, vehicle=foe_veh, weapon="assault_rifle", weapons=["assault_rifle"])
    snap = Snapshot(50.0, [me, foe], vehicles=veh if veh is not None else [banshee()], mode="slayer")
    b.per.beliefs[1] = B.Belief(foe.pos, Vec(), 50.0, True, "eyes")
    b.per.recognized.add(1)
    b.per.last_seen[1] = b.per.clear_at[1] = 50.0
    return b, me, snap


class ViewTests(unittest.TestCase):
    def test_only_a_reach_banshee_pilot_gets_the_3d_view(self):
        me = PlayerState(0, 0, "bot", Vec(0, 0, 9.0), vehicle=77, weapon="banshee")
        for game, kind, seat, want in (("reach", "banshee", "driver", True), ("reach", "banshee", "gunner", False),
                                       ("reach", "falcon", "driver", False), ("h3", "banshee", "driver", False),
                                       ("h4", "banshee", "driver", False)):
            b = pilot(game, kind, seat)
            snap = Snapshot(10.0, [me], vehicles=[dict(banshee(), kind=kind)], mode="slayer")
            self.assertEqual(bool(b.reach_bomber() and b.piloting(me, snap)), want, (game, kind, seat))

    def test_a_man_under_it_is_seen_with_a_line_only(self):
        for line_ok in (True, False):
            b = pilot()
            me = PlayerState(0, 0, "bot", Vec(0, 0, 10), yaw=0.0, pitch=-1.05, vehicle=77, weapon="banshee")
            foe = PlayerState(1, 1, "f", Vec(-2.0, 0.5, 0.0), weapon="assault_rifle", weapons=["assault_rifle"])
            snap = Snapshot(10.0, [me, foe], vehicles=[banshee()], mode="slayer")
            b.per.air_view = True
            for t in range(30):
                b.per.update(10 + t / 15, me, snap, lambda a, c: line_ok, [], game="reach")
            self.assertEqual(1 in b.per.visible_enemies(), line_ok)

    def test_not_past_its_reach(self):
        b = pilot()
        me = PlayerState(0, 0, "bot", Vec(0, 0, 20), yaw=0.0, pitch=-1.0, vehicle=77, weapon="banshee")
        foe = PlayerState(1, 1, "f", Vec(-10.0, 0.0, -10.0), weapon="assault_rifle", weapons=["assault_rifle"])
        snap = Snapshot(10.0, [me, foe], vehicles=[banshee()], mode="slayer")
        b.per.air_view = True
        for t in range(30):
            b.per.update(10 + t / 15, me, snap, lambda a, c: True, [], game="reach")
        self.assertNotIn(1, b.per.visible_enemies())


class BombManTests(unittest.TestCase):
    def test_the_man_ahead_and_under_with_the_bomb_ready(self):
        b, me, snap = fresh()
        self.assertEqual(b.air_bomb_man(50.0, me, snap), 1)

    def test_not_when_it_cannot_bomb(self):
        b, me, snap = fresh(game="h3")
        self.assertIsNone(b.air_bomb_man(50.0, me, snap))
        b, me, snap = fresh()
        b.rod_next = 60.0                                          # (10 s to the bomb)
        self.assertIsNone(b.air_bomb_man(50.0, me, snap))
        b, me, snap = fresh(foe_at=Vec(10.0, 0.0, 0.0))            # (behind: a new pick only ahead)
        self.assertIsNone(b.air_bomb_man(50.0, me, snap))
        b, me, snap = fresh(foe_at=Vec(-1.0, 0.0, 0.0))            # (9 u straight under: too steep)
        self.assertIsNone(b.air_bomb_man(50.0, me, snap))

    def test_odd_vehicle_rows_do_not_raise(self):
        for veh in ([{k: v for k, v in banshee().items() if k != "fwd"}], [dict(banshee(), fwd=None)],
                    [dict(banshee(), fwd=(1.0, 0.0))], [dict(banshee(), fwd=(0.0, 0.0, 0.0))], []):
            b, me, snap = fresh(veh=veh)
            b.air_bomb_man(50.0, me, snap)


if __name__ == "__main__":
    unittest.main()

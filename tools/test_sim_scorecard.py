"""(custom, Nov 21) tools/sim_scorecard.py's live-trace metrics and tools/banshee_sim.py's game delays (Match(delay))."""
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import banshee_sim as B  # noqa: E402
import sim_scorecard as S  # noqa: E402
from brain import bot  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402


def world(t, men):
    """men: [(id, team, x, y, total)]"""
    return dict(t=t, world=[[i, tm, 1, x, y, 0.0, min(1.0, tot), max(0.0, tot - 1.0)] for i, tm, x, y, tot in men])


def botrow(t, pid, x, y, mag, target, goal="fight", shield=1.0):
    return dict(t=t, id=pid, pos=[x, y, 0.0], goal=goal, wpn="dmr", inv=["dmr", "assault_rifle"], mag=[mag, 32],
                cmd=[0, 0, 0, 1, 0], hp=[shield, 1.0], att=["aim", target, 0, 0], veh=-1)


class ScorecardTest(unittest.TestCase):
    def rec(self):
        r = S.Rec()
        r.add(dict(t=0.0, meta=dict(bot=dict(id=1, tier="noble"))))
        # bot 1 at the origin, the owner (0) 8 u off along x, running sideways (+y) at 2 u/s
        for k in range(12):
            t = k * 0.27
            hurt = 2.0 if t < 0.5 else 1.75 if t < 1.3 else 1.5
            r.add(world(t, [(0, 0, 8.0, 2.0 * t, hurt), (1, 1, 0.0, 0.0, 2.0)]))
        r.add(botrow(0.40, 1, 0.0, 0.0, 15, 0))
        r.add(botrow(0.44, 1, 0.0, 0.0, 14, 0))      # a round at 0.44: his total falls by the next row: a hit
        r.add(botrow(1.90, 1, 0.0, 0.0, 14, 0, goal="retreat", shield=0.5))
        r.add(botrow(1.94, 1, 0.0, 0.0, 13, 0, goal="retreat", shield=0.5))   # a round at 1.94: no fall: a miss
        r.add(botrow(2.40, 1, 0.0, 0.0, 15, 0))      # (a reload: not a round)
        return r

    def test_rounds_hits_and_bands(self):
        acc = S.accuracy(self.rec())
        self.assertEqual(acc[("noble", "owner")]["all"], [2, 1])
        self.assertEqual(acc[("noble", "owner")]["6-12u"], [2, 1])
        self.assertEqual(acc[("noble", "owner")][">1.5u/s"], [2, 1])     # (his 2 u/s across the line)
        self.assertNotIn(("noble", "bot"), acc)

    def test_goals_share(self):
        g = S.goals(self.rec())["noble"]
        self.assertEqual(g["_rows"], 5)
        self.assertEqual(g["retreat"], 2)
        self.assertEqual(g["_retreat_hurt"], 2)

    def test_first_hitter(self):
        r = S.Rec()
        r.add(dict(t=0.0, meta=dict(bot=dict(id=1, tier="noble"))))
        r.add(dict(t=0.0, meta=dict(bot=dict(id=2, tier="demon"))))
        # 2 hurt from 1.0, 1 from 1.5 (1 shot first); 2 kills 1 at 2.5: the first hitter lost
        for k in range(12):
            t = k * 0.25
            r.add(world(t, [(1, 1, 0.0, 0.0, 2.0 if t < 1.5 else 1.0), (2, 0, 5.0, 0.0, 2.0 if t < 1.0 else 1.5)]))
        r.add(dict(t=2.5, kill=dict(v=1, k=2, vp=[0, 0, 0], kp=[5, 0, 0])))
        r.add(dict(t=2.6, kill=dict(v=2, k=1, vp=[5, 0, 0], kp=[0, 0, 0])))   # (the other way: the first hitter won)
        ks = S.kills(r)
        self.assertEqual(ks[0][:2], ("demon", "noble"))
        self.assertAlmostEqual(ks[0][2], 1.0)          # (his first drop shows at 1.5)
        self.assertEqual(ks[0][3], 5.0)
        self.assertFalse(ks[0][4])
        self.assertTrue(ks[1][4])
        m = S.metrics([r])
        self.assertEqual(m["kills"]["all"]["first_hitter_won"], 0.5)
        self.assertIn("first_hitter_won", S.show([("x", m)]))


class DelayTest(unittest.TestCase):
    def test_sample_and_ticks(self):
        rng = random.Random(3)
        ages = [B.sample_delay(rng) for _ in range(4000)]
        self.assertTrue(all(B.DELAY_Q[0] <= a <= B.DELAY_Q[-1] for a in ages))
        ages.sort()
        self.assertAlmostEqual(ages[2000], B.DELAY_Q[10], delta=0.002)          # (the median)
        n = [B.delay_ticks(rng, 0.03) for _ in range(4000)]
        self.assertTrue(all(k >= 1 for k in n))
        self.assertAlmostEqual(sum(n) / len(n) / B.GAME_HZ, 0.03, delta=0.002)   # (whole ticks, the mean kept)
        self.assertEqual(B.delay_ticks(rng, 0.0), 1)

    def match(self):
        m = B.Match.__new__(B.Match)
        m.ticks, m.hist, m.reads, m.vel_t, m.ages = 0, B.collections.deque(maxlen=8), {}, {}, []
        m.drng = random.Random(1)
        return m

    def push(self, m):
        m.ticks += 1
        x = 2.5 * m.ticks / 30                         # (he runs 2.5 u/s along x, a sim tick a 1/30 s)
        ps = [PlayerState(0, 0, "him", Vec(x, 0.0, 0.0), Vec(2.5 * 30, 0, 0), 0.0, 0.0, True),
              PlayerState(1, 1, "bot", Vec(0.0, 5.0, 0.0), Vec(), 1.0, 0.0, True)]
        m.hist.append((m.ticks * 2, ps))
        return Snapshot(m.ticks / 30, ps)

    def test_delayed_read(self):
        m = self.match()
        for k in range(8):
            base = self.push(m)
        m.drng = random.Random(5)
        snap, age = m.delayed_snapshot(1, base)
        n = round(m.ages[-1] * B.GAME_HZ)
        him = snap.player(0)
        self.assertAlmostEqual(him.pos.x, 2.5 * (m.ticks * 2 - n) / 60, places=6)     # (the read n game ticks old)
        self.assertIsNone(him.vel_t)                   # (no read before: no velocity yet, as live)
        self.assertEqual(base.player(0).pos.x, 2.5 * 8 / 30)                         # (the present untouched)
        base = self.push(m)
        snap2, _ = m.delayed_snapshot(1, base)
        him = snap2.player(0)
        if him.vel_t is not None:
            self.assertAlmostEqual(him.vel_t.x, 2.5, places=6)                       # (over the game time between)
        # the live plain velocity: the move since the last read x 30
        moved = him.pos.x - snap.player(0).pos.x
        self.assertAlmostEqual(him.vel.x, moved * B.LIVE_HZ, places=6)

    def test_same_tick_read_keeps_vel_t(self):
        m = self.match()
        for k in range(8):
            base = self.push(m)
        m.reads[1] = (m.ticks * 2 - 4, {0: Vec(2.5 * (m.ticks * 2 - 4) / 60, 0, 0)})
        m.vel_t[1] = {0: Vec(9.0, 0, 0)}
        m.drng = random.Random(0)
        orig = B.sample_delay
        try:
            B.sample_delay = lambda rng, q=B.DELAY_Q: 4 / 60 - 0.0001     # (4 ticks: the same tick as the last read)
            snap, _ = m.delayed_snapshot(1, base)
        finally:
            B.sample_delay = orig
        self.assertEqual(snap.player(0).vel_t.x, 9.0)

    def test_noble_lead_reads_the_age(self):
        snap = Snapshot(0.0, [])
        B.Match.think_snapshot(snap, 0.05)
        self.assertAlmostEqual(bot.Bot.noble_lead_s(snap), 0.05, delta=0.003)

    def test_lead_ray_uses_vel_t(self):
        me = PlayerState(1, 1, "bot", Vec(), Vec(), 0.0, 0.0, True)
        him = PlayerState(0, 0, "him", Vec(8, 0, 0), Vec(0, 5.0, 0), 0.0, 0.0, True)
        him.vel_t = Vec(0, 2.5, 0)
        o, p = bot.lead_ray(me, him, (Vec(), Vec(8, 0, 0)), 0.04)
        self.assertAlmostEqual(p.y, 0.1, places=6)


if __name__ == "__main__":
    unittest.main()

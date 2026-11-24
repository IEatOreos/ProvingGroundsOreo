"""(custom, Nov 24) The map used more, on every map. The owner: "I do want parts of the map utilized more any ideas from
your end?" ... "Build 1,2,3,4,5 all in one phase": his own hot spots count (Slayer posts, Take Space for Legendary and
up), the team's coverage (stale spots pull), Flankers' crossfire spots, Rushers on sneak routes and flanks, high
ground for Legendary and up."""
import random
import sys
import types
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import bot, director                                  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec               # noqa: E402
from brain.director import Director                              # noqa: E402
from brain.profiles import make_profile                          # noqa: E402
from test_take_space import Base, man, mk, snap                  # noqa: E402


def director_on(positions, info=None):
    d = Director.__new__(Director)
    d.team, d.map = 0, {"positions": positions, "position_info": info or []}
    return d


class CoverageTests(unittest.TestCase):
    def test_stale_after_nobody_for_a_while(self):
        q, far = Vec(10, 0, 0), Vec(50, 0, 0)
        d = director_on([q, far])
        me = PlayerState(1, 0, "me", Vec(11, 0, 0))
        foe = PlayerState(2, 1, "foe", Vec(50, 0, 0))
        d.coverage_tick(0.0, Snapshot(0.0, [me, foe]))
        self.assertEqual((d.stale_of(q, 0.0), d.stale_of(far, 0.0)), (0.0, 0.0))     # (both start at the first tick)
        d.coverage_tick(30.0, Snapshot(30.0, [me, foe]))                          # (ours on q; only theirs on far)
        self.assertEqual(d.stale_of(q, 30.0), 0.0)
        self.assertAlmostEqual(d.stale_of(far, 30.0), 30.0 / director.COVER_STALE_S)
        self.assertEqual(d.stale_of(far, 500.0), 1.0)
        me.pos = Vec(10, 0, 10)                                                   # (a floor above it is not on it)
        d.coverage_tick(40.0, Snapshot(40.0, [me]))
        self.assertGreater(d.stale_of(q, 40.0), 0.0)

    def test_post_weights_owner_and_stale(self):
        a, b, c = Vec(0, 0, 0), Vec(20, 0, 0), Vec(40, 0, 0)
        d = director_on([a, b, c], [dict(pos=a, score=1.0, owner=True), dict(pos=b, score=1.0), dict(pos=c, score=1.0)])
        d.cover_seen = {d.cover_key(a): 0.0, d.cover_key(b): 0.0, d.cover_key(c): -director.COVER_STALE_S}
        w = d.post_weights(0.0, [a, b, c])
        self.assertEqual(w, [director.OWNER_POST_W, 1.0, 1.0 + director.COVER_POST_W])

    def test_owner_spots_most_of_the_picks_on_boneyard_numbers(self):
        # (Boneyard's 13: 5 owner at 1.0, 8 computed 0.7-0.95: 43% of the weight before, about 72% now)
        scores = [0.95, 0.92, 0.86, 0.85, 0.81, 0.8, 0.79, 0.7]
        pts = [Vec(i * 10, 0, 0) for i in range(13)]
        info = [dict(pos=p, score=1.0, owner=True) for p in pts[:5]] + [dict(pos=p, score=v) for p, v in zip(pts[5:], scores)]
        w = director_on(pts, info).post_weights(0.0, pts)
        share = sum(w[:5]) / sum(w)
        self.assertTrue(0.65 <= share <= 0.75, share)


class TakeSpacePickTests(Base):
    def test_rushers_no_longer_always(self):
        self.assertNotIn("rusher", bot.SPACE_ALWAYS)
        b, me = mk("strong", style="rusher"), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        scores = {}
        b.take_space(1.0, me, snap(me), scores, [])
        self.assertEqual(scores, {})

    def pick(self, b, me, *others):
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        got = b.space_pick(1.0, me, snap(me, *others), {}, [])
        return got[0] if got else None

    def test_owner_spot_counts_more_for_legendary_and_up(self):
        for tier, want in (("top", Vec(20, 0, 0)), ("strong", Vec(10, 0, 0))):
            b, me = mk(tier), man(1, 0, Vec(0, 0, 0))
            b.map["positions"] = [Vec(10, 0, 0), Vec(20, 0, 0)]
            b.map["position_info"] = [dict(pos=Vec(10, 0, 0)), dict(pos=Vec(20, 0, 0), owner=True)]
            self.assertEqual(self.pick(b, me), want, tier)     # (10 u farther: Legendary's 15 u covers it, Heroic's 6 not)

    def test_a_stale_spot_pulls(self):
        b, me = mk("strong"), man(1, 0, Vec(0, 0, 0))
        b.map["positions"] = [Vec(10, 0, 0), Vec(16, 0, 0)]
        self.assertEqual(self.pick(b, me), Vec(10, 0, 0))
        b.cover_seen = {(10.0, 0.0, 0.0): 1.0, (16.0, 0.0, 0.0): 1.0 - director.COVER_STALE_S}
        self.assertEqual(self.pick(b, me), Vec(16, 0, 0))     # (nobody of ours on it for a minute)

    def test_high_ground_for_legendary_and_up(self):
        for tier, want in (("demon", Vec(13, 0, 3)), ("average", Vec(10, 0, 0))):
            b, me = mk(tier), man(1, 0, Vec(0, 0, 0))
            b.map["positions"] = [Vec(10, 0, 0), Vec(13, 0, 3)]
            b.map["position_info"] = [dict(pos=Vec(10, 0, 0), height=0.0), dict(pos=Vec(13, 0, 3), height=5.0)]
            self.assertEqual(self.pick(b, me), want, tier)

    def at(self, style, positions, T=None, *others):
        b, me = mk("strong", style=style), man(1, 0, Vec(0, 0, 0))
        if T is not None:
            b.T = lambda: T
        b.map["positions"] = positions
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(30, 0, 0), t=0.0)
        got = b.space_pick(1.0, me, snap(me, *others), {}, [])
        return got[0] if got else None

    def test_flanker_round_the_fight_from_the_team(self):
        mate = man(2, 0, Vec(4, 0, 0))                                  # (a teammate on the straight line at the fight)
        spots = [Vec(10, 0, 0), Vec(15, 15, 0)]                          # (straight on; 45 deg round the fight)
        self.assertEqual(self.at("flanker", spots, None, mate), Vec(15, 15, 0))
        self.assertEqual(self.at("camper", spots, None, mate), Vec(10, 0, 0))   # (not a Flanker: as before)
        self.assertEqual(self.at("flanker", spots), Vec(10, 0, 0))        # (no teammate: nobody to cross with)

    def test_flanker_side_spot_that_sees_the_fight(self):
        sees = types.SimpleNamespace(nav_z=lambda x, y, z: z, ground_ok=lambda *a, **k: True, los=lambda a, c: True)
        blind = types.SimpleNamespace(nav_z=lambda x, y, z: z, ground_ok=lambda *a, **k: True, los=lambda a, c: False)
        side = [Vec(5, 22, 0)]                                          # (no nearer the fight: only to its side)
        self.assertEqual(self.at("flanker", side, sees), Vec(5, 22, 0))
        self.assertIsNone(self.at("flanker", side, blind))              # (it does not see the fight from there)
        self.assertIsNone(self.at("camper", side, sees))                # (the others: forward only)


class RusherTests(unittest.TestCase):
    def test_every_trip_flanks(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p = make_profile("strong", "rusher", random.Random(1))
        b.rng = types.SimpleNamespace(random=lambda: 0.999, choice=lambda xs: xs[0])
        zone = types.SimpleNamespace(center=Vec(15, 12, 0))
        b.map = {"zones": types.SimpleNamespace(zones=[zone])}
        me = PlayerState(1, 0, "me", Vec(0, 0, 0))
        self.assertEqual(b.detour(0.0, me, "hunt", Vec(30, 0, 0)), Vec(15, 12, 0))
        b2 = bot.Bot.__new__(bot.Bot)
        b2.p, b2.rng, b2.map = make_profile("strong", "camper", random.Random(1)), b.rng, b.map
        self.assertEqual(b2.detour(0.0, me, "hunt", Vec(30, 0, 0)), Vec(30, 0, 0))   # (a roll over its chance: straight)

    def test_ctf_sneak_route_first(self):
        d = Director.__new__(Director)
        d.side, d.threat, d.rng = 0, {}, random.Random(3)
        d.zones = types.SimpleNamespace(name=lambda p: "z")
        lane, sneak = Vec(20, 0, 0), [Vec(0, 20, 0), Vec(20, 20, 0)]
        d.map = {"lanes": [lane], "sneak": {0: [sneak]}}
        for style, want in (("rusher", tuple(sneak)), ):
            b = types.SimpleNamespace(p=make_profile("average", style, random.Random(1)))
            for _ in range(20):
                self.assertEqual(d.pick_route(0.0, b, used=[(lane,)]), want)
            self.assertEqual(d.pick_route(0.0, b, used=[tuple(sneak)]), want)   # (even one a teammate took)


if __name__ == "__main__":
    unittest.main()

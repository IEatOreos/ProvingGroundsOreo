"""(custom, Nov 27) CTF squads (brain/director.py Director.ctf_squads): runners in groups of 3 at most round a leader (a
person of ours on their half of the map, else a Legendary-and-up runner), the others its escorts. The owner: "Mythics,
Demons, Legendaries, Nobles, will make calls to move together in groups of 2-3"; "would a squad be able to be built
around a player? Similar to how our firefight setup is?"."""
import random
import sys
import types
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import FlagState, PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director, Order  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

OURS, THEIRS = Vec(0, 0, 0), Vec(100, 0, 0)


class FakeBot:
    def __init__(s, i, tier):
        s.id, s.p = i, make_profile(tier, "rusher", random.Random(i))
        s.order = Order("runner", THEIRS)

    def set_order(s, o, sure=False):
        s.order = o


def setup(tiers, at=None, people=(), their_flag="home"):
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map = {"flags": {0: OURS, 1: THEIRS}}
    d.events, d.roles = [], {}
    bots = [FakeBot(i, t) for i, t in enumerate(tiers, start=1)]
    d.bots = {b.id: b for b in bots}
    players = [PlayerState(b.id, 0, f"b{b.id}", (at or {}).get(b.id, Vec(30 + b.id, b.id, 0))) for b in bots]
    for k, q in enumerate(people):
        players.append(PlayerState(100 + k, 0, f"p{k}", q, is_bot=False))
    players.append(PlayerState(200, 1, "them", Vec(95, 0, 0)))
    for b in bots:
        d.roles[b.id] = "runner"
    snap = Snapshot(10.0, players, mode="ctf")
    snap.flags = {0: FlagState(0, OURS, OURS), 1: FlagState(1, THEIRS, THEIRS, their_flag)}
    return d, bots, snap


class SquadTests(unittest.TestCase):
    def test_runners_in_threes_round_a_high_tier(self):
        d, bots, snap = setup(["demon", "average", "average", "noble", "strong", "strong"])
        d.ctf_squads(10.0, snap, bots)
        self.assertEqual(set(d.squads), {1, 4})                       # (the Demon and the Noble lead)
        self.assertTrue(all(len(m) <= 2 for m in d.squads.values()))
        for lid, members in d.squads.items():
            for m in members:
                self.assertEqual((d.roles[m], d.bots[m].order.role, d.bots[m].order.target), ("escort", "escort", lid))
        self.assertTrue(any(e[1] == "squad" for e in d.events))       # (the call, in the team's events)

    def test_no_high_tier_no_squad(self):
        d, bots, snap = setup(["average", "strong", "novice"])
        d.ctf_squads(10.0, snap, bots)
        self.assertEqual(d.squads, {})
        self.assertTrue(all(d.roles[b.id] == "runner" for b in bots))

    def test_a_squad_round_the_person_on_their_half(self):
        d, bots, snap = setup(["average", "average", "average"], people=[Vec(60, 0, 0)],
                              at={1: Vec(55, 0, 0), 2: Vec(58, 2, 0), 3: Vec(20, 0, 0)})
        d.ctf_squads(10.0, snap, bots)
        self.assertEqual(sorted(d.squads.get(100, [])), [1, 2])       # (the two nearest him; the far one runs on)
        self.assertEqual(d.bots[1].order.target, 100)
        d, bots, snap = setup(["average", "average"], people=[Vec(10, 0, 0)])    # (on our half: no squad round him)
        d.ctf_squads(10.0, snap, bots)
        self.assertNotIn(100, d.squads)

    def test_kept_across_passes(self):
        d, bots, snap = setup(["demon", "average", "average", "average"])
        d.ctf_squads(10.0, snap, bots)
        first = dict(d.squads)
        for b in bots:                                                # (the next pass: all runners again)
            d.roles[b.id] = "runner" if b.id not in first.get(1, []) else "escort"
        d.ctf_squads(12.0, snap, bots)
        self.assertEqual(d.squads, first)

    def test_not_while_carrying_or_their_flag_out(self):
        d, bots, snap = setup(["demon", "average"], their_flag="carried")
        d.ctf_squads(10.0, snap, bots)
        self.assertEqual(d.roles[2], "runner")
        d, bots, snap = setup(["demon", "average"])
        snap.players[0].has_flag = True
        d.ctf_squads(10.0, snap, bots)
        self.assertEqual(d.roles[2], "runner")


if __name__ == "__main__":
    unittest.main()

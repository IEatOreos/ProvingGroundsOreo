"""CTF defending by the capture lead alone (custom, Nov 9, the owner: "If the match is tied, no one on either team
defends ... If the team is losing everyone should continue to attack. Only have a defender if the winning team is up by
2 or more flag captures, and defender count should never be higher than 1 ... always make it the lower difficulty
player, Excluding easy")."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import profiles                                  # noqa: E402
from brain.bot import Order                                 # noqa: E402
from brain.core import FlagState, Snapshot, Vec             # noqa: E402
from brain.director import Director                         # noqa: E402
from test_legendary_power_fetch import participant          # noqa: E402

RED, BLUE = Vec(0, 0, 0), Vec(100, 0, 0)


def director(lead=0, unit=1, n_bots=6):
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map = dict(flags={0: RED, 1: BLUE}, holds={0: [RED, Vec(-5, 0, 0)], 1: [BLUE]}, points={"mid": Vec(50, 0, 0)},
                 lanes=[], returns={})
    d.posture = SimpleNamespace(lead=lead, state="even")
    d.score_unit = unit
    d.plan = {"stance": "balanced", "defenders": 2}
    d.rng = random.Random(1)
    d.split_until, d.split = 1e9, False
    d.home_rule, d.defend_until = True, 1e9          # (a death at the flag just now: no extra defender any more)
    d.defend_posts = lambda home, k: [home + Vec(6, 0, 0)] * k
    d.cutoff_point = lambda snap, own: None
    d.bots = {}
    return d


def snapshot(own_state="home"):
    flags = {0: FlagState(0, RED, RED if own_state == "home" else Vec(40, 0, 0), own_state,
                          carrier=7 if own_state == "carried" else -1),
             1: FlagState(1, BLUE, BLUE)}
    return Snapshot(100, [], flags=flags, mode="ctf")


def defenders(slots):
    return [sl for sl in slots if sl[0] == "defender"]


class DefenderCountTests(unittest.TestCase):
    def test_tied_or_behind_nobody_defends_everyone_attacks(self):
        for lead in (0, -1, -3):
            slots = director(lead).role_slots(100, snapshot(), 6)
            self.assertEqual(defenders(slots), [], lead)
            self.assertTrue(any(sl[0] == "runner" for sl in slots), lead)

    def test_up_by_one_nobody_defends(self):
        self.assertEqual(defenders(director(1).role_slots(100, snapshot(), 8)), [])

    def test_up_by_two_or_more_one_defender_whatever_the_team_size(self):
        for lead in (2, 3, 5):
            for n in (2, 4, 8, 15):
                slots = director(lead).role_slots(100, snapshot(), n)
                self.assertEqual(len(defenders(slots)), 1, (lead, n))
                self.assertEqual(slots[0][0], "defender")              # filled first: the lowest tier is free
                self.assertEqual(slots[0][2], "low_tier")
                self.assertTrue(any(sl[0] == "runner" for sl in slots), (lead, n))   # still attacking at +2

    def test_lead_counts_captures_not_points(self):
        # a variant scoring 10 a capture: 10 ahead is one capture, 20 two
        self.assertEqual(defenders(director(10, unit=10).role_slots(100, snapshot(), 6)), [])
        self.assertEqual(len(defenders(director(20, unit=10).role_slots(100, snapshot(), 6))), 1)

    def test_no_defender_while_our_flag_is_out(self):
        for state in ("carried", "dropped"):
            slots = director(3).role_slots(100, snapshot(state), 8)
            self.assertEqual(defenders(slots), [], state)
            self.assertTrue(any(sl[0] == "hunter" for sl in slots), state)   # its hunters, as before

    def test_a_lone_bot_attacks(self):
        self.assertEqual(defenders(director(4).role_slots(100, snapshot(), 1)), [])


class DefenderPickTests(unittest.TestCase):
    def test_defend_priority(self):
        p = {t: participant(t, 0)[0].p for t in ("average", "strong", "scaling", "top", "demon", "novice")}
        order = sorted(p, key=lambda t: profiles.defend_priority(p[t]))
        self.assertEqual(order[0], "average")
        self.assertEqual(order[-1], "novice")
        self.assertEqual(profiles.defend_priority(p["scaling"]), profiles.defend_priority(p["strong"]))
        self.assertLess(profiles.defend_priority(p["strong"]), profiles.defend_priority(p["top"]))
        self.assertLess(profiles.defend_priority(p["top"]), profiles.defend_priority(p["demon"]))

    def assigned(self, tiers, dists):
        d = director()
        entries = [participant(t, x, pid=i) for i, (t, x) in enumerate(zip(tiers, dists))]
        bots = [b for b, _ in entries]
        for b in bots:
            b.order, b.via_left = Order("mid", Vec(50, 0, 0)), []
            b.set_order = lambda order, sure=False, b=b: setattr(b, "order", order)
        d.bots, d.roles = {b.id: b for b in bots}, {}
        d.event = lambda *a: None
        d.enemy_vehicles = lambda *a: []
        d.role_slots = lambda *a: [("defender", RED, "low_tier")] + [("runner", BLUE, "objective")] * len(bots)
        for name in ("backup_orders", "power_runs", "vehicle_orders", "rider_calls", "ferry_orders", "vehicle_jobs"):
            setattr(d, name, lambda *a: None)
        snap = Snapshot(100, [p for _, p in entries], flags=snapshot().flags, mode="ctf")
        d.assign_roles(100, snap)
        return [b.order.role for b in bots]

    def test_the_lowest_difficulty_defends_not_easy_and_not_the_nearest(self):
        # the Legendary stands on the flag; the Normal is far off: the Normal defends
        roles = self.assigned(["top", "average", "strong"], [1, 80, 40])
        self.assertEqual(roles, ["runner", "defender", "runner"])
        # Easy is never the defender (it plays for itself): the Heroic is
        roles = self.assigned(["novice", "strong", "top"], [1, 60, 2])
        self.assertEqual(roles[1], "defender")
        self.assertNotEqual(roles[0], "defender")
        # a tie in tier: the nearest of them
        roles = self.assigned(["strong", "strong", "demon"], [70, 5, 1])
        self.assertEqual(roles, ["runner", "defender", "runner"])


if __name__ == "__main__":
    unittest.main()

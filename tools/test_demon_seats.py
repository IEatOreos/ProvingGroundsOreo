"""(custom, Nov 24) The owner: "Dont let Mythic noble or demon ride passenger in mongoose or warthogs, unless theyre
carrying the objective. Only gunners of Gauss hog and normal warthogs. Not rocket hogs" ... "No passenger seat in the
rocket hog unless carrying objective. Any difficulty can feel [fill] those seats that isnt mythic demon or noble".
vehicles.demon_seat_ok, Bot.seat_ok, the director's calls (honk, driver calls, the gun call, a driver's pickup) and a
seated bot getting out (Bot.drive)."""
import random
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import vehicles                                      # noqa: E402
from brain.bot import Bot                                       # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec      # noqa: E402
from brain.profiles import make_profile                        # noqa: E402
from test_resource_calls import scene                          # noqa: E402

RULED = ("demon", "noble", "mythic")


class SeatRuleTests(unittest.TestCase):
    def test_the_table(self):
        ok = vehicles.demon_seat_ok
        for k in ("warthog", "gauss"):
            self.assertTrue(ok(k, "gunner"), k)
            self.assertTrue(ok(k, "ride"), k)
        for k in ("rwarthog", "thog", "mongoose", "gungoose"):
            self.assertFalse(ok(k, "gunner"), k)
        for k in ("warthog", "rwarthog", "gauss", "thog", "mongoose", "gungoose"):
            self.assertFalse(ok(k, "passenger"), k)
            self.assertFalse(ok(k, "board"), k)
            self.assertTrue(ok(k, "passenger", carrying=True), k)
        for k in ("falcon", "revenant", "hornet", "spectre", "scorpion", "prowler"):   # every other seat as before
            self.assertTrue(ok(k, "passenger") and ok(k, "gunner"), k)

    def test_only_demon_noble_and_mythic_are_held_to_it(self):
        v = dict(kind="rwarthog")
        for tier in ("novice", "average", "strong", "top", "blind", "tactician") + RULED:
            b = Bot(0, 0, make_profile(tier, "rusher", random.Random(1)), {"name": "t", "items": []}, random.Random(2))
            want = tier not in RULED
            self.assertEqual(Bot.seat_ok(b, v, "board"), want, tier)
            self.assertEqual(Bot.seat_ok(b, v, "ride"), want, tier)
            self.assertTrue(Bot.seat_ok(b, v, "board", carrying=True), tier)


class CallTests(unittest.TestCase):
    def honk(self, kind, tiers, flag=None):
        d, snap, bots, players = scene(kind, distances=(2, 12), tiers=tiers)
        snap.honks = [10]
        snap.vehicles[0].update(occupied=True, riders=1)
        if flag is not None:
            players[flag].has_flag = True
        d.honk_orders(100, snap, bots, players)
        return [b.order.role for b in bots]

    def test_honk_rocket_hog_the_gun_and_seat_go_to_the_others(self):
        for tier in RULED:
            self.assertEqual(self.honk("rwarthog", (tier, "strong")), ["mid", "ride"], tier)

    def test_honk_warthog_gun_yes_passenger_no(self):
        for tier in RULED:
            roles = self.honk("warthog", (tier, "demon"))          # (the gun to one of them, by difficulty)
            self.assertEqual(sorted(roles), ["mid", "ride"], tier)
            # (the gun by difficulty, theirs or the Heroic's; never the passenger seat for them)
            roles = self.honk("gauss", ("strong", tier))
            self.assertIn("ride", roles, tier)
            self.assertNotEqual(roles[1], "board", tier)

    def test_honk_mongoose_only_with_the_objective(self):
        self.assertEqual(self.honk("mongoose", ("demon", "average")), ["mid", "board"])
        self.assertEqual(self.honk("mongoose", ("demon", "average"), flag=0), ["board", "mid"])

    def test_driver_calls_skip_them(self):
        d, snap, bots, players = scene("mongoose", distances=(2, 10), tiers=("noble", "top"))
        snap.vehicles[0].update(occupied=True, riders=1)
        d.rider_ok = lambda *a: True
        snap.mode, d.roles = "ctf", {0: "runner", 1: "runner"}   # (custom, Nov 27: a Mongoose's back seat, runners only)
        d.rider_calls(100, snap, bots, players)
        self.assertEqual([b.order.role for b in bots], ["mid", "board"])

    def test_gun_call_skips_them_on_a_rocket_hog(self):
        d, snap, bots, players = scene("rwarthog", distances=(5, 20), tiers=("mythic", "average"))
        snap.vehicles[0].update(occupied=True, riders=1)
        for name in ("honk_orders", "crew_orders", "rider_calls", "ferry_orders", "vehicle_jobs"):
            setattr(d, name, lambda *a: None)
        d.vehicle_orders(100, snap, bots)
        self.assertEqual([b.order.role for b in bots], ["mid", "ride"])

    def test_a_driver_does_not_fetch_them_for_a_rocket_hogs_gun(self):
        from test_legendary_power_fetch import participant
        d, snap, bots, players = scene("rwarthog", distances=(5, 30), tiers=("demon", "strong"))
        driver, me = participant("average", 0, pid=3)
        me.vehicle = 10
        players[3] = me
        d.rider_ok = lambda *a: True
        self.assertEqual(d.gunner_pickup(100, driver, me, snap, bots, players), players[1].pos)


class SeatedTests(unittest.TestCase):
    def seated(self, tier, kind, seat, flag=False):
        b = Bot(0, 0, make_profile(tier, "rusher", random.Random(1)), {"name": "reach_t", "items": []}, random.Random(2))
        b.notes = []
        me = PlayerState(0, 0, "bot", Vec(), vehicle=10, has_flag=flag, gunner_seat=seat == "gunner")
        snap = Snapshot(100, [me], vehicles=[dict(handle=10, kind=kind, pos=(0, 0, 0), occupied=True, team=0, riders=2)])
        b.seat_for, b.seat_since, b.seat = 10, 99.0, seat
        act = Action()
        b.drive(100.0, 0.1, me, snap, act, None)
        return act.action and any("Demon rules" in str(n) for n in b.notes)

    def test_out_of_a_seat_it_does_not_take(self):
        for tier in RULED:
            self.assertTrue(self.seated(tier, "warthog", "passenger"), tier)
            self.assertTrue(self.seated(tier, "rwarthog", "gunner"), tier)
            self.assertTrue(self.seated(tier, "mongoose", "passenger"), tier)

    def test_stays_with_the_objective_or_on_a_warthogs_gun(self):
        self.assertFalse(self.seated("demon", "warthog", "passenger", flag=True))
        self.assertFalse(self.seated("demon", "gauss", "gunner"))
        self.assertFalse(self.seated("strong", "rwarthog", "passenger"))


if __name__ == "__main__":
    unittest.main()

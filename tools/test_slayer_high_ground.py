"""Team Slayer high ground, Legendary / Blind / Scaling / Demon (custom, Nov 10, the owner: "the game is about power
positions and knowing when to push ... too many bots are always on the lowest levels of the map. They need to utilize
high ground alot more often, or stay in the hot spots once reached unless better conditions arise like a power weapon,
or playing objective" and "Dont change the power weapons though"). Live Complex 20261110-193429: bots on the ground
floor 51% of the match, over 4.5 u 0-1%; posted bots within 3 u of their post 0-9% of their post time.

A posted bot of those tiers keeps to its post (Bot.keep_role, ANCHOR_R): guns, hunts and patrols off it lose weight,
fights and power weapons never do; Heroic and below, and other modes, play as before. The director holds a post that
is working (post_working), leaves one losing men (post_lost) and sends the support to a perch above the fight (perch)."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import director as D                                   # noqa: E402
from brain.bot import ANCHOR_DZ, ANCHOR_R, Bot, Order             # noqa: E402
from brain.core import PlayerState, Snapshot, Vec                 # noqa: E402
from brain.director import Director                               # noqa: E402
from brain import profiles, scaling                               # noqa: E402
from brain.profiles import make_profile                           # noqa: E402

POST = Vec(40, 0, 6.0)                       # a post on the top floor
ROCKETS = Vec(10, 0, 0.0)                    # the map's rocket spawn, on the ground floor
ITEMS = [dict(kind="weapon", name="rockets", value=1.0, pos=ROCKETS),
         dict(kind="weapon", name="magnum", value=0.3, pos=Vec(15, 5, 0.0))]


def prof(tier):
    if tier == "scaling":
        return scaling.profile(1.0, "flanker", random.Random(1))
    return make_profile(tier, "flanker", random.Random(1))


def posted(tier, mode="slayer", at=POST, ground=()):
    b = Bot(0, 0, prof(tier), {"name": "h4_z05_cliffside", "items": ITEMS}, random.Random(4))
    b.order = Order("mid", POST)
    me = PlayerState(0, 0, "bot", at, weapon="battle_rifle", weapons=["battle_rifle", "magnum"], ammo=[60, 24],
                     mag=[36, 8])
    snap = Snapshot(10.0, [me], mode=mode, ground_weapons=list(ground))
    return b, me, snap


def scored(b, me, snap, scores):
    scores = dict(scores)
    b.keep_role(scores, me, snap, [])
    return scores


HIGH = ("top", "blind", "scaling", "demon")


class TierTests(unittest.TestCase):
    def test_the_four_tiers_and_no_others(self):
        for tier in HIGH:
            self.assertTrue(profiles.high_ground(prof(tier)), tier)
        for tier in ("strong", "average", "novice"):
            self.assertFalse(profiles.high_ground(prof(tier)), tier)
        self.assertEqual(prof("blind").tier, "top")
        self.assertIsNotNone(prof("scaling").extra)


class LeashTests(unittest.TestCase):
    far_gun, far_hunt = ("item", Vec(15, 5, 0.0)), ("hunt", Vec(25, 0, 0.0))

    def test_guns_and_hunts_off_the_post_lose_weight_and_the_post_wins(self):
        for tier in HIGH:
            b, me, snap = posted(tier, at=Vec(30, 0, 0.0))            # down on the ground floor, off its post
            s = scored(b, me, snap, {self.far_gun: 1.2, self.far_hunt: 1.1})
            self.assertLess(s[self.far_gun], 0.5, tier)
            self.assertLess(s[self.far_hunt], 0.5, tier)
            back = max(v for k, v in s.items() if k[0] == "objective")
            self.assertGreater(back, 1.6, tier)                       # getting back up outranks them

    def test_on_its_post_a_gun_by_it_is_still_taken(self):
        b, me, snap = posted("top")
        near = ("item", POST + Vec(ANCHOR_R - 2, 0, 0))
        self.assertEqual(scored(b, me, snap, {near: 1.2})[near], 1.2)
        under = ("item", POST + Vec(2, 0, -ANCHOR_DZ - 1))           # under its floor: off it
        self.assertLess(scored(b, me, snap, {under: 1.2})[under], 0.5)

    def test_fights_are_never_cut_it_shoots_from_the_post(self):
        b, me, snap = posted("demon")
        fight = ("fight", 7)
        self.assertEqual(scored(b, me, snap, {fight: 2.0})[fight], 2.0)

    def test_power_weapons_are_never_held_back(self):
        for tier in HIGH:
            b, me, snap = posted(tier)
            spawn = ("item", ROCKETS)                                  # its spawn, 30 u off and 6 down
            self.assertEqual(scored(b, me, snap, {spawn: 1.4})[spawn], 1.4, tier)
            loose = Vec(20, -8, 0.0)
            b, me, snap = posted(tier, ground=[("rockets", loose)])   # a dropped one lying loose
            self.assertEqual(scored(b, me, snap, {("item", loose): 1.3})[("item", loose)], 1.3, tier)

    def test_heroic_and_other_modes_play_as_before(self):
        for tier, mode in (("strong", "slayer"), ("average", "slayer"), ("top", "ctf"), ("demon", "oddball")):
            b, me, snap = posted(tier, mode=mode, at=Vec(30, 0, 0.0))
            self.assertIsNone(b.slayer_post(snap), (tier, mode))
            s = scored(b, me, snap, {self.far_gun: 1.2, self.far_hunt: 1.1})
            self.assertEqual((s[self.far_gun], s[self.far_hunt]), (1.2, 1.1), (tier, mode))

    def test_only_a_post(self):
        b, me, snap = posted("top")
        b.order = Order("hunter", POST)
        self.assertIsNone(b.slayer_post(snap))


def director(bots, pts):
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map = dict(positions=pts, holds={0: [], 1: []}, points={"mid": Vec()})
    d.bots = {b.id: b for b in bots}
    d._T = SimpleNamespace(los=lambda a, b: True)
    return d


def mate(pid, tier, role="mid", point=POST, seen_at=None):
    b = SimpleNamespace(id=pid, p=prof(tier), order=Order(role, point), per=SimpleNamespace(last_seen={}))
    if seen_at is not None:
        b.per.last_seen[9] = seen_at
    return b


class DirectorTests(unittest.TestCase):
    def snap(self, where):
        return Snapshot(100.0, [PlayerState(pid, 0, "b", q) for pid, q in where.items()], mode="slayer")

    def test_a_post_held_and_seeing_men_is_kept(self):
        d = director([mate(1, "demon", seen_at=95.0)], [POST])
        d.post, d.post_since = POST, 60.0
        self.assertTrue(d.post_working(100.0, self.snap({1: POST + Vec(2, 0, 0)})))

    def test_quiet_off_it_held_too_long_or_heroic_it_moves_on(self):
        d = director([mate(1, "demon", seen_at=100.0 - D.POST_QUIET - 1)], [POST])
        d.post, d.post_since = POST, 60.0
        self.assertFalse(d.post_working(100.0, self.snap({1: POST})))                  # nobody seen lately
        d = director([mate(1, "demon", seen_at=99.0)], [POST])
        d.post, d.post_since = POST, 60.0
        self.assertFalse(d.post_working(100.0, self.snap({1: POST + Vec(0, 0, -3)})))  # down off it
        d.post_since = 100.0 - D.POST_HOLD_MAX
        self.assertFalse(d.post_working(100.0, self.snap({1: POST})))                  # held long enough
        d = director([mate(1, "strong", seen_at=99.0)], [POST])
        d.post, d.post_since = POST, 60.0
        self.assertFalse(d.post_working(100.0, self.snap({1: POST})))                  # Heroic: upstream rotation

    def test_two_of_ours_down_by_it_and_the_team_leaves(self):
        d = director([], [POST])
        d.post, d.post_since = POST, 50.0
        d.fell_at = [(90.0, POST + Vec(3, 0, 0))]
        self.assertFalse(d.post_lost(100.0))
        d.fell_at.append((95.0, POST + Vec(-4, 2, 0)))
        self.assertTrue(d.post_lost(100.0))
        d.post_since = 92.0                                   # one before it was taken counts for nothing
        self.assertFalse(d.post_lost(100.0))
        d.post_since, d.fell_at = 0.0, [(100.0 - D.POST_LOSS_S - 5, POST), (95.0, POST)]
        self.assertFalse(d.post_lost(100.0))                  # one too long ago

    def test_the_perch_is_above_the_fight_and_sees_it(self):
        fight = Vec(0, 0, 0.4)
        low, high, far = Vec(8, 0, 0.6), Vec(12, 0, 3.0), Vec(40, 0, 6.0)
        d = director([], [low, high, far])
        self.assertEqual(d.perch(fight), high)                # not level with it, not out of range
        d._T = SimpleNamespace(los=lambda a, b: False)
        self.assertIsNone(d.perch(fight))                     # none that sees it


if __name__ == "__main__":
    unittest.main()

"""(custom, Nov 18) Live grenades read and run from (brain/live.py LiveReach.grenades, Bot.nade_danger /
enemy_grenade, equipment's grenade cue). The owner's Forge World 20261118-180057: frags killed three of N1ghtR4ven's 13
deaths and no bot ever moved for one, since snap.grenades was only ever filled in a simulator. The owner: "make them
read enemy grenades"."""
import math
import random
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                # noqa: E402
from brain import live as livemod                              # noqa: E402
from brain import profiles                                     # noqa: E402
from brain.bot import Bot                                      # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec      # noqa: E402
from test_h4_pickup_board import Flat                          # noqa: E402


def scene(tier=profiles.DEMON, terrain=None):
    b = Bot(0, 0, profiles.make_profile(tier, "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
    t = terrain or Flat()
    b.T = lambda: t
    b.notes = []
    me = PlayerState(0, 0, "bot", Vec(), weapon="dmr")
    me.yaw = 0.0
    snap = Snapshot(0.0, [me], mode="slayer")
    return b, me, snap


def nade(h, pos, since=0.0, vel=None, first=None, kind="frag_grenade"):
    return {"h": h, "kind": kind, "pos": pos, "vel": vel or Vec(), "since": since, "team": -1, "t": since,
            "from": first or pos}


def run(b, me, snap, now):
    act = Action(yaw=me.yaw, pitch=0.0)
    act.forward, act.strafe = 1.0, 0.0            # walking on at the man / the goal, east
    b.notes = []
    b.enemy_grenade(now, me, act, snap)
    return act


class DodgeTests(unittest.TestCase):
    def test_demon_runs_out_after_noticing_and_keeps_its_view(self):
        b, me, snap = scene()
        snap.grenades = [nade(1, Vec(2.0, 0.0, 0.1))]
        act = run(b, me, snap, botmod.NADE_REACT_MIN - 0.05)
        self.assertEqual((act.forward, act.strafe), (1.0, 0.0))        # not noticed yet
        act = run(b, me, snap, botmod.NADE_REACT_MIN + 0.05)
        self.assertAlmostEqual(act.forward, -1.0, places=3)             # straight away from it, west
        self.assertAlmostEqual(act.strafe, 0.0, places=3)
        self.assertEqual(act.yaw, 0.0)                                  # the view stays on the fight
        self.assertIn("grenade: out of the blast (frag_grenade)", b.notes)

    def test_slower_tiers_notice_later_and_easy_never(self):
        b, me, snap = scene("average")
        snap.grenades = [nade(1, Vec(2.0, 0.0, 0.0))]
        wait = b.p.reaction + botmod.NADE_NOTICE * (1.0 - b.p.aware)
        self.assertGreater(wait, botmod.NADE_REACT_MIN)
        self.assertEqual(run(b, me, snap, wait - 0.02).forward, 1.0)
        self.assertLess(run(b, me, snap, wait + 0.02).forward, 0.0)
        b, me, snap = scene("novice")
        snap.grenades = [nade(1, Vec(2.0, 0.0, 0.0))]
        self.assertEqual(run(b, me, snap, 5.0).forward, 1.0)

    def test_far_high_or_in_a_vehicle_not_run_from(self):
        b, me, snap = scene()
        snap.grenades = [nade(1, Vec(botmod.NADE_DODGE_R + 0.5, 0.0, 0.0)),
                         nade(2, Vec(1.0, 0.0, botmod.NADE_DODGE_DZ + 0.5))]
        self.assertEqual(run(b, me, snap, 1.0).forward, 1.0)
        snap.grenades = [nade(3, Vec(1.0, 0.0, 0.0))]
        me.vehicle = 4
        self.assertEqual(run(b, me, snap, 1.0).forward, 1.0)

    def test_one_flying_at_it_counts_where_it_will_be(self):
        b, me, snap = scene()
        snap.grenades = [nade(1, Vec(0.0, 6.0, 0.5), vel=Vec(0.0, -8.0, 0.0))]   # 6 u off, 3.2 u in 0.4 s
        act = run(b, me, snap, 1.0)
        self.assertAlmostEqual(act.strafe, -1.0, places=3)              # away from it: south, to the right
        snap.grenades = [nade(1, Vec(0.0, 6.0, 0.5), vel=Vec(0.0, 8.0, 0.0))]    # flying off
        self.assertEqual(run(b, me, snap, 1.0).strafe, 0.0)

    def test_its_own_throw_is_not_run_from(self):
        b, me, snap = scene()
        hand = Vec(0.5, 0.0, 0.6)
        snap.grenades = [nade(1, hand, since=1.0, first=hand)]
        self.assertEqual(run(b, me, snap, 1.03).forward, 1.0)           # at its hand: its own
        snap.grenades = [nade(1, Vec(2.0, 0.0, 0.0), since=1.0, first=hand)]  # bounced back by it
        self.assertEqual(run(b, me, snap, 2.0).forward, 1.0)
        self.assertIn(1, b.own_nades)

    def test_a_wall_behind_turns_the_escape(self):
        class WallWest(Flat):
            def clearance(s, at, yaw, far=1.0):
                return 0.1 if math.cos(yaw) < -0.9 else 9.0              # shut straight west
        b, me, snap = scene(terrain=WallWest())
        snap.grenades = [nade(1, Vec(2.0, 0.0, 0.0))]
        act = run(b, me, snap, 1.0)
        way = math.atan2(act.strafe, act.forward)
        self.assertGreater(math.cos(way), -0.9)                          # not into the wall
        self.assertLess(math.cos(way), 0.0)                              # still away from the grenade

    def test_equipment_cue_goes_through_nade_danger(self):
        b, me, snap = scene()
        hand = Vec(0.5, 0.0, 0.6)
        snap.grenades = [nade(1, hand, since=1.0, first=hand)]
        self.assertIsNone(b.nade_danger(1.03, me, snap))                # (equipment: no lock / dash at each throw)
        src = (Path(__file__).resolve().parents[1] / "brain" / "equipment.py").read_text(encoding="utf-8")
        self.assertIn('getattr(bot, "nade_danger", None)', src)

    def test_wired_into_plan_after_the_zone_before_the_guards(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("    def plan(s, now, dt, snap, los, nav, callouts, items=None):")
        body = src[i:src.index("    def ", i + 10)]
        at = body.index("s.enemy_grenade(now, me, act, snap)")
        self.assertLess(body.index("s.keep_in_zone(me, snap, act)"), at)
        self.assertLess(at, body.index("s.obstacle_guard(now, me, act, snap)"))
        self.assertLess(at, body.index("s.edge_guard(now, me, act)"))


NAMES = ["sound\\weapons\\frag_grenade\\frag_throw"] * 0x10 + [
    "objects\\weapons\\grenade\\frag_grenade\\frag_grenade",                    # 0x10
    "objects\\weapons\\grenade\\frag_grenade\\frag_grenade_equipment",          # 0x11
    "objects\\weapons\\grenade\\frag_grenade\\detonation_hack\\spawn_detonation_hack",   # 0x12
    "shaders\\shader_templates\\_0_2_0",                                         # 0x13
    "objects\\weapons\\rifle\\dmr\\projectiles\\dmr_bullet",                    # 0x14
    "objects\\weapons\\grenade\\plasma_grenade\\plasma_grenade",                # 0x15
]


class FakeMem:
    def __init__(s, blobs):
        s.blobs = blobs

    def read(s, addr, n):
        for base, data in s.blobs.items():
            if base <= addr < base + len(data):
                return data[addr - base:addr - base + n]
        return b""


def fake_reach(objs):
    """A LiveReach over made-up memory: objs [(type, tag, parent, (x, y, z))]."""
    r = object.__new__(livemod.LiveReach)
    r._tag_name_list = NAMES
    ents = bytearray(len(objs) * 0x18)
    blobs = {}
    for i, (typ, tag, parent, pos) in enumerate(objs):
        struct.pack_into("<H", ents, i * 0x18, 7 + i)
        ents[i * 0x18 + r.TYPE_AT] = typ
        o = 0x10000 + i * 0x100
        struct.pack_into("<Q", ents, i * 0x18 + 0x10, o)
        head = bytearray(0x100)
        struct.pack_into("<I", head, 0, tag)
        struct.pack_into("<I", head, r.PARENT_AT, parent)
        struct.pack_into("<3f", head, r.POS_AT, *pos)
        blobs[o] = bytes(head)
    blobs[0x1000] = bytes(ents)
    r.g = FakeMem(blobs)
    r._array = lambda at: (0x1000, len(objs), None)
    return r, blobs


class LiveReadTests(unittest.TestCase):
    def test_grenade_kind_by_its_own_tag_name(self):
        r, _ = fake_reach([])
        self.assertEqual(r._grenade_kind(0xE0000010), "frag_grenade")
        self.assertEqual(r._grenade_kind(0xE0000015), "plasma_grenade")
        self.assertEqual(r._grenade_kind(0xE0000013), "frag_grenade")      # a shader's index past its own name
        for k in (0x11, 0x12, 0x14, 0x05):                                 # pickup, detonation, a bullet, a sound
            self.assertIsNone(r._grenade_kind(0xE0000000 | k), hex(k))

    def test_reads_loose_grenades_with_speed_and_first_sight(self):
        N = livemod.NONE
        r, blobs = fake_reach([(5, 0xE0000010, N, (1.0, 2.0, 3.0)),       # a frag
                               (5, 0xE0000014, N, (5.0, 5.0, 5.0)),       # a DMR round
                               (5, 0xE0000015, 0x00020003, (0.0, 0.0, 0.0)),   # a plasma stuck to someone
                               (2, 0xE0000010, N, (9.0, 9.0, 9.0))])      # (not a projectile)
        out = r.grenades(10.0)
        self.assertEqual([g["kind"] for g in out], ["frag_grenade"])
        g = out[0]
        self.assertEqual((g["since"], g["t"], g["team"]), (10.0, 10.0, -1))
        self.assertEqual((g["pos"].x, g["from"].x), (1.0, 1.0))
        head = bytearray(blobs[0x10000])
        struct.pack_into("<3f", head, r.POS_AT, 2.0, 2.0, 3.0)
        blobs[0x10000] = bytes(head)
        g2 = r.grenades(10.1)[0]
        self.assertAlmostEqual(g2["vel"].x, 10.0, places=3)
        self.assertEqual((g2["since"], g2["from"].x, g2["h"]), (10.0, 1.0, g["h"]))
        r._array = lambda at: (0x1000, 0, None)
        self.assertEqual(r.grenades(10.2), [])
        self.assertEqual(r._grenades_seen, {})                             # gone: forgotten

    def test_halo4_reader_reads_none(self):
        self.assertTrue(livemod.LiveReach.GRENADE_READ)
        self.assertFalse(livemod.LiveH4F.GRENADE_READ)
        r = object.__new__(livemod.LiveH4F)
        self.assertEqual(r.grenades(1.0), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

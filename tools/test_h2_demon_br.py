"""(custom, Nov 14) Halo 2, H2A and Halo 3 Demon's precision guns: fire on the sight of him and the press snaps to his
head, like Reach's DMR (bot.demon_precision_snap). Legendary, Blind, Mythic, other guns and other games keep their own
paths."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot, demon_precision_snap as h2_demon_br    # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to, eye  # noqa: E402
from brain.profiles import make_profile                           # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_demon_fire import Cover                                 # noqa: E402


class Open(Cover):
    """Open ground, no glass: a round goes where the sight does."""
    def ground_ok(self, *args, **kw):
        return True

    def shot_los(self, *args, **kw):
        return True


def scene(tier="demon", weapon="battle_rifle", game="h2", at=Vec(10, 1.0, 0.5)):
    cover = Open((True, True), (True, True), (True, True))
    rng = random.Random(1)
    bot = Bot(0, 0, make_profile(tier, "rusher", rng), {"name": game + "_test"}, rng)
    bot._terrain = cover
    bot.goal, bot.next_decide = ("fight", 1), 99.0
    bot.per.recognized.add(1)
    for name in ("no_wall_jump", "edge_guard", "obstacle_guard", "unstuck"):
        setattr(bot, name, lambda *args: None)
    me = PlayerState(0, 0, "bot", Vec(), weapon=weapon, weapons=[weapon], mag=[36], ammo=[72])
    him = PlayerState(1, 1, "enemy", at)
    return bot, me, him, cover


def final_shot(tier, weapon="battle_rifle", game="h2"):
    """The final shot step alone (think after a stubbed plan that fires at his head)."""
    bot, me, him, cover = scene(tier, weapon, game)

    def plan(*args):
        bot.shot_part = (1, True)
        return Action(fire=True, yaw=0.0)
    bot.plan = plan
    act = bot.think(1.0, 1 / 30, Snapshot(1.0, [me, him]), cover.sees, None, [])
    return act, me, him


class H2DemonBRTests(unittest.TestCase):
    def test_only_demon_precision_guns_on_foot_in_h2_h2a_h3(self):
        me = PlayerState(0, 0, "bot", Vec(), weapon="battle_rifle")
        demon = make_profile("demon", "rusher", random.Random(1))
        for game in ("h2", "h2a", "h3"):
            for w in ("battle_rifle", "covenant_carbine", "magnum", "sniper", "beam_rifle"):
                me.weapon = w
                self.assertTrue(h2_demon_br(demon, game, me), (game, w))
            for w in ("smg", "assault_rifle", "shotgun", "rockets", "sword"):
                me.weapon = w
                self.assertFalse(h2_demon_br(demon, game, me), (game, w))
        me.weapon = "battle_rifle"
        for game in ("ce", "reach", "h4"):      # (Reach and Halo 4 Demons: their own paths)
            self.assertFalse(h2_demon_br(demon, game, me), game)
        for tier in ("top", "blind", "strong", "mythic"):
            try:
                prof = make_profile(tier, "rusher", random.Random(1))
            except Exception:
                continue                       # (a tier this copy does not have)
            self.assertFalse(h2_demon_br(prof, "h2", me), tier)
        me.vehicle = 4
        self.assertFalse(h2_demon_br(demon, "h2", me))

    def test_demon_press_snaps_to_the_head(self):
        for game, weapon in (("h2", "battle_rifle"), ("h2a", "covenant_carbine"), ("h3", "battle_rifle"),
                             ("h3", "magnum"), ("h2", "beam_rifle")):
            act, me, him = final_shot("demon", weapon, game)
            want = angles_to(eye(me), him.pos + Vec(0, 0, 0.62))
            self.assertAlmostEqual(act.yaw, want[0], msg=(game, weapon))
            self.assertAlmostEqual(act.pitch, want[1], msg=(game, weapon))

    def test_legendary_and_other_games_keep_their_aim(self):
        for tier, game in (("top", "h2"), ("top", "h3"), ("demon", "ce")):
            act, me, him = final_shot(tier, game=game)
            want = angles_to(eye(me), him.pos + Vec(0, 0, 0.62))
            self.assertNotAlmostEqual(act.yaw, want[0], places=4, msg=(tier, game))

    def test_demon_fires_on_sight_before_its_own_aim_settles(self):
        # him well off to the side: the capped aim is not on him the first ticks, the sight of him is enough
        first = {}
        for tier in ("demon", "top"):
            bot, me, him, cover = scene(tier, at=Vec(6, 6, 0))
            for k in range(30):
                now = 1.0 + k / 30
                act = bot.think(now, 1 / 30, Snapshot(now, [me, him]), cover.sees, lambda a, b, **kw: b, [])
                if act.fire:
                    first[tier] = k
                    break
        self.assertIn("demon", first)
        self.assertLess(first["demon"], first.get("top", 99))


if __name__ == "__main__":
    unittest.main()

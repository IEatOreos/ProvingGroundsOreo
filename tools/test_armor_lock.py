"""Armor Lock proximity activation and preservation of existing ability restrictions."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot, Belief
from brain.core import PlayerState, Snapshot, Vec
from brain.equipment import Energy
from brain.profiles import make_profile


def scene(tier='top', weapon='sword', distance=6.0, shield=1.0, seen=True, hit=False):
    bot=Bot(0,0,make_profile(tier,'rusher',random.Random(3)),{'name':'reach_test'},random.Random(5))
    me=PlayerState(0,0,'bot',Vec(),equipment='armor_lock',shield=shield)
    # Facing away: the new trigger must not require the enemy to aim at us.
    foe=PlayerState(1,1,'enemy',Vec(distance,0,0),weapon=weapon,yaw=0)
    bot.goal=('fight',1)
    bot.hit_at=10 if hit else -99
    bot.cover_from=lambda *args:None
    if seen:
        bot.per.beliefs[1]=Belief(foe.pos,Vec(),10,True,'eyes')
        bot.per.recognized.add(1)
    bot.kit.kind='armor_lock'
    bot.kit.energy=Energy('reach','armor_lock')
    return bot,me,foe,Snapshot(10,[me,foe])


class ArmorLockTests(unittest.TestCase):
    def test_sword_and_hammer_trigger_at_full_shields_without_damage(self):
        for tier in ('average','strong','top','demon'):
            for weapon in ('sword','gravity_hammer'):
                with self.subTest(tier=tier,weapon=weapon):
                    b,me,_,snap=scene(tier,weapon)
                    self.assertEqual(b.kit.plan(b,10,me,snap),
                                     ('armor_lock','self',None,2.0,'armor lock: sword or hammer within 6 units'))

    def test_six_unit_boundary_and_visibility(self):
        for distance,seen in ((6.001,True),(6.0,False)):
            b,me,_,snap=scene(distance=distance,seen=seen)
            self.assertIsNone(b.kit.plan(b,10,me,snap))

    def test_low_shields_and_damage_alone_no_longer_trigger_lock(self):
        for tier in ('average','strong','top','demon'):
            for distance in (5,9):
                b,me,_,snap=scene(tier,'assault_rifle',distance,shield=.1,hit=True)
                self.assertIsNone(b.kit.plan(b,10,me,snap))

    def test_easy_infection_cooldown_energy_and_input_restrictions_remain(self):
        b,me,_,snap=scene('novice')
        self.assertIsNone(b.kit.plan(b,10,me,snap))
        for reason in ('infection','cooldown','energy','input'):
            b,me,_,snap=scene()
            if reason=='infection':snap.mode,snap.infected='infection',1
            elif reason=='cooldown':b.kit.cool['armor_lock']=11
            elif reason=='energy':b.kit.energy.level=0
            else:b.kit.pressable=False
            self.assertIsNone(b.kit.plan(b,10,me,snap),reason)

    def test_other_survival_and_objective_triggers_remain(self):
        b,me,foe,snap=scene(weapon='rockets',distance=10)
        foe.yaw=3.141592653589793
        self.assertEqual(b.kit.plan(b,10,me,snap)[4],'armor lock: rocket / laser')
        b,me,_,snap=scene(weapon='assault_rifle',distance=1)
        b.goal=('hold',Vec())
        self.assertEqual(b.kit.plan(b,10,me,snap)[4],'armor lock on the stand')


if __name__=='__main__':
    unittest.main()

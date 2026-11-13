"""Demon owns the former tuned profile; Legendary has stock attributes and protected precision."""
import ast
import dataclasses
import hashlib
import json
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from brain import profiles,scaling
from brain.bot import Aim,HEAD_AIM,Bot,percentage_sniper
from brain.callouts import TIMING,Call,VoiceChannel
from brain.core import PlayerState,Vec
from escort_bots import TIERS as ESCORT_TIERS


class DifficultySeparationTests(unittest.TestCase):
    def test_legendary_only_changes_stock_overshoot(self):
        values=[]
        for style in sorted(set(profiles.PERSONALITIES)-{'wheelman'}):   # (the fingerprint's styles; Wheelman: Nov 13)
            for seed in range(5):
                p=profiles.make_profile('top',style,random.Random(seed))
                self.assertEqual(p.overshoot, 0.0)
                numeric = {k:v for k,v in vars(p).items() if isinstance(v,(float,int))}
                # Replay stock jitter to restore only overshoot for the stock fingerprint.
                rng = random.Random(seed)
                stock = {**profiles.TIERS['top'], **profiles.CRAFT['top'], **profiles.PERSONALITIES[style]}
                original = {k:v*rng.uniform(.9,1.1) for k,v in stock.items()}
                numeric['overshoot'] = original['overshoot']
                self.assertAlmostEqual(math.degrees(numeric['turn']), 650)   # (Nov 10, owner)
                numeric['turn'] = math.radians(1000)     # the stock turn speed, for the stock fingerprint
                values.append(numeric)
                self.assertGreater(p.reaction,.1385)
                self.assertLess(p.reaction,.1695)
                self.assertGreater(p.decide,.0899)
                self.assertLess(p.decide,.1101)
        digest=hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        # Captured from the author's installed 0.2.2-s181 profile factory.
        self.assertEqual(digest,'1af8a8c28e1c95322996ba8a3d7323f13e761351ff2619ef042aa90882d0153c')

    def test_demon_has_all_required_tables_and_independent_settings(self):
        for table in (profiles.REACTION,profiles.SHARP,profiles.TURN,profiles.PRESS,
                      profiles.TIERS,profiles.CRAFT,TIMING,HEAD_AIM,Bot.DRY_SHOTS,ESCORT_TIERS):
            self.assertIn('demon',table)
        for table in (profiles.SHARP,profiles.TIERS,profiles.CRAFT,TIMING):
            self.assertIsNot(table['top'],table['demon'])

    def test_demon_queues_a_real_team_callout(self):
        voice=VoiceChannel(random.Random(1))
        call=Call('seen','Mid',Vec(),0,1,'demon',False)
        self.assertEqual(voice.post(0,call),'queued')
        self.assertIn(call,voice.queue)

    def test_scaling_is_not_a_fixed_high_profile(self):
        p=scaling.profile(1,'rusher',random.Random(1))
        self.assertFalse(profiles.fixed_high(p))
        self.assertFalse(profiles.fixed_demon(p))
        self.assertIs(profiles.precision_profile(p),p)
        self.assertGreater(p.reaction,0)

    def test_head_and_turret_precision_matches_demon_without_mutating_base(self):
        me=PlayerState(0,0,'bot',Vec(),weapon='sniper')
        for gun in ('sniper','dmr','assault_rifle','tank_shell'):
            top=profiles.make_profile('top','rusher',random.Random(1))
            demon=profiles.make_profile('demon','rusher',random.Random(1))
            saved=dataclasses.asdict(top)
            a,b=Aim(top,random.Random(9)),Aim(demon,random.Random(9))
            for k in range(30):
                args=(k/30,1/30,me,1,Vec(12,k/20,.2),Vec(0,1,0),True)
                opts=dict(gun=gun,origin=Vec(0,0,.7))
                self.assertEqual(a.step(*args,protected=True,**opts),b.step(*args,**opts))
                self.assertEqual(a.rng.getstate(),b.rng.getstate())
                self.assertEqual(a.on_target(me,Vec(12,0,0)),b.on_target(me,Vec(12,0,0)))
            self.assertEqual(dataclasses.asdict(top),saved)

    def test_protected_context_clears_stale_ordinary_aim_error(self):
        p=profiles.make_profile('top','rusher',random.Random(2));a=Aim(p,random.Random(9))
        me=PlayerState(0,0,'bot',Vec(),weapon='assault_rifle')
        a.step(0,1/30,me,1,Vec(10,0,0),Vec(),False)
        self.assertNotEqual(a.err,(0,0))
        a.step(.01,1/30,me,1,Vec(10,0,0),Vec(),True,protected=True)
        self.assertEqual(a.err,(0,0))
        self.assertEqual(a.active_profile.lag,.001)
        self.assertEqual(a.p.lag,p.lag)

    def test_only_demon_uses_fixed_ten_ms_decision_deadline(self):
        src=(ROOT/'brain/bot.py').read_text();tree=ast.parse(src)
        plan=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='plan')
        block=next(n for n in ast.walk(plan) if isinstance(n,ast.If)
                   and ast.unparse(n.test)=='now >= s.next_decide')
        code=compile(ast.fix_missing_locations(ast.Module(body=block.body[:2],type_ignores=[])),'scheduler','exec')
        for tier in ('novice','average','strong','top','demon','scaling'):
            p=(scaling.profile(1,'rusher',random.Random(1)) if tier=='scaling'
               else profiles.make_profile(tier,'rusher',random.Random(1)))
            bot=SimpleNamespace(p=p,rng=random.Random(5))
            exec(code,dict(s=bot,now=1,profiles=profiles))
            expected=.01 if tier=='demon' else p.decide*random.Random(5).uniform(.8,1.3)
            self.assertAlmostEqual(bot.next_decide-1,expected)

    def test_demon_and_legendary_keep_sniper_policy_exception(self):
        me=PlayerState(0,0,'bot',Vec(),weapon='sniper')
        for tier in ('top','demon'):
            self.assertFalse(percentage_sniper(profiles.make_profile(tier,'sniper'),me))

    def test_vehicle_and_head_aim_calls_use_protected_context(self):
        tree=ast.parse((ROOT/'brain/bot.py').read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
               and isinstance(n.func,ast.Attribute) and n.func.attr=='step'
               and isinstance(n.func.value,ast.Attribute) and n.func.value.attr=='aim']
        vehicle=[n for n in calls if any(k.arg=='gun' for k in n.keywords)]
        self.assertEqual(len(vehicle),3)  # gunner, passenger look, armed driver
        for n in vehicle:
            if any(k.arg=='origin' for k in n.keywords):
                self.assertTrue(any(k.arg=='protected' for k in n.keywords))
        head=[n for n in calls if any(k.arg=='target_point' for k in n.keywords)]
        # the fight's, and (custom, Nov 7) Halo 4's real points from a gun seat and an armed driver's seat
        self.assertEqual(len(head),3)
        for n in head:
            self.assertTrue(any(k.arg=='protected' for k in n.keywords))


if __name__=='__main__':unittest.main()

"""Halo 4 animated head/view decoding, shooting geometry, and compatibility checks."""
import math
import random
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Aim, Bot, Perception, head_solution, live_head_ray
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to, eye
from brain.live import LiveH4F
from brain.profiles import make_profile


def pose(crouched=False):
    unit = bytearray(0x668)
    struct.pack_into('<HH', unit, 0x1BC, 120*52, 0x145C)
    struct.pack_into('<3f', unit, 0x64, 0, 0, -.38)
    matrix = struct.pack('<13f', 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, .01 if crouched else .25)
    view = struct.pack('<3f', 0, 0, .04 if crouched else .22)
    memory = {0x10000+0x145C+54*52: matrix, 0x10000+0xD50: view}
    live = LiveH4F.__new__(LiveH4F)
    live.g = SimpleNamespace(dll='halo4.dll', read=lambda a, n: memory.get(a))
    return live, unit, memory


def scene(tier='top'):
    bot = Bot(0, 0, make_profile(tier, 'sniper', random.Random(2)), {'name':'h4_test'}, random.Random(8))
    me = PlayerState(0, 0, 'bot', Vec(), weapon='dmr', view_pos=Vec(0, 0, .22), head_pos=Vec(0, 0, .25))
    target = PlayerState(1, 1, 'enemy', Vec(10, 0, 0), view_pos=Vec(10, 0, .22), head_pos=Vec(10, .08, .19))
    bot.notes, bot.shot_part = [], (1, True)
    return bot, me, target, Snapshot(0, [me, target])


class H4HeadAimTests(unittest.TestCase):
    def test_standing_and_crouched_pose(self):
        for crouched in (False, True):
            live, unit, _ = pose(crouched)
            head, view = live.h4_spartan_pose(0x10000, unit, (0, 0, 0))
            self.assertAlmostEqual(head[1], .02300628)
            self.assertAlmostEqual(head[2], (.01 if crouched else .25)-.006868857)
            self.assertAlmostEqual(view[2], .04 if crouched else .22)

    def test_other_dll_layout_and_short_reads_are_rejected(self):
        for dll in ('groundhog.dll','haloreach.dll'):
            live, unit, _ = pose();live.g.dll = dll
            self.assertEqual(live.h4_spartan_pose(0x10000, unit, (0,0,0)), (None,None))
        for count, offset in ((82*52,0x145C),(120*52,1),(120*52,0x9000)):
            live, unit, _ = pose();struct.pack_into('<HH',unit,0x1BC,count,offset)
            self.assertEqual(live.h4_spartan_pose(0x10000,unit,(0,0,0)),(None,None))
        for data in (None,b'',b'\0'*12):
            live, unit, memory = pose();memory[0x10000+0x145C+54*52]=data
            self.assertEqual(live.h4_spartan_pose(0x10000,unit,(0,0,0)),(None,None))

    def test_corrupt_transform_or_view_is_rejected_as_a_pair(self):
        for field,value in ((0,2),(1,float('nan')),(4,1),(9,-1),(10,1000)):
            live,unit,memory=pose();key=0x10000+0x145C+54*52
            matrix=list(struct.unpack('<13f',memory[key]));matrix[field]=value
            memory[key]=struct.pack('<13f',*matrix)
            self.assertEqual(live.h4_spartan_pose(0x10000,unit,(0,0,0)),(None,None))
        for view in ((0,0,20),(float('nan'),0,.22),(5,0,.22)):
            live,unit,memory=pose();memory[0x10000+0xD50]=struct.pack('<3f',*view)
            self.assertEqual(live.h4_spartan_pose(0x10000,unit,(0,0,0)),(None,None))

    def test_final_shot_hits_animated_point_from_matched_view(self):
        bot,me,target,snap=scene()
        def plan(*args):
            bot.shot_part=(1,True)
            return Action(fire=True,yaw=.5,forward=.3,strafe=.2)
        bot.plan=plan
        act=bot.think(0,1/30,snap,None,None,[])
        self.assertEqual((act.yaw,act.pitch),angles_to(me.view_pos,target.head_pos))
        self.assertLess(act.pitch,0)  # the strafe animation lowers the actual target head
        self.assertAlmostEqual(math.cos(act.yaw)*act.forward-math.sin(act.yaw)*act.strafe,
                               math.cos(.5)*.3-math.sin(.5)*.2)

    def test_tracking_and_precise_sniper_share_world_point(self):
        bot,me,target,_=scene()
        for precise in (False,True):
            aim=Aim(bot.p,random.Random(8))
            got=aim.step(0,1/30,me,1,target.pos,Vec(),True,origin=me.view_pos,
                         target_point=target.head_pos,precise=precise,protected=True)
            expected=angles_to(me.view_pos,target.head_pos)
            self.assertAlmostEqual(got[0],expected[0])
            self.assertAlmostEqual(got[1],expected[1])

    def test_sniper_hit_roll_uses_matched_view_without_changing_outcome(self):
        bot,me,target,snap=scene('strong')
        me.weapon,me.weapons,me.mag='sniper',['sniper'],[4]
        bot.sniper_roll=dict(mag=4,hit=True,side=1,margin=1,next_roll=10)
        act=Action(fire=True)
        bot.percentage_sniper_shot(0,me,snap,act)
        self.assertEqual((act.yaw,act.pitch),angles_to(me.view_pos,target.head_pos))
        self.assertTrue(bot.sniper_roll['hit'])

    def test_reach_and_partial_h4_fallback_do_not_mix_origins(self):
        _,me,target,_=scene()
        me.view_pos=None
        self.assertEqual(head_solution(me,target),(eye(me),target.pos+Vec(0,0,.62)))
        target.view_pos=None  # Reach continues to use its existing animated-head point
        self.assertEqual(head_solution(me,target),(eye(me),target.head_pos))
        me.vehicle=10
        self.assertIsNone(live_head_ray(me,target))

    def test_firing_visibility_uses_actual_point_and_respects_obstruction(self):
        bot,me,target,snap=scene();calls=[]
        class Terrain:
            see_clear=True
            allowed=True
            def sees(self,*a): raise AssertionError('legacy-height visibility used')
            def point_los(self,a,b,mode=None):
                calls.append((a,b,mode));return self.allowed
        terrain=Terrain();bot.T=lambda:terrain
        bot.per.clear_at[1]=0;bot.per.target_parts={1:(False,True)}
        self.assertTrue(bot.line_clear(0,me,1,snap,head=True))
        self.assertEqual(calls[-1],(me.view_pos,target.head_pos,'shot'))
        terrain.allowed=False
        self.assertFalse(bot.line_clear(0,me,1,snap,head=True))

    def test_perception_uses_actual_head_visibility(self):
        bot,me,target,snap=scene()
        class Terrain:
            def target_parts(self,*a,**kw): return (False,False)
            def point_los(self,a,b,mode=None): return a==me.view_pos and b==target.head_pos
            def sees(self,*args): return False
        terrain=Terrain()
        bot.per.update(0,me,snap,terrain.sees,[])
        bot.per.update(1,me,snap,terrain.sees,[])  # Legendary now has its stock recognition delay
        self.assertEqual(bot.per.target_parts[1],(False,True))
        self.assertIn(1,bot.per.visible_enemies())

    def test_h4_player_reader_publishes_both_pose_endpoints(self):
        live,unit,memory=pose()
        player=bytearray(0x1E4)
        struct.pack_into('<H',player,0,1)
        struct.pack_into('<I',player,0x2C,123)
        struct.pack_into('<I',unit,0x24,0xFFFFFFFF)
        struct.pack_into('<4I',unit,0x640,42,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF)
        struct.pack_into('<3f',unit,0x4E0,1,0,0)
        memory[0x10000]=bytes(unit)
        memory[0x80000]=bytes(player)
        live.g.read=lambda a,n: memory.get(a,b'')[:n]
        live._array=lambda _: (0x80000,1,0x400)
        live.object=lambda handle: 0x10000 if handle==123 else None
        live.weapon_name=lambda _: 'dmr'
        live._vitals=lambda *args: (1,1)
        live.ability=lambda _: ('',False)
        live.tracker=lambda _: True
        result=live.players()[0]
        self.assertIsNotNone(result['head_pos'])
        self.assertAlmostEqual(result['view_pos'][2],.22)
        self.assertEqual(result['weapon'],'dmr')


if __name__=='__main__':
    unittest.main()

# Custom release history

## Unreleased

### Slayer anchor priority and paired posts, 2026-11-08

- The Team Director can assign up to two anchors per Slayer role pass, with each assigned to a separate nearby post. Fixed Demon bots get first pick regardless of personality, followed by Campers, Snipers, and other eligible bots. Distance and current role break ties within each priority group. The aggressive Slayer plan still sends hunters toward the fight.
- A focused director check verified the priority order, two Demon anchors, separate posts, the single-bot fallback, and the Slayer posture and mode rules. All 299 regression tests passed. Gameplay validation needs a fresh bot process.

### Teleporters by gametype; Gore Valley's stuck pad, patrol area and hot spot, 2026-11-08

- The owner's two reports from the Gore Valley Slayer game (`logs/bug_reports/h4_ca_gore_valley_20261107-222718`).
- "Bots get stuck here" (34.8 s):
  - Sword117 and Havoc94 (Easy, roaming) stood at about (-1.0, -6.1), by red's spawns, from 17 s to past 80 s. Lord117 (Normal) was caught there twice.
  - Cause: the nav's next step for 7 of the map's 11 zones was the bots' own cell. `maps/h4_ca_gore_valley/features.json` (`tools/map_features.py`) pairs a two-way teleporter there with one at the other base (-1.09, 43.53). The pad's objects are Dominion's: `fw_teleporter_2_way` under a netgame flag labelled "dominion". In Slayer and CTF there is no pad. `Terrain.nav` said "on a teleporter that is the way: step onto its centre", and nothing teleported them.
  - The same labels elsewhere: Canyon has a Dominion pair beside its other modes' one-way pads ("no_dom"); H2A Warlock's four and Ascension's one are removed in CTF ("ctf_delete").
- Fix in `brain/maps.py`:
  - `teleporter_tag` reads the label of the nearest netgame flag on each teleporter end. Canyon's Dominion pads stand 0.1 u from its receivers.
  - `tele_in_mode` applies the labels: "dominion" only in Dominion (brain/modes.py names it territories); "no_dom" in all modes but Dominion; "ctf_delete" in all but CTF.
  - `set_mode(m, mode)` keeps only the pairs a mode has in `m["teleporters"]`, the list the nav links and the bots' pad logic read, with the whole set in `m["teleporters_all"]`. A terrain built before is dropped when the list changes.
  - `tools/live_bots.py` reads the starting mode (`start_mode`: CTF by the engine, as the snapshot reads it, else `mode_of` with its aliases) and calls `set_mode` before each nav build, the variant one included. It prints any pads left out.
- "Make this a patrol area and a hot spot" (71.8 s): he was dead when he filed it. From 61.6 s he stood 9 s still at (9.28, 18.75, 2.43), the "Red rockets" spot, until he was killed at 70.4 s. That spot:
  - New `maps/h4_ca_gore_valley/infantry_patrols.json`: one patrol point, shared by both teams (the existing patrol rules: Invasion excluded).
  - `maps/h4_ca_gore_valley/positions.json`: an owner power position, via `tools/power_positions.py --add`, score 1.0, above every computed spot. It sees 4 spots, height 15.5, with a duck spot. The 8 computed rows are kept.
  - Every Slayer (230 per team) and CTF (70 and 78) spawn reaches it.
- Validation:
  - `tools/test_mode_teleporters.py`, 6 tests: the label rules; the nearest label; Gore Valley's pads only in Dominion; Canyon's one-way pads kept outside Dominion and its Dominion pair only in it; the patrol and hot spot load; and on the real terrain no zone's next step from the stuck cell is the cell itself in Slayer.
  - All 299 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4, every tier: shots at Warthogs and their riders go to the real point, 2026-11-07

- Owner's request: make every difficulty shoot the Warthog, and its drivers and passengers, properly.
- What was wrong in Halo 4 (all tiers but the new Demon rider path):
  - The live snapshot gives a rider his vehicle's place, its origin (`tools/live_bots.py`). The generic aim adds 0.35 (chest) or 0.62 (head) to that place, and aims from a generic eye 0.4 u over the real view.
  - A chest shot at a rider went just under the vehicle's origin, into its body. A head shot went 0.22 u over the origin: near a Warthog driver's head (0.24), but under the passenger's (0.43) and the gunner's (0.49-0.68).
  - A rocket or laser went at that same point, not at the vehicle's body.
  - Seated shooters were off too. The Warthog gunner aimed from its pivot (the collaborator's 8baecbe) at a man's place + 0.35, the top of his head. A passenger aimed from his vehicle's origin + 0.62, and a Ghost driver likewise, where the game's own view for those seats is his eye, or the vehicle's camera point at its origin (the seat capture).
- New `h4_aim_point` (`brain/bot.py`): the real point a shot goes to.
  - A rider: his seated head (`h4_seated_head`; else the vehicle origin + 0.24), or the upper chest 0.12 u under it.
  - A gun that kills vehicles or splashes, or a gun Warthog's gauss or rocket cannon: the vehicle's body, its origin (a tank's rear hatch from behind its beam, as `weak_point`).
  - A man on foot: his live head or torso, else his place's own heights.
- New `h4_origin`: on foot our live view (else place + 0.22); seated, the seat's view (`vehicles.H4_SEAT_VIEW`, `h4_seat_view`, from the capture: driver at the vehicle's camera point, the Warthog passenger's eye).
- Used, Halo 4 only and every tier, with each tier's own aim error, lead and trigger pace kept:
  - On foot at a rider or his vehicle (`fight`), where the Demon rider path does not already aim.
  - A gunner or passenger at anyone (`drive`). The gunner keeps its pivot. A seat not captured (the Mongoose passenger) keeps the generic pair rather than mixing one real end.
  - A driver's own gun at anyone (`drive`, the Ghost); a tank keeps its camera view (`vehicles.DRIVER_VIEW`).
- Unchanged: on-foot shooters at men on foot (the generic pair is consistent there: both ends sit 0.4 u high), Reach and the other games, and Legendary's protected seat precision (still passed).
- `tools/test_difficulty_separation.py` counted one aim call with an explicit point; it now counts the three (the fight's, a gun or passenger seat's, an armed driver's) and still checks each passes the protected context.
- Validation: `tools/test_h4_vehicle_aim.py`, 10 tests:
  - The points: a rider's head and chest, without a head read, vehicle killers at the body, a tank's hatch from behind, and a man on foot.
  - The origins: on foot; the passenger's eye; the gunner's own; the Ghost driver's.
  - A Heroic on foot aims at a Warthog passenger's chest from its view, where the generic pair aimed 0.03+ rad lower, into the body; Reach keeps its aim.
  - A gunner aims from its pivot at a man's real torso; a passenger aims from his eye.
  - All 293 regression tests pass. Gameplay is untested; the Ghost driver's aim from the vehicle camera point is INFERRED from the capture's view point. The bot process must be restarted.

### Halo 4 Demon aims at riders' heads; seated head reader; vehicle hulls, 2026-11-07

- Owner's request, after his seat capture: `logs/h4_seat_capture_20261107-233231`, Grind, solo. He sat as Warthog driver, passenger and gunner (aiming all round and up), then in a Ghost and as Mongoose driver; 3,714 seated poses.
- What the capture showed:
  - The animated target_head is sane in every seat: the bone checks passed on all poses, and the head stood within 0.45 u of the unit's place and within 1.6 u of its parent. The gunner's parent is the chaingun, which rides the Warthog.
  - The view point (+0xD50) is the vehicle camera's for drivers and the gunner, and the first-person eye for the passenger. That is why every seated pose failed `h4_spartan_pose`'s view and base guards.
  - In his Gore Valley CTF, Demons spent 44% of their on-foot fight time at riders and did a quarter of their on-foot damage rate there. (Corrected in the next entry: the snapshot gives a rider his vehicle's place, so the generic aim went mostly into the vehicle's body, not over his head as first written here.)
- New `LiveH4F.h4_seated_head` (halo4.dll, the 120-node rig): the seated head, guarded by the rig layout, a sane head transform, within 0.6 u of the place (`SEATED_HEAD_PLACE`) and 2.0 u of the parent (`SEATED_HEAD_PARENT`). `players()` publishes it as `head_pos` with `view_pos` None. Replayed, all 3,714 captured seated poses pass. On foot nothing changed.
- New `vehicles.HULLS` / `hull_blocks`: rough bodies as boxes in each vehicle's frame. INFERRED around the captured heads and bones, not from the tags' collision models.
  - Warthog (every kind): a chassis up to the riders' waists, plus the hood ahead of the cab.
  - Mongoose: a low body.
  - Ghost: a hull, plus the nose and canopy ahead of the driver.
  - `hull_blocks` tests our shot line against them, leaving the head's own last 0.06 u out.
- Halo 4 Demon at a rider (`h4_rider`: we on foot with our live view, he seated with his seated head read):
  - `h4_demon_fire` covers him. Both parts are his head; his body is in the vehicle.
  - Perception: a shot needs a clear line to his head over the level and past his vehicle's body (`rider_hull_clear`). Seeing him is as before, the vehicle he rides, so a Ghost head-on is seen though its canopy covers him.
  - `line_clear` adds the hull test.
  - The view lock and the lead apply as on foot, with the rider's lead cap at 25 u/s (`RIDER_VEL_MAX`) so a Warthog's 11 u/s is led.
  - `dry_part`: a rider 0.8 s and 3 presses dry is held off for 1.5 s (`rider_dry`, note "rider dry: hold, go round"). This catches rounds the real hull takes where the model has none.
- Unchanged: on-foot targets, the other tiers (fixed in the next entry), Reach, and vehicle killers (rockets and the like).
- Validation: `tools/test_h4_rider_aim.py`, 13 tests:
  - The seated head read and its guards: place, vehicle, scale, dll.
  - Hulls: the Warthog driver open from the side and above and the gunner from behind; low rounds through the hood and the far side, and a turned Warthog; the Ghost canopy from the front, open from behind; no hull, no block.
  - The rider gate; lead at vehicle speed.
  - Perception: shoot the head, see the vehicle; with the hull in the way, seen but not shot.
  - The fight: taps on an exposed rider's head; no shot through the hull; a dry rider held off.
  - All 283 regression tests pass. Gameplay is untested; the hull sizes need live checking. The bot process must be restarted.

### Demon glances at a close radar dot behind it; Halo 4 vehicle seat capture tool, 2026-11-07

- Owner's requests, after his Gore Valley CTF review (`logs/trace_h4_ca_gore_valley_20261107-223617`).
- Demon radar glance:
  - The problem: 11% of his hits on Demons came on their objective runs while they had him only as a radar dot. Walking, a bot's look at a dot is held within 50° of the walk (`walk_cone`). A dot behind cover more than 6 u away was not looked at at all (`look_point` fell back to the path). Demon sees 90° each side, so a man behind it stayed unseen.
  - New `Bot.dot_glance`: a fixed Demon on foot and not carrying, with a fresh (0.7 s) radar dot within 20 u more than 80° off its view and not in its eyes, looks his way. The glance lasts 0.7 s at its whole turn speed (`whip`), is not held to the walk's cone, and does not slow the walk. It is at most once every 2 s per man, nearest dot first; the note is "radar: glance at #k" (att "glance"). If he is really there with a line, perception sees him and the fight on the way takes him (`on_way_target`).
  - Replay on that match: 9 of the 10 radar-only hits on Demon objective runs met the glance's conditions. All 9 were OutlawMarine at 48.9-50.7 s, with him 4.8-5 u behind at 128-180°; it died there.
  - Not covered: 5 hits on hunts where he was in front within 15° at 11-19 u and the Demon still did not see him (a sight-model question, open).
- `tools/h4_seat_capture.py`, a read-only Halo 4 capture for seated Spartans:
  - Why: `h4_spartan_pose` reads the animated head and view only on foot, so Halo 4 Demon's aim cannot target a rider.
  - What it records at 30 Hz for the person (`--everyone` for all players): place, model base, view point (+0xD50), target_head (node 54, unguarded), seat (+0x2C), the parent chain (a Warthog's chaingun rides the Warthog) with its forward and up, the head and view in the vehicle's frame, the on-foot reader's verdict, and which of its guards a seated pose fails. The full 120-node bone block is kept every 6th tick.
  - `--summary <dir>` gives per vehicle and seat the medians and p10-p90 in the vehicle frame and the guard failure shares. Output goes to `logs/h4_seat_capture_<stamp>/` (gitignored).
  - It sends no input, writes no game memory, and can run beside the brain.
- Validation:
  - `tools/test_demon_dot_glance.py`, 6 tests: a dot behind is glanced at; the glance holds, then waits 2 s; it ends once its eyes have him; none for a dot in view, past 20 u or stale; none for callouts, Legendary, a carrier or a rider; the nearest dot first.
  - `tools/test_h4_seat_capture.py`, 3 tests on a stand-in Halo 4 memory: the on-foot row matches the reader; a seated row in the vehicle frame at three yaws; the summary groups by seat.
  - An end-to-end run of the capture loop on the stand-in memory took 36 samples in 1.2 s.
  - All 270 regression tests pass. Gameplay is untested; the capture tool has not met a live game yet. The bot process must be restarted for the glance.

### Demons do not drive Warthogs or Mongooses; Normal and Heroic are the drivers, 2026-11-07

- Owner's request, after his Halo 4 Gore Valley CTF (`logs/trace_h4_ca_gore_valley_20261107-223617`; his team won 2-0, he went 25-8, the 3 Demons 16-25 together):
  - OutlawMarine and Slayer7 drove about a minute each, and a Warthog's driver has no gun.
  - 28% of his hits on Demons came while they rode vehicles.
  - 44% of their on-foot fight time went at riders, at about a quarter of the damage per second they did to men on foot (0.09/s against 0.36/s).
- New `vehicles.DEMON_NO_DRIVE`: every Warthog (chaingun, rocket, gauss, troop) and the Mongoose and Gungoose. A fixed Demon does not take their wheel in any game, outside Race (every racer drives). It can still take their gun or a passenger seat. Ghosts, tanks, aircraft and the other vehicles are unchanged.
- How it is enforced:
  - `Director.crew_orders` sends no Demon to drive them, drops a kept drive job a Demon held, and skips Demons for the rocket and gauss Warthogs (power vehicles) too.
  - `Bot.may_drive` guards the bot's own trip pick, a committed vehicle run, the Invasion spawn errand and a drive order.
  - A Demon that ends up at such a wheel anyway (a hijack, or a seat it was put in) gets out with Use held (`exit_until`, as every get-out).
- Driver priority (new `profiles.driver_priority`): for a Warthog or a Mongoose the director sends a Normal or Heroic bot within reach first, then Scaling and Legendary, then the nearest. Before, it sent the nearest, and for the gun Warthogs Demon came first. Gunner calls are unchanged; Demons still come first for the gun.
- `tools/test_mongoose_transport.py` (the collaborator's 1b59ccd) used a Demon as its test driver. It now uses a Legendary, which may still drive and whose juke always answers a threat (Heroic's 0.6 juke failed the evade test). The trip, wait, evade and dismount checks are unchanged.
- Validation: `tools/test_demon_no_drive.py`, 11 tests (which vehicles; driver priority; may_drive with Race excepted; a Heroic drives the Warthog though the Demon is nearer; Normal before Legendary; a Demon alone is never sent; a Demon still drives a Ghost; a kept job dropped; a seated Demon gets out of a Warthog's or a Mongoose's wheel but stays on the gun; a Heroic at the wheel drives). All 261 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 Warthog chaingun aim origin, 2026-11-07

- Recognize the attached `storm_warthogchaingun` on Halo 4 Warthogs and aim it from its pivot. The Harvest model markers put the pivot 0.616 world units behind the chassis origin and 0.924 above it. Rotate that offset with the Warthog's forward and up vectors. If orientation is unavailable or invalid, use the existing aim fallback.
- The owner's stationary Harvest recording showed the aim turning to both sides of the vehicle. Verified the model offsets and checked the reader and snapshot together with Harvest tag names, a rotated chassis, targets on both sides, and invalid orientation. All 250 regression tests passed. Bullet impacts still need a live test after the bot process starts again.

### Reach Demon leads its shots one tick and switches a dry part, 2026-11-07

- Owner's request, after a fight-by-fight review of his Reach games: the Rasu game (`logs/trace_reach_forge_halo_20261107-191109`, 8 Demons, 647 s), with Headlong and Settlement as cross-checks.
- What the review found:
  - Duels: 69 with Demons. He landed the first hit in 40, and a Demon died in 17. When his hits landed, the Demon was: fighting him in view, 38%; in a vehicle seat, 23%; retreating, 11%; fighting someone else, 11%; the rest hunting, fetching or boarding. Its own belief said it saw him in about 79% of those hits.
  - Not bloom: Demon DMR rounds that left the gun (magazine drop) landed 48% on Rasu and 54% on Headlong; Legendary 56%. A first shot after 0.8 s or more of rest, with no bloom, landed 44%, against 47-49% at the normal pace.
  - Not dropped presses: on foot, 93% of paced presses fired, 80% of first presses, and 25% of presses under 0.38 s (the DMR refires about every 0.4 s). Presses from a vehicle seat (150) never fire the DMR.
  - Lead: against a man crossing its view at 1 u/s or more, the applied view trailed him by a median 0.07 u (hits) to 0.105 u (misses). 111 of 164 missed head rounds were at such a man. Against a still man there was no trail. Re-aiming those shots with one tick of lead put 67% of the misses' views within 0.06 u of his head line (34% without) and 83% of the hits (60%); 0.05 and 0.068 s did no better.
  - Height: rounds up at him 1+ u above landed 41%, down at him below 62%.
  - Sight from below: real but smaller. About 21% of his hits came while the Demon had him only as a radar dot or from his hit, including him 2 u above at 2 u (Settlement) and 7 u below. The Forge World variant's pieces are not in the offline replay, so the cause is not confirmed; the 0.6 u feet-slab rule is the suspect. Not changed.
- Changes (Reach Demon direct fire only; `reach_demon_direct_fire`):
  - Fight aim and the final DMR snap use `lead_ray`: both ends moved on by `DEMON_LEAD_S` (0.034 s, one brain tick) of our own and his read velocity, ignored past `LEAD_VEL_MAX` (8 u/s). Legendary's protected, unled head point is unchanged.
  - The Halo 4 dry-part switch is now shared (`Bot.dry_part`, `part_flip`; `PART_DRY_S` 0.8 s, `PART_FLIP_S` 1.5 s). It also needs 3 presses at the part with no hit (`PART_DRY_SHOTS`), because two paced Reach misses in a row are common. In Halo 4 the taps reach 3 presses well within 0.8 s, so its behavior is unchanged.
  - Renamed the shared constants: `H4_LEAD_S` to `DEMON_LEAD_S`, `H4_VEL_MAX` to `LEAD_VEL_MAX`, `H4_DRY_S` and `H4_FLIP_S` to `PART_DRY_S` and `PART_FLIP_S`.
- Unchanged: Reach Demon's cadence and bloom handling, its part preference (head when clear), its sight, Legendary, the lower tiers, Scaling and Halo 4's other rules.
- Validation: `tools/test_reach_demon_lead.py`, 5 tests (the led final DMR shot; a teleport read not led; Legendary's head point unled at the final shot while Demon's is led; a dry head gives way to the chest after 0.8 s and 3 presses; landing rounds keep the head). The existing Reach Demon fire tests still pass with still bodies. All 250 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 Demon: rifles back on the head, torso-centered body point, dry-part switch, 2026-11-07

- Owner's request: review each fight of his latest Adrift 1v1 on the new Halo 4 Demon code (`logs/trace_h4_wraparound_20261107-210807`, with its bug report at 126.4 s, "Find out why I won this gunfight"). The trace carries the new part fields and no Demon thruster charges or thrusts to cover, so it ran the current code.
- 18 fights: he died 8 times and the Demon 9. Both fired the BR at its full rate (bursts 0.33-0.4 s apart; a kill in 1.2 s when every round lands). The fights turned on rounds landed:
  - Body versus head, both Adrift games on this code (also 20261107-205747): firing at the body landed 1.44 and 1.52 BR rounds a second over 68 s and 53 s of firing, and only 0.40/s at close range on level ground. Firing at the head landed 5.64 and 4.93/s, against a BR best of about 7.5. The body-first rule of the previous entry was wrong for rifles.
  - Body point: Halo 4's place (+0x40) sits a fixed 0.045 u ahead and 0.054 u right of the model's base in the player's aim frame, across all 1,626 poses of `logs/h4_bot_aim_probe_2026-11-06`. The body point was aimed at the place, not at the torso.
  - Fight 8 (the bug report, 118.2-120.0 s): he dropped off a ledge to 4.4 u and nearly stood still. The Demon's view stayed within about 1° of his body and fired a burst every 0.4 s, but only 1-2 of each burst's 3 rounds landed; all 3 of his landed every time.
  - Fight 17 (236.8-239.3 s): from a ledge 1.3 u above him at 4.3 u, the head burst landed 3 of 3. Then 20 presses at the body over 1.4 s did no damage while he stood almost still. The level data called the body line clear; the ledge lip took the rounds.
  - Slow starts (fights 1, 3, 9, 16): see-through cover, ledge lips and his own out-of-sight hits. These are geometry, not aim.
- Halo 4 Demon only:
  - Rifles, pistols and snipers (`PRECISION`) aim at the head again; automatics and the shotgun aim at the body; a covered part still yields to the clear one.
  - The body point is his place moved -0.015 u forward and 0.04 u left in his aim frame (`H4_BODY_FWD`, `H4_BODY_LEFT`), onto the torso between the model base and the head.
  - New `Bot.h4_dry_part`: after 0.8 s of presses at one part with no drop in his shield or body (`H4_DRY_S`), while the other part's line is clear, it fires at the other part for 1.5 s (`H4_FLIP_S`; note "part dry: the chest / head"). A hit, a new target or a new part restarts the clock.
- Unchanged: the real-height sight, the view lock and lead, the tapped trigger, the thruster rules, Reach Demon, Halo 4 Legendary and the other tiers.
- Validation: `tools/test_h4_demon.py`, 18 tests (part by weapon at any shield; the torso point in his aim frame at four facings; head taps; a covered head takes the body; the dry switch at 0.8 s holding the body afterwards; hits keep the part; no switch onto a covered part; and the earlier sight, lock and cadence tests). All 245 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Demon uses no thruster in gunfights outside Infection, 2026-11-07

- Owner's requests: remove the Demon's thruster charge during gunfights in every mode except Infection, then its thrust to cover as well. In his Warhouse game (`logs/trace_h4_ca_warhouse_20261107-195112`) Demons thrust in fights for two reasons: "dash in to close" 8 times (the charge: 3-6.5 u from the man, with a close-range gun or his shield down) and "thruster to cover" 10 times (shield under 0.3 and shot in the last 0.8 s; once more on a retreat).
- `Kit.plan`: for fixed Demon outside Infection, the thruster takes neither the fight's dash-in nor the cracked-and-shot thrust to cover. Kept: Demon's thrusts out of a grenade, out of a lunge, across a sniper's lane and onto the capture point with the flag; Demon's evade (Reach); every other tier; Scaling; and Infection, where the infected's runs at survivors, the dash-in and the thrust to cover stay as they were.
- Validation: `tools/test_demon_thruster.py`, 5 tests: no charge for Demon in Slayer, CTF, Oddball, King, Assault and Invasion (shield down, or a shotgun at full shield); Demon still charges in Infection; Normal, Heroic and Legendary still charge; no thrust to cover for Demon in Slayer, CTF and King, but it still thrusts to cover in Infection, as do Heroic and Legendary; Demon still thrusts out of a grenade. All 240 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 Demon: real sight heights, body then head, locked view, tapped trigger, 2026-11-07

- Owner's request: Halo 4 Demons are the weakest bots of all the games; make them aimbot-hard there without changing the other games. Evidence: his Warhouse game (`logs/trace_h4_ca_warhouse_20261107-195112`, "Slayer was missing to my right with a dmr") and the 1v1 on Adrift (`logs/trace_h4_wraparound_20261107-201103`, "missed me twice while I was strafing").
- Findings, from the traces and the collector's 30 Hz positions:
  - Halo 4 reports a body 0.38 u over its floor (`H2A_FEET`). The generic sight pair (eye pos + 0.62, chest pos + 0.35) sat 0.38 u over both bodies. Replayed on the maps' terrain, 369 of the Adrift Demon's 1,183 seen rifle fight ticks (873 of 8,751 on Warhouse) were "seen" over cover that every real line (view to head, chest, belly) crossed. It held fire and stood in the standoff instead of going round.
  - Rounds land one tick after the press (hitscan). At hits and misses alike the applied view was within 0.05-0.1 u of his head, and misses did not depend on his speed, yet about 40% of presses did no damage (26 of 57 in the 1v1). A round that passes a head misses the whole body, and misses leaned high.
  - Cadence: Reach's DMR pace (0.4 s, x1.1-1.35 past 10 u). With perfect aim, a 5-shot kill took about 1.9 s.
- Halo 4 Demon on foot only (`h4_demon_fire`: game h4, fixed Demon, live head/view pair on both bodies, a hitscan-like gun):
  - Perception's chest line runs from the live view to the chest under the live head (head z - 0.16); the head line was already live.
  - Part choice: the body while he is shielded (same shield damage, bigger mark), the head once his shield is at or below 0.05 and for snipers; the clear part if only one is clear; automatics stay on the body. `line_clear` and `fire_gate` use the same live rays. A seen man with no clear part counts as glassed, so the Demon goes round instead of standing.
  - `Bot.think` locks the view onto the chosen part every tick its line is clear: past the 480°/s turn cap, led by one brain tick (0.034 s) of both bodies' read motion (ignored past 8 u/s), with the walk direction kept. Not during a grenade throw.
  - Trigger: semi-automatics get a fresh press every other tick within 30 u, so the gun fires as soon as it can; past 30 u the old pacing stays. Automatics hold within 20 u. No crouch at the kill shot (it drops the view 0.18 u under the locked shot).
- Unchanged: Reach Demon's exposed-part fire, Halo 4 Legendary and the lower tiers, Scaling, H2A, vehicles and the protected Legendary/Demon head and turret precision outside this Halo 4 path.
- Validation: `tools/test_h4_demon.py`, 15 new tests: the gate; part choice and lead; no sight over cover with the generic pair open; the real chest line; Legendary's generic chest; tapping on alternate ticks on the body; head at no shield; head when the body is covered; no line, no shot and no lock; an automatic held; pacing past 30 u; the led lock keeping the walk; the grenade's own aim; and no lock for Reach Demon or H4 Legendary. All 235 regression tests pass. Gameplay is untested. Not verified: Halo 4's true refire times (no H4 ammo reader, so tapped presses the gun cannot take yet are not measured), whether the read-to-shot lead is one tick, and the chest offset on every pose. The bot process must be restarted.

### Demon fights on the way on objective runs too, 2026-11-07

- Owner's request: extend fight-on-the-way to objective runs. `Bot.on_way_target` now also covers an "objective" goal outside Slayer (Slayer posts still turn into a full fight) and Race (laps). Covered: CTF runs, Invasion pushes, Oddball, King of the Hill, Territories, Assault and so on. A Demon on foot running the objective with a man in view within 30 u shoots him and keeps running.
- The objective's own last steps are left alone: no fighting on the way within 3 u of the point (`ON_WAY_OBJ_LAST`), while standing on a loose core or flag (`stay_at`), or on its exact steps onto an objective (`walk_onto`). Carriers are excluded as before. Flag, core and bomb pickups run after any goal, so they are unaffected; the ball pickup is within the 3 u.
- Validation: 2 new tests in `tools/test_shoot_back.py`, 21 there in all. Through `think`: CTF, Invasion and KOTH runs fire on the way and keep heading to the point. Within 3 u, in Slayer, in Race and for a Legendary: no fire. All 242 regression tests pass, including the collaborator's 3 Demon commits (4d23bac, f8b68b7, 12f28c2) that landed in the meantime. Gameplay is untested. The bot process must be restarted.

### Demon fights on the way to a gun, 2026-11-07

- Owner's request: rather than dropping its errand, a Demon should keep going to the gun and fight on the way. A 6.6 s look at a man in view without a shot is too long.
- New `Bot.on_way_target`. A Demon on foot going for a gun or on a hunt (including the anti-vehicle mission's walk and hunt), with a man in view within `DEMON_ENGAGE_R` (30 u), fights him while it walks on. This reuses the patrol's existing way of moving: fight's aim, trigger and weapon choice, with the walking input turned toward the goal. In the last 1.5 u onto the gun, the normal pickup takes over. No fighting on the way while dry, carrying the objective or in a vehicle.
- `Bot.shoot_back`'s engage-on-sight (the entry below) narrowed to what cannot be fought on the way: a vehicle walk, a hold, a Slayer post (`DEMON_SIGHT_OVER`). A gun or a hunt is no longer dropped for the fight; the collaborator's fetch commit is a gun, so it stands as designed. Being shot, or a man within 8 u, still makes the fight the goal, as before.
- Validation: `tools/test_shoot_back.py` now has 19 tests. Through `think` on a flat floor: the Demon fires at the man while walking toward the gun; a man 40 u off and a Legendary in the same scene walk on without firing; no shooting in the last steps onto the gun. Engage tests are updated for the narrowed set. All 220 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Demon engages a man in view instead of running errands; DMR accuracy findings, 2026-11-07

- The owner's Rasu game (Forge World variant `forgeworld_rasu_031`, `logs/trace_reach_forge_halo_20261107-191109`, played on custom.7 before the upstream merge). He felt Demons were "slower mentally" and filed two reports:
  - "HeadshotTV took a long time to shoot at me" (t 464): from t 439.1 the Demon saw him by eyes at 22 u. For 6.6 s it ran errands: a plasma-pistol walk for an enemy vehicle (anti-vehicle mission 2.4), that vehicle's hunt (2.3, looking straight at him without firing), and a gun pickup (1.85 + 0.2 kept) over the fight's 1.87. It fired only once his first shot hit it (shoot_back, "shot at: answering him"), and lost the duel.
  - "FatalHawk was missing at least 4-5 shots" (t 618): at 597.2 it saw him at 28 u on its way to a gun, then turned to hunt the bot that hit it, then fired 5 DMR shots at 22 u. The first came with its view 67° off; the next four had the view within about 1° of his head, and none landed.
- The brain itself was not slow: ticks were normal (37 ms median, p99 115 ms). Across the match, with a man in view within 30 u and not being hit, Demons chose a fight in 59% of 13,187 decisions, an item 26% (beating the fight by a median 0.35) and a vehicle 10%.
- `Bot.shoot_back` (fixed Legendary/Demon, from the previous update) now also engages on sight for Demon only: on foot, a man in view within `DEMON_ENGAGE_R` (30 u) is fought over its errands (item, vehicle, hold, patrol, objective in Slayer, and the anti-vehicle mission's walk or hunt) by 0.4, without waiting to be shot. Kept as they were: the gun it was sent for a few steps off (the collaborator's fetch commit, `FETCH_COMMIT_SCORE`), its objective outside Slayer, the team posture's avoid, regroups, retreats, radar and attacker hunts, and boarding. A crew order's walk to a vehicle also yields to the fight. Legendary still answers only when shot.
- Not changed: DMR accuracy. Demon DMR shots landed less often than Legendary's on every Reach trace checked, before and after Codex's exposed-part fire commit. Demon: Headlong 68%, Settlement 60%, Boneyard 57%, Forge World 59% / 55% / 48% (Rasu). Legendary: 61-70%; Heroic and Normal 49-65%. The trace explains none of the gap: not view turn on the shot tick (under 1°: 48.5% in Rasu), not zoom, not the target's speed or jumping, not bloom (first shots miss most, for both tiers). The final DMR head snap is the protected Legendary/Demon precision path, so it was left alone. A controlled check in game is the next step: the owner standing still at 20 u from one Demon and one Legendary, counting hits. Hit detection here is the shooter's own read of the target's shield and body within 0.35 s, so other shooters and regen add noise.
- Validation: 6 new tests in `tools/test_shoot_back.py` (fights over a gun on sight; range and Demon-only; avoid; the fetch commit wins; anti-vehicle hunt counts and objective only in Slayer; a radar hunt is not an errand). All 217 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Upstream 0.2.2-s181 build 20261107-1530 merged, 2026-11-07

- The owner ran his friend's installer over the custom.7 install. The installer reset 14 of our customized files to s181, overwrote 50 that his update changed, and deleted 26 custom-only files (`brain/anticipate.py`, `tools/owner_profile.py`, 20 custom tests, 4 docs). Before the install, a full verified backup was made: `F:\Proving Grounds Backups\Project Proving Grounds_2026-11-07_193218`.
- New `upstream` branch: his files only, on the s181 import (6433bb3), as one commit (4a3dd32, 53 files: his 50 changes and 3 new files, `BUILD`, `maps/_inputs/h2.json`, `tools/release_notes.py`). The deletions were not recorded, because none of those files were his. A normal merge into main then applied only what he changed since s181; future updates merge the same way.
- His update (docs/UPDATES.md, s181 updates 3 to 8): call a bot into your vehicle with the horn; aircraft pick up bots; Halo 4 Mantis (walk, machine gun, stomp, rockets); Halo 4 Banshee bombs; H4 Theater with bots; Spire man cannons and aircraft landing (`AIR_ARRIVE_R`); vehicle crews during a blitz; DMR over AR; snipers never "low" with rounds left; magazine learning; Breakpoint bridge-to-ledge sight; and more.
- 16 files changed on both sides. 10 merged cleanly; 6 had 25 conflicting spots. Owner's rule: our changes win. Where a spot had a line we changed, ours was kept. Where his edit was to a line we left as base, or he added lines beside ours, his went in too:
  - kept ours only (his version dropped): our head and chest aim helpers over his `head_point`, keeping the protected Legendary/Demon head and turret precision (bot.py hunks 1-4 and 14); our turret origin over his `gun_origin` (8-10); our sniper-ammo and rocket-ready rules over his equivalents (6, 13); `core.py` fields; `maps.py` and `terrain.py` `set_open_under` (the same feature on both sides); `live.py` Reach `rounds()` and `spartan_head_position`.
  - ours plus his: his `learn_mags` call after our patrol weapon choice; his `veh_kind` beside our Scorpion settle (his Banshee bomb code reads it); his Mantis weapons call after our Scorpion fire; his aircraft `near` arrival inside our Mongoose arrival; his `nade_ok` grenade rule in our two fixed-high grenade gates; his blitz vehicle crews after our `power_runs`; his `alive + blitzing` vehicle orders with our patrols; his horn-picked bot and `HORN_CALL_R` with our `gunner_available` check.
- Native: the launcher loads the newest `native/bin/botcore*.dll`, and his installer's `botcore.dll` (his source, without our Demon tier and panel) had become newest. `native\build.bat demon` rebuilt `botcore_demon.dll` and `inject.exe` from the merged source (his h4f/film/overlay/shared changes and ours). The build had no errors; `panel_art.py` failed after it as before (PIL missing on PATH Python), which does not affect the DLL. `ppg_window.exe` is his build (we do not change `ppg_window.cpp`).
- Local data: the learned map files, `user/`, `tools/fixtures/` and all logs and bug reports are unchanged from the backup. Only his `maps/_shapes/*.json` and `unins000.dat` changed (his).
- Validation: all 211 regression tests pass on the merge, and the conflicted modules compile. Gameplay is untested, including his new features with our changes. MCC must load the new DLL: restart the launcher.

## 0.2.2-custom.7 — Demon awareness and fights, vehicle wall guard, 2026-11-07

- Covers the 21 commits since 0.2.2-custom.6 (989cb8d). 18 were already on GitHub without a version; 3 are new in this candidate: Codex's Reach Demon exposed-part fire (1f8e070), the ground vehicle wall guard (ed2b87f), and Legendary/Demon shooting back with the wedges body filter (1e0bd78). Each entry below gives its own behavior and validation.
- Demon gets radar heading reading and out-of-sight prediction, corner discipline, mending in cover, 180-degree vision, a 480°/s aim turn cap, fight commitment through short hunts and retreats, turning on radar flankers, line-of-sight cover, power-weapon runs only to reachable guns, rifles kept out until a hammer or sword can reach, Reach exposed head/chest fire, and answering a visible shooter. Legendary and Demon get more Jet Pack high-ground openings. Ground vehicles look ahead for walls. Also included: infantry patrol trios, the owner play profile tool (run automatically at match start), Headlong patrols and power positions, Reach rocket re-equipping, and `wedges.py` skipping fight scrums.
- Validation at the candidate: all 211 regression tests pass. Gameplay is untested for the three new commits, and for most of the Demon changes beyond what each entry records. The bot process must be restarted to pick them up.

### Legendary and Demon shoot back on the way to a gun or a seat; wedges skip fight scrums, 2026-11-07

- The owner's three Forge World bug reports (`logs/bug_reports/reach_forge_halo_20261107-180755`), from the trace:
  - "LilWraith didn't shoot back" (t 244): from t 222.8 to 230.8 he took a Demon's shield from 1.0 to 0.11 while it could see him. It went on to the gravity hammer it had been sent for, 2 u away, because the Demon power-weapon commit (2.95 + 0.2 kept) beat fighting him (1.76).
  - "OutlawMarine refused to shoot me" (t 568): under his fire at 10 u, cracked, it walked to a Warthog to fetch a plasma pistol (anti-vehicle errand, 2.4 over the fight's 1.72).
  - Underneath both: `hit_at`, which `decide` reads as `hit_recent`, was only set inside `fight`. A bot shot on its way to a gun or seat logged `hit: False`, so none of the under-fire exceptions held, including the fetch's own "busy" check.
  - "Stuttering to shoot back" (t 528): its DMR ran dry at 13 u, and the empty-magazine rule (switch up to 15 u) moved it to the assault rifle. The rifle holds fire past 11 u (reach 5 × 2.2), so it held fire for a second; the owner died at t 518.6. Earlier it had seen him at 16 u and gone for a gun 36 u away (the fetch's normal 1.85, unchanged).
- Across the whole match, decisions by Demons on foot within 2 s of taking damage, with a man in view aiming at them: 4,602, 18% a gun and 12% a vehicle. Fixed Legendary: 240, 36% a vehicle and 10% an item.
- `decide`: `hit_recent` also reads perception's `hurt_at`, set every tick. This applies to all tiers, so their existing under-fire rules (avoid, the power-weapon fallback, upgrades, fetch "busy", patrol) now also hold out of a fight.
- New `Bot.shoot_back`, fixed Legendary and Demon only (`profiles.fixed_high`; Scaling excluded). On foot, shot in the last 2 s, with a man in view within 40 u who is the known attacker or whose view is on it (0.25 rad): fighting him scores over every errand (item, vehicle, objective, hold, patrol) by 0.4. Retreats, regroups and hunts keep their scores, so a cracked bot still breaks to cover. The fight also skips a crew order's walk to a vehicle. Not shot, the Demon still takes the gun it was sent for.
- `choose_weapon` (all tiers): an empty magazine mid-fight switches only to a gun that fires at that range (`reach × OUT_OF_REACH`); otherwise it reloads.
- `tools/wedges.py` leaves out a spot when half its samples or more had another player or vehicle within 3 u, not counting the driver's own gunner (within 1.6 u of its vehicle). Correction to the previous entry's hand filtering: my classifier read world-row column 14 (the enemy in sights) as the player's vehicle. Every gunner counted as a body block, and many scenery spots were wrongly dropped. Rerun with the fix: Headlong has 8 spots (648 cells; one dropped because it cut a pad-to-pad drive), and Boneyard adds 11, merged into the saved spots (the 15:34 Boneyard trace those came from has since left `logs/`). Pad-to-pad drives: 8/8 and 138/138 still arrive. These are local, gitignored map files.
- Validation: `tools/test_shoot_back.py` adds 10 tests on Headlong's map (shot Demon fights; not shot it still takes the gun; a man looking away is not the shooter; Legendary yes; Heroic, Normal, Easy and Scaling no; regroup, seat and retreat-to-cover kept; the hit flag out of a fight; the rifle swap at 8 u but not 13 u). `tools/test_wedges_bodies.py` adds 4 (scenery, a vehicle scrum, own gunner, mixed). All 211 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Ground vehicles look ahead for walls, 2026-11-07

- The owner reported bots driving straight into walls. I scanned 4 recent traces (Boneyard ×2, Headlong, Invasion; about 80 driving minutes, mostly Ghosts) and found 81 crashes: 31 into scenery and 50 near another player or vehicle. Of the 31 scenery crashes, 18 came while following a route, 4 each during splatters and aiming, 3 during the 1.5 s run straight on after a ram, and 2 during evasions. 18 of the 31 were off the vehicle's drivable ground, beside a wall. These maps have no recorded LiDAR drives, so recorded drives were not involved. Drivers also wedged 166 times, for about 535 s in total, mostly 2–4 s each.
- New `Bot.ground_guard` runs after `drive` for every ground and hover driver, at all difficulties. Using the new `Terrain.drive_clear`, it looks 2–6 u ahead (0.6 s at the current speed) on the floor it drives, following the nav's own step rule so ramps and drops stay open. It looks both where it steers and where it is sliding. If a wall is ahead and the heading is the steering, it turns to the nearest open heading (up to 80°) and holds that side for 1 s. On a trip, a wall beyond the next waypoint only slows it. If the heading is the gun's ("aim"/"spin"/"scan"), the aim is left alone: forward into the wall is dropped and a hover's strafe flips. Within 0.5 s of contact the throttle eases with the time left, down to 0.35, and boost is dropped. Splatter and charge look only as far as their target.
- Not fixed: the guard cannot see obstacles missing from the map data. 8 of the 30 replayed scenery crashes include the Boneyard hotspot near (304, 95), hit 3 times, and the probe read it as open until contact. `tools/wedges.py` can learn such spots; it has not been run for these maps. I also tried a stricter route look-ahead (shortcuts kept on the vehicle ground). It changed almost nothing in replay, so I reverted it.
- Validation: `tools/test_ground_guard.py` adds 14 tests (11 on a fake wall; 3 on the real Boneyard terrain, skipped without its map data). All 197 regression tests pass. In an open-loop replay of every fast driver row in the 4 traces through the real guard and terrain, it acted before 22 of 30 scenery crashes, most 0.4–0.9 s early. It kept 94–95% of throttle over fast driving and steered on 6–10% of fast rows; open loop overstates this, because the vehicle never responds. Each call costs about 0.05 ms (p99 0.3 ms). Gameplay is untested. The bot process must be restarted.

### Reach Demon fires at the exposed part, 2026-11-07

- Reach Demon checks head and chest separately for ordinary handheld fire against an on-foot enemy. The DMR, sniper and other non-AR guns in this path prefer the head. The AR prefers the chest. Either can use the other part if it has a clear shot. The live head point, when available, is shared by sight, the shot check and aim. A generic height-based shot check can no longer veto a clear ray to the selected part.
- The final DMR and sniper command corrects to the selected point. Weapon cadence, sniper alignment, solid cover, bulletproof materials and vehicle obstruction still apply. An automatic burst stops on lost sight or when Armor Lock or another ability protects the target. The trace records the chosen part and whether its shot line was clear.
- In an offline replay of the Boneyard match at 80.539 s, the recorded positions gave Demon a clear chest ray and a covered head. The previous Demon held fire and the new Demon requested a chest shot. The replay uses recorded positions and stance heights. Nine new tests and all 183 regression tests passed. Live gameplay still needs a check after the next bot-process launch.

### Friend's clip review: Demon keeps its opponent through hunts and retreats; Powerhouse railing trap, 2026-11-07

- The owner's friend reviewed the owner's Powerhouse clips and proposed four fixes (Powerhouse is reach_30_settlement). Each was checked against logs/trace_reach_30_settlement_20261107-134849, -135726 and -140335 before any change.
- Turning toward incoming fire and then pausing was not supported. A Demon's first press came 0.20 s (median, 76 fights) after a fight that followed a hunt (a turn on a shooter or a dot), against 0.30 s for other fight starts (404); the wait is the DMR cadence, a blocked line, or the aim swinging on. Unchanged.
- Bouncing between opponents: new `Bot.carried_target` (Demon only) keeps the last man it fought through a hunt or retreat while he lives and was seen within COMMIT_S (6 s, the fight's reacquisition window). `pick_target` treats him as the current target, so `demon_commit` holds him and the existing switches still apply (the shooter now, a man at arm's length, one close and aiming at it, 2x threat). The retreat's covering fire aims at him while he is in sight.
- A tracker contact closing from behind during a pickup is already covered by 04af23a (a fresh dot out to 12 u turns a Demon with its shield holding, over a pickup's 2.95).
- Bots stuck on the second floor near (123, 229, 41.6): up to 142 s, with thousands of "wall ahead" and "unstuck wiggle" notes; the nav's next step was (123, 230) on the way to the rockets at (119, 230, 38) or the gravity hammer at (131, 248). From the railing the nav stepped 1.3 u down onto a ledge (z 40.1) through the railing, which nobody has walked (the owner's LiDAR variant shows people on that ledge and two drops from it to the floor, never a step onto it from the upper floor). From anywhere inward, routes already used the real way down at the west end, (119, 229) -> (120, 233). The 46 ledge cells reached only over the railing are now a painted block layer in maps/reach_30_settlement/paint.json (a wall-sized cost, as the Paint tool's blocks). It is local data, gitignored like the LiDAR files, and not committed. From the stuck spot, the route to the rockets now takes the real way down (12.2 u, no railing step), the hammer stays reachable, and all 30 tested spawns reach both.
- Validation: 7 new carried-target tests; all 174 regression tests pass; the route checks above on the real map data. Gameplay is untested; takes effect on the next match.

### Demon turns on radar flankers and does not turn its back on a man on it, 2026-11-07

- Owner's clips and bug report from Powerhouse (logs/trace_reach_30_settlement_20261107-135726 and -140335; F9 at 227.5 s, "Bot decided to never shoot at me"). At the report, Slayer7 was killing HeadshotTV in front of it (6 DMR rounds, on target 103 of 140 ticks) while the owner stood 11–12 u away, 88–108° off its aim, outside its 180° vision, on its tracker and not shooting. Across both games the owner killed Demons 21 times. In 11 of them the Demon knew him by a tracker dot under 1 s old through its last 3 s, and 6 of those never turned on him (an item, a retreat, another man). Several died retreating with him 5–9 u behind (Slayer7 at 49 and 152 s, Havoc94 at 40 s).
- Demon only: the close-dot check in `decide` (turn on a fresh tracker dot or an unseen hit, as a hunt with the existing `turn_ok` and `finishing` guards) reaches out to 12 u, against 3.5 u before, while Demon's shield is at least half (always without shields). Cracked, it stays at arm's length.
- New `Bot.stand_ground` (Demon only): with an enemy within 6 u, in sight or on the tracker in the last 0.6 s, retreats to cover farther than 2.5 u are dropped. The close-fight rule fights a man in sight; one only on the tracker gets a turn (a hunt at his dot, 3.2). Not with the objective, not in a vehicle. The stuck-in-a-room clip has no bug report, so its spot is not identified yet.
- Validation: 5 new tests (a decision on the real Headlong map turns on a 9 u dot; Legendary and a cracked Demon do not; far cover is dropped and near cover kept with a man at 4 u; a tracker-only chaser is faced; a man 8 u off, or Legendary, keeps the retreat). All 165 regression tests pass. Gameplay is untested; takes effect on the next match.

### Reach bots ready loaded rockets after a close fight, 2026-11-07

- In the Powerhouse match, OutlawMarine switched from rockets to the DMR after a radar contact at about 3.9 units and carried both loaded rockets for the rest of that life. In `brain/bot.py`, Reach bots from Normal upward can switch to a loaded launcher as soon as it scores above the current gun between fights or against a target outside the close splash penalty and within rocket range. The swap cooldown and close splash and friendly-fire checks still apply.
- Added two regression checks in `tools/test_reach_loadout.py` for re-equipping rockets when a close radar contact ages out and selecting a loaded launcher in range. All 160 tests passed. Live gameplay is pending the next bot-process launch.

### Demon keeps its rifle out until a hammer or sword can reach, 2026-11-07

- Owner's two Powerhouse games after the weapon-run fix (logs/trace_reach_30_settlement_20261107-135726 and -140335; reach_30_settlement is Powerhouse): Demons picked up 6–7 power weapons per game and held one 5.8–10.5% of the time, against 0.7–1.4% before, but got 1 kill with one in 65. Their item trips rose to 23% of their time and the team K/D fell from 50–29 to 38–43 and 50–40. In fights, the gravity hammer (5 of 13 pickups) was out for 216 ticks at a median 6 u with no swing. Rockets were in hand for about 3 s of fighting, fired 3 times, and were put away on an empty magazine. The focus rifle fired normally (172 presses in 475 fight ticks).
- Cause: `choose_weapon` adds +2.5 for a sword or hammer whenever the man is within 6 u (to draw it) or 8 u (to keep it), based on human sword fights. At 6 u the hammer scored about 6.1 against the DMR's 5.5, so a Demon walked around with it out at rifle range.
- Demon only: the blade bonus applies inside 3 u (to draw) and 4.5 u (to keep), so at range the DMR fights and the hammer or sword comes out for the man nearly in reach. Legendary and the other tiers keep the old blade rule.
- Validation: 3 new tests (Demon hammer at 6 u switches to the DMR; the DMR at 2 u draws the hammer or sword; kept at 4 u; Legendary unchanged). All 158 regression tests pass. Gameplay is untested; it takes effect on the next match.

### More Jet Pack high-ground openings for Legendary and Demon, 2026-11-07

- In `brain/equipment.py`, fixed Legendary and Demon can boost for a high-ground shot when the enemy is more than 4 world units away and aiming about 20 degrees or more off the bot. The previous thresholds were more than 6 units and about 29 degrees. The move still requires more than half shields, at least 90% Jet Pack charge, and a clear flight to a perch with sight of the target.
- All 155 regression tests passed. Focused checks covered both new openings, Heroic and Scaling, direct enemy aim, shield and flag restrictions, and the failed-search cooldown. Live gameplay is pending the next bot-process launch.

### Demon power-weapon runs: reachable guns only, commit when close, 2026-11-07

- Diagnosis from the all-Demon Headlong 8v8 (logs/trace_reach_cex_headlong_20261107-032305, before the ramp and lift fixes): of 282 Demon weapon assignments, 25 (8%) ended holding the gun. A median assignment spanned 10 s, 7 s of it actually heading for the gun. Of 253 run trips, 107 ended for a fight, 57 for a hunt and 48 for an objective. Of 156 times a Demon came within 3 u of its gun without taking it, 83 were 2+ u below or above it: 52 under the sword (reachable only by the air lifts and man cannon, now recorded) and 20 under rockets at (1.4, -24.8, 8.1) that no spawn reaches even now (the map loader marks them unreachable). Boneyard: 49 trips, 3 guns. The two Settlement games: 26 trips, none.
- `Director.fetch_reachable`: fixed Legendary and Demon fetchers are sent only to a gun the nav reaches from where they stand, with people's jumps and rides included (as bots that jump walk). An unreachable gun falls to the next eligible fetcher who can reach it. Without terrain (a bare test director) there is no check. Other tiers keep the existing rules.
- `Bot.decide`: a Demon within 10 u flat (and 2 u up or down) of the gun it was sent for scores the run 2.95. That is over a new fight in view (about 1.9), a committed fight (2.6 + 0.3 aggression) and a mend (2.9). A man inside the close-fight range and a turn on an unseen shooter or a dot at arm's length still win. Farther away the run keeps its previous score.
- Not addressed yet: 73 same-floor near misses at Headlong and 33 at Boneyard, where the Demon reached the gun but did not take it (the pickup presses within 1.2 u, holding the gun to swap out). These wait for a match after the ramp and lift fixes.
- Validation: 6 new tests in tools/test_legendary_power_fetch.py, including decisions on the real Headlong map (gun 6 u away: the gun over a man in view; 20 u away, or Legendary: the fight). The real Headlong guns check as expected: the unreachable rockets from 0 of 59 spawns, the sword and the west rockets from 59 of 59. All 155 regression tests pass. Gameplay is untested; the bot process must be restarted.

### Demon line-of-sight cover, 2026-11-07

- Cover was only LiDAR-painted spots (`cover_from`). In normal matches, base Boneyard, Launch Station and Headlong have none: the owner's LiDAR runs were filed under map variants. On those maps the losing-fight, after-fight recharge, regroup, relocate and power-weapon cover rules never found cover. For Demon only, `cover_from` now falls back to `los_cover` when no painted spot qualifies: the nearest spot within 10 u, a short walk away, that breaks every threat's line of sight (`hidden_spot`). The result is kept 0.5 s for the same place and threats. Other tiers keep painted cover only.
- `hidden_spot`, also used by the after-kill mend, now checks that the walk's actual end point, up to 1 u from the candidate, is hidden too. Before, some returned spots were still in view.
- Validation: on 60 random spawn and threat pairs per map, cover was found 59/60 (Boneyard), 60/60 (Launch Station) and 60/60 (Headlong), all hidden from the threat, about 1.4 u away (median), in 0.4–1.9 ms (median) and at most 21 ms. 4 new tests; all 149 regression tests pass. Gameplay is untested; the bot process must be restarted.

### Owner play profile runs automatically, 2026-11-07

- tools/play.py `match_trace` (each recorded match start, after the carnage report copy and the rotation) now starts `tools/owner_profile.py --background`. It is a separate, below-normal-priority, windowless process, logging to logs/owner_profile/last_run.txt. The last match is summarized while its recording is still on disk; the rotation reaches it only 4 matches later (5 games kept by default). Profiles are rewritten each time. Any failure to start is ignored so a match always starts, and only the install's own logs/ folder triggers it.
- The tool runs one background run at a time: a lock in logs/owner_profile/, released at the end, and treated as stale after 20 minutes. Matches that aren't the owner's (bots only, no person or several, no world rows, unreadable, analysis failed) are kept as skip markers, so later runs don't read them again; a file that changes is read again. Errors are logged, not raised.
- Validation: lock, stale-lock and skip-marker tests in tools/test_owner_profile.py. The hook returns immediately. All 145 regression tests and the tools/recording.py self-check pass. Takes effect the next time the launcher starts a match.

### Owner play profile tool, 2026-11-07

- New tools/owner_profile.py ("play like the owner") reads the owner's recorded matches (logs/trace_*.jsonl with their carnage reports). Matches where the owner got fewer than `--min-kills` kills (default 1) are skipped as spectating, and so are matches with no carnage report, no person, or more than one person. Per map it writes maps/<map>/owner_profile.json with:
  - spots: where he got his kills, clustered within 3.5 u, with kills, deaths, time there, visits, typical visit length, shot distance, and height over his victims
  - engagements: distance, height advantage, what the victim was aiming at, who had whom in sights first, time to kill
  - fights: won, lost and broken off, and the health and shield he started them at
  - disengage: the health and shield at which he backed out of fights he was losing
- Measures match the fight reports used in the Settlement analyses: head or chest counts as in sights, a target is held through 0.5 s gaps, kills are attributed to the enemy with the victim in sights (approximate), and K/D comes from the game's report.
- Recordings rotate (tools/recording.py keeps the newest 5 unsaved matches by default). So each match the tool reads is also kept as a summary in logs/owner_profile/ (about 20 KB each; rotation never touches it), and profiles keep a match after its recording is deleted. The owner's 35–15 and 30–12 Settlement recordings had already rotated out before the first run. The first run kept 10 matches on 5 maps; one 0-kill Settlement match was skipped as spectating.
- The generated owner_profile.json files and summaries come from the owner's recordings and are local, not committed. Nothing in the brain reads them yet; the anchor role will.
- Validation: tools/test_owner_profile.py (a constructed kill from a ledge, profile fields, spot clustering) and all 143 regression tests pass.

### Demon aim turn cap, 2026-11-07

- Lower Demon's general aim turn cap from 1,000 to 480 degrees per second in `brain/profiles.py` for all personalities, including Warthog gunner aim. Reach Scorpion drivers still use the dedicated 90-degree-per-second cap. Protected final DMR and sniper head-shot corrections still apply on the firing tick.
- All 140 regression tests passed. The profile test checks the new cap and compares the other numeric settings with the prior profile. A focused check confirmed the general and Scorpion turn limits for Demon and Legendary across all personalities. Gameplay testing is pending the next bot-process launch.

### Demon fight commitment, 2026-11-07

- From the owner's Settlement 3v3v3v3 (logs/trace_reach_30_settlement_20261107-041239, owner 35-15 against a three-Demon team): the owner won 58% of his fights (an enemy in his sights for 0.5 s or more) and broke off 27%. The Demons won 34–42% and broke off 40–48%, with the same 1.1–1.3 s time to kill. Of the Demons' break-offs, about a third switched to another enemy, about a third were the target leaving sight briefly or the aim moving to another man, and 13–23% went to cover with the target still in view.
- `Bot.demon_commit` (Demon only, from `pick_target`):
  - A target that left sight stays the target for 0.8 seconds, or 1.6 seconds when its estimated shield is at or below half, and Demon chases it through the existing chase and corner logic.
  - A visible target is kept for 2 seconds after it is taken on. After that, a new enemy must pose 2x its threat (rising as the kill nears) to take over, against 1.25x for the other tiers.
  - Demon still turns at once on the enemy shooting it now (`shot_by_other`), an enemy at arm's length, or an enemy within 10 units aiming at it while the current target is looking away. A kill about to land (`finishing`) still goes first.
- Mending after a won fight waits while an enemy is in view and Demon's shield is at least 0.5: it fights first, and the mend stays owed until no enemy is in view or the shield drops below half. Mending still takes priority when cracked.
- Legendary and the other tiers keep their targeting rules.
- Validation: 6 new tests in tools/test_demon_anticipate.py. The full suite (140 tests) and the compile check (94 sources) pass. This install has no match simulator, so gameplay is the test; the bot process must be restarted.

### Infantry patrol trios, 2026-11-07

- In `brain/director.py`, roll once per new infantry patrol. Half of assignments send one Spartan and half try to send up to three to the same waypoint. If fewer than three qualify, send the eligible Spartans. Applies to maps with infantry patrols, including Boneyard and Headlong, outside Invasion.
- All 134 regression tests passed. A focused director check covered both outcomes, the three-bot cap, smaller groups when eligibility is limited, and independent arrivals. Gameplay testing is pending a bot-process restart.

### Headlong Red side ramp, lifts, man cannon and the ledge power position, 2026-11-07

- Owner report 3's ledge (-10.01, -9.37, 10.36), the east end of the Red side sniper floor over Mid, was reachable only from that floor's own spawns. In the 03:23 match the owner walked a ramp from the middle level (z 7.6) up to it; the level data's 0.1 u height steps read as 0.2 u rises per 0.25 u nav cell, over MAX_RISE 0.18, so the ramp had no link. New maps/reach_cex_headlong/moves_review.json (the existing reviewed-floor mechanism) approves that walk as floor at the owner's recorded foot heights every 0.1 u. Walking alone, the ledge is now reachable from 582 of 584 spawns. Ramp cells shifted up 0.1–0.2 to the walked heights, and no power position or patrol spot lost reach.
- The owner's LiDAR session (variant reach_cex_headlong@v2e9a3603) recorded his rides on the two air lifts and the man cannon, which lands on the same sniper floor. His three bug reports from that session point at these. Normal Headlong matches load the base map, so the three rides were copied into the base map's local, gitignored maps/reach_cex_headlong/lidar.json. A backup of that file is in logs/. With the rides, the ledge is reachable from all 584 spawns, and each lift top and the cannon landing is reachable from below. Bots that jump at all (everyone but Easy) plan with people's rides. The lidar.json change is local data and is not committed.
- The ledge is added as an owner power position (score 1.0, 6.5 u above its surroundings, duck cover) with `power_positions.py --add`.
- Validation: reachability checks above; all 134 regression tests pass. Gameplay is untested; the bot process must be restarted.

### Headlong patrol areas and owner power positions from bug reports, 2026-11-07

- The owner's six F9 reports from the Headlong 8v8 (logs/bug_reports/reach_cex_headlong_20261107-032305) mark spots where the owner stood. New maps/reach_cex_headlong/infantry_patrols.json lists the four patrol requests (reports 1, 4, 5 and 6: north spawn, southwest lower level, west spawn, man cannon), shared by both teams. Patrol orders, timers and the Invasion exclusion are the existing rules.
- Power positions: reports 2 (13.55, 17.84) and 6 (man cannon, 7.92, -2.7) are added to Headlong's positions.json with `owner: true` and score 1.0, above every computed spot, so the Slayer anchor's weighted post pick favors them. Report 3, the ledge at (-10.01, -9.37, 10.36), is not added: the level's nav reaches it only from the 3 spawns on that ledge (none of the other 37 tested), even with jump links, so an anchor sent there would stall. It waits on the owner describing the way up.
- tools/power_positions.py gains `--add X,Y,Z` (one map) to write an owner-marked row, measured like the computed spots (sightlines, height, duck spot). A later full regeneration keeps owner rows and drops computed spots within half the spacing of them.
- Validation: the map loads 4 patrol points and 10 positions with the owner's first. The patrol points (reports 1, 4, 5, 6) and the two power positions are reachable from all 40 tested slayer spawns. The owner-row merge was checked. All 134 regression tests pass, and the compile check passes. Gameplay is untested; the bot process must be restarted.

### Demon 180-degree horizontal vision, 2026-11-07

- Widen Demon's visual detection from 140 to 180 degrees (90 degrees to either side) in `brain/bot.py`. The entire cone uses Demon's zero configured recognition delay. The ordinary sight range, line-of-sight checks and other difficulties retain their existing rules.
- Validation: updated `tools/test_demon_awareness.py` to check both edges of the wider cone, including zero delay inside and no visual detection just outside. All 134 regression tests passed across the suite and the localhost-only rerun. Syntax and whitespace checks passed. Live gameplay is untested; the change takes effect on the next bot-process launch.

### Demon mends in cover after winning a fight, 2026-11-07

- Owner's request: once Demon wins a fight with any shield or health lost, it goes to cover until both are back. A win means the target died within one second of Demon's last shot. Demon uses painted cover from the remaining known threats (or from the kill spot when none are known). Without painted cover, it searches up to 10 units for the nearest walkable spot, a short walk away, that no threat can see. At the spot it crouches, which keeps it off the enemy's motion tracker, and watches out of cover.
- Mending (score 2.9; 3.1 while already under way) outranks objectives, weapon pickups, hunts and a newly visible enemy at range; Demon fires back while moving. It still loses to an enemy within the close-fight range, a hit from an unseen shooter, and a tracker dot at arm's length. A teammate on a loose objective (`stay_on`) and the flag-grab reduction keep their rules. Demon stops mending when its shield is full and its health is full or has stopped refilling for 1.5 seconds (Reach health refills only partially), when the enemy carries our flag or objective, or after 15 seconds at most. A new hiding spot is chosen if a visible enemy can see the current one. Excluded: carriers, vehicles, matches without shields and Race. Other tiers are unchanged.
- Validation: 4 new tests (won-fight mend and end, stalled health, no mend at full or for Legendary, the cap). The full suite (134 tests) and the compile check pass. On Forge World, a hiding spot was found for 35 of 40 random positions, in under 1 ms (median) and at most 18 ms, once per kill. Gameplay is untested; the bot process must be restarted.

### Demon corner follow-up from the first live match, 2026-11-07

- Owner's Reach Forge World 1v1 Slayer against one Demon (logs/trace_reach_forge_halo_20261107-022003.jsonl). Of 28 breaks of line of sight during fights, Demon held 4 (2 continued to a swing and then a push) and pushed 24, mostly targets 10 or more units away or cracked targets. Its 291 hunt destinations were within 0.5 units of the owner's true position, because they came from live tracker dots.
- **Shield recharge estimate.** Demon judges a target's shield by its value when last seen plus the recharge since. Demon learns this match's recharge delay and rate from its own shield (defaults 2.0 seconds and 0.5 shield per second, measured in that match), and a hit seen on the target restarts his clock. A target pushed while cracked becomes a hold once his estimated shield is back. Fixes the push at 480 seconds, which was triggered by a half-shield sighting although the shield was full one second later.
- **Close-corner fallback.** When no reappearance spot is found (Demon is already at the corner), it holds back from its estimate of the target's position instead of pushing. This was the likely cause of the push at 484 seconds against a full-shield target 4.5 units away.
- **Ledge hold.** If the target is at least 1 unit higher with no short walkable way up, Demon holds whatever the target's shield, then resumes the chase via the nav without a swing. Fixes the 3-second strafe into a platform wall below the owner (1.9 units up) at 480–483 seconds.
- Recharge retreats were checked in the same match: Demon left cover at 0.94–0.95 shield, as designed (the 95% threshold). Shields began refilling 2.0 seconds after the last hit and filled from empty in 1.9 seconds, so a recharge retreat lasted about 3–4 seconds. Some retreat goals at full shields while the owner was dead have an unidentified cause, because the trace does not record decision scores. Unchanged.
- Validation: 5 new tests in tools/test_demon_anticipate.py (19 in total). The full suite (130 tests) and the compile check (94 sources) pass. Gameplay is untested; the bot process must be restarted.

### Demon radar reads, out-of-sight prediction and corner discipline, 2026-11-07

- **Radar reads (Demon only).** Demon now works out which way each motion-tracker dot is moving by comparing its successive positions. A dot older than 0.5 seconds starts a new heading. Unsuppressed fire puts the shooter on Demon's tracker even when crouched or standing still, within the existing tracker range, the tracker setting and jamming. A crouch-walking enemy who isn't firing stays off the tracker. Other tiers keep heading-less dots and the existing radar and heard-gunfire rules.
- **Out-of-sight prediction (Demon only).** The new `brain/anticipate.py` estimates where an unseen enemy has reached since his last trace. Candidates are: continuing along his last heading on the walkable path, nearby painted cover hidden from the bot, or staying put. A tracker dot that disappears more than 3 units inside tracker range is read as the enemy crouching or stopping, so the guess stays near the last dot. The prediction uses only the last trace, its heading and the map, never the live position. It feeds Demon's main hunt destination and its out-of-sight pre-aim (`man_appears`). Damage-direction hunts, other tiers and Demon's fight aim are unchanged, including the protected head corrections. Only h2_warlock and h2a_ca_ascension currently have painted cover; on other maps, prediction uses heading and staying put only.
- **Corner discipline (Demon only).** When a fight target breaks line of sight within 10 units with more than half his shields when last seen, Demon no longer chases him round the corner. It holds a standoff at least 5 units from where he would reappear for a random 1.2–2.8 seconds. It then swings wide, offset 3.5 units to the side of the corner, for up to 2 seconds before resuming the chase. The existing flush-grenade roll still applies. Demon pushes immediately when the target was cracked, carries the flag or objective, is fleeing on the tracker, is out of range of the rule, or when Demon holds a sword or hammer or is in a vehicle. CTF defender holds and the sniper lane-hold keep their previous rules.
- Validation: tools/test_demon_anticipate.py adds 14 tests (radar heading, crouched shooters, prediction cases, Demon-only gating, hold/swing/push choices, backing off, varied hold length). The full regression suite (125 tests) and the compile check (94 sources) pass. On real map data (Breakpoint, Warlock, Ascension), a prediction takes about 2 ms (median), at most 7 ms, and is cached for 0.4 seconds per trace. Gameplay is untested; the bot process must be restarted.

## 0.2.2-custom.6 — Reach vehicle aim and Boneyard patrols, 2026-11-07

- Correct the Reach Warthog chaingun’s horizontal firing origin. For fixed Legendary and Demon, limit Scorpion turret turns to 90 degrees per second, require aim to settle before firing, and aim the main cannon at infantry chests.
- Add two shared Boneyard infantry patrol spots and one per team outside Invasion. A new patrol has a 50% chance to request a second eligible bot. Bots can return fire at distant visible enemies while continuing toward their waypoint.
- All 111 regression tests passed. The owner confirmed the Warthog aim and Scorpion turn changes in gameplay and reported that chest aim appeared to fix shots at infantry feet. The cannon settling check and Boneyard patrols were verified offline.

### Boneyard team patrol spots, 2026-11-07

- Add the two reported infantry patrol waypoints, one for Red and one for Blue. Restrictions follow team color, including when spawn sides swap. The original two Boneyard patrol spots are available to both teams. Patrols apply outside Invasion.
- Verified routes from nearby spawns on the reported Boneyard variant. Offline checks confirmed each team selects only its own restricted spot and that the restriction follows color when sides swap. All 41 selected regression tests passed. Live testing requires a bot process restart.

### Boneyard patrol return fire, 2026-11-07

- Patrollers use normal aiming, weapon selection, and firing checks against visible enemies while walking toward their waypoint. Taking a hit from range can leave the patrol active when a target is visible. Close threats, incoming fire with no visible target, and retreats can still interrupt the trip.
- Offline checks confirmed a bot could take a hit, fire at a distant target, and keep its movement pointed toward the patrol waypoint. Also checked close threats and unseen incoming fire. All 50 selected regression tests passed. Live testing requires a bot process restart.

### Boneyard patrol pairs and combat interruptions, 2026-11-07

- Roll once per new team patrol on Boneyard. Half of assignments request a second eligible bot for the same destination. Each patroller can finish independently, so the first arrival does not cancel the second bot's trip.
- Give each assignment up to 40 seconds. Patrollers favor moving past enemies they see at 18 world units or farther, with normal combat priority when an enemy is closer, they are hit, or they need to retreat.
- Offline checks covered both group sizes, the single-bot fallback, independent arrivals, distant and nearby contacts, recent damage, and Invasion exclusion. All 41 selected regression tests passed. Live gameplay is pending a bot process restart.

### Boneyard infantry patrols, 2026-11-07

- Add the reported Banshee Building and west upper level positions as infantry patrol destinations on Boneyard outside Invasion. One available bot per team can visit a reachable spot that teammates have not visited recently. Combat, retreat, and dedicated team assignments take priority. Patrols end on arrival or after 25 seconds.
- Verified walking routes from nearby spawns on the reported Boneyard variant and checked patrol selection, rotation, reassignment to defense, and Invasion exclusion offline. All 41 selected regression tests passed. Live gameplay testing is pending a bot process restart.

### Reach Scorpion chest aim, 2026-11-07

- Fixed Legendary and Demon Scorpion drivers aim the main cannon at the chest of standing and crouched infantry instead of applying the normal splash weapon aim at the feet. Vehicle targets, other weapons, and Scaling keep their existing aim. The Scorpion's turn cap and firing alignment checks still apply.
- Offline driver checks confirmed both chest heights and the existing aim for vehicle targets, Scaling and the Wraith. All 42 selected regression tests passed. The owner tested the change in gameplay and reported that it appeared to fix the Scorpion aiming at infantry feet.

### Reach Warthog gunner alignment and Scorpion turning, 2026-11-07

- Aim the Reach Warthog chaingun from the attached turret's horizontal position, rotated into map coordinates, with the existing calibrated firing height. Keep the chassis position for navigation and perception. Fall back to the existing origin when attachment data is unavailable or invalid.
- Boneyard's second report requested the owner's Scorpion turning speed for Legendary and Demon. Cap Reach's fixed Legendary and Demon Scorpion drivers at 90 degrees per second, based on the recorded sustained yaw rate (90.3 degrees per second at the 90th percentile of moving samples). Require 0.10 seconds of continuous aim alignment before requesting cannon fire, including at close range. The game reader does not expose the live barrel direction, so this is a settling check on view readback and aim commands.
- Offline driver checks confirmed the turn cap, firing after settling, resetting when the target moves out of alignment, and Scaling exclusion. Attachment transform and fallback checks passed, and all 92 Python source files compiled. The suite passed 110 of 111 tests; the sandbox denied the LiDAR localhost connection in the remaining test.
- The owner confirmed in gameplay that the Warthog aim correction and Scorpion turning sensitivity worked. The confirmation did not separately measure cannon timing.

## 0.2.2-custom.5 — Mongoose transport source update, 2026-11-06

- Publish the owner's approved five Mongoose fixes from 1b59ccd. Ordinary Mongoose becomes transport-only, with finite destinations, cancellation of empty/invalid jobs, bounded carrier/getaway waits, automatic ride cooldown, and retained evasions/recovery/forward splatters. Chosen defaults and full validation are recorded in the implementation entry below.
- Include the main-AI review handoff from 4c0fc95 and add a post-baseline Mongoose follow-up note so its 0.2.2-custom.4 review baseline remains explicit. All prior collaborator and owner commits retain their identities.
- Validation: 111 regression tests passed and 92 Python sources compiled for the implementation, followed by passing targeted checks after final cleanup. Release preparation changes documentation/version only; whitespace checks pass. Gameplay still needs a bot-process restart and live confirmation.
- The owner requested this normal source push to IEatOreos/ProvingGroundsOreo main. Machine settings, learned maps, fixtures, logs and installed binaries remain local. No installer, tag or GitHub Release is included.

## Unreleased — Finite Mongoose transport trips, 2026-11-06

- Apply the owner's five approved Mongoose changes. Remove ordinary Mongoose from the harasser role, require a useful distant destination for director-assigned transport, preserve the destination when assigning a driver, and exclude Mongoose from persistent crew-patrol arrival behavior. Completed trips request dismount and continue on foot.
- Give ordinary Mongoose drivers explicit finite taxi, carrier-pickup and CTF-getaway jobs. Remember the carrier across role passes, stop for boarding, carry a boarded carrier home, and cancel invalid/dead/dropped/carried-away targets. Keep only one getaway vehicle per team. Reassess getaway objective changes and carrier death.
- Chosen defaults: 8 seconds waiting beside a carrier, 20 seconds parked for a getaway, 30 seconds of automatic ride cooldown after dismount, and a travel deadline of max(60 seconds, initial straight-line distance / 3 + 30 seconds). Reassigned moving destinations cannot restart that deadline. Race checkpoints remain the continuous riding case.
- Keep emergency evasions, reversing/stuck recovery and opportunistic splatters. Ordinary Mongoose taxi trips can splatter eligible infantry within 18 units and 20 degrees ahead rather than detouring into a chase. Shared vehicle logic keeps its existing behavior for other chassis, including armed Gungoose and Warthog crew patrols. Use the existing per-game exit hold/retry mechanism and add Mongoose completion reasons to bot notes.
- Files: brain/vehicles.py, brain/director.py, brain/bot.py, tools/test_mongoose_transport.py and current customization notes. No native rebuild is needed. This changes ordinary Mongoose behavior across supported games through the shared brain.
- Validation: all 111 regression tests pass, including 16 new tests through real director/driver entry points covering arrival, no-purpose dismount, cooldown, finite moving-target deadlines, pickup/home delivery, wait cancellation, getaway approach, race, splatters, evasion, reversing, and Warthog patrol preservation. All 92 Python sources compile in memory and whitespace checks pass. The existing LiDAR localhost endpoint test requires socket access and passed on the full run. Gameplay remains untested; restart the bot process/launcher to apply.

## Local documentation — main AI review handoff, 2026-11-06

- Add docs/AI_REVIEW_HANDOFF_2026-11-06.md describing the combined published code through 9a4cf17 / 0.2.2-custom.4. Organize by Reach, Halo 4, other game scope, brain/difficulty, weapons/ammo, equipment/maps, director/vehicles, LiDAR, native menu/reporting, and upstream integration.
- Include the complete 27-commit ledger, current values and superseded settings, file/function/test map, repository access and runtime setup, test command, release validation evidence, and unresolved proposals. Distinguish retained upstream behavior, custom changes, owner confirmation, offline checks, and unverified gameplay.
- Validation: all listed commits match the published history, linked local references and named source/test files exist, and the embedded Python test snippet compiles. Documentation only. This handoff is prepared locally for the owner to share.

## 0.2.2-custom.4 — source update, 2026-11-06

- Publish the approved recent bot updates: independent Demon difficulty and restored Legendary attributes with protected head/turret precision (6a31238); Legendary zero overshoot, Demon 140-degree zero-edge-delay vision and deterministic eligible radar, and resource-call priorities (f022024, bfbb62d). Power calls rank Demon → Legendary → Heroic/Scaling → Normal; gunner calls tie Legendary/Heroic/Scaling, and reserve Demon's power jobs before new gunner assignments.
- Include teammate-coordination workflow documentation (dde7dcc) and the collaborator's LiDAR vehicle-path recording/view support (a57893f), both approved for this combined push. Preserve all existing commit identities. The fetched GitHub main is an ancestor; no incoming merge is needed. Machine settings, learned-map data and fixtures remain excluded.
- Validation: all 95 tests pass with local fixtures; the isolated committed-source snapshot passes 92 with 3 fixture-dependent skips. All 91 brain/tools Python sources and the LiDAR viewer JavaScript pass syntax checks; Git whitespace checks pass. Gameplay remains untested for these changes; restart the bot process/launcher to apply. No new Warthog missed-shot fix is claimed.
- Owner explicitly approved pushing both the bot changes and the collaborator's LiDAR feature to main in IEatOreos/ProvingGroundsOreo. No binary, installer, tag, or GitHub Release is included; upstream VERSION remains unchanged.

## Unreleased — LiDAR mode records vehicle drives and shows them in the 3D view, 2026-11-06

- The owner asked to record driving paths in LiDAR mode instead of painting them; items 1 and 2 of the plan (record in LiDAR mode; show drives in the LiDAR viewer/simulator). Item 3, a Paint-page eraser and vehicle-size tags for recorded drives, is deferred.
- tools/lidar.py main (LiDAR matches) now runs the existing RideWatch each tick, as normal bot matches already did. Every vehicle a person or bot drives or flies is merged into maps/<map>/rides.json at the one-minute LiDAR save and at match end. The bots' vehicle ground, people's "road" preference and aircraft heights (brain/maps.py rides_layers, Terrain._build_vnav) use it from the next match. Recording and saving errors are logged and never stop the mapping. The in-game LiDAR notice now mentions drives.
- RideWatch keeps a live feed of its samples (person drive / bots-only drive / flown air; up to 300,000, oldest dropped). Hub.live sends new samples after the page's `rsince`; rides_view gives every view (live match, LiDAR Viewer, LiDAR Simulator, other maps) the stored drives, using the same thresholds as the nav: a person once, bots twice. Flown air is drawn at its mean flown height.
- tools/lidar_view.html: new "Vehicle drives" layer (key V) with legend rows. Person drives are mint, bot-only drives faint mint, flights light blue. A "Vehicle drives: people / bots" stat; a driven but unscanned map still frames its drives.
- Validation: tools/test_lidar_drives.py (8 tests: person/bot feed and save thresholds, flight heights, feed trimming, riderless/dead/unknown vehicles, bad files, Hub feed only with a watch, the /live rsince endpoint including a 400 on bad input, page wiring). The LiDAR self-check and all other test suites pass. Browser check: the stored Park view drew the 459 recorded person-drive cells and the V toggle hid them and their legend; a stand-in live server driving a fake Warthog streamed new samples onto the page every poll. Not yet tried in a real LiDAR match.

## Unreleased — Clarified gunner weights and Demon resource precedence, 2026-11-06

- Apply the owner's clarification: power calls rank Demon → Legendary → Heroic/Scaling → Normal; gunner calls rank Demon → Legendary/Heroic/Scaling → Normal. Equal-weight candidates use distance; Easy retains its existing eligibility rules.
- Reserve power-weapon fetches after objective roles but before vehicle orders; select vehicle crews before honked/direct/aboard gunner calls. Exclude a Demon with a weapon fetch or driver job from new gunner and gunner-pickup calls; exclude a fetching Demon from new crew assignments. Protect every tier's assigned driver from subsequent gunner calls. Keep existing range, urgency, eligibility and radar restrictions. Demon can still take a gunner seat when no eligible power job was assigned.
- Files: brain/profiles.py, brain/director.py, resource-call/fetch regression tests and customization notes. The owner confirmed the prior deterministic eligible Demon radar behavior; no further radar or aiming change.
- Validation: all 87 tests pass, including real role-pass weapon/gunner contention, vehicle/honk contention, all four gunner-call exclusions, and tied Legendary/Heroic/Scaling weights. All 90 brain/tools Python sources compile in memory and Git whitespace checks pass. Gameplay is untested; restart the bot process/launcher. Local source only; no GitHub push or native rebuild.

## Unreleased — Demon awareness and resource-call priority, 2026-11-06

- Set fixed Legendary flick overshoot to exactly zero after profile variation. Keep other restored attributes, protected head/turret precision, lower tiers and Scaling unchanged.
- Expand Demon to a 140-degree horizontal vision cone, with no peripheral recognition penalty and its existing zero configured reaction delay. Always notice eligible motion-tracker contacts, preserving tracker settings/range, movement, crouching and jamming checks. Ordinary awareness probability remains for other difficulties.
- Prioritize new calls Demon → Legendary → Heroic → Normal → Scaling, then existing Easy eligibility, with same-tier distance ties. Apply to power-weapon fetches, power-vehicle drivers (existing taxi_ok classification), direct/aboard/honked gunner calls and driver gunner pickups. Preserve existing commitments and ordinary transport/passenger/ferry selection. Filter ranges before ranking; eligible objective bots retain their 15-unit power-vehicle limit and compete with idle drivers.
- Owner was asked about gunner inclusion, eligible radar certainty, and Scaling/Easy placement. The stated defaults above were used pending clarification. No native changes, automatic restart or GitHub upload.
- Validation: 82 regression tests pass, including actual power-weapon/vehicle/gunner selection, fallbacks, existing commitments, transport preservation, Demon vision boundaries and 120 radar eligibility scenarios. Source syntax and Git whitespace checks pass. Gameplay remains untested; restart the bot process/launcher to apply.

## Unreleased — Separate Demon from Legendary attributes, 2026-11-06

- Make Demon a distinct brain tier (`tier="demon"`, extra None), retaining the prior tuned Legendary numeric profile exactly across tested personalities/seeds. Add independent Demon entries to tier/turn/craft/reaction/callout/headshot/dry-shot/ramming/escort tables and extend fixed-tier checks, vehicle/head aiming, landing grenade tactics, resource fetching and CLI difficulty mapping. Preserve the collaborator's native menu keys, local build and display/report support.
- Restore Legendary's base profile to the installed author's defaults: reaction 0.154 s, decisions 0.10 s, tracking 0.08 s, lag 0.045 s, aim error 0.006 rad, overshoot 0.30, lead 0.8, flick 0.7 and turn 1000 deg/s, with the original variation. Demon retains 0 reaction, 0.01 s decisions without jitter and the former precise aim parameters. Scaling and lower-tier profiles remain unchanged.
- Preserve Legendary live head tracking and final DMR/sniper head corrections, plus its precise vehicle/head-directed aim via an explicit protected context. Active aim parameters also govern the firing-alignment test; switching from ordinary aiming clears stale error samples. Reaction/decision attributes are restored globally; the protected exception preserves aiming accuracy, not zero-delay target recognition.
- Keep the existing 120-degree vision, 80-unit fetch allowance, tactical grenade policy, head/chest selection, sniper percentage exceptions and Armor Lock rules for fixed Legendary and Demon. Mixed keeps its existing standard difficulty composition. Campaign/Firefight escort code recognizes Demon explicitly while retaining its prior escort parameters. No native source/binary changes, automatic restart or GitHub push.
- Validation: 69 regression tests, 88 source syntax checks and whitespace checks pass. Numeric golden profiles match the author for Legendary and the pre-split custom profile for Demon. An additional 4,480 simulated aim steps matched pre-change output and RNG state for Demon, lower tiers, Scaling and protected Legendary. Existing Halo 4/Reach, sniper, fetch, Armor Lock and migration checks remain passing. Gameplay is untested; restart the bot process to apply.

## Local workflow — review teammate work before publishing, 2026-11-06

- Record the owner's requirement to inspect both local teammate changes and fetched GitHub history before every push. Review all outgoing commits and the combined scope; additional unpublished teammate features need approval when outside the requested upload.
- Recheck concurrent work and publish only the reviewed commit. Preserve in-progress files and all existing commit identities. Documentation only; no gameplay change or GitHub upload.

## Unreleased — Demon native build confirmed in game, 2026-11-06

- Documentation only; no code change. After 0.2.2-custom.3, the owner's machine received Visual Studio Build Tools 2022 (C++ workload). `native\build.bat demon` compiled the published source (through 5620698) into native/bin/botcore_demon.dll without errors. The only warnings were existing _wfopen deprecations in unchanged lines. The tools/panel_art.py step after the build failed because PATH Python lacks PIL; the DLL is unaffected.
- The owner restarted MCC through the launcher and confirmed in game that the Demon difficulty works. The rebuilt DLL stays local and is not uploaded. The 0.2.2-custom.3 and Demon entries below that say "not compiled" or "untested" describe the state when they were written.

## 0.2.2-custom.3 — source update, 2026-11-06

- Publish the six-unit sword/Gravity Hammer Armor Lock activation change (5620698), retaining the preceding Demon difficulty commit (23e1149) without rewriting either commit. Low shields/recent damage alone no longer trigger Armor Lock; other triggers and existing restrictions remain.
- This normal main-branch source push includes the pending Demon implementation. Its native BOTS menu changes are source-only: no rebuilt DLL or installer is included, and the native code has not been compiled here. See the implementation entry below for the existing saved-difficulty compatibility limitation.
- Validation: all 60 Python regression tests passed with a workspace-local temporary directory; all 87 Python sources compiled in memory; whitespace checks passed. Gameplay remains untested. The owner requested this push. No tag, GitHub Release, binary, personal setting, recording or learned-map upload is included.
- The earlier Unreleased headings describe the state when each feature was implemented; those entries are retained for detailed behavior and validation history.

## Unreleased — Armor Lock melee-weapon proximity trigger, 2026-11-06

- Replace both low-shields/recent-damage Armor Lock branches (the nearby-enemy rule and Normal's no-cover fallback) with activation when a visible enemy carrying a sword or Gravity Hammer is within 6 world units, inclusive. This new trigger does not require low shields, recent damage, enemy facing or lack of cover.
- Preserve grenade, explosive-aim, vehicle, existing lunge and objective-hold triggers; retain current energy/input/cooldown gates, Easy's ability restriction, Infection survivor exclusion and hold/release behavior. Other abilities' low-shield rules are unchanged. Demon inherits the rule through its existing Legendary alias; preserve commit 23e1149 and its behavior.
- Validation: all 60 regression tests passed and all 87 current Python sources compiled in memory. Five new Armor Lock tests cover full-shield sword/hammer activation across Normal/Heroic/Legendary/Demon, exact range and visibility, removal of low-shield-only activation, restrictions, and retained explosive/objective triggers. The first full run hit a sandbox temporary-directory permission error in the existing Demon test; rerunning with a workspace-local temporary directory passed without modifying that test.
- Restart the bot process to apply. Gameplay is untested. No GitHub upload or native rebuild is included.

## Unreleased — Demon difficulty (fixed Legendary renamed), 2026-11-06

- Add a Demon difficulty, an exact copy of fixed Legendary under its own name, as the owner asked. brain/profiles.make_profile("demon") builds the "top" profile with the same random draws and sets only Profile.label = "demon"; tier stays "top" and extra None, so every `tier == "top" and extra is None` rule (precision, zero reaction, 10 ms decisions, 120-degree vision, live DMR/sniper head corrections, grenade policy, 80-unit power fetch) applies unchanged. Any later Legendary change also changes Demon.
- Native BOTS panel: tier 5 / key "demon" (HB_TIER_DEMON), "for everyone" difficulty 6 (botcore.ini difficulty=, shared.h). Quick setup and the footer show Easy, Normal, Heroic, Legendary, Demon, Mixed, Scaling (Scaling stays last for its hover box). The selected-bot inspector shows Demon beside Scaling on the second row because five ranks don't fit its width. Demon uses a crimson colour and five chevrons; the lobby tile names it. botcore launches play.py with --tier demon. Existing saved lists and difficulties 0-5 load unchanged.
- Python: botctl accepts "demon" on the BOTS list; the trace meta line, Observer, player stats and match export show "Demon"; the escort brain plays it as Legendary; the guide lists it.
- Validation: tools/test_demon_difficulty.py (5 tests: Demon equals fixed Legendary for every play style and seed apart from label, trace label, BOTS-list parsing, native tier/difficulty tables agree with the Python keys). Existing sniper, power-fetch, migration, Halo 4 head and Breakpoint suites pass; edited Python compiles. No C++ compiler is installed on this machine, so native/botcore.dll is NOT rebuilt or compiled: the menu change needs `native\build.bat` on a machine with Visual Studio C++ build tools, then an MCC restart. Gameplay is untested. A DLL older than this change reads a "demon" bot as Legendary, but reads a saved difficulty=6 as Easy.

## 0.2.2-custom.2 — Halo 4 animated-head aiming, 2026-11-06

- Add a Halo 4-only reader for the captured 120-node Spartan target_head marker (node 54, descriptor +0x1BC) and cached unit view point (+0xD50). Validate layout, alignment, complete reads, finite/orthonormal/right-handed transforms, scale and world-space proximity; publish both endpoints or neither.
- Carry view_pos through the live snapshot without changing the shared generic eye() function. Head-directed tracking and final Legendary DMR/sniper shot corrections use the matched Halo 4 view/head pair. Percentage sniper shots use the same pair while retaining existing thresholds and retry outcomes. Movement direction is preserved during final corrections.
- Head perception and firing use the same world-space endpoints with the existing terrain/material/barrier rules. Chest aiming is unchanged. Unsupported models or partial pairs retain legacy aiming; Reach's animated-head reader and H2A behavior are preserved. No reaction, decision interval, weapon cadence, damage or accuracy-roll thresholds changed.
- Evidence: two read-only Halo 4 captures, 1,154 human calibration poses and 1,626 human/bot poses; all 2,780 raw poses passed reader replay. The source's .62/.38 offsets were not applied as a standalone height subtraction because the shooter reference also differs. The captured view point is a view-origin correction, not independent proof of every physical bullet spawn.
- Validation: all 50 regression tests passed, all 85 Python sources compiled in memory, and whitespace checks passed. Ten new checks cover stance decoding, corrupt/unsupported data, matched-origin aiming, movement preservation, sniper outcomes, Reach/partial-pair fallback, occlusion, perception and player-reader wiring. The existing placed.py ResourceWarning remains. MCC was closed before implementation, so post-fix gameplay is untested; restart Proving Grounds and test a fresh Halo 4 match.
- The owner authorized this source push, including the dependency on the previously local 0.2.2-s181 import/custom migration (6433bb3, ca7eeb0). Preserve all prior collaborator commits. No tagged GitHub Release, installer, raw game capture, user settings, learned map export or binary upload is included.

## 0.2.2-custom.1 — local upstream migration, 2026-11-06

- Migrate to the author's installed 0.2.2-s181 source and native binaries. Archive the newly installed source locally before editing, record that installed source separately in Git, and merge individual custom methods/blocks rather than restoring old full files. All prior custom and collaborator commit identities remain ancestors.
- Retain new upstream Firefight match shutdown/respawn behavior, DLC detection, separate species loadouts, Forge/dropped-weapon identification, shared team scheduling, aircraft/navigation improvements, equipment hazard routing and final melee validation. The new launcher, updater and native adapters remain as installed.
- Restore fixed Legendary precision, zero reaction delay, 10 ms decision interval, 120-degree vision, head/chest targeting and live DMR/sniper head correction; restore sniper intended accuracy (Easy 10%, Normal 25%, Heroic 50%), tactical grenade policy, firing recovery, loaded-sniper retention, 80-unit power fetching, Reach loadout ratings/ranks and the collaborator's Breakpoint correction. Legendary-first resource assignment was discussed but never implemented and is not added here.
- Integrate the new Reach ammo fields and tag/magazine naming caches with our known-empty detection, signed/short-read guards and non-Reach isolation. Unknown named guns can still use upstream's magazine-learning fallback; battery depletion remains unknown.
- Restore installer-removed custom tests/workflow documentation. Add seven behavioral migration checks for upstream hazard and melee integration, tag caches, first-seen empty snipers, unknown-weapon learning, animated-head validation and species palette separation.
- Validation: all 40 regression tests passed; all 84 current Python sources compiled in memory; live runner --help and the new updater's offline selftest passed. The pre-existing placed.py ResourceWarning remains. This validates source integration, not live gameplay. No game/bot restart, native rebuild, GitHub push, tag or installer publication is included.
- Prior installation backup: F:/Proving Grounds Backups/Project Proving Grounds_2026-11-06_163131 (12,676 SHA-256-verified files). Raw newly installed source and its manifest are under ignored logs/migration_0.2.2-s181_2026-11-06. User settings, recordings, binaries and derived map assets remain outside the source commit.

## 0.2.1-custom.3 — source update, 2026-11-05

- Batch the three local gameplay updates: fixed Legendary zero reaction delay; fixed Legendary 10 ms decision interval without timing variation; and fixed Easy/Normal/Heroic sniper intended accuracy of 10%/25%/50% with precise aim and deliberate misses. Legendary sniper behavior and Scaling remain unchanged by the accuracy feature. The shared live loop remains 30 Hz.
- Preserve the individual implementation commits f929768, 12145d5, and 0c99e08 and all previously published collaborator commits. The owner explicitly authorized this source push to IEatOreos/ProvingGroundsOreo main. No tagged GitHub Release or installer asset is included.
- Detailed entries below describe the state when each change was implemented; their earlier "Unreleased" headings and "No GitHub upload performed" notes refer to that implementation stage.
- Validation: all 33 regression tests passed, all 82 current Python sources passed syntax compilation, and the full batch passed whitespace checks. The pre-existing placed.py unclosed-file ResourceWarning remains. Gameplay is untested; restart the bot process to apply. Intended sniper percentages do not guarantee match hit or kill rates.

## Unreleased — Difficulty-based sniper accuracy, 2026-11-05

- Fixed Easy/Normal/Heroic sniper rifles use precise head tracking with 10%/25%/50% intended hit rolls against on-foot targets. Remove competing aim wobble, lead error, and loose early/follow-through firing on this path. Use the live animated head marker where available, with the existing stance-height fallback. Miss outcomes fire beside and above the target rather than suppressing shots.
- Retain each difficulty's perception/reaction, decisions, movement, weapon cadence and safety checks. Preserve world movement direction during final shot aiming. Legendary's existing sniper/DMR behavior, Scaling, other weapons and vehicle combat are unchanged.
- Retain outcomes until a known magazine changes; rejected attempts and post-grenade retries do not repeatedly reroll. When magazine counts are unknown, use a cadence-bounded fallback; actual per-bullet acknowledgement is unavailable in that case. Suppress simultaneous melee/switch fire and exclude intentional misses from blocked-sightline learning.
- Validation: 33 offline regression tests passed, including nine sniper tests for distributions over 10,000 consumed rounds per tier, retry acknowledgement, reload observation, unknown-magazine fallback, action conflicts, exemptions, perfect tracking, final live-head aiming/movement, and false-wall prevention. All current Python source syntax and whitespace checks passed. The pre-existing placed.py ResourceWarning remains.
- Restart the bot process to apply; live gameplay is untested. Percentages describe intended shots, not guaranteed engine hits or kills. No GitHub upload performed.

## Unreleased — 10 ms fixed Legendary decision interval, 2026-11-05

- Set fixed Legendary's decision interval to 0.01 seconds and remove its per-decision timing variation. Other difficulties and Scaling retain their original interval and random variation.
- The live brain loop remains 30 Hz. The shorter decision deadline is processed on an available loop update, not at a guaranteed 100 decisions per second. The prior zero reaction delay remains in place.
- Validation: profile isolation and actual scheduling-block checks passed; existing regression tests, Python syntax checks, and whitespace checks passed. Gameplay is untested; restart the bot process to apply. No GitHub upload performed.

## Unreleased — Zero fixed Legendary reaction delay, 2026-11-05

- Set make_profile's fixed Legendary reaction override from 1/30 second to 0 seconds. Other difficulties and Scaling's separate profile builder are unchanged.
- Zero removes the configured perception reaction delay, including its peripheral multiplier; it does not remove live-loop scheduling or decision intervals.
- Validation: checked all personalities for zero Legendary reaction, unchanged other-tier and Scaling profiles against the prior source, and zero central/peripheral react_time results. Python syntax and whitespace checks passed. Live gameplay is untested; restart the bot process to apply. No GitHub upload performed.

## 0.2.1-custom.2 — source update, 2026-11-05

- Set Reach's weapon ranks to Focus Rifle 3.6 and DMR 3.5, across difficulties. Other games retain their prior ranks. Retain the requested Focus range tuple (0.1, 1.0, 1.0, 1.0), Reach AR Short-band rating 0.8, shotgun rating 1.0, and Reach upgrade cutoff 0.05.
- Verified calculated scores with the new ranks: DMR+AR 0.91, DMR+Focus 0.92, Focus+AR 0.98, DMR+shotgun 0.97, Focus+shotgun 1.04. An eligible nearby Focus upgrade replaces the DMR while preserving the AR or shotgun; it is still not a dedicated power-weapon fetch item. Battery depletion remains unknown.
- This source-upload batch also includes the earlier developer handoff, the collaborator's unchanged Breakpoint sight-line fix (1aa3339), fixed Legendary 80-unit power-weapon calls with travel allowance, the AR/shotgun preference change, Focus range ratings, and the collaborator-preservation workflow. Detailed entries below record the state when each was implemented; their earlier "not uploaded" notes do not describe the final publication state of this batch.
- Preserve all existing commits, including the collaborator's commit, in the normal main-branch history. The owner explicitly approved this source push. No tagged GitHub Release or installer asset is requested or included.
- Extend loadout regression coverage to verify Focus pickup/drop decisions across difficulties, preservation of the close-range secondary, reverse-pickup rejection, and unchanged ranks outside Reach. Live gameplay still requires restarting the bot process and owner confirmation.
- Validation: all 24 regression tests passed; all 81 Python sources compiled; whitespace check clean. The existing placed.py unclosed-file ResourceWarning appeared during the passing Breakpoint checks. The collaborator's commit remains an ancestor, and its map, terrain, correction-data, and test files are byte-for-byte unchanged from that commit.

## Local workflow — preserve collaborator commits, 2026-11-05

- Recorded the owner's requirement to preserve the coding collaborator's commits and intended behavior in AGENTS.md and docs/CUSTOM_RELEASE_WORKFLOW.md.
- Future pushes require fetching/reviewing the latest remote commits, merging incoming work without rewriting published history, reconciling overlapping behavior, and using normal pushes. Force-pushing or overwriting newer files with older copies is prohibited.
- Documentation only; no bot behavior changed and no GitHub upload performed.

## Unreleased — Focus Rifle range ratings, 2026-11-05

- Set the Focus Rifle proficiency tuple to the requested (0.1, 1.0, 1.0, 1.0). This changes AI range/loadout valuation, not the weapon's actual damage, battery, or aiming mechanics.
- With Reach's current AR rating and range weights, the real loadout calculator returns DMR+AR 0.95, DMR+Focus 0.92, and AR+Focus 0.94. DMR+Focus still scores 0.03 below DMR+AR: a 0.06 weighted short-range loss exceeds the 0.03 extreme-range gain.
- A nearby Focus Rifle is still rejected as an ordinary upgrade from a loaded DMR+AR loadout. No pickup cutoff, weapon rank, or power-weapon fetch classification was changed for this request.
- Validation: all four loadout regression scenarios passed; all 81 Python sources compiled. Requires a bot-process restart for gameplay; no GitHub upload or release performed.

## Unreleased — Reach AR and shotgun loadout preference, 2026-11-05

- Set Reach's assault-rifle Short-band proficiency to 0.8; the shotgun remains 1.0. AR ratings at other distances are unchanged. Other Halo games retain their original AR ratings.
- Reduce the ordinary Reach upgrade cutoff from 0.08 to 0.05. The requested DMR+AR -> DMR+shotgun improvement is 0.06, so changing the rating alone would still have been rejected by the old cutoff. This cutoff applies to other ordinary Reach upgrade decisions too; it does not force every higher-ranked gun to replace a lower-ranked one.
- Current calculated pair scores: DMR+AR 0.95, DMR+shotgun 1.01. The real upgrade/weapon-selection methods accept the nearby shotgun and equip the AR for replacement while keeping the DMR. The reverse AR pickup is rejected.
- Applies across Reach difficulties, including Scaling. Existing pickup distances, recent-swap protections, combat priorities, and the loaded-sniper low-ammo exemption remain in place. The range rating also informs ordinary combat weapon selection; game weapon damage and accuracy are not modified.
- Added four regression scenarios in tools/test_reach_loadout.py covering the requested pickup/drop decision, reverse rejection, other-game behavior, and distance/cooldown restrictions. Requires bot-process restart and gameplay confirmation; no GitHub push is included.
- Validation: all 22 available regression tests passed, all 81 Python sources compiled, and the whitespace check passed. The pre-existing placed.py unclosed-file ResourceWarning appeared during Breakpoint checks; no test failed.

## Unreleased — Fixed Legendary power-weapon call range, 2026-11-05

- Increase the team director's power-weapon fetch radius from 40 to 80 world units for fixed Legendary only (`tier == "top" and extra is None`). Easy, Normal, Heroic, and Scaling retain their existing behavior and radius.
- For fixed Legendary loose-weapon calls, allow at least estimated straight-line walking time (distance / 2.3) plus 10 seconds, retaining the original 25-second minimum. This prevents longer trips from expiring before normal arrival; it is a travel allowance, not a delay before starting.
- Preserve nearest-eligible one-bot assignment, the existing height limit, objective/carrier/vehicle restrictions, missing-weapon cancellation, and timed-spawn deadlines. Combat priorities, weapon classifications/rankings, and respawn anticipation remain unchanged. This improves opportunities, not guaranteed pickup ownership or a measured majority of spawns.
- Added tools/test_legendary_power_fetch.py with seven focused scenarios covering expanded range, difficulty separation, travel lifetime, assignment ownership, eligibility, cancellation, and timed-spawn deadlines.
- Validation: all 18 focused checks passed (seven power-fetch, eight ammo/rearm, three existing Breakpoint sight checks); all 80 Python sources compiled; whitespace check clean. The existing Breakpoint check emitted an unclosed-file ResourceWarning from brain/placed.py but passed.
- Requires a bot-process restart and gameplay confirmation. No GitHub push or release is included in this local change.

## Unreleased — Breakpoint tower-to-bridge sight fix, 2026-11-05

- Breakpoint (reach_dlc_invasion) only. The level export has no ground in the gap between the tower ledge and the bridge, only a thin sloped surface 16-26 u overhead (x 1.9-6.6, y 11-23). Sight, shot and crosshair rays treated the air under it as inside a hill, so bots on the bridge never saw a person on the ledge.
- Evidence: BTB match 20261105-192945, seconds 171-213. Enemies aimed straight at the ledge from 15-23 u but only heard the person or tracked them on radar, while the person's DMR shots hit them. The owner's Theater clip from the same spot shows a clear view of the bridge.
- Added maps/reach_dlc_invasion/sight_open.json and Terrain.set_open_under (loaded by maps._build). In that box, cells with no floor whose only surface is above z 5 have no ground for _ray and aim_hit (375-400 cells). Walking, falls and aircraft still use the original lowest-surface data. No other map has the file, so no other map changes.
- Replaying the match positions, sight lines from enemies facing the ledge (within 30 u and 60 degrees) went from 13 of 138 open to 46 of 138. The remaining blocks are the ledge lip in front of the person and a low solid wall near the bridge, which a bot's eye line just grazes. Those were left unchanged.
- Validation: the new tools/test_breakpoint_sight.py (3 tests) fails without the correction file and passes with it; the eight ammo/rearm tests pass; 79 Python sources compile; whitespace check clean.
- Gameplay confirmation still needs a bot-process restart and a live check from the tower ledge with enemies on the bridge. No GitHub upload or release performed.

## Local documentation — developer handoff, 2026-11-05

- Added DEVELOPER_HANDOFF_2026-11-05.md with repository access/setup, exact published commits, retained customizations, implementation details, validation, evidence locations, and outstanding work.
- Publication clarification: the initial snapshot c9a9b1f and both fixes (3f96e8e and a731340) were pushed to the private GitHub repository with owner approval. Earlier "Unreleased" and pre-upload statements below describe the state when those entries were written; no tagged GitHub release or installer has been published.
- Handoff verification reran all eight ammo/rearm tests and compiled all 78 Python sources. No bot behavior changed for this documentation task.
- The handoff and this documentation update are local; another upload requires owner approval.

## Unreleased — Keep a sniper with ammunition, 2026-11-05

- Exempt the held sniper from low-ammunition rearming while it has any total ammunition remaining, including a reserve round awaiting reload. Applies across difficulties and games using this shared rule.
- A completely empty sniper retains existing rearming and weapon-switching behavior. Other weapons retain their low-ammo rules. Deliberate upgrade/power-weapon pickup decisions are unchanged.
- Motivated by LilWraith dropping a sniper with two rounds for an assault rifle while carrying a loaded DMR. Regression coverage checks one/two remaining sniper rounds across five difficulty modes, empty snipers, and an ordinary low-ammo weapon.
- Validation: all eight ammo/rearm regression tests passed; all 78 Python sources compiled; the patch passes whitespace checks.
- Gameplay confirmation requires restarting the Proving Grounds bot process. No GitHub upload or release performed.

## Unreleased — Reach live ammo and reload fix, 2026-11-05

- Supply live total-ammo and magazine counts for recognized magazine-fed Reach weapons. Battery/charge weapons and objectives remain unknown, rather than being incorrectly treated as empty. Halo 4 and H2A retain their existing reader behavior.
- Remember observed magazine counts every bot tick, including combat, so the existing 40% between-fights reload threshold has a useful reference after a kill.
- Existing empty-weapon switching and rearming rules can now use Reach ammo counts. These data changes apply across difficulties; their existing decision differences remain.
- Verified read-only in a live Reach match: DMR 15 loaded/30 reserve -> 12/30 after three shots -> 15/27 after reload; sniper 4/4 -> 3/4 -> 4/3 -> 0/0 after depletion. HUD showed the empty-sniper switch prompt at 0/0.
- Other listed magazine-fed weapons use the same reader but still need individual gameplay confirmation. Battery depletion is not implemented. Bot reload/switch behavior after restarting the process still needs gameplay confirmation.
- Validation: six offline regression tests passed, covering recorded count sequences, unknown/battery and invalid reads, isolation from H4/H2A layouts, empty-sniper switching across all five difficulty modes, and low-magazine reload decisions after combat observation. All 78 Python sources compiled. The updated live player reader reported DMR total/magazine 42/15 and sniper 0/0; the player had already switched to the DMR, so this was not an observed bot switch.
- Controlled memory samples, pre-change source copies, and the exact patch are saved locally under logs/ammo_probe (excluded from GitHub).
- No GitHub upload or published release is authorized by this local fix.

## 0.2.1-custom.1 — prepared 2026-11-05, unpublished

- Establish local version control for the installed upstream 0.2.1 derivative.
- Inventory retained Legendary precision, live-head targeting, grenade, firing retry, and vision changes in CUSTOMIZATIONS.md.
- Preserve upstream license, notices, documentation, and credits.
- Exclude local logs, recordings, settings, bundled runtimes, generated map exports, installers, and the separate vehicle recorder.
- Document explicit user approval for every GitHub push and release.

This setup makes no changes to bot behavior. Historical gameplay and validation results in the handoff are not new checks performed for this snapshot. Sniper live-head behavior still needs gameplay confirmation. No sniper miss-chance behavior has been added.

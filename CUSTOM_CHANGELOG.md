# Custom release history

## Unreleased

### Tank drivers: a man with a vehicle killer in range counts with the vehicles, 2026-11-13

The owner, on the tank targeting below: "Can you change the one mongoose scenario?" (a Mongoose 30 u off picked over a rocket man 20 u off).

- `brain/bot.py` `Bot.vehicle_pick`: a man on foot carrying a gun that kills vehicles (`VEHICLE_KILLERS`: rockets, Spartan Laser, Plasma Launcher, missile pod, railgun, fuel rod, incineration cannon) within `TANK_VEHICLE_R` (40 u) is in the vehicles' band, the second, and the guide's score decides among them: a rocket man 20 u off now goes before a Mongoose 30 u off. A man within 10 u still goes first whatever he carries; one with a rifle past 10 u stays with the rest.
- A correction to the entry below: its test named the launcher "rocket_launcher", the brain's name is "rockets", so its "rocket man" carried a pistol to the score. The example there (a Mongoose over him) held for a man with a rifle, not a launcher.
- Validation: `tools/test_tank_targets.py` (6: a rocket man 20 u off over a Mongoose 30 u off for both tanks, not past 40 u; a man with a pistol 20 u off still after the Mongoose; past both ranges the plain score, checked against `target_score`). All `tools/test_*.py` files pass. Python only. **Untested in game.**

### LiDAR Simulator: simulate every map of one game, 2026-11-13

The owner: "can we add an option to lidar simulate all the maps in a per game basis? So if I want to simulate all of reach I can do that instead of having to Que them all".

- The Simulator panel's "Every map" button is now "Simulate every map of" a game (Halo CE, Halo 2, Halo 2 Anniversary, Halo 3, ODST, Reach, Halo 4) or every game, then Simulate all.
  - The confirmation names the game and how many maps (on this PC: Halo CE 19, Halo 2 25, H2A 7, Halo 3 32, ODST 8, Reach 28, Halo 4 25, 144 in all), and says when the map running now stops.
  - From a map opened in the window it switches to the simulation.
  - Forge layouts are left out, as before.
- `tools/lidar_sim.py` `Control` action "all" takes `game`: that game's maps only (`jumpphys.game_of`). An unknown game is refused (400), a game with no maps here too (404), and a refused one leaves the queue as it was. The answer says how many were queued.
- Validation: `tools/test_lidar_mappers.py` +2 (one game's maps only, no layouts; every game; the refusals keep the queue; the test caught a refusal that emptied it). All 650 regression tests pass. In the Simulator window, with the confirmation cancelled so nothing ran: the list showed every game, and the confirmations read Reach 28, Halo 4 25, every game 144. A full run by game is untested.

### Tank drivers: a man on foot close by first, then vehicles in range, 2026-11-13

The owner: "a tank driver, scorpion or wraith prioritizes killing an enemy that's within so many units, then prioritizes vehicles. Unless an infantry is within so many more units?"; on the proposal (infantry within 10 u, then vehicles within 40 u, then the rest): "Yea we can try that at first".

- Before (`brain/bot.py` `Bot.vehicle_pick`, guide 17 §4.2 `vehicles.target_score`): every enemy in sight was scored by his threat and how fast the main gun kills him, distance only a tiebreak. A man carrying a launcher scored three times one with a rifle, so a Scorpion could shell a far Warthog while a man walked up to board it, or a rocket man over a Mongoose in range.
- Now a Scorpion's or Wraith's driver picks in bands: a man on foot within `TANK_FOOT_R` (10 u) first; else an enemy vehicle within `TANK_VEHICLE_R` (40 u); else the best of the rest (men farther off, vehicles past 40 u). Within a band, the guide's score as before (a Banshee over a Mongoose). A shot the score holds (0) stays held.
- Every difficulty. The tank's gunner seat (Halo 3's Scorpion), the Mantis and every other vehicle unchanged; Easy's tank still shoots what it meets in front of it on its trip.
- Validation: new `tools/test_tank_targets.py` (5: the close man first for both tanks; a Mongoose 30 u off over a rocket man 20 u off where the Mantis, uncovered, still picks the rocket man; a man 8 u off over a Banshee 15 u off the old score picked; the score within a band; past both ranges as before). All 63 `tools/test_*.py` files pass. Python only. **Untested in game.**

### Wheelman: always out looking for a gunner or a passenger, in place of the objective run, 2026-11-13

The owner, on the objective run below: "Can we change number 3 I don't want it sitting idle. It should always be searching for a gunner or passenger".

- **The search** (`brain/director.py` `vehicle_jobs`, `gunner_pickup(anyone=True)`): a Wheelman with a seat free and no other job drives to the nearest teammate on foot, any distance (others: a gunner only, within 60 u, and only one with a trip of 25 u or more). Bots and a person of ours both count, not a carrier (the ferry's job), a defender (his post) or, while we carry, an escort (`wheel_rider_ok`). By him it stops and waits (the existing pickup wait, 8 s; one who does not get in is skipped for 30 s). An Easy Wheelman fetches only bots: Easy never drives a person. Nobody to fetch: its patrol, so it keeps moving. The objective run (drive to their flag or the hill and wait there) is gone.
- **The call** (`rider_calls`): a Wheelman's vehicle calls a teammate within 12 u aboard whatever his trip (others: only a trip of 25 u or more), the gun first, then a passenger seat. Once riders are in it takes them where they go, as every driver.
- Validation: `tools/test_wheelman.py` (16: the search for a bot 150 u off, a person 120 u off, the nearer of the two; none for a Rusher, none for a person by an Easy Wheelman, nobody to fetch; a teammate 5 u off with a 3 u trip called by a Wheelman, not by a Rusher). All 62 `tools/test_*.py` files pass. Python only. **Untested in game.**

### Wheelman: first to pick up our carrier, the getaway ride, and an objective run, 2026-11-13

The owner: "Can we also add to wheelman to always go pick up flag carriers or objective? Or is that already baked in to a driver", then "Add all three".

- **Our carrier** (`brain/director.py` `ferry_orders`): a Wheelman at the wheel of a vehicle with a passenger seat free is sent for our flag or bomb carrier on foot before a nearer driver, from `WHEEL_CREW_REACH` (70 u; other drivers 45). The getaway ride waiting for him still goes first, from any distance. The carrier still gets in within 10 u, as before.
- **The getaway ride** (`vehicle_jobs`): drivers are now weighed Wheelmen first, so the team's one getaway ride (parked on the way out of their base while our runners go for their flag) is a Wheelman's; other drivers in their old order.
- **The objective run** (`vehicle_jobs`): a Wheelman with no other job (no carrier to hunt or escort, no riders to take, no getaway, no enemy vehicle for its tank, no gunner to fetch) drives to the objective (`straight_objective`: their flag, the hill, the ball, the bomb, a drop point), there to be when a ride is wanted. Not in a Mongoose, nor as a runner or a ferry. Slayer: its patrol, as before. Riders aboard: taken to their own objective, as for every driver.
- **Unchanged**: a Demon Wheelman still never drives a Warthog, Mongoose or Ghost; other drivers' jobs as before.
- Validation: `tools/test_wheelman.py` adds 3 (14 in all: the carrier sent to a Wheelman at 60 u over a Normal at 20 u, not at 80 u, and no other driver from 60 u; the getaway ride to a Wheelman listed second and, with none, to the first driver as before; the objective run in CTF to their flag, none for a Rusher or in Slayer). All 62 `tools/test_*.py` files pass. Python only: a bot-process restart, no new DLL. Committed as dafbdad, this entry after it (the changelog was being edited at the same time). **Untested in game.**

### LiDAR Viewer and Simulator: zoom where you point, double-click to fly there, arrow keys to move, 2026-11-13

The owner: "in the LiDAR simulator can we make it to where I can traverse the map better instead of just being able to rotate? I would like to free move around the map and zoom in to where I exactly need to edit."

- Before: left-drag orbited, right- or Shift-drag panned, and the wheel zoomed toward the view's middle, so a spot took zoom, pan, zoom, pan. The arrow keys only turned and tilted it.
- `tools/lidar_view.html` (the Viewer's and the Simulator's page):
  - The wheel zooms toward the floor under the cursor: the view scales round that point, so it stays under the cursor. It falls back to the plane at the view's height where no floor is drawn. As close as 1 u now (was 2).
  - A double-click flies to the spot under it, at half the distance (4-30 u). Off while Edit spots is adding something: those clicks are the tool's.
  - The arrow keys move over the map while held, along the view; Shift is three times as fast, and the speed follows the zoom. Page Up / Down raise and lower the view.
  - `[` / `]` turn it and Home / End tilt it (what the arrows did). The middle mouse button pans too.
  - Any drag, wheel or key cuts a double-click's flight short. Moving turns "Follow you" off.
  - The help line names the new controls; its tooltip has the rest.
- Validation (the page in a 1280x800 viewport, its frames run by hand: the Browser pane was hidden on the owner's desktop): six wheel notches toward a floor point took the view from 88 u to 30 u, the point stayed within 8 px of the cursor; a double-click flew to the clicked point (3.46, 4.50, 3.49) at half the distance; the up arrow held 0.5 s moved 5.97 u straight ahead (0 aside), as worked out; Page Up raised it; `]` turned it; every key let go cleanly. `lidar.py --selftest` passes. Not tried by hand with a mouse.

### Vehicle blockers in the LiDAR view: areas no ground vehicle of any size drives into, 2026-11-13

The owner: "It was trying to push into the base at home which I want vehicles to avoid at all sizes so maybe we will add a lidar simulator blocker", then "Yes add it now".

- Edit spots, new Vehicle blocker tool:
  - Click the middle of an area, then set its name and radius (0.5-30 u, 3 by default) in the panel. It shows as an orange ring on the floor; drag the middle to move it, Remove or Delete takes it out.
  - Saved to `vehicle_blocks.json` in the folder of the map or layout shown (`tools/spots.py` "vblock").
  - A viewer from before blockers sends no "vblock", and the file is kept as it is.
- `brain/maps.py` `owner_vblocks`: the brain reads each folder of `data_names` (malformed ones left out) into `Terrain.vblocks` when the nav is built.
- `brain/terrain.py`:
  - `vblock_nodes`: the cells inside each blocker within `VBLOCK_DZ` 2.5 u of its middle's height (one floor, not a deck over it) are off every vehicle size's ground, over painted drive cells too.
  - `drive_clear` meets them as a wall, so the ground guard steers off them, but not from inside one (a vehicle parked there drives out).
  - `_straight_ok` takes `avoid`: `vnav`'s shortcuts never cross a blocker or a wedge mark (a route past one cut 0.67 u into its edge without it).
  - Every ground vehicle (tanks, Warthogs, Mongooses, Ghosts); aircraft are not affected.
- Checked on the report's layout (Forge World `v4328b40e`): a 4 u blocker over the wedge spot in the red spawn area was read from its file, its cells were off both the car and tank ground, and a vehicle 6 u off driving at it met a wall at its edge (2.0 u). The test blocker was removed; the save had also rewritten the layout's `callouts.json` (its empty `sneak` written as empty red and blue lists, the same to the brain), which was put back.
- Validation: `tools/test_tank_drive.py` +4 (off both sizes' ground; a wall to the look ahead, not from inside; a route past it goes round; malformed blockers left out); `tools/spots.py --selftest` (blockers saved, named, refused out of range, kept by an edit without them); `tools/test_spots.py` updated. All 638 regression tests pass; `lidar.py --selftest` passes. In the viewer (its pane hidden, so through the editor's own functions): the tool added a blocker, the radius and name fields took 4 u and a name, Save wrote it and loaded it back. Its drawing and vehicles keeping out of it in a match are unverified.

### Tanks drive on a tank-sized ground, back off long enough to turn, and a wedge marks the spot for every vehicle, 2026-11-13

The owner's F9 on a Forge World layout (`20261112-213825`, 196.5 s): "Bots dont advance the map with a scorpion"; then "It was trying to push into the base at home which I want vehicles to avoid at all sizes ... for know do your proposed fixes both".

- What the trace showed: two bot Scorpions spent about 2.5 minutes each by their own bases.
  - Cosmic (Demon) sat within 2 u of (-56.4, -195.7) from 113 s to 270 s. The loop: throttle 0.35-0.6 with the hull facing about 45 degrees into a wall, no movement, 1.2 s of reverse (0.2 u back), then in again. After two wedges, "another way" picked a random place, routed out the same way. OblivionClaw by (-42, -98) did the same.
  - At the spot the nav saw only part of what it pushed into: open floor ahead on the vehicles' ground, a wall 1.8 u along the hull. Every vehicle had one ground, kept 0.75 u (`VEH_ROOM`) from walls: about half a Scorpion's width, not room to turn it.
- `brain/terrain.py`:
  - `use_vground(big)`: a tank's own vehicle ground, `VEH_ROOM_TANK` 5 cells (1.25 u, half a Scorpion's length) from walls. Each size keeps its own graph and caches, built on first use; `vnav` and `drive_clear` take `big`. The paint, rides and out-of-bounds resets clear both (`_vreset`).
  - `vwedge(p, yaw)`: where a vehicle wedged, the floor `VWEDGE_AHEAD` 1.5 u ahead of its hull, `VWEDGE_R` 1.25 u round, costs `VWEDGE_COST` 40 times more to drive into. It is taken off the vehicles' ground, and `drive_clear` meets it as a wall, on every size's ground. Kept for the match (`_build_vnav` applies the list), at most 64.
- `brain/bot.py`:
  - `tank_ground(v, T)`: a Scorpion, Wraith or Mantis drives and looks (trip, retreat, `ground_guard`) on the tank ground.
  - A wedged vehicle marks the spot (`vwedge`, the hull's heading).
  - A wedged tank backs off `TANK_BACK_S` 2.5 s with its view on its way on (the trip's next point), so its hull swings round. Other vehicles keep the 1.2 s three-point turn.
- Checked on the report's layout: the look along the hull at the wedge spot went from 1.8 u to 0.4 u after the mark; the look along its route (-78 degrees) stayed 6 u clear. The tank ground there is 248,692 cells against the cars' 278,694.
- Not fixed: the hand-placed blocker for a base's way in that vehicles of every size should keep out of (a LiDAR editor blocker, the owner's idea for later).
- Also: `tools/spots.py` level floor and `tools/lidar_sim.py` air-only seed took a nav cell as `NAV_CELL * nstep`; it is `NAV_CELL` (`Terrain._center`). Every map's heightmap cell is 0.25 u (nstep 1), so nothing changed in practice.
- Validation: new `tools/test_tank_drive.py` (the tank ground smaller and inside the cars', each size's ground kept apart; a wedge is a wall ahead for both sizes, costs more, survives a rebuild, is marked once, the way back open; the longer back-off). All 634 regression tests pass. Tank driving in a match is untested; the bot process must be restarted.

### Reach and Halo 4 Banshee pilots drop the bomb about every run, 2026-11-13

The owner: "I'd like the reach and halo 4 banshee pilots to use the bomb a lot more as it's a lot stronger than the plasma casters".

- Before: a bomb at most every 15 s (`FUELROD_EVERY`, from the owner's Reach rhythm, one every 17 s), and only with the nose within the cannons' 1.5 u of the man. Recent matches: 16 cycle presses on Boneyard (about 8 bombs), 6-14 in each of four Blood Crash matches (3-7 bombs).
- `brain/bot.py` `air_pass`, Reach and Halo 4 (the games where the cycle is decoded; Halo 3 and H2A still have no bomb input):
  - `FUELROD_EVERY` 15 -> 6 s: about one bomb a run.
  - The bomb goes with the nose within `BOMB_GUN_R` 3 u of him (its blast), the cannons still within `AIR_GUN_R` 1.5 u.
  - Unchanged: 10-31 u off, in Halo 4 from 2 u or more over him, the cycle timing (`fuel_rod`).
- The game's own bomb recharge is not read (the kits are not on this PC). A cycle to a bomb that is still recharging drops nothing and costs about 1.3 s of cannons.
- Validation (`tools/air_replay.py`, three real pilots' windows, the cycle on as live): bombs 3 -> 6 (Boneyard, 56 s), 3 -> 6 and 4 -> 8 (Blood Crash, 74 and 58 s); cannon fire ticks 11-16% fewer (the cycles). `tools/test_banshee_runs.py` +3 (a bomb with the nose 2 u off him, none 4 u off, the gap). All 631 regression tests pass. Bomb hits in a match are untested; the bot process must be restarted.

### The Wheelman play style: always goes for a vehicle, a Warthog first, and keeps driving, 2026-11-13

The owner: "Should we make a personality that always wants to drive warthogs? Like driver", "Or call it wheelman", then "Keep the two as they are now" (no Demon at a Warthog's, Mongoose's or Ghost's wheel; Easy never sent to drive a person on a gun).

- **Its own pick** (`brain/bot.py` `Bot.wheel_pick`, in `plan` before the usual trip rule): on foot, with no flag, no close fight, nothing urgent (and not in Race, Infection or as a Firefight escort), it goes for the nearest vehicle within `WHEEL_SEEK_R` (60 u) it may drive: a Warthog first (any kind), then another ground vehicle, then an aircraft, a Mongoose last. Every match, whatever the trip, where other bots take a vehicle only for a trip over 35 u, at 30-90%.
  - An empty one, or (not Easy) one of ours with a teammate on its gun and nobody at the wheel (`vehicles.wheel_open`), so a Wheelman comes to drive you.
- **The team's wheels** (`brain/director.py` `crew_orders`; `profiles.driver_priority` -1): a Wheelman is first for a Warthog's or Mongoose's wheel, ahead of a nearer Normal or Heroic, and is sent from `WHEEL_CREW_REACH` (70 u; others 45). `wheel_calls` (a person on a gun) also asks it first.
- **Keeps its vehicle** (`Bot.drive`): at a trip's end it drives on to the next place it is needed (patrol) instead of getting out, as a role's vehicle does. Wedged, it backs off as before, then takes another way up to `WHEEL_WEDGED_MAX` (3) times at a spot before it gets out. Not a Mongoose (its trips still end on foot), nor as a runner or a ferry.
- **Unchanged**: a Demon Wheelman never takes a Warthog's, Mongoose's or Ghost's wheel (it goes for a tank or an aircraft, else plays on foot); Easy is never sent by the team and never takes the wheel of a person's vehicle. Its driving is its difficulty's. On foot it plays as a flanker (traits). Not dealt to "Any style": only when picked.
- **Menus** (`native/bots_panel.cpp`, `bots_panel.h` `HB_STYLES` 9, `HB_STYLE_ANY` 8; `tools/botctl.py` `STYLE_KEYS`): "Wheelman" in the bot editor's play styles and the quick setup. Saved bots keep their style: styles are saved as words. Needs `native/bin/botcore_wheelman.dll` (MCC restart).
- `tools/test_demon_difficulty.py` and `tools/test_difficulty_separation.py`: their fingerprints cover the original seven styles.
- Validation: new `tools/test_wheelman.py` (11: the priority, menus, not in "any", the pick order, range, Demon and Easy rules, sent ahead of a nearer Normal and from 60 u, kept at a trip's end where a Rusher gets out). All 61 `tools/test_*.py` files and the pool checks pass; `native\build.bat wheelman` built `botcore_wheelman.dll` (not in Git; the build's panel-art step needs PIL, as before). **Untested in game.**

### Banshee pilots keep their attack on a man out of sight and stay on one man per run, 2026-11-13

The owner: "We have to make the banshee work. They're almost near useless when a bot is driving them. Make their dive pattern more steep or give ideas on what'll make them fly more efficiently".

- Measured: bot Banshee pilots in six matches (Boneyard, Valhalla, four Blood Crash). Their attacks barely lasted:
  - The guns fired on 1-19% of their rows. 0-22% of those rows saw the man's vitals drop, and there were 0-4 kills a match.
  - Attack runs lasted 0.1-0.3 s (median). Most ended in travel ("path", up to 87% of a pilot's time on Boneyard) or on a switch to another man. The way out and back (the "pass") lasted 0.1-0.5 s instead of seconds.
  - Most runs fired nothing: 62 of 75 on Boneyard, 118 of 174 on Valhalla.
  - The cause: the attack needs a man in sight this tick. Flown past him, or turned off him by a wall guard, he is out of view. The pilot then flew to its objective between structures, where the guards fought each other ("a structure by us, pull up" on 89% of Boneyard's travel rows).
  - Dives were not shallow: the nose was 24-33 degrees down when firing (median), inside the owner's 23-46. They fired from 15-21 u, 9 u up.
- `brain/bot.py`:
  - `Bot.air_keep`: with nobody in sight, a pilot's run man is still its target while he is alive, in its beliefs from the last `AIR_KEEP_S` 6 s and within `AIR_KEEP_R` 60 u. The way out and the turn back into the next run fly on him. `fire_gate` still wants the clear line, so nothing is fired blind.
  - `Bot.run_target`: while he is in sight, the run's man stays its target over the per-tick pick.
  - Every tier but Easy, every game, Banshee-role aircraft only (`vehicles.STRATEGY` role "air").
- Not done, tried in replay: a level approach at the run's height, then a steeper dive from 15 or 20 u flat. It cut the firing ticks in every replay (from 15 u: to 10-45% of today's), so it is left out. It can be tried in a match on its own.
- Validation (`tools/air_replay.py`, the bot flying four real pilots' windows against the matches' enemies):

  | Window | Travel ("path") before → after | Way out ("pass") | Fire ticks / min |
  |---|---|---|---|
  | Boneyard | 59% → 20% | 6% → 41% | 306 → 323 |
  | Valhalla | 37% → 4% | 10% → 40% | 534 → 519 |
  | Blood Crash bot 11 | 70% → 20% | 5% → 39% | 277 → 385 |
  | Blood Crash bot 8 | 42% → 2% | 13% → 41% | 471 → 665 |

  The guards' pull-up notes a minute fell to a fifth to a quarter. New `tools/test_banshee_runs.py` (6 tests: kept out of sight, not past 6 s, dead or 60 u, no run no keep, the run's man held in sight). All 617 regression tests pass. Hits and kills in a match are untested; the bot process must be restarted.

### Reach Headhunter: skull counts, banking and the live drop point, 2026-11-12

The owner: "see if there is code for headhunter in halo reach, and if not try and start making the bots play that mode", then "Yes, build it".

- **Before:**
  - Headhunter was recognised (`brain/modes.py`: the variant name, Reach's drop points on every multiplayer map, the loose skulls).
  - A third of the team ran to the drop point nearest its middle whatever it carried. Nobody knew who held skulls, and no recorded match had ever played it.
- **New `brain/headhunter.py` `Skulls`**, filled every tick by `modes.Watch` (`snap.skulls_held`, `snap.hh`). It reads nothing new from the game:
  - A loose skull that vanishes with a living player on it (1.6 u) is his.
  - A death drops them all.
  - A team score rising while a carrier of that team stands in a drop point is a bank, and that drop point is the live one (kept 90 s).
  - Skulls carried and 3 s in a drop point with no score: that drop point is not live and is skipped 45 s.
  - With no score for his team (Reach's free-for-all scores are not decoded), or the score never moving for anyone, he is taken to have banked.
- **The director** (`brain/director.py`):
  - `hh_bankers` (in `assign_roles`, as a carrier): a bot banks at 5 skulls always, 3 within 45 u of the drop point, 1 within 12 u, or enough to win. It runs to the live drop point (else the nearest not found dead) with no rogue moment.
  - `mode_slots`: an enemy carrying 3 or more that one of ours saw in the last 8 s is hunted first (two hunters from four bots up). Two take the loose skulls within 40 u, some cover the drop point, and the rest play Slayer.
- `tools/live_bots.py`: the trace's world lines carry `skulls` (the estimates) and `banked`, to check them after a match.
- Validation:
  - New `tools/test_headhunter.py` (16 tests): pickups, a rolling skull, deaths, a bank marking the live drop point, a dead drop point skipped then retried, free-for-all banking, a score that never moves, the bank rules, the Watch filling the snapshot, who banks, and hunting a seen carrier but not an unseen one.
  - All `tools/test_*.py` pass (592 tests). `tools/live_bots.py` compiles.
  - **Untested in game:** the whole mode. Whether Reach's skulls read as loose objects the way Oddball's do, whether the team score reads in Headhunter, and how Reach's drop points move are not yet seen live.

### Halo 4: every tier takes a Sword, Hammer or SAW over its AR, 2026-11-12

- The owner, Nov 12: "Yes, fix that too", after the note below. Before, in Halo 4 a bot on BR + AR took no sword, gravity hammer or SAW: they added 0.07-0.08 to the AR's Short 1.0, at the game's 0.08 bar. Demons got them by `power_grab` only.
- `brain/bot.py` `POWER_PICKUP_GAMES` {"h4", "reach"}, `POWER_PICKUP_RANK` 3.8, `power_gun`: a power gun (rank 3.8 and up, and in Reach `NEEDLE_YIELDS_TO`) is worth at least the bar + `OVER_AR_MARGIN` to a bot carrying no loaded power gun (`upgrade_point`), every tier. `drop_slot` gives up as before: the AR from BR + AR, the Boltshot from BR + Boltshot.
  - Halo 4's Shotgun (3.4) is not one: the playtest note at `DMR_OVER_AR` ("a shotgun is not taken over the AR either") and `test_reach_loadout`'s Halo 4 case. Counted as one at first by Reach's list, that test failed.
- Checked through `upgrade_point` and `drop_slot`:
  - Halo 4, Normal, Heroic, Legendary and Demon: sword, hammer and SAW taken from BR + AR (the AR dropped) and BR + Boltshot (the Boltshot dropped).
  - A loaded SAW or sword carried is not traded for the other; an empty one is.
  - With a sword and rockets lying there, the rockets.
  - Easy keeps its walk-over reach (`ON_THE_WAY`): a gun 3 u off is not taken.
  - Reach: shotgun, sword, hammer, Plasma Launcher and sniper taken from DMR + AR (as before), and a sniper carrier passes a shotgun. Halo 3 as before.
- Validation: `tools/test_needle_over_dmr.py` +3 (Halo 4's three over BR + AR and BR + Boltshot; a power gun carried is not traded unless empty; the better power gun wins), 11 in the file. All 597 regression tests pass (with other work in progress in the tree). Gameplay is untested.

### Grenade Launcher and Concussion Rifle take the AR's place, power guns still first, 2026-11-12

- The owner, Nov 12: "I do want every weapon to pretty much outweigh the ar combo. So raise the concussion and grenade launcher scores. And the distance scores can be raised to 100 for close and medium".
- Before: from DMR + AR (Reach) or BR + AR (Halo 4) they added -0.06 to -0.09, never picked up.
- `brain/bot.py`:
  - `BANDS`: Short and Medium 1.0. The Grenade Launcher was (0.4, 0.9, 0.4, 0.1), the Concussion Rifle (0.6, 0.8, 0.3, 0.05).
  - `RANK_GAME`: Reach's Grenade Launcher and Concussion Rifle 3.5 (were 3.0 and 2.8), Halo 4's Concussion Rifle 3.6: the rifle's beside them, no higher.
  - `OVER_AR_GUNS`: to a bot carrying an AR, a loose one is worth the game's bar + `OVER_AR_MARGIN` 0.005 (`upgrade_point`), and `drop_slot` gives up the AR. Not while a power gun (`NEEDLE_YIELDS_TO`, or rank 4.0 and up) lies within reach.
- Tried first and dropped: ranks 3.6 (Reach) and 3.85 (Halo 4) got them picked up (+0.10), but their rank's pull took most of a power gun's. Carrying one with a rifle, a sniper, fuel rod, gravity hammer, Focus Rifle, Plasma Launcher or Shotgun (Reach), or a Railgun, fuel rod, sword, hammer or SAW (Halo 4), lying there was left.
- Checked through `upgrade_point` and `drop_slot`:
  - Reach, both guns: taken from DMR + AR, AR + Magnum and Needle Rifle + AR (the AR dropped), Plasma Repeater + Plasma Pistol (the Repeater) and DMR + Magnum (the Magnum).
  - Halo 4, Concussion Rifle: taken from BR + AR, DMR + AR and Light Rifle + AR (the AR), and BR + Boltshot (the Boltshot).
  - Power guns: never dropped for one. With one carried beside a rifle, rockets, sniper, laser and sword are still taken. With both lying there, the power gun.
  - Left: in Reach a Grenade Launcher a step nearer is taken over a Shotgun or Plasma Launcher (its Short 1.0 now matches theirs), and one carried is not swapped for them.
- Seen, not changed: in Halo 4 a bot on BR + AR takes no sword, gravity hammer or SAW (they add 0.07-0.08 to the AR's 1.0 Short, at the 0.08 bar). Demons get them by `power_grab`.
- Validation: `tools/test_needle_over_dmr.py` +2 (both take the AR's place in Reach and Halo 4; a power gun comes before them, carried, lying beside them, and never dropped). 8 in the file. All 594 regression tests pass (with other work in progress in the tree). Gameplay is untested.

### Reach: bots take a Needle Rifle over a DMR, but not over a power weapon, 2026-11-12

- The owner, Nov 12: "I want bots to pick up the needler rifle over a dmr cause its better. but I dont want them to pick it up over a power weapon".
- Before: rank 3.0 (the general table), bands 0.6/1.0/0.9/0.5, against Reach's DMR 3.5 with 0.6/1.0/1.0/0.7. From DMR + AR a Needle Rifle added -0.045, under Reach's 0.05 bar.
- A higher rank alone was no good. At 3.8 it replaced the DMR (+0.075), but from Needle Rifle + AR a sniper, fuel rod or gravity hammer then added only 0.02 (the power pull counts only the top-ranked gun), and the Focus Rifle, Plasma Launcher and Shotgun lost to it.
- `brain/bot.py`:
  - `NEEDLE_OVER_DMR` {"reach"}: a loose Needle Rifle is worth `NEEDLE_SWAP_GAIN` 0.055 to a bot carrying a DMR (`upgrade_point`), and `drop_slot` gives up the DMR for it.
  - `NEEDLE_YIELDS_TO` (rockets, sniper, Focus Rifle, Spartan Laser, fuel rod, Plasma Launcher, sword, gravity hammer, Shotgun, Grenade Launcher, Concussion Rifle): with one of them lying within reach, the Needle Rifle has its own gain only.
  - `RANK_GAME["reach"]["needle_rifle"]` 3.5, the DMR's (no power pull).
- Checked through `upgrade_point` and `drop_slot`:
  - DMR + AR takes it and drops the DMR; AR + Magnum drops the AR; Needle Rifle + AR leaves a DMR lying there.
  - Carrying a power gun + DMR, it drops the DMR and keeps the power gun.
  - From Needle Rifle + AR, every power gun is taken but the Grenade Launcher and Concussion Rifle (not taken from DMR + AR before either).
  - With both lying there, the Needle Rifle a step nearer, the power gun is taken.
- Validation: new `tools/test_needle_over_dmr.py`, 6 tests. All 576 regression tests pass (with other work in progress in the tree). Gameplay is untested.

### Bots answer the owner's Falcon and pickups; carriers ride; no Demon in a Ghost, 2026-11-12

The owner: "when I drive the falcon no bot enters it tell me why, also bots don't get in a warthog or mongooses passenger when carrying the bomb or flag. And finally make demon bots not drive ghosts".

- **The Falcon** (live Forge World Slayer 20261112-200003, flights at 98-113 s and 583-604 s, nobody ever aboard):
  - Bots are called aboard a person's aircraft only once it is set down (`landed_aircraft`), when he stops by them (a honk), or when the bot's own trip is 25 u or more (`rider_calls`). In the air, nobody is called.
  - First flight: he set down at 108 s. Two bots were sent to its guns at 109.5 and 111.5 s, and he died at 113 s.
  - Second flight: a Blind bot had given up on that Falcon at 576 s while it stood parked out of reach ("no way to it", a 30 s ban). From 584 s it ignored every call onto its gun, even after the Falcon set down 11 u away (596-602 s).
  - Of the others, one was on its way to drive another vehicle and one was Easy, which takes no calls.
- **Fixes:**
  - `Bot.veh_banned`: the ban keeps where the vehicle stood and ends once it has moved 4 u (`VEH_BAN_MOVED`).
  - `director.honk_orders`: a person's aircraft set down calls bots from 20 u (`LAND_CALL_R_PERSON`), not 10.
- **Carriers** (live Breakpoint 20261112-193700, 306-321 s): the owner's Warthog stood 1-4 u from our Easy bomb carrier, who never got in.
  - A carrier was put in a vehicle only by a bot driver (`ferry_orders`) or by a honk, which Easy refuses (`set_order`).
  - New `director.person_pickup`, run first in `ferry_orders`: a person at the wheel of a ground vehicle with a passenger seat free, within 8 u of our carrier bot (flag or bomb, 30 u or more from where he scores), gets him into the passenger seat. Easy is included, its order set outright as `ferry_orders` does. Never a tank, never with the person on a gun.
- **Demon and the Ghost:** `vehicles.DEMON_NO_DRIVE` adds the Ghost, in every game, Race laps excepted.
  - The director never sends a Demon to one; Normal and Heroic go first (`driver_priority`).
  - A Demon put at a Ghost's controls gets out, as at a Warthog's.
- Validation:
  - `tools/test_demon_no_drive.py` and `tools/test_demon_vehicles.py` updated: Ghost on the list, a Demon never sent to one, Heroic drives it, a Demon at its controls gets out, a Demon still drives a Scorpion.
  - `tools/test_wheel_and_one_bomb.py` adds the carrier pickup (Easy gets in; not from 15 u, not into a full Warthog, not with the person on the gun) and the ban ending once the Falcon moves.
  - All `tools/test_*.py` pass (570 tests).
  - **Untested in game:** whether Reach and Halo 4 seat a flag or bomb carrier bot in a passenger seat.

### A driver for a person on a driverless gun; One Bomb's sides swap each round, 2026-11-12

The owner: "Check the bug report" (Blood Crash CTF 20261112-164125, F9: "Whya re they not driving me") and "on breakpoint a bot on my team second round of assault got stuck for a long time carrying bomb" (Breakpoint 20261112-193700).

- **Blood Crash, 189-209 s:** the owner sat on a Warthog's gun with nobody at the wheel.
  - The vehicle counted as taken, so the empty-vehicle driver picks (`crew_orders`) skipped it.
  - `rider_calls` counted the empty wheel as a free seat and called two bots into the one passenger seat. One got in and sat; the other stood beside it.
- **The fix:**
  - `brain/vehicles.py` `wheel_open`: a vehicle whose riders are all on its guns. A person in a passenger seat cannot be told from a driver, so only guns count.
  - `brain/director.py` `wheel_calls`, run before `rider_calls`: when a person rides such a gun, the bot on foot within 30 u best to drive (`driver_priority`: Normal and Heroic first) is sent to the wheel, as a honk. Never a Demon at a Warthog's or Mongoose's wheel, never Easy, never the flag carrier. A bot that has not got in after 15 s is skipped for 30 s and the next one is tried.
  - `rider_calls` no longer counts that wheel as a passenger seat.
  - `brain/bot.py`: a bot sent there may walk to and enter the driver's seat of a teammate's vehicle while `wheel_open` holds. Before, any occupied vehicle was "taken" for a driver.
- **Breakpoint, round 2:** One Bomb picked the attackers by the bomb stand's team in the map data (team 1), but Reach swaps sides each round.
  - In round 2 team 0 attacked, and its target goal was the one removed as "the attackers' own".
  - Its carriers had no goal and walked to `carry_point`'s fallback, the map's mid (-10.85, -12.79). Two Easy bots held the bomb there from 274 to about 370 s.
  - The loose bomb also read as the other team's, so no non-Easy bot of ours went for it.
- **The fix** (`brain/modes.py` `Watch.bomb_attackers`):
  - The attackers are the bomb carrier's team, kept while the bomb lies loose away from its stand.
  - With the bomb on its stand, the attackers are the team whose living players are nearer it by 8 u or more (they spawn by it).
  - The goal is the one far from the stand, for the defenders. The bomb belongs to the attackers, and an armed bomb is the defenders' to disarm.
  - The stand's team is still used until a side is seen. With no stand, the old rule applies.
- Validation:
  - New `tools/test_wheel_and_one_bomb.py`: the owner on the gun gets a Heroic driver; no Demon or Easy; a person who may be driving and a vehicle with another rider are left alone; too far is not called; the attacking side follows round 1, round 2 and a carrier; an armed bomb is the defenders'.
  - All `tools/test_*.py` pass (565 tests).
  - **Untested in game:** whether Halo 4 and Reach seat a bot at the wheel of a vehicle a person rides the gun of, and the round 2 side detection in a live match.

### Easy, Normal and Heroic react faster and answer the man shooting them, their aim unchanged, 2026-11-12

The owner: "make all difficulties from easy to heroic react faster. That doesnt mean make them better ... its a little unrealistic that when you shoot at a bot it just doesnt shoot back ... raise their base reaction times up, but keep their accuracy settings", then "Make the changes".

- **Base reaction** (`brain/profiles.py` `REACTION`, a share of a good human's 0.22 s; each bot's is jittered 0.9-1.1 and each reaction drawn log-normal around it, as before):
  - Easy 0.275 s → 0.22 s (1.25 → 1.0).
  - Normal 0.22 s → 0.194 s (1.0 → 0.88).
  - Heroic 0.187 s → 0.172 s (0.85 → 0.78).
  - Legendary (0.154 s), Demon, Blind and Scaling unchanged. Tactician's reaction was the halfway point of Heroic's and Legendary's; it is pinned at its old 0.1705 s (`TACTICIAN_REACTION`), its other hands still halfway.
- **The man shooting them** (`profiles.arc_spot`, `brain/bot.py` `Perception`): Easy, Normal and Heroic took 1.6× their reaction to recognise anyone past the centre of their view (35°). For the enemy hurting them in the last 1.5 s that delay is gone, as a player follows the HUD's damage arc. It also applies to when they notice who a new shooter is (`hurt_by`'s `attacker_notice`, which lets Normal and Heroic turn on him mid-fight). Every other man at the edge of the screen keeps the delay, so first-sight duels are not quicker. Legendary, Demon, Blind, Tactician and Scaling unchanged.
- Roughly, from a hit 90° to the side to the start of aiming (turn plus recognition, typical values): Easy ~0.9 s → ~0.65 s, Normal ~0.65 s → ~0.5 s, Heroic ~0.55 s → ~0.4 s.
- **Unchanged**: aim error, lag, tracking, flick, overshoot, lead, the looser trigger, turn speed (Easy's 270°/s), memory, radar, teamwork and every tactic.
- Validation: new `tools/test_reaction_speed.py` (the base values and their order; aim tables unchanged; which tiers lose the delay; the shooter found 1.6× quicker at 45° for Easy-Heroic, Legendary the same). `tools/test_tactician_difficulty.py` expects the pinned reaction. All 56 `tools/test_*.py` files pass. **Untested in game.**

## 0.2.2-custom.11 — the first public installer: Team Slayer high ground, CTF cut-offs, Blind and Tactician, Bot Matchmaking, MCC nameplates and ranks, 2026-11-12

The first release published for others to download: `ProjectProvingGrounds-Setup-0.2.2-custom.11.exe` on this repository's Releases page (tools/build_installer.py, adapted from upstream's: the code, the built mod, the map tools, a bundled Python and the map pack in one Setup). The launcher's update check now reads this repository's releases and `CUSTOM_VERSION` (tools/updater.py, tools/launcher.py), so an install is never offered upstream's Setup over the custom bots. README.md says it is a custom build and links here.

### The BOTS panel's Remove all closed MCC: ImGui used from two threads, 2026-11-12

The owner: "I got a game crash after clicking remove all bots. See if you can track it down".

- **What the PC kept**: nothing that names the crash.
  - No Windows Error Reporting event or dump, and no Unreal crash report in `LocalLow\MCC\Saved\Crashes` (the last is from April).
  - The botcore log ends at the lobby probe, with no fault line.
  - `botcore.ini` still held the 11 bots from the post-match rotation (10:16:00). Remove all never saved, so MCC closed before the confirmation's frame finished.
  - A C runtime assert ends a process that way: its dialog, then an exit, with no report. The DLL that was running (`botcore_netwatch1.dll`) has asserts compiled in (build.bat does not define NDEBUG).
- **The panel itself is not it.** A scratch driver links the real `bots_panel.cpp` with ImGui, its asserts on, and loads the crash's own data: botcore.ini, the 899-name pool, the profiles, and MCC's nameplates and ranks. It clicks the toolbar's Remove all, then the confirmation's. No failure: the list empties and saves.
- **The cause found**: ImGui is not thread safe, and the overlay used it from two of MCC's threads.
  - `h_present` draws frames on the render thread, while `wndproc` calls `ImGui_ImplWin32_WndProcHandler` (mouse, keys) on MCC's window thread. A click that arrives while a frame reads ImGui's input queue tears it.
  - The same driver, with a second thread sending mouse events at 1000 Hz as the window thread does, failed ImGui's check `i >= 0 && i < Size` (imgui.h:2282, the C runtime's assert) within 1-6 s, in four runs.
  - This is not proven to be this exact crash, since nothing was recorded. It is the only failure found that ends MCC this way.
- **The fix** (`native/overlay.cpp`):
  - `g_imgui_lock`: one lock around every use of ImGui on either thread. It covers the frame (NewFrame to RenderDrawData), the setup, and the routing of window messages (`wndproc_route`). MCC's own window procedure runs after the lock is let go. With the lock, the driver ran 150 s at 1000 Hz (60,000+ frames) and 150 s flat out (140,000+ frames) with no failure.
  - `native/imgui_checks.h` (build.bat `/I. /DIMGUI_USER_CONFIG`): in botcore.dll, a failed ImGui check writes `imgui check failed: <check> (<file>:<line>)` to the botcore log, once a place, and MCC goes on. The new DLL holds none of the C runtime's assert dialog. The tests and the preview builds keep ImGui's own assert.
  - A fault while drawing is now logged (`overlay: fault <code> while drawing`) and the lock let go. Nothing of the overlay is left holding MCC's cursor or pad.
  - The overlay is then made again, without hooking MCC's window a second time. Upstream's restart hooked it again, and every message would have called itself without end. A third fault turns the overlay off until MCC restarts.
  - A fault while routing a window message is logged, and the message is passed to MCC.
  - The log now says which thread draws and which gets the window messages.
- Validation:
  - `native\build.bat imguilock` built `native/bin/botcore_imguilock.dll` (not in Git) from the working tree, which includes the uncommitted Reach netwatch logging, as `botcore_netwatch1.dll` did.
  - All 55 `tools/test_*.py` files pass, and the pool checks pass.
  - The driver is a scratch tool, not in Git.
  - Untested in game: restart MCC to load the new DLL.

### Reach: network watch log, for bots in custom games with a friend, 2026-11-11

The owner: a friend joined his Reach custom game (anti-cheat off) and "could see and shoot the bots. They just slide around no animations his own team showed as enemies, but played perfectly for me"; "I want to make it multiplayer compatible."

- **Likely cause, from the code (not confirmed yet):** `hr_add_bot` makes each bot with the game's `player_new_at` on the host only, giving it the host's machine, not through the session that tells every machine who is in the match. The friend's game would then get the bots' bodies with no player behind them: no team, and no movement or aim state to animate.
- **First step, read only:** `native/reach.cpp` `hr_net_watch` / `hr_net_dump`, called each players-update tick. It writes `netwatch` lines to the botcore log: "netwatch first tick" once (the hook runs on this machine), then a snapshot every 10 s, and at most once a second when the live players or bipeds change. Each live player gets its index, handle, flags, machine, team (+0xAC), unit and name. Each biped gets its handle, position, the player whose unit it is, and the offsets in its first 0x600 bytes holding a live player's handle (the unit's own player link, not mapped in Reach yet). It writes nothing to the game, and the panel's status line is kept as it was.
- The plan: the host and the friend each play one Reach custom game with bots, the friend with bots off; their two logs say whether his machine has players for the bots at all, and which unit field ties a body to its player. That decides the fix: the bots joining the session, or the host's mod telling the friend's which players to make.
- Validation: `native\build.bat netwatch1` built `native/bin/botcore_netwatch1.dll` (not in Git) with no new warnings. All 55 `tools/test_*.py` files pass (none covers this). Untested in game, on either machine.

### Bots wear MCC's account rank badges by difficulty, 2026-11-11

The owner: "Look up all of mcc ranks and instead just give a bot a random ranking emblem like i have based on their difficulty. So demon gets the max or close to max and the other bots fill based on the difficulty".

- **Found in MCC's files**: the badge beside a player's name is MCC's account rank, a tour's shield with the level's insignia on it (his: "Tour 6, Level 26 Colonel"). It is not in `Data\UI`; it is in MCC's Unreal pak, `MCC\Content\Paks\MCC-WindowsNoEditor.pak` (version 7, index not encrypted).
  - `UI/Shared/Textures/AccountLevelProgression/T_Im_*`: 30 insignia and 11 tour shields, 512x512 BGRA, stored uncompressed.
  - `UI/Features/Nameplate/DA_AccountProgression` (MCCAccountProgressionData): 30 levels (1 Rookie .. 26 Colonel .. 30 General, each its icon) and 11 tours (Prestige 0-10 with the icons Tier11 down to Tier01). The last tour, the gold eagle, has no levels (HasLevels false).
  - (The numbered 1-50 icons in `Data\UI`'s texture pack are the playlists' skill ranks, not these.)
- **`tools/mcc_ranks.py`** reads the pak's index, decodes DA_AccountProgression's tagged properties through the package's name map, and writes `native/bin/ranks` (game data, not in Git): tour_01-11 and level_01-30 at 128x128, and `index.txt` (tour=<n>|levels or max, level=<n>|<name>, the names from the icons with their spelling put right). If the asset cannot be read, it falls back to the order it held in Nov 2026.
- **The panel** (`native/bots_panel.cpp` `ranks_frame`, `bot_rank`, `rank_badge`): when `native\bin\ranks` is missing, the extraction runs in the background from the MCC folder the nameplates found, and the ranks are read once it is there.
  - A bot's rank is drawn from its name and difficulty, the same every match while its difficulty is. Tours by difficulty (`RANK_TOURS`): Easy 1-2, Normal 2-4, Heroic 4-6, Tactician 5-7, Scaling 5-8, Legendary and Blind 6-9, Demon 10-11. Demon gets the eagle (the top) or tour 10 at level 20 or over (near General). The other tours take any level 1-30.
  - The badge is the tour's shield with the level's insignia at 58% on it (none on the eagle), as his own is drawn.
- **Shown**: the lobby's rows (`overlay.cpp`) draw the badge left of the team bar, where MCC puts the player's. The bot card adds CURRENT LEVEL ("Tour 6, Level 26", the rank's name, the badge), as MCC's Player Details shows a player's.
- Validation: new `tools/test_mcc_ranks.py`, 4 tests. They check the names, and against this machine's MCC: pak version 7, the 30 levels and 11 tours read (his Tour 6 the gold spear shield, the eagle with no levels), and an extraction of 41 pictures with `level=26|Colonel`. `native/pool_test.cpp` checks `bot_rank` for 8 names: Demon in tour 11 (no level) or tour 10 at level 20+, the same each time; Easy, Heroic and Legendary in their tours. All checks pass and all 55 `tools/test_*.py` files pass. A mock of his bots' rows with their badges was drawn on his recording's slide-out frame (scratchpad). `native\build.bat ranks2` built `native/bin/botcore_ranks2.dll` (not in Git). Untested in game.

### Nameplates found: MCC's folder matched in any case, 2026-11-11

The owner, after the first live run: "It did not work. Still no nameplates."

- `botcore_nameplates.log` and the running process showed the cause. Steam runs MCC as `...\mcc\binaries\win64\mcc-win64-shipping.exe`, in lower case. `nameplates_load` looked for `\MCC\Binaries\` as written, so it found no folder, read no catalog and gave no bot a nameplate anywhere. The tests had handed it the folder directly.
- `native/bots_panel.cpp` `mcc_root_of` finds `<MCC>\` from the exe's path in any case. `native/botcore.cpp` logs `nameplates: <n> of MCC's, from <folder>` (or why none) at start.
- Validation: `native/pool_test.cpp` checks `mcc_root_of` on his real lower-case path, the usual case and a path that is not MCC's (all checks pass). All 54 `tools/test_*.py` files pass. `native\build.bat nameplates2` built `native/bin/botcore_nameplates2.dll` (not in Git). Untested in game.

### Bots wear MCC's own nameplates: the lobby's rows, their card, the editor, and MCC's screens, 2026-11-11

The owner: "would you be able to locate the games files and give them actual player cards and emblems inside the games menus?"

- **Found in MCC's files**: each player's nameplate (the card behind the name: a square for the emblem on its left, the art behind the name) is a PNG, `<MCC>\Data\UI\NamePlates\Images\<image>.png` (360x52, 540 of them). They are listed in `<MCC>\Data\UI\playercustomization.xml` (`<Nameplate id image allow_team_color>`, 531 with their picture there). The emblems the bots wear were already MCC's (`tools/emblems.py`, from the same catalog and its texture pack).
- **Read from the running MCC's own folder** (`native/bots_panel.cpp` `nameplates_load`, botcore at start: its exe is `<MCC>\MCC\Binaries\Win64`), nothing copied into the project. The PNGs are decoded with Windows' own WIC (`png_rgba`; `build.bat` links `ole32.lib windowscodecs.lib`) and kept as textures, so a full cache lets go of the lobby's emblems and nameplates (Bot Matchmaking shows new bots all evening).
- **Each bot's** (`bot_nameplate`): picked in the bot editor (its profile's `mcc.nameplate`), else drawn from its name (the same every match), never the blank one. A picked number MCC does not have falls back to its own.
- **Shown**:
  - The lobby's rows (`overlay.cpp` `draw_session`): the nameplate is the row's card as MCC draws a player, the emblem in its square, a dark edge under the name for the light ones, and the plain ones (MCC's team-colour ones) in the team's colour.
  - The bot card adds NAMEPLATE with its card, emblem and name.
  - The bot editor has Nameplate beside the clan tag: arrows through MCC's nameplates in its order, the card shown, "Its own" back to the drawn one. The clan tag's hint went to its tooltip.
- **MCC's own screens** (`native/report.cpp` `h_profile`): the player lookup the mod already answers for bots (emblem, clan tag, service tag) now gives each bot's nameplate too, so MCC's scoreboards and post-game report draw it behind the bot's name. The offset was read from MCC's unknown-player fill (FUN_140249418): the emblem's five at +0x00 to +0x10, then 6 at +0x14 and 1 at +0x18. Avatar 6 is MCC's free default and nameplate 1 its blank one, so +0x18 is the nameplate.
- **Not possible this way**: MCC's own MY GAME SESSION list still holds only the player. The bots there are the mod's drawing, now on their real nameplates.
- Validation: `native/pool_test.cpp` checks against this machine's MCC (or `MCC_ROOT`; skipped without one). All pass, including: 531 nameplates, the blank one first and team-tinted, MadPistol's (72) the same in any case and its PNG read at 360x52, a picked one taking over, and one MCC lacks falling back. `tools/test_bot_matchmaking.py` adds the wiring test, including the brain's looks ignoring `mcc.nameplate` (10 pass). All 54 `tools/test_*.py` files pass. A mock of the rows on their nameplates was drawn on his recording's slide-out frame (scratchpad). `native\build.bat nameplates` built `native/bin/botcore_nameplates.dll` (not in Git). Untested in game: MCC's scoreboards and post-game report drawing the nameplates, and the editor's picker.

### The session list's bots can be picked: their menu and a Player Details card, 2026-11-11

The owner, on MCC's own list: "they can become inspectable, seeing their armor rank etc"; clicking his name gave MCC's player menu (Player Details, Find Player, ...) and Player Details his career screen.

- **Picking a bot** (`native/overlay.cpp` `draw_session`): a bot row under the mouse lights up as MCC focuses a player (a lighter box, a white frame), and a click opens its menu. Mouse only: MCC's own pad and keys move through its list, which does not hold the bots.
- **Its menu** (`draw_bot_menu`): MCC's player menu, a panel down the right side (measured from his screenshot with his own name picked).
  - It shows the bot's name and clan tag, "<difficulty> bot - <team>", and PLAYER DETAILS, SWAP FOR NEXT BOT (with Bot Matchmaking on, not in Firefight) and BACK.
  - A click off it, Esc or the pad's B closes it. The click that opened it is not taken as a pick in it.
- **SWAP FOR NEXT BOT** (`native/bots_panel.cpp` `bot_pool_swap`): that seat takes the next pool bot, never itself or a seated one. It brings its saved settings, else the difficulty the other unsaved seats share (else the "for everyone" deal) and any play style. Nothing free keeps the seat. It is written at once.
- **Its card** (`bot_card`, `overlay.cpp` `draw_card`): full screen, laid out as MCC's Player Details screen.
  - PLAYER DETAILS over the bot's name and clan tag, and its emblem large.
  - DIFFICULTY, PLAY STYLE, TEAM and BOT MATCHMAKING (whether it keeps its settings).
  - The difficulty as a rank in the top right, a ring in the tier's colour with its chevrons.
  - The bot itself in 3D in the lobby's game, the bot editor's model, turning (drag to turn it). "Getting its look ready..." shows while its look is exported, and a bot with no profile gets one (`profile_ensure`, its look unchanged).
  - Back, Esc or the pad's B closes it and its menu.
- **Input**: while a bot's menu or card is open, MCC gets no keys, clicks, raw input or pad, and its cursor is held where it was (like the BOTS panel). Esc closes the card and menu without reaching MCC (its release eaten too). A click on a bot row never reaches MCC. The BOTS tile is not drawn under an open menu, and the B key does not open the panel then. Opening the panel or leaving the lobby closes them.
- Validation: `native/pool_test.cpp` adds the swap's checks (the next bot, a saved bot's settings, the table's difficulty otherwise, wrapping past a seated one, nothing free keeping the seat): all pass. `tools/test_bot_matchmaking.py` adds the wiring test (9 pass). All 54 `tools/test_*.py` files pass. Mock-ups of the menu (on his recording's frame) and the card were drawn at the code's coordinates (scratchpad). `native\build.bat botcard` built `native/bin/botcore_botcard.dll` (not in Git). Untested in game: the clicks and input capture in MCC, the 3D view on the card, and the menu's fit over MCC's slide-out.

### Bot Matchmaking keeps a name's repeats in the queue; the owner's Call of Duty bot list added, 2026-11-11

The owner: "This is the bot.txt file I want to use integrate it in with the names we already have ... Leave all of the duplicates. And all of these names I posted I want to be Legendary, or Blind. Excluding the first Row ... these bots will all be demons."

- **Repeats kept** (`native/bots_panel.cpp` `bot_pool_load`): a name listed more than once in `bot_pool.txt` stays in the queue each time, as his Call of Duty name file has it, so that bot comes up more often. `pool_take` still never seats one name twice at once (a repeat already seated is passed over). A new pool's header says so, and the Settings line reads "names in your pool".
- **His list** (local data in `native/bin`, not in Git; merged by a scratchpad script, `bot_pool.txt` and `bot_pool_saved.ini` backed up there first):
  - `bots.txt`'s 839 names (692 different) were added in its order after the pool's 60, under a `# Call of Duty Bots-to-Humans list` note.
  - The 16 names of his first row are saved as Demon. His other 61 named bots are saved as Legendary (30) or Blind (31), drawn once with a fixed seed and kept. Every named bot was in the file. Play style is any.
  - 47 of the file's names are over the game's 15 characters and are cut there, e.g. `oO Savage Pigeon Oo` becomes `oO Savage Pigeo`.
- Validation: `native/pool_test.cpp` now checks that a repeat is kept and is seated when its turn comes, and that one name never sits in two seats (all checks pass). All 54 `tools/test_*.py` files pass. `native\build.bat cod` built `native/bin/botcore_cod.dll` (not in Git). Untested in game.

### The first bot row no longer touches the player's row, 2026-11-11

The owner, with a 16-player slide-out screenshot: "Even out my tab from theres. the next players clips into mine."

- His own row with its light-blue focus line reaches y 131 (1080 units), and the first bot row started at 132, flush against it. Bot rows keep 6 between them (44 high, 50 apart).
- `ui_layout.h` `mcc_session_row`: the bots' rows start at 87 + 50k (the first at 137), 6 under his row like the gaps below. His own row stays 82.
- Checked by outlining the new rows on that screenshot: the gaps are even. `tools/test_bot_matchmaking.py` holds the line (8 tests pass); all 54 `tools/test_*.py` files pass. `native\build.bat lobbyrows4` built `native/bin/botcore_lobbyrows4.dll` (not in Git). Untested in game.

### The session list's bots follow MCC's list: the slide-out, a picked player, and the right height, 2026-11-11

The owner, with a 6 s recording (2556x1436) after the first live run: the bots showed under him in the lobby's corner, but "if I hover to the right side of the screen new ui shows up ... The second ui keeps all the player on there as well". The recording (frames through Windows' MediaComposition, scratchpad) showed the rows drawn in the corner, the first one over the bottom of his own row, and nothing in the slide-out.

- **Measured from the recording**, a nearly full-screen capture (the screenshots behind the first numbers were cropped about 7 units at the top: the tile row, 158 by `ui_layout.h`, read 151 there):
  - The player's box is y 82-126, 332 wide, right-aligned with the header (y 36-72).
  - Its right edge is at 1903 in the lobby's corner, 1879 in the slide-out (the cursor at the right edge) and about 1291 with a player picked (the list moved to the middle).
- **Found on screen** (`overlay.cpp` `probe_session`): every 4th frame in a lobby's menus, a strip of the back buffer across y 78-87 is read.
  - The longest run of light pixels (r, g and b over 140), 120 units or longer and ending past x 600, is the player's box's bright top edge, and its right end is the list's right edge. The edge fades to the left, so the right end is the sure one.
  - It is cleared after two misses running, and outside a lobby's menus.
  - Run on the recording's frames and the screenshots with the same rules (scratchpad `probe_sim.py`): 1904 in the corner, 1880 in the slide-out, 1291 picked (on the crop-corrected screenshot), and none on Player Details.
- **Drawn there** (`draw_session`; `ui_layout.h` `mcc_session_row(H, x1, k)`, `mcc_session_header`, `mcc_session_bar_x`, `mcc_session_probe_y0/1`, `mcc_session_box_w`):
  - The rows are drawn wherever the list stands, in the lobby's menus, whenever the probe finds the list and the BOTS panel is shut. No longer only with the lobby's tile row in sight, which the slide-out blurs.
  - Rows are y 82 + 50k, 44 high, 332 wide from the found edge; the team bar is 346-334 left of it.
  - This places them in other titles' lobbies too, where the list stands as in Halo 4's (unchecked).
- Validation: `tools/test_bot_matchmaking.py` adds the probe and layout checks (8 tests pass). The pool test passes 14 checks. All 54 `tools/test_*.py` files pass. `native\build.bat lobbyrows3` built `native/bin/botcore_lobbyrows3.dll` (not in Git). Untested in game: the probe on the live buffer (its colours there, not a video's), the slide-out's animation, and other screens with a long light line at that height (the post-game report).

### Every lobby bot can be dressed and saved; the bots listed under the player in MY GAME SESSION, 2026-11-11

The owner: "Can we make it to where the bots that are in the 'lobby' that are loaded in will show on the bot profile page? I want every bot I edit to save their difficulty playstyle armor everything. If I edit them. But I want them to be viewable at the time of them being in my lobby. ... I would like them to show as a 'real player' In my lobbys game session under my name which is always the top one."

- **Settings > Bot profiles shows the lobby** (`native/bots_panel.cpp` `mod_settings`):
  - The page lists the bots in the next match (the lineup, up to 15), not the install's 15. Each bot shows its team colour, clan tag, name, difficulty and play style.
  - Picking one opens the bot editor. The Bots tab inspector has "Edit look and clan tag", which opens the same editor for the selected bot.
- **Any bot gets a profile** (`profile_ensure`, `name_look_seed`, `profile_index`):
  - A bot with no profile (a pool bot) gets one when its editor opens. It is written to `bot_profiles.ini` after the install's 15, with the look seed the brain already gives it (`brain/looks.py` seed_of: zlib CRC-32 of the lower-case name) and no clan tag, so its armor and emblem do not change until something is changed.
  - Its armor, clan tag and name are saved like the 15's. Its difficulty and play style are saved by Bot Matchmaking (`bot_pool_saved.ini`).
  - Profiles go up to 1024 (`PROF_MAX`, was 32). The profile view's look cache is a vector (was 192 lines), and the texture cache holds 256 (was 64).
  - The Re-roll draws the install's 15 again and keeps every bot dressed beyond them, hand-set looks included. A new name equal to a kept bot's yields to the kept bot.
- **Renaming in the editor** (`bot_pool_rename`, `bot_pool_has`): a pool bot's line in `bot_pool.txt` (the first of that name; every other line, note and the order as written) and its saved settings follow the new name. A name already in the pool is refused, like a name already in the profiles.
- **MY GAME SESSION** (`native/overlay.cpp` `draw_session`, `native/ui_layout.h` `mcc_session_header` / `mcc_session_row` / `mcc_session_bar_x`):
  - The lobby's bots are drawn under the player's own row (MCC's, always first) as MCC draws a player: the team's colour bar, a box in the team's colour, the bot's MCC emblem, its clan tag (`[ ]` with none, as MCC shows it) over its name. The header shows the session's count (8/16; Firefight /4).
  - Shown while the lobby's tile row is on screen and the BOTS panel is shut, with bots on and not in LiDAR mode. The rows fade in one after another when the lineup changes (Bot Matchmaking seating the next bots).
  - This is the mod's drawing, like the BOTS tile: MCC's own session still holds only the player, because adding fake members to its network session could stall the match start. The bots join as the match loads, as before.
  - Measured from the owner's Halo 4 lobby screenshot (about 2000x1115) in the header frame (anchored right, scaled by height): rows 50 units apart from y 75, 45 high. Checked by drawing the rectangles and a mock of the rows on that screenshot.
- **Emblems for pool bots** (`bot_emblem`, `bot_emblems_frame`; `tools/looks_export.py --emblems profiles.ini NAME...`): a bot with no emblem picture gets one drawn in the background, then picked up. One that cannot be drawn (no emblem art extracted) shows a plain badge and is not asked for again.
- Validation: `native/pool_test.cpp` adds 4 checks (14 in all pass): the look seed equals Python's for three names, a new profile written with that seed and no clan and one per name, the Re-roll keeping a dressed pool bot's clan and hand-set armor, and a rename carrying the pool line (notes and CRLF kept) and saved settings. `tools/test_bot_matchmaking.py` adds 3 tests (7 pass): the brain's seed and clan for those names before and after the profile line, `--emblems`, and the page and rows wiring. All 54 `tools/test_*.py` files pass. `native\build.bat lobbyrows2` built `native/bin/botcore_lobbyrows2.dll` (not in Git). Untested in game: the rows' fit at other window sizes and in the other games' lobbies, the editor on a new pool bot, and the page's layout.

### Bot Matchmaking: a pool of bots, each match's seats filled from it in queue order, 2026-11-10

The owner: "I have a call of duty mod with bots that can switch between 1-1000 bots per match due to a name que file"; "I would like every bot to be able to be customized and saved"; "if we just did like 50-60 bots right now to see if it works can I just add the other 900 later manually? ... And add an option in the menu that allows me to turn off 'Bot Matchmaking'".

- **The pool** (`native/bots_panel.cpp`, `bots_panel.h` `bot_pool_*`):
  - `native/bin/bot_pool.txt` has one name per line, in queue order. It is made on first use with 60 bots: the 15 profiles, then made-up names from the panel's own name maker.
  - Names are cut to 15 characters (the game's name field) and kept to printable ASCII without commas. A UTF-8 BOM is dropped, a repeat in any case is skipped, and lines starting `#` or `;` are notes.
  - The file is re-read before each rotation (and by the Settings tab's Reload pool button), so names added while MCC runs count.
  - The match still holds 16 players, so a match seats up to 15 of the pool.
- **Saved bots** (`native/bin/bot_pool_saved.ini`: `next=` queue position, `saved=<difficulty>,<style>,<name>`):
  - While Bot Matchmaking is on, changing a bot's difficulty or play style in the inspector saves it to that bot's name, and the bot comes back that way. The inspector says so, with a "Use defaults" button that forgets the saved settings.
  - A bot with no saved line takes the difficulty the unsaved seats share, so an all-Heroic table around a saved Demon stays Heroic. Otherwise it takes the "for everyone" choice dealt by seat. Its play style is any.
  - Looks still come from the 15 profiles, or from the name for every other bot, so each pool bot looks the same every match. A pool bot's look is not editable yet.
- **Rotation**:
  - When a match with bots ends and MCC is back in the menus (`botcore.cpp`: the brain ran, menu 1 to 0; not a Theater film), `overlay.cpp` `pool_after_match` seats the next bots on the panel's own thread (`bot_pool_rotate`). Teams and the number of seats are kept.
  - Rotation is skipped after Firefight (its own 3-bot list), in LiDAR mode and with bots off.
  - A pool smaller than the seats seats every pool name once, and the rest get made-up names.
  - While it is on, `roster_name` takes the next free pool name, so Quick setup, Add bot and Rename fill from the pool, with saved settings.
- **The menu**:
  - Settings tab, under Bot profiles: a "Bot Matchmaking" On/Off switch (on by default; `botcore.ini` `matchmaking=`). With it: the pool's size, how many bots have saved settings, the next five names, where to add names, and Reload pool.
  - Switching it on seats pool bots at once. Off keeps the same bots every match, as before.
  - The Bots tab shows a banner while it is on.
- Validation: new `native/pool_test.cpp` (`native\build_pool_test.bat`) links the real `bots_panel.cpp` and passes 10 checks: a new 60-bot pool, the file's rules, queue order and teams kept, the shared difficulty, a saved Demon coming back and the others at defaults, the position and saved settings surviving a reload, Use defaults, names added while running, a pool smaller than the seats, and the pool used only while on. New `tools/test_bot_matchmaking.py`, 4 wiring tests, including the brain reading the list with the new line. All 54 `tools/test_*.py` files pass. `native\build.bat matchmaking` built `native/bin/botcore_matchmaking.dll` (not in Git), loaded at the next MCC start. `pool_test.exe <bin> make` made the owner's `native/bin/bot_pool.txt` (60 bots; not in Git). Untested in game: the switch's layout, the banner and the rotation after a real match.

### New Tactician difficulty: Legendary's brain, hands between Heroic and Legendary, 2026-11-10

The owner, picking from proposed new difficulties: "Make a tactician first and make its stats between legendary and heroic".

- **Profile** (`brain/profiles.py` `TACTICIAN`, `tactician_hands`, `tactician_profile`, `fixed_tactician`, `own_hands`):
  - Fixed Legendary (tier `top`, extra None, label `tactician`), so every Legendary rule applies: memory 10, radar 1.0, teamwork 0.95, routes, map timing, tactics, awareness, Team Slayer high ground, and Legendary's decision interval, lead and 650 deg/s turn.
  - Its aim and hands (reaction, aim error, lag, tracking, flick, overshoot) are each set halfway between Heroic's and Legendary's base (`TACTICIAN_TOWARD` 0.5), then jittered 0.9-1.1 as every tier's are. Base: reaction 0.171 s, aim error 0.0064, lag 0.0515, tracking 0.0825, flick 0.75, overshoot 0.15.
  - Like Blind, its own hands aim everywhere: `protected_aim` now excludes `own_hands` (Blind and Tactician), so no protected head/turret precision, unerring lead or DMR/sniper head snap. `fight()`'s head-only override reads `own_hands` instead of `fixed_blind`.
  - Still Legendary's, looked up by tier: the head-aim share (0.97), the tight trigger (no loose aim), PRESS 1.0 and the dry-shot count.
- **Native BOTS panel**: tier 7 / difficulty 8 "Tactician" (teal, three chevrons) in `bots_panel` (names, colours, about text, keys, both difficulty pickers between Heroic and Legendary, the inspector's second row, the clamps), `overlay` (`DIFF_NAME[9]`), `botcore` (`difficulty % 9`, `TIERS[9]` launches `--tier tactician`) and `shared.h`. `botctl` keys match; Observer, match export and player stats name it. Mixed's deal is unchanged (it does not include Tactician).
- Validation: new `tools/test_tactician_difficulty.py`, 4 tests (hands halfway, Legendary's game sense under the same seed, own hands, Legendary / Demon / Blind unchanged, the keys and pickers); `tools/test_demon_difficulty.py` updated to 9 codes. All 53 `tools/test_*.py` files pass. `native\build.bat tactician` built `native/bin/botcore_tactician.dll` (not in Git), loaded at the next MCC start. The footer picker keeps its 600 px width with nine buttons, so check the labels fit. Untested in game.

### Mixed difficulty deals Demon and Blind too, 2026-11-10

The owner: "When selecting the menu option for mixed teams. Demon, and blind aren't apart of that selection".

- `native/bots_panel.cpp` `roster_mixed_tier`: Mixed dealt Heroic, Normal, Legendary, Easy in turn. It now deals Normal, Easy, Heroic, Legendary, Demon, Blind. Bots are dealt one at a time team by team, so each pair is two neighbouring ranks with the stronger to alternate teams: red gets Normal, Heroic, Demon and blue Easy, Legendary, Blind. The first four bots are the old four tiers. Scaling stays out (its match-long climb is its own pick).
- The Quick setup hover text for Mixed now reads "A mix of Easy to Demon and Blind, like a real lobby."
- Validation: `tools/test_blind_difficulty.py` adds a test of the deal (all six fixed tiers, no Scaling, the old four first, each pair a rank apart). Both difficulty test files pass. `native\build.bat mixed6` built `native/bin/botcore_mixed6.dll` (not in Git), loaded at the next MCC start. Untested in game.

### Halo 4: the Boltshot's Short band 0.8 -> 0.6, 2026-11-09 (committed 2026-11-10)

The owner's call, Nov 9. It had sat uncommitted in the shared tree; the dead pickup spots entry below and its tests (`tools/test_h4_dead_spots.py`) assume it.

- `brain/bot.py` `BANDS["boltshot"]` Short 0.8 -> 0.6.
  - At 0.8, a loose shotgun or Scattershot added 0.06 to a BR + Boltshot loadout, under `UPGRADE_GAIN` 0.08, so it was never picked up.
  - At 0.6, the BR's 0.7 is the loadout's best Short, and the shotgun, Scattershot and AR add 0.09.
  - A loaded BR stays in hand at 2 u (3.7 to the Boltshot's 4.6).
- Validation: on a clean checkout of the commits, `test_h4_dead_spots.py` failed 2 of 2 without it and passes with it. Gameplay untested.

### Halo 4 Ghost drivers aim from the Ghost's camera point: its bolts landed half a unit over their target, 2026-11-10

The owner: "the bots are shooting at spartans above their head so im doing a test to shoot straight at a wall for you to record the height and angle of the ghost shots", then "Yes, fix the aim".

- Measured (`tools/h4_shot_capture.py`, new: read-only, each tick the person's place, aim, view point and vehicle frame, and every projectile followed from where it shows to where it is gone). His wall test on Grind, `logs/h4_shot_capture_20261110-195939`: 200 Ghost bolts in 11 bursts, at 3-14 u, aiming middle, high and low (-9 to +6 degrees).
  - From the Ghost's origin (the seat view Ghost drivers aimed from, `H4_SEAT_VIEW`), every burst landed 0.46-0.50 u above the aim line, at every distance and aim height.
  - From its `ghost_d_camera` marker (-0.019, 0, 0.496 in its frame), every burst landed within 0.03 u of the aim line.
  - The bolts leave the guns about 1.4 u ahead of the origin at about 49-52 u/s and climb to the camera's crosshair point: +11 degrees over the aim at 3 u, +4.5 at 8 u, +3 at 10-14 u.
  - So a Ghost driver aiming from its origin at a man's chest put its bolts 0.5 u over the chest, about over the head.
- Fix (`brain/vehicles.py` `H4_DRIVER_AIM`): the Ghost aims from `ghost_d_camera`, as the Banshee aims from its camera anchor. Every tier, Halo 4 only. Its target point (`h4_aim_point`), lead, error and pace are unchanged, and so are the other seats.
- The same point was tried on Nov 8 and taken back after one Blood Crash match (Ghost kills 0.6 a minute against 1.3-2.2 before). That match's trace is not on this PC to recheck; the wall test is a direct measurement against it. Watch Ghost kills and hits in the next matches.
- Validation: `tools/test_demon_vehicles.py` (the Ghost aims from its camera point; on the measured rule, aimed from it a bolt meets the chest, from the origin it passed 0.5 u over; the Mongoose keeps its seat view) and `tools/test_h4_vehicle_aim.py` (the Ghost driver's origin 0.496 u up) updated. All 533 regression tests pass. Bots' Ghost fire in a match is untested; the bot process must be restarted.

### Team Slayer: Legendary, Blind, Scaling and Demon hold the high ground, 2026-11-10

The owner, on Complex: "In halo the game is about power positions and knowing when to push. I feel like too many bots are always on the lowest levels of the map. They need to utilize high ground alot more often, or stay in the hot spots once reached unless better conditions arise like a power weapon, or playing objective." Then: "Just make it to where this fixes bots that are Legendary, Blind, Scaling and Demon" and "Dont change the power weapons though. Let them go get those if one is up".

- **Cause**, live Complex 20261110-193429 (8v8 Team Slayer, 678 s; scratchpad `heights.py`, `posts.py`, `floor_area.py`):
  - Bots stood on the ground floor (under 1 u) 51% of the match and over 4.5 u 0-1%. Complex's five best-rated power positions are up there (z 5.3-6.6), and all 16 positions are walkable from spawn on the nav.
  - Posted bots (Order "mid", `slayer_slots`' two anchors) were within 3 u of their post 0-9% of their post time. In Slayer a post had no leash (`keep_role` only kept Invasion's "mid"). Its pull scored 0.6-1.2, so a gun (about 1.2), a hunt, or an infantry patrol (1.25) won.
  - The team's post changed every 25-45 s whatever happened there, about the walk up to the top floor. The support and the floaters went to where the enemy was last seen, or to a zone centre, which is the zone's lowest floor.
- **Who**: `profiles.high_ground`: tier `top` (fixed Legendary, Blind, Scaling) and Demon. Heroic, Normal and Easy keep the upstream play, and so does every other mode.
- **The leash** (`brain/bot.py`; `Bot.slayer_post`, `keep_role`, `ANCHOR_R` 8 u, `ANCHOR_DZ` 1.5 u):
  - Guns, hunts and holds past 8 u of the post, or under its floor, lose weight by teamwork (×0.33 at 0.95). A gun "on the way" (6 u) on the floor under it counts as off it.
  - Off the post (past 4 u, or under its floor), getting back scores 1.2 + 0.6 teamwork.
  - Fights are never cut. `fight` holds the bot as a CTF defender is held: no walk in or down on a man off the post, and back to it when he breaks sight. A sword or shotgun still closes.
  - Power weapons are not changed: a power spawn or a power gun lying loose (`Bot.power_at`: the map's 0.8+ weapons and Halo 4's power drops) is never cut. The way back does not cut short a trip to one the bot wants (scores at least the post). The team's power runs (`fetch`) were already exempt.
  - The director no longer sends these posts on infantry patrols (`infantry_patrol_orders`). Hunters and free bots still patrol.
- **Hold a post that works** (`brain/director.py`; `slayer_slots`, `post_working`, `post_lost`, `POST_*`): Team Slayer only.
  - The post is kept 15 s at a time, up to 120 s, while one of these tiers is posted on it (within 8 u, not under its floor) and has seen a man in the last 20 s.
  - Two of ours dead within 12 u of it in 30 s, since it was taken, and the team moves on at once (`fell_at`, from `track_events`), weighing that post a fifth.
  - Otherwise the upstream 25-45 s.
- **Fights from above** (`perch`, `PERCH_*`, `high_alt`, `assign_roles`):
  - The support's slot, when one of these tiers takes it, goes to the power position nearest the fight 5-25 u from it, 1 u or more above it, that sees it, and holds it ("mid").
  - The sweep floaters' slots go to a power position (the sweep's, else `sweep_high`), held.
  - The lead hunter and the far floaters still go straight at the fight, and the push posture (behind) is unchanged.
- Validation:
  - New `tools/test_slayer_high_ground.py`, 11 tests:
    - the four tiers and no others;
    - off-post guns and hunts cut, and the way back wins;
    - a gun by the post kept, one under its floor cut;
    - fights never cut;
    - power spawns and loose power guns never cut, at all four tiers;
    - Heroic, Normal and other modes untouched;
    - `post_working`, `post_lost` and `perch`.
  - All 531 regression tests pass.
  - On Complex's real map data, the director's orders for a mixed team (scratchpad `complex_slots.py`), with the fight on the ground floor (z 0.4):
    - the two Demon anchors went to z 6.6 and 6.2;
    - Blind's support to a perch at z 2.8, 13 u off;
    - Scaling's sweep to a power position at z 3.4;
    - the Legendary lead hunter to the fight;
    - the Heroic and Normal slots unchanged.
  - The live match's 28,200 posted decisions by Legendary, Blind and Demon, re-scored by the new leash (scratchpad `rescore.py`; only the logged candidates, power weapons by their spawns only):
    - a target off the post or under its floor 61% → 13%;
    - targets on the ground floor 26% → 8%, on the top floor 11% → 24%;
    - fights 19% → 19%.
  - A full think-loop replay on Complex's nav, posted on the top floor (scratchpad `post_replay.py`): with the Sword and Snipers up, Legendary and Demon still go for the Sword as before.
- Untested in a live match: how the holding plays against people (too passive or not), the fight hold on ledges, and the perch picks over a whole match. Restart the bot process to load it.

### Halo 4: bots stop retrying racked guns they cannot take (the spawn-room Boltshot stops), 2026-11-10

The owner's bug reports, Warhouse 17:35 "The bots pulling out their bolt shots almost every spawn?" and 18:56 "My team sometimes just stops in base switches to bolt shot and then leaves. I think both teams do it."

- **Cause**, live Warhouse 20261110-184913 (scratchpad `bolt_switch.py`, `bolt_items.py`, `bolt_reach.py`):
  - 191 switches onto the Boltshot. 98 came within 6 s of a spawn, 174 had the goal `item`, 8 had an enemy within 8 u, and 9 fired.
  - The items are the spawn rooms' racked rifles. `LiveH4F.ground_weapons` lists a gun as loose unless a biped or vehicle holds it, and reads them as `assault_rifle`.
  - With the Boltshot's Short at 0.6 (the owner's Nov 9 call, still uncommitted in the shared tree), an AR adds 0.09 to a BR + Boltshot loadout, over `UPGRADE_GAIN` 0.08, so `upgrade_point` sends the bot there and `gun_to_drop` puts the Boltshot in hand for the swap.
  - The bots stood 0.2 u from the gun holding Use about 90% of the time. The busiest spawn-room spots took nothing in 0 of 26 holds, while loose guns elsewhere took 7 of 7.
  - After the 4 s item wait, each bot skipped the spot for 30 s, only for itself, so it was back after its next spawn.
- **Fix** (`brain/bot.py`): Halo 4 counts each loose-gun spot whose 4 s wait came to nothing in `DEAD_SPOTS`, shared by every bot on both teams. At `DEAD_SPOT_FAILS` (2) the spot is skipped by all of them for the match (`Bot.skip_dead_spots`, run each live tick, sets their `rearm_skip` to forever). A swap that goes through clears the spot's count. A gun dropped later on a dead spot's 1 u cell is also passed over.
- The Boltshot value and the rest of the pickup logic are unchanged.
- Validation: new `tools/test_h4_dead_spots.py`, 2 tests (the racked AR stays an upgrade after one failed wait, is skipped by another bot after two, and another map's count does not apply). All 51 `tools/test_*.py` files pass. The counting step inside `plan` is not unit-tested, and gameplay is untested.

### Turn speeds, Halo 4 Demon melee reach, and the new Blind difficulty, 2026-11-10

The owner, from the tier chart: turn speed "435 · 650 · 650 · 700 ... Normal Hard legendary Demon"; "Demon bots seem to have an issue meleeing they miss quite a bit of melee ... Investigate"; and "another difficulty called Blind. And its just legendary but all the Aim and Hands Stats, are a random value between their current base stats and the celing being a little under the demons stats".

- **Turn speeds** (`brain/profiles.py` `TURN`): Normal 435, Heroic 650 (unchanged), Legendary 650 (was 1000), Demon 700 (was 480) deg/s. `LEGENDARY_AIM` no longer carries its own 1000 deg/s, so Legendary's protected head/turret aim plans its flicks at Legendary's real turn speed. Before this, `turn_cap` already held the view to the profile's speed, which it does for every tier. The protected aim's other values are unchanged.
- **Halo 4 Demon melee** (`brain/bot.py`):
  - Measured in 8 live Halo 4 matches (Nov 9 and 10, scratchpad `melee_audit.py`). A hit means the nearest enemy lost 0.4 or more of shield and health, or died, within 0.6 s of the press.
  - Demon's presses hit 48% under 0.9 u, 34% at 0.9 to 1.1 u, 28% at 1.1 to 1.25 u and 20% at 1.25 to 1.5 u (246 presses).
  - Demon walks in on every man (`PRESS` 1.0), so most of its presses came at the old 1.25 u edge (`MELEE_R`, measured in Reach). Its view was on the man in most misses (median 6 degrees), so aim was not the cause.
  - Change: `H4_DEMON_MELEE_R` = 1.0 u via `Bot.melee_r`, for the press, the empty-gun punch and `push_in`'s stop (now 0.8 u). Reach and the other tiers keep 1.25 u.
  - Every tier: `melee_check` now runs after `turn_cap` and the Halo 4 lock, so the "enemy in the swing" check uses the view the swing really goes out on.
  - Heroic and Legendary showed the same falloff with distance, at 17 to 23% overall. They are not changed here.
- **Blind** (`profiles.BLIND`, `blind_profile`, `blind_ranges`, `fixed_blind`, `protected_aim`):
  - Blind is fixed Legendary (tier `top`, extra None, label `blind`): all of Legendary's game sense, rules, priorities and calls, jittered as before.
  - Each bot draws reaction, aim error, aim lag, tracking, flick, overshoot, decision interval and turn speed on its own, uniformly between Legendary's base and 85% of the way to Demon's (`BLIND_TOWARD`). Examples: reaction 0.154 to 0.023 s, turn 650 to 692.5 deg/s, decision interval 0.10 to 0.0235 s. Lead stays Legendary's.
  - Its own hands aim everywhere: no protected head/turret precision (`precision_profile`), no unerring lead (`Aim.step`), no DMR/sniper head snap (`think`), and its trigger waits on its own aim. Legendary and Demon keep all of these (`protected_aim`).
  - Trace/report name "blind"/"Blind" (`tracefmt` label, `match_export`, `observer`, `player_stats`).
- **Native BOTS panel** (`native/bots_panel.h`/`.cpp`, `overlay.cpp`, `botcore.cpp`, `shared.h`):
  - Tier 6 "Blind" (key `blind`, violet, Legendary's four chevrons), with "for everyone" difficulty 7.
  - The pickers show Easy, Normal, Heroic, Legendary, Blind, Demon, Mixed, Scaling. The inspector's second row shows Blind, Demon, Scaling. botcore launches difficulty 7 as `--tier blind`.
  - `tools/botctl.py` `TIER_KEYS` / `DIFFICULTY_TIERS` match.
- Validation:
  - `tools/test_blind_difficulty.py` is new. `tools/test_demon_difficulty.py` now expects Demon at 700 deg/s and checks the native tables (8 difficulties, `HB_TIERS` 7). `tools/test_difficulty_separation.py` checks Legendary at 650 and keeps the rest of its stock fingerprint. All 50 `tools/test_*.py` files pass (the project's `python\python.exe`).
  - `native\build.bat blind` built `native/bin/botcore_blind.dll` (not in Git). The only warnings were the existing `_wfopen` ones; the `panel_art.py` step failed as before (PIL missing).
- Not tested in game: the Blind menu entries need MCC restarted onto `botcore_blind.dll` (the launcher loads the newest `botcore*.dll`). The turn speeds, melee reach and Blind brain need a bot-process restart. Whether 1.0 u lifts Demon's Halo 4 melee hit rate is unconfirmed. The hit measure is approximate: a teammate's burst can count as a hit.

### Halo 4 CTF: the flag carrier shoots its magnum on the way home, 2026-11-10

The owner: "Halo 4 is the only halo where you have a weapon wielded while carrying flag, but they currently do not shoot the magnum at all when carrying the flag in halo 4".

- Cause: a bot only pulls the trigger while it fights, and a carrier never got a fight goal (`decide`: fights only `if seen and not me.has_flag`). That rule is right for CE, Reach and Halo 3, where the flag is the carrier's only weapon. Today's Adrift traces: bot carriers ran home for 5,600 ticks with enemies listed, always "objective", never a shot. Their weapon read showed `unknown` 99% of the time, the inventory slot with 8 rounds a magazine and 24 total: the carrier's magnum.
- `brain/bot.py` `carrier_shot` (`CARRIER_SHOOT_R` = 25 u): in Halo 4 CTF, carrying on foot on its run home, the bot picks an enemy in view (`pick_target`) within 25 u. That enemy goes through the same branch as a Demon's "on the way" fight (`on_way_target`): fight's aim and trigger, the walk home steered as before.
  - Kept from the run as before: its own crouch and sprint.
  - Cleared: fight's grenade, ability, Use, reload and weapon switch. Any of those presses could drop the flag, so they are not sent. An empty magazine reloads itself on the next pull.
  - The flag melee at arm's length is unchanged.
  - Every tier. Radar dots and the emblem are not shot at: eyes only, as always.
- Not changed: other games and modes (Reach, Halo 3, CE, Oddball, Invasion's core), riders, and the carrier's route home.
- Validation:
  - New `tools/test_h4_carrier_shot.py` (3 tests): a Halo 4 carrier shoots a man in view at every tier; not out of range or out of view; only carrying, only Halo 4 CTF, on foot, on its run home.
  - A scratch replay of the full think loop on Adrift's real nav, a carrier on its way home with an enemy 12 u off in view, 5 s:
    - before, 0 trigger presses at every tier;
    - now 6 (Normal), 6 (Heroic), 7 (Legendary), 9 (Demon), with the same progress home (7.6-7.8 u).
  - All 513 regression tests pass.
- Untested in a live match: that the `unknown` weapon in a Halo 4 carrier's hands is the magnum and fires on the trigger, and that a pull on an empty magazine reloads without dropping the flag. Restart the bot process to load it.

### CTF: hunters cut the carrier off instead of chasing him, and every bot knows where he is under his emblem, 2026-11-10

The owner: "how would we add the ability to bots hunt the flag carrier, but without back tracking. Like cutting them off." Live on Adrift, he was on the top lane of their base, they were below him, and they went back through their base to reach where he was, which left their flag open. Also: "once you pick up the flag it shows an emblem above your head showing that im carrying their flag. So maybe make it to where they always know where the flag carrier is?"

- Cut-offs, `brain/director.py` `intercepts` (`CUT_*` constants). Every role pass (2 s) while an enemy carries our flag:
  - His likely ways home (`carrier_routes`), each as the distance he runs:
    - the shortest from where he is to their stand or flag return;
    - kept per match: the next shortest from our stand (the shortest with its own floor priced 3x, `alt_routes` / `penalised_way`);
    - the enemy's hand-drawn sneak routes, reversed.
    - A way is kept if he is within 6 u of it, it is no more than 1.6x the shortest, and it is not 60% the same as one already kept.
  - For the 6 nearest bots, a forward Dijkstra over the nav gives each its walk cost to every cell (about 2-4 ms a bot on Adrift).
  - On each way, the bot that cuts him off soonest gets a cut-off (`cut_on`): the first point, checked every 3 u from 4 u ahead of him, that the bot gets within 5 u of, on that point's floor, 1 s before he gets there. Both are taken at 2.25 u/s; his pace relative to ours, `CARRIER_PACE`, is 1.0, ASSUMED, since a Halo 4 carrier's speed is unmeasured. The bot waits at the spot nearest it in that range.
    - His time is the distance he runs; ours is the nav's cost. The nav prices drops for bots (Adrift: a 1.8 u drop off the top lane costs 28.8), and a person just drops. So a cut-off is only taken where the bot surely makes it.
  - More hunters than ways: further cut-offs at spots 8 u or more from those already taken. If one of us is within 15 u of him and not cutting off, one hunter slot stays a chase. Within 8 u of his goal, or with nowhere the bot is in time, the hunters chase as before.
  - A bot keeps its spot while a point of his way within 5 u of it is still one it is in time for.
  - The slot goes to that bot (fit `("bot", id)` in `assign_roles`, the nearest if it is taken). It now works with the usual 2 hunters; before, it needed 3 or more.
- Replaced: upstream's `cutoff_point`, one straight-line point 10 u ahead with 3+ hunters. The bot then swapped that point for the flag's position (`Bot.live_point` for "hunter"), so every hunter chased. `CUTOFF = False` still switches back to all chasing.
- `brain/bot.py`, the "cutoff" role:
  - Its objective is the point (scored as a hunter's: 1.3 + 0.6 teamwork), and it loiters 2.5 u round it.
  - `keep_role` keeps it within `CUT_R` = 10 u, and fights and hunts beyond that lose weight by teamwork.
  - It never hunts the carrier's emblem: that was the walk back after him.
  - It doesn't make the camper hold detour.
- The emblem, `Perception.update`: while an enemy holds our flag (CTF), each bot has an exact "marker" belief of him if he is within `MARKER_R` = 30 u, or anywhere if its job is him (hunter or cutoff, `marker_far`).
  - It is never a sighting: `seen` stays False, so there is no shot, recognition or reaction time through walls, and it is not posted to the team's sightings.
  - It feeds hunting, pre-aiming and target priority like an exact radar dot that doesn't fade. Easy gets it too (it's on everyone's screen).
- Adrift check (a scratch script on the real nav; not in the suite, since the level data isn't in Git): the carrier on the upper floor (z 6.2-7.6) by our base, two bots below (z 2.4). Six placements:
  - A bot whose old chase spent its first 10 u getting 13 u farther from his goal now gets its cut-off at the spot it is on, in range of where he comes down.
  - Bots that can be in time nowhere chase.
  - The second bot's spread cut-off was 18-51 u off on his way, the far ones by their stand.
  - Re-plan cost: about 10 ms for the cut-offs plus about 5 ms for the routes, once the stand's alternate routes (about 20 ms) are cached.
- Validation: new `tools/test_ctf_cutoff.py` (14 tests, on a small grid):
  - cut off ahead, never behind; nothing for a bot behind him;
  - the top-lane case (the cut-off is by where he comes down, not over the bot);
  - one bot per way; spread when there are more bots than ways;
  - a bot right by him keeps chasing; all chase near his goal;
  - the kept spot; role slots give the cut-off to that bot; the switch off;
  - the marker is exact and not seen within range, only for hunters when far, and absent when our flag isn't carried.
  - `tools/test_ctf_defender.py`'s stub now stubs `intercepts`.
  - All 510 regression tests pass.
- Untested in a live match: how well the predicted route matches a person's, the carrier's real speed, and whether the bot holds its spot facing his approach well enough. Restart the bot process to load it.

### CTF: one defender, only two captures ahead, the lowest difficulty bot, 2026-11-09

The owner: "Remove that team size logic for defending ... If the match is tied, no one on either team defends. You can keep the hunters, but no one should defend when tied. If the team is losing everyone should continue to attack. Only have a defender if the winning team is up by 2 or more flag captures, and defender count should never be higher than 1. If there is a defender, always make it the lower difficulty player, Excluding easy."

- `brain/director.py` `role_slots` (CTF): the capture lead alone decides defending (`CTF_DEFEND_LEAD` = 2). The lead is counted in captures: the posture's lead divided by the learned `score_unit`.
  - Tied, behind, or one capture ahead: no defender, and the whole team attacks.
  - Two or more captures ahead, with our flag home: one defender at the first `defend_posts` post. Never more than one, and never the team's last bot.
- Removed for CTF: the count by team size (1 / 2 / 3 by 4 / 7 / 8+ bots, at most half their team), the team plan's `defenders`, the extra defender for 15 s after a death at our flag (`defend_until` is still set, now unused here), lead +1 keeping more home, and the turtle at +2 that sent no runners. Up two, the rest still pull their flag (that turtle was a defence too, so it went with the rest; easy to restore if wanted). The defender with our flag out at 6+ bots is also gone: the hunters bring it back.
- Kept: hunters on a taken flag, the cut-off, the collapse on their carrier, the standoff, the all-in carry, and One Flag's defending side (its sides come from the round, not the score).
- Who defends: the defender slot is filled first, with fit "low_tier" (`assign_roles`), so it goes to the lowest difficulty bot by `profiles.defend_priority`: Normal, then Heroic and Scaling (Scaling counted as Heroic, as `resource_priority` does), then Legendary, then Demon. Ties go to the nearest. Easy never gets team roles, so it is never picked; a team of Easy bots and people has no defender.
- Validation: new `tools/test_ctf_defender.py` (8 tests): no defender when tied, behind or +1, at any team size; exactly one at +2 / +3 / +5 with 2, 4, 8 and 15 bots, runners still sent; captures, not points (10 a capture); none while our flag is carried or dropped, with hunters still sent; a lone bot attacks; the priority order; through `assign_roles`, the Normal 80 u away defends over a Legendary on the flag, Easy never does, and the nearer of two Heroics does. All 496 regression tests pass. Untested in a live match; restart the bot process to load it.

### Edit spots: CTF lanes and sneak routes drawn by hand, 2026-11-09

The owner, after finding that Halo 4's CTF routes come from fixed generated points (no Halo 4 map has a sneak route; Warhouse, Abandon, Gore Valley, Shatter, Impact and Forge Island have one lane): "Add a 'lane / sneak route' mode to tools/spots.py ... and add it to the edit part of lidar simulator so I can manually add lanes or sneak routes".

- Where they were from: `callouts.json` `lanes` and `sneak`, written by the upstream exporter's `tools/gen_zones.py` (not in this install) from the map's geometry (Adrift: its middle and 10.7 u either side), not from LiDAR or the game. `brain/maps.py` loads them; `director.pick_route` makes each lane a one-stop route and each sneak route a waypoint list (a carrier's backwards), skilled bots preferring sneak routes and the lane with the least recent threat.
- `tools/spots.py`: new kinds "lane" (`lanes` [[x, y, z]], at most 12) and "sneak" (`sneak` {red, blue}: routes of 2-32 waypoints, at most 8 a team), saved into the same callouts.json as the holds, the rest of the file kept. An edit with neither key (a viewer page from before) keeps the file's lanes and sneak routes rather than wiping them.
- `tools/lidar_view.html` Edit spots (LiDAR Viewer and Simulator): **Lane point** (cyan ring) and **Red / Blue sneak route** tools.
  - A sneak route is drawn by clicking its waypoints in order from the team's base to the enemy flag, with lines joining them. Enter, Esc or another tool finishes it. A one-waypoint route is dropped, and Save refuses one.
  - A picked waypoint can be dragged, removed (Delete), its whole route removed, or "Add waypoints after this" inserts more after it.
  - The counts line shows lanes and sneak routes per team. A viewer started before this change hides the new tools (its server cannot save them).
- Validation: `tools/spots.py --selftest` (lanes and routes round-trip into callouts.json as `load_map` reads them; malformed lanes, one-point and non-list routes refused; an edit without them keeps them) and `tools/test_spots.py`, `tools/test_owner_rides.py` pass. In the browser on Exile, nothing saved: a 3-waypoint red route (2 legs drawn), Enter finishing it, a one-point route dropped with its message, a waypoint inserted after the first and removed again with Delete, a lane added, a 2-point blue route finished by switching tool; the page's payload passed `spots.check` and reads as `load_map` reads it. No map's lanes or routes were authored: bots running drawn routes in a match is untested. The LiDAR Viewer must be restarted to load the new `spots.py`.

### LiDAR view: a Match / Simulator / Both scan switch, reopen the last map viewed, and lifts and man cannons drawn by hand, 2026-11-09

The owner: "Why is it when I load a lidar map, it doesnt load the fully simulated one? ... Im not sure what version is being loaded when viewing", then: the scan switch with the date and run count, reopening the last map viewed, and "a way to manually add the ability for me to make it able for a bot to use a man cannon or grav lift ... make it simple for me to do it in lidar".

- Why the simulated scan did not show: the Viewer opened the newest scan of any map, and a map with both scans always opened the match scan. Normal matches write one too (where people walk, their jumps), so 17 maps and layouts showed their played scan over the simulator's (Longbow: 41,852 floor cells against the simulator's 109,458).
- Scan switch (`tools/lidar_view.html`; `tools/lidar.py` `scans_of`, `/map` "scans"):
  - Match / Simulator / Both in the header of a stored map. Both draws the simulator's floor and walls in violet over the match scan. A scan the map lacks is greyed out.
  - The header line (and each button's tooltip) says what each scan is: LiDAR runs or "from your matches", floor cells or "no floor, only jumps", and when it was updated.
  - The scan picked is remembered: opening a map from the list shows that scan where the map has it.
- Reopen the last map: the page records the map and scan it shows (`POST /last`, `logs/lidar_view_last.json`). `lidar.py --view` with no map opens that one (the scan it still has), else the newest as before.
- Lifts and man cannons (Edit spots, Gravity lift / Man cannon tools):
  - Two clicks: where you step in (the pad), then where it puts you down. A line joins them; either end can be dragged. Name and kind can be changed; Remove takes both ends.
  - Saved to `owner_rides.json` in the folder of the map or layout shown (`tools/spots.py` "ride").
  - `brain/maps.py`: `owner_ride_links` adds each as a one-way people's ride link (ride 1, human 1, found_by "owner"), after `anchor_launches`, so its pad stays where it was drawn. `owner_ride_pads` adds a "lift" (or "launcher") marker at a pad no marker of the map is within 1.5 u of, so `Bot.lift_near` / `lift_base` steps into the lift and waits, and the nav keeps drops out of its column. Built-in maps read their layout's and base's (`data_names`).
  - Save warns when an end is off floor the nav can walk (more than 0.7 u off it, outside the nav, or both ends on one node): `Terrain.add_human_links` skips such a link, so bots would not use it.
- Validation: new `tools/test_owner_rides.py` (marker added only where the map has none, one-way ride links, malformed rides left out, and on Headlong's real nav a drawn lift is one hjump from pad to landing node, one way); `tools/spots.py --selftest` (rides saved, named, warned off the nav); `tools/test_spots.py` updated. In the browser on Headlong: the switch showed Match (jumps only), Simulator and Both (violet overlay, "MATCH + SIMULATOR"); a Viewer started with no map reopened Headlong in Both; a gravity lift drawn and saved was read by `load_map` (lift marker at the pad) and `_build` (its ride link); a landing moved off the floor saved with the warning. The test ride, its backup and the last-view file were removed. All 488 regression tests pass; `lidar.py --selftest` passes. Bots riding a drawn lift or cannon in a match is untested.

### LiDAR Simulator: open a map, edit it, then choose to simulate it; no more stuck panel after Stop and save, 2026-11-08

The owner: "when pressing save and stop. I cannot select another map to simulate. Itll just let me pull up the heatmap for it, but itll be stuck saying the other map is still live. Allow me to open a map without simulating it, with ability to still edit it. Then choose if I want to simulate or not."

- Cause (`tools/lidar_view.html`): a map opened from the list is shown as a stored map, and that page stopped asking the simulator anything (`poll` ran only for the live view). So on it:
  - the Simulator panel and the list's Simulate buttons were gone;
  - the list still called the stopped map LIVE (its hub stays the window's live one);
  - the simulator, which closes 90 s after its window stops asking (`lidar_sim.main` `last_seen`), shut down while the map was open.
- Fix:
  - `tools/lidar.py serve`: new `GET /sim`, the simulator's state alone, which also refreshes `last_seen`. The LiDAR Viewer has no simulator: 404.
  - The page polls `/sim` every second while a map is open in the simulator's window. Its panel stays and says "<map> is open: simulate it, or open another map", with a **Simulate <map>** button ("... instead" while another map runs, after the existing confirm). Starting it switches the page to the live simulation.
  - "Pick a map" is now **Open a map**: clicking a map opens it, to look at and edit its spots. The list's Simulate button still starts one at once.
  - With no map running, no map is LIVE in the list, and the last one stopped opens like any other. "Back to the live scan" reads "Back to the simulation" in the simulator. "Click the map" (spots for the running map) is off on a map opened beside it.
- Validation: in the browser with the simulator: Rat's Nest simulated, Stop and save, Open a map > Construct opened with the panel and Simulate Construct; Edit spots loaded its spots; the simulator was still up after 100 s on that page; Simulate Construct started it and switched to the live view; opening Rat's Nest while Construct ran offered "Simulate Rat's Nest instead", "Back to the simulation" and Construct alone LIVE. Test files removed. New test in `tools/test_lidar_mappers.py` (`/sim` answers and refreshes `last_seen`; 404 in the Viewer). All 429 regression tests pass; `lidar.py --selftest` passes.

### Red and Blue patrol tools in Edit spots; the LiDAR Simulator maps ground, air or both, 2026-11-08

The owner: "Add a functional Red patrol (red only) and a Blue patrol (blue only) Marker ... Also if possible add it to where we can choose if they bots are all mapping the ground or all mapping the air or both."

- Edit spots (`tools/lidar_view.html`): new Red patrol and Blue patrol tools beside Patrol (both). They place a team-only patrol point (`{"pos", "team"}` in infantry_patrols.json, the brain's existing team patrols: only that team's free bots go), named "Red patrol N" / "Blue patrol N". Their labels take the team's colour and the count line shows how many are team-only. A point's team can still be changed after.
- LiDAR Simulator, "Who maps" in the Simulator panel (`tools/lidar_sim.py` `crew`, `Control` action `mappers`, `--mappers`):
  - Both: 16 walkers and 8 aircraft, as before.
  - Ground: the 16 walkers, no aircraft.
  - Air: no walkers, 16 aircraft. Aircraft fly the air over floor walked in the same run, so with no walkers they had nothing to fly; `Airspace.seed` now gives them the air over the nav's reachable floor at once. The LiDAR director (it sends walkers) and "Spots to cover first" are off for an air-only map.
  - A choice applies from the next map started; a running map keeps its own and the panel says so.
  - Live LiDAR matches are unchanged: there every LiDAR bot walks; aircraft exist only in the simulator.
- Validation: new `tools/test_lidar_mappers.py` (crew counts, the panel command and running map, air-only has air to fly). Rat's Nest (`h3_armory`) headless: air only flew 16,271 of 16,279 air cells in 1.6 sim min with no floor marked and ended by itself; ground only marked 35,292 floor cells and flew none; both did both. In the browser: Air ran 0 walkers and 16 aircraft; a switch to Ground mid-map showed the next-map note; the Red and Blue patrol tools placed team points and saved teams in the edit. The test's files were removed. All 428 regression tests pass.

### Edit spots in the LiDAR view: hot spots, patrol points and team holds by hand, 2026-11-08

The owner: "Can we also make Lidar more interactive? ... can we make a tool to where I can implement Hot zones, Patrol Areas, and other spots the bots use so I dont have to have you do it for me all the time?"

- LiDAR Viewer, new "Spots bots use" panel (`tools/lidar_view.html`, button Edit spots or key S):
  - Add: pick Hot spot, Patrol point, Red hold or Blue hold, then click the floor. Click a spot to select it, drag it to move it, Delete or Remove to take it out, Esc to stop adding.
  - A patrol point gets a name and who patrols it (both teams, red only, blue only). A computed power position can be made a hot spot.
  - Spots are placed on the floor drawn under the cursor, the one nearest the camera: the LiDAR scan, or "Show the floor bots can reach" (the nav's reachable floor, as `power_positions.py` picks from; on by default where a map has no scan). The level data's every upward face was tried first and put a dragged spot on a roof 20 u up.
  - Save and Undo changes; leaving with unsaved changes asks first.
- `tools/spots.py` (new) reads and writes the files the brain reads (`brain/maps.py load_map`):
  - Hot spots: positions.json rows marked `owner`, score 1.0, first. A kept one keeps its measures; a new or moved one is measured by `power_positions.describe` (what it sees, height, cover), as `--add` does. Computed rows stay; one within 1 u of a hot spot gives way, as with `--add`.
  - Patrol points: infantry_patrols.json in the hand-made layout (`{name: [x, y, z]}` or `{name: {pos, team}}`).
  - Team holds: callouts.json `holds`, the rest of the file kept. Each team keeps at least one (the brain picks from them: CTF carriers waiting for their own flag, the Oddball carrier, Firefight, and power positions on a map without any).
  - A Forge layout edits its own positions/callouts where it has them, else the base map's; patrols are always the base map's (the panel says which files are shared).
  - Writes are whole-file replaces, only for files whose data changed, each old file copied to `backups/spots/` first. A malformed edit (no place, duplicate patrol names, a team with no hold) writes nothing.
- `tools/lidar.py serve`: `GET /spots`, `GET /spots/floor`, `POST /spots` (needs the `X-LiDAR: spots` header, like the view's other writes).
- Validation: `tools/spots.py --selftest` and new `tools/test_spots.py` (owner rows, patrol layout, refused edits, unchanged saves, backups, file choice); `tools/lidar.py --selftest` passes. In the browser on Headlong: added a red hold and a blue-only patrol point, dragged a hot spot, saved; the brain's `load_map` read all three (the moved hot spot measured: sees 23, 1.5 u up, cover), then the map files were restored from Git. All 420 regression tests pass. Bots using the edited spots in a match is untested. Edits apply from the next match; restart the LiDAR Viewer to get the panel.

### Easy and Normal walk the jumps people take on their way, 2026-11-08

- The owner, Nov 8: "make easy bots jump, they get stuck alot without jumping".
- Six Halo 4 matches (scratchpad `traverse.py`, walking between fights on foot):

  | | Speed | Pushing on but under 0.5 u/s | Path straightness over 5 s | Unstuck wiggles |
  |---|---|---|---|---|
  | Easy | 1.44 u/s | 18% | 0.46 | 10% |
  | Normal | 1.93 u/s | 4% | 0.73 | 2% |
  | Heroic to Demon | 1.84-1.97 u/s | 3-5% | 0.76-0.77 | 1-2% |

  On Haven, Normal was stuck 11% of the time, straightness 0.56. In Reach, Easy went 1.71 u/s, 8%, 0.96.
- Cause: the nav plans people's jump routes (`ROUTE_JUMP`) and jumps onto ledges only for a jump skill of 0.5 and up. Easy's is 0. Normal's 0.5 is jittered per bot (`make_profile`), so roughly half the Normal bots had none either (one at 0.497).
- `brain/bot.py` `nav_jumps` (`EASY_NAV_JUMP`): Easy and Normal take those jumps on their way. The four checks are in the jump onto a landing, the path to a point, `move_to`'s ways and `route_view`; the walk-or-jump field is the fifth. Their hops, fight jumps and jump shots stay by their jump skill, so Easy still makes none.
- Validation: new `tools/test_easy_nav_jump.py`, 4 tests (every tier takes the routes; Easy keeps jump skill 0; a Normal jittered under 0.5 still takes them; with the switch off, Easy and that Normal walk round as before). All 457 regression tests pass. Gameplay is untested.

### Halo 4: battery guns read unknown, not empty; Haven's bottom-middle pillar is no longer glass or shoot-through, 2026-11-09

The owner, after Haven 20261109-192854: "I dropped a beam rifle twice that game and it was never picked up figure out why. Also I think reasons alot of bots see eachother and dont shoot is because the walls in lidar might be too tall?", and his report at 103 s: "Bots try to shoot through this massive pillar in the bottom middle of Haven".

- **Beam Rifle.**
  - His inventory (`collect_*.jsonl`) read the Beam Rifle 0 + 0 the moment he held it, at 380.9 s and again at 414.5 s.
  - `LiveH4F.ground_weapons` drops a loose gun at 0 rounds, so no bot ever saw it. No "power weapon" note, and no bot held one.
  - Across 13 matches every bot's sword read 0 (147 rows), and no bot ever carried a Storm Rifle or Plasma Pistol: the battery guns, whose count is not at `H4_AMMO`.
  - `brain/live.py` `LiveH4F.H4_BATTERY` (sword, gravity hammer, Beam Rifle, Storm Rifle, Plasma Pistol): `rounds` reads them unknown (-1). A loose one is listed, and one in hand is never "dry". With no name read, the rounds read as before.
- **Look but do not shoot**, every bot row aimed at a man (scratchpad `no_fire.py`):

  | tier | firing | not firing: aim not on him yet | gun pacing | a wall ("shot obstructed") |
  |---|---|---|---|---|
  | Demon | 26% | 26% | 29% | 17.6% |
  | Heroic | 5% | 60% | 30% | 5% (through glass) |
  | Normal | 12% | 59% | 29% | under 1% |
  | Easy | 6% | 67% | 26% | under 1% |

  For the lower tiers it is their aim settling, not walls (not changed here). Of the Demons' 242 "obstructed" rows on the owner, 24 had his crosshair on that Demon, 15 of them at one spot pair (a Demon about (-0.8, -10.3), he about (1.7, -2.5)).
- **The pillar** (x -2..2.5, y -10.8..-14.5):
  - Haven's `wall_kinds.json` / `glass.json` (from H4EK's bsp: the Forerunner glass shaders) had it as a window from the floor (-0.99) to its top (2.38), so the bots saw through it.
  - `walls_learned.json` had 88 learned shoot-through cells on it, so the round's line read clear. 94.0-97.5 s: two Demons fired across it at #6 ("line"), and his shield stayed 1.00.
  - Removed: the pillar's 230 cells from `wall_kinds.json` "window" (3,545 to 3,315; tracked) and `glass.json` (untracked), and its 88 cells from `walls_learned.json` (212 to 124; untracked). Backups: `backups/spots/h4_wraparound_20261109-194815_pillar_*`.
  - The rest of Haven's glass network (3,315 cells through the centre) is left as it was.
  - A match running at the time (started 19:44:41) loaded the old data and re-saved its learned walls, the 88 included. After it ended (its last save 19:53:04) they were taken out again (220 to 132; backup `backups/spots/h4_wraparound_*_pillar_walls_learned.json`).
  - A fresh load of Haven: the three lines the Demons fired across the pillar read blocked for sight and rounds; open lines 3-9 u west and east of it read open.
- `brain/terrain.py` `learn_shot_through` (`LEARN_SOLID_BELOW` 0.6, `LEARN_SOLID_ABOVE` 1.2): no learned shoot-through inside a wall running from 0.6 u under the round's line to 1.2 u over it (a pillar); a railing, a grate or a sill as before.
- Validation:
  - `tools/test_h4_ammo.py` +1 (Beam Rifle, sword and Storm Rifle read unknown while a BR of the same tag word reads its rounds).
  - New `tools/test_learn_shot_through.py` (a pillar is never learned, a railing is). The pillar case learns a cell with the guard off.
  - Haven's terrain rebuilt with the pillar out reads its solid line blocked.
  - All 485 regression tests pass. Gameplay is untested.

### Halo 4: the Boltshot's short-range value 0.8 to 0.6, so a shotgun or Scattershot is picked up, 2026-11-09

- The owner, Nov 9: "why does the scattershot or shotgun never get picked up", then "Can we just lower the bolt shots weight?"
- `upgrade_point` takes a loose gun that adds over `UPGRADE_GAIN` 0.08 to `loadout_value`: each band's best gun, weighted Short 0.30, Medium 0.35, Long 0.25, Extreme 0.10, plus a power gun's pull. With the Boltshot's Short at 0.8, a shotgun or Scattershot (1.0/0.2/0/0) added 0.06 to BR + Boltshot and 0.00 to BR + AR: never picked up. Their rank 3.4 is also under the Demon power-gun rule's 4.0.
- `brain/bot.py` `BANDS["boltshot"]` (0.8, 0.4, 0.05, 0) to (0.6, 0.4, 0.05, 0): the BR's Short 0.7 is a BR + Boltshot loadout's best.
  - From BR + Boltshot: shotgun +0.09, Scattershot +0.09, AR +0.09 (picked up); magnum +0.03; the rest 0.00 or less (as at any value up to 0.7).
  - `choose_weapon` at 2 u, every tier: a loaded BR 3.7 against the Boltshot 4.6 (5.2 before), under the 1.0 a swap needs, so the BR stays in hand (Halo 4 Demon's `keeps_gun` held it already). With the main gun empty the Boltshot comes out as before.
- Seen, not changed: the Storm Rifle and Suppressor have no band row. From `WEAPON_RANGE` they read 0.2/1.0/1.0/0.2, a rifle's, where in Halo 4 they are close-range automatics.
- Validation: `tools/test_demon_odds.py` `BoltshotBandTests` (shotgun and Scattershot over the bar from BR + Boltshot; a loaded BR kept at 2 u by Legendary). `KeepGunTests` set the old 0.8 for their own run, so they still test `keeps_gun`. 72 in the file. All 482 regression tests pass. Gameplay is untested.

### Halo 4 Demon fights it out with a man on it within 8 u instead of breaking off, 2026-11-09

The owner's bug report, Warhouse FFA 20261109-185804 at 202.1 s: "Camper delayed heavily to kill me".

- Camper25 (Demon) had the SAW. At 186.5 s, the owner 5 u off with his sights on it and its shield down to 0.46, it broke off ("odds 0.54"). It backed off for 3 s at 3-5 u from him, firing on 2 of its samples ("full first, no re-peek"), then turned at 189.5 s and killed him at 190.56 s.
- Today's four Halo 4 matches (scratchpad `break_range.py`; Haven 181312, Blood Cavern 183113, Warhouse 184005 and 185804): Demon break-offs by the nearest man aiming at it.

  | nearest man aiming at it | break-offs | died within 5 s |
  |---|---|---|
  | under 6 u | 35 | 74% |
  | 6-12 u | 13 | 69% |
  | 12 u+ | 6 | 0% |
  | nobody | 87 | 36% |

  Retreating while aiming at a man, Demons fired on 23% of rows, about a fight's pace: the gun's cadence, not a retreat rule.
- `brain/bot.py` `demon_odds_rules` (`BREAK_CLOSE_R` 8 u): with a man aiming at it in sight within it, no break-off; it fights on (note "he is on me at N u: fight it out"). The trade rule still comes first.
- Power guns in the same match: the SAW was taken four times, by Demons each time (64.5, 71.1, 170.3, 275.0 s; never in Warhouse 184005).
- Validation: `SixTests` +1 (a man on it at 5 u is fought out, not run from), 70 in the file. All 480 regression tests pass. Gameplay is untested.

### Halo 4 Demon: a power gun banned as out of reach is taken again beside it; one the nav cannot reach is passed over, 2026-11-09

The owner, after two matches with the power-gun rule below: "I died with a saw also".

- Blood Cavern 20261109-183113: he died with the SAW at 239.1 s and 341.4 s. Demons took it 8.1 s and 8.2 s later; the normal pickup rules got there first (no "power weapon" notes).
- Warhouse FFA 20261109-184005 (he won 25-9): the SAW lay on the lower floor at (1.2, -1.4). Four Demons noted it for 115-157 s, and none took it.
  - Demon 1 stood on the walkway 3.6 u over it for 6 s, then `headway` banned the item for 30 s.
  - When it got down 1.8-3 u from it, its think rows had no item at all: the ban struck it each tick (`goal_ban`, `decide`). The "power weapon" note was written before that, so the notes overstated it.
- `brain/bot.py` `power_grab`: a banned power gun within `POWER_UNBAN_R` 3 u flat on its floor (1 u) has the ban lifted. A ban farther off holds (no score, no note). A gun the nav has no way to (`Terrain.reaches`) is passed over for the next.
- Rearm check:
  - Haven 20261109-181312, before the fix: 3,055 Demon and bot rows with the main gun at 0 rounds, 6 of them going for a gun; 275 rows of sidearm fire past 6 u came with the main gun empty.
  - Blood Cavern and Warhouse after: no rows with the main gun empty, and none of the 18 rows of sidearm fire past 6 u came with an empty main gun.
- Validation: `PickupTests` +2 (the ban lifts beside the gun on its floor; it holds from the walkway 3.6 u over it; an unreachable gun is passed over), 69 in the file. All 479 regression tests pass. Gameplay is untested.

### Halo 4: Demons take a dropped power gun first, judge fights by their loaded rifle, and every bot refills an empty main gun, 2026-11-09

The owner, Nov 9, after Haven 20261109-181312: "why they take so long to pick up a power weapon after killing someone holding one. I died with the saw twice before they picked it up. Also a bot was shooting at me with a boltshot from distance, Was it out of ammo in the primary? Can bots pick up default weapons off dead bodies?"

- That match: the four Demons went 60-32 (K/D 1.88; 1.28 before the six rules below), and the owner 27-21.
- **SAW:** he died with it at 447.3 s and 481.7 s; Demon 1 took it at 488.0 s.
  - Over the first 7 s other goals scored over it: an objective, a radar hunt, a one-shot hunt (3.0-3.4 to the item's 1.2-1.9).
  - Then a loop, twice. Coming up to it, `gun_to_drop` switched Demon 4 to its Boltshot (the gun the pickup would swap out). The odds, by the gun in hand, read a Boltshot at the owner 17 u off: 0.01-0.03. It broke off 1.26-1.4 u from the gun (the pickup takes 1.2 u), switched back and came again.
- **Boltshot at range:** 267 of 326 rows of Boltshot fire past 6 u came with the BR or Carbine at 0 rounds, reserve and magazine. `rearm_point` went for a loose gun only when every gun was empty or the one in hand was low. `upgrade_point` skips a gun named like one carried, so a BR on a body was walked past by a bot with an empty BR.
- Of the match's 57 Demon break-offs, 5 came holding a sidearm with the main gun loaded and 12 with it empty.
- `brain/bot.py`:
  1. `odds_threats`: our kill time is the best of the loaded guns carried (`loaded_guns`), a gun not in hand plus `H4_SWAP_S` 0.5 s.
  2. `power_grab` (in `demon_odds_rules`, Halo 4 fixed Demon): a power gun lying within `POWER_GRAB_R` 15 u (rank `POWER_GRAB_RANK` 4.0 and up: the SAW, rockets, sniper, laser ...) that it does not carry loaded is its goal at `POWER_GRAB_SCORE` 3.3. That is over its hunts 3.2 and the callout and third-party pushes, under a trade 3.4 and a break-off 3.6. It sets `pickup_gun` so the swap gives up the right slot. Not with a man in sight within `POWER_GRAB_CLOSE` 6 u, nor when a Demon teammate on foot is nearer the gun by 2 u. Note "power weapon: the lmg, 8.0 u".
  3. `rearm_point` / `main_dry` (Halo 4, every tier): every gun but a sidearm (`DEMON_SIDEARMS`) empty sends it for the nearest loose gun within `MAIN_DRY_R` 40 u, its own kind too (walking over one refills it; `drop_slot` gives up the empty gun first), at `MAIN_DRY_SCORE` 3.25. Every gun empty scores the same in Halo 4 (3.0 before).
  - The empty-gun score itself was already there: `choose_weapon` never picks a gun at 0 rounds (-9) and switches off one at once ("dry").
- Validation: `tools/test_demon_odds.py` `PickupTests`, 6 tests, 67 in the file:
  - the odds by the loaded Carbine while the Boltshot is in hand, and by the Boltshot when the Carbine is empty;
  - a SAW 8 u off and rockets 14 u off come first; not a BR, not 20 u off, not with a man 4 u off, not for a nearer Demon;
  - an empty BR is refilled from a BR 25 u off, Demon and Easy; a loaded BR, or Reach, as before;
  - `main_dry` (an unknown count is not empty; sidearms alone are `dry`'s).
  - All 477 regression tests pass. Gameplay is untested.

### Halo 4 Demon: trades, full-shield re-peeks, one-shot callouts, instant trades, third parties, regroups, 2026-11-08

The owner, Nov 8: "Go ahead and try to build these 6 for demon difficulty". All six are Halo 4 fixed Demon only (`h4_demon`), in `brain/bot.py`; constants `TRADE_*`, `THIRD_*`, `CALLOUT_*`, `TEAM_CRACKED`, `TEAM_ATTACKERS`, `REGROUP_MATE_R`, `REPEEK_*`.

1. **Trade rule** (`TRADE_MODES` Slayer; `trades`, `odds.kills_first`): a losing fight is broken off only when it would not kill one of them before it drops, counted with its kill times x `TRADE_MARGIN` 1.6. A man not looking it would not beat, and a hunt into a group, the same. Note "losing, but a kill first: trade".
   - Replay (scratchpad `odds_replay_trade2.py`; Haven 182020, 183706, 203750, Blood Crash 141550, Redoubt 010650): 206 Demon deaths, 176 with no kill in its last 4 s; 285 Demon kills.

     | rule (line 0.6, teammates counted) | no-kill deaths warned | won fights it would leave |
     |---|---|---|
     | before | 60% | 21% |
     | trade x1.0 | 36% | 7% |
     | trade x1.3 | 47% | 11% |
     | **trade x1.6** | **50%** | **12%** |
     | trade x2.0 | 55% | 14% |
2. **Third party** (`team_play`, `push_on`): a teammate on foot fights a man (`TEAM_TARGETS`) and is not clearly winning (his kill time on him over `THIRD_EVEN` 0.7 of the man's on him). The man is out of a free Demon's sight (no man in its own), within `THIRD_R` 20 u, and it is healthy (`CHASE_MIN`). It hunts a point `THIRD_ANGLE_R` 6 u off the teammate's line on its side (`THIRD_SCORE` 3.0), when it would kill him first with him busy (not aware: the odds' late start). A teammate winning it gets the spreading rule instead.
3. **One-shot callouts** (`TEAM_CRACKED`): every bot posts the men in its view with their shield gone.
   - A man in sight with his shield gone: threat x `ONE_SHOT_K` 1.5.
   - One called out of its sight within `CALLOUT_R` 15 u for `CALLOUT_S` 2 s: hunted (`CALLOUT_SCORE` 3.1), when healthy and it would kill him first (aware).
4. **Instant trades** (`TEAM_ATTACKERS`): every bot posts who is hurting it. A teammate dead within `TRADE_R` 20 u with his attacker posted in his last `TRADE_FRESH` 2 s: that man is fought in sight or hunted for `TRADE_S` 4 s (`TRADE_SCORE` 3.4), when healthy and it would kill him first (his real shield; aware). Note "trade: #N is down, after #M".
5. **Regroup** (`regroup_cover`; `lidar_cover(every=True)`): a break-off's cover is, of the LiDAR cover from them it reaches in time, the one nearest a teammate on foot within `REGROUP_MATE_R` 25 u. With none, the nearest cover as before.
6. **Re-peek with a full shield** (`repeek_rule`, armed by a break-off for `REPEEK_S` 10 s): while its shield is under `REPEEK_SHIELD` 0.95 it hunts no one and fights only a man hurting it, one within `REPEEK_CLOSE` 5 u, one with his shield gone, or one a teammate fights. It holds its cover (`REPEEK_HOLD_SCORE` 3.0; upstream's 2.3 hold lost to the 2.9 fight and 3.2 hunts). Note "shield N: full first, no re-peek".

- Not done: the opening grenade stays off (the owner: during its throw "I already have two bursts shot into them").
- The rules cost about 0.06 ms a call with 4 enemies and 3 teammates (the test terrain).
- Validation: `tools/test_demon_odds.py` `SixTests`, 14 tests, 61 in the file:
  - kills_first counts; Slayer losing with a kill first stays; CTF has no trade rule; no kill first still breaks off and arms the re-peek hold;
  - half shield no re-peek, a man hurting it or one shot is fought, a full shield or the hold's end peeks again;
  - a called one shot is hunted when healthy, not when hurt; one shot in sight first; every bot posts cracked men and its attacker;
  - a teammate's killer is pushed;
  - a teammate's even fight is taken from an angle off his line; a teammate winning gets no third man;
  - cover nearest a teammate, the far one out of time, alone the nearest.
  - All 471 regression tests pass. Gameplay is untested.

### Bots crouch on people's crouch floor only under a low ceiling, 2026-11-08

- The owner, Nov 8: "why do the demons crouch so much now? it only started happening earlier after your super in depth update on them".
- Demon rows on foot with crouch held:

  | Match | Crouched |
  |---|---|
  | Blood Crash 01:34 | 1.7% |
  | Blood Crash 14:15 | 6.3% |
  | Haven 18:20 | 11.2% |
  | Haven 20:37 | 20.7% |
  | Haven 21:18 | 18.6% |

  It was in fights, hunts, objectives and pickups alike, in spells of a median 0.24-0.27 s.
- Cause, not the Demon changes: the live LiDAR records a person's walk with crouch held as crouch floor (`tools/lidar.py` `KIND_CROUCH`). `maps.terrain` made every such cell crouch floor, and `Bot.crouch_spots` crouches every tier on and just before it. The owner's fight crouches over his Haven matches today (78 human-minutes) had painted 535 cells.
  - 57-76% of every tier's crouched rows in the two last Haven matches stood on them.
  - 11 of them have a ceiling over them (a face at head height, open at the knee); Blood Crash 4 of 207, Cliffside 0 of 51.
- `brain/terrain.py` `low_overhead`: `_low_ceiling`'s test for given points, walked or not.
- `brain/maps.py` (`CROUCH_LOW_ONLY` True): crouch floor is the painted cells under such a ceiling. The recording is unchanged: `lidar.json`, its crouch routes and the bots' `ROUTE_CROUCH` routes as before.
- Validation: new `tools/test_crouch_floor.py` (Haven's crouch floor is exactly its painted cells under a low ceiling, under a fifth of them; an empty query). All 457 regression tests pass. Gameplay is untested.

### Experiment removed: Demons that always know where every enemy is, 2026-11-08

- The owner tried it for an evening ("make it to where the demon bots always know where their enemy is at all times ... and see how that works"; Haven 20261108-211827, Demons knew 100% of living enemies' places to the 0.1 s, 12% by their own eyes), then: "remove the all seeing switch".
- Removed: `DEMON_ALL_SEEING`, its flag check in `tools/live_bots.py` (back to the committed file), its loop in `Bot.share_sightings`, `AllSeeingTests`, and `logs/demon_all_seeing.on`.

### Halo 4 Demons' target spreading: one of two alike keeps the man, and a man left stays left 1.5 s, 2026-11-08

- First live match with the teammate odds, the rifle rule, spreading and the press with two in view: Haven 20261108-203750, the owner and three bots against four Demons, 25.2 bot rows a second.
  - Scoreboard: the owner 36-26, the Demons 60-47 (K/D 1.28, 15.0 kills each). The closest match before, 18:37, was owner 46-27 and Demons 60-56 (1.07); at 18:20, 50-40 and 90-64.
  - Break-offs: 96, about as many as before (92 at 18:20). 29% died within 5 s (46% and 33% before); a break-off came within 4 s before 46% of Demon deaths.
  - The rules fired: "spread" 46 notes a minute, "keep the battle_rifle" 22 a minute.
  - Against 18:37:
    - A teammate was also on the man in 70% of Demon kills (66% before).
    - Time from first on him to dead was 1.62 s (1.52); kill range 9.1 u (9.8).
    - The owner lost 0.30 a second of Demon fire on him (0.43).
  - Teammates rarely saw the same men: with another Demon within 15 u at 96% of the break-offs, only 26% had those enemies in view (the teammate odds count only those).
- Cause: target switches within 3 s of the last went up to 13.6 a minute per Demon (4.8 at 18:37), and back to the same man within 2 s to 5.9 (0.8). Two Demons alike on one man (the same gun, equal kill times) each read him as the other's under "no slower than us": both left, nobody had him, both came back.
- `brain/bot.py`:
  - `mate_has_him`: a teammate has him only when more than `SPREAD_TIE` 10% quicker, or within it with the lower bot id.
  - `demon_commit` records the man left (`spread_from`); `threat` keeps him at x `SPREAD_K` for `SPREAD_HOLD` 1.5 s after.
- Validation: `tools/test_demon_odds.py` `SpreadTests` +2 (two alike on one man: only bot 9 leaves him to bot 5, bot 0 keeps him; the man left stays left through the hold). The spread tests now arm the test Demon with an AR at 10 u, so the teammate's BR is the quicker kill. 47 in the file.
  - 450 of 451 regression tests pass. The failure is the same `test_h4_reports_nov8.py` `test_owner_spots` on the uncommitted Gore Valley patrol points.
  - Gameplay is untested; the next match's bot process loads it.

### Halo 4 Demons spread their targets and walk in on two when winning; melee checked, unchanged, 2026-11-08

The owner, Nov 8: "even in 4v4 I get alot more kills even though I die more". Haven 20261108-182020 and -183706:
- He got about 50 kills a match, about 22 per Demon. Another Demon was firing on the man in 63% of the Demons' kills (his: 36%).
- Their median kill was 9.1 u off and took 1.31 s from first on him (his: 7.6 u, 1.08 s).
- 13-23% of their fight decisions had two or more men in view, where upstream's press holds.

Changes in `brain/bot.py`:
- **Spread** (`TEAM_TARGETS`, `mate_has_him`, `SPREAD_K` 0.5): every bot posts the man it fights (`share_sightings`). For a Halo 4 Demon, a man a teammate on foot fights (post under 0.3 s old) counts as the teammate's kill when the teammate kills him no slower than it would and is winning (his time under the man's on him alone). Such a man's threat goes x0.5 with no team-shot lift. A committed Demon (`demon_commit`) turns to a man in view nobody has, unless it is finishing its own (note "spread: ..."). A teammate losing to him still gets help (the team-shot lift and the third-party rule as before).
- **Press with two in view** (`press_on`, `DEMON_PRESS_LEAD` 0.0): Demons press every fight already (`profiles.PRESS[DEMON]` 1.0), but upstream's press holds with two or more men in view. A Halo 4 Demon now walks in on its man there too when even on the vitals, its shield at his or over, and its fight odds (teammates counted) 1.25 or better. With one man in view the rule is as before.

Melee checked, not changed: within `MELEE_R` 1.25 u it pressed melee on 5-6% of rows, one per 0.6-0.9 s swing at about 25 rows a second. `push_in` already walks it in on a man whose shield is down within 8 u.

Validation: `tools/test_demon_odds.py` adds 8 tests, 45 in the file:
- `SpreadTests`: a teammate's winning kill scores half with no team-shot lift; a committed Demon turns to the man nobody has; a losing or stale teammate still gets help; other tiers and games unchanged.
- `PressTests`: two in view, ahead and winning, it walks in; behind or losing it holds; one man as before; Legendary and Reach Demon keep the hold.
- 448 of 449 regression tests pass. The failure is the same `test_h4_reports_nov8.py` `test_owner_spots` on the uncommitted Gore Valley patrol points.
- Gameplay is untested; the next match's bot process loads it.

### Halo 4 Demon keeps a loaded rifle over a slower gun up close, 2026-11-08

- The owner's Haven 1v1 against one Demon (h4_wraparound 20261108-185123, 7-5 to the Demon on the scoreboard). With its 3 sniper kills and the owner's 2 sniper openers set aside (one hit from full to 11% body, and to about half), the 7 straight fights went Demon 4, owner 3.
  - The Demon's 4: it hit first and kept firing, about 13 presses a second, dealing 0.83-1.06 of shield plus body a second to the owner's 0.41-0.51.
  - The owner's 3: a BR fight at 17.6 u (0.62 a second to his 1.24), and two Boltshot swaps up close.
  - 167.3 s: at 2.5 u, with his shield at 36% and its own at 61%, it stopped a loaded BR (30 rounds; about 0.7 s from the kill), swapped to the Boltshot and held its charge 0.75 s. The magazine stayed at 10, and it died after about 1.2 s with no damage dealt.
  - 125.3 s: stuck 4 s in a pocket on the lower level (-2.8, -3.9; "unstuck wiggle, try 5 at this spot"), then the Boltshot at 1.9 u, dead 0.4 s on.
- Cause: `choose_weapon`'s range score lifts close-quarters guns inside `CLOSE` 2.5 u (+2) and drops a rifle there (-1). Its "finish him" hold keeps the gun in hand only at his shield 25% or under.
- `brain/bot.py` `keeps_gun`: for a Halo 4 fixed Demon mid-fight with the gun in hand loaded, a range or best-gun swap goes through only if the other gun kills him sooner as he is now (`odds.kill_time`), counting `H4_SWAP_S` 0.5 s and its `CHARGE` time. Example: BR at 2 u on a full man 1.35 s against the Boltshot 1.2 + 0.5 + 1.0; a shotgun 0.25 + 0.5 still comes out. Dry and empty-magazine swaps, other tiers and other games are unchanged.
- Not changed: the lower-level stuck pocket on Haven, and the BR fight lost at 17.6 u.
- Validation: `tools/test_demon_odds.py` `KeepGunTests`, 4 new tests (the BR kept over the Boltshot at 2 u, his shield 36% or full; a shotgun still comes out; an empty magazine still swaps; Legendary and Reach Demon swap as before); 37 in the file.
  - 440 of 441 regression tests pass. The failure is the same `test_h4_reports_nov8.py` `test_owner_spots` on the uncommitted Gore Valley patrol points.
  - Gameplay is untested. The bot process must be restarted.

### Halo 4 Demon's fight odds count its teammates, 2026-11-08

The owner, Nov 8: "The demon bots can beat me in a 1v1 but in a team enviroment they struggle".

- Haven 20261108-182020, 64 Demon deaths:
  - At its death the nearest Demon teammate was a median 4.7 u off (none within 15 u in 6%). But a teammate fired on one of its shooters in the 3 s before in only 33%, and a shooter died within 3 s after in 23%. The teammates within 15 u were mostly hunting (38) or on an objective (28); 12 were fighting a shooter.
  - The odds judged each Demon alone. Another Demon was within 15 u in 94% of its 203 dropped hunts into a group, 91% of its 92 break-offs and 92% of its 49 men not taken on. The Demons were as many as the enemies or more within 20 u in 90%, 74% and 86% of those.
- `brain/odds.py` `with_help`: the time to kill a man with teammates on him too; the paces add up.
- `brain/bot.py`:
  - `TEAM_EYES`: every bot posts the enemies in its view each tick (`share_sightings`), with its accuracy share: a fixed Demon `DEMON_ACC`, another bot `ACC[False]`.
  - `mate_kill_times`: in `odds_threats`, each enemy's kill time counts the teammates on foot whose post is under `TEAM_FRESH` 0.3 s old and has him in it, at their gun's time over their accuracy. This covers all of `demon_odds_rules` (break-off, men not taken on, hunts into a group) and `chase_ok`.
  - `ODDS_BREAK` 0.5 to 0.6 (0.85 while breaking).
- Replay (scratchpad `odds_replay_team.py`; teammates' eyes from their think rows; Haven 182020, Haven 183706, Blood Crash 013418 and 141550, Redoubt, Canyon: 243 Demon deaths, 375 Demon kills):

  | odds | deaths flagged 0.75-4 s before | wins it would have left |
  |---|---|---|
  | alone, line 0.5 (before) | 60% | 20.9% |
  | with teammates who see him, 0.5 | 55% | 16.6% |
  | with teammates who see him, 0.6 (now) | 64% | 20.5% |

  Every Demon teammate within 8 u counted as on him flagged too few: 20% of Haven 182020's deaths.
- Haven 20261108-183706, the first match with the run-to-cover fix below: 33% of the 36 break-offs died within 5 s (46% before). Retreat rows aiming at a man had a walk under 0.8 in 14% (34% before), mean 0.93 (0.84). The walk to cover still averaged 1.44 u/s. The rows not aiming include 33% standing in cover; the rest are mostly slowed by the 60-degree turn rule (upstream; not changed).
- Validation: `tools/test_demon_odds.py` `TeamOddsTests`, 5 new tests (a mate with both enemies in view lifts two on one over the line; a stale, riding, dead or not-looking mate does not count; no break-off while a mate fights them, one without; `with_help`; every bot posts its eyes); 33 in the file.
  - 436 of 437 regression tests pass. The failure is the same `test_h4_reports_nov8.py` `test_owner_spots` on the uncommitted Gore Valley patrol points.
  - Gameplay is untested. The bot process must be restarted.

### Halo 4 Demon's break-offs run to cover at full speed, 2026-11-08

- First live matches with the fight odds below:
  - Gore Valley 20261108-181229 does not count: the LiDAR Simulator mapped Gore Valley in the background through the whole match (its log: 634 s, done 18:19). Every bot thought 7.4 times a second (21-25 in today's other 15-bot matches, 12-15 on Gore Valley Nov 7), and the owner, 34-4, saw Demons miss his strafes.
  - Haven (h4_wraparound) 20261108-182020, the owner and three bots against four Demons, at the full 24.7 a second. The owner went 50-40 and the Demons 90-64. One on one, Demons beat him in 10 of 14 (14 of 36 before), and he lost 0.40 of his shield and body per second of Demon fire (0.29 in Blood Crash 20261108-152614).
  - Break-offs: odds under the line came in the 4 s before 61% of Demon deaths (the replay's 60%). But 43 of 94 break-offs died within 5 s: a median 1.2 u moved in 1.65 s, against 3.2 u for the 51 that lived. Once at its cover an enemy's sights were on it in 7% of rows, and it lost 0.06 of its vitals a second there.
- Cause: on a retreat with a man in view, upstream mixes the walk's strafe 0.6 with a juke's 0.4. A walk to the side against the juke came out at 0.2 (a (-0.36, -0.93) walk sent as (-0.36, -0.16)), and the walk to cover averaged 1.39 u/s.
- `brain/bot.py` `retreat_juke`: for Halo 4 fixed Demon the juke (`RETREAT_JUKE` 0.4) goes at right angles to the walk, and the walk stays at full speed (0.93 of it toward the cover). Every other tier and game keeps upstream's mix.
- Validation: `tools/test_demon_odds.py` `RetreatJukeTests`, 3 new tests (full speed to the side with either juke, the juke still swings the walk, other tiers and games keep the mix); 28 in the file.
  - 431 of 432 regression tests pass. `test_h4_reports_nov8.py` `test_owner_spots` fails on the uncommitted `maps/h4_ca_gore_valley/infantry_patrols.json`, which has 6 more patrol points than the 3 it expects (Edit spots data, not this change).
  - Gameplay is untested. The bot process must be restarted.

### Halo 4 Demon picks its fights by the odds: breaks off losing fights, no peeking while one shot, no chasing hurt; the team's sightings, 2026-11-08

The owner, Nov 8: Demons "die in silly ways, they play recklessly they pursue losing fights, they challenge another player even when one shot. Make this next line of code incredibly hard to beat." His answers: radar plus teammates' sightings (no wallhack), Halo 4 Demon only.

- What killed them: 398 Halo 4 Demon deaths over 16 matches (K/D 1.48; the owner made 133 of the kills).
  - 55% outnumbered (two or more firing). 96 of 217 walked in with two or more in view; 121 were collapsed on. After the second shooter opened up it had a median 2.0 s, and chose a fight 55%, a hunt 24%, a retreat 11%; one was scored in 105.
  - 17% fought on with its shield gone and body under 70%; 12% chased a man out of sight while hurt; 34% died within 1.5 s of full.
  - Against the owner one on one (36 fights) it won 14. With him in view its aim was on him 73-81% of rows (off rows were mostly a blocked line, 1.4-1.7° off), and it pressed the trigger 15 times a second. But he killed it in a median 1.08 s from his first hit, against its 1.58 s on him.
- `brain/odds.py` (new), the model, judged by the SHIELD (the owner, Nov 8: "In Halo you break their shields and then they become one shot to the head. So I think we should make them judge fights based on shield pools instead of a health pool"):
  - How each gun kills (`H4_GUNS`, Halo 4 times from full with every shot landing, three times as long past the gun's reach):
    - A precision gun (BR, DMR, Light Rifle, Carbine, Magnum): his shield's share of the strip time plus one finishing headshot (`FINISH`, 0.25-0.45 s). His body does not count, and with no shields it is the headshot alone.
    - An automatic or a spray (AR, Storm Rifle, Suppressor, Needler, SAW, Plasma Pistol, Boltshot uncharged): the pool's share (shield 70, body 45).
    - A power gun or blade: its fixed time.
    - A rider: a vehicle gun on the pool.
  - Each man's time is over his accuracy (`ACC`: a person 0.8, a bot 0.15). A man not aware of it (not aiming within 0.35 rad, not the one who hit it) starts 0.45 s late, and one not in sight 0.6 s later still.
  - It kills them one at a time, quickest first, at its own pace (`DEMON_ACC` 1.0). Each one alive adds his time's share of a kill on it, and the odds are 1 over the share taken before the last falls.
  - Readings against the owner aware with a BR at 10 u: full against full 1.25. Its shield gone, body full: 0.28 (the pool model read about 0.7), and 0.42 with him not looking. Full against him with his shield down: 5.6.
- Calibration (scratchpad `odds_replay.py`, 5 matches, 135 Demon deaths, 215 Demon kills): with the shield model, odds under 0.5 came in the 0.75-4 s before 60% of its deaths and in 15% of the fights it went on to win. With a 0.25 s hold it was 53% and 10%; the pool model's best was 59% and 16%; the first guess (bots 0.5, line 0.85) was 81% and 50%.
- `brain/bot.py` `demon_odds_rules` (after `stand_ground` in `decide`; Halo 4 fixed Demon on foot, not carrying, not in Race or Infection):
  - Losing (under `ODDS_BREAK` 0.5, no hold, `ODDS_PERSIST` 0; under 0.75 while breaking, `ODDS_BREAK_HOLD` 1.5 s) against a man aware of it: it goes to cover it can reach (`ODDS_RUN` 2.25 u/s) within `ODDS_REACH_SHARE` 1.25 of the time it has under the aware men's fire (`time_left`, by its shield). That retreat scores `ODDS_BREAK_SCORE` 3.6, over the committed fight, the close-fight lift and the 3.2 turns; hunts are dropped and the recharge hold set. With no such cover, it fights it out as before.
  - A man in sight not aware of it that it would not beat (under `ODDS_ENGAGE` 1.25) gets no fight; it goes to cover within `ODDS_HIDE_R` 10 u from him (2.4).
  - A hunt toward two or more known enemies it would lose to all at once, judged from where the hunt goes, is dropped.
- `chase_ok`: a man out of sight is chased (`demon_commit`'s gap, the carried target, `decide`'s commit score) only with `CHASE_MIN` 60% of its shield (its body without shields), odds over him alone (round the corner, aware) of 1.3 or better, and no other enemy known within 12 u of where he went.
- `share_sightings` (`TEAM_SIGHTINGS`): every bot posts the enemies in its view each tick. A Halo 4 Demon takes its teammates' under 0.3 s old as exact "team" beliefs, where its own are older and he is not in its view. Bot teammates only: a person's view is not read.
- Not changed: its aim and trigger (the measured on-target share and press rate above). Its slower kills on the owner remain open; the trace cannot show where each round lands.
- Validation: new `tools/test_demon_odds.py`, 25 tests:
  - Model: full against a full person aware is a slight edge; a man not looking is taken; one shot is not; two people on it lose; two bots on a full Demon is taken; a cracked man is finished; a shotgun out of reach.
  - Shields: the kill times (a BR on a bare shield is the finishing shot; an AR still needs the body; a sniper is fixed; SWAT is the headshot); shields down with a full body is one shot, not peeked and broken off; his shield down is a kill to take; an automatic weighs the body; the chase goes by the shield.
  - Rules: a break to cover in reach after the hold, the hunt dropped; no way out fights on; cover out of reach in time is no way out; one shot does not peek; full takes a man not looking; a hunt into a group dropped; Legendary and Reach Demon unchanged.
  - Chase: healthy alone chases; hurt or into his friend does not; others unchanged. Team sightings: a Demon takes them; stale ones and other tiers do not.
  - All 425 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Banshee runs last through a target switch and pilots do not leave a dive for a tracker dot; Halo 4 Banshee aims at the chest from its camera, 2026-11-08

The owner, after testing the dive fix: "The banshee doesnt do its strafe run long enough, also it shoots just above the head, so its shooting too high, and also the ghost shoots too high against infatry."

- Run length (`brain/bot.py` `air_pass`, every tier):
  - A new target in the middle of a dive, or a fresh run, now dives at once when the man is ahead and `AIR_RUN_FROM` 8 u or more off. Only a man behind, or closer than that, starts on the way out. A target switch mid-dive keeps the dive's clock.
  - Before, every new target under `PASS_START` 15 u began with the way out, `PASS_OUT_S` 6 s with the guns off. Live Blood Crash `20261108-151434`: 9 of a Demon pilot's 16 runs ended on a target switch, median run 0.13 s, 90th percentile 1.25 s. 4 more ended on the fight being dropped (to a path), which is not changed here.
- Pilots and tracker dots (`brain/bot.py` `decide`, `piloting`, every tier from Heroic up): the radar-dot check (a 3.2 hunt for Demon out to `DEMON_RADAR_TURN_R` 12 u, 3.5 u for the others) no longer runs at an aircraft's controls. From the air the men under it are tracker dots all the time, and that hunt beat the fight (1.78) mid-dive. Live Blood Crash `20261108-152614`, the first match with the run fix: runs now lasted 1-2.4 s and mostly ended passing over the man, but a Demon pilot's runs turned into a "path" to a dot 4 times in its first 30 s.
- Banshee aim height (`brain/vehicles.py` `H4_DRIVER_AIM`, `h4_driver_aim`; `brain/bot.py` `h4_origin`; Halo 4, every tier):
  - The Banshee had no seat view at all, so it fell back to the generic chest, his place + 0.35, which is over a Halo 4 Spartan's head. It now aims at his real chest (`h4_aim_point`) from its camera anchor, `banshee_d_camera` (-0.104, 0, 0.595) in the vehicle's frame. That comes from `tools/map_tools/model2obj --skin` on `ca_blood_crash.map` (`storm_banshee`), the marker through its bone's bind pose; the conventions were checked against the Warthog's turret marker that `h4_warthog_gun_origin` uses.
- The Ghost keeps its captured seat view (`H4_SEAT_VIEW`, at the origin). Its own `ghost_d_camera` (0.496 u up) was tried and taken back the same day. Aimed from it in `20261108-152614`, Ghost drivers made 0.6 kills a minute at the controls, against 1.3-2.2 in the four Blood Crash matches before. A man 10-20 u off took damage after 5% of their fire rows (25% before). The owner's "the ghost shoots too high against infantry" is still open.
- Validation: `tools/test_demon_vehicles.py` adds 8 tests: a new man ahead mid-dive keeps the dive and its clock, a fresh run on a man ahead dives, a man behind or under 8 u starts on the way out, the Banshee driver aims from its camera anchor while the Ghost and a Mongoose keep their seat views, `piloting`, and a Demon's radar hunt on foot but not in the air. `tools/test_h4_vehicle_aim.py` is unchanged. All 397 regression tests pass. The aim was confirmed live (the pitch follows the new line within about 1°); its effect on the Banshee's hits is not measured (0 kills either way, small samples). The bot process must be restarted.

### Banshee strafe runs dive like the owner's: slower in gun range, lower before they end, 2026-11-08

The owner flew the Banshee in Halo 4 Blood Crash `20261108-144947` to show the way (his F9s "This is how you should use the banshee" and "This is how to use the banshee bomb and cannons"): "they make their shooting floor too high, so they can never actually do a strafe run". His 63 rows with the crosshair on a man: 10-19 u off (median 13.5), 4.6-9.6 u over the floor (median 7.1, lowest 2.6), nose 23-46° down (median 34°), 4.6-10 u/s (median 5.8). Every tier, `brain/bot.py` `air_pass`:

- In gun range (`CANNON_R`), the dive is governed to `AIR_RUN_SPEED` 6 u/s: throttle `1 - (speed - 6) * 0.25`, down to `AIR_RUN_THROTTLE_MIN` 0.15. At full throttle, about 12 u/s, `air_guard`'s run check (the path 1.2 s down the nose under 1.5 u of the floor) would have pulled him out on 44 of his 63 shooting rows, ending the run before a shot. At 6 u/s it is 8. The check itself is unchanged. It is a governor, not a set throttle, so Reach's Banshee (4.3 u/s unboosted) keeps its throttle.
- A run ends by height only under `AIR_RUN_LOW` 2.5 u within 12 u of the man (was 5 u: it would have cut 7 of his shooting rows).
- Not changed: the bomb. His second report shows the bomb with the cannons, but the trace records no buttons for a person, so his bomb timing could not be read. The existing Halo 4 bomb cycle stays (`FUELROD_R` 10-31 u, from 2 u or more over the man).
- Validation: replayed over his 63 shooting rows, the run check passes 55 at the governed speed against 19 at full throttle. `tools/test_demon_vehicles.py` adds 3 tests: a fast dive in range throttles down, one at his speed keeps the throttle, and a dive 3.5 u up 10 u off goes on while one under 2.5 u ends. All 389 regression tests pass. No bot flew in that match, so live gameplay is untested. The bot process must be restarted.

### Halo 4 gun ammo read: empty guns are switched off, reloads work, 2026-11-08

- `brain/live.py` `LiveH4F.H4_AMMO`: a Halo 4 gun's reserve at +0x5AA and loaded rounds at +0x5AE (int16), Halo 4 only (`AMMO_AT` / `MAG_AT` properties by the dll; H2A stays unread). `players()` now fills each player's `ammo` (reserve + loaded) and `mag`.
- Before, every Halo 4 gun read unknown, so no Halo 4 bot ever knew a gun was empty. The owner's F9 "Bot didnt switch weapons after out of ammo" (Blood Crash `20261108-141550`, about 104-115 s): a Legendary pressed an empty rocket launcher 9 times at 5-7 u while his shield never moved. Now the existing rules apply in Halo 4: "dry: switch to a loaded gun", "empty magazine mid-fight: switch", reloads between fights, and rearming at a loose gun.
- Found live with two read-only scans of every held gun in a running Blood Crash match. In 11 of 11 reloads, +0x5AE gained exactly what +0x5AA lost (BR 0 -> 36, carbine 0 -> 18, sniper 0 -> 4, DMR 5 -> 14), and +0x5AE fell one per DMR shot. Spawn guns read BR 36 + 72, Light Rifle 36 + 72, Boltshot 10 + 20, Magnum 8, and an emptied BR 0 + 0. Read back through the patched reader in the same match, every living player's guns gave plausible counts.
- A gun kind never seen with a round (the sword) stays unknown, as before. Battery weapons (Plasma Pistol, Storm Rifle) were not held during the scans, so how they read is unchecked.
- Validation: new `tools/test_h4_ammo.py`, 4 tests: the offsets on fake memory, an emptied gun reads dry, a never-loaded kind reads unknown, H2A stays unread, and an empty rocket launcher is switched off for the rifle. All 386 regression tests pass. Gameplay with the bots is untested. The bot process must be restarted.

### Reloads out of a fight: topped off at 80%, in a retreat too, 2026-11-08

The owner met "too many bots that reload mid fight" and asked that they reload "when they have the appropriate time, like retreating, or patrolling, whenever they arent fighting". Every tier, `brain/bot.py`:

- `reload_check` tops off a magazine at `RELOAD_TOP_OFF` 0.8 of the most it has held or less (was 0.4), so the next fight starts on a near-full magazine. It still never reloads with a man in view, and now also not within `RELOAD_QUIET` 1.5 s of being hit (a man unseen shooting it), nor with no reserve.
- `plan` runs `reload_check` in a retreat too, not only on patrols, hunts, objectives and roaming. A fight goal still never reloads.
- `choose_weapon`'s "reload the empty one" (the pocket gun with an empty magazine comes out to be reloaded) runs in a retreat too, nobody in view.
- Halo 4 is covered once its ammo is read (the entry above).
- Validation: new `tools/test_reload_timing.py`, 5 tests: top-off for every tier, a near-full magazine waits, none with a man in view or within 0.75 s of a hit, none without reserve, the empty pocket gun out in a retreat. All 382 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Banshee pilots shoot under a low roof; Demon leaves a dying Ghost, backs off with only a sidearm, and plays Slayer in pairs, 2026-11-08

Taken from the owner's Blood Crash match `20261108-024522`, where his teammates got about 8–9 of the 15 Demon deaths. Two Demon pilots fired 7 shots in 10 s in a Banshee and were shot down. Camper25 died in a Ghost at 6% health. Havoc94 left a Ghost holding only a Boltshot and a Magnum and lost a 3 on 1. The two Demons were within 8 u of each other 18% of the match.

- Banshee, every tier (`brain/bot.py`):
  - `air_ceiling` gives the highest an aircraft may fly: the map's roof less `AIR_ROOF_M`, capped by the owner's flight envelope. `air_roof_guard` now uses it too.
  - `air_pass` caps the next run's start height at the room under that ceiling less `AIR_ROOM_SPARE` 1.0, and never under `AIR_ROOM_MIN` 4.0 u over the floor. Blood Crash's soft kill from z 12.18 held pilots under 9.7 z. The 11 u start height was never reached, so every way out ran its full `PASS_OUT_S` 6 s with the guns off. That was 567 of 1778 Demon pilot rows, while the pull-up fought the roof guard.
  - `air_snap_fire` (new) runs after the guards and before `fire_gate`. A pilot fires when its nose, after every guard has steered it, is within `AIR_GUN_R` of an enemy inside `CANNON_R` with a clear line. It skips gunners and bomb or fuel-rod cycles. In range, the wall guards had turned the nose on 337 of 461 run rows, which fired 10% of the time against 47% for the others.
- Demon only:
  - `may_drive` refuses a Ghost at `DEMON_GHOST_BAIL` 0.20 of its body left or less (`ghost_spent`), using the snapshot's `left`. A Demon at its wheel gets out with Use held, notes "vehicle: Ghost nearly gone, out", and isn't allowed back for 20 s. Other vehicles, a tank too, go down with their driver: the owner's choice.
  - `sidearm_cover` (new): holding nothing but sidearms (`DEMON_SIDEARMS`: Magnum, Boltshot, Plasma Pistol) with an enemy in sight and none within `DEMON_STAND_R`, it retreats to cover within 12 u at `DEMON_SIDEARM_SCORE` 3.0. A man right on it is still fought.
- Team Slayer, Demon (`brain/director.py`):
  - `demon_pairs` pairs each fixed Demon with another Demon first, else a fixed Legendary. The lower id of two Demons leads.
  - `pair_orders` runs after the infantry patrols and gives the mate its lead's job (`mid`, `hunter` or `free`), a point `PAIR_GAP` 3 u off the lead's (`spread`), the same route, and the lead's patrol. It passes `sure=True`, so the mate has no rogue moment.
  - It is skipped while either one rides, carries, is on a power run, or the lead's job is another.
  - `infantry_patrol_orders` gives mates no patrol of their own.
- Validation:
  - New `tools/test_demon_vehicles.py`, 18 tests: the low-roof way out turns back and still climbs where there is room; snap shots for every tier, none off the nose, out of range, without a line, as a gunner or mid-bomb; the Ghost bail for Demon only (a tank and Legendary unchanged); the sidearm retreat; pairs, patrol sharing, no pair in a vehicle, outside Slayer or without a partner. All 377 regression tests pass.
  - Replayed over the match's 1778 pilot rows, the snap shot adds about 55 firing rows to the 92 fired, before the clear-line check. The ceiling fix changes the flight path, so it can't be replayed.
  - Gameplay is untested. The bot process must be restarted.

### Halo 4 weapon ranks, second pass: the SAW a power weapon, 2026-11-08

- `brain/bot.py` `RANK_GAME["h4"]`: SAW (`lmg`) 4.0, Light Rifle 3.6, Shotgun and Scattershot 3.4 (Halo 4 only).
- `brain/maps.py` `H4_ORDNANCE`: the SAW is a power drop at 0.8 (the Railgun's), so a teammate now goes for it like the other power drops (`director.power_runs`) instead of taking it only when it passes by.
- Validation: the ranks resolve as set, and Reach's shotgun stays at 3.0. `tools/test_h4_ordnance.py`'s Redoubt power-drop list now includes the SAW. All 359 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 weapon ranks: the owner's power-weapon order, Storm Rifle and Suppressor ranked, 2026-11-08

- `brain/bot.py` `RANK_GAME["h4"]` (Halo 4 only; other games unchanged): Incineration Cannon, Sniper Rifle and Beam Rifle 5.0, Rocket Launcher 4.9, Binary Rifle 4.8, Spartan Laser 4.5, Railgun and Fuel Rod Cannon 4.2, Energy Sword and Gravity Hammer 3.8.
- `WEAPON_RANK`: `storm_rifle` 2.2 and `suppressor` 1.8. Halo 4's live tags `storm_assault_carbine` and `storm_forerunner_smg` read as those names (`live.py` `TAG_ALIAS`, a single lookup), and neither had a rank, so both fell to the 1.0 default and were dropped for almost any gun.
- These ranks decide which gun a bot picks up and which one it drops. The power-weapon threat and regroup checks still read `WEAPON_RANK` directly (4.0 or more), so a Halo 4 Sword or Hammer at 3.8 still counts there as a power weapon.
- Validation: each Halo 4 tag resolved to its new rank through `TAG_ALIAS` and `RANK_GAME`, and Reach's rockets stay at 5.0. All 359 regression tests pass. Gameplay is untested. The bot process must be restarted.

## 0.2.2-custom.10 — Halo 4 ordnance pickups, hijack boarding, power vehicles, Forge shapes, 2026-11-08

- Covers the 8 commits since 0.2.2-custom.9 (d9ced49), none on GitHub before: 7 from this Claude session, and the Forge piece shapes (8e9f848) from a second session the owner started. Each entry below gives its own behavior and validation.
- Halo 4 ordnance: bots see a gun in its drop pod as lying loose, know the map's initial drops (gone once seen taken) and send a runner to a random drop's power gun. They hold Use on a gun, and botcore gives each bot its own pickup slot, so it no longer takes what the player is prompted for. The Light Rifle, Boltshot, Suppressor and Storm Rifle, plus the Incineration Cannon and Binary Rifle, read under the brain's names.
- Halo 4 vehicles: botcore seats a boarder on an enemy vehicle's boarding spot, and bots no longer freeze by a tilted vehicle. A bot the director calls to a vehicle goes even with nothing else scored. Fixed Legendary and Demon go first for power vehicles, over power-weapon runs and gun seats.
- Maps: Halo 4's Forge canvases are read as canvases, and Forge pieces get shapes from MCC's own map files (local data; run `tools/h4_forge_shapes.py` once per PC). Owner hot spots and patrol areas on Cliffside, a hot spot on Blood Cavern.
- Native: `native/h4f.cpp` and `shared.h`; the owner's DLL is built locally as `native/bin/botcore_pickup.dll` (not in Git). Other PCs build it with `native\build.bat <tag>`.
- Validation at the candidate: all 359 regression tests pass.
  - In game, Blood Crash 20261108-024522, on `botcore_pickup.dll`: the owner reported that it all seems to work. botcore's log shows 14 guns handed to bots on the first tick of the hold, 29 offers let go after 3 s and no fault. Bots gained 4 snipers, 5 rockets and 2 SAWs where they stood, the two sniper pods and the rockets pod among them.
  - The previous match (20261108-021511, the boarding DLL): 20 of 22 boards with Use pressed got the bot into the enemy's vehicle, but Halo 4's hijack does not run that way, so the driver mostly stays (left as is, the owner's choice).
  - Not separately checked in game: the power-vehicle priorities, the Forge shapes, and the Cliffside and Blood Cavern spots.

### Halo 4 bots no longer take what the player is prompted to pick up; Blood Cavern hot spot, 2026-11-08

- The owner's reports from Blood Crash (20261108-021511, the first match with the hold-Use pickups and the boarding DLL): "Ordanance drops are disapperaing. I dont know if the bots are using them but not obtaining the weapon" (100.8 s), and "Medic went to pick up rockets, left the pad and I went to pick it up and the display left" (187.1 s).
- Findings:
  - Bots held Use on the pods and got nothing: bot 9 2 s at 0.4 u from the Rockets, bot 4 1.5 s at a Sniper, bot 8 2.1 s at the other Sniper (70.1-72.2 s).
  - Bot 8 got a sniper at 72.25 s, the moment the owner came within reach of the other sniper pod 38 u away (2.05 u at 70.2 s, 1.58 at 71.8, 0.41 at 72.6).
  - Cause: botcore copies the player's own action as every bot's template each tick (`native/h4f.cpp` `f_update`, "the player's as the template"), his interaction slots with it, his pickup prompt. A bot holding Use took what he was prompted for, from wherever it stood; a drop he walked up to emptied in front of him. A bot already holding that gun takes it as ammo, which fits the rockets gone with nobody new holding them. H2A replaces those slots (`f_interaction`); Halo 4 did not.
- `native/h4f.cpp`: `f_interaction`, its held Use and its quiet after a pickup now run for Halo 4 too (H2A's multiplayer is Halo 4's engine). Every bot's interaction slots are cleared each tick, and while it holds Use on foot with no seat asked it is offered its own nearest loose gun within 1 u (a pod's gun counts as loose: `f_holder`, parent not a unit), the same one until taken, up to 3 s. Its log line now reads "pickup:" in both games. Built as `native/bin/botcore_pickup.dll` (`native\build.bat pickup`; no new warnings; `panel_art.py` failed after it as before).
- Blood Cavern (20261108-015141, 130.5 s, "Mark this as a hotspot"): an owner power position at (8.36, 1.47, 4.27), score 1.0, reached from all 292 spawns.
- The boarding DLL in that match: 27 bots were seated on boarding spots ("in"), none refused, no fault. A board with Use pressed got the bot into the enemy's vehicle 20 of 22 times (4 of 100 before). But the enemy driver mostly stayed: out within 4 s in about 6 of 25 boards, while the boarder rode the spot meleeing for up to 15 s. Seating a bot on the spot does not run the game's hijack. No change here.
- Validation: a source check in `tools/test_h4_pickup_board.py` (Halo 4 calls `f_interaction` and gets its held Use and quiet), and the Blood Cavern row in `tools/test_h4_reports_nov8.py`. All 359 regression tests pass. Not verified in game: whether Halo 4 takes a gun offered this way (H2A does, with the same slot type) and that bots now leave the player's pickups alone. MCC must be restarted to load the new DLL.

### Halo 4 Forge pieces' shapes read from MCC's own map files, 2026-11-08

- Follows the Ravine report below ("Bots arent reading this as a wall. Or a base."): 23 of the 39 piece kinds in the owner's Ravine layout had no shape in `maps/_shapes/h4.json`, so the nav had no wall or floor for the round base he stood by, the 3-story tower, the window wall, platforms, bridges and ramps (`forge.block`: no shape, no block).
- Source: MCC's own Halo 4 `.map` files (read only; no game running, no memory read). Their collision models keep no surfaces: every Forge piece's collision BSP blocks are empty (1 of Ravine's 645 collision models has any). New `tools/h4_forge_shapes.py` (its own reader of the cache file; no map-tools or Reclaimer code) reads each piece's physics model instead, what the game moves bodies against: Havok convex hulls, plane equations shrunk by a convex radius (the 1x1 flat platform: 0.4836 + 0.0164 = the kit's 0.5). Pushed out by the radius and closed by each hull's vertex box, the hulls clip into faces; a face inside another hull of the piece, or back to back against one, is left out. Taken: each region's default permutation, collision layer 0, no phantoms. So gravity volumes, man cannon and lift pulls, lights and shield-door panes are not walls. Its docstring lists the offsets found.
- Data (map pack, gitignored, local only, not committed): `maps/_shapes/h4.json` and `h4_faces.json` get 259 pieces marked `"source": "physics_model"`: every solid kind in the Ravine layout, the rest of the four Forge canvases' palettes (Erosion's `fw_unsc_d_*`, Forge Island's missing `fi_*`), and Forge items of other maps. 30 names with no solid shape (skies, gravity volumes) join `no_collision`. The kit's 353 shapes and their faces are unchanged (compared with a backup). Faces file 7.1 MB to 19.0 MB. Another PC runs `python -I tools/h4_forge_shapes.py` once (Halo 4 installed in MCC).
- Checked against the kit (`--check`): of 245 pieces the kit has, itself or as their Forge Island twin (`fw_unsc_c_base_round` is `fi_unsc_c_base_round`), 243 boxes agree within 0.12 u (median 0). The 3-story tower, round base and bridges are exact. Worst: the kit's own `fw_damage_sphere` (2.1 u, not replaced) and `fw_cannon_vehicle` (0.23 u). Faces differ in detail: the kit's collision meshes keep slabs inside a piece (the walkway's at z 5.14, 5.3 and 5.55), the hulls only its outer surface; hulls are convex simplifications (a railing's lip reads as a slope).
- Ravine layout nav (`maps.get_map("h4_ca_forge_ravine/variants/vc736941c")`, the round base at (27.0, 17.3, -2.7)): before, 70 of its 117 pieces were in the nav and none of its four round bases; a path from 9 u on one side to 9 u on the other went straight through (39 points at ground level inside its box). After, 112 pieces. Chest-high sight lines across the base are blocked (3 of 3; 1 before), a bot walking in from 9 u out meets its wall after 3.5 u (none within 12 u before), and the path goes round it (22.0 u for 18 u; 9 points still inside its box near the edges, not checked against its doorways). Building that terrain takes 6.3 s (2.6 s before).
- Not verified: anything in game. Three pieces have bodies on a node other than the root (jersey barriers, large palette, vehicle barrier) and are placed as if at the root; their Forge Island twins' boxes agree within 0.02 u. Built-in Halo 4 maps are unaffected: none of their exported placements uses these pieces, and only Forge canvases read pieces live. The Ravine layout's power positions and callouts were scored without these walls (`tools/variant_strategy.py` can score them again).
- Validation: `tools/test_h4_forge_shapes.py`, 11 tests. A box's six faces wind outward. Touching, stacked and overlapping hulls give their union's surface (42 for two 2 u cubes overlapping by 1). Flush tops stay, and string ids resolve across namespaces. A piece read this way goes into the nav face by face. Where this PC has them: the Ravine pieces have shapes, Ravine's map gives the kit's 1x1 flat platform and the round base's twin box, and gravity volumes and skies are not solid. In the local Ravine layout the round base blocks sight across and walking in. All 357 regression tests pass. Restart the bot process (shapes load at match start).

### Legendary and Demon go for power vehicles, over power weapons and gun seats, 2026-11-08

- The owner, on the entry below: "No make Legendary or Demon go for power vehicles and prioritize a power vehicle over power weapons, and gunner seats."
- Withdrawn: the Halo 4 band from 2074058 (`power_tiers`: rank only among bots within 10 u of the nearest). A power vehicle's driver is again picked by rank first in every game (`profiles.resource_priority`: Demon, Legendary, Heroic and Scaling, Normal), then by distance, within the director's 45 u reach (`CREW_REACH`). The decide fix from that entry stays: a called bot goes even with nothing else scored.
- `brain/director.py` `crew_orders`, every game, for a power vehicle a Demon may drive (`power_kind`: taken for a job, `vehicles.taxi_ok`, and not a gun Warthog, which Normal and Heroic drive):
  - A fixed Legendary or Demon on a power-weapon run is called to it. Before, a fetching Demon was left out of every vehicle job. Once it has the job, its run is dropped (`Bot.fetch`), and `power_runs` sends no fixed Legendary or Demon holding a power vehicle's job on another run.
  - A fixed Legendary or Demon riding a gun or a passenger seat of another vehicle is called to it too (`vehicle_orders` passes them in: alive, not carrying, not a ferry or escort, not urgent). `Bot.drive`: a seated bot whose drive order is for another, empty vehicle gets out (Use held, as every get-out) and walks to it.
  - Bot calls were already ordered vehicle jobs before gun calls in each role pass (`crew_orders` before the honk and gunner calls). The gunner calls skip a bot with a drive order (`gunner_available`).
- Halo 4 handover (`power_handover`): only a teammate ranked as high takes the job from the one on its way, when within 15 u of the vehicle and 15 u or more nearer. A Legendary who respawns by it takes it from a Legendary 40 u off; a Heroic does not.
- Validation: `tools/test_h4_power_vehicle.py`, now 11 tests. A called driver goes with nothing scored (Halo 4, Reach). A Legendary at 44.7 u is sent over a Heroic at 27.3 u (Halo 4, Reach), and a Demon at 40 u over a Normal at 10 u. A Legendary and a Demon on a rockets run are sent to a Wraith and their runs dropped; not for a gauss Warthog. A Legendary and a Demon in a Warthog's gun are called out to the Wraith; a Heroic is not. The handover goes to a Legendary or Demon by it, not to a Heroic, not to one hardly nearer, and not in Reach. `power_runs` gives the rockets to the Heroic, not the Legendary driving. A called gunner gets out with Use held. All 346 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Power vehicles: a called driver goes at once; Halo 4 sends the near one, 2026-11-08

- The owner, on Redoubt's "Red team Wraith spawn" report: bots do not go straight to the Wraith off spawn as they do to other vehicles, and as a power vehicle the team leader should send them to it.
- Redoubt 20261108-010650: every Ghost and Warthog spawn drew a rider in 5-20 s, often with several bots on their way. Each of the three Wraith spawns (0.4, 312, 626 s at red's base) had one bot sent, from 43-45 u away, and its first driver 23-37 s after the spawn. Bots never take a tank for a trip of their own (`vehicles.taxi_ok`), so the director's call (`Director.crew_orders`) is its only way to get a driver.
  - At the start the director did call one 1 s after spawn: OutlawMarine (Legendary) at 10.8 s. With nothing in sight and no objective, its `decide` had no scores and returned "roam" before reaching the order, so it walked the other way 7.5 s, until a hunt came up at 18.5 s. That is a bug in every game.
  - At the 312 s respawn the director sent OutlawMarine again from 44.7 u, over Rapid62 (Heroic) at 27.3 u: a power vehicle's driver went by rank first (Demon, Legendary, Heroic ...) at any distance in its 45 u reach. The job then stayed his for up to 30 s.
- Changes:
  - `brain/bot.py` `Bot.decide` (every game): with nothing scored, a bot with a ride, board or drive order still takes the order's branch (it goes for the vehicle when it is usable and within its range, as with other goals), and roams only if not.
  - `brain/director.py` `crew_orders` (Halo 4 only): a power vehicle's driver is ranked only among the bots within `POWER_TIER_BAND` (10 u) of the nearest one in reach (`power_tiers`); Demon and Legendary still win when about as near. A bot within `POWER_R` (15 u) of the empty power vehicle that is `POWER_HANDOVER` (15 u) or more nearer than the one on its way takes the job (`power_handover`: one who respawns by it). The far bot keeps the role order its pass gave it. Reach and the other games keep the rank-first pick and the 30 s job.
- Validation: `tools/test_h4_power_vehicle.py`, 7 tests: a Legendary sent to a Wraith with nothing else scored goes (Halo 4 and Reach); in Halo 4 a Heroic at 27 u is sent over a Legendary at 45 u, a Legendary at 34.8 u over a Heroic at 34 u, a Demon at 19 u over a Normal at 10 u; Reach still sends the Legendary; a teammate 5 u off takes the job from one 40 u off, one at 28 u does not, and Reach keeps the job. All 342 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 Forge canvases read as canvases; Cliffside's owner spots, 2026-11-08

- Ravine (the owner's report, 20261108-012136, 336.6 s: "Bots arent reading this as a wall. Or a base.", at a round UNSC base). Two causes:
  - Halo 4's Erosion, Ravine and Forge Island place one object of their own, `mp_cinematic_fallback_camera`. `variants.base_area` counted it as the map's layout, so a Forge layout on them was taken for a built-in map's variant: no layout callouts or power positions were made (`tools/live_bots.py` makes them only for an empty canvas), and `load_map` gave it the empty canvas's callouts (5 zones) and no power positions. `base_area` now leaves cameras out. Ravine's layout (`maps/h4_ca_forge_ravine/variants/vc736941c`, local data) then got its own: 8 scored power positions and its callouts (`tools/variant_strategy.py`, built offline in 6 s).
  - Not fixed here: 23 of the 39 piece kinds in that layout have no collision shape in `maps/_shapes/h4.json`, so the nav has no wall or floor for them. Among them: `fw_unsc_c_base_round` (the base he stood by), the 3-story tower, the 2x2 window wall, platforms, bridges and ramps. The shapes came from the Halo 4 editing kit's collision models through a tool this installation does not have, and the kit is not on this PC.
  - His hot spot on it (34.6 s, (1.15, -11.18, 3.21)) is an owner power position of that layout (`tools/power_positions.py --add`; local data, the variant folders are not in Git). `tools/variant_strategy.py` now keeps owner rows when a layout's positions are scored again (`power_positions.merge_owner`); it wrote over them before.
- Cliffside (report 20261108-001811), where he stood at each:
  - Hot spots, owner power positions (score 1.0; the 8 scored rows kept): (13.46, 0.05, 3.36), (45.42, 15.24, 2.39), (40.84, -6.51, 3.36), (40.71, -7.63, 6.56), (30.34, 9.71, 5.72).
  - Patrol areas, shared infantry patrol points (new `maps/h4_z05_cliffside/infantry_patrols.json`): (13.46, 0.05, 3.36), (53.28, -12.25, 3.27), (4.54, 0.2, 2.0).
  - All eight are reached from each of the 400 spawns checked, by the nav with people's jumps and rides.
  - "Go up these gravity lifts" (28 s, by the two lifts at y 13.34): his rides up them in that match were learned as two nav links (take-off y 14.5, z 0.8, to the ledge at z 3.37; `lidar.json`, local data). After the report, bots rode up 4 of their 16 trips past the lifts. The nav now routes up them toward the high spots above. No code change for this one.
- Redoubt (20261108-010650, 334.7 s, "Red team Wraith spawn"): no change. Red's Wraith spawns at (25.76, -15.69) at 0, 312 and 626 s; a red bot drove it each time (OutlawMarine, Legendary, ran 45 u across the map from 314 s and got in at 334 s, beside him). The report's intent is not clear from the data; asked.
- Validation: `tools/test_h4_reports_nov8.py`, 6 tests: a camera is no layout and Halo 4's three canvases have none; Ravine's layout loads its own positions (local data); a Ghost at up 0.43 / 0.5 / 0.57 is not boarded and an upright one is; Cliffside's patrols and owner rows load and the scored rows are kept. All 335 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 hijacks, held-Use pickups, and no frozen boarders by a tilted vehicle, 2026-11-08

- Hijacking (the owner: make Reach's boarding work in Halo 4). Reach's bots board an enemy's vehicle by its boarding seats (`vehicles.REACH_BOARD`, botcore's interaction) and the game runs the hijack. In Halo 4 the brain asked botcore for the driver's seat, and botcore's Halo 4 seat picker (`native/h4f.cpp` `f_board`) skips occupied seats and every boarding / hijack spot (seat flag bit 27). In his last four Halo 4 games 4 of 100 board attempts with Use pressed got in, all apparently after the driver had left; Reach 37 of 51, mostly on the first press. botcore's log lists the Halo 4 spots: the Ghost 3, the Warthog 3 and its gun 1, the Mongoose 2, a tank's more.
  - `native/shared.h` `HB_SEAT_BOARD` (14) and `brain/vehicles.py` `H4_BOARD_SEAT`: the seat number that asks for a boarding spot. `brain/bot.py` plan's board: Halo 4 asks it (Reach its boarding seats as before, the other games the driver's).
  - `native/h4f.cpp` `f_board` (Halo 4 only, that seat asked): the vehicle's free boarding spots that the game's own seat test lets this unit take, the vehicle's own before its gun's, a different one each try (every 15 ticks while Use is held), entered by the same call as any seat. None to take: logged once per 3 s with the counts (spots, taken, refused). The call is untested with a boarding spot, so it is guarded: a fault turns boarding off for the run and is logged. Other seats, H2A and the other games are unchanged.
  - After boarding, the existing step applies (`Bot.drive`, an enemy still aboard): no movement, melee every 0.55 s, a grenade after 1 s outside Reach.
  - Built as `native/bin/botcore_board.dll` (`native\build.bat board`: no new warnings; `panel_art.py` failed after it as before, PIL missing, which does not affect the DLL). MCC still holds the older DLL; the launcher loads the newest `botcore*.dll` at its next start.
- Pickups (the owner's Blood Crash report, 20261108-013418, 255 s: "bots struggling to pick up the ordanance drop. Then I walk up to it and it shows how to pick it up"). The first match with the ordnance change: bots reached the pods (bot 4 101 ticks within 1.2 u of the Rockets, another 112 at a Sniper's) with the gun to swap out in hand and tapped Use six times a second for 3 s without a pickup. Halo 4's prompt asks for a hold, as botcore's H2A notes record ("requires a hold press not a tap"). `Bot.plan` at an item: Halo 4 holds Use; the other games keep the tap. The swap check (the hands changed: no more presses there) is unchanged. Ten bots had chased that one launcher for 200 s.
- Frozen boarders (the owner's Canyon report, 20261108-002354, 258.5 s: "Im not sure why they were frozen"). Bots 1 and 5 stood still 3 s at a time, no stick and no Use, choosing to board a red Ghost tilted on a ledge (up 0.43-0.57). `board_check` chose it every tick; plan's board refused it every tick (`vehicles.usable`: upright over 0.5) and asked for a new decision. `board_check` now skips a vehicle that is not usable or is under `BOARD_UPRIGHT` (0.6, a margin). botcore's Halo 4 boarding already passes over vehicles under 0.5.
- Validation: `tools/test_h4_pickup_board.py`, 5 tests through `plan` on stand-in open ground: Halo 4 holds Use on a gun 12 ticks in a row, Reach still taps; Halo 4 boards of a Ghost, Warthog, Mongoose and Scorpion ask the boarding-spot seat, Reach still cycles its boarding seats; the seat number matches `shared.h` and fits the 4-bit field. The tilted-vehicle tests are in `tools/test_h4_reports_nov8.py`. All 335 regression tests pass; botcore compiled. Gameplay is untested: whether Halo 4 runs its hijack when botcore seats a bot on a boarding spot, and whether a held Use takes a pod's gun, both need a match. MCC must be restarted for the new DLL; the bot process for the Python changes.

### Halo 4 loadout guns by the brain's names: Light Rifle, Boltshot, Suppressor, Storm Rifle, 2026-11-08

- Found while doing the ordnance work: Halo 4's live tags for four loadout guns did not match the names `brain/bot.py`'s tables use, so each read as a gun the brain does not know. Live tag names (Redoubt and Forge Ravine): `storm_forerunner_rifle` (Light Rifle), `storm_stasis_pistol` (Boltshot), `storm_forerunner_smg` (Suppressor), `storm_assault_carbine` (Storm Rifle). They read `forerunner_rifle`, `stasis_pistol`, `forerunner_smg` and `assault_carbine`, none of them in `PRECISION`, `AUTO`, `CHARGE`, `WEAPON_RANK` or `WEAPON_RANGE`. In his last three Halo 4 games, bots held the Boltshot under its old name for 75,080 to 189,369 trace ticks a game, from the first spawns on.
- Effects of the old names: a bot with the Light Rifle did not treat it as a precision rifle (no head aim; no Halo 4 Demon head lock, `h4_demon_fire`, which needs a gun in `H4_SNAP`). The Boltshot was no charge gun. The Suppressor and Storm Rifle were not automatics (no held trigger). Every one of them had the default range and rank, which upgrades and gun choice read.
- `brain/live.py` `TAG_ALIAS`: `forerunner_rifle` → `lightrifle`, `stasis_pistol` → `boltshot`, `forerunner_smg` → `suppressor`, `assault_carbine` → `storm_rifle`. These are the names the brain already lists: the Light Rifle in `PRECISION` (range 1.5-45 u, rank 3.5), the Boltshot in `CHARGE` (held 1 s, then released; range 0-8 u, rank 1.8), and the Suppressor and Storm Rifle in `AUTO`. The Halo 4 Demon tests already used `storm_rifle`. The older `TAG_ALIAS` entries `storm_rifle` → `plasma_rifle` and `suppressor` → `smg` never matched a live Halo 4 gun and are left as they were; mapping to those names would also have brought the CE plasma rifle's 37 u/s lead.
- Behavior this switches on, by the brain's existing rules: the Light Rifle gets the precision-rifle rules the BR and DMR get, and Halo 4 Demon locks it on the head and taps it as it does them. The Boltshot charges its shot. The Suppressor and Storm Rifle hold the trigger, with Halo 4 Demon's view lock. The protected Legendary and Demon DMR and sniper corrections are unchanged; the Light Rifle takes the general precision path, not those.
- Validation: `tools/test_h4_loadout_names.py`, 5 tests: the four live tags, what each name is in the brain's tables, that the old names were in none of them, Halo 4 Demon's head lock with the Light Rifle (none under its old name), and the Suppressor aimed at the body. Checked against the live game's tag list on Forge Ravine (read-only): all six Halo 4 guns renamed this session read as the brain's names. All 324 regression tests pass. Gameplay is untested. The bot process must be restarted.

### Halo 4 bots pick up ordnance, 2026-11-08

- The owner: Halo 4 has no weapon pickups like Reach or the other Halos; bots must find a way to take ordnance drops, most of which land like a weapon on the ground at fixed spots, and some randomly during the game.
- Findings:
  - Halo 4 bots never planned a trip to any gun. `Bot.decide`'s item goals, rearming, upgrades, the team's power runs and the anti-vehicle search are all gated on `can_pickup`, which `tools/live_bots.py` set only for CE, Halo 2, Halo 3 and Reach ("H2A / H4 pickups not decoded yet"). In his last three Halo 4 games (Canyon, Cliffside, Blood Crash): no item goal at all, and apart from loadout guns, power weapons held for 31 ticks in total.
  - Halo 4's Use does take a gun: both of those holds came from a Use press by a bot walking to board a Warthog, standing on a loose gun (Blood Crash 42.4 s, Rockets one tick after the press; Canyon 281.1 s, an Incineration Cannon). No native pickup code is needed, as the runners already take the flag with the same decoded Use.
  - The reader saw no ordnance. Live, read-only, on his Redoubt match (01:10): every ordnance gun (2 needlers, 2 snipers, a sticky detonator, Rockets) was attached to its drop pod, `unsc_weapons_pod_scenery`, an object of type 6. The loose-gun test (`LiveH2.ground_weapons`, parent must be none) counted each one as held. Each pod gun lay 0.2-0.4 u from one of the map's placements. The export already labels each placement `"ordnance": "initial"` or `"random"`: 5 of the 6 were initial drops and the Rockets a random one that fell in the first 3 minutes (an Incineration Cannon followed on the random point at (31.0, 9.9)).
  - Two ordnance guns read under names the brain does not know: `storm_forerunner_incineration_launcher` and `storm_forerunner_sniper_rifle` (Redoubt's tag names).
- Changes:
  - `brain/live.py` `LiveH4F.ground_weapons` (Halo 4 only): a gun is held only when its parent is a unit, a biped or a vehicle (type 0 or 1), as `native/h4f.cpp` `f_holder` counts it; a gun in its pod lies loose. H2A keeps the inherited reader. Live on Redoubt: 37 loose guns, where the old reader found 31 and none of the ordnance.
  - `brain/live.py` `TAG_ALIAS`: `forerunner_incineration_launcher` → `incineration_cannon`, `forerunner_sniper_rifle` → `binary_rifle`.
  - `brain/maps.py`: `H4_ORDNANCE` values for Halo 4's ordnance guns beside `POWER` (Incineration Cannon 0.9, Binary Rifle 0.85, Railgun 0.8, Scattershot 0.6, Concussion Rifle, Sticky Detonator and Shotgun 0.5; needlers, SAWs and grenade drops make no trip). On a Halo 4 map, `power_items` keeps the initial drops as items with `ordnance: "initial"` and `ORDNANCE_GONE` (no timed respawn: Infinity Slayer drops them once); random points are no items. `ordnance_power` lists the power guns (0.8 and up) the random points may bring, as `m["ordnance_power"]`.
  - `brain/director.py` `power_runs`: those names count as power, so a random drop of one gets the team's run. Its usual limits apply: Normal and up, one fetcher, 40 u (80 for fixed Legendary and Demon).
  - `tools/live_bots.py`: `PICKUP_GAMES` adds Halo 4 (`Bot.can_pickup`). `item_check`: an initial drop seen gone is gone; a gun lying loose on its spot again (the snapshot's loose list, not one in someone's hands) brings it back for both teams, as the game marks drops for everyone.
- Unchanged: H2A (no pickups), the other games' items and timers, and personal ordnance (no bot calls one in; one lying loose is a loose gun like any other).
- Validation:
  - `tools/test_h4_ordnance.py`, 11 tests: on a stand-in reader, a pod gun is loose and a held, mounted or empty one is not, H2A unchanged; the two names; the initial/random split, values and no-respawn on a stand-in map, other games unchanged, and Redoubt's real items (2 snipers, 2 sticky detonators) and random power names; a random drop's Railgun gets a fetcher only with the ordnance names; `item_check` marks a drop gone, does not bring it back for a gun in someone's hands, and brings it back once it lies loose; Halo 4 in `PICKUP_GAMES` and H2A not; a Heroic with a BR and a magnum walks 6 u for a pod's Incineration Cannon, Binary Rifle, Railgun or Rockets.
  - All 319 regression tests pass; 113 sources compile. The new reader was checked live on the running Redoubt match (read-only).
  - Gameplay is untested: a bot taking a gun out of a pod (whether the pod lets it close enough, and whether a tap of Use is enough) has not been seen. The bot process must be restarted, after the current match.

## 0.2.2-custom.9 — Halo 4 Demon and vehicle aim, Demon driving, Halo 4 Scorpion, 2026-11-08

- Covers the 16 commits since 0.2.2-custom.8 (fe2dd9f), none of them on GitHub yet, and the merge of custom.8 (ef4486d). Also carried: e7d0a39, the local original of custom.8's Slayer anchor change. GitHub has it as the cherry-pick fe2dd9f, so the code is the same; it keeps the commit's identity. Each entry below gives its own behavior and validation.
- Halo 4 Demon on foot: real sight heights from its live view, rifles at the head and automatics at the torso, the view locked on the part and led one tick, a tapped trigger and a dry-part switch. No thruster charge or thrust to cover in gunfights outside Infection. It engages a man in view over errands, and fights on the way to a gun and along an objective run. Reach Demon gets the one-tick lead and the dry-part switch. A Demon glances at a close radar dot behind it.
- Vehicles: Demons do not drive Warthogs or Mongooses, and Normal and Heroic are sent to drive them first. In Halo 4, every tier's shots at Warthogs and riders go to the real point (seated head, upper chest or the vehicle's body), from the Warthog gunner's pivot (8baecbe), the passenger's eye or the Ghost's camera. Halo 4 Demon aims at riders' heads when the shot clears the vehicle's hull. The Halo 4 Scorpion gets Reach's tank fix for every fixed tier.
- Maps and tools: teleporters only in the gametypes their labels name (Gore Valley's stuck pad; also Canyon, H2A Warlock and Ascension); Gore Valley's "Red rockets" patrol spot and owner power position; `tools/h4_seat_capture.py`, the seat capture the rider aim is built on.
- Validation at the candidate: all 308 regression tests pass. In game, the owner reported Halo 4 Demons playing much better in his 1v1s after the Halo 4 Demon aim and thruster changes (through 909c67d). Everything else here is untested in a game, including all the vehicle, rider, Scorpion, teleporter and fight-on-the-way changes. The bot process must be restarted to pick them up.

### Halo 4 Scorpion: Reach's tank fix for every fixed tier, 2026-11-08

- The owner: the Halo 4 Scorpion "has the same issue the Reach scorpion had": the driver's turn speed, and the rest of the Reach fix.
- His Blood Crash game (`logs/trace_h4_ca_blood_crash_20261108-000424.jsonl`) is the only recent Halo 4 trace with a Scorpion, and it had one driver: Rapid62 (bot 9, Heroic, spammer), at the wheel from 26 s to 68 s. Its view swung 150 deg/s at the 90th percentile of ticks, 709 at the 99th and 1,122 at the most. It fired on 381 of its 577 aim ticks, 44 of them with its command more than 3 degrees from its view. The Reach fix only applied to fixed Legendary and Demon in Reach, so this driver had none of it.
- `brain/bot.py` `Bot.drive`:
  - The `scorpion` gate is Reach's fixed Legendary and Demon (as before) or, in Halo 4, every fixed tier, Easy to Demon. Scaling (extra set) is excluded in both games.
  - As in Reach, a Halo 4 Scorpion driver's view turns at most `vehicles.SCORPION_TURN`, 90 deg/s. That rate was measured on the owner's Reach Boneyard drive; Halo 4's turret speed has not been measured. The cannon waits for 0.10 s of continuous alignment before it fires, close in too.
  - Chest aim at a man on foot: in Halo 4, his real chest (`h4_aim_point` → `h4_chest`, his live head less 0.16 u, so a crouch lowers it) from the tank's camera view (2 u over the hull). Reach's chest point, his place + 0.35, is over a Halo 4 Spartan's head (place + 0.25). The old splash aim, place + 0.05, sat near the hips. A rider or a vehicle keeps the vehicle aim.
  - Easy drives its trip and only shoots what is in front of it on the way. The Reach fix turned those travel shots off for a capped driver. Easy's Halo 4 tank keeps them, so it still fires.
- Validation:
  - `tools/test_h4_scorpion.py`, 9 tests: every fixed Halo 4 tier is capped, Scaling and a Ghost are not; Reach is unchanged (Heroic and Scaling uncapped, Legendary and Demon capped); the turn is held to 90 deg/s, the profile's own turn otherwise; the chest point at a man on foot, the vehicle aim at a rider; the cannon holds until settled, close in too; and Easy still fires while driving.
  - All 308 regression tests pass. Gameplay is untested. The bot process must be restarted.

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

## 0.2.2-custom.8 — Slayer anchors, 2026-11-08

- The Team Director can assign up to two Slayer anchors to separate nearby posts. It picks fixed Demon bots first, then Campers, then Snipers, then other eligible bots. Distance and current role break ties within each group.
- Verified the assignment logic offline. The isolated source suite passed 205 tests and skipped six that need local map data. The change needs a fresh bot process and a live match for gameplay validation.

### Slayer anchor priority and paired posts, 2026-11-08

- The Team Director can assign up to two anchors per Slayer role pass, with each assigned to a separate nearby post. Fixed Demon bots get first pick regardless of personality, followed by Campers, Snipers, and other eligible bots. Distance and current role break ties within each priority group. The aggressive Slayer plan still sends hunters toward the fight.
- A focused director check verified the priority order, two Demon anchors, separate posts, the single-bot fallback, and the Slayer posture and mode rules. All 299 regression tests passed. Gameplay validation needs a fresh bot process.

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

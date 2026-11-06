# Known bugs (0.2.2-s178)

What I already know is broken or buggy in this version, so you don't have to report it (but if you find something worse, or a way to make it happen every time, a [bug report](https://github.com/AyoItzKye/project-proving-grounds/issues/new?template=bug_report.yml) still helps).

For everything that works, game by game, see the [bot status sheet](BOT_STATUS.pdf). Things I simply haven't tested in a real match yet are listed there, not here.

## In every game

- **The bots only work in offline custom games with Easy Anti-Cheat off.** Started with anti-cheat on, there is no BOTS tile. This is on purpose.
- **An MCC update can break the mod** until a new version is out: the BOTS tile goes missing or bots don't join. Check the Releases page for a newer version.
- **Windows Security can delete the injector** if the exclusion was not added during install. The launcher says so when you press Play; the README's Troubleshooting section shows the fix.
- **Bots don't crouch-aim at a crouching player on a controller** in Halo: CE, Halo 2, Halo 3 and Reach: the mod can only tell you're crouching from the keyboard's crouch key there. Halo 2 Anniversary and Halo 4 read it from the game.
- **Bots don't pick up weapons off the map in Halo 2 Anniversary and Halo 4** yet. They keep their starting guns.
- **Spectate (no body)** is not available in Halo 2 Anniversary yet.
- **Big maps with many bots can stutter on slower PCs**: use fewer bots.

## How the bots play (every game)

- **Allied bots won't get into a vehicle with you**, only with other bots: they don't hop in as your gunner or passenger, or take you as theirs.
- **In CTF, a bot driver will pick up your flag carrier but won't drive back to your base** to score.
- **Destroyed vehicles in Halo 2 and ODST**: bots skip wrecks in Halo 2 Anniversary, Halo 3, Reach and Halo 4; in Halo 2 Classic and ODST this is not checked in a real match yet, so a bot may still try to get into a wreck.
- **Flying vehicles need reworking**: how bots fly and fight in the air is being redone.
- **Bots lack urgency on offense**: when the objective means attacking (taking the flag, planting the bomb, pushing in Invasion), they're too slow and cautious about it.
- **Theater mode only works with bots in Halo: Reach.** Films of bot matches in every other game (Halo: CE, Halo 2, Halo 2 Anniversary, Halo 3, ODST and Halo 4) load, then stop with "an error occurred" as they start.

## Halo: CE

**Works, but buggy**

- **Capture the Flag**: Both teams have captured flags in real matches, but on Blood Gulch the bots rarely make it to the flag.
- **Race**: Bots race the flags in order and finish laps; on Blood Gulch they drive, but often get stuck at one flag up on a rock.

## Halo 2

**Not working yet**

- **Warthog**: Bots can't get into vehicles in Halo 2 yet.
- **Gauss Warthog**: Bots can't get into vehicles in Halo 2 yet.
- **Ghost**: Bots can't get into vehicles in Halo 2 yet.
- **Banshee**: Bots can't get into vehicles in Halo 2 yet; they walk right past them.
- **Wraith**: Bots can't get into vehicles in Halo 2 yet.
- **Scorpion**: Bots can't get into vehicles in Halo 2 yet.
- **Spectre**: Bots can't get into vehicles in Halo 2 yet.
- **Mounted turrets**: Bots can't use any seat in Halo 2 yet, turrets included.

**Works, but buggy**

- **Team Slayer**: Bots fight really well here (Halo 2 SWAT is my benchmark for Legendary), but they can't use vehicles yet.
- **Capture the Flag**: Bots capture flags, but sometimes a carrier can't score or one team never goes for the flag.

## Halo 2 Anniversary

**Not working yet**

- **Hornet**: Bots get in but can't make it climb, so it sits on the ground.

**Works, but buggy**

- **Team Slayer**: Plays and scores, but bots can't pick up weapons off the map yet, and a few wander off, even into the water.
- **Capture the Flag**: Bots scored on Zenith, but they get stuck in a few spots on Coagulation.
- **Ghost**: Bots drive and shoot it well, but can't boost it yet.

## Halo 3

**Not working yet**

- **Hornet**: Bots get in but can't make it climb, so it sits on the ground.
- **Elephant**: Bots get in but almost never drive it or use its guns.

**Works, but buggy**

- **Team Slayer**: Some of my best matches with the bots have been Halo 3 Slayer. A weapon-swapping bug was just fixed and needs a recheck.
- **Capture the Flag**: Bots capture flags in shorter matches, but in longer games they don't push the flag enough.
- **Assault**: Bots have carried and armed the bomb, but results are mixed: one match ended 0-0.
- **King of the Hill**: Bots find and hold the moving hill and score, but when you stand in the hill they can lose track of it. That's fixed and needs a recheck.
- **Warthog**: Bots drive and gunners shoot, but drivers often park and wait for a crew.
- **Mongoose**: Bots ride it a lot, but still park and wait at times.
- **Chopper**: Bots drive it hard, shoot and boost-ram, though now and then one froze in place.
- **Scorpion**: Bots drive it, but miss a lot of shots and sometimes leave the tank behind.
- **Wraith**: Bots drive and fire it; a fix to its mortar aim still needs a recheck.
- **Banshee**: Bots fly it without getting stuck, but almost never shoot from it. A fix for that needs a recheck.
- **Mounted turrets**: Bots man the turrets and fire; a fix to their aim still needs a recheck.

## Halo 3: ODST

**Not working yet**

- **Warthog**: Bots can't get into vehicles in ODST yet.
- **Mongoose**: Bots can't get into vehicles in ODST yet.
- **Ghost**: Bots can't get into vehicles in ODST yet.
- **Olifaunt**: Bots can't get into vehicles in ODST yet.
- **Mounted turrets**: Bots can't use any seat in ODST yet, turrets included.

## Halo: Reach

**Not working yet**

- **Invasion**: Improving, not done: on Spire both sides now take the phases and deliver the core; on Boneyard the first attack still loses most rounds, and custom Forge Invasion maps (issue #2) aren't played yet. Being fixed first.
- **Scorpion**: Bots get in but spend most of the time stuck or standing still. They do board enemy tanks and take out the driver.

**Works, but buggy**

- **Invasion on Boneyard**: The attackers loiter in the Tier 2 spawn area instead of pushing the objectives aggressively.
- **Capture the Flag**: Bots capture flags and it plays well, but in big games the bot teams don't push the enemy flag enough.
- **Assault**: Bots pick up and carry the bomb, but I haven't seen them score a plant in a real match yet.
- **King of the Hill**: Bots hold the hill and score, but it can feel a little slow on the objective.
- **Territories**: Bots take and hold territories on Boardwalk, Powerhouse and Boneyard; on Spire they struggle.
- **Headhunter**: Bots head for the drop points, but often without any skulls to bank.
- **Warthog**: Bots drive and gun it, but often drive alone, use it like a taxi and miss shots.
- **Rocket Warthog**: Bots drive it and have used its gun, but they don't lock on or lead the rockets yet.
- **Transport Warthog**: Bots drive it; only the front passenger seat is handled so far.
- **Revenant**: Bots drive it, but get stuck on the terrain often.
- **Wraith**: Bots drive and fire it, but wait for a crew and get stuck on the terrain. They also board enemy Wraiths and take out the driver.
- **Banshee**: Bots fly and boost, but rarely shoot from it, and sometimes crash into buildings or just use it to get around. A fix for their attack runs needs a recheck.
- **Falcon**: Bots fly it, but pilots leave without their gunners, hover in place, and have flown out of bounds.
- **Sabre**: Bots can fly it, but don't use its missiles or other moves yet.
- **Seraph**: Bots can fly it, but don't use its weapons yet.
- **Mounted turrets**: Bots man the turrets and fire, but miss most shots and don't carry a turret they've ripped off.

## Halo 4

**Not working yet**

- **Extraction**: Not supported yet: bots play it as Slayer and never plant at the sites.

**Works, but buggy**

- **Team Slayer (Infinity Slayer)**: Plays and scores, and bots ride vehicles, but they can't pick up weapons off the map yet.
- **Free for All**: Plays smoothly, but bots can't pick up weapons off the map yet.
- **King of the Hill**: Bots follow the moving hill, but they stand around a lot and games are one-sided.
- **Flood**: Plays like a real game: the Flood rush survivors and use their thrusters, and survivors hold rooms in small groups. The first round can end right away; a fix for that needs a recheck.
- **Warthog**: Bots get in, drive, gun and get out, but drivers stall about half the time.
- **Mongoose**: Bots ride and drive it, but sit still about a third of the time.
- **Ghost**: Bots drive and shoot it well, but can't boost it yet.
- **Scorpion**: Bots drive and fire it, but sit still a lot. I've only checked one match.
- **Banshee**: Bots have flown it, but didn't shoot from it, and can't use its bomb or boost yet.

## Reported on GitHub

| Issue | What | Status | Notes |
|---|---|---|---|
| [#2](https://github.com/AyoItzKye/project-proving-grounds/issues/2) | Invasion on custom Forge maps | Open | Bots don't play custom Forge Invasion layouts yet. |
| [#4](https://github.com/AyoItzKye/project-proving-grounds/issues/4) | Bots stuck on Boneyard's stairs | Fixed in 0.2.2 | A floor in the map data that isn't there in the game, and how bots run the route up, both fixed. |
| [#5](https://github.com/AyoItzKye/project-proving-grounds/issues/5) | Bots at High Ground's gate | Open | Bots can't use the gate terminal yet. |
| [#7](https://github.com/AyoItzKye/project-proving-grounds/issues/7) | Halo 2 Anniversary Assault bomb not picked up | Fixed in 0.2.2 s177 | Bots now hold Use until the bomb is in their hands (it also sits on a stand the pickup used to skip). Tested on Lockdown Multi-Bomb: bombs taken and one armed. |
| [#8](https://github.com/AyoItzKye/project-proving-grounds/issues/8) | LiDAR Simulator stops early | Fixed in 0.2.2 | At Max speed a map was cut after 4 minutes; now it runs until mapped. |
| [#9](https://github.com/AyoItzKye/project-proving-grounds/issues/9) | Halo 3 bots ignore trip mines | Fixed in 0.2.2 s179 | Bots now see Halo 3's thrown equipment and whose it is, and route around an enemy trip mine. Tested on Rat's Nest: mines, a bubble shield and a regenerator read with their owners. |
| [#10](https://github.com/AyoItzKye/project-proving-grounds/issues/10) | LiDAR Simulator bots start outside Forge creations | Fixed in 0.2.2 | They started on Forge World's own spawns; now inside the creation. |
| [#11](https://github.com/AyoItzKye/project-proving-grounds/issues/11) | No weapon pickups on Forge creations | Fixed in 0.2.2 s178 | The guns on a creation read as unknown (bots only know guns by the map's own spots, and a creation's guns are not on Forge World's), and a creation without its map file kept Forge World's power weapon spots. Now they are named from the game its| [#12](https://github.com/AyoItzKye/project-proving-grounds/issues/12) | Firefight | Fixed in 0.2.2 s180 | Every part of the report is fixed. Up to 3 bots join your team from the BOTS tile in the Reach and ODST Firefight lobbies and stay a few steps behind you (s177). They now also join on the DLC maps (Unearthed, Installation 04), go for a dropped gun when they run dry, only melee an enemy in front of them, stay on foot with you, fight beside the Covenant on the Elite side (s179), and respawn like you on your team's shared lives (s180). Tested on Beachhead, Unearthed and Installation 04. Firefight's enemy types still get no special tactics. |

*Last updated November 6, 2026.*

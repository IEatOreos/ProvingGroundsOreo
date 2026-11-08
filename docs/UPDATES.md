# Updates

What changed in each version. Download the newest one from the [Releases page](https://github.com/AyoItzKye/project-proving-grounds/releases/latest). Everything still broken is on the [Known bugs](KNOWN_BUGS.md) page, and every game, mode and vehicle is rated on the [bot status sheet](BOT_STATUS.pdf).

Click a version to see what changed since the one before it.

<details open>
<summary><b>0.2.2 s181</b> (November 6, 2026): call bots into your vehicle, a smarter Spire attack and Banshee, careful grenades, Flood survivors that use their shotguns</summary>

s181 was updated eight times, on November 6 and 7. Everything new and fixed since 0.2.2 s180 is below, the newest first.

<!-- build: 20261107-1530 -->
#### Eighth update (November 7, afternoon)

**Fixed**
- **Banshee bombs in Halo 4**: bots switch to the bomb like a second weapon, drop it with the main trigger and switch back, the way players do it. Seen working: bots dropped five bombs in a five-minute match.
- **Halo 3 and Halo 4 Banshees** no longer press the second trigger as if it were the bomb.

<!-- build: 20261107-1400 -->
#### Seventh update (November 7, afternoon)

**Fixed**
- **Halo 4, the Mantis's rockets**: bots fire them now, held like a player does: a short hold at a soldier for one or two rockets, a long hold at a vehicle for the lock and a full salvo, as many as the magazine has left.

<!-- build: 20261107-1200 -->
#### Sixth update (November 7, midday)

**Fixed**
- **Halo 4, the Mantis**: bots really use it now. In a match Halo 4 makes the Mantis a walker, not the kind of object other vehicles are, so no bot ever saw it; now they get in, walk it, fire its machine gun and stomp (seen in matches on Forge Island). Its rockets don't fire yet.
- **Halo 4 Theater**: films of bot matches play with their bots instead of crashing as the bots join. A 12-minute Forge Island film matched its match's score at every point checked. Theater with bots now works in Reach and Halo 4.

<!-- build: 20261107-0230 -->
#### Fifth update (November 7, early)

**Fixed**
- **Halo: Reach Invasion, Spire**: a bot sent to a man cannon now stays on its pad until it launches, instead of turning for a grav lift the moment it got there.
- **Aircraft landing**: a bot flying to the objective sets down where there is room near it (within about 10 units) and gets out, instead of circling over Spire's top (tested, not yet seen in a real match).

<!-- build: 20261107-0100 -->
#### Fourth update (November 7)

**New**
- **Halo 4, the Mantis**: bots get in it and use all of it: the machine gun, the rockets (held on a vehicle to lock on) and the stomp on anyone and any vehicle beside it (tested, not yet seen in a real match).
- **Aiming at the head**: in Reach and Halo 4 bots aim where an enemy's head really is, as it moves when he strafes and crouches. Their aim is as good as before, just aimed at the right spot.
- **LiDAR mode** records where people and bots drive and fly, and the LiDAR Viewer shows it (V).

**Changed**
- **DMR over the assault rifle** (Reach, Halo 4): a bot with a loaded DMR uses it at every range, never drops a DMR for an assault rifle, and gives up the assault rifle for a DMR.

**Fixed**
- **Halo: Reach Invasion, Spire**: the attackers spread over both grav lifts and the man cannons during their all-out pushes on the core too, and walk onto a man cannon's pad instead of past it.
- **Vehicles during a push**: while the team pushes the objective together, bots still get into your landed aircraft and its guns, a free power vehicle (like a Banshee) still gets a driver, and empty guns still get gunners.
- **Falcons**: a bot pilot flies onto the top of Spire from outside instead of up under it. It also no longer jumps out when you take its gun, and waits a moment when you stand next to it (tested, not yet seen in a match with a person).
- **Snipers and reloads**: bots no longer trade a sniper rifle that still has rounds for another gun, and reload magazines they had only seen part empty.
- **Breakpoint**: bots on the bridge see, and shoot at, players on the tower ledge.
- **Bots joining**: all the bots you asked for join even if you open the pause menu while they do (Halo 3: ODST Firefight had one of three).

<!-- build: 20261106-2300 -->
#### Third update (November 6, night)

**New**
- **Call a bot into your vehicle**: aim at a teammate bot and press the horn (crouch) while driving, and that bot gets in (Halo 3, Reach, Halo 2 Anniversary, Halo 4). Stopping next to a bot still calls the nearest one, as before.
- **Aircraft pick up bots**: land an aircraft next to teammate bots and they get in, both of a Falcon's gunner seats too. Bots flying one do the same for their teammates.
- **The launcher's What's new**: when an update is out, What's new in the launcher lists everything added and fixed since the copy you have. From this build on, a same-day update of a version (like these three) shows up as an update too.

**Fixed**
- **Falcons**: bots no longer jump out of a Falcon in mid-air, and a bot pilot that lands to pick up a gunner waits for him (up to 20 seconds) instead of leaving as he walks up.
- **Warthog gunners** aim from the gun itself, so their shots no longer drift to one side of the target.
- **Halo: Reach Invasion, Spire**:
  - In phase 3 the attackers spread over every way up the spire (both grav lifts and the three man cannons) instead of all queuing for one lift, and they no longer stop for guns on the core run.
  - Bots know the man cannons only appear in phase 3 and that the spire's grav lifts only reach the top in phase 3.
  - Banshees fly the spire closer and lower with real attack runs instead of creeping around it, stay under the map's ceiling, and make bomb runs into the phase 2 objective rooms.
- **Grenades**: bots no longer throw a grenade where a teammate (or you) is standing or about to walk.
- **Halo 4 Flood**: survivors no longer get stuck on Blood Cavern's upper walkway on their way to the hiding spot by the back lift.
- **Bug reports**: a report now saves where you were when you pressed Save, and reports no longer fail to file now and then.

<!-- build: 20261106-1840 -->
#### Second update (November 6, evening)

**Fixed**
- **Halo 4 Flood**: with the shotgun out, human bots no longer sprint around a Flood coming at them (they couldn't shoot and turned their backs to him). They keep their sights on him and fire when he's in range.
- **Halo 4 Flood and Infection**: a bot that loses sight of a Flood or zombie for a moment keeps fighting him instead of walking back to its spot.
- **Infection and Flood**: human bots hide in places people actually play. On Blood Cavern they crowded against a wall trying to reach a floor nobody can get to.
- **Gravity lifts**: bots no longer try to go down a lift from its top end (Blood Cavern's back lift, and the low lifts on Halo 2 Anniversary's Lockout and Reach's Ivory Tower).

<!-- build: 20261106-1440 -->
#### First release (November 6, afternoon)

**Fixed**
- **Halo 4 Flood** (and Infection against swords): human bots got caught holding the magnum when the Flood reached them. Now they shoot the magnum at a Flood on its way in, switch to the shotgun before it gets close, and hold their ground with it instead of walking into the sword. Against enemies with guns nothing changes.
- **Firefight** ([#12](https://github.com/AyoItzKye/project-proving-grounds/issues/12)): after a match on Unearthed or Installation 04, the bots' brain for that match kept running into the next one and gave your bots a second set of orders. It now stops when its match ends.

</details>

<details>
<summary><b>0.2.2 s180</b> (November 6, 2026): Firefight bots respawn, Installation 04</summary>

### Fixed
- **Firefight** ([#12](https://github.com/AyoItzKye/project-proving-grounds/issues/12)):
  - Bots now respawn when they die, the same way you do: after the same wait, at the same spawn point, and each respawn uses one of your team's shared lives. When the team runs out of lives, they stay down, just like you.
  - Bots now join on Installation 04 too.
  - The BOTS tile no longer covers the last stat on the Firefight post-game screen.

</details>

<details>
<summary><b>0.2.2 s179</b> (November 6, 2026): Halo 3 trip mines, Firefight teammates that fight like teammates</summary>

### Fixed
- **Halo 3**: bots now see thrown equipment (trip mines, bubble shields, regenerators and the rest) and route around an enemy trip mine instead of walking into it ([#9](https://github.com/AyoItzKye/project-proving-grounds/issues/9)).
- **Firefight** ([#12](https://github.com/AyoItzKye/project-proving-grounds/issues/12)):
  - Bots now join on Reach's DLC Firefight maps (tested on Unearthed).
  - A bot that runs out of ammo now goes for a dropped gun, a Covenant one included. Reach bots also read how many rounds they have left.
  - Bots only melee when an enemy is right in front of them. They used to swing at the air and hit teammates after a fight.
  - Your teammates stay on foot with you instead of taking vehicles across the map, where they drove into walls.
  - On the Elite side (Versus' Elite rounds), bots now fight beside the Covenant instead of shooting them.

</details>

<details>
<summary><b>0.2.2 s178</b> (November 6, 2026): weapon pickups on Forge creations</summary>

### Fixed
- **Halo: Reach Forge creations**: bots now see and pick up the weapons placed on a creation ([#11](https://github.com/AyoItzKye/project-proving-grounds/issues/11)). They used to ignore all of them.
- **Halo: Reach**: a dropped gun that isn't on one of the map's weapon spots is now recognised too, so bots can pick it up when their own guns run dry.

</details>

<details>
<summary><b>0.2.2 s177</b> (November 6, 2026): Firefight bots that actually follow you, Halo 2 Anniversary bomb and flag pickups</summary>

### Fixed
- **Firefight** (s165 said these worked; in a real match they did not):
  - The BOTS tile now shows in the Reach and ODST Firefight lobbies, next to START.
  - Firefight has its own list of up to 3 bots, all on your team. Your 16-player list is kept as it is.
  - The bots on that list are the ones who join (s165 added 3 random teammates instead).
  - Teammates stay a few steps behind you and fight what comes, instead of wandering off or driving away.
- **Halo 2 Anniversary**:
  - Bots pick up the Assault bomb, which needs Use held ([#7](https://github.com/AyoItzKye/project-proving-grounds/issues/7)).
  - Bots pick up the enemy flag in CTF again.
- **The BOTS panel**:
  - Closing it with Esc no longer backs you out of the lobby.
  - The BOTS tile no longer shows on top of the post-game scoreboard.

</details>

<details>
<summary><b>0.2.2 s165</b> (November 6, 2026): Invasion rework, vehicles fixed, Firefight bots panel, launcher updates</summary>

### New
- **Update check in the launcher**: it checks GitHub for a new version (at most every 6 hours, or with **Check**), shows when it last checked, and tells you when one is out. **Auto-update** is off unless you turn it on; nothing is ever installed without it or the **Update** button.
- **Firefight**: the BOTS tile and panel now show in the Reach and ODST Firefight lobbies, with up to 3 bots (Firefight holds 4 players). Teammates follow you, and while you're down they hold a safe spot nearby instead of running into the open.
- **Observer**: the game list shows games only. A game with bug reports has a flag, and a **Bug reports** section lists each report with its time; click one to jump to that moment.
- **A real player's guide**: **Read the guide** in the launcher opens a searchable guide in the mod's own window.
- **The launcher** in the Proving Grounds art's colours, with the sign as the app icon.
- **Flight heights from the map**: aircraft pick their attack and travel heights from the ground under them; painting airspace is optional.

### Fixed
- **Invasion**:
  - Attackers take and hold the territories from inside them, and shoot on the way in instead of stopping to fight far from the objective.
  - The core carrier no longer drops the core by meleeing, and a dropped core is picked up again at once.
  - Attackers climb the Spire to the core.
  - Bots no longer get stuck on Boneyard's stairs, plank and walkway ([#4](https://github.com/AyoItzKye/project-proving-grounds/issues/4)) or in the rock on the way to Spire's B.
  - Both teams play with the same brain (team 2 was always thinking last).
- **Vehicles**:
  - Bots take empty Banshees.
  - A bot mans your Warthog's gun when you drive.
  - Falcon pilots fetch gunners and stay under the map's kill ceiling.
  - Aircraft climb over the Spire instead of flying into its side.
- **Halo 4 Flood**: survivors shoot the Flood instead of hiding behind the hardlight shield. The shield comes out only as a short block when reloading (then a melee), when swarmed, or when cornered.
- **Jetpacks**: bots let them refill before flying again.
- **Paint the nav**: works in an installed copy, and opens a map straight away.
- **LiDAR Viewer**: shows maps you mapped in the Simulator. Its controls are grouped, and a map's Forge layouts are in one drop-down.
- **LiDAR Simulator**: maps are no longer cut short at Max speed ([#8](https://github.com/AyoItzKye/project-proving-grounds/issues/8)), and bots start inside Forge creations ([#10](https://github.com/AyoItzKye/project-proving-grounds/issues/10)).
- **Windows**: windows the launcher opens now come to the front instead of opening behind it.
- **In-game UI**: the BOTS tile and the **Report bot bug** button are placed correctly at every resolution, not just ultrawide.

### Known problems in this version
- **Invasion** is still not fully right: on Boneyard the first attack loses most rounds, and custom Forge Invasion maps aren't played ([#2](https://github.com/AyoItzKye/project-proving-grounds/issues/2)).
- The [Known bugs](KNOWN_BUGS.md) page lists every open report from GitHub with its status.

</details>

<details>
<summary><b>0.2.1</b> (November 2026): melee weapons, Infection and Flood, wrecks, LiDAR, Theater, a new launcher</summary>

### New
- **Energy sword and gravity hammer**: bots lunge the moment the reticle turns red and get kills with them in Halo 3, Reach and Halo 4. Sword fights: Normal bots and up follow a clash with a quick melee.
- **Infection and Flood**: survivors hold rooms with few entrances in small groups; zombies hunt, wait at corners, then rally and charge together. Halo 4 Flood is read as Flood and Flood use their thrusters; survivors dodge lunges. ([#3](https://github.com/AyoItzKye/project-proving-grounds/issues/3))
- **Choose which MCC to use**: the launcher's Game folder setting lets you pick any copy of MCC or go back to the one Steam installed. ([#1](https://github.com/AyoItzKye/project-proving-grounds/issues/1))
- **Boarding**: bots board a distracted enemy Scorpion or Wraith from the front and beat the driver out.
- **Windows and fences**: bots see enemies through glass and fences, shoot through fences, railings and glass that breaks, and walk around bulletproof glass instead of firing into it.
- **Kill zones from the maps**: bots stay out of each map's kill zones and "return to the battlefield" areas, on foot, in vehicles and in the air.
- **Race and Regicide**: played as their own modes (Halo: CE and Reach Race, Halo 4 Regicide) instead of as Slayer.
- **LiDAR**: the Viewer and the Simulator are separate windows (the Viewer shows your LiDAR match live). A LiDAR run visits every gametype objective on the map, rides lifts and man cannons, and a director sends bots to the parts of the map not mapped yet.
- **Observer**: keeps your newest 5 games (a Keep game button saves one for good) and trims long recordings to the last 15 minutes, both changeable in Recording settings. It also lists games recorded by another copy of the mod.
- **A redesigned launcher**: status at a glance, a big Play button, a tools grid, everything fits the window.
- **Linux and Steam Deck**: a first installer for Linux and SteamOS (through Proton), as its own download.

### Fixed
- Bots no longer get into destroyed vehicles in Halo 2 Anniversary, Halo 3, Reach and Halo 4.
- Halo 4 Flood's first round no longer ends right away.
- Infection zombies no longer walk off to pick up guns, ride Mongooses or hide from far-off shotguns; Flood no longer spawn with DMRs; sides no longer mix up after the first round.
- Reach Theater films of bot matches play again (films are now kept in one place for every copy of the mod).
- Observer, LiDAR Viewer and Paint the nav open every time, not just once.
- The Observer's game list is no longer empty when the games were recorded by the other copy of the mod.
- Bots stop walking into the same ledge or wall over and over (a route that dropped through a ledge's own floor; Halo 4's height read).
- Bots no longer drop into pits they cannot climb out of (Construct's lift wells) when following LiDAR routes.
- Banshee and other aircraft pilots fire through their attack runs instead of pulling up at every building.
- King of the Hill in Halo 3 keeps the hill when you stand in it (the game hides the hill marker from you there).

### Changed
- Legendary bots walk in on their target instead of strafing in place (Heroic half the time); sniper rifles and launchers are unchanged.
- Infection and Flood no longer give bots custom loadouts.

### Known problems in this version
- **Reach Invasion does not play properly**: bots do not push the objectives, get stuck on Boneyard's stairs ([#4](https://github.com/AyoItzKye/project-proving-grounds/issues/4)), and custom Forge Invasion maps are not played ([#2](https://github.com/AyoItzKye/project-proving-grounds/issues/2)). Being fixed first.
- Bots cannot use the gate terminal on High Ground ([#5](https://github.com/AyoItzKye/project-proving-grounds/issues/5)).
- Theater with bots still only works in Reach.
- The Linux and Steam Deck installer has not been tried on a real Steam Deck yet.
- The full list is on the [Known bugs](KNOWN_BUGS.md) page.

</details>

<details>
<summary><b>0.2.0</b> (November 2, 2026): own app window, no key logging, setup fixes</summary>

### New
- Repair and Uninstall buttons in the launcher.

### Fixed
- The first-time setup works when some MCC games are not installed or MCC's menu art is missing, and finds MCC in the right Steam library.
- No console windows flash while the launcher or the setup runs.

### Changed
- The launcher and the tools open in the mod's own window instead of Microsoft Edge: no browser profile, no account sign-in, no synced extensions.
- The Data collector no longer records any keys or controller buttons, only what the game itself knows (positions, aim, guns, rounds, equipment). Exports leave out the keys 0.1.0 recorded.
- The installer makes clear that the Windows Security exclusion is required.

</details>

<details>
<summary><b>0.1.0</b> (November 1, 2026): the first release</summary>

Bots in Halo: CE, Halo 2 Classic and Anniversary, Halo 3, Halo: Reach and Halo 4 custom games, plus Reach and ODST Firefight. Slayer, CTF and objective modes, vehicles, equipment and armor abilities, team directors with callouts, five difficulties, seven play styles, up to 15 bots, the launcher, the Observer, and LiDAR mapping.

</details>

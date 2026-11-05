# Updates

What changed in each version. Download the newest one from the [Releases page](https://github.com/AyoItzKye/project-proving-grounds/releases/latest). Everything still broken is on the [Known bugs](KNOWN_BUGS.md) page, and every game, mode and vehicle is rated on the [bot status sheet](BOT_STATUS.pdf).

Click a version to see what changed since the one before it.

<details open>
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

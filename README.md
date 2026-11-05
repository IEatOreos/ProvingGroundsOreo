<p align="center"><img src="docs/banner.jpg" alt="Halo MCC: Project Proving Grounds" width="100%"></p>

# Project Proving Grounds

PvP bots for **Halo: The Master Chief Collection** on PC. Bots join your offline custom games as real players on the
scoreboard: they move, aim, strafe, jump-shot, take power weapons, drive and fly vehicles, play the objective, and
talk to their team through each team's own director (map callouts). Four difficulties plus Scaling, which follows
your own results, and seven play styles.

Games: Halo: Combat Evolved, Halo 2 (Classic and Anniversary), Halo 3, Halo: Reach and Halo 4 custom games, and
Reach and ODST Firefight (bots fill your team). Up to 15 bots: the game holds 16 players.

> Offline custom games only, with Easy Anti-Cheat off. The mod refuses to run with anti-cheat on and never touches
> matchmaking, Xbox network or Steam online services.

## What works right now

An honest rating of every game, game mode and vehicle in this version, from green (good to go) to red (not working
yet). Click the picture for the full sheet: what to expect in each mode and with each vehicle.

[![How the bots play each game: summary](docs/bot_status.png)](docs/BOT_STATUS.pdf)

**[Open the full bot status sheet (PDF)](docs/BOT_STATUS.pdf)** · **[Known bugs](docs/KNOWN_BUGS.md)** · **[Updates](docs/UPDATES.md)**

Found a bug? **[Report it here](https://github.com/AyoItzKye/project-proving-grounds/issues/new?template=bug_report.yml)** (how: [Report a problem](#report-a-problem)).

## Install

1. Check the [system requirements](#system-requirements).
2. Download **ProjectProvingGrounds-Setup-&lt;version&gt;.exe** from the [**Releases** page](https://github.com/AyoItzKye/project-proving-grounds/releases/latest) (on the right of
   the GitHub page).
3. Run it. Windows may say "Windows protected your PC": the installer is not code-signed. Click **More info**, then
   **Run anyway**.
4. The installer asks where to install (your user folder; no administrator rights needed) and whether you want a
   desktop shortcut.
5. **The Windows Security exclusion (required).** The mod loads its bots into MCC with a small injector, and Windows
   Security treats injectors as suspicious and usually deletes them, so the bots can't load without the exclusion. The
   installer adds one exclusion, for the mod's own `native\bin` folder and nothing else, and Windows asks for
   administrator permission when it does. Leave it ticked. Uninstalling removes it again. Using another antivirus? Add
   the same folder to its exclusions too.
6. At the end the launcher opens and runs the **first-time setup** (a few minutes): it builds the 3D bots, emblems,
   effects and map pictures from your own copy of the game. None of the game's files ship with the mod.

On Linux or a Steam Deck: see [Linux and Steam Deck](#linux-and-steam-deck).

Optional download on the same Releases page: **human-play-data-&lt;version&gt;.zip**, recorded matches of people
and bots for anyone who wants to study how they play (the zip has its own README).

## Play

1. Open **Project Proving Grounds** from the Start Menu and press **Play**. Steam asks how to start MCC: choose the
   option with **anti-cheat off**.
2. In MCC: **Multiplayer > Custom Multiplayer >** Halo: CE, Halo 2: Classic, Halo 2: Anniversary, Halo 3, Halo:
   Reach or Halo 4. For bot teammates against the Covenant: **Firefight > Halo: Reach Custom Firefight** or **Halo 3:
   ODST Custom Firefight**.
3. Next to START there is a **BOTS** tile (or press **B**). It opens the BOTS panel, the exact bots that join your
   next match, by team:
   - **Quick setup**: how many teams (2 to 8; Halo CE has 2), how many bots on each, difficulty and play style, then
     **Make N bots**.
   - Move a bot by dragging it to another team, with **Ctrl+Left / Right**, or right-click it > **Move to**. **+ Add
     bot** on a team, **+ Add team** for another.
   - Pick a bot to set its name, difficulty and play style. **Del** removes it. **Balance teams**, **Shuffle teams**,
     **New names**, **Difficulty for everyone**, **Remove all**.
   - **Spectate (no body)**: join with no body and fly a free camera (WASD or the left stick, mouse to look, Space up,
     Ctrl or C down, Shift fast; not in Halo 2 Anniversary yet).
   - **Settings**: each bot's profile with its 3D look, emblem and clan tag; re-roll them.
4. Pick a map and game type, then START. The bots join a few seconds after the match loads.

## Difficulty

Pick a difficulty for each bot in the BOTS panel, or one for everyone. Every difficulty aims the way a person does;
what changes is how fast the bots react and how smart they play.

- **Easy**: relaxed games. Reacts a little slower than a person, rarely dodges and only jumps to get around. It does
  not plan: in Slayer it wanders, in objective games it heads straight for the objective. It picks up a gun only if it
  passes one, never uses equipment, and mostly aims at your chest.
- **Normal**: plays like an average player. Reacts like a person, strafes in fights, follows its team's plan, knows
  some routes and power weapons, uses equipment when it makes sense, and goes for your head about half the time once
  your shields are down.
- **Heroic**: plays like a good player. Reacts faster, strafes almost all the time and jump-shots, takes sneaky
  routes, knows where enemies spawn, checks its flanks and radar, shoots together with its teammates, and lands
  headshots nearly every time.
- **Legendary**: plays like a top player. The fastest reactions, constant strafing and jukes, holds the best spots,
  times every power weapon respawn, uses every equipment trick, focuses fire with its team, and always goes for the
  head.
- **Scaling**: adjusts to you. The bots play with Legendary's smarts, but their skill (how fast they react and how
  well they aim) changes after every game, toward the level where you and the bots finish about even: win a lot and
  they get tougher, lose a lot and they ease off. The panel shows it as a percentage, where 100% is a skilled player.
  You can lock it at a level in the panel's **Advanced** tab.

## Play styles

- **Rusher**: pushes fights and hunts people down; never camps.
- **Camper**: holds power spots and defends; waits longer, crouches at its post.
- **Objective**: takes the flag, hill or ball, and skips far fights while it does.
- **Grenadier**: opens most fights with a grenade and makes enemy vehicles its job (rockets, lasers, plasma pistols,
  sticks).
- **Grudge**: goes after whoever killed it last.
- **Sniper**: hangs back and defends.
- **Flanker**: plays as an all-rounder for now (side routes come with the difficulty).

## Map the maps (LiDAR)

The bots play better on a map they have mapped: every floor, height, jump and drop. No scans ship with the mod
(each PC maps its own), and bots play unmapped maps with the map pack's height data in the meantime. Two ways:

- **LiDAR Simulator** in the launcher, no game needed: **Pick a map** (or a Forge layout the bots have played on) and
  watch the bots map it from its level data. Choose the speed (1x to 16x, or Max), pause or stop it, and turn on
  **Click spots to cover** to send bots to places first. **Every map** maps them all in turn.
- **LiDAR mode** in the BOTS panel: start any match and the bots walk the whole map while you watch. Jumps you land
  that beat walking are learned and every bot uses them.

**LiDAR Viewer** shows any map's scan in 3D. Details: [LiDAR mapping](#lidar-mapping) below.

## Tools

All from the launcher, each in its own window:

- **Observer**: replay recorded matches, see what every bot saw, thought, was told and did, and your own numbers next
  to the bots' (aim, reaction, fights, positioning). Import and export games to share them; names are replaced and
  Xbox ids removed in exports.
- **Data collector** (a switch in the BOTS panel): records your movement, aim, shots and guns for the Observer, read
  from the game itself (never your keyboard or controller). Everything stays on your PC.
- **LiDAR Simulator** and **LiDAR Viewer**: above.
- **Paint the nav** (advanced): mark where bots may and may not walk.

More on each of them: the [Player's guide](#players-guide) below.

## Player's guide

Command lines below run from the install folder (the launcher's **Open the install folder**) with the bundled Python: `python\python.exe -I tools\<tool>.py ...`.

### Team directors

Every team of bots has its own director: code that knows only what its own team knows (where teammates are, what they
saw and heard, the score and the clock). It speaks map callouts to the team, hands out roles every 2 seconds (CTF:
runner, escort, defender, hunter; Slayer: map control and hunters; each mode its own), pulls bots back to defend after
a death near the flag, and sets the team's play by the score and the clock: careful when the enemy is about to win, all
in when behind late. Nothing shows over the game: every decision is in `logs\brain.txt` and in the Observer's event
feed.

### Data collector and the Observer

Turn on **Data collector** in the BOTS panel and play. It records your movement and aim, your shots, guns and equipment, all read
from the game itself (your keyboard, mouse and controller are never recorded), on this PC only
(`logs\collect_<map>_<date>-<time>.jsonl`).

Open the **Observer** from the launcher and pick a game: a live one shows LIVE. Scrub the timeline and click a bot to
see what it saw, thought, was told and did. The **You** section shows your numbers beside the bots' (by difficulty,
measured the same way):

- **Aim**: seconds from an enemy coming into view to your aim on them (and to your first shot); how often you were
  already aimed where they came from. **Hit**: from being shot to your aim on someone.
- **Fights** a minute alive, how long they last, the time between them and from a spawn to the first.
- **Speed**, time standing still, sideways speed in fights, jumps.
- **Positioning**: the zones you spend time in, fight distance and height, who aims first when you and an enemy see
  each other, how much of the time an enemy has you in view. **Show where you were on the map** draws it.
- **Accuracy**: firing time on a body, damage dealt, kills; your guns, shots, switches, pickups and equipment uses.

Games recorded without the Data collector still get positions, aim, pace and positioning from the bots' recording
(4 times a second, without your shots). The **Crosshairs** layer draws your line of sight to what your crosshair is on: red on a
player, gold on a vehicle, white on the ground or a wall. Click yourself on the map to see what your crosshair is on,
what you ride and which gun. Text versions: `tools\observer.py you <trace file>` and
`tools\observer.py at <trace file> <seconds>`.

The Observer keeps your newest 5 games. When a new game starts, the oldest one you did not keep is removed. Press
**Keep game** to keep a game for good; exported games and games with bug reports are always kept. A recording keeps
at most the last 15 minutes of a game, so a long game does not fill your disk. Change both in **Recording settings**
(saved in the `user` folder, kept by updates and Repair).

### Share a game

In the Observer, pick a game and press **Export game**. It saves one zip (a copy also goes to `logs\exports`) with
everything recorded in that game:

- `manifest.json`: the game, map, modes, score and length; every player marked **human** or **bot** (bots with their
  difficulty and play style); every file inside and the format of each row.
- `trace.jsonl`: everyone 4 times a second, every bot every tick (position, aim, goal, buttons), every bot decision
  with its scores and callouts.
- `collect.jsonl`: the Data collector's recording when it was on.
- `carnage_report.xml`: MCC's own post-game numbers when they belong to this game; the Observer's objective and player
  analyses.

Gamertags, clan tags and service tags become Player 1, Player 2 ..., Xbox ids are always removed and your Windows
user folder in any path becomes `<home>`; tick **Keep names** to keep the names. **Import** opens a zip someone shared.
Command line: `tools\match_export.py <trace file>`.

### LiDAR mapping

Bots play better on a map they have mapped. No scans ship with the mod: each PC maps its own.

#### LiDAR mode (in a match)

Tick **LiDAR mode** in the BOTS panel and start any match: up to 16 players, all bots on your team, nobody fights.
The bots walk every floor, measure heights and jumps, and record where they fall. Open the **LiDAR Viewer** to watch
in 3D: bots are white dots, you are gold, every step colours the floor by height, a jump or fall is a white trail that
turns magenta only if the bot lands and is still alive 5 seconds later, and a red cross marks each deadly edge.
Open the Viewer any time during the match: it shows the match live (the Simulator has its own window and never gets in
the way).

**Objectives of every game type.** Any game type works for LiDAR mode: the bots also visit every objective place the
map has for all of its game types at once (flag stands and returns, hills, oddball and bomb spawns, plant points,
territories, havens, drop points, race checkpoints, Invasion zones), read from the map's own data, plus objectives seen
in the game on a Forge layout. Up to half the bots at a time walk to the nearest ones; the rest keep mapping. The scan
saves each place with whether someone reached it and whether the bots' navigation reaches it, and the map's report
(`logs\lidar_<map>.md`) lists the ones nobody reached. A jump you land up to one of those makes it reachable for every
bot. The Simulator does the same offline and shows "Gametype objectives: n of m visited" in its panel.

**Maps list** (L, or the button): one button per game, then a picture button per map with its real name and scan
status (runs, floor cells, when it was last updated; LIVE on the one being scanned now). Click any map to see its
stored scan. **Remove** on a scanned map deletes that map's scan to start it over (it asks first); the files move to
`backups\lidar`, and copying one back into `maps\<map>` restores it.

Every jump you land that beats walking (and survive for 5 seconds after landing) is saved for the map; LiDAR bots go
and try it, and from the next match every bot uses it (Easy bots too: to get around, never as a fighting trick). A
notice shows in the game when a jump of yours is learned, and again when bots have done it twice. Crouch spots work
the same way (Halo 2 Anniversary and Halo 4): floor you walk crouched is marked and every bot crouches there.

**Called jumps.** A LiDAR bot only learns a jump it called: before jumping it says where it will land, worked out from
the game's run speed, jump and gravity over the map's level data, and it only calls jumps whose small misses it would
survive. If it lands on the call and lives 5 seconds, the jump is open to every bot; a miss does not count, and a jump
missed twice is not called again. Your own jumps always count. Every jump is judged two-way (a gap bots use both ways)
or one-way (a drop with no way back up); a recorded jump is a way in, not a detour: a bot only takes it when it is the
best way to where it is going.

The paint spreads a little around every player over connected floor, and where it meets a wall the wall is painted
solid: bots backing off from a losing fight head for a wall that shields them. Glass and other see-through surfaces
are never counted as walls (Halo 2 Anniversary, Halo 4, ODST; the other games' level files carry no material names).

#### LiDAR Simulator (no game needed)

The **LiDAR Simulator** in the launcher runs the same bots on a map's level data and shows them in the 3D view: 16 bots
map the floor and call jumps, 8 aircraft fly the air over the walked floor up to the map's ceiling. Its **Simulator**
panel (bottom right):

- **Pick a map**: the Maps list opens; click a map's picture (or its **Simulate** button). Forge layouts the bots have
  played on are listed under their map. Picking another map while one runs stops it (what it mapped is saved).
- **Every map**: all of them in turn, each saved when it finishes.
- **Speed**: 1x (real time) to 16x, or **Max** (as fast as this PC runs it). The panel shows the speed actually
  reached: big maps with 16 bots and 8 aircraft run slower than asked on most PCs.
- **Pause** / **Resume** and **Stop** (it saves what was mapped).
- **Click spots to cover** (or C): click the map where the bots should go first; the 3 nearest bots go to each spot
  (pink ring), green once a bot got there, a red cross when no bot found a way within 2 minutes. **Clear spots**
  removes them.

A map runs until nothing new turns up for 45 seconds (6 simulated minutes at most); run it again to add to its scan.
Jumps the bots land go into the map's LiDAR data, where bots in real matches try them and stop using ones that fail
in the game. Command line: `tools\lidar_sim.py --open [maps...] [--all] [--speed 4]`. The simulator only
knows the level data, so it cannot find floor the data lacks or steps the game lets you walk up; LiDAR mode in a match
fills those in. Its jump physics is each game's own (gravity and jump speed measured from recorded matches, run speeds
and fall damage from the official editing kits).

### Map features

Every map's weapons, powerups, vehicles, objective points (flags and their returns, hills, balls, territories, bombs
and goals) and usable things (teleporters, man cannons, gravity lifts, switches, doors, shields) are on its LiDAR map
with names (M in the 3D view). In Halo 3, Reach, Halo 4 and Halo 2 Anniversary the brain also reads every gameplay
object as it plays: armor abilities and equipment, teleporters (and which sender leads to which receiver, once someone
goes through), man cannons, lifts, power-ups, weapon and vehicle spawns, spawn points and kill / safe zones. LiDAR bots
in a real match ride each man cannon and lift nobody has ridden yet: where it throws them becomes a path every bot can
use.

### Report a problem

Press **F9** in a match with bots on to save a bug report: the moment is kept with the recording around it in
`logs\bug_reports\<date-time>`, and a note you type goes with it. Attach that folder (or the Observer's export of the
game) to a **[bug report](https://github.com/AyoItzKye/project-proving-grounds/issues/new?template=bug_report.yml)**: the
form asks for the game, mode, map and difficulty and has a box to drop the zipped report into. Ideas and requests:
**[New issue > Idea or request](https://github.com/AyoItzKye/project-proving-grounds/issues/new/choose)**.

### Where things are

| Folder in the install | What |
|---|---|
| `maps\<map>` | each map's knowledge (callouts, positions, objects), its LiDAR scan and what the bots learned there |
| `logs` | the brain's log, recordings, bug reports, exports |
| `native\bin` | the mod (botcore.dll, inject.exe), the BOTS panel's settings and pictures, the 3D bots |
| `python` | the bundled Python |
| `tools` | the launcher, the tools and the map tools |

## System requirements

| | Minimum | Recommended |
|---|---|---|
| Windows | 10, 64-bit (or Linux / SteamOS with Proton: [Linux and Steam Deck](#linux-and-steam-deck)) | 11, 64-bit |
| Game | Halo: The Master Chief Collection on Steam, Easy Anti-Cheat off | same |
| CPU | 4 cores, one core as fast as an Intel Core i5-8400 / i7-4790K or AMD Ryzen 5 3600 | 6+ cores, one core as fast as an AMD Ryzen 5 5600X or Intel Core i5-12400 |
| Memory | 8 GB | 16 GB |
| Graphics | MCC's own minimum (DirectX 11, feature level 11.1) | MCC's recommended or better |
| Storage | about 2.5 GB beside MCC | the same on an SSD |

The bots think on one CPU core, so a fast single core matters most; fewer bots need less.

## Troubleshooting

| What you see | What to do |
|---|---|
| No BOTS tile in the lobby | MCC was started with anti-cheat on: quit it and press Play again, choosing anti-cheat off. Or MCC updated since this version of the mod: check Releases for a newer one. |
| The launcher says Windows Security removed inject.exe | The exclusion is missing. Restore inject.exe from Windows Security > Protection history, then run the installer again with the exclusion ticked, or add the install folder's native\bin yourself (Windows Security > Virus & threat protection > Manage settings > Exclusions). |
| Bots do not join | The brain's log is logs\brain.txt in the install folder (Open the install folder in the launcher). |
| The game stutters with many bots | Use fewer bots; see the requirements. |
| Another mod (ReShade, an ASI loader ...) | The launcher lists files from other mods that can clash and offers to start without them for one session. |
| The launcher says the game is not found, or uses the wrong copy of MCC | In the launcher, **Game folder > Choose folder ...** and pick your MCC folder (the one with `MCC`, `halo1`, `halo3` ... in it), or paste its path and press **Use**. The choice is kept through updates and Repair; **Use automatic** goes back to the copy Steam has installed. Run **Repair** after switching to another copy. |

### Which copy of MCC the mod uses

In this order:

1. The environment variable **`HB_MCC`**, if it is set (for example `setx HB_MCC "D:\MCC builds\stable"` in a
   command prompt, then open the launcher again; `setx HB_MCC ""` clears it).
2. The folder you chose in the launcher (**Game folder**), saved in `user\mcc_folder.txt` in the install folder.
3. The copy Steam has installed (Steam's library list, `steamapps\libraryfolders.vdf`, every library on every drive).

Several copies of MCC (for example one kept away from Steam updates for your own mods): choose the one to play in
the launcher. **Play** starts Steam's own copy through Steam. Any other copy is started directly from its folder
(`MCC\Binaries\Win64\MCC-Win64-Shipping.exe`, with anti-cheat off); Steam must be running and signed in, and the mod
puts a `steam_appid.txt` file (976730) in that copy's folder so it starts as itself and not as Steam's copy. Already
running a copy? The bots load into the one that runs.

`python -I brain\paths.py` (from the install folder, with `python\python.exe`) prints what the mod finds.

## Uninstall

In the launcher: **Uninstall** (bottom row), or Windows **Settings > Apps > Installed apps > Project Proving
Grounds > Uninstall**. It removes the Windows Security
exclusion if you added one and asks whether to keep your LiDAR scans, learned map data and recorded matches.

## Linux and Steam Deck

MCC runs on Linux and SteamOS through Proton, and so does the mod: its Windows parts run through the same Proton as
the game. Linux support is new: if something does not work, please [report it](#report-a-problem).

**Install** (on a Steam Deck: in Desktop Mode, with a keyboard or the on-screen keyboard: Steam + X)

1. Install MCC through Steam and start it once (Steam sets up Proton for it), then quit it.
2. Download **ProjectProvingGrounds-Linux-&lt;version&gt;.tar.gz** from the
   [Releases page](https://github.com/AyoItzKye/project-proving-grounds/releases/latest) and unpack it (right-click >
   Extract, or `tar -xzf ProjectProvingGrounds-Linux-<version>.tar.gz`).
3. In a terminal (Konsole on the Deck), in the unpacked folder: `./install.sh`. It finds Steam (also the Flatpak
   Steam) and MCC in any of your libraries (an SD card too), copies the mod to `~/.local/share/project-proving-grounds`,
   runs the first-time setup (a few minutes) and adds **Project Proving Grounds** to the application menu. It does not
   change MCC or MCC's Proton prefix, and needs no root rights.
4. It prints one line for Steam. In Steam: **Halo: The Master Chief Collection > Properties > General > Launch
   Options**, paste it. It looks like `"/home/deck/.local/share/project-proving-grounds/app/installer/linux/ppg-run.sh" %command%`.

**Play**: press Play in Steam (Game Mode works) and choose the **anti-cheat off** option. The bots load as MCC
starts; the rest is the same as on Windows ([Play](#play)). With anti-cheat on, the game starts as normal, without
the bots. The log of each start is `logs/linux_play.txt` in the mod's folder.

**The launcher** (setup, Repair, the Observer and the LiDAR tools): **Project Proving Grounds** in the application
menu. It opens in your web browser.

**Update**: run the new version's `./install.sh` (your LiDAR scans, learned map data and recordings are kept).
**Uninstall**: `~/.local/share/project-proving-grounds/app/installer/linux/uninstall.sh`, then clear the launch option
in Steam.

Found in an unusual place? Set `PPG_STEAM` (Steam's folder), `PPG_MCC` (MCC's folder) or `PPG_PROTON` (a Proton
folder) before `./install.sh`.

## For developers

How the code works, part by part and file by file, and how to build it and run the tests:
[docs/CODE_GUIDE.md](docs/CODE_GUIDE.md). How to contribute: [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

Built by the Project Proving Grounds contributors with **Claude**, Anthropic's AI model, which wrote most of the code
and documentation together with the project's author.

> Making this mod cost Anthropic an estimated **$3,893** in compute. That's more than a Warthog, and the bots still
> can't drive one back to base with the flag. Worth every credit. Sorry, Anthropic.

- [Dear ImGui](https://github.com/ocornut/imgui) (MIT) draws the BOTS panel; [MinHook](https://github.com/TsudaKageyu/minhook)
  (BSD 2-Clause) hooks the game.
- The map tools (bsp2obj, model2obj) are a [separate GPL-3.0 project](https://github.com/AyoItzKye/proving-grounds-map-tools) built on
  [Reclaimer](https://github.com/Gravemind2401/Reclaimer) by Gravemind2401 and contributors.
- CPU single-thread ratings in the requirements: PassMark.

## License

Free to use, share and change for any noncommercial purpose under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md); selling it or earning money from it is not permitted. Notices and
third-party licenses: [NOTICE.md](NOTICE.md).

Halo: The Master Chief Collection © Microsoft Corporation. Project Proving Grounds was created under Microsoft's
"[Game Content Usage Rules](https://www.xbox.com/en-US/developers/rules)" using assets from Halo: The Master Chief
Collection, and it is not endorsed by or affiliated with Microsoft.

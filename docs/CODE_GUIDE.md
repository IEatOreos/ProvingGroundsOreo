# Project Proving Grounds: code guide

This guide explains what every part of the code does and how the parts work together, for anyone who wants to read,
change or build the mod. It follows the code as it is in this version.

## The big picture

Project Proving Grounds puts bots into Halo: The Master Chief Collection's offline custom games as real players. It
has three layers:

1. **The mod inside the game (`native/`).** A small injector loads `botcore.dll` into MCC (only with Easy Anti-Cheat
   off). botcore hooks each game's update loop, creates bot players the way the game creates real ones, and every tick
   writes each bot's buttons, movement and aim into the game. It also draws the BOTS panel in the lobby (an ImGui
   overlay) and shares a block of memory with the Python side.
2. **The brain (`brain/`, run by `tools/live_bots.py`).** A Python program reads the game's state (where everyone is,
   what they hold, the objectives), lets each bot perceive, decide, move and aim like a person, has a director per team
   hand out roles and callouts, and sends the actions back through the shared memory, about 30 times a second.
3. **The launcher and tools (`tools/`).** The launcher starts MCC and the mod, runs the first-time setup (3D bots,
   emblems, effects and map pictures built from your own copy of the game), and opens the tools: the Observer for
   replays and stats, LiDAR mapping and its simulator, and the nav painter. Each tool is a small local web page shown in
   the mod's own window (`native/bin/ppg_window.exe`).

## Folders

| Folder | What is in it |
|---|---|
| `native/` | the C++ mod: botcore.dll's source (the game hooks, the per-game code, the BOTS panel, the 3D bot viewer), the injector, the app window, the build scripts |
| `native/bin/` | the built mod, its settings (`botcore.ini`, `bot_profiles.ini`, `bot_looks.ini`), and the art and 3D models the setup builds |
| `brain/` | the bots' thinking: one bot, the team director, the game modes, the map and navigation model, reading each game's memory |
| `tools/` | the launcher and setup, the live brain loop, the shared-memory link to botcore, the tools and their pages, the setup's art builders |
| `maps/` | what the bots know about each map: callouts, objects, positions, level heights; on your PC also its LiDAR scan and what the bots learned there |
| `logs/` | made on your PC: the brain's log, match recordings, bug reports, exports |
| `user/` | made on your PC: your own settings (the MCC folder you chose in the launcher, `user/mcc_folder.txt`) |
| `python/` | the bundled Python the installer ships (installs only) |
| `installer/` | the Windows installer script and icon; `installer/linux/` holds the Linux and Steam Deck scripts |
| `docs/` | this guide and the bot status sheet |

## Contents

- [The mod inside the game (native/)](#the-mod-inside-the-game-native)
- [How a bot thinks (brain/)](#how-a-bot-thinks-brain)
- [How the brain knows the map and the game (brain/ and maps/)](#how-the-brain-knows-the-map-and-the-game-brain-and-maps)
- [Starting a match and the tools (tools/)](#starting-a-match-and-the-tools-tools)
- [Art and models made on each PC (setup builders)](#art-and-models-made-on-each-pc-setup-builders)
- [The developer kit (public repository only)](#the-developer-kit-public-repository-only)
- [Building from source](#building-from-source)

## The mod inside the game (native/)

The native side of Project Proving Grounds is a 64-bit DLL, `botcore.dll`, that runs inside `MCC-Win64-Shipping.exe`, plus two small stand-alone programs: `inject.exe`, which loads the DLL into a running MCC, and `ppg_window.exe`, the app window that shows the project's local web pages. The bots' decision making does not live here. It lives in the Python "brain" (`tools/play.py` and the `brain/` package), which runs as a separate process. The DLL's job is mechanical: find each Halo engine as MCC loads it, hook the engine's per-tick player update, create bot players with the engine's own player creation function, and every tick copy the brain's chosen input (move, look, buttons) into each bot's slot of the engine's action array, so the game simulates a bot exactly as it would simulate a person. It also draws the in-lobby BOTS panel, fixes up what MCC's own screens show for bots (names, clan tags, emblems, post-game rows), records bot input for Theater films, and starts and stops the brain.

The DLL starts a background thread from `DllMain` (`botcore.cpp main_thread`). That thread creates the named shared memory block defined in `shared.h`, loads the settings from `botcore.ini`, installs the overlay hooks (`overlay.cpp`) and MCC's report hooks (`report.cpp`), then loops forever: every 33 ms (100 ms when Halo: CE is not loaded) it checks whether each title's engine DLL (`halo1.dll`, `halo2.dll`, `halo3.dll`, `haloreach.dll`, `halo3odst.dll`, `groundhog.dll` for Halo 2 Anniversary, `halo4.dll`) is loaded and hooked, rehooks any that MCC has unloaded and reloaded, and watches MCC's menu state to start the brain when a match begins and stop it in the menus. MCC reloads a title's DLL between matches, so every per-game file has a `*_watch()` function that compares the first five bytes of its hooked function with the jump it wrote and installs the hook again when they differ. All hooks are MinHook detours. The engine hooks run on the game thread; everything they do (running a brain command, writing actions) happens inside the game's own tick, guarded by structured exception handling so a bad pointer sets a fault flag instead of crashing MCC.

The brain talks to the DLL only through shared memory. `shared.h` defines `hb_shared`, a packed 3622-byte block named `Local\HaloMCCBots31`. The brain side is `tools/botctl.py`: it reads the block's name out of `shared.h` with a regular expression, opens it with `mmap.mmap(-1, SIZE, tagname=NAME)`, and reads and writes fields at hand-maintained byte offsets (`OFF_BOTS`, `OFF_ACTIONS`, `OFF_CMD`, `OFF_BTN_MAP`, `OFF_LOOK`, `OFF_SPAWN` and so on). A `static_assert` in `shared.h` pins the size so the two sides cannot drift silently. Two patterns run through the block. Per-bot actions (`hb_action`) are a mailbox the brain overwrites every brain tick; their `seq` field becomes non-zero once the brain drives that bot, and the DLL leaves a bot alone until then. Commands (`ADD_BOT`, `ADOPT`, `SET_TEAM`, `SET_LOADOUT`) use a sequence handshake: the brain writes `cmd` and `cmd_arg`, then bumps `cmd_seq` last; the next game tick of the matching title runs the command and copies `cmd_seq` into `cmd_done_seq`, which `botctl.command` polls for. Each title's command runner only accepts commands whose `cmd_arg` carries that title's bit (bit 24 Halo 2, 25 Halo 3, 26 Reach, 27 ODST, 28 Halo 2 Anniversary, 29 Halo 4; Halo: CE takes unmarked commands), so a command meant for one engine can never run in another.

The overlay (`overlay.cpp`) hooks DXGI `Present` and `ResizeBuffers`, `CreateFileW`, the cursor position functions and XInput, and uses Dear ImGui to draw a BOTS tile over MCC's custom game lobby, the full BOTS panel (`bots_panel.cpp`) when the tile is opened, a timed notice banner the brain can raise, and a bug report window over a match. The panel edits the roster of bots for the next match and the install's 15 bot profiles, and its 3D bot preview is drawn by `model_view.cpp` on MCC's own Direct3D 11 device. The per-game files (`h2.cpp`, `h3.cpp`, `reach.cpp`, `odst.cpp`, `h4f.cpp`, with CE inside `botcore.cpp`) each hold one engine's reverse-engineered layout and its action writer; `spawnhook.cpp` and `film.cpp` add Reach's Invasion respawns and Theater support. Outside the game, `ppg_window.exe` is a minimal WebView2 host that `tools/appwindow.py` uses to show the launcher, the Observer and the other local pages in a window of their own.

| File | Role |
|---|---|
| `shared.h` | Shared memory layout (`hb_shared`) and inline helpers both the DLL and its tests use |
| `botcore.cpp` | DLL entry, main thread, settings (`botcore.ini`), brain process control, Halo: CE hooks and bot creation |
| `inject.exe` / `inject.cpp` | Loads `botcore.dll` into MCC with `LoadLibraryW` in a remote thread; refuses with anti-cheat running |
| `h2.cpp` | Halo 2 Classic: players-update hook, bot creation, action writer, weapon pickup |
| `h3.cpp` | Halo 3: the same, plus vehicle boarding and the CTF flag pickup |
| `reach.cpp` | Halo: Reach: the same, plus Armory armor rolls, loadouts, spawn teleports and Theater-safe input |
| `spawnhook.cpp` | Reach: hook on the spawn check so bots respawn in Invasion |
| `film.cpp`, `film.h` | Records the bots' commands and input per tick and replays them in Theater (Reach) |
| `odst.cpp` | Halo 3: ODST Firefight bot teammates |
| `h4f.cpp` | Halo 2 Anniversary and Halo 4 (one engine family): bots, Armory rolls, sprint, boarding, exits, loadouts |
| `report.cpp` | Hooks in MCC's own executable so bots show their names, tags, emblems and teams in MCC's screens |
| `overlay.cpp` | D3D11 Present hook, ImGui setup, lobby detection, BOTS tile, notices, bug report, input capture |
| `bots_panel.h`, `bots_panel.cpp` | The BOTS panel: roster editing, bot profiles, bot editor, Scaling settings, sounds, bug report UI |
| `look_names.h` | Generated tables naming Reach's and Halo 4's Armory items for the bot editor |
| `model_view.h`, `model_view.cpp` | Offscreen 3D renderer for the bot editor's character preview |
| `ppg_window.cpp` | `ppg_window.exe`: the project's WebView2 app window for its local pages |
| `build.bat` | Builds `botcore.dll` and `inject.exe`, then the panel's art and model files |
| `build_window.bat` | Builds `ppg_window.exe` |

Third-party code compiled in from `native/third_party`: MinHook (function hooking), Dear ImGui with its Win32 and DX11 backends, and the WebView2 SDK headers and static loader. These are not documented here. The other sources in `native/` (`diag.cpp`, `filemon.cpp`, `watch.cpp`, `panel_preview.cpp`, `test_zoom.cpp`, `build_diag.bat`, `build_preview.bat`, `tests/`) are developer tools and tests that do not ship.

A note on identifiers used throughout: the shared memory field `game` holds which engine is ticking (1 CE, 2 Halo 2, 3 Halo 3, 4 Reach, 5 ODST, 6 Halo 2 Anniversary, 7 Halo 4). The overlay uses a different "title" numbering for lobbies (1 CE, 2 Halo 2, 3 Halo 3, 5 Reach, 6 Halo 2 Anniversary, 7 Halo 4, 4 for any other title). Every bot gets a made-up player identifier of the form `0xB07B07B0000000nn` (nn the player index); several files use the high 32 bits `0xB07B07B0` to recognise a bot.

### `native/shared.h`

`shared.h` is the contract between `botcore.dll` and the Python side. It is included by every native file that touches bots, and its constants are mirrored in `tools/botctl.py`. The comments in it are mostly accurate; the version number (`HB_VERSION 13`) and the mapping name (`HB_SHM_NAME`, renamed per build so a fresh DLL never shares a block with an old one still loaded in MCC) are the two values that change when the layout changes.

**`hb_action`** (24 bytes) is one bot's input for a tick, shaped after Halo: CE's `player_action`: `forward` and `strafe` throttles in -1..1 (strafe +1 is left), `yaw` and `pitch` in radians, a `buttons` bit field and a `seq` counter. `seq == 0` means the brain has not driven the bot yet, and every per-game writer skips such a bot, leaving its slot as the game filled it.

**Button bits** (`HB_BTN_*`) pack more than buttons. Bits 0-7 are fire, jump, crouch, grenade, melee, action (Use), reload and equipment. Bits 8-10 carry a wanted weapon slot plus one (0 keeps the current weapon). Bit 11 is Halo 4's sprint. Bits 12-13 are the wanted scope level. Bits 14-17 are a wanted vehicle seat plus one, used together with Action held. Bit 18 asks for a vehicle's turret (a Warthog's gun is its own vehicle object). Bits 19-20 encode a hovering aircraft's vertical input. Bits 21-23 (`FIRE2`, `CYCLE`, `ABILITY`) are not handled by any native writer directly; they reach a game only through the decoded button table described below.

**Inline helpers** shared by several engines:

- `hb_pick_loose(pos, n, feet, yaw, pitch)` chooses which nearby loose weapon a Use press should take: among weapons within 1.0 unit horizontally and 1 unit vertically of the feet, the one closest to the view line if it is within 0.6 rad, else the nearest within 0.6 units. Reach uses it so a bot that looks at a flag or core takes that, not a gun lying next to it.
- `hb_seat(buttons)` and `hb_use_picks_up(buttons)` decode the seat request; Use only picks things up when no seat is asked for.
- `hb_loose_parent_ok(parent_type)` says whether a weapon attached to a parent object may be taken (not when held by a biped or mounted on a vehicle; yes when it sits on a marker or a stand, as an Oddball or a flag does).
- `hb_vertical(buttons)` maps the 2-bit vertical level to Reach's vertical input value (0, +1, -1, +0.5).
- `hb_zoom_index` and `hb_set_zoom(game, act, size, buttons)` write the wanted scope level into the action's zoom field for the games where that field is decoded (CE at +0x1C, Halo 2 at +0x2A, Halo 3 at +0x4A) and return false for the others.
- `hb_replace_id(cfg, size, person, bot)` replaces every 8-byte copy of the human player's identifier in a cloned configuration with the bot's own, at any alignment (Halo 3 and its successors keep a second copy that MCC's report reads).
- `hb_apply_look(m, game, cfg, size)` lays the brain's chosen look bytes over a cloned configuration when the pending look is for this game, then clears it so the next bot gets its own.
- `hb_apply_buttons(m, game, act, size, now, prev)` applies the decoded button table: for each entry of this game it clears the entry's mask in the 64-bit word at `act + off`, then sets it while the bot holds the button (or only on the press tick for press-only entries). Clearing first matters because writers copy the human player's action as a template and his own presses must never leak into a bot.
- `hb_spawn_take(unit, last_unit, seq, done)` decides whether a freshly spawned unit should be moved to a brain-chosen spawn point: only a new unit, and only for a target sent while the bot was dead (a target sent while it lives is consumed and dropped).

**`hb_shared`**, in layout order: magic and version; `dll_alive` and `brain_alive` heartbeats (the DLL bumps its own from the main thread); `game_tick`, incremented by whichever engine hook is running; `bot_player_index[16]`, which maps a bot slot to a game player index (-1 unused); `actions[16]`; a 256-byte `status` line (the last `logf` message, so the brain can log what the DLL said); the command block (`cmd`, `cmd_seq`, `cmd_done_seq`, `cmd_arg`, `cmd_result`, `cmd_fault`, where fault 1 means the command raised and 2 means the action writer raised); the panel settings (`bots_enabled`, `red_players`, `blue_players`, `difficulty`, `settings_seq`); `cmd_name`, the next added bot's name; `game`; debug buffers (`dbg_seq`, `dbg_action`, `dbg_big`) where hooks copy player 0's raw action each tick for the decoding tools; `h2_raw_valid` and `h2_raw_action`, a decoding aid (when `h2_raw_valid == 2`, Halo 3 and its successors send that raw buffer as the bot's action unchanged; Halo 2 uses value 1 to take it as the template); LiDAR mode fields (`lidar_mode`, `lidar_players`); the notice (`notice_seq`, `notice[128]` as `TITLE|line`); the decoded button table (`btn_map_seq`, `btn_map[32]` of `hb_btn_entry`); the next bot's look (`cmd_look_game`, `cmd_look_off`, `cmd_look[64]`, `cmd_look_mask[64]`), clan tag (`cmd_clan`) and MCC emblem (`cmd_emblem[5]`); per-player spawn targets (`spawn_at[16][4]`, `spawn_seq[16]`, `spawn_done[16]`); and a reserved `chat_seq` and `chat[64]` kept only so the offsets do not move.

`cmd_look_game` has two meanings. A plain game id means "apply these masked bytes from `cmd_look_off` on". The id ORed with `HB_LOOK_ROLL` (0x100) means "roll the armor from the game's own Armory": `cmd_look[0..3]` is a seed, `[4..5]` a slot mask, `[6..7]` a mask of slots forced to the catalog's first item, `[8]` an armor effect value (Halo 4 and Halo 2 Anniversary; 0xFF keeps it), `[9]` a count n followed by n triples (u16 configuration offset, u8 value) laid over the roll for colours and visor. `reach.cpp` and `h4f.cpp` read this format.

The decoded button table is written by the brain at startup from `maps/_inputs/<game>.json` (produced by `tools/decode_buttons.py`) via `botctl.set_button_map`. Each `hb_btn_entry` names a brain button bit, an offset into the action, a press-only flag, a game id and a 64-bit mask. This lets a newly decoded button reach a game without rebuilding the DLL.

### `native/botcore.cpp`

`botcore.cpp` is the DLL's core: the entry point and main loop, the settings file, the brain process, and the complete Halo: CE implementation. Its header comment describes only the original Halo: CE stages; the file now also orchestrates every other title through the `*_watch()` calls and the menu watcher.

**Startup (`DllMain`, `main_thread`).** `DllMain` only spawns `main_thread`. That thread:

1. Records the DLL's folder (`native\bin`) in `g_dir` and loads `bot_profiles.ini` from it through `bots_panel_profiles()`. `tools/launch.py` writes that file before injecting, so the panel's name generator can use the install's 15 bot profiles.
2. Opens a log file named after the DLL (`botcore.log`, or `botcore_<tag>.log` for a tagged build) in shared-read mode so it can be read while MCC runs. `logf()` appends each line to this file and also copies it into `g_shm->status`.
3. Checks for an `EasyAntiCheat` process and unloads itself (`FreeLibraryAndExitThread`) if one is running.
4. Creates the shared memory mapping, writes magic and version, marks all bot slots unused and aligns `cmd_done_seq` with `cmd_seq` so a stale command is not replayed.
5. Calls `load_settings()`, `MH_Initialize()`, `overlay_start()` and `report_hooks()`.
6. Enters the forever loop: bump `dll_alive`; rehook `halo1.dll` if it is loaded but not hooked (waiting 500 ms for the loader and checking the module is still at the same address); call `h2_watch`, `h3_watch`, `reach_watch`, `odst_watch`, `h4f_watch` and `spawnhook_watch`; then run the brain state machine.

**Brain control.** `mcc_menu_state()` (in `overlay.cpp`) reads one byte of MCC's executable that is 0 in the menus and 1 in a game. When it changes to 1 the loop records `g_brain_due`, resets `g_shm->game` to 0 and clears `g_playback`; when it changes to 0 the brain is stopped. The brain is started only once some engine hook has set `game` to 1..7 (proof that a supported engine is actually ticking) and no Theater film is playing; if nothing ticks within 60 s the start is abandoned. A film that starts while the brain runs stops it. `start_brain()` clears all bot slots (bots belong to one match), and if bots are enabled launches

`<python> -u -I "<root>\tools\play.py" --red R --blue B --tier T --minutes 600 --wait 120 --lidar N --roster "<root>\native\bin\botcore.ini"`

with no window, the working directory at the project root and stdout and stderr redirected to `logs\brain.txt`. `<python>` comes from `hb_python()` (`bots_panel.cpp`): the install's own `python\python.exe` if present, else `python` from `PATH`. `--tier` is one of `novice`, `average`, `strong`, `top`, a mixed list, or `scaling`, from the panel's difficulty. `stop_brain()` terminates the process.

**Settings (`botcore.ini`).** `load_settings()` sets defaults (bots on, 4 v 4, Mixed difficulty, LiDAR off with 16 players), then parses `key=value` lines: `enabled`, `red`, `blue` (capped at 8), `difficulty` (0-5: Easy, Normal, Heroic, Legendary, Mixed, Scaling), `lidar`, `lidar_players` (2-16), `prejoin` (the H2A and Halo 4 first-tick hold, see `h4f.cpp`), `collector` (the brain records the player for the Observer), `sounds` (panel volume 0-100) and `scale_games` (1-20 games averaged by Scaling). Roster lines (`roster=1`, `teams=N`, `bot=team,tier,style,name`) are handed to `roster_parse_line()` in `bots_panel.cpp`. Two migrations run once: a file with no roster gets a roster built from the old team sizes (keeping one spot for the human on the bigger side), and a roster saved with the global difficulty on Scaling but no bot marked Scaling gets every bot set to Scaling. `save_settings()` recomputes `red_players` and `blue_players` from the roster (for older readers such as `botctl.settings()`) and rewrites the whole file. The overlay calls it whenever the panel reports a change.

Other globals defined here and used elsewhere: `g_shm`, `g_roster` (the panel's roster), `g_prejoin`, `g_collector`, `g_scale_games`, `g_sounds`, `g_playback` (set by game hooks while a Theater film plays), `film_dir()` (creates and returns `%LOCALAPPDATA%\ProjectProvingGrounds\films`, shared by every copy of the mod), `film_old_dir()` (`<project>\logs\films`, read only) and `bug_reports_dir()` (`<project>\logs\bug_reports`).

**Halo: CE hooks.** All CE addresses (relative to `halo1.dll`, found by reverse engineering, listed in the file) target MCC build 1.3528. `hook()` removes any previous hooks (MCC reloaded the DLL), clears the bot slots, and installs three detours:

- `tick_hook` on the game tick counter function. After calling the original it increments `game_tick`, sets `game = 1`, runs a pending command (`run_command`), refreshes the bot unit table (`update_bot_units`) and rewrites each bot's player identifier (`ce_own_ids`, so MCC does not name the bot after the host).
- `dequeue_hook` on the host's action dequeue. CE fills one 0x30-byte action per live player in players-array order from the local input queues, so a bot's slot is empty. After the original runs, `fill_bot_actions()` walks the live players in the same order and, for each bot driven by the brain, writes an `mcc_action_head`: yaw, pitch, throttles, trigger value, unit control flags mapped from the button bits (`UC_FIRE`, `UC_JUMP`, `UC_CROUCH`, `UC_GRENADE`, `UC_MELEE`, `UC_ACTION | UC_SWAP` for Use, `UC_RELOAD`), the wanted weapon slot and the zoom level. Flags in `UC_PRESS_ONLY` are cleared on ticks where they were already held, because CE acts on the press edge for those.
- A hand-assembled stub on CE's "unit to local player index" function. The weapon update asks it before creating bullets for client-predicted weapons; a non-local player's bullets are expected to arrive from his own machine, so a bot's pistol spent ammo and fired nothing. `make_unit_local_stub()` emits machine code (not C++) because the caller relies on the original clobbering only `rax`, `rdx` and `r8`: it compares the return address against the two known bullet call sites and, if the unit in `ecx` is in `g_bot_units`, returns 0 (local); otherwise it jumps to the MinHook trampoline. A `ponytail:` comment notes the known gap: a bot on a vehicle turret still produces no turret bullets.

**CE commands.** `run_command()` handles `ADD_BOT`, `ADOPT` and `SET_TEAM` on the game thread. `add_bot()` clones the local player's 0x4C-byte network record, sets the name (from `cmd_name`, else `Bot N`), a service tag derived from the name (`bot_service_tag` in `report.cpp`) and any look bytes, and calls the game's own `player_new` for the given machine. On success it notes the bot for MCC's report (`report_note_bot`), writes the bot's own identifier, adopts it into a free slot and applies the team. `adopt()` drives an existing player; `set_team()` writes the team field, which takes effect on the next spawn. `ce_player_numbers()` reads a player's kills, assists, deaths, suicides and the game variant's engine type for `report.cpp`, because CE does not give MCC rows for bots.

### `native/inject.cpp`

`inject.exe` is the loader. It resolves the DLL path (the first argument, or `botcore.dll` next to the executable), refuses with exit code 2 if any `EasyAntiCheat` process is running (so bots can never enter a matchmaking session), finds `MCC-Win64-Shipping.exe` (exit 3 if absent), and refuses with exit code 7 if a module whose name starts with `botcore` is already loaded, since two builds would hook the same code (`--force` overrides). It then writes the path into MCC with `VirtualAllocEx` and `WriteProcessMemory`, starts a remote thread at `kernel32!LoadLibraryW`, waits up to 10 s and reports success (exit 0) or `LoadLibrary` failure (exit 6). `tools/launch.py` runs it; `botctl.injector()` locates it and, because Windows Defender sometimes deletes DLL injectors, can restore it from git or rebuild it with the same `cl` line `build.bat` uses.

### `native/h2.cpp`

Halo 2 Classic (`halo2.dll`). The file follows the CE plan with Halo 2's layout. Addresses are found by reverse engineering and listed in the file.

`h2_watch()` hooks the engine's players-update function, which receives the tick's action block: a bitmask at +8 of players that have an action and 0x60-byte actions from +0x100. Hooking clears all bot slots. The detour `h_update` sets `game = 2`, runs a pending Halo 2 command, copies player 0's action into `dbg_action`, writes every driven bot's action and calls the original.

The action writer starts from a template (the raw buffer when `h2_raw_valid` is set, else player 0's action), then clears the fields that must not come from the human: the interaction type and object, the melee target and the aim-assist block (a template aim assist with a cleared target makes the game's action check reject the action and replay the bot's previous one). It copies the bot's own weapon set from its unit so a weapon switch request matches what the unit control checks, sets the wanted primary weapon index, and writes the button flags (jump; fire as a held pattern plus a press-only bit, because Halo 2 fires on the press edge), yaw, pitch, throttles and both triggers. Use is written as the "held long" state the game uses for "hold to pick up", and for a bot on foot with no seat requested `h2_pickup_target()` scans the object table for the nearest loose weapon within 1.5 units and offers it as a type-1 (weapon pickup) interaction. Reload sets its two bits natively (the button table clears its mask each tick and would fight the Use bit). Finally `hb_apply_buttons` runs and the bot's bit is set in the action mask.

`h2_add_bot()` builds the creation record for the engine's `player_new_at_index`: valid flag, the host's machine identifier, a made-up player identifier, and a copy of player 0's 0x84-byte configuration with the bot's name, team (configuration +0x7C), look bytes and service tag. The controller and user fields end up as "none" (`0xFFFF` and -1): the code first computes a split-screen style local index and then overwrites it, so the "second local player" comment in that function describes an earlier experiment, not the current behaviour. Arg bits 16 and 17 select "no machine" and an unknown machine identifier for testing. The command runner only accepts commands with bit 24, because adding a player to a Halo 2 match from a CE-style command ends the match.

### `native/h3.cpp`

Halo 3 (`halo3.dll`). Halo 3 keeps its engine globals in thread-local storage, so the file reads the DLL's TLS index from its PE header (`tls_index_of`) when hooking and finds the game thread's block through `gs:[0x58]` (`h3_tls`). From that block it reaches the players array, the object header table and the game globals, whose +0x200 holds the match's player configurations. Offsets are listed in the file.

`h3_watch()` hooks the players-update function (actions of 0x88 bytes from +0x10). The detour `h_h3_update` sets `game = 3`, runs a pending Halo 3 command (bit 25), copies player 0's action for decoding and then, for every bot:

- Sets the player's "present" flag (bit 0 of player +4) every tick, because the engine only spawns or respawns a unitless player while it is set and the session clears it for players of no known machine.
- Skips a bot with no unit (waiting to respawn); writing for it froze the other bots' input.
- Uses the raw decoding buffer when `h2_raw_valid == 2`, else player 0's action as the template.
- Clears the interaction slots and the aim-assist block, writes the zoom level, copies the unit's current weapon set (the one the unit control compares against) and the wanted primary index, and sets the action's validity byte and the unit's life counter (the engine ignores an action whose counter does not match, so a respawned bot would otherwise ignore everything).
- Writes control flags, yaw, pitch, throttles, trigger and jump values.
- For Use: the "held long" value, a weapon pickup target from `h3_pickup_target()`, and a boarding request from `h3_board()`.
- Applies the decoded button table.

`h3_pickup_target()` finds the nearest loose weapon within 1.5 units, including weapons attached to something that is not a biped or vehicle. A CTF flag hangs on a stand, so its world position is the stand's plus its offset; on Sandtrap the stands ride on Elephants, so the offset is rotated into the vehicle's axes (forward at object +0x5C, up at +0x68, left as their cross product). `h3_near_vehicle()` finds the nearest upright vehicle within 3 units (or, with the turret bit, the nearest gun riding on a vehicle, placed by the same axis transform), passing over a destroyed one: a vehicle, or the vehicle a gun rides on, whose damage flags byte at object +0x110 has bit 2 set (the game's own "destroyed" bit, the one its `object_get_health` script function answers 0 for). `h3_board()` writes interaction type 4 with the requested seat and vehicle so the game's Use handler seats the unit.

`h3_add_bot()` copies player 0's configuration from the game globals, sets "valid", and by default an unknown machine identifier so no local user is mapped (arg bit 17 would put the bot on the host's machine and split the screen; bit 16 makes it machine-less and its team loses). Controller and user are set to none, the player identifier is replaced everywhere with `hb_replace_id`, team, both name copies, service tag and look are written, the bot is noted for the report and `player_new_at_index` is called. After creation the "present" flag is set and the host's machine identifier is copied into the player, because the server only applies damage from a player's shots when his machine is the host's.

### `native/reach.cpp`

Halo: Reach (`haloreach.dll`) is the most complete port. The structure is Halo 3's (TLS globals, players-update hook, cloned configuration) with Reach's offsets; the file's header still carries the original Halo 3 notes below the Reach summary, and a couple of strings and comments still say "Halo 3" (the command runner's comment says "marked for Halo 3" but checks Reach's bit 26, and `reach_watch` logs `h3 hook failed` on failure). Addresses and offsets are listed in the file.

**Hook and per-tick flow.** `reach_watch()` hooks the players-update function (actions of 0xA8 bytes from +0x10). The detour `h_hr_update`:

1. Reads the game globals and sets `g_playback` from the byte that is 1 while a Theater film plays.
2. Calls `film_tick()` (`film.cpp`) with a key hashed from the match's game options (identical in a match and its film), the game's own tick count, the playback flag and Reach's command bit. In a live match this freezes the bot slot table and actions for the tick and records them; in a film it returns the recorded input and injects the recorded commands. Everything below uses this frame, not shared memory directly, so a film replays exactly what the match did.
3. Sets `game = 4`, runs a pending command, applies spawn moves (`hr_spawn_moves`), copies player 0's action for decoding.
4. For each bot in the frame: sets "present", marks the action, uses the raw buffer when decoding, else player 0's action as the template, and then overwrites the bot's own fields.

**The Reach action writer.** It copies the unit's weapon set at the offset the unit control checks (and clears the secondary when it equals the new primary, which the game would reject), clears the three interaction slots (the template carries the human's pickup prompt and melee target), zeroes the aim-assist weights (they pulled the bot's shots toward the human's target), sets the validity int and the unit's life counter, and writes jump and fire flags, yaw, pitch, throttles, trigger and the vertical input (`hb_vertical`, needed for a Falcon pilot to leave the ground). Use is assembled from three cases:

- On foot, no seat requested: `hr_loose_weapon()` gathers loose weapons within reach (type 2 objects whose pickup test field is clear, attached only to acceptable parents; one riding a marker is placed at the marker) and `hb_pick_loose()` chooses between them by view direction; the chosen weapon goes into interaction slot 0 as type 2 with the Use press bits.
- On foot with a seat requested: `hr_near_vehicle()` finds the nearest vehicle within 3 units across and 2 up or down (top level, or a turret riding on one with the turret bit), written as interaction type 5 with the seat. A destroyed vehicle (bit 2 of the damage flags byte at object +0x138), or a turret on one, is passed over.
- In a seat with no seat requested: the Use press bits get the bot out (holding alone did not).

**Armor from the Armory.** When the pending look is `4 | HB_LOOK_ROLL`, `hr_add_bot()` calls `hr_roll_armor()`, which uses the game's own Armory functions (item count per slot, the n-th item's id, the item record with its variant count, and "equip this item on an appearance block") to pick a random legal item and variant per slot in the mask with an xorshift generator seeded from the brain. Slots in the "none" mask get the catalog's first item. Slot 12 (the Firefight voice, not armor) is always skipped because equipping it faulted. Then the (offset, value) triples are laid over the configuration for colours. The first roll in a session also calls `hr_log_catalog()`, which writes the whole catalog and, for every item variant, the bytes it writes into a scratch appearance block to `botcore.log`; `tools/armory_tables.py` turns that log into the tables the 3D preview uses. Without a roll request the plain `hb_apply_look` path is used.

**Bot creation.** `hr_add_bot()` clones player 0's configuration (0xA0 bytes), sets an unknown machine, no controller or user, the bot identifier (also written at the Xbox user id field), team byte, both name copies, service tag and look, notes the bot for the report, calls `player_new_at_index`, then sets "present" and copies the host's machine identifier (without it a bot's hits did no damage).

**Loadouts.** `hr_set_loadout()` (`SET_LOADOUT`, bot players only) writes the slot into the two player fields that the host's own loadout-request handler writes; it takes effect at the next spawn. `botctl.set_loadout()` sends it.

**Invasion spawns.** Two cooperating pieces. `hr_bot_solo_spawn(player)` is called from `spawnhook.cpp` just before the game's spawn check; for a bot it clears the per-player co-op spawning byte so the game does not wait for a spawn-screen choice the bot cannot make, and the bot respawns on the normal timer. `hr_spawn_moves()` then moves the bot's new unit to the spawn the brain picked (`brain/invasion.py` writes `spawn_at` and bumps `spawn_seq` while the bot is dead, via `botctl.spawn_at`). It uses `hb_spawn_take` to act only on the first tick of a new unit, skips NaN targets (a cancelled target), verifies the first nine bytes of the game's internal teleport function before calling it (any other game build: bots spawn where the game puts them, logged once), calls it with the position and a facing built from the yaw, records the move in the film (`film_spawn`) and logs it.

### `native/spawnhook.cpp`

A single hook on Reach's per-player spawn check, which the players update's spawn loop calls. The detour calls `reach.cpp hr_bot_solo_spawn(player)` and then the original. `spawnhook_watch()`, called from the main loop, keeps the hook on while `haloreach.dll` is loaded. It differs from the other watchers in one deliberate way: hooks are created once per address and afterwards only disabled and re-enabled, never removed, because MinHook frees a removed hook's trampoline and a game thread inside it at that moment would crash. A module reloaded at the same address has its original bytes back, so the watcher disables (rewriting the original bytes) and enables again. It checks the function's first eight bytes before creating the hook and logs once if they do not match.

### `native/film.h` and `native/film.cpp`

Theater support for bots, used by Reach. A film replays a match from its start by re-running every recorded tick, but bots are created outside the game's recorded player list and driven by writes into the action array, so without help the replay diverges and MCC drops the film; the brain, started when the menus gave way to a "game", would also add bots into the film. `film.cpp` solves this by recording, for every live match, exactly what botcore gave the game, and replaying it in the film.

`film.h` declares `film_frame` (the bot slot table and 16 actions for one tick), `film_tick()`, `film_end()`, `film_spawn()`, and `film_hash()` (64-bit FNV-1a, used to build the film key from the match's game options).

Recordings live in `%LOCALAPPDATA%\ProjectProvingGrounds\films\<key>.hbf`, one folder for every copy of the mod (a film is also looked up in the copy's old `<project>\logs\films`); the newest 30 are kept (`prune`). Records are `u32 tick, u16 type, u16 length` followed by the bytes, with four types: `R_CMD` (a command with all the shared memory it reads: name, look, clan), `R_BOTS` (a `film_frame`, written only when it differs from the last one), `R_BUTTONS` (the decoded button table, when its sequence changes) and `R_SPAWN` (a spawn move).

`film_tick(key, tick, playback, cmd_bit)`:

- Live (`playback` false): a new key or a tick going backwards starts a new recording. The slot table and actions are copied out of shared memory into the frame for this tick (so the hook sees one consistent snapshot) and the pending command for this game, a changed button table and a changed frame are recorded. Returns the frame.
- Film: on a new key it opens the matching recording (mode 2) or notes that none exists (mode 3, no bots). On a rewind (the tick going back) it reads from the start, applying frames and button tables but not commands up to the new tick, because the bots created earlier are already part of the rewound game state. Otherwise it applies every record up to the current tick: frames go into the frame and back into shared memory (the spawn hook reads the slot table), commands are written into the command block with `cmd_seq = cmd_done_seq + 1` so the hook's command runner executes them this very tick, and spawn records set the spawn target so `hr_spawn_moves` repeats the move. Any fault closes the files and returns null, which makes the Reach hook skip bot handling for that tick.

### `native/odst.cpp`

Halo 3: ODST Firefight (`halo3odst.dll`) bot teammates, using the Halo 3 plan with ODST's offsets (listed in the file). Firefight is cooperative, so `od_add_bot()` keeps the human's team from the cloned configuration and never writes a team; it sets an unknown machine, no controller or user, the bot identifier everywhere (`hb_replace_id`), both name copies, service tag and look, creates the player, and then sets "present" and copies the host's machine identifier. The hook `h_od_update` sets `game = 5`, runs commands marked with bit 27, copies player 0's action into both debug buffers (`dbg_big` holds the full 0x240-byte action), keeps each bot "present", and fills its action from player 0's template through `od_fill()`: validity byte and life counter, cleared interactions and aim assist, zoom forced to none, the unit's checked weapon set and the wanted primary, jump and fire flags, view, throttles, trigger, jump value and a plain held Use. ODST has no pickup targeting or boarding in this file. The brain caps Firefight at four players (`botctl.player_cap`) because more crashed ODST.

### `native/h4f.cpp`

Halo 2 Anniversary (`groundhog.dll`, game 6, command bit 28) and Halo 4 (`halo4.dll`, game 7, bit 29) share one engine family descended from Reach, so one code path serves both. The `h4f_game` struct holds per-game constants (DLL name, ids, the players-update and player creation addresses, the unit's weapon-request offset, the player's loadout field, and the Armory function addresses) plus runtime state (module base, hook patch bytes, TLS index, trampoline, last-tick buttons). Two instances, `g_h2a` and `g_h4`, are hooked by `h4f_watch()` through `f_watch()`. Every engine function the file calls beyond the hooked ones is verified first by comparing its prologue bytes; on any mismatch that feature is switched off and logged once.

**Per-tick flow (`f_update`).** Sets `game`, detects the first tick of a match (no call for 3 s), runs a pending command, copies player 0's action, and for each bot keeps it "present", rewrites its player identifier in both of its player bodies (`f_own_ids`, so MCC's post-game report names it correctly), then fills its 0x100-byte action from player 0's template (`f_fill`), applies the button table, and attempts boarding and exiting.

`f_fill()` writes the validity int and life counter, the unit's requested weapon set and wanted primary, crouch and jump flags, fire, view, throttles, trigger and the whole 64-bit Use word (writing the whole word stops the human's Halo 4 sprint press from toggling every bot's sprint). Then:

- Halo 4: `f_sprint()` drives sprint. Sprint is an ability whose press toggles it, and the body only sprints while a separate bit is held, so the function presses only when the game's sprint state differs from the brain's wish and holds the sprint bit while it is wanted.
- Halo 2 Anniversary: `f_interaction()` gives the bot its own interaction slots. With Use held on foot and no seat requested, it offers the nearest loose weapon within 1 unit as interaction type 13, at most once every 45 ticks. For 45 ticks after an offer, `f_update` suppresses Use and the weapon request so the held Use does not immediately drop a just-taken flag.

**Boarding and exits.** The bots' Use did nothing at vehicles in these games, so botcore calls the game's own scripting internals. `f_board()` (at most every 15 ticks while Use is held with a seat requested) finds the nearest upright top-level vehicle within 3 units that is not destroyed (`f_near_vehicle`: bit 2 of the damage flags byte at object +0x16C in both games), lists its seats and its guns' seats with the function behind the `vehicle_load_magic` script command, logs each vehicle type's seats once, picks a seat by role from the seat definition's flags (driver, gunner with the turret bit, or a passenger seat; boarding and hijack spots skipped), checks it is empty and that the unit may take it, and enters it through the unit's own virtual function. `f_exit()` calls the function behind the `unit_exit_vehicle` script command for a seated bot holding Use with no seat requested.

**Armor rolls.** `f_roll_armor()` mirrors Reach's: random visible item and variant per slot in the mask, the first item for slots in the "none" mask, applied by `f_apply_variant()` to both copies of the configuration's appearance block by writing the variant's region permutations and, for Halo 4, its special value, as the game's own equip does. `f_log_catalog()` logs the full catalog once per session. `f_add_bot()` then applies the armor effect byte and the (offset, value) triples to both copies.

**Bot creation and loadouts.** `f_add_bot()` clones the human's 0x200-byte configuration (keeping his team for Firefight and Spartan Ops unless a team is given), sets an unknown machine, no controller or user, the bot identifier, team, both names, both service tag copies and the look, creates the player, sets "present" and copies the host's machine identifier. `f_set_loadout()` writes the loadout slot fields for a bot.

**The first-tick hold (`f_prejoin`, H2A and Halo 4).** Halo 2 Anniversary creates each team's CTF flag, stand and goal on the first tick only for teams that already have players, but the brain starts on that tick, so the bots would join too late for the other team's objects to exist. Halo 4 Flood picks its first round's Flood from the players present at the start: with the bots joining 0.3-8 s later, round 1 had no Flood and the game ended it at once (since botcore s163 the hold runs in Halo 4 too). When the first tick is detected with the match clock under one second (player +0xA94 in H2A, +0xA8C in Halo 4), bots enabled, `prejoin` on in `botcore.ini` and no bot yet in the match, the hook holds the game thread and keeps running commands every 5 ms until no command has arrived for 1 s after the last one, with a 4 s limit if none arrives and an 8 s cap overall.

### `native/report.cpp`

MCC itself (not the engine DLLs) builds the post-game report, the scoreboard emblems, the roster and player cards, and it identifies players by Xbox user id. Bots carry made-up ids MCC does not know, so without this file they showed blank names, the host's name, missing emblems or a red cross. `report_hooks()` (called once at startup) verifies the prologues of six functions in `MCC-Win64-Shipping.exe` and that the report builder's two row loops call the expected functions at the expected sites; on any mismatch (another MCC build) it leaves MCC untouched. Then it hooks four functions:

- `h_build` on the post-game report builder: writes each bot's real team into its results entry (bot ids only) and logs which result rows MCC was given. For Halo: CE, which gives MCC only the human's row, `ce_rows()` first creates a row for each noted bot from the human's row as a template, with the bot's id, team and its kills, assists, deaths and score read through `botcore.cpp ce_player_numbers()`.
- `h_gamertag` on the gamertag lookup: when called from one of the builder's row loops (checked by return address), remembers which bot the current row is for.
- `h_string` on a string constructor: at the builder's two name call sites, substitutes the pending bot's name for the blank MCC would produce.
- `h_profile` on the player profile lookup: for a bot id, fills the output with MCC's own "unknown player" defaults, then the bot's emblem (when one was sent), clan tag and service tag (assigned through MCC's own string assign so MCC's allocator owns them) and reports found. Every other id goes to MCC.

The per-bot data comes from `report_note_bot()`, which every game's add function calls before creating the player, with the name, service tag, team (or -1 to keep the game's), clan tag from `cmd_clan` and emblem ids from `cmd_emblem` (the brain sends these from `bot_profiles.ini` and `brain/emblems.py`). `bot_service_tag()` derives a 4-character service tag from a name: its capitals and digits, topped up with the following lowercase letters to at least three characters.

### `native/overlay.cpp`

`overlay.cpp` owns everything drawn over MCC and every input hook. Its header comment still says it draws over the Halo: CE lobby; it now covers every title with bots (CE, Halo 2, Halo 3, Reach, Halo 2 Anniversary and Halo 4; the ODST lobby is not recognised as one of them, so no tile appears there).

**Hook installation (`overlay_start`).** It creates a throwaway window, device and swap chain to read `Present` (vtable slot 8) and `ResizeBuffers` (slot 13), which are shared by all swap chains in the process, and hooks them. It also hooks `kernelbase!CreateFileW`, `user32!GetCursorPos` and `GetPhysicalCursorPos`, and `xinput1_3!XInputGetState`, logging each result. `mcc_menu_state()` (also used by `botcore.cpp`) reads MCC's menu/game byte under an exception guard.

**Which lobby is open.** MCC's lobby is a Scaleform movie, so the mod cannot add a real tile; instead it infers the screen. `h_createfile` watches file opens: opening `Screens\MultiplayerCustomGame.gfx` starts a short window in which the first `game_variants\` or `maps\info\` file names the lobby's title (`title_of` maps `halo1\`, `halo2\`, `halo3\`, `haloreach\`, `groundhog\`, `halo4\` to 1, 2, 3, 5, 6, 7 and anything else to 4). A later variant file from another title means the lobby was left. For a few seconds after a lobby opens it also logs the files it reads, as evidence for supporting new titles. Because a lobby can be covered (the carnage report, another menu) without any file being opened, `probe_lobby()` checks the frame itself every eighth frame: it copies two thin vertical strips of the back buffer where the stock OPTIONS and START tiles draw their left frame lines into a staging texture and requires a bluish line down at least 70% of the tile height on both. `in_ce_menus()` (despite its name, used for every supported title) is true when the title is supported, the probe sees the lobby and MCC is in its menus.

**The Present hook (`h_present`).** On first call it gets the device and context, creates the ImGui context with no ini file, loads Bahnschrift at two sizes scaled to the back buffer height, styles ImGui in MCC's dark blue, initialises the Win32 and DX11 backends, creates the render target view and subclasses the game window with `wndproc`. Each frame after that it decides what is visible: the tile and panel over the lobby, the notice, or the bug report UI over a match. When anything is visible it starts an ImGui frame (reading the real cursor through the `t_ours` thread flag), enables keyboard and gamepad navigation only while the panel is open (so the lobby's Enter can never press the tile), draws, and renders onto the back buffer. Any exception disables the overlay rather than crashing MCC. `h_resize` releases and recreates the render target view around `ResizeBuffers`.

**The tile (`draw_tile`, `draw_helmet`).** The tile sits right of START in the same 16:9 area and at the same size as the stock tiles (`tile_rect`), styled with colours sampled from them, with an original vector Spartan helmet whose "active camo" ripples are animated Bézier curves (no game art). Its summary reads `OFF`, `LiDAR N`, `No bots`, `RvB Difficulty` or `N bots Difficulty`, and a key prompt beneath shows `B` or, after pad input, `LS+RS`. Clicking it opens the panel.

**The panel (`draw_panel`).** Builds a `bots_panel_env` pointing at the roster, the shared memory settings and the `botcore.cpp` globals, with callbacks for textures (`make_texture` creates an SRV on MCC's device), the 3D model (`render_model`, `model_has`, and the `mv_*` zoom, head and headroom functions) and sounds, then calls `bots_panel()`. When it reports a change, `settings_seq` is bumped and `save_settings()` rewrites `botcore.ini`.

**Input capture.** While the panel is open the lobby must not react to it. `wndproc` toggles the panel on `B` (unless a name is being typed), closes it on Esc when no popup is open, feeds messages to ImGui, and swallows mouse and keyboard messages (and raw input) while the panel is open, plus clicks on the tile. Because MCC also polls the cursor itself (moving right slid its roster pane open), `h_getcursorpos` and `h_getphyscursorpos` return the position where the cursor was when the panel opened to every caller except the overlay's own frame. `h_xinput_get` reports a pad at rest to MCC while the panel is open and until every button is released afterwards. `pad_frame()` toggles the panel when both sticks are clicked together, closes it with B at the top level, and tracks whether the last input came from the pad (prompts then name pad buttons).

**Notices.** When `notice_seq` changes, `draw_notice()` shows `notice` (`TITLE|line`) at the top centre for 3.5 s, longer for long lines up to 7 s, with fades, a gold title and MCC's frame colours. It uses the foreground draw list, not a window, so it never takes input. The brain sends these through `botctl.notice()`.

**Bug reports over a match.** `in_match()` is true in a game of a supported title outside Theater. When the OS cursor is visible over the game (which in a match only happens with MCC's pause menu up) a "Report bot bug" button appears; F9 toggles the report window at any time. While the window is open, input goes to ImGui and never reaches the game; ImGui is fed game input only while the report UI is up, so nothing typed during play is queued. `save_bug_report()` writes `<project>\logs\bug_reports\<yyyymmdd-hhmmss>\report.json` with the time, title, how it was opened and the JSON-escaped description, then raises a "BUG REPORT SAVED" notice. The brain (`tools/live_bots.py`) adds the match recording beside it and `tools/bug_reports.py` lists reports.

**Panel sounds (`play_sound`).** Plays WAV data generated in memory by `bots_panel.cpp panel_sound_wav()` with `PlaySound` asynchronously, regenerating a sound when the volume changes.

### `native/bots_panel.h`

The interface between the overlay and the panel, kept free of Direct3D so the panel can also be drawn offscreen by the developer preview. It defines:

- `hb_bot` (name up to 15 characters, team 0-7, tier 0-4 where 4 is Scaling, style 0-6 or 7 for "any") and `hb_roster` (count, number of team cards shown, up to `HB_ROSTER_MAX` = 15 bots, so 16 players with the human).
- `bots_panel_env`, everything the panel needs: pointers to the roster and settings, the lobby title, the display scale, fonts, the open flag, and the callbacks for textures, model rendering and queries, and sounds. Any callback may be null, and the panel then degrades (no pictures, no 3D view, no sounds).
- The sound kinds (`PS_MOVE`, `PS_SELECT`, `PS_BACK`, `PS_OPEN`, `PS_ERROR`) and `panel_sound_wav()`.
- `bots_panel()` (draw; returns true when settings changed) and `hb_python()`.
- Roster operations (`roster_fill`, `roster_add`, `roster_remove`, `roster_balance`, `roster_shuffle`, `roster_rename_all`, `roster_name`, `roster_on_team`, `roster_mixed_tier`, `roster_max_teams`) and the `botcore.ini` roster line parser and writer.
- Profile functions for `bot_profiles.ini`: load, re-roll, count, names, clan tags, hand-set look overrides, save, and the experience, effects, species and Elite share settings.
- Name helpers (`team_name`, `tier_name`, `tier_key`, `style_name`).
- `bug_report_env` and `bug_report_ui()` for the report button and window.

### `native/bots_panel.cpp`

The BOTS panel, the largest file in `native/` and pure Dear ImGui. Its opening comment lays out the design: tasks (set bots up fast, move them between teams, tune one, turn bots off, LiDAR), layout (header, toolbar, team cards beside an inspector, footer), states (off, LiDAR, empty, full, Halo: CE's two teams, eight teams, long names, confirmations) and a fixed type and spacing scale in MCC's colours.

**Tables and names.** Team names and colours (eight teams), difficulty names (`Easy`, `Normal`, `Heroic`, `Legendary`, `Scaling`) with their file keys (`novice`, `average`, `strong`, `top`, `scaling`) and descriptions, play style keys in `brain/profiles.py` order (`rusher`, `camper`, `flanker`, `objector`, `spammer`, `grudger`, `sniper`, `any`) with display names and descriptions, and title names. The name lists (`FIRST`, `SECOND`, `WORDS`) mirror `brain/names.py`; `made_name()` builds gamertag-style names in several patterns. `CLAN_TAGS` mirrors `brain/looks.py`, and `made_clan()` picks a known tag two times in three, else a random 2-4 character tag.

**The roster in `botcore.ini`.** `roster_parse_line()` reads `roster=1`, `teams=N` and `bot=<team>,<tier key>,<style key>,<name>` lines (the name is the rest of the line); `roster_write()` writes them. `tools/play.py` and `tools/live_bots.py` read the same lines to add the listed bots and give each its difficulty and style. Roster operations: `roster_add()` names each new bot with `roster_name()`, which prefers an unused profile name from `bot_profiles.ini` (so a bot keeps its name and look from match to match) and otherwise generates a unique one; `roster_fill()` deals bots team by team so the 15-bot cap cuts every team evenly, Mixed cycling Heroic, Normal, Legendary, Easy; `roster_balance()` moves bots from the largest team to the smallest until they are within one; `roster_shuffle()` reassigns teams keeping sizes; `roster_max_teams()` is 2 for Halo: CE and 8 otherwise.

**Bot profiles (`native\bin\bot_profiles.ini`).** The install's 15 bots, written by `brain/looks.py` on first launch and by the Settings tab's re-roll. Lines: `experience=original|modern`, `effects=none|rare|common|frequent`, `species=spartans|mixed|elites`, optional `elites=<percent>`, and `bot=<name>,<look seed>[,<clan tag>[,<overrides>]]`, where overrides are `<game>.<field>=<value>` pairs separated by `;` holding looks set by hand in the bot editor. `bots_panel_profiles()` loads it (botcore calls this at startup), `profiles_save()` rewrites it from memory, `profile_over_get/set()` read and edit override pairs, and `profiles_reroll()` writes 15 new unique names, look seeds and clan tags (two or three clan tags shared among the bots, about half in none) and reloads.

**Rolled looks (`native\bin\bot_looks.ini`).** The bot editor shows what each bot actually rolled, never "Random". `looks_refresh()` runs `tools/looks_export.py <profiles> <bot_looks.ini>` in the background with the install's Python; `looks_load()` re-reads the file when it changes (at most twice a second, every frame for 3 s after a request) and asks for a new export when the file is missing or older than the profiles. Lines are `<name>|<game>|own|other|k=v;...` ("other" is the species the bot does not prefer). `look_get()`, `look_field()` and `look_text()` read values from it.

**Pictures.** `texture()` loads `native\bin\<file>.rgba` (u32 width, u32 height, then RGBA pixels) once per key through the `make_texture` callback: game logos (`art\<game>.rgba`, made by `tools/panel_art.py`), the stage backdrop (`art\stage.rgba`), armor effect sprites (`art\fx_*.rgba`, from `tools/fx_art.py`), in-game pictures of a bot (`looks\<name>_<game>_<spartan|elite>.rgba`) and emblems (`emblems\<name>.rgba`). Missing files are remembered and not retried each frame.

**UI kit (`namespace ui`).** Colours, a 1080p-relative scale (`px`), three font sizes, and small widgets used across the panel: `caption`, `muted`, `button` (primary, outline, secondary, ghost, danger), `segmented`, `stepper`, `toggle`, `icon_x`, `chevrons` (difficulty rank marks), `nav_button` (a navigable invisible button) and `line`.

**The Bots tab (`bots_panel`).** The panel is a fixed modal-style window with:

- A header: the BOTS title, the lobby's title, a Bots On/Off toggle and a close button.
- Tabs Bots, Settings and Advanced (pad shoulders switch them).
- On the Bots tab, a toolbar with a summary, Quick setup, Balance teams, Shuffle teams, Remove all (with a confirmation), a Data collector toggle (records the human for the Observer; hidden in LiDAR mode, disabled with bots off) and a LiDAR mapping toggle with a players stepper.
- State banners (LiDAR on, bots off, Halo: CE with more than two teams, data collector on).
- The team cards grid (`team_card`: coloured header, count, a removable last empty team, scrolling bot rows, a drop target, and an Add bot button) plus an "Add team" slot (`add_team_card`). Each `bot_row` shows rank chevrons, the name (shortened with "..." when needed) and its style, is draggable onto another team, and has a context menu (Move to, Duplicate, Remove).
- An empty state with a primary Quick setup button.
- The `inspector` for the selected bot: clan tag and name (names and looks are edited in Settings), team chips, difficulty (the four ranks, Scaling on its own row, the "Games averaged" stepper for Scaling), play style, Duplicate and Remove.
- A footer that sets one difficulty for everyone (or Mixed) and Done.

Keys for the selected bot: Delete, Ctrl+D, Ctrl+Left/Right to move between teams, Up/Down to change the selection. `quick_setup` is a modal for teams, bots per team, difficulty and play style that replaces the roster with `roster_fill`. `sync_difficulty()` keeps the footer's difficulty consistent with the bots (Mixed when they differ).

**The Settings tab (`mod_settings`).** On the left the 15 bot profiles, each opening the bot editor. On the right, how the bots suit up (experience, armor effects, species) with a "Re-roll profiles..." button that opens `reroll_dialog` (experience Original or Modern, armor effects None/Rare/Common/Frequent, species Spartans/mixed/Elites with an Elite percentage in steps of 5; a write failure keeps the dialog open with an error), and a panel sounds volume slider.

**The bot editor (`bot_editor`, `ed_*`).** A modal for one profile: name and clan tag (kept unique and free of the file's separators; renaming also renames the roster's bot of that name), a list of games down the left (Halo: CE, Halo 2, Halo 3, Reach, Halo 2 Anniversary, Halo 4, each with its logo), a live preview in the middle and the game's options on the right. Options per game include species (Halo 2, Halo 3, Reach, Halo 2 Anniversary), gender (Reach Spartans, Halo 4), colours from each game's palette (`ed_colors` with tables such as `CE_COL`, `H2_COL`, `H3_COL`, `REACH_COL`, `H4_COL`), armor pieces (`ed_pieces` over the piece tables: Halo 3's helmet, chest, shoulders, visor, arms, legs, tech suit and backpack, and the Elite's slots; Halo 2 Anniversary sets or mixed pieces; Reach and Halo 4 from `look_names.h`), visors, armor effects, and for Reach and Halo 4 "New look" and "Its first look" buttons that change the roll seed. Original experience limits lists to each game's shipped items (the `*_ORIGINAL` counts). Choosing the rolled value again removes the override. Done saves `bot_profiles.ini` and triggers a new looks export. "Back to its roll" clears the game's overrides.

**The preview (`ed_preview`, `ed_model`, `ed_fx`).** The stage image is framed in the bot's primary colour, with a name plate and the bot's emblem in a ring. `ed_model()` builds the model path `native\bin\models\<game>_<spartan|elite>.mdl`, the colour set (primary, secondary, detail, undersuit, visor including Halo 4's front and rim colours) and the list of worn pieces. Halo: CE draws one cyborg in its colour; Halo 2 draws base pieces; Halo 3, Reach, Halo 2 Anniversary and Halo 4 draw the `region:permutation` pairs from `bot_looks.ini` "pieces", falling back to the region's base piece when the model lacks one. It then calls the `render_model` callback. If no model can be drawn the editor shows the in-game picture or, failing that, the game's logo. The bot turns by dragging or arrow keys and zooms with the wheel or Up/Down between upper torso and full figure. `ed_fx()` draws the armor effect over the head position returned by `mv_head`, using the game's own particle bitmaps animated purely from the clock: fire in three colours, hearts, Pestilence, a storm cloud with lightning and birthday confetti. `ed_fx_kind()` selects which effect from the bot's look.

**The Advanced tab (`advanced_settings`).** Settings for the Scaling difficulty, stored in `native\bin\scaling.ini` (read by `brain/scaling.py`): `lock=`, `rating=` (a percentage used while locked), `use=` (0 Standard, k the k-th custom profile) and `profile=<name>|<key>=<percent>|...` lines weighting each of 15 hand settings (`SP_KEY`, in `brain/scaling.py PARAMS` order). The left side shows the current skill rating from the player's K/D, the games-averaged setting and a lock; the right side manages custom profiles (new, rename, delete with a second press to confirm) and each setting's weight next to the value it currently plays at. The numbers come from `logs\scaling_view.txt`, written by `tools/scaling_view.py`; `scale_refresh()` runs that tool with `botcore.ini` and `scaling.ini` when the panel opens, and `scale_load()` re-reads the file when it changes. The Scaling tooltip in the inspector uses the same data.

**Sounds.** `panel_sound_wav()` synthesises short 16-bit mono 22.05 kHz tones into a WAV in memory (a tick for focus moves, a rising pair for select, a falling pair for back, a swell for open, a low double tone for errors). `panel_sounds()` decides once per frame which to play from ImGui's state (keyboard or pad focus moving, a control pressed and released, back, the panel opening, a failed save) and calls `e.play_sound`; the mouse merely hovering makes no sound.

**Bug report UI (`bug_report_ui`).** Draws the "Report bot bug" button beside MCC's pause menu column (with its key) and the report window: a dimmed game, a "What happened" multiline text box with a hint, Cancel and Save report (Ctrl+Enter also saves). It sets `hovered` so the overlay keeps the window's clicks from the game, and returns true when the report should be saved.

**Developer hooks.** Functions named `bots_panel_debug*` set panel state for `native/panel_preview.cpp`, the offscreen preview used for checks; they do nothing in normal use.

### `native/look_names.h`

A generated header (`tools/look_names.py`; not to be edited by hand) included by `bots_panel.cpp`. It defines `piece` arrays naming Reach's and Halo 4's Armory items as the games' own Armory names them: helmet, shoulders, chest, wrist, utility, visor, knees, Elite armor and armor effect for Reach; helmet, shoulders, chest, legs, arms, visor and armor effect for Halo 4. Each value is the customization table index that botcore lays over the game's own Armory roll. Original items come first in the Armory's order, followed by MCC's additions, and a matching `*_ORIGINAL` constant gives how many are original, which the editor uses to restrict lists in Original experience.

### `native/model_view.h`

The renderer's small C-style interface: `mv_pick` (a region and a permutation name, or `#n` for the n-th permutation of that region), `mv_colors` (armor, undersuit, visor, lights, skin, secondary, visor rim and whether the rim colour is used), `mv_render()` (draws a model into its own render target and returns an `ID3D11ShaderResourceView*` usable as an ImGui texture, or 0), `mv_has()` (whether a model has a given permutation), `mv_set_zoom()` (0 whole figure to 1 upper torso), `mv_set_headroom()` (extra space above the head for an armor effect) and `mv_head()` (where the last draw put the head, in view pixels). The header calls it the Settings tab's view; in practice it is the bot editor's preview, which lives under the Settings tab.

### `native/model_view.cpp`

A self-contained Direct3D 11 renderer that draws character models packed from MCC's own map files into an offscreen texture on MCC's device, with the game's rendering state saved and restored around each draw.

**Model files (`load`).** Models are `native\bin\models\*.mdl`, produced by `tools/make_models.py` and the `model_pack` tools. The format starts with the magic `HBMD` and a version. Version 1 has geometry only (position and normal); version 2 adds texture coordinates, a material table (five texture file names per material: diffuse, colour-change, normal, self-illumination and detail normal, plus a detail tiling), and a material index per group, and holds posed models with their weapon. After the header come the groups (region name, permutation name, permutation index, a kind, and an index range), the vertices (32 bytes each) and 32-bit indices. `load()` also computes each group's bounding box so the camera can frame only the worn pieces. Up to four models are cached by path, round robin; a failed load is remembered. Textures are PNG or JPEG files in the model folder's `tex\` subfolder, decoded with WIC to RGBA, uploaded with a generated mip chain, and cached by name (up to 768) across models.

**Group kinds** select the material treatment in the shader: 0 armor, 1 undersuit, 2 visor, 3 lights, 4 skin, 5 skipped, 6 an energy sword blade. Region `weapon` is always drawn.

**Shaders (`HLSL`, `make_shaders`).** One vertex and one pixel shader, compiled at run time with `D3DCompile` (`vs_4_0` and `ps_4_0`). The pixel shader lights the figure as a studio would: a warm key light, a cool fill, a back light for the outline, a sky and ground ambient, ambient occlusion darker toward the feet and on inward-facing surfaces, and screen-space curvature that brightens convex edges and darkens creases. Untextured armor gets fine value noise and semi-gloss specular; the undersuit is matte; the visor reflects a studio environment tinted between its front and rim colours (Halo 4 visors have both). Textured (version 2) pieces use the game's diffuse tinted by the colour-change map (red channel primary, green secondary), normal and detail normal maps applied through a cotangent frame from screen-space derivatives (no stored tangents), specular from the diffuse alpha, and self-illumination in the secondary colour. Guns get a metallic environment term.

**Rendering (`mv_render`).** Resets all device objects if the device changed (an MCC device reset), loads the model, makes shaders and a render target of the requested size (4x MSAA when supported, resolved into a single-sample texture), saves the context state (`save`, which mirrors what the ImGui DX11 backend keeps plus pixel shader textures and sampler), and clears to transparent so the panel's stage shows through. It frames the camera on the bounding box of the worn non-weapon pieces (so every game's figure comes out the same size), applies the zoom by raising the frame's bottom from the feet toward the waist, adds headroom when asked, widens the distance if the arms would be cut off, and turns the model by the yaw. It projects the worn head or helmet pieces' extent to report the head's position and size for `mv_head`. Then it draws each picked group with its colours, flags and textures through a dynamic constant buffer, resolves, restores the game's state and returns the SRV.

### `native/ppg_window.cpp`

`ppg_window.exe` is Project Proving Grounds' app window, a separate program unrelated to MCC. It hosts one of the project's local web pages (the launcher, the Observer, the LiDAR view, the nav painter) in a native window through the Microsoft Edge WebView2 control, so the tools look like a desktop app rather than a browser tab. Usage: `ppg_window.exe --url http://127.0.0.1:8793/ [--title ...] [--icon file.ico] [--width 1040] [--height 700]`; `tools/appwindow.py` starts it.

The program parses its arguments, accepts only `http://127.0.0.1:`, `http://localhost:` and `about:` URLs (anything else becomes `about:blank`), becomes per-monitor DPI aware, creates a dark-titled window sized in 96-DPI units, and creates a WebView2 environment whose user data lives in `%LOCALAPPDATA%\ProjectProvingGrounds\webview`. Once the controller exists it sets a dark default background, disables developer tools, the status bar, default context menus and web messaging, cancels any navigation to a non-local URL (opening `https://` links in the default browser instead), routes new-window requests the same way, fits the view to the client area on resize and navigates to the page. If the WebView2 Runtime is missing it offers to open Microsoft's download page and exits.

### `native/build.bat`

Builds the DLL and the injector with Visual Studio's C++ tools, located with `vswhere` (it exits with a message when none is installed) and set up with `vcvars64.bat`. Usage: `build.bat [tag]`; a tag produces `botcore_<tag>.dll`, because MCC keeps an already injected DLL locked (and `inject.exe` refuses a second botcore anyway, so testing a new build normally means restarting MCC). It compiles `botcore.cpp`, `overlay.cpp`, `bots_panel.cpp`, `model_view.cpp`, `h2.cpp`, `h3.cpp`, `reach.cpp`, `odst.cpp`, `h4f.cpp`, `spawnhook.cpp`, `report.cpp`, `film.cpp`, Dear ImGui with its Win32 and DX11 backends, and MinHook into `native\bin\<name>.dll` with `/O2 /W3 /EHsc /MT /LD` (static runtime, so no Visual C++ redistributable is needed in MCC), linking `d3dcompiler`, `d3d11`, `dxgi`, `user32` and `winmm` (the WIC and COM libraries come from `#pragma comment` lines in `model_view.cpp`). It then compiles `inject.cpp` into `native\bin\inject.exe` at `/W4`. Afterwards it runs three Python tools: `tools/panel_art.py` every time (the panel's logos and art as `.rgba` files), `tools/make_models.py` once (the 3D models, extracted from MCC's own maps) and `tools/fx_art.py` once (the armor effect sprites from the game's particle bitmaps). Without these files the panel still works, showing names instead of logos and logos instead of 3D bots.

### `native/build_window.bat`

Builds `native\bin\ppg_window.exe` the same way (vswhere, vcvars64), as a C++17 Unicode Windows-subsystem program linked statically against `WebView2LoaderStatic.lib` from `third_party\webview2` plus `user32`, `ole32`, `shell32`, `dwmapi`, `gdi32`, `advapi32` and `version`. It is separate from `build.bat` because the app window does not depend on the DLL and changes rarely.

## How a bot thinks (brain/)

The `brain` package is pure Python decision-making. It never touches the game directly: each tick the live runner (`tools/live_bots.py`, about 30 passes a second) builds a `core.Snapshot` of the world from game memory, hands it to every bot's `Bot.think()`, and receives one `core.Action` per bot, which it packs into a button word and sends to the native `botcore` DLL with `botctl.act()`. The offline simulator (`brain/sim.py`) drives exactly the same `Bot` and `Director` objects through the same `Snapshot`/`Action` interface, which is how most behaviour is tested without the game running.

One bot's think loop (`Bot.plan`) runs in a fixed order. Perception comes first: `Perception.update` looks at every enemy, decides whether he is in view (field of view, sight range, line of sight, active camo shimmer, a flare in the eyes), and only after a log-normal reaction delay drawn from the bot's profile does a sighting become "recognized". What the bot knows is kept as `Belief` records (position, velocity, time, whether seen right now, and a source: `eyes`, `radar`, `heard`, `hit`, `callout`, plus a few equipment-specific ones), which fade after the profile's `memory` seconds. Being shot by someone unseen creates a `hit` belief toward the most likely shooter, like the HUD's damage arc. Every `decide` interval (roughly 0.1 s, jittered) `Bot.decide` scores candidate goals such as `("fight", enemy_id)`, `("retreat", cover_point)`, `("hunt", pos)`, `("objective", pos)`, `("item", pos)`, `("hold", pos)` or `("vehicle", handle)`, adjusts the scores for the team's role discipline, score posture and stalemates, adds a small commitment bonus to the current goal and some noise, and picks the best. The chosen goal then drives movement (`move_to`, which asks the map's `Terrain.nav` for the next waypoint, jump or recorded human route), looking (`look_point`, which picks what the eyes should be on), human-like aiming (`Aim.step`, with sampled velocity reads, imperfect lead, Fitts-law flicks, overshoot, a pursuit lag and hand tremor), and, in a fight, `Bot.fight`, which handles strafing and juking, trigger discipline per weapon class, charge weapons, scopes, grenades and melee. Equipment and armor abilities are planned by a per-bot `equipment.Kit`, and in a vehicle the whole tick is replaced by `Bot.drive`, which handles seats, driving roles, attack runs, ramming, evasion and getting out.

Difficulty is split into four tiers named in code `novice`, `average`, `strong` and `top` (the panel's Easy, Normal, Heroic and Legendary) plus a fifth, Scaling. `brain/profiles.py` deliberately keeps the hands (reaction, tracking, aim error) close to a good human's on every tier, with Heroic and Legendary a little sharper, and puts most of the difficulty into knowledge and decisions: memory length, motion tracker use, teamwork (how often a bot follows the director's orders and takes part in focus fire and callouts), and the craft traits (`jump`, `strafe`, `juke`, `routes`, `map_iq`, `tactics`, `aware`). Easy is written to play for itself: it ignores the team plan, never calls out, knows no weapon spawns, uses no equipment except sprint, and runs straight at the objective. On top of the tier, one of seven personalities (rusher, camper, flanker, objector, spammer, grudger, sniper) changes what the bot prefers, never how well it aims. Every value is jittered by plus or minus 10% per bot. Scaling (`brain/scaling.py`) uses Legendary's behaviour and sets the hand values from a single skill rating that is recomputed after each game from the person's kill/death ratio.

Above the bots, one `Director` per team acts as the team's voice and coach. Bot reports (sightings, deaths, cracked shields, flag events from the announcer) are posted to a per-team `callouts.VoiceChannel`, which models one speaker at a time, speech onset and syllable timing by tier, urgent calls cutting in, duplicates merged and stale calls dropped; each teammate only "hears" a call after his own listening delay. Every 2 s `Director.assign_roles` hands out orders (`bot.Order`: a role such as runner, escort, defender, hunter, mid, screen, free, drive, ride, ferry, plus a point, a target and optional waypoints) from mode-specific slot lists, matched to bots by a cost of distance, role inertia and personality fit. The team's score posture (`brain/match.py`) runs from 0 (hide and hold) to 1 (all in), driven by the score against the variant's limit, the clock, how many players each side has alive, and the leader's scoring pace; the director pushes it to each bot, where it changes how cracked counts as cracked, whether to avoid fights, and how hard to hunt. The director also runs team plays: blitzes when desperate, CTF attack waves, power weapon fetches, backup calls in hold modes, and vehicle crewing, ferrying and rider calls.

What comes back out of a tick is one `core.Action`: `forward` and `strafe` (-1..1, relative to the sent view), `yaw` and `pitch` (absolute view angles, rate-limited by `Bot.turn_cap` to the profile's turn speed), the buttons `fire`, `jump`, `crouch`, `grenade`, `melee`, `action` (use/pick up/enter), `reload`, `equipment` and `ability` (an ability's press and its held bit), `sprint` (Halo 4), `fire2` and `cycle` (a vehicle's second weapon or boost, and the weapon cycle), plus `weapon` (inventory slot to switch to, -1 keep), `zoom` (0-2), `seat` and `turret` (which vehicle seat to enter) and `vertical` (a hovering aircraft's climb input). `tools/live_bots.py` `buttons()` packs these into bits (weapon slot in bits 8-10, zoom 12-13, seat 14-17, turret 18, vertical 19-20) for `botctl.act(m, slot, forward, strafe, yaw, pitch, buttons)`. Alongside the Action, a bot leaves diagnostic state the runner writes to the match trace: `goal`, `fx` (fight facts), `att` (what it looks at and why), `notes` (what overrode the plan this tick), `last_scores`/`last_flags` (what it weighed), and `reports` (events for its director, drained each tick).

| File | Role |
|---|---|
| `__init__.py` | Empty package marker. |
| `core.py` | Shared types: `Vec`, `PlayerState`, `FlagState`, `Snapshot`, `Action`, angle and eye-height helpers. |
| `bot.py` | One bot: `Perception`, `Aim`, and `Bot` (decisions, fighting, weapons, movement, looking, objectives, vehicles, guards, learning). |
| `director.py` | One per team: callouts, role assignment, score posture, team plays (blitz, wave, power runs, backup, vehicles). |
| `callouts.py` | Callout zones (`ZoneMap`) and the team voice channel (`VoiceChannel`, `Call`, timing tables). |
| `match.py` | Score posture from score, limit, clock and numbers; tempo push; One Flag posture. |
| `scaling.py` | Scaling difficulty: skill rating from the person's K/D, the hand settings it implies, panel files. |
| `profiles.py` | Tier tables, craft traits, personalities, `Profile` and `make_profile`. |
| `names.py` | Generates gamertag-style bot names. |
| `loadouts.py` | Learns what each loadout slot gives and picks a slot per bot (favourite gun or a fix for how it keeps dying). |
| `equipment.py` | `Kit`: equipment, armor abilities and powerups, own use and counters to the enemy's. |
| `vehicles.py` | Vehicle tables (kinds, seats, roles, target scoring, flight clearance) and helpers. |
| `tracefmt.py` | Trace line formats shared by the live runner and the simulator; crosshair and formation helpers. |
| `sim.py` | Test simulator only: offline match loop with crude movement and damage. |
| `sim_modes.py` | Test simulator only: objective-mode rules for the simulator. |
| `simgear.py` | Test simulator only: equipment and ability effects for the simulator. |

### `brain/__init__.py`

An empty file (0 lines). It only makes `brain` a package so modules import each other relatively (`from .core import ...`) and tools import them as `brain.bot`, `brain.director` and so on.

### `brain/core.py`

The shared vocabulary of the brain: what the game hands the brain each tick and what the brain hands back. Nothing here has behaviour beyond small geometry helpers.

- `TICK = 1/30`: the simulation step (Halo CE's 30 ticks a second); the simulator steps by it and many rates are expressed per tick.
- `Vec` (frozen dataclass `x, y, z`): `+`, `-`, scalar `*`, `length()`, `flat()` (horizontal length), `norm()`. Positions are in world units (u); comments throughout treat 1 u as about 10 ft.
- `dist(a, b)`, `angles_to(src, dst)` (yaw and pitch in radians), `wrap(a)` (angle to -pi..pi).
- `eye(p)`: where a player's shots come from. Positions are at the feet; the eye is 0.62 u up standing and 0.35 u crouched. `CROUCH_HEAD, CROUCH_CHEST = 0.38, 0.22` are the aim heights used on a crouched target.
- `PlayerState`: one player as read from the game: `id`, `team`, `name`, `pos`, `vel`, `yaw`, `pitch`, `alive`, `shield` and `health` (0..1; an overshield reads above 1), `weapon`, `weapons` (inventory in slot order), `ammo` and `mag` per inventory entry (-1 unknown), `vehicle` (handle or -1), `gunner_seat`, `turret` (name of the gun ridden, see `vehicles.TURRETS`), `has_flag` (carrying any objective), `camo_until`, `crouching`, `is_bot`, `equipment`, `ability_on`, `decoy` (a hologram, only set by the simulator) and `tracker` (whether this match shows enemies on the motion tracker).
- `FlagState`: `team`, `home`, `pos`, `state` (`home`, `carried`, `dropped`), `carrier`.
- `Snapshot`: the whole world for one tick: `time`, `players`, `flags` (team to `FlagState`, CTF only), `score`, `mode` (`slayer`, `ctf`, `king`, `oddball`, `invasion`, `territories`, `assault`, `stockpile`, `headhunter`, `infection`, `vip`, `firefight`, `juggernaut`...), `score_limit` and `time_left` (0/None when unknown), `vehicles` (list of dicts with at least `handle`, `kind`, `pos`, `occupied`; the live reader adds facing, riders, team, turrets and more), `honks`, `ground_weapons` (`[(name, Vec)]`), King's `hill`/`hill_r`, Oddball's `ball`/`ball_carrier`, `deployed` (domes, fields, mines, sentries), `grenades` (simulator only), `shieldless` (no-shield variants), the Invasion fields (`inv_phase`, `inv_attackers`, `inv_zones`, `inv_zone_r`, `inv_core`, `inv_core_carrier`, `inv_armed`, `inv_delivery`, `inv_phase_t`), the generic objective fields from `brain/modes.py` (`obj_zones`, `obj_items`, `obj_goals`), `infected` and `vips`. `snap.player(pid)` looks a player up by id.
- `Action`: what one bot does this tick (fields listed in the overview above). Defaults are "do nothing": zero sticks, no buttons, `weapon=-1`, `seat=-1`.

### `brain/bot.py`

The largest module by far (about 5,300 lines). It contains three classes, `Perception`, `Aim` and `Bot`, and a large block of weapon and behaviour tables at the top. Imports: `core`, `equipment` (`Kit`, `game_of`), `profiles`, `terrain` (route flag constants and drop/rise limits), `vehicles`, and lazily `maps.terrain` for the map's `Terrain` object (`Bot.T()`).

#### Module tables and helpers

- Vision: `FOV_HALF` (35 degrees), `PERIPHERAL_HALF` (55 degrees: noticed later), `SIGHT_RANGE` 80 u, `RADAR_RANGE` 25 u, `HEAR_RANGE` 30 u.
- `WEAPON_RANGE`: per weapon, the `(lo, hi)` band it wins at. Past `hi` the bot closes in, under `lo` it backs off (and switches if it can). Covers CE, Halo 2, 3, Reach and 4 weapon names.
- `BAND_EDGES` (4, 10, 20 u: Short, Medium, Long, Extreme), `BAND_WEIGHT` (how often each band is fought), `BANDS` (each gun's proficiency 0..1 per band) and `BANDS_GAME` (per-game overrides, e.g. Reach's and Halo 4's magnum). `band(d)`, `proficiency(w, d, game)` and `loadout_value(guns, rank, game)` turn these into a value for a set of guns (each band's best gun weighted, power weapons counted at half in their bands plus a bonus for rank above 3.5). `loadout_value` drives pickups and swaps.
- `WEAPON_RANK` and `RANK_GAME`: how much a player wants each gun in hand, per game (`Bot.rank`).
- Ballistics and fire: `PROJECTILE_SPEED` (lead time; hitscan-like guns default to 360 u/s), `SPLASH` (aimed at the feet), `PRECISION` (head-shot guns), `AUTO`, `BEAM`, `FIRE_GAP` (paced cadence floor), `FIRE_FAST` (Short band spam cadence), `BLAST` (own-blast radius of explosives), `CHARGE` (held-charge weapons, "release" or "auto" kind and hold time), `PL_LOCK_S` (2.2 s: how long the plasma launcher's reticle stays on a vehicle before the bombs are let go), `LUNGE`/`LUNGE_GAME`/`LUNGE_GAP` (sword and hammer reach and press rhythm), `LUNGE_ANGLE`/`LUNGE_BODY` (the red reticle's autoaim cone from the weapon tags: sword 2.25 u and 6 degrees, hammer 1.35 u and 10 degrees; Halo 3's sword 1.8 u and Halo 2's 2.2 u per game), `MELEE_TRIGGER` (Reach, Halo 4 and H2A, where a sword or hammer attacks through the melee action, not the trigger), `SWORD_OPEN`, `CLASH_MELEE` (the quick melee after a sword clash, never on Easy), `SHOTGUN_SLACK`, `OUT_OF_REACH`, `CQ` (close-quarters guns), `SCOPED`, `ZOOM_FROM`, `ZOOM_FAR`, `SNIPERS`, `LOCK_GAMES` (rocket lock-on), `ANTI_VEHICLE`, `VEHICLE_KILLERS`, `EMP_GUNS`/`EMP_GAMES`. `reach(w, game)` is how far a gun's shots do anything (lunge reach, shotgun band plus slack, else the top of its band).
- `HEAD_AIM`: per tier, the share of targets a precision gun aims at the head (Easy 0.20, Normal 0.5, Heroic 0.9, Legendary 0.97).
- Fight timing: `COMMIT_S`/`COMMIT_WEAK_S` (how long a fight survives losing sight of the target, longer when his shield is down), `TARGET_HOLD` (1 s before a new target in view may take over), `HUNT_KEEP`, `TREMOR`, `MELEE_R` (1.25 u), `CLOSE` and `SHORT_BAND`, `STRAFE_JUMP`, `STRAFE_PAUSE`, `HOP_RATE`, `IDLE_JUMP`, `JUMP_SHOT`, `PLANT` (share of fights where it plants its feet for long shots), `OBJ_NADE` and `NADE_RATE` (grenade rates), `NADE_CLEAR`/`NADE_FUSE` (keep clear of its own grenade).
- Role and objective distances: `DEFEND_R`, `ESCORT_R`, `DEFEND_HOLD`, `CLOSE_FIGHT_R`, `POWER_NEAR`, `REGROUP_MATE`, `HUNT_R`, `ESCORT_TRAIL`, `RUN_DETOUR`, `PRESS_COVER_R`, `STAGE_*` (a CTF runner waiting for company and a clear base), `GRAB_R`/`GRAB_SCORE`/`GRAB_NEEDS_COMPANY`/`GRAB_MATE_R`, `SCREEN_R`, `STALE_S`. Several booleans (`STAGE_NEED_CLEAR`, `KING_TAKE_IN`, `ONE_FLAG_PRESS`) switch between the current play and an older one for A/B comparisons.
- Vehicle constants: `VEHICLE_TRIP` (35 u: a farther goal makes a nearby free vehicle worth taking), `GETAWAY_PARK_R`, `RIDE_OUT_R`, `CALLED_WAIT_R`, the Banshee attack-run constants `PASS_*`, `CANNON_R`, `FIRE2_*`, `FUELROD_*`, `RAM_ERR` (heading error of a ram by tier), `BOOST_*`, `TRAVEL_BOOST_*`, `CHAINGUN_HEAT`, `FLEE_*`, `BOARD_*`, `TANK_FETCH_R`, `AIR_HIGH`/`AIR_LOW`, `AIR_LOOK_MAX`, `AIR_SIDES`, `AIR_GUN_R` (1.5 u: an aircraft's guns fire with its nose this near his middle), `AIR_JINK`/`AIR_JINK_S` (the swerve when shot at on a run), `AIR_PULL_S`/`AIR_RUN_FLOOR` (an attack run's ground check along the nose), `AIR_CEIL` (off a run, floors up to this far over the craft still count as ones to climb over), `GRAVITY`.
- Small helpers: `crouched(p)`, `aims_at(e, me, within)` (is player e's view on my chest), `vpos(v)` (a vehicle's position as a `Vec`).
- Data classes: `Belief(pos, vel, t, seen, source, weak)` and `Order(role, point, target, via)`.

#### Perception

`Perception(prof, rng)` holds what one bot knows about enemies. Its state: `beliefs` (keyed by enemy id, or by tuples such as `("callout", zone)`, `("static", id)` or `("fake", ...)`), `pending` (enemy id to the time recognition completes), `recognized`, `lost_at`, `dropped`, `last_seen` (eyes only), `clear_at` (last time a clear line ran to him, used by `Bot.line_clear`), `mags` (to detect gunfire), plus attacker fields set by `hurt_by`.

- `react_time(peripheral, d)`: log-normal around the profile's `reaction`; Easy reacts at a human's base speed to a man within 3 u; peripheral sightings take 1.6 times longer.
- `fired(e)`: true when an enemy's magazine dropped with the same gun in hand since the last look (the live readers report every player's magazine).
- `hurt_by(now, me, snap, los)`: detects a drop in our shield plus health and attributes it. The attacker is the enemy aiming within 0.25 rad of us; failing that, the one aiming nearest within 0.7 rad and 35 u ("sloppy", found slower); failing that, the nearest enemy who can see us. It records `losses` (damage over the last 2 s, used to judge whether cover is reachable in time), `hurt_at`, `attacker_id`/`attacker_t`, `attacker_notice` (when the bot will actually know who it is, a reaction time later), and `attacker_sure` for a confident first hit. It also writes a `hit` belief at the attacker's position if he is not currently seen.
- `update(now, me, snap, los, callouts)`: per enemy, decides `in_view` (inside the peripheral cone and sight range, or within 2.5 u anywhere, and not blinded by a flare) and `visible` (in view with line of sight, or the man who just shot us confidently). Active camo hides a man past 4 u 90% of the time. A visible man becomes recognized after his pending reaction time (much quicker if he was just lost behind cover); recognized men refresh an `eyes` belief each tick. A man out of view keeps recognition for 1.2 s, then loses it but stays in memory. The motion tracker adds `radar` beliefs for moving, uncrouched enemies within 25 u with chance `radar * 0.15` per tick (when the match shows enemies on the tracker and the radar is not jammed). Gunfire within 30 u adds a jittered `heard` belief with chance `aware`. Teammates' callouts become `("callout", zone)` beliefs at the zone's spoken position once this bot has understood them (`c.avail`); Easy does not listen. Beliefs older than `memory` are dropped, as are beliefs of players no longer present. Returns the newly recognized enemies, which `Bot.plan` turns into `("seen", ...)` and `("flag_carrier", ...)` reports for the director.
- `visible_enemies()`: recognized enemies currently seen.

#### Aim

`Aim(prof, rng)` turns a target into a view angle the way a human hand moves.

- `step(now, dt, me, target_id, tpos, tvel, aim_head, gun, origin, crouched)`: the hand follows the target's current position every tick, but its read of the target's velocity, the lead factor and the aim error are re-sampled only every `track` seconds (a stale velocity read is what makes jukes work). The aim point is the target position plus estimated velocity times (flight time plus 0.05 s) times the lead factor, at the feet for splash weapons, else head (0.62 u) or chest (0.35 u), or the crouched heights. The shot origin includes our own motion. The error spread shrinks as `focus` builds over 1.5 s on one target. A large change of aim (over 0.35 rad) starts a flick: a ballistic move whose duration follows Fitts' law, scaled by the profile's `flick` factor and capped by its turn speed, with an occasional overshoot of 8-18% (`overshoot` chance), landing where the target will be by then. Otherwise smooth pursuit closes the gap with a time constant of `lag` seconds plus a small Gaussian tremor (`TREMOR`, scaled by Scaling's `tremor_k`). Without a target (looking around) it turns at walking-look rates, with a quicker turn allowed for a new heading behind (`quick_ok`) and a fast spin (`whip`) toward a shooter out of view. `gun` and `origin` let a vehicle gunner aim with the turret's ballistics and mount height.
- `on_target(me, tpos, yaw, pitch, slack)`: whether the bot believes its crosshair is on the man: within a Spartan's width (0.12 u each side, 0.22 u up or down) at that range, plus the hand's steady trail behind a moving aim point, times `slack` for close quarters. This gates the trigger in `Bot.fight`.
- `landing(now, early, target_id)`: in the last `early` share of a flick onto this target, used by the looser trigger below Legendary.

#### The tick: `think`, `plan`, `turn_cap`

- `think(now, dt, snap, los, nav, callouts, items)` calls `plan` and then `turn_cap`. `los` is the terrain's line-of-sight function, `nav` its path query, `callouts` the director's heard calls and `items` the team's item respawn timers.
- `turn_cap(me, act, dt)`: limits the view change to `profile.turn * dt` and, on foot, rotates the stick so the walk still goes where it was planned under the view it actually gets.
- `plan(...)` is the per-tick body. In order it: resets per-tick diagnostics (`notes`, `att`, `fx`, `nav_cmd`, `shot_now`); records `last_pos`/`last_weapon` (for `loadouts.record_death`); notices a teleport (`came_through`); computes `grab_point` (a loose objective to take); runs `kit.perceive` and applies flare blindness and radar jamming to perception; removes beliefs about players now on our side (Juggernaut, Infection); runs `per.update` and queues reports; re-decides when `next_decide` is due (`decide` interval times 0.8-1.3); tracks headway toward place goals. Then, by goal: in a vehicle it calls `drive`, `air_guard` and `fire_gate` and returns. On foot, a `vehicle` goal walks to the right door (`seat_point`), taps Use and, in Reach, asks for a seat index (`vehicles.reach_seat`); a `board` goal does the same at an enemy vehicle's driver seat and gives up after `BOARD_GIVE_UP`; `fight` calls `fight`; `retreat` fights the nearest visible threat while backing toward the cover point; any other goal walks there, with detours, loitering at posts (`loiter`, `post_loiter`, `zone_shuffle`), occasional hops and idle jumps, pitch wandering, the walking look cone, grenades into an objective or onto a lift landing, ball pickup and item pickup handling (`took_at`, `rearm_skip`, `item_wait`). After the goal it handles taking an enemy flag or loose objective it stands on (`take`), the flag carrier's melee, quiet periods after a pickup (no Use or weapon switch while the carry read catches up), then the equipment kit (`kit.act`), and the guards in a fixed order: `give_way`, `crouch_spots`, `own_grenade`, `obstacle_guard`, sprint steering, `unstuck`, `no_wall_jump`, `edge_guard`, `fire_gate`. Finally it chooses the weapon slot (`choose_weapon`) and, between fights, may reload (`reload_check`).

#### Decisions: `decide`

`decide(now, me, snap)` returns one goal tuple. It builds a `scores` dict; the main entries and their typical weights are:

| Goal | When | Weight |
|---|---|---|
| `fight, t` | an enemy in view (target from `pick_target`) | 1.5 + 0.4 aggression; runners minus 1.2 objective past 12 u; a VIP less past 8 u |
| `fight, t` (kept) | already fighting and the target unseen less than `COMMIT_S` (or `COMMIT_WEAK_S`) | at least 2.6 + 0.3 aggression |
| `hunt, pos` | an aware bot (Heroic/Legendary) with a radar dot or hit within 3.5 u in the last second | 2.7 + 0.5 aware |
| `retreat, cover` | cracked (threshold follows posture) and losing (outnumbered or he is healthier), cover reachable in time | 2.5 + 0.5 tactics + 0.3 caution |
| `retreat, cover` | power weapon in his band, none of ours, alone, Heroic and up | 2.0 (fight drops to 0.3) |
| `retreat, point` | `relocate_point` after a SWAT or sniper kill / `regroup_point` alone against two | 2.4 / 3.0 |
| `retreat, cover` | fight over, shield under half, recharge near | 1.6 + 0.6 tactics; held at 2.3 while recharging |
| `objective, pt` | a role with a point | 0.5 + 0.7 objective; runner at an unguarded stand +1.0; inside `GRAB_R` at least `GRAB_SCORE`; carrying 3.0; CTF hunter with our flag out or a blitz 1.3 + 0.6 teamwork |
| `hunt, pos` | the freshest unseen belief (sticky via `HUNT_KEEP`) | (0.3 + 0.6 aggression + weak bonus) x (0.4 + 1.2 posture) x caution; snipers x0.4 |
| `hunt, pos` | a fresh `hit` belief / the attacker out of view | 1.4 + 0.4 aggression / 2.7 + 0.5 tactics |
| `hold, spot` | campers with map knowledge and no objective role | 0.2 + 0.6 camping |
| `item, pos` | `best_item`, `rearm_point` (3.0 when dry), `upgrade_point`, the team's `fetch` | per helper |

"Avoid" mode applies when posture is 0.3 or lower, we are outnumbered in view, not just hit and the target is past 8 u: the fight drops to 0.3 and a retreat is added. After the base scores, `vehicle_mission` (the Grenadier's anti-vehicle job, and everyone's against a tank), `keep_role` (role discipline), `break_stalemates` (a fight with no damage either way for `STALE_S` past 6 u drops to a quarter), a rule that a man in sight within `CLOSE_FIGHT_R` is always fought, `board_check` (hijack an enemy ground vehicle within 6 u), and goal bans from `headway` (with `alt_post` offering a nearby substitute) all adjust the dict. The current goal gets +0.2 (commitment) and each score gets uniform noise up to 0.15 before the maximum is taken. Last, vehicle overrides: a `ride`, `board` or `drive` order sends the bot to the ordered vehicle unless a close fight or the Invasion core is at stake; a committed vehicle run is kept for `vehicle_until`; an `errand` vehicle is honoured; and a far goal (past `VEHICLE_TRIP`) may pick any usable vehicle by `vehicles.ride_score`, with chance 0.3 + 0.6 map_iq. The final scores and some facts (`post`, `seen`, `friends`, `avoid`, `cracked`, `recharge`, `hit`) are kept in `last_scores` and `last_flags` for the trace's think line.

Related methods:

- `threat(now, me, snap, k)`: the threat score of a visible enemy: base 100 for a power weapon in its band, 70 in band, 30 out of band; a distance multiplier (higher up close, more so for tactical bots); x1.15 with his shield down; x1.3 if aiming at us, less if aiming away (a free kill for tactical bots); a third-party bonus when he is shooting a teammate; +40 carrying the objective or a VIP; +60 x teamwork when a teammate is already shooting him (focus fire via the director's `team_focus`); a grudge bonus for our last killer; +45 for the Grenadier against a vehicle crew; +60 x tactics for whoever is shooting us now; times `kit.threat_mod` (armor lock, decoys, sprinters, jetpacks).
- `pick_target(now, me, snap, seen)`: the highest threat, but a new target must beat the current one by a margin of 1.25 + 0.75 x (1 - tactics), multiplied up by how much damage the current target has taken; a new target is held `TARGET_HOLD` s and a kill about to land (`finishing`) is kept, unless someone is at arm's length. `shot_by_other` lets Heroic and Legendary turn at once on a man hurting them when the man they fight is not aiming at them. `turn_ok` gates turning from a man in view to an unseen one.
- `keep_role(scores, me, snap, seen)`: role discipline, scaled by teamwork (Easy has none). For each role it defines a leash: an Invasion defender sent at the carrier or a territory (`HUNT_R`), a carry's screen (`SCREEN_R`), a defender's post (`DEFEND_R`, or the zone's own radius in Territories, Infection and King, a 10 u firm leash in CTF), a CTF hunter on our dropped or carried flag, an escort on its lead (`ESCORT_R`), Invasion attackers covering a territory (`PRESS_COVER_R`), a CTF runner on its line to the flag (`RUN_DETOUR`) and an Invasion runner to the core or bomb. Fights, hunts, items and holds outside the leash are multiplied by 1 - 0.7 teamwork (0.15 when urgent), with exemptions for the man shooting us, a man right here, a gun when dry, a gun on the way, a power weapon spawn nearby and the team's fetch or anti-vehicle mission. When the bot is away from its spot, an objective score of 1.2 + 0.6 teamwork brings it back. It also invokes `stage`, which makes a runner wait (in cover if there is some) for a teammate within `STAGE_MATE` and for a clear base before going in, with timeouts and a 30 s-left override.
- `urgent(me, snap)` (Invasion phase 3 defending the core) and `pressing(me, snap)` (Invasion attacking, and One Flag attacking) are static predicates used by `keep_role`, `decide` and the director.
- `live_point(me, snap)`: where an escort should stand right now (`ESCORT_TRAIL` behind or ahead of its lead, offset to one side by id parity, or the lead escort clearing 9 u into their base while the runner stages), or where our flag is for a CTF hunter.
- `objective_point(me)`: the order's point, or the next of its `via` waypoints not yet passed.

#### Combat: `fight` and weapon handling

`fight(now, dt, me, snap, tid, act, nav)` runs every tick of a fight against target `tid`:

1. At the start of a fight it rolls whether this fight is strafed (always above Easy), whether it plants its feet for long shots (`PLANT`), and whether it opens with a grenade (by the grenades trait and tactics).
2. Aim: `dry_fire_check` (learning), `aim_head` (head or chest, decided once per target, weapon and shield state by `HEAD_AIM` or Scaling's `head_aim`), the aim point (a tank's weak point via `weak_point` for vehicle killers), then `Aim.step`. `att` becomes `["aim", tid, x, y]`.
3. Movement: forward or back by the weapon's band; `push_in` closes on him with a close-range gun or when his shield is down; `keep_off` keeps out of a sword or hammer's reach; a CTF defender never leaves its post area; after losing sight a tactical bot chases by the nav toward where he went (a sniper holds its lane instead); a sword or hammer runs him down by the nav.
4. Strafing: `under_fire` (hit within 0.8 s) or, for Heroic and up, being in his sights triggers jukes by the `juke` trait: irregular side steps, occasional crouch-jukes and short pauses (`STRAFE_PAUSE`); otherwise ordinary strafe flips every 0.45-1 s. Strafe jumps by `STRAFE_JUMP`. Reach uses partial stick. Planting stops strafing for long shots.
5. Trigger: `seen_now` (seen in the last 0.25 s) and `seen_fire` (plus the looser trigger's follow-through from `profiles.LOOSE`, or Scaling's own), both requiring `line_clear`. `on` is `Aim.on_target` with slack up close, or the end of a flick under the loose trigger, with a point-blank rule within 1.6 u. `kit.can_shoot` vetoes shots into an armor lock, through a dome or at a known decoy. Dry guns melee. Explosives never fire inside their own blast or onto a teammate, except a timed "trade" when cornered with nothing else. Swords and hammers fire only within reach with him in front. Shotguns hold fire past reach; other guns hold fire far past reach except a short deterrent burst while being shot. Rockets in lock-on games (and the missile pod) hold the reticle 0.9 s on a vehicle first.
6. Fire cadence: charge weapons via `charge_fire` (release or auto kind; the plasma pistol's overcharge sets up the noob combo; against a man in a vehicle the plasma launcher is let go only after its reticle has stayed on him for `PL_LOCK_S`, so every bomb locks, and the clock restarts whenever the reticle comes off); automatics spray up close (and at any range for beams and Easy), burst at range; one-shot weapons press every `fire_gap(w, d)` (spam close, paced at Medium, slower at Long, one pace for Easy), with occasional jump shots. `zoom_level` sets the scope (rifles past Short band, snipers from 6 u and second zoom past 20 u, never right after a hit; Easy only zooms sniper-type guns).
7. Grenades: a flush grenade where he went behind cover (once per loss of sight, 4-16 u), the fight opener, the Grenadier's sticky at a vehicle, a steady pressure rate (`NADE_RATE`), and `kit.grenade_spot` counters (beside an armor lock, into a heal field, at a hardlight user's feet). Grenades respect `grenade_ready_at` cooldowns and never land by teammates.
8. Melee within `MELEE_R` on the same floor, one press per swing; Easy is slow to swing and avoids melee trades on a lower shield. A crouch at the kill by the crouchy trait.
9. `fx` records the fight's facts for the trace (`d`, `on`, `hold`, `unseen`, `chase`, `strafe`, `splash_hold`, `dry`, `charge`, `zoom`).

Weapon choice and ammunition:

- `choose_weapon(now, me, kind, arg, snap)`: returns an inventory slot or -1. Never while carrying an objective. It brings a carried flag or ball into hand; holds the gun a pickup should swap out (`gun_to_drop`); switches at once when the gun in hand is dry, when its magazine ran out mid-fight with another loaded (not Easy), or when inside its own blast; follows a plasma pistol bolt with a precision gun (noob combo). Otherwise, at most every 1.2-2 s, it scores each gun: rank, plus proficiency at the target's distance, plus bonuses for a lunge weapon before he is in reach, close-quarters guns up close, the plasma pistol against a full shield, anti-vehicle guns against a vehicle, minus own-blast penalties; between fights, band-weighted proficiency. It switches only for a gain of more than 1.0, and keeps the gun in hand when finishing a man it can reach. Easy ignores range bands.
- `reload_check`: reload between fights at 40% of the largest magazine seen, never with an enemy in view.
- `rank`, `gun_to_drop`, `drop_slot` (an empty gun first, else the one whose loss keeps the loadout worth most), `dry` (every gun empty).
- `rearm_point` (a loose loaded gun when dry or low), `upgrade_point` (a loose gun that raises `loadout_value` by `UPGRADE_GAIN`), `swap_rested` (no upgrades from spots it just swapped at), `best_item` (power weapons and powerups by map knowledge: a bot estimates respawns with an error that shrinks with `map_iq`; Easy only takes guns it sees within 2 u; powerup preferences by personality, role and posture; Halo 3 equipment never swapped down by `equipment.PICKUP_RANK`), `power_spawn`.
- `line_clear` and `fire_gate`: the final say on the trigger for any seat: no shot without an enemy in front of the aim and a clear line (terrain line of sight this tick and no vehicle in the way). A charge being held stays held.

Positioning helpers used by `decide` and `fight`: `cover_from` (the nearest LiDAR-painted cover spot within 10 u that blocks every threat's line), `away_from`, `relocate_point`, `regroup_point`, `keep_off`, `push_in`, `finishing`, `turn_ok`.

#### Movement and navigation

- `move_to(me, point, act, nav)`: the single entry point for walking somewhere. In order: an active gravity lift ride (`ride_lift`); an Elephant's bay (`way_in`, for Sandtrap's flags); a recorded human route in progress (`follow_route`, crouching and jumping where people did); special handling for the last steps onto an objective the nav has no floor for (straight in, then running jumps, then a people's jump onto the stand via `jump_onto`, then other sides of it); otherwise a `nav(...)` query with options `jump` (jump skill 0.5 or more), `human` (use people's links), `safe` (carriers avoid big drops) and `no_tele`. The nav result is a plain waypoint, a jump (an object with take-off `sx, sy` and, for a person's jump, run-up `rx, ry`), or a route (`path`). Jumps check `jump_blocked`, `exit_held` and `pad_held` first (no riding a lift, cannon, drop or teleporter into an enemy known at its exit: go round, or wait up to 6 s); a person's jump is run from his run-up spot at speed (a carrier lines up behind it first, `lineup_point`, and takes off a little nearer, `carrier_take_off`). It sets `wp`, `planned_jump`, `jump_land`, `exact_until` and `nav_cmd`, which the guards read.
- `steer(me, point, act, go, arrive)`: sets `forward`/`strafe` toward a point relative to the action's yaw.
- `detour` (once per goal, a trip over 15 u may go by a side zone, by route craft and style), `headway` (no progress for 6 s bans a goal for 30 s, never a carrier's run), `loiter`, `post_loiter` (a CTF defender moves between cover spots that see its stand), `zone_shuffle`, `jump_onto`, `alt_post`, `patrol_point`, `roam`.
- Lifts and launchers: `lift_near`, `lift_base`, `ride_lift`, `launches`, `arrival` (pre-aim the landing of an enemy on a launch), `came_through` and `tele_watching` (step off a teleporter exit and watch it when chased), `exit_held`, `exit_watched`, `exit_cover`, `held_wait`, `uncovered` (a carrier treats an exit with no teammate at it as held), `pad_held`.
- Guards applied every tick after the goal: `give_way` (bend around a player in the way, or queue), `redirect` and `blocked_way` (a wall or vehicle right ahead), `obstacle_guard`, `own_grenade`, `crouch_spots` (crouch where people crouched), `unstuck` (no progress while pushing: back off a body block, flip the strafe in a fight, else wiggle with a jump, and tell the terrain about the unmapped obstacle), `no_wall_jump`, `edge_guard` (never walk or jump off a deadly edge; in the air steer back over the last solid ground; planned jumps and trusted human routes pass) with `edge_other_way`, `fall_time`, `fall_steer`, `soft_landing`, `segment_ok`, `no_floor_at`, `judge_jump`.

#### Looking

`look_point(me, point, nav, post)` returns the point the eyes should be on when not aiming at a target, and sets `att` to say why. Priority: a carrier looks down its way; a watched teleporter exit; an enemy's launch landing; otherwise the freshest known threat, kept in mind for `0.5 + 4.5 x aware` seconds (eyes at least `EYES_KEEP`, hits at least `HIT_KEEP`, heard shots at most `HEARD_KEEP`), with a 1 s hold against flipping. A fresh hit, or the current attacker, wins and sets `aim.whip` for a fast spin. A threat in the open is looked at directly; one behind cover is pre-aimed where he would come into view (`man_appears`), or the way he would come if close. Riding a lift with nobody known, Heroic and up watch the cover at the exit. At a post it looks out along an open sightline toward the team's hot spot (`post_view`). Aware bots glance 60 degrees to each flank every few seconds when there is room to see. With nothing known it pre-aims the farthest visible point of its route (`route_lead`), else 8 u down its next waypoint at eye height (`ahead`). `walk_cone` keeps a deliberate look within 50 degrees of the walking direction, and `plan` slows walking that points more than 60 degrees off the view.

#### Objectives

- Taking things: `take(me, act, pos)` (Use held with the view on it), `loose_point` and `on_loose_objective` (the Invasion core or bomb, Assault's bomb, a Stockpile flag), `grab_ok` (at their flag the grab beats a new fight, unguarded or with company), `theft` (our flag or core is running: gun trips wait), `zone_at` (the size of the zone a post is in, for loitering inside it).
- Flag handling in `plan`: a bot on an enemy flag takes it whatever its goal; after a pickup it suppresses Use and weapon switches for 1.5 s because a switch drops the objective in some games.
- `set_order(order, sure)`: accepts a new role with probability `teamwork` (never for Easy, always for a honk with `sure`), resets waypoints on change. `lead(me, snap)` is who an escort escorts.
- `on_death(killer_id)`: remembers the killer (grudge), clears the order's waypoints so the director picks a fresh route, and resets perception and aim.

#### Vehicles

On foot, vehicle use is a goal: `decide` may choose `("vehicle", handle)` for long trips or by order, `board_check` adds `("board", handle)` for hijacks (Halo 2 on, Normal and up), and `vehicle_mission` sends bots after enemy vehicles with launchers. `board_check` takes the nearest enemy-driven ground vehicle (`BOARDABLE`) within `BOARD_TRY_R` (6 u) that is not running at the bot nose first faster than `BOARD_SPEED` (3 u/s) nor passing at twice that; a tank going at most half that speed whose driver looks more than `BOARD_BLIND` (90 degrees) away from the bot is stalked from `BOARD_STALK_R` (11 u). The board goal walks to the driver's seat point, or for a tank to a point `BOARD_FRONT` (2 u) ahead of its nose, and taps Use there. Once aboard an enemy's vehicle the bot stands still and melees, one press every `BOARD_MELEE_EVERY` (0.55 s), and after a second plants one grenade, except in Reach, where melee alone is used. Helpers: `seat_point` (driver's door front left, gun at the back, Falcon side doors), `dud_check`/`duds` (a vehicle bots stand beside without getting in for `DUD_S` is skipped by everyone for `DUD_FOR`), `vehicle_stalled`, `veh_banned`, `enemy_vehicle`, `anti_vehicle_gun`, `explosive_source`.

In a vehicle, `drive(now, dt, me, snap, act, nav)` takes over the whole tick. Its seat is inferred when it gets in from the riders already inside and the seat it asked for. A gunner or passenger aims and fires (`crew_target` and `vehicle_pick` choose the target with `vehicles.target_score`; the turret's own gun and mount height feed `Aim.step`), looks around when idle (`rider_look`), cools Reach's chaingun (`chaingun_heat`), and gets out once nobody drives. A driver: waits for called crew (`crew_coming`); evades the worst threat in view (`evade`: EMP guns close by, vehicle killers aimed at it, a tank barrel on it, enemy Banshees for transports, armor lock, boarders), after a reaction time and by its juke trait; in Halo 2 and 3 retreats toward teammates when its shield is down; runs its director job (`vjob`: ferry, getaway, pickup, taxi, escort, hunt, anti-vehicle, patrol); fights by the vehicle's `vehicles.STRATEGY` role (strafe, charge, artillery with a tank driver's camera height and mortar lob from `vehicles.driver_view`, circle so its gunner works, air attack runs via `air_pass`), rams light targets (`ram_ok`, with a heading error by tier from `RAM_ERR`), boosts into close men (`ram_boost`) and along open legs (`travel_boost`), cycles Reach's Banshee fuel rod (`fuel_rod`) and sends Reach's Banshee boost as the vertical input (`boost`). Pilots hold height over the floor, take off by kind (`vehicles.TAKE_OFF`) and are protected by `air_guard` (a short look-ahead probe at the craft's height that climbs or turns away from obstacles, a stall detector that backs off and remembers blocked spots, and floor clearance rules) with `air_open` and `air_terrain`. Getting out happens at the destination, when wedged after two reverse attempts (tanks doing a job try another way instead), or for a pilot only close to the ground; the exit press is held long enough for each game. Easy only drives trips and shoots what it meets in front of it.

#### Learning during a match

Several mechanisms let bots adapt to level data that is wrong or incomplete:

- `dry_fire_check`: counts shots fired while on target without the target taking damage; past `DRY_SHOTS` for the tier (40, 24, 16, 12 from Easy to Legendary; Scaling's own `dry_shots`) and `DRY_SECONDS`, it marks the line blocked in the shared terrain (`Terrain.learn_blocked`, saved per map), so every bot stops fighting through that surface.
- `unstuck`: reports obstacles the level data lacks (`Terrain.learn_stuck`) so paths learn to go around.
- `headway`, `judge_jump` (a jump short twice is avoided 60 s), `dud_check` (shared duds), `board_ban`, `vehicle_stalled`, `item_skip` and `rearm_skip` (spots that gave nothing): temporary per-bot or per-team bans.
- Loadout learning (in `loadouts.py`) and item timers (in the director) are the other learned state.

### `brain/director.py`

`Director(team, mapdata, bots, rng, log, legacy_comms, side, home_rule)` is created once per team (in `tools/live_bots.py` and in `sim.py`). `bots` maps player id to `Bot` for that team; `team` is the game's team and `side` the red/blue index used for map knowledge (home flag, holds, routes). It imports `Bot` and `Order` from `bot.py`, `Call`, `VoiceChannel`, `TIMING` and `LISTENER_BUSY` from `callouts.py`, `NEW_MODES` from `modes.py`, and the posture functions from `match.py`. The module docstring still describes CTF and Slayer roles as the main case; the current code covers every supported mode.

Main state: `zones` (the map's `ZoneMap`), `voice` (the team's `VoiceChannel`), `callouts` (heard calls still fresh, passed to every bot's `think`), `threat` and `threat_at` (a per-zone threat map: level up 1 per report, 3 per death, capped at 10, fading with time), `roles`, `posture`/`posture_state`, `item_up` (item index to the time it should be back), `defend_until`, `home_rule` (whether a capture needs our flag home), `plan` (stance and defender count), plus a match record (`events`, `match` tallies and samples, role changes) kept for reporting.

#### Reports and callouts

- `report(now, bot_id, kind, pos, count, enemy, busy, killer_weak, died_at)`: entry point for events. `bot_id` -1 is the game announcer or HUD. It names the zone, logs objective events, updates tallies and the threat map, starts a 15 s defend pull (`DEFEND_PULL_TIME`) when a teammate dies within 12 u of our flag (turning the report into an urgent `died_at_flag` if the killer is on the flag), uses the coarse area name when the speaker is fighting, drops everything from Easy bots (they never call out), and posts a `Call` to the voice channel. Returns the channel's verdict (`queued`, `merged`, `covered`, `dropped`, `silent`, `announced`).
- `text(c)`: callout wording in a big-team comms style: "Two Big Hill", "Three now, Mid", "Weak, Water", "One shot, Red port", "Carrier Red port!", "Dead, he's Sunny", "Need backup, Mid!", "Get in, Red base!", "Flag pulled!", "We scored!".
- `said_at(pos)`: where a callout puts the enemy for listeners: the zone's centre, adjusted to his floor.
- In `update`, calls whose key words are out get `pos_said` and a per-listener understanding time `avail[bot_id] = t_key + hear(tier) (+ LISTENER_BUSY if fighting)`, with Scaling's own `hear` value when set; they stay in `callouts` for 6 s. The live runner and the simulator call `report` for every bot report and for kills, deaths, shield breaks and flag events.

#### Per-tick update

`update(now, snap)` runs every tick:

1. Advances the voice channel and distributes heard calls (above).
2. `track_events` (kill feed, respawns, flag runs, match phase via `match_phase`: opening, objective crisis, endgame, mid-game).
3. Learns the variant: turns `home_rule` off if we score with our flag out; learns `score_unit` (points per kill, e.g. 10 in Halo 4 Infinity Slayer) as the gcd of score steps.
4. Counts the alive difference against the strongest other team (not in Firefight, Infection, Juggernaut), computes `match.posture`, applies `one_flag_posture` in One Flag, then `match.tempo` with the leader's scoring rate over the last 3 minutes.
5. Builds `team_focus` (how many of our bots fight each enemy) and the `hot_spot`, and pushes `team_focus`, `posture` and `hot_spot` onto each bot (Easy gets none of them and a neutral 0.5 posture).
6. Every 2 s: `assign_roles` and `power_runs`.
7. Every tick: `blitz_tick` and `wave_tick`.

#### Role assignment

`assign_roles(now, snap)`: excludes bots in a blitz; gives every Easy bot a straight run at the objective (`straight_objective`) or a free roam; asks `role_slots` for an ordered list of `(role, point, trait)`; makes our carrier a runner home (`carry_point`, by the safest lane from `pick_route(home=True)` in CTF); leaves our VIP free; then fills each slot with the cheapest free bot, cost = distance / 30 + 0.5 if the role changes - 0.8 x the slot's trait (aggression, camping, objective, teamwork). CTF runners get a lane from `pick_route` (Easy straight, better bots spread over lanes, the best take sneak routes and avoid the threat map); Invasion phase 2 pushers get flank lanes (`push_lanes`); escorts get their lead (the carrier, a person carrying, the VIP or the runner). Remaining bots become free. Then `backup_orders` and `vehicle_orders`.

`role_slots` dispatches by mode:

- Firefight: everyone escorts the nearest human.
- King: `king_take` (one more of us than the enemies seen on the hill, two at least) as defenders on the hill and the rest on `overlooks`; otherwise one scorer on the hill (at its near edge when hiding and holding) and the rest on overlooks.
- Invasion: `invasion_slots` (attackers mass on one territory with flank lanes in phase 2 and split with five or more; phase 3 runners for the core and escorts; defenders post at territories, hunt inside them, and guard the core and delivery point).
- Territories, Assault, Stockpile, Headhunter, Infection: `mode_slots`.
- Oddball: our carrier gets two escorts and overlooks; their carrier is hunted by all; a loose ball gets two runners and hunters.
- VIP: two escorts for ours, a hunter on theirs, then Slayer slots.
- Slayer and anything else: `slayer_slots`. By posture: 0.35 or lower holds a power position and its neighbour in pairs; 0.65 or higher sends two pairs at the fight from two sides; otherwise an anchor at a power position (chosen every 25-45 s weighted by its score and whether it sees the hot zone), a slayer and support at the fight (`hot_spot` or `likely_enemy`/`spawn_guess`), and floaters. `spread` gives each bot its own spot.
- CTF: the carry play (runner home plus up to three escorts and a screen when `CARRY_PLAY`), the standoff rule when both flags are out, hunters on our flag carrier with a cutoff ahead of him (`cutoff_point`), defenders at cover posts that see our stand (`defend_posts`; count by team size, enemy count, defend pull and lead), runners and escorts at their flag, split attacks over two lanes decided every 40-70 s (`SPLIT_CHANCE`), and pushers behind the runners. One Flag swaps attacker and defender logic per round.

#### Team plays

- `desperate`, `blitz_tick`, `blitz_team`, `blitz_target`, `blitz_holds`, `blitz_rally`, `blitz_prongs`, `prong_pair`, `blitz_role`, `inv_late`, `overtime`: when only an all-in push can save the game (CTF, Assault, Stockpile, King, Headhunter by posture; Invasion attackers in a phase's last minute or after a wave wipe), every non-Easy bot on foot rallies `BLITZ_RALLY_D` short of the objective, waits up to `BLITZ_GATHER_S` or until `BLITZ_READY` of the team is there, then all go in at once by two prongs for up to `BLITZ_GO_S`, with the urgency flag `Bot.blitz_until` that tightens `keep_role`; `BLITZ_COOL_S` of normal play follows.
- `wave_tick`: CTF's normal attack as a wave: attackers gather up to `WAVE_GATHER_S` at the rally, go in together for up to `WAVE_GO_S`, cool `WAVE_COOL_S`; defenders stay home.
- `power_runs` and `press_fetch_ok`: a power weapon lying loose (or a power spawn due back within `POWER_EARLY`) sends the nearest suitable bot within `POWER_RUN_R`, setting `Bot.fetch`; attackers on the clock only fetch weapons on their way.
- `backup_orders`: in Territories, King and Invasion a contested post makes a holder call "Need backup" and sends up to `BACKUP_MAX` nearby free bots there.
- Vehicles (`vehicle_orders` and the functions it calls): `crew_orders` (pick vehicles by role in `vehicles.ROLE_ORDER`, biased by `ROLE_FIRST` per mode, and send a driver), `honk_orders` (a teammate honking fills his gun and seats), `rider_calls` and `rider_ok` (drivers flag down teammates with long trips), `gunner_pickup` (drive to a teammate to fill an empty gun), `ferry_orders` and `ferry_seat` (pick up our carrier and run him home), `getaway_park` and `drivable_near` (a getaway ride parked near their stand), `vehicle_jobs` (every bot at a wheel gets a job: hunt their carrier, escort ours, taxi, anti-vehicle or patrol), `enemy_vehicles`.
- Knowledge helpers: `hot_spot` (where the enemy last was in the hottest zone), `likely_enemy`, `spawn_guess` (their likely spawn: near their living players, away from us), `positions`, `spread`, `overlooks`, `guard_spots`, `defend_posts`, `team_centre`, `capture_point`, `carry_point`, `is_one_flag`, `hill_contested`, `seen_near`, `sighting`, `belief_zone`, `objective_points`, `track_objective`, `item_taken` (start an item's timer; tallies which items the enemy takes). All of these use only what the team's bots believe, never true enemy positions.

### `brain/callouts.py`

Callout zones and the per-team voice channel.

Zones: `Zone` is a named polygon with a height band, side, priority, alternative names and an `area` flag for large areas; `contains(p)` is a point-in-polygon test, `edge_distance(p)` the distance to the outline. `ZoneMap(zones)` sorts by priority and computes centres; `ZoneMap.load(path)` reads `maps/<map>/callouts.json` (via `read_json`, which retries while a file is being rewritten). `zone(p)` returns the highest-priority zone containing the point, else the nearest outline (preferring zones whose height band fits); `name(p)`; `area_name(p)` returns only the coarse area, used when the speaker is fighting.

Timing: `TIMING` per tier gives `p_call` (chance to call a fresh sighting when not fighting), `decide` and `onset` (log-normal times to pick the message and start speaking), `urgent_start`, `rate` (syllables per second), `hear` (listener delay after the key words), `busy_skip` (chance a fighting speaker drops a non-urgent call), `dead` (chance and delay of a call on death) and `self_gap`. Further constants: `START_FLOOR`, `BUSY_EXTRA`, `LISTENER_BUSY`, `TURN_GAP`, `URGENT_RATE`, `RATE_CAP`, `DOUBLE_KEY`, `STALE` (per kind, how long a call may wait before it is dropped), `STALE_URGENT`, `MERGE_WINDOW`, `URGENT_REPEAT`, `ANNOUNCER`, `PRIORITY` (objective events are urgent, priority 0) and `URGENT`. `syllables(text)` and `key_part(text, zone)` time speech.

`Call` (dataclass) carries kind, zone, position, event time, speaker, tier, busy flag, count and enemy set, text, and the computed times `t_start`, `t_key`, `t_end`, `t_heard`, plus `avail` (listener id to understanding time).

`VoiceChannel(rng, legacy, text_of)`:

- `post(now, call)`: announcer calls (speaker -1) go straight out via `announce`. Otherwise it may drop a dead speaker's call, merge into a queued call on the same zone and kind, mark it covered if the same zone and kind was said within `MERGE_WINDOW` (or `URGENT_REPEAT`), unless the count rose (then it becomes an update such as "Three now"), drop it if the speaker is busy, or stay silent by `p_call`. Queued calls get a start time from decision, onset and busy delays.
- `update(now)`: returns calls whose key words have just been said; finishes the current speaker; drops stale queued calls; starts the next due call by priority and age, respecting the gap between speakers and each speaker's own gap. Urgent calls cut in on a non-urgent speaker, and a cut sighting returns to the queue.
- `_say` sets text (sometimes doubling "Carrier, carrier"), speaking rate and the key and end times; `talk_share(now)` measures the share of the last 20 s someone was talking. `legacy=True` is the original flat 0.5-2.5 s delay with no channel, kept for comparison (`sim.py --compare-comms`).

### `brain/match.py`

Score posture: how safe or bold a team plays, from 0 (hide) to 1 (all in), default 0.5. Nothing is a fixed kill count; everything is relative to the variant's own limit.

- `near_win_window(limit, mode, unit)`: how many points from the limit count as "one more push and it is over": a tenth of the limit, 1 to 5 kills (in points of `unit` per kill), and for timed modes (`TIME_SCORED`: Oddball, King) a tenth of the limit, at least 10 s. None when the limit is unknown.
- `Posture` (dataclass): `value`, `state` (why), `lead`, `ours`, `theirs`, `limit`, `window`.
- `by_score(score, team, limit, time_left, mode, unit)`: last minute ahead `hide_and_hold` 0.15; last minute behind `all_in` 0.9; enemy within the window `enemy_near_win` 0.2; we within it `we_near_win` 0.35; then by lead as a share of the limit (or of 50 with no limit): `far_ahead` 0.3, `ahead` 0.4, `behind` 0.6, `far_behind` 0.7 (0.9 in the last 3 minutes), else `even` 0.5.
- `posture(score, team, limit, time_left, mode, unit, up)`: `by_score`, then numbers from the kill feed: two or more alive up pushes to at least 0.7, two or more down holds at most 0.3, except in the near-win, hide-and-hold and all-in states.
- `one_flag_posture(p, defending, time_left)`: One Flag's limit of 1 would make both teams read "enemy near win"; the side decides instead (defenders careful, attackers behind, all in the last minute).
- `tempo(p, leader_rate, time_left)`: if the leader's pace will not reach the limit before time runs out, both teams raise the tempo to at least 0.7 (`tempo_push`, or `close_out` for a leader near the win), except a team the enemy is about to beat, an all-in team, or a leader protecting a lead whose limit is out of reach.
- `selftest()` (run as `python -m brain.match`) asserts the rules on worked examples.

The director calls `posture`, `one_flag_posture` and `tempo` every tick and gives each bot `posture.value`.

### `brain/scaling.py`

Scaling difficulty: one skill rating (1.0 = 100% = a skilled human player's baseline, starting at 100%) recomputed after each Scaling game. The behaviour is always Legendary's (tier `top` tables for teamwork, map knowledge, routes, tactics, radar); the rating scales the hands and, past Legendary's level, the game sense.

- `PARAMS`: the scaled settings with their panel labels and 100% values: reaction, aim error and tremor, aim speed (`lag`), flick, tracking, decision speed, flick overshoot, turn speed, headshots (`head_aim`), leading (`lead`), trigger looseness (`loose_follow`, `loose_early`), ramming error (`ram_err`), memory, callout hearing (`hear`) and shots before moving on (`dry_shots`).
- `values(rating, weights)`: times and errors are divided by the rating (with floors of one 30 Hz tick for reaction, tracking and decisions); turn speed is multiplied up to `TURN_MAX` (2000 deg/s); the missed shares of headshots and leading shrink with the rating (`MISSES`); game sense (`SENSE`) stays at Legendary's until `LEGEND` (150%) and then grows by rating / LEGEND. A custom profile's weights multiply the rating per setting. `level` clamps to `MAX` (1800%).
- `profile(rating, personality, rng, weights)`: builds a `Profile` with tier `top`, the scaled values jittered 10%, and the settings the brain otherwise reads from tier tables (`EXTRA`: `head_aim`, `loose_follow`, `loose_early`, `ram_err`, `tremor_k`, `hear`, `dry_shots`) placed in `profile.extra`. `bot.py` (aim tremor, head aim, trigger looseness, ram error, dry-fire limit) and `director.py` (callout hearing) read `extra` first and fall back to their tier tables when it is None.
- Rating update: `read_report` parses MCC's carnage report XML; `person_kd` returns the single person's kills and deaths if the game counts (completed, 2+ minutes, 3+ kills plus deaths; bots are recognised by the Xbox ID prefix `BOT_ID`); `skill_played` reads the rating a match was played at from the first lines of its trace; `next_skill(games, n)` is the weighted geometric mean (newest weighted most) of rating x K/D over the last n games, capped at `MAX`; `update(logs, n, cfg)` applies every new `trace_*.carnage.xml`, saves `logs/scaling.json` (`load`, `save` with atomic replace) and returns the state with `play`, the rating to use (the locked one if locked).
- Panel integration: `settings(path)` reads `native/bin/scaling.ini` (lock, locked rating, custom profiles and which one is in use); `games_window(ini)` reads `scale_games=` from `botcore.ini` (1-20, default 5); `view_lines` and `write_view` write `logs/scaling_view.txt`, the BOTS panel's hover box with each setting's percentage and value for every N; `summary` and `pct` format a one-line description.

`tools/live_bots.py` calls `scaling.update(...)` at start-up to get the rating and `scaling.profile(...)` for bots whose tier is `scaling`.

### `brain/profiles.py`

Skill tiers and personalities. The module docstring says the starting values come from the research documents and should be tuned against telemetry; the current tables have since been tuned (the comments beside each table record why).

- `HANDS`: a good human's hands for every tier: `reaction` 0.22 s, `track` 0.10 s (velocity re-read interval), `lead` 0.8, `decide` 0.10 s, `overshoot` 0.30, `aim_err` 0.009 rad, `lag` 0.09 s, `flick` 1.0.
- `REACTION`: reaction multipliers per tier (Easy 1.25 down to Legendary 0.70). `SHARP`: quicker hands for Heroic and Legendary (lag, flick, aim error, tracking).
- `LOOSE_AIM` and `LOOSE`: a looser trigger below Legendary: `follow` (seconds the trigger stays on where the man went after losing sight) and `early` (the end share of a flick already firing). Can be switched off by a test override in `tools/live_bots.py`.
- `TURN`: maximum view turn rate per tier (270, 435, 650, 1000 deg/s), not jittered.
- `TIERS`: per tier, `HANDS` with the tier's reaction and sharpening, plus `memory` (4, 6, 8, 10 s), `radar` (0, 0.5, 0.8, 1.0) and `teamwork` (0, 0.55, 0.8, 0.95).
- `CRAFT`: per tier `jump`, `strafe`, `juke`, `routes`, `map_iq`, `tactics`, `aware`, each 0..1 (Easy: jump, juke, routes, map_iq, tactics and aware all 0, strafe 0.9; Legendary all 1.0).
- `PERSONALITIES`: seven trait sets over `aggression`, `caution`, `camping`, `jumpy`, `crouchy`, `grenades`, `grudge`, `objective`. "spammer" is the Grenadier (anti-vehicle missions, grenade-heavy).
- `Profile` (dataclass): all of the above as flat fields plus `turn` and `extra` (Scaling's overrides).
- `make_profile(tier, personality, rng)`: merges the tables and jitters each value by 0.9-1.1.

The director and bot read tiers as behaviour switches throughout: `teamwork <= 0` means Easy for team play, `tactics` thresholds (0.15, 0.5, 0.75, 0.9) gate tactical rules, and `tier == "novice"` is checked directly in a few places.

### `brain/names.py`

`make_names(n, rng, taken)` generates unique gamertag-style names of at most 15 characters (the game's name field) in five styles: two words ("ShadowWolf"), a word and a number ("Reaper117"), "xX...Xx", a Halo-flavoured word with a suffix ("KilltacularTV"), and a prefix with a word ("LilJackal"), avoiding names in `taken` case-insensitively. The `FIRST`, `SECOND` and `WORDS` lists supply the parts. Running the module checks 30 unique names.

### `brain/loadouts.py`

Loadout choice for games with loadouts (Reach, Halo 4, H2A). The game hands out a player's requested slot at the next spawn; botcore writes the request. What a slot holds depends on the gametype, so each team learns it from its own spawns.

- `Palette`: per team, `seen` (slot to the first two guns a bot held right after spawning with it), `ability` (slot to its armor ability) and `off` (the game refused requests). `learn(slot, weapons, ability)`; `choice()` is false when requests are off or three or more learned slots give the same kit (no real choice).
- `record_death(bot, now, snap)`: appends how a life ended (time, slot, own gun, the likely killer's gun, whether he was in a vehicle, distance) to `bot.deaths` (last 8). The killer is the recent attacker (2 s) or the fight target.
- `death_kind(d)`: `vehicle`, `outranged` (killed from 8 u or more by a gun that reaches further), `close` (killed under 4 u by a gun better up close), or None (a fair fight).
- `fit(guns, kind, ability)`: how well a slot answers a problem, with `ABILITY_FIT` bonuses (armor lock against vehicles, hologram or camo against snipers, evade, thruster or armor lock up close); unseen slots score 0.5 so bots try them.
- `LIKED`, `liked_guns(name)` (a bot's favourite primaries, drawn once from its name so they are stable across matches) and `liked_slot(bot, palette, current, carried)` (the slot with its favourite gun, looking in unseen slots first; ties go to the slot whose ability the team carries least).
- `want_slot(bot, palette, current, now, carried)`: returns `(slot, problem, deaths)` or None. A problem fix (`_problem_slot`) wins and fixes the bot's choice from then on: it needs 1, 2 or 3 deaths of one kind (by tactics; Easy never changes) since the last switch, and picks the best-fitting slot, penalising slots that already died that way. Otherwise the liked slot.

It imports `ANTI_VEHICLE`, `AUTO` and `WEAPON_RANGE` from `bot.py`. `tools/live_bots.py` calls `liked_guns` when a bot is created, `record_death` on death and `want_slot` while it waits to respawn.

### `brain/equipment.py`

Equipment, armor abilities and powerups: when a bot uses its own and how it works around the enemy's. Each `Bot` owns a `Kit(profile, game)`. `bot.py` calls `kit.perceive()` early each tick, `kit.act()` after the goal's movement and aim are set, and `kit.threat_mod`, `kit.can_shoot`, `kit.fight_move` and `kit.grenade_spot` inside a fight.

Tables and helpers:

- `TAGS`: ability timings (activation mode, energy cost, drain, recharge, warmup) per game from `brain/equipment_tags.json`, extracted from the editing kits.
- `ITEM`: per kind, where it deploys (`feet`, `throw`, `front`, `self`, `aim`, `dash`), how long it lasts and its radius; covers Halo 3 equipment (bubble shield, power drain, regenerator, trip mine, deployable cover, radar jammer, flare, grav lift) and Reach and Halo 4 abilities (armor lock, sprint, jetpack, active camo, hologram, drop shield, evade, thruster, Promethean vision, hardlight shield, regeneration field, autosentry). Category sets: `HEALS`, `DOMES`, `TEAM_ITEMS`, `DEFENSIVE`, `EXPLOSIVE_AIMED`, `SNIPERS`, `LUNGERS`, `CQB`, `PLACED`, `HELD`. Distances and times: `THRUST_REACH`, `NADE_BLAST`, `NADE_FUSE_SEEN`, `OS_PUSH`, `REGEN_REACH`, `THROW_RANGE`, `JET_RISE`, `JET_BRAKE`, `SAFE_LAND`, `JET_FLY`, `RUN_SPEED`, `LONG_WALK`. `PICKUP_RANK` (Halo 3 equipment priority) and `NAMES` (map tag names to kinds).
- `USE`, `use_of(game, kind)` and `hold_bit(game, kind)`: how each kind takes its button per game: `tap` (one tick, toggles), `press` (held a set time, extended past the tag's warmup for hold-mode kinds) or `hold` (held while in use). In Reach a hold-mode ability also needs its held bit, sent as `Action.ability`.
- `brake_speed`, `jet_hold`: jetpack fall braking and climb timing. `game_of(map_name)`: the game from the map folder prefix (`h2a_`, `h2_`, `h3_`, `odst_`, `reach_`, `h4_`, else CE). `level(prof)`: the tier ladder by tactics: 0 obvious cues only, 1 use-now triggers, 2 plus hold and bait rules, 3 plus sneaky uses.
- `Energy(game, kind)`: an ability's charge from its tag (`ready()`, `tick(now, dt, on)`). `facing_me(e, me, tol)`.

`Kit` methods:

- `perceive(bot, now, me, snap)`: tracks our own kind and energy; reads enemy deployables (a flare in view blinds, shorter for strong players; a radar jammer jams the tracker and plants a fake radar belief for novices); notices camo users jamming nearby radar (strong players get a `static` belief near him); tracks enemies standing still and running straight (hologram tells); resolves suspected decoys shot once (vanished: a hologram; still there: real for 10 s); with Promethean vision active, adds `pv` beliefs through walls and flags decoys.
- `posture(now, me, post)`: aggressive (0.9) for `OS_PUSH` s after our own overshield comes on.
- `decoy_suspect`, `state(now, e, snap)` (locked, hardlight, sprinting, flying, overshield, inside a dome or heal field, decoy).
- Counters in fights: `threat_mod` (an armor-locked enemy is a timer not a target, a decoy is shot once, a sprinter cannot shoot, a jetpacker cannot strafe, and so on; novices weigh none of it), `can_shoot` (no shots into armor lock, through a dome, or at a known decoy), `fight_move` (back off an armor lock, walk into a dome), `grenade_spot`, `avoid`.
- `situation(bot, now, me, snap)`: a dict of facts for planning: enemies seen, mates within 10 u, hit, cracked, an explosive aimed at us, a sword or hammer about to lunge, a vehicle about to splatter us, a sniper on us, a stationary enemy, an overshield, a grenade landing by us, pushing, holding, carrying, fighting, losing or winning, watched, moving, travelling.
- `plan(bot, now, me, snap)`: returns `(kind, how, point, hold seconds, why)` or None. Survival triggers first, then tactical ones, each gated by the tier ladder. Easy uses nothing but sprint on a long walk. Example reasons in the code: "armor lock: shield down, he is close", "armor lock: grenade at my feet", "bubble before the grab", "dash out of his aim, shield down", "dash out of the grenade", "thruster to cover", "hologram to bait the sniper", "hologram round the corner first", "camo for the objective run", "drain the group", "flare before the push", "trip mine on their vehicle route", "sentry on the flank", "regenerator: winning the trade", "jetpack up the ledge", "jetpack up out of the lunge", "brake the fall". Helpers `fly_to`, `air_ok`, `fight_jet`, `high_ground`, `descent`, `road_near`, `flying`, `jet_brake`, `evade_way` and `sprint_wish` support jetpack, dash and sprint decisions.
- `act(bot, now, dt, me, snap, act)`: carries out the plan: aims where it goes, presses, holds, taps on and off, steers a dash, ends a hold whose reason went (an enemy in sight during a sprint, a non-fight jetpack climb when watched), brakes dangerous falls with the jetpack, and handles Halo 4's sprint (everyone's, its own button). Never in Reach with an objective in hand (the press drops it). Sets `act.equipment`, `act.ability`, `act.sprint` and the stick. Returns a note for the trace. `run_away`, `sprint_steer` (steer rather than strafe while sprinting, since a strafe ends Reach's sprint), `sprinting` and `steer_clear` (stay out of mines and grenades) are its helpers.
- `pressable` and `sprint_ok` are switched off by `tools/live_bots.py` where the game's equipment or sprint button is not decoded, and `decoys_listed` is off live (live readers list players only); `unread` holds kinds whose on-state readings were found unreliable.

### `brain/vehicles.py`

Vehicle knowledge for every MCC game, as tables plus small helpers. Kinds are the maps' own names normalised by `kind_of(name)` through `ALIASES` (substring matches in order; cameras, forklifts and similar map objects return None).

- `VEHICLES`: per kind, `move` (`ground`, `air`, `hover`, `none` for turrets), `seats` (in entry order), `gun` (which seat shoots: `driver`, `gunner` or None), `speed`, `crew` (seats worth filling before leaving) and `value` (how much a driver wants it); the Falcon is marked `vtol`. `spec(name)` returns the entry.
- Guns: `GUNNER_GUN` (what a gunner's seat shoots, as a hand gun for lead and aim height), `TURRETS` (Reach's turret names to the variant they make and what they shoot), `variant(name, turrets)`, `gunner_gun(v, turret)`, `driver_armed(v)`, `gun_sides(v)`, `GUN_HEIGHT`, `GUN_HEIGHT_KIND` and `gun_height(turret, kind)` (where a turret's shot leaves).
- Driving roles: `STRATEGY` per kind (`role`: strafe, charge, artillery, circle, air, transport; `rng`: fighting range; `gun`: what the driver's gun throws; `splatter`: runs down men on foot), `strategy(name)`, `RAM_VEHICLES`, `RAM_THETA`, `BOARD_D`, `TANKS`, `BOOSTS`, `TRAVEL_BOOST`, `DRIVER_VIEW` and `driver_view(kind, flat)` (a tank driver's camera height and a mortar's lob angle by range).
- Team roles: `ROLES`, `ROLE_ORDER` (anti-air, anti-vehicle, transport, harasser), `ROLE_FIRST` per mode, `roles_of(name)`.
- Target scoring: `TTK` (seconds for each vehicle gun to kill each target class), `TARGET_COL`, `SEAT_GUN`, `BASE_THREAT`, `seat_gun(kind, seat)` and `target_score(game, shooter, gun, seat, target, killer, objective, off, up, moving, d, in_ram)`: base threat x objective weight / time to kill, with angle penalties, a tank's overhead cone, the Chopper's rear, anti-air bonuses, the gauss gun's preference for vehicles, the rocket Warthog holding fire on infantry in Reach and Halo 4, and the tank gunner's close-hull priority in Halo 3 and ODST. In CE vehicles never die, so all targets count as infantry.
- Flight: `CLEARANCE` and `clearance(kind)` (how far a pilot keeps from obstacles, seconds of open flight ahead, height over the floor, travel height), `TAKE_OFF` and `TAKE_OFF_S` (straight up first for the Falcon and Hornet; nose up for Banshee, Sabre, Seraph).
- Seats and state: `REACH_SEATS` and `reach_seat(kind, want, tries)` (the seat index and turret flag a bot asks for in Reach), `BOARDABLE`, `upright(v)`, `usable(v, now, duds)` (upright, not a wreck, not a dud), `DUD_S`, `DUD_FOR`, `DUD_NEAR`, `needs_gunner(v, snap)`, `taxi_ok(name)` (transports and light harassers only), `ride_score(v, me, goal, trip)` (value x closeness x trip length).
- Geometry: `ELEPHANT` (Sandtrap Elephant's bay, ramp and flag return in its own frame) and `frame_of(v)` (convert between world and a vehicle's local frame).

`bot.py` uses nearly all of it inside `drive`, `decide` and `board_check`; `director.py` uses roles, `needs_gunner`, `taxi_ok` and friends for crewing and jobs; `tools/live_bots.py` imports it as `V`.

### `brain/tracefmt.py`

The extra trace lines that `tools/observer.py` and the report tools read, written the same way by the live runner and the simulator. The module docstring lists the line types: `meta` (once per bot: map, game, bot id, name, team, tier, personality), `think` (whenever a bot decides: top six scores, the chosen goal, `last_flags`, its order, posture and beliefs), `call` (every callout once), `world` (all players, 4 a second live, 8 in the simulator, with blitz state) and `bot` (per bot, including `att`).

- `crosshair(p, players, vehicles, T, reach)`: what a person's crosshair is on: `[x, y, z, on]`, where `on` is a player id, `"v<handle>"` for a vehicle or None for the level, using the terrain's `aim_hit` when available; things within 3 u are ignored when in a vehicle. `seat_of(p, vehicles)` returns `[vehicle kind, gun]`. Both are used for people's rows live.
- `Everyone.rows(now, players, bots, los, aims)`: world rows per player: id, team, alive, position, shield, health, bot flag, has_flag, yaw, pitch, seconds standing still, teammates formed up within `FORM_R` (8 u), the enemy in its sights (`sights`), and optionally crosshair and seat.
- `sights(p, players, los)`: the enemy nearest a player's aim line with line of sight, else -1.
- `brief(x)`, `think_line(now, index, b)`, `meta_line(...)`, `blitz_rows(directors)`, `call_lines(now, director, said)`.

### `brain/sim.py` (test simulator)

Not used in a real match. An offline match loop with the same `Snapshot`/`Action` interface as the live runner, so the brain and directors can be exercised and measured without the game. The module docstring calls it a Blood Gulch simulator; the code now loads any map with `--map` (`maps.get_map`), uses that map's terrain, spawns and items, and supports Slayer, CTF (including One Flag via `set_one_flag`) and, through `sim_modes.SimModes`, Invasion, Territories, Assault, Stockpile, Headhunter, King, Crazy King, Oddball and VIP. It still has no vehicles; gravity lifts are one-way pads (`lifts`), and jumps land on the far side of the terrain's jump links or people's recorded jumps when taken at a run.

- `Sim(mode, per_team, seed, tiers, legacy_comms, map_name, personalities)`: creates players with `make_profile` across the given tiers and personalities, a `Bot` per player, a `Director` per team, item state, a `CommsMeter` and a `simgear.Gear`.
- `step()`: advances `TICK`, builds a `snapshot()`, updates directors, calls every bot's `think`, routes bot reports to the directors, then applies each action: view, crouch, equipment effects (`gear.tick_player`), movement at `SPEED` 2.3 u/s by `move` (walk on the real ground, slide along walls), jumps, `shoot`, `melee`, `grenade`, shield recharge (`SHIELD_DELAY` 5 s, `SHIELD_REFILL` 4 s), then gear, CTF and mode rules and item respawns.
- Damage model: `target_in_crosshair` picks the enemy nearest the view line with line of sight; `shoot` hits if the view line crosses his body (0.12 u to each side, 0.08-0.58 u up) or head (0.07 u, 0.58-0.70 u), smaller when crouched or jumping, larger for splash weapons (`HIT_SIZE`); `BODY_DMG` per weapon; head shots kill an unshielded target; `AMMO` limits power weapons; grenades hit the crosshair target within 25 u 40% of the time; melee 0.8 (a flag melee kills). `damage` and `kill` report shield breaks and deaths to the directors as the live runner does, and deaths respawn after 5 s.
- `run(seconds, trace, pace)`: runs until time or the score limit, optionally writing a trace in the live format using `tracefmt`.
- `CommsMeter` measures callout latency, time for a team to learn of a sighting, staleness and lost sightings; `report`, `compare_comms` (old flat-delay comms against the voice channel on the same seeds) and `main()` (`python -m brain.sim --seconds --map --mode --per-team --limit --seed --trace --compare-comms`).

Many tools import it for tests and reports (for example `tools/test_modes.py`, `tools/test_invasion.py`, `tools/difficulty_report.py`, `tools/tier_matrix.py`, `tools/mode_sims.py`).

### `brain/sim_modes.py` (test simulator)

Not used in a real match. `SimModes(sim)` adds simplified objective rules to the simulator, filling the same `Snapshot` fields the live readers fill (`snapshot(snap)`), so the director's mode plans run offline.

- Invasion (using `brain/invasion.py`'s layout and barriers): in phases 1-2 an attacker alone in a territory for `TAKE_S` (10 s) takes it; in phase 3 the core is picked up and carried to the delivery point; a phase lasts `PHASE_S` (180 s); each team respawns in its phase zone (`spawn_points`, from recorded live spawns where available).
- Territories: a team alone in a zone for `modes.CAPTURE_S` owns it; one point per owned zone every 10 s.
- Assault and Stockpile (`step_carry`): bombs or flags picked up by walking over, carried to a goal (Assault arms over `ARM_S`), dropped on death.
- Headhunter: skulls dropped on death, banked at the active drop point, which rotates every 60 s.
- King and Crazy King, Oddball, VIP (`step_spot`, `pay`, `pick_vip`): hill holding with contest rules (`hills(m)` finds each game's hill markers; Crazy King moves every `HILL_MOVE_S`), ball pickup, scoring and reset after `BALL_RESET_S` (`ball_spawn(m)`), and VIP kills.
- `on_kill(e)` handles drops on death. Infection and Juggernaut are not simulated.

### `brain/simgear.py` (test simulator)

Not used in a real match. `Gear(sim)` gives the simulator equipment and armor abilities so `equipment.Kit` uses and counters run end to end. Reach bots get the default Spartan abilities in turn (`PALETTE`), Halo 4 bots the Halo 4 ones; Halo 3 bots pick equipment up from the map.

- `tick_player(p, a, st)`: turns the action's equipment press into the ability (respecting Reach's held bit via `hold_bit`), drains and recharges `Energy`, fires one-shot kinds (`ONE_SHOT`: hologram, thruster, evade, drop shield, regen field, autosentry), ends armor lock with an EMP, breaks camo on firing, and returns the speed factor and whether the player may move and shoot. It also records thrown grenades so bots can see them land (`NADE_SEEN`).
- `fire_one` (a hologram as a decoy `PlayerState` walking ahead; a wall-aware dash), `deploy` (Halo 3 equipment thrown or placed, fields and domes), `update` (heal fields `HEAL_RATE`, power drain `DRAIN_RATE`, trip mines, autosentry shots, decoy movement), `snapshot` (adds decoys to the players and fills `deployed` and `grenades`), `blocked` (shots do not cross a dome; a drop shield takes damage) and `immune` (armor lock takes nothing; a hardlight shield blocks from the front).

## How the brain knows the map and the game (brain/ and maps/)

The brain never asks the game for anything through an API: it reads the running game's memory, read-only, and turns what it finds into one common picture. `brain/live.py` holds one reader class per MCC title (Halo: CE, Halo 2, Halo 3, Halo 3: ODST, Halo: Reach, Halo 2 Anniversary and Halo 4). Every reader answers the same questions in the same shape: `players()` returns a list of plain dicts (index, name, team, unit handle, position, body forward, aim vector, vehicle, health and shield as fractions, the weapon in hand, the weapons carried, rounds, the motion tracker setting, and per-game extras such as equipment or an armor ability), `objects()` lists live objects by type, and further methods read the flags, the oddball, the active hill, the score and the clock. The match loop in `tools/live_bots.py` picks the class for the game being played and its `snapshot()` function turns those dicts into the brain's `Snapshot` and `PlayerState` objects (velocities from the previous tick, yaw and pitch from the aim vector, riders placed at their vehicle, impossible positions replaced by the last good one). Everything above the reader, the bots, the directors and the simulator, works on that snapshot and never needs to know which game it came from. The memory layouts were found by reverse engineering and are listed in the file; the games that keep no tag names in memory (Halo 3, ODST, Reach) have their objects named by matching them to the map's own placements or to the tag names read from the map file on disk.

Movement and sight run on `brain/terrain.py`. Each map's level mesh is rasterised offline (`tools/heightmap.py`) into `maps/<map>/heightmap.npz`: a 0.25 unit grid with, per cell, the highest and lowest surface, up to several stacked walkable floor levels (a doorway, the roof above it, a catwalk above that) and a bitmask of the heights at which steep faces pass through the cell. `Terrain` builds a directed graph over (layer, row, column) nodes from that grid, with edges only where a body can step (gentle climbs, drops off ledges, stairs and ramps, never through a wall at chest and head height), and answers "where do I walk next" with Dijkstra cost fields computed backwards from each goal and cached. Line of sight is a ray marched over the same grid: it stops at a wall bit at its height, at a floor slab it crosses, under the ground, or in a see-through shield's box. The level data is not the whole truth, so the terrain is layered with what was learned: jumps, crouch paths and lift or cannon rides that people (and bots) actually completed, recorded by the LiDAR tracker (`tools/lidar.py`) into `lidar.json`; floor people walked that the mesh lacks (approved by review); spots where bots kept getting stuck (`nav_learned.json`); sight lines that kept failing to land shots (`los_learned.json`); what people drove and flew (`rides.json`); where bot drivers wedged (`wedges.json`); hand painting (`paint.json`); and learned out-of-bounds spots (`oob.json`). Placed objects the mesh does not contain (crates, Forge pieces, Invasion's gates and one-way shields) are stamped in as walls, floors and ramps, or added as switchable barriers.

The rest of the per-map knowledge comes from files exported once from the official mod kits and the map files: `objects.json` (the scenario's netgame flags, weapon and vehicle placements, player spawns and other placed objects), `callouts.json` (named zones, holds, lanes and key points), `positions.json` (scored power positions), `features.json` (weapons, objective points, teleporters, man cannons, lifts and switches), `inv_spawns.json` (Invasion respawns), and shared data under `maps/_shapes` (object sizes and collision faces, tag names), `maps/_looks` (appearance layouts and armor catalogs), `maps/_inputs` (decoded button bits) and a few others. `brain/maps.py` loads these into one map dict (`get_map`) and builds the terrain once per map (`terrain`), applying every learned layer in a fixed order.

The game mode is read live: the engine number or the variant's engine icon, else the variant's own name (`brain/modes.py mode_of`, `LiveReach.engine`, `LiveReach.invasion`). Slayer, CTF, King and Oddball are handled by the readers and the loop directly; the other objective modes (Territories, Assault, Stockpile, Headhunter, Infection, Juggernaut, VIP, and Halo 4 and H2A modes played as their nearest equivalent) get their places from the scenario's netgame flags (`modes.layout`) and are tracked tick by tick by `modes.Watch`; Reach Invasion has its own layout and phase tracker (`brain/invasion.py`). Forge map variants (a layout built on a Forge canvas or on a built-in map) are recognised from the objects they place that the base scenario does not (`brain/variants.py identify`), filed under `maps/<base>/variants/<id>/` with their own navigation data, and their pieces are read from the running game, named exactly through the map file's tag names and turned into nav geometry (`brain/forge.py`), so a variant gets its own navmesh over its own area, which grows as players reach its edges.

| File | Role |
|---|---|
| `brain/live.py` | Read-only memory readers for every MCC title; one common player and object shape; flags, balls, hills, scores, variant, abilities, Firefight AI |
| `brain/terrain.py` | The walkable grid, line of sight, Dijkstra flow fields, jumps and human links, barriers, out of bounds, vehicle and aircraft navigation, learning from play |
| `brain/maps.py` | Loads a map's files into one dict and builds its terrain with every learned layer; power items; LiDAR link filtering; saving what bots learned; growing a variant's window |
| `brain/modes.py` | Detects the objective modes beyond Slayer, CTF, King, Oddball and Invasion; their places from the scenario; the live `Watch` that fills the snapshot's objective fields |
| `brain/invasion.py` | Reach Invasion: layout from the scenario, phase and side tracking from respawns, score and the core, gates as barriers, spawn choice for bots |
| `brain/stations.py` | Every gameplay object on the map (abilities, teleporters, cannons, lifts, powerups, zones, objectives) named and kept per map or layout in `stations.json` |
| `brain/oob.py` | Learns out-of-bounds spots from unexplained deaths and from bug reports; `oob.json` |
| `brain/forge.py` | Reads placed scenery and crates from the live game, names them by tag id, turns them into nav blocks, faces and shields |
| `brain/placed.py` | The scenario's own placed solid objects (from `objects.json`) as oriented boxes for the nav |
| `brain/variants.py` | Identifies and files Forge map variants; their nav window |
| `brain/armory.py` | Reproduces botcore's armor roll offline (Reach, Halo 4) so the profile view shows the exact pieces |
| `brain/looks.py` | Each bot's name, seed, clan tag and per-game appearance; writes the profile view's look file |
| `brain/emblems.py` | Each bot's MCC emblem from its seed, and its picture for the profile view |
| `brain/paths.py` | Finds Steam, MCC, the mod kits, Visual Studio and the map tools on this PC |

A note on docstrings: several module headers predate multi-game support. `brain/live.py` opens by describing Halo CE only, `brain/terrain.py` calls itself "real Blood Gulch terrain" over a "2-layer" grid, and `brain/maps.py` describes CE kit exports. The code covers every game listed above and any number of floor layers; the descriptions below follow the code.

### `brain/live.py`

`live.py` is the brain's only window into a running match. It never writes to the game. All memory access goes through `tools/memread.Game` (opened on the game's DLL: `halo1.dll` by default, `halo2.dll`, `halo3.dll`, `halo3odst.dll`, `haloreach.dll`, `groundhog.dll` for Halo 2 Anniversary, `halo4.dll`). The addresses and structure offsets were found by reverse engineering and are listed in the file as class constants and comments, many with a note of how each was confirmed.

#### The class family and how a game picks its reader

| Class | Game(s) | Notes |
|---|---|---|
| `Live` | Halo: CE | Fixed globals in `halo1.dll`; tag names in memory |
| `LiveH2(Live)` | Halo 2 Classic | Fixed globals; tag names in a names buffer |
| `LiveH3(LiveH2)` | Halo 3 | Engine globals live in the game thread's TLS block (found with `tools/tls.py`); no tag names in memory |
| `LiveReach(LiveH3)` | Halo: Reach | Halo 3's approach with Reach's layout; damage-taken vitals; armor abilities; loadouts; Invasion helpers; Firefight AI |
| `LiveODST(LiveH3)` | Halo 3: ODST | Firefight only; no score, no flags |
| `LiveH4F(LiveReach)` | Halo 2 Anniversary and Halo 4 | One class, constructed with the DLL name; exact tag names from the map file |

`tools/live_bots.py` chooses the class from the `--game` option (`h2`, `h3`, `reach`, `odst`, `h2a`, `h4`, anything else gives `Live`). Running `python -I brain/live.py --h3` (or `--h2`, `--reach`, `--odst`, `--h4`) prints the current `players()` list, which is a quick way to check a reader against a live game.

Subclasses override only what differs. Each class sets a few layout constants that shared methods use, for example `SLOTS_AT` (where a unit keeps its four weapon handles), `PARENT_AT` (an object's parent field), `OBJECTS_AT`, `TYPE_AT`, `POS_AT`, `TAG_AT`, `VEH_VITAL` (which float on a vehicle is its body health, and whether it counts damage taken), `UNIT_ZOOM` (the unit's zoom byte for traces, `None` where not decoded), `TRACKER_AT`, `AMMO_AT` / `MAG_AT`, and behaviour switches (`PARENT_CARRIES`, `ATTACHED_RELATIVE`, `CHAIN_ATTACHED`, `OBJECTIVE_NAMES`). Reading a shared method therefore means checking which subclass constants it depends on.

#### Finding the engine's data

- **CE and Halo 2** keep their player array, object header array, object pool and tag data at fixed DLL offsets. `_array(ptr)` reads an engine data array header (element count, element size, data start) and `object(handle)` resolves an object handle: the low 16 bits index the header array, the high 16 bits are a salt that must match the entry, or the handle is stale and `None` is returned. Halo 2's pool start is aligned the way the engine aligns it (`_pool`).
- **Halo 3, ODST, Reach, H2A and Halo 4** keep their engine globals in a thread-local block of the game thread. `_find()` walks the TLS blocks (`tools/tls.py blocks`) and keeps the one whose players (or objects) array header carries the engine's `@t@d` data-array signature. `_hdr()` re-checks the signature on every access and calls `_find()` again when it fails, because a new match runs on a new game thread. Each object entry holds the object's address directly.
- Object types used throughout: 0 biped, 1 vehicle, 2 weapon, 3 equipment, 6 scenery, 10 or 11 crate (by game; see `brain/forge.py TYPES`).

`objects(types)` returns `[(handle, type, name, position)]` for live objects of the given types. In CE and Halo 2 the name is the tag path read from memory. In Halo 3 and later it is the name learned for that tag (below), or `"unknown"`; scanning the objects is also what drives that learning.

#### Player records: the common shape

`players()` returns one dict per used player slot:

- `index`, `name` (UTF-16 in memory), `team`, `unit` (the biped's object handle).
- `pos`, `fwd`, `aim`: position, body forward and aiming vector; `pos` is `None` when the player is dead (no unit object).
- `vehicle`: the parent object handle when riding, else -1. In Halo 4 and H2A the seat is read from the real parent field (a nearby flags word had been mistaken for it) and is only accepted if that object exists.
- `health`, `shield`: fractions. CE, Halo 2, Halo 3 and ODST store health and shield fractions directly; Reach, H2A and Halo 4 store damage taken, converted by `_vitals` (below).
- `weapon` (the one in hand), `weapons` (every carried one), `ammo`, `mag` (lists, -1 where unknown).
- `tracker`: whether enemies show on this player's motion tracker (`tracker()`).
- Extras by game: `handle` (Halo 3: the player's own datum handle, for HUD markers), `wtag` (Halo 3: the tag of the weapon in hand, used to tell Infection's zombies apart), `equipment` (Halo 3's carried equipment, Reach/H2A/H4 armor ability), `ability_on`.

Halo 3 also corrects positions for riders: a unit seated on something stores its position relative to the parent, so `world_pos()` walks up the parent chain and transforms the offset by each parent's forward and up vectors.

#### Naming weapons, vehicles and equipment

The brain uses one vocabulary for guns (`brain/bot.py` `WEAPON_RANGE` / `WEAPON_RANK` keys). Two tables map game names to it: `WEAPON_ALIAS` (CE and Halo 2 tag file names, Halo 3's sword) and `TAG_ALIAS` (Reach, H2A and Halo 4 tag names, and the objectives in hand: flag, ball). `brain_name()` strips the prefixes the later games use (`ord_weapon_storm_`, `storm_`, `h2a_` and others) before the lookup. The same table names the map exports' placements (`tools/reach_export.py`), so a gun in a hand and the same gun on the map share one name.

How each game gets names:

- **CE and Halo 2**: `tag_path(tag_id)` reads the tag path from memory (CE's tag array; Halo 2's offsets-into-names buffer) and caches it. `weapon_name()` takes the file name part and applies `WEAPON_ALIAS`. `LiveH2.map_name()` finds the scenario name by searching the names buffer.
- **Halo 3** keeps no tag names. `set_map(objs)` loads the map's weapon and equipment placements and vehicle placements from `objects.json`. Whenever `objects()` sees a loose weapon or equipment object whose tag is not yet named, `_learn()` gives the tag the name of the nearest placement within 0.75 units (1.5 units for equipment, which settles off its spot). Objects anyone has ever held (`_ever_held`, filled by `weapon_name()`) are excluded by `_was_held()`, so a gun dropped on another gun's spawn cannot be misnamed. A tag the map never places is named by its largest magazine seen when that size belongs to one gun only (`MAG_NAMES`). Vehicles are named by the vehicle placement they stand on within 1.5 units (`_learn_vehicle`). Equipment just picked up, still unnamed, is named from the equipment spot within 3 units of the player.
- **Reach** names a tag, in order: by placement (as Halo 3); by the map file's own tag names through `brain/forge.py _tag_names` and `_own_name()` (the name at the tag's index or up to four entries before it, a quirk seen on Forge World), but only for guns the brain has a range for; else by its largest magazine (`MAGAZINE`). Vehicles not on a placement are named by their own tag name, and guns that ride on vehicles (a Warthog's chaingun, a Falcon's side guns, objects of type vehicle themselves) are named by tag name only, never by a nearby placement. `ground_weapons` is Halo 2's version (parent field, rounds).
- **H2A and Halo 4**: the tag index names the tag exactly, so `_learn()` uses the map's own name (through `brain_name`) and only falls back to placements for equipment; `_vehicle_name()` takes the file name at the tag's own index when it lies under a `vehicles` folder. The map path is read from a fixed per-DLL address (`PATHS`).

`ground_weapons()` returns `[(name, position)]` of loose guns with rounds left (empty drops are useless). CE's version reads CE fields; Halo 2's (also used by Reach, H2A and Halo 4) uses the per-game parent field, keeps guns whose rounds are unknown, and leaves Halo 3's flag tags out. ODST still uses CE's version, marked in the code as unchecked for that game.

#### Rounds

CE's `ammo()` and `mag()` read the reserve and magazine of a weapon object; battery weapons (plasma pistol, plasma rifle) report -1. `LiveH2.rounds()` (Halo 2, Halo 3) reads reserve and magazine and keeps the fullest values ever seen per tag: a kind whose magazine has never held a round is a battery weapon and reads (-1, -1), so it is never dropped as empty. Reach, ODST, H2A and Halo 4 set `AMMO_AT = None` (rounds not decoded): every gun reads unknown.

#### Health and shields in the later games

Reach, H2A and Halo 4 store shield damage and body damage taken (1.0 = gone). `_vitals()` converts them to "left" fractions and handles variants without shields (SWAT and similar), where the shield-damage float simply stays 0 and would otherwise read as full shields. A unit that takes body damage while its shield damage stays 0 is marked shieldless; once two players are marked and no player's shield has ever been hit in the match, every player counts as shieldless. Any shield damage seen clears the mark. AI units count only for themselves.

#### Vehicles

`vehicle_dead(handle)` reads the game's own "destroyed" bit: bit 2 of the object's damage flags byte at `DEAD_AT` (Halo 2 +0x10A, Halo 3 +0x110, ODST +0x104, Reach +0x138, Halo 4 and H2A +0x16C). The offsets come from each DLL's `object_get_health` script function, which answers 0 when the bit is set (the decompiled functions are in `ghidra/`, a developer folder that does not ship). The bit was read live on wrecks on Nov 3 2026 in Reach, Halo 3, Halo 4 and H2A (about 100 vehicles destroyed in six matches): at each destruction the flags byte went from 0 to 12 (bit 2 destroyed, bit 3 shield depleted) and stayed set while the hulk sat, and each wreck left the bots' vehicle list at its death. Halo 2 Classic and ODST use the same bit at their own offsets, but no wreck has been read live in those two games yet. Halo: CE has no `DEAD_AT` (its multiplayer vehicles cannot die): there a vehicle is a wreck only when its body field reads 0 after it was read alive earlier in the match, so a field that reads 0 from the start keeps every vehicle usable. `vehicle_left(handle)` is the health left in the body: in Reach, Halo 4 and H2A from the block `object_get_health` reads (`HEALTH_BLOCK`: the block's size as an int16 there, its offset as a uint16 next, the health float 0x10 into the block), elsewhere from the fixed field `VEH_VITAL`. Halo 4 also has `ORIENT_AT` (where a vehicle's forward and up vectors are) used by the loop's `vehicle_fwd`.

#### Motion tracker

`tracker(player)` says whether enemies appear on a player's motion tracker. CE reads the variant's radar flags, Halo 2 the variant's Motion Sensor flag (the same for every player). Halo 3, Reach, H2A and Halo 4 read the player's resolved trait byte (off and allies-only count as off; an unread value counts as on).

#### Score, clock and variant

`match_state()` returns `dict(score={team: points}, limit, time_left)` for `brain/match.py`, or `None` when not applicable.

- CE: the variant block gives engine, teams, score to win and time limit; the slayer globals give team or per-player scores. Other engines' scores are not decoded (empty score, limit kept).
- Halo 2: score to win and time limit from the variant, time left from the 60 Hz tick counter; Halo 2 keeps no team score, so `score` is empty and the loop tallies deaths instead.
- Halo 3: team scores, score limit, time limit (minutes) and ticks from the game globals, each confirmed against the HUD.
- Reach: team scores, limit and minutes from the game globals.
- H2A and Halo 4: a per-DLL `MATCH` table of (TLS slot, offset) cells; time is the largest tick count found in any player record, which runs ahead of the HUD by the deploy countdown.
- ODST: `None` (Firefight has no score race).

`engine()` returns the game engine in CE's numbering (1 CTF, 2 Slayer, 3 Oddball, 4 King, 5 Race). Halo 2 and Halo 3 read it from their variant (`variant()` also returns the teams flag and, in Halo 2, the variant name). Reach runs every mode on one scripted engine, so `LiveReach.engine()` reads the variant's engine icon (`ICON_ENGINE`), and when the icon is out of range it looks for words in the variant name (`ENGINE_WORDS`); anything else plays as Slayer. `variant_name()`, `engine_icon()` and `invasion()` (an Invasion variant that is not Invasion Slayer) serve `brain/modes.py` and the loop. H2A and Halo 4 use the same methods with their own variant block constants.

#### CTF flags

- CE and Halo 2 name flag objects by their tag path (`...\flag`) and read the team each flag belongs to from a field on the object. The carrier is whoever has the flag handle in a weapon slot; a carried flag takes the carrier's position.
- Halo 3, Reach, H2A and Halo 4 cannot rely on names, so `LiveH3.flags()` uses the module function `flags_by_stand()`. The input is every weapon object `(handle, tag, parent, position)` and the map's stands. A tag becomes "the flag tag" the first time an object of it lies on a stand (within 0.6 units across and 1 unit up or down), unless it is the tag of a gun the map places (`_placed`), a tag someone is holding right now, or the object was found in a third weapon slot (objectives ride past the two gun slots). Only one tag is learned per match. Each flag object's team is the stand nearest where it was first seen; a flag first seen carried belongs to the carrier's enemy. The result is `[{team, stand, handle, pos, carrier}]`.
- `_weapons_held()` gathers what `flags_by_stand` needs and also handles the cases that break naive reading: objects carried outside the weapon slots (Halo 4's flag is parented to the carrier's body: `PARENT_CARRIES`), objects attached to a marker whose position is relative to it (Reach's ball: `ATTACHED_RELATIVE`), and markers that themselves ride a vehicle (Halo 3: a CTF stand on a vehicle, `CHAIN_ATTACHED`), whose position is the vehicle's plus the offset along its axes.
- Stands that ride vehicles move. `LiveH3.flags()` matches flags riding a vehicle to the nearest map stand's team, publishes the moving stands as `live_stands` and their capture points as `live_returns` (the vehicle's flag-return marker from `brain/vehicles.py`), and the loop copies them into the map dict every tick.
- One Flag: when only one flag has ever been seen in the match, `one_flag_owner()` gives it to the team that first stands within 12 units of a new flag object (the defenders spawn beside it each round), because the stand's own team label does not follow the sides as they swap.
- H2A and Halo 4 seed the learned tag sets from the map's exact tag names (`OBJECTIVE_NAMES` and `_name_objectives`), so a gun on a stand is never taken for a flag there.
- `loose_flags()` / `loose_named(name)` (Reach and later) list loose objects whose tag name is `...\multiplayer\<name>\<name>`: the start positions of a Forge variant's flags (its stands are not in the export) and Headhunter's skulls.

#### Oddball, King of the Hill and other objectives

- `balls(players)`: CE and Halo 2 by tag path (`...\ball`). Halo 3 and later find the ball the way flags are found, but on the map's oddball spawn flags, and learn it only from an object hung on the spawn marker or carried in a third slot, never from a loose gun lying near a spawn.
- `king_hill()` returns `(centre, radius)` of the active hill or `None`. CE reads the engine's king globals (hill points and centre; radius to the farthest point). Halo 2 reads the active hill number, and `LiveH2.set_map` builds each numbered hill from the map's `King Hill <n>` flags. Halo 3 scans the host's HUD waypoint block for the hill marker and snaps it to the map's hill in 3D (maps can stack hills). Reach, H2A and Halo 4 read the hill marker's handle from the variant or game globals (Halo 4 has a fallback cell for the opening hill), snap the position to the map's hill, and take the radius from the scenario boundary of that hill (`_hill_bounds`, set by `LiveH3.set_map`), else `HILL_R`.
- `objective_items(players, stands, key)`: Assault bombs and Stockpile flags, found like flags with tag sets kept per mode. Halo 2 has a name-based version (`OBJ_PATHS`), marked in the code as not yet confirmed live.
- `item_stands()` (Halo 3): positions of the stands objective items hang on (a weapon whose parent is a crate), for Assault maps whose export lists no bomb spawn.
- `marked_players(raw)` (Halo 3): players the host's HUD marks as VIP, from the same waypoint block.
- `LiveReach.core(players, stand, key)`: Invasion's core (or Breakpoint's bomb with `key="bomb"`), the object first seen on its stand. `LiveReach.present(points)`: which points have any object standing at them (Invasion's gates while closed).

#### Equipment, armor abilities and loadouts

Halo 3's carried equipment handle is named through the placement learning above and mapped with `brain/equipment.NAMES`. Reach, H2A and Halo 4 read the unit's armor ability handle; `ability(handle)` finds the ability's kind by looking up its tag definition and checking which type blocks it fills (`TYPE_ORDER`, per game), caches it per tag, and reads whether it is running. Read failures return `("unknown", False)` instead of failing the tick. `loadout(index)` reads the loadout slot a player's next spawn will use (Reach, H2A, Halo 4), which botcore sets for bots.

#### Firefight

`firefight()` says whether the match is Firefight (Reach by the scenario path, ODST always). `ai_units(players)` returns the AI's live bipeds as player-like dicts with index 1000 plus the object slot and team -1, leaving out players' units, passengers riding a dropship, dead units and (Reach) a player's old body. The loop appends them as enemy players.

#### Per-game map setup

`set_map(objs)` is called once by the loop with the map's `objects.json`. Halo 2 builds its hills; Halo 3 and later load weapon, equipment and vehicle placements, oddball spawns, KotH spots and hill boundaries. `map_name()` returns the running scenario's name (Halo 3, ODST and Reach from the cache header's scenario path).

### `brain/terrain.py`

`terrain.py` is the brain's model of the level: where a body can stand and step, what it can see, how to get anywhere, and what was learned that the level data got wrong. One `Terrain` object exists per map (built by `brain/maps.py terrain`) and is shared by every bot, director and tool in the process.

#### Units and constants

All distances are world units (u). Key constants at the top of the file:

- Body: `EYE = 0.62` (eye height over the feet), `CHEST = 0.40`, `WAIST = 0.30`, `BODY = (0.55, 0.85)` (a cell is walled if steep faces pass at both of those heights over its floor).
- Grid: `NAV_CELL = 0.25`, equal to the heightmap cell.
- Stepping: `MAX_RISE = 0.18` per edge, `MAX_DROP = 3.0`, `STAIR_RISE = 0.27` (stairs, where the stair rule is on), `WALK_NZ` (the steepest walkable face, 50 degrees, from Reach's biped physics), `FLAT_NZ` (2 degrees: a floor), `LAYER_GAP = 1.0` (surfaces this far apart are separate floor levels).
- Costs: `WALL_COST = 1.5` (entering a cell next to a wall, so paths keep to the middle of doors and ramps), `RAIL_COST = 25.0` (a drop over a handrail), `ROAD_COST = 0.4` (a vehicle edge on floor a person drove).
- CE jump model: `JUMP_RISE = 0.6`, `JUMP_REACH = 2.0`, `JUMP_UP_REACH = 1.25`.
- Sight: `FEET_SLAB = 0.6`, `RAY_MAX = 1000.0` (no sight line longer than this; a corrupt position once produced a sight line that exhausted memory).

#### What the heightmap holds and how a Terrain is built

`Terrain(npz_path, bases, extra_floor, blocks, slit_rule, window, stair_rule)` loads `heightmap.npz`:

- `top` (highest surface per cell; missing cells become a high wall), `low` (lowest surface),
- `floors` with shape (L, h, w): walkable floor levels per cell, lowest first, NaN for none,
- `walls` with shape (h, w, words): a bitmask of 64-bit words; bit k set means a steep face passes through the cell at height `wall_z0 + k * wall_bin`,
- `x0`, `y0`, `cell`, `wall_z0`, `wall_bin`.

`window` (a Forge variant's area, `brain/variants.py`) crops the arrays to a rectangle; `s.full` keeps the whole level's extent and `s.window` the cropped one, and `inside(x, y)` tells whether a point is in it (learned spots, links and spawns outside are ignored, not pinned to the edge). `bases` is `[(centre, radius, roof z)]` for `base_of()`.

Construction order: `_add_floor(extra_floor)` (approved floor people walked), `add_blocks(blocks)` (placed objects), `_build_nav()`, then an empty field cache. `brain/maps.py _build` then adds teleporters, jumps, people's links, paint, wedges, rides, spawns and learned spots, in that order.

#### Placed geometry: boxes and faces

- `add_blocks(boxes)` takes `(pos, (forward, left, up), min, max, name)` boxes in the object's own axes (from `brain/placed.py` and `brain/forge.py`) and sets the wall bits of every cell whose centre falls inside the box at each wall bin's height (with half a cell of padding). Paths then go around and sight lines stop there. A box given with its collision faces as a sixth item is passed to `add_faces` instead.
- `add_faces(pieces)` inserts a piece face by face. Each polygon is fanned into triangles and classified by its normal: flatter than `FLAT_NZ` is floor, up to `WALK_NZ` and at least a cell long downhill is a ramp, steeper or facing down is a wall. Walls set wall bits (`_face_walls` samples each triangle densely). Floors and ramps become walkable floor levels of the cells beneath them (`_face_cells` rasterises triangles from above); ramps keep their slope in `s.slope`, and `s.piece` marks floor levels that belong to placed pieces. Floor buried inside a piece (between a downward face below and an upward face above in the same cell) is removed. The cell's floor levels are then re-stacked with `LAYER_GAP`, growing the layer count if needed. `s.face_kinds` counts the faces of each kind.

#### Approved walked floor

`_add_floor(cells)` adds floor that people walked but the mesh lacks (from reviewed moves and the paint "walk" layer): where the cell already has a floor within 0.3 u, that floor is corrected to the walked height (keeping a subtle ramp's rise); otherwise a new level is inserted. `_build_nav` later forces these cells walkable whatever the wall bits say.

#### Height queries

- `top_at`, `ground` (the lowest surface, 0 when none), `top_near(x, y, r)` (the highest floor within r, used for roofs and tower tops), `height_over(x, y, z)` (height over the highest floor at or below z, for aircraft).
- `nav_z(x, y, from_z)`: the floor height the path grid agrees on, preferring the layer a walker at `from_z` can step to.
- `floor_in_band(x, y, zmin, zmax)`: a typical floor height near a point inside a height band, preferring reachable floor (used to put callout zone centres on real floor).
- `ground_ok(x, y, z, drop)`: is there floor within `drop` below (or a step above)? False over a void or off the map. A lowest surface far above head height is treated as an overhang with air under it, not a wall.
- `walkable(p)`, `base_of(p)`.

#### Line of sight and the crosshair

- `los(a, b)`: eye of `a` to chest of `b`, or else to `b`'s eye (a head over a low wall). Non-finite positions return False. A learned blocked line (below) hides `b` only when more than 8 u away.
- `_ray(a, b, part)` samples the segment every 0.8 cells and fails on: a see-through shield box in the way (`_through_glass`), the ray crossing the plane of either player's own floor within `FEET_SLAB` of him (shots through the floor he stands on), any sample under the lowest surface, a wall bit at the sample's height, or the ray crossing any floor level between samples (a slab between storeys). Open air under overhangs stays open.
- `aim_hit(o, yaw, pitch, reach)`: where a view ray first meets the level, for the trace's crosshair.
- `clearance(p, yaw, far, height, waist)`: how far a body can move along a heading before a wall at chest height; with `waist=True` it also stops at handrails at waist height, following the floor step by step so stair risers are not mistaken for rails.
- `fly_clear(p, yaw, far, dzs, floor, start, avoid)`: an aircraft's short look ahead at several heights against wall bits, floor slabs within 0.4 u and the ground; `avoid` adds remembered blocked spots (and out-of-bounds spots).

#### The navigation graph

Nodes are `(layer, row, col)` on the `NAV_CELL` grid, with id `(l * nh + j) * nw + i`. `_build_nav()`:

1. `lz` is the floors array at nav resolution; `lwalk` marks floors that are finite and not walled at body height (`_walled`: wall bits at both `BODY` heights). Approved walked cells are forced walkable.
2. `near_wall` (from `_near_wall`) marks nodes with a neighbour that rises into solid above the floor with no surface to step onto.
3. For each of the four edge directions and every pair of layers, it computes the rise between neighbour floors and adds an edge when the rise is within the limit and the drop within `MAX_DROP`. The rise limit is `MAX_RISE`, raised for placed ramps to the ramp's slope times the edge length (`tz`), and for stairs to `STAIR_RISE` along the stair's run when `stair_rule` is on (`_stairs()` finds cells whose floor climbs steadily through both neighbours on an axis). Halo 4 and H2A maps use the stair rule.
4. Drops off ledges: with `slit_rule` (Reach maps), a drop into a slit no body fits through (5 or more of the landing's 8 neighbours still have floor at the upper height) is removed. A drop through a handrail (wall at `RAIL` heights over the upper floor) costs `RAIL_COST` extra rather than being forbidden.
5. Edge cost: length, plus twice the height change, plus `WALL_COST` near walls, plus the rail cost.
6. The edges become a SciPy CSR matrix `graph`; `graph_to` is its transpose, so a single Dijkstra from a goal gives every node's cost to that goal. `degree` counts each node's exits (0 means a sliver you cannot leave).

Lookup helpers: `_cell(p)`; `_layer(j, i, z, reach_from, tan)` (the layer nearest a height, optionally only those reachable by a step); `_node(p)` (the node for a position: its layer by height; for a thing on a stand whose own cell only has floor far below, the nearest walkable cell at about its height; for a wall-hugging position, the nearest open cell on the same level); `_center(l, j, i)` (waypoints at cell centres); `_straight_ok(a, l, j, i, ground)` (can a body walk a straight line to that node using the same step rule, without dropping off a ledge or scraping a wall).

#### Flow fields and memory

`_field(goal, jump, human, safe, limit, no_tele)` returns the cost-to-goal array (L, h, w) and caches it:

- The goal is snapped to a floor near its height (searching neighbours if its own cell's floors are all far away, preferring reachable ones), then to a reachable node outside out-of-bounds (`_reachable_node`).
- Goals in the same half-unit square share a field.
- There are separate caches for walking (`_fields`), jump-capable bots (`_jfields`, over `graph_jump_to`) and bots that use people's links (`_hfields`, over `graph_h_to`).
- `safe=True` (an objective carrier) temporarily prices people's drops of more than `RISKY_DROP` (8 u) as walls; `no_tele=True` prices every edge on or off a teleporter trigger as a wall (`_risky`). `limit` searches only a radius around the goal (rounded up to 10 u so neighbours share).
- Field memory is bounded by `FIELD_BYTES`: `total_ram()` reads physical memory through `GlobalMemoryStatusEx`, `field_budget()` gives each of the four caches (walking, people's, jump, vehicle) a share of 20 percent of RAM, at most 1.5 GB each, and `keep_field` / `cached_field` evict the least recently used field. Large Forge canvases made this necessary.

#### Asking the way: `nav`, `path_ahead`, `reaches`, `can_step`

`nav(a, b, lookahead, jump, human, safe, no_tele)` returns the next point to walk toward:

1. Non-finite input returns `None`; a goal with no height is taken on the walker's own level.
2. Within 2.5 u and walkable in a straight line: the goal itself.
3. With people's links available: a jump (or crouch or recorded route) is taken only when its take-off is right here and it is on the cheapest route to this goal (`way_in`: the landing's cost plus the link's cost equals the take-off's cost), returning a `JumpVec` (land point, take-off point, optional run-up point) or a `RouteVec` (the recorded path with crouch and jump flags per point). This stops bots from taking a jump just because it happens to be near.
4. With CE jump links (`jump=True`): a jump from here or a neighbouring cell that saves at least 1.5 of cost.
5. No path from here: the nearest cell that has one (own level first), else straight at the goal.
6. Standing on a teleporter trigger that is the way: the pad's centre.
7. Otherwise `_down()` walks up to `lookahead` steps down the field along the graph's own walking edges, and the farthest node still reachable in a straight line is the answer.

`path_ahead(a, b, n, ...)` returns the same descent as a list of cell centres (what a walker "sees" of its route). `reaches(a, b)` tests for any path. `can_step(a, b)` is the movement rule used by the simulator: a step is allowed exactly when the path graph has that edge (or the same cell, or the walker is on a sliver with no exit), so movement can never reach a place the paths cannot leave.

`open_spot(center, r, rng)` picks a random walkable spot near a point, preferring open ones (the share of walkable neighbours on a ring), never out of bounds.

#### Teleporters, CE jumps and people's links

- `add_links(pairs)`: one-way teleporters. Every walkable node within about 0.75 u of the sender pad and at most 1.5 u under it gets a cheap edge to the receiver's node; `s.links` maps trigger nodes to `(destination node, pad position)`.
- `build_jumps()` (CE maps only, `brain/maps.py` decides): jump edges from floor at an edge (fewer than 8 neighbours) up onto ledges within `JUMP_RISE` and `JUMP_UP_REACH`, or across or down real gaps up to `JUMP_REACH`, with no floor bump inside the arc and no wall at body height in between. They go into a second graph, `graph_jump`, used only by skilled bots. `s.jumps` maps nodes to their jump targets.
- `add_human_links(links)`: links recorded by LiDAR or painted by hand (`take_off`, `land`, optional `runup`, `path`, `kind`). Jumps cost 1.5 times their flat length plus 1; rides that climb 10 u or more (man cannons, lifts) cost their time aloft at running speed instead; crouch paths and recorded routes cost about their length. `jump_ways()` decides whether a jump also works backwards: yes if someone did it the other way, no for called, ridden or painted links, climbs over 4 u, arcs much higher than a jump, landings higher than three quarters of the map's measured jump apex above the take-off, and running jumps with no floor to run up from; `reverse_jump()` builds the way back. Crouch routes go both ways, recorded routes one way. The edges are added to `graph_h` (walking plus people's links) and to `graph_jump` (rebuilt from `graph_jump_base` so repeated calls never stack edges). Learned stuck spots and barriers are re-applied to the new graphs. It is safe to call again as LiDAR adds links during a match.
- `route_points(link)`, `crouch_key(x, y, z)` (the half-unit crouch cell key shared with `tools/lidar.py`), `climb_ok()` (the shared step rule) are module helpers.

#### Reachability

`set_spawns(points)` runs a breadth-first search over `graph_h` (people's links count) from every spawn point and stores `reach`. Goals elsewhere, such as the top of a rock nobody can climb, are moved to the nearest reachable node by `_reachable_node`. With no spawn inside a variant's window everything walkable counts.

#### Learning from play

- **Blocked sight lines** (`learn_blocked(a, b)`): when bots keep shooting along a line on target and nothing lands, the level data probably misses something solid. The line is keyed by both ends' 2 u cells, counted only on its third dry episode (`BLOCK_VOTES`), stored both ways, capped at `BLOCK_MAX` (300) per map, and saved to `los_learned.json`.
- **Stuck spots** (`learn_stuck(p, sure, who)`): a bot that pushed toward a spot alone and did not move (or fell off the map there). A spot becomes a cost disk of radius `STUCK_RADIUS` costing `STUCK_COST` (400, a wall unless there is no other way) on the walking, jump and human graphs (`_stuck_cost`), and the field caches are cleared. Guards: never on a spot people stood on (`people_walked`, from LiDAR walk cells), never inside an existing disk, at most `STUCK_MAX` per map. Reports from live or simulated bots need three reports from at least two bots and at most ten new spots a match; tool reports need two. Spots loaded from `nav_learned.json` pass `sure=True`.
- `brain/maps.py save_learned` writes both sets back to the map folder.

#### Barriers and shields

Objects that come and go (Invasion gates, Forge shields) are not baked into the grid. `set_barrier(key, a, b, z0, z1, through, on)` registers a vertical rectangle seen from above as segment a-b from z0 to z1; `set_barriers(items)` does the same for many keys at once (`{key: (a, b, z0, z1, through, on)}`) with a single refresh, and only when something changed (used for the Forge pieces that come and go, `brain/forge.py PieceWatch`). `_refresh_barriers()` removes the previous penalty and adds `BARRIER_COST` (100000) to every reversed-graph edge that crosses an active barrier at standing height (`_crossing` computes and caches each graph's edge endpoints); a one-way shield (`through`, a unit vector) only penalises crossings the wrong way. `crosses_barrier(a, b)` is the simulator's collision test. `set_glass(key, pos, axes, lo, hi)` registers a box that blocks sight lines (`_through_glass`, a slab test in the box's axes).

#### Out of bounds

`set_oob(spots, version)` turns `brain/oob.py`'s counted spots into a mask: floors within `oob.R` across and `oob.DZ` in height of any spot. Every step into a masked node costs `BARRIER_COST` (`_apply_oob`, applied after every graph rebuild), goals inside it move out, the vehicle ground leaves it out, and `oob_avoid()` gives pilots the spots for `fly_clear`. `out_of_bounds(p)` tests a position. It does nothing when the version has not changed.

#### Paint and rides

- `apply_paint(layers)` applies `paint.json` layers: `block` cells cost a stuck spot's wall; `drive_s`, `drive_m`, `drive_l` cells become vehicle ground whatever the wall-room rule says (`drive_paint`, `hand_drive`); `fly_low` and `fly_high` (and an older `fly`, treated as high) become `fly_cells`, half-unit air cells with the floor height under them. (`walk` is added earlier as floor.)
- `add_rides(drive, air, heights, marks)` adds what people and bots drove and flew (from `rides.json`): driven cells with a small footprint join `drive_paint`; flown cells join `fly_cells` without overwriting painted ones; `air_heights` (strafing and travelling clearance) and `air_marks` (take-offs, landings, turn-backs) are kept for pilots.
- `fly_way(a, b, layer, ahead)` routes through a painted air layer: a Dijkstra over the half-unit air cells toward the goal cell, cached per goal (pilots ask every tick), returning a point a few cells along, or `None` when the air is not painted there or not joined (then pilots fly straight).

#### Vehicle ground

`_build_vnav()` (built on the first drive, and rebuilt when paint, rides or out of bounds change) keeps the walking graph's edges between nodes at least `VEH_ROOM` (3) cells from any wall, with rises up to `VEH_RISE` and drops up to `VEH_DROP` per cell, out of bounds removed, painted and driven cells added back, and cells around recorded bot wedges (`nodrive`, from `wedges.json`) removed unless painted by hand. Edges on floor people drove cost `ROAD_COST` of their length, and edges near walls cost up to `VEH_WALL_COST` times more inside `VEH_PREF` u (taken from recorded human drives). Only strongly connected pieces of at least 200 nodes or 2 percent of the ground are kept (`vroomy`), so goals never snap into pockets a vehicle cannot leave. `vnav(a, b, lookahead)` returns the next drive point: onto the vehicle ground first when off it, toward the nearest ground node when the goal is off it, through cached fields keyed per unit square of goals; when this piece of ground does not reach the goal it drives as near as the piece goes, and it returns `a` when the vehicle is at the end of the ground nearest the goal.

### `brain/maps.py`

`maps.py` turns a map's folder into the dict the brain uses and builds its terrain. `ROOT` is the project's `maps/` folder.

**`load_map(name)` / `get_map(name)`.** `get_map` caches; `load_map` reads `objects.json` (from the base map's folder; a variant name `"<base>/variants/<id>"` is resolved with `brain/variants.base_of`) and builds:

- `flags` (CTF stands by team; when the scenario has several setups, the farthest red and blue pair) and `returns` (each team's capture point: its own return nearest its stand if that is nearer its own stand than the enemy's, else any return within 3 u).
- `teleporters` (pairs from the "teleport from" and "teleport to" flags, plus any extra pairs from `features.json`).
- `spawns` by mode (`ctf`, `slayer`) and team; a spawn with no game types listed counts for every game; extra spawn groups fold into red and blue.
- `zones` (`brain/callouts.ZoneMap` from `callouts.json`), `bases` (stand, radius, roof height), `points`, `holds` per team, `lanes`, `sneak` routes.
- `spots` by objective kind from the netgame flags (`SPOT_KINDS`: hills, balls, territories, drop points, havens, bombs, bomb goals, stockpile flags and goals). Halo 3 flag names are translated to Reach's (`H3_TYPES`) first.
- `items`: power items from `power_items()` (see below), `positions` and `position_info` from `positions.json` (height, floor seen, cover, score), `features`, `heightmap` path, `objects`, `base`, and for a variant its `variant` info and nav `window`.

For a variant, callouts and positions come from the variant's folder when it has them (made by `tools/variant_strategy.py` for Forge canvases); a variant of a built-in map (one whose scenario places things) keeps the base map's.

**`POWER` and `power_items(objs, h3)`.** A table from each game's placement names to (brain name, kind, value): rockets, sniper, sword, overshield, camo, fuel rod, Halo 3 power weapons and equipment, Reach, H2A and Halo 4 power items. Each matching placement becomes `{name, kind, value, pos, respawn}`, with the scenario's respawn time or a default (60 s powerups, 45 s weapons), plus 2 s for Halo 3 weapons whose timer starts after they are disturbed. `_build` later marks each item `reachable`.

**`terrain(m, live_blocks)` and `_build(m, window)`.** `terrain` builds once per map name (`_TERRAIN` cache); passing `live_blocks` (Forge pieces read live) forces a rebuild. `_build` gathers data from every name in `data_names(m)` (the map itself, or for a built-in map's variant the base map first, then the variant) and builds in this order:

1. Approved floor from `moves_review.json` plus the paint `walk` layer.
2. Paint layers and painted jumps from `paint.json`, and drops onto something that breaks the fall from `drops.json` (both treated as people's one-way links).
3. Static placed objects for Reach, H4 and H2A maps (`brain/placed.static_boxes`), or for a variant its own pieces and shields (`brain/forge.nav_pieces` over `variants.pieces_of`), leaving out the pieces its `variant.json` lists as `dynamic` (seen to come and go in an earlier match, `forge.PieceWatch`; matched by `forge.piece_key`), which are walls only while they stand.
4. `Terrain(...)` with `slit_rule` for Reach (`SLIT_GAMES`) and `stair_rule` for Halo 4 and H2A, then teleporters.
5. CE jump links (`build_jumps`) only on CE maps; Halo 2 and later rely on people's links.
6. LiDAR data from `lidar.json`: crouch cells, cover spots, the map's median jump apex (with at least 20 measured jumps), and the links that pass `usable_links()`; `anchor_launches()` then moves the take-off of every recorded ride up a man cannon or lift (`features.json` "launcher"/"lift") to the pad's trigger.
7. `add_human_links`, `apply_paint`, wedges from `wedges.json` (`nodrive`), rides from `rides.json` (`rides_layers`), spawns (`spawn_points`), item reachability.
8. Callout points, lanes, holds and zone centres are snapped to reachable floor at their real height.
9. `people_walked` from LiDAR walk cells, learned blocked lines from `los_learned.json`, learned stuck spots from `nav_learned.json`, and finally Forge shields (`forge.apply_shields`).

**`usable_links(links, pvp)`.** Decides which LiDAR links bots may use: anything a person did; jumps a bot called and landed (in a match or the simulator); others bots did twice. It drops links bots keep failing, links whose recorded path shows two or more rises (a chain of hops recorded as one jump, `path_rises`), and links the simulator keeps failing. In real matches (`PVP`, set by `tools/live_bots.py`) a drop of more than 2.5 u that only the simulator has landed waits until a bot lands it in a real game.

**Other functions.** `reviewed_moves(name)`; `air_heights(hist)` (strafing and travelling heights from flown-time histograms: the 25th and 75th percentiles, clamped); `rides_layers(names, T)` (drive cells count once a person drove them or bots twice; people's driving lines also go to `T.people_drive` as roads; flown cells split into low and high layers by the learned heights); `spawn_points(m)` (a variant's own spawn objects, else the map's); `grow(m, positions)` and `swap(m)` (a variant's nav window grows in a background thread when a player nears an edge the level continues past, and `swap` moves the new terrain into the same `Terrain` object between ticks, carrying over what was learned meanwhile, and saves the window); `save_learned(m)` (atomic writes of `los_learned.json` and `nav_learned.json`).

Importing `brain.maps` loads Blood Gulch (`BLOODGULCH = get_map("bloodgulch")`), which the offline simulator uses as its default map.

### `brain/modes.py`

Handles the objective modes past Slayer, CTF, King, Oddball and Invasion (`NEW_MODES`, `OBJECT_MODES`).

- **Detection.** `mode_of(game, live)`: Halo 3 by engine number (`H3_ENGINES`: Juggernaut, Territories, Assault, Infection, VIP); Halo 2 by its variant's name; the others by `live.variant_name()`; H2A falls back to its engine icon (`H2A_ICONS`) when the name says nothing. `detect(name)` matches words in the variant name (`NAMES`; Invasion is excluded, it is read elsewhere). Any read error returns `None`, which plays as Slayer.
- **Aliases.** Halo 4 and H2A modes are played as the mode they resemble (`ALIAS`: Ricochet and Grifball as Assault, Dominion as Territories) on their own netgame flags (`KINDS`).
- **Places.** `layout(objs, mode)` returns `{kind: [(Vec, radius, team)]}` from the netgame flags (`PLACES`, covering Reach's and Halo 2's names). `radius(f)` sizes a zone from its scenario boundary (a cylinder's radius, half a box's short side, clamped). When a map has no bomb goal (Halo 3), the CTF flag returns are the goals and the CTF stands are recorded.
- **`Watch`**, created by the loop for the current mode, fills the snapshot every tick in `update(live, snap, now, raw)`:
  - Territories, Headhunter drop points, Infection havens become `snap.obj_zones` with the team holding each. Zone control is not read from the game: a team that holds a zone alone for the game's capture time (`CAPTURE_S`) owns it until the other team does the same.
  - Headhunter's loose skulls (`live.loose_named("skull")`) become `snap.obj_items`.
  - Assault and Stockpile items come from `live.objective_items` on the layout's stands (Halo 3 Assault reads stands live: `live_stands`); each item gets its team from its stand and, for Assault, `armed` when it lies uncarried in the other team's goal off its own stand. `snap.obj_goals` lists each team's goals; `one_bomb()` recognises One Bomb (one bomb, one team's, steady over 10 to 20 s) and removes the attackers' own goal. Carriers get `has_flag`.
  - Infection in Halo 3 (`split_infected`): the game treats it as free for all, so the infected are recognised by their weapon tag (the kind the fewest players hold at the start) and the snapshot's teams become 0 survivors and 1 infected.
  - Juggernaut and VIP (`mark_special`): the Juggernaut is the player whose shield reads over 1.0 (his overshield), and the snapshot becomes everyone against him; VIPs come from `live.marked_players`.
- **Helpers.** `carry_goal(mode, snap, team, pos)` (Assault: the enemy's goal; Stockpile: its own), `zombie_team(snap)` (Reach: the team with the most swords), `stands_by_spawn(spots, players)` (a Forge variant's CTF stands: each loose flag position paired with the team whose players spawned nearest, best pairing overall).

### `brain/invasion.py`

Reach Invasion: Elites attack, Spartans defend, in three phases (two territory phases, then a core run; Breakpoint's phase 2 is a bomb run).

- **`layout(objs, shapes)`** builds the setup from the scenario's Invasion flags: `inv_objective` (territories and the delivery point), `inv_obj_flag` (the core's stand), `inv_res_p1..p3` (respawn zones per team and phase), and gate and platform objects. The attackers are the team whose phase 1 respawn zone is farther from every objective. Each phase's territories are the two objectives nearest the defenders' zone for that phase; the stand nearest the phase 2 territories is the core's; the remaining objective farthest from it is the delivery point; a second core marker more than 5 u away is Breakpoint's bomb stand. Zone radii come from the boundaries. Gates, platforms and Invasion objects big enough to stop a body become barrier segments sized from `maps/_shapes/reach.json`; a collision material ending in `_for` marks a one-way shield passable from its front to its back; the core's own stand is skipped. Returns `None` on a map without Invasion.
- **Reading the phase and sides.** `roles_from_spawns` decides which player team is attacking from where each team respawns (the teams swap roles between rounds, so scenario labels name roles, not colours). `phase_from_spawns` votes the phase from the attackers' respawns near their zones (it can only tell phase 1 from 2 or later).
- **`Watch(inv, T)`** runs every tick: it records respawns (except bots the brain placed itself), detects a round change (nearly everyone dead at once, or a burst of spawns) and resets the round, sets the sides from the round's opening spawns, raises the phase on a clear majority of respawn votes but never past what the attackers' score says (the score's low 16 bits, counted from the round's start), detects phase 3 when the core is carried or moved off its stand (`live.core`), reads which gates still stand every 2 s (`live.present`) and switches their barriers (`apply_barriers`; Breakpoint's vault doors count as open in phase 3), and fills `snap.inv_phase`, `inv_attackers`, `inv_zones`, `inv_zone_r`, `inv_delivery`, `inv_core`, `inv_core_carrier`, `inv_phase_t` and `inv_armed` (Breakpoint's bomb, played as a core run to the nearest plant marker). The carrier gets `has_flag`.
- **Bot spawns.** `honor_spawns(map)` reads named spawns from `inv_spawns.json`. `honor_spawn(...)` picks where a dead bot respawns: one of its side's named spawns offered this phase by weight, or behind a teammate who is out of the fight (`mate_clear`: alive, on foot, unhurt, not carrying, no enemy within 25 u seeing him; `ally_spot` finds floor behind him in his sight). A spawn reserved for vehicles is offered only while a free vehicle is near it (`free_rides`). botcore then moves the bot there as it spawns.
- `apply_barriers` / `clear_barriers` put the layout's barriers on the terrain or take them off.

### `brain/stations.py`

Keeps a catalogue of every gameplay object on a map or Forge layout, for LiDAR's view and the bots' map knowledge.

- `scan(live, game)` reads the whole object table (Halo 3, Reach, H2A and Halo 4, the games whose map files give tag names, via `tools/reach_tag_names.py`) and classifies each object by its tag path (`classify`): ability or equipment to pick up (`ABILITY` maps tag names to the brain's kinds), teleporter (sender, receiver or two-way), launcher (man cannon), lift, powerup, health, ammo, grenade, weapon, vehicle, objective, spawn, kill, safe, trait and spawn zones (`ZONES`), and controls. Objectives (flag stands, spawns and returns, oddball, bomb spawns and goals, hills and hill beacons, territories, capture plates, skulls) are matched before spawns, because Halo 3 names its flag and bomb stands `ctf_flag_spawn_point` and `assault_bomb_spawn_point`. Building pieces are not stations. A vehicle is renamed by what rides on it (`brain/vehicles.variant`, for example a Warthog variant by its turret).
- `Stations(map_name)` loads and updates `stations.json`: each object keeps the spot where it lay before anyone took it (held or carried things are not moved; a vehicle keeps where it stood before anyone rode it); an unattended object that moved more than `MOVED_R` follows (moved in Forge). `watch(players)` learns teleporter pairs from a jump of more than 6 u from beside a sender to beside a receiver. `mark(text, pos, stamp)` records a bug report with the stations nearest the reporter. `save()` drops objects not seen during a run of at least 60 s and writes the file atomically.
- `features(map)` exports the stations for the LiDAR view; `describe(map)` prints a summary (`python -I -m brain.stations <map>`).

### `brain/oob.py`

Learns where nobody may be. The games' kill zones and soft kill zones are not read from the maps; they are inferred.

- `Oob.watch(now, people, sees)` keeps each player's last 2 s. A death counts as out of bounds when the player was alive and unhurt (health and shield at least `FULL` a second before, and the vehicle's health full when riding), did not fall `FALL` u, had no enemy within `NEAR` u and none in sight within `SIGHT` u, and was not one of `AT_ONCE` or more deaths in the same tick (a round reset). The first such death is a candidate; it is counted when a second lands within `R` (and `DZ` in height) or immediately if no enemy was alive within `ALONE` u.
- `Oob.flag(text, pos, t)` counts a spot at once when a bug report's text names out of bounds (`WORDS`).
- `save()` writes `oob.json` (`spots` with source, time and note; `candidates`). `features(map)` exports spots for the LiDAR view. `Terrain.set_oob` turns spots into a soft wall (see above).

### `brain/forge.py`

Reads placed objects from the running game and turns them into navigation geometry.

- `_tag_names(live)` gets the running map's tag names by index from `tools/reach_tag_names.py` (cached per map in `maps/_shapes/<game>_tags_<map>.json`). The game keeps no names in memory, but the tag id indexes the map file's list exactly (with the small slack `LiveReach._own_name` allows).
- `_pieces(live)` / `live_pieces(live)` list `(name, pos, (forward, left, up))` for live scenery and crates (`TYPES` per game; moving machines are left out), with orientation from the object's forward and up vectors (`AXES_AT`). In Halo 4 and H2A, markers, beacons, spawns and similar are skipped by name (`SKIP`).
- `block(name, pos, axes, ...)` makes one nav piece: with collision faces known (`maps/_shapes/<game>_faces.json`) it carries them so `Terrain.add_faces` inserts floors, ramps and walls by angle; otherwise its box from `maps/_shapes/<game>.json`. Energy and hologram-only pieces and boxes too small to bump into are dropped.
- Shields: `shield_groups()` reads `maps/_shapes/reach_shields.json` (hand-sorted groups `two_way`, `one_way` with a through direction, `no_pass`). `shields(pieces)` gives each shield's segment, height and box; `apply_shields(T, found)` blocks sight through every shield (`set_glass`) and adds one-way and thin no-pass shields as barriers; `shield_blocks(found)` turns thick no-pass shields into solid boxes.
- `nav_pieces(pieces, game)` returns `(blocks, shields)` for `brain/maps.py`.
- Pieces that come and go. The nav is built once, from the pieces read at the match start, with each piece stamped in for good, but a game type can delete and restore its own walls during a match (Invasion opens its phase gates this way and puts them back for the next round). `PieceWatch(built, dynamic, game)`, made by `tools/live_bots.py` on a map variant, is given each new read of the live pieces (`update(pieces, T)`, every 2 s). A solid piece standing that the nav was not built with becomes a wall: `outline()` turns its box into four sides seen from above with their height, and they go onto the nav as barriers (`Terrain.set_barriers`, keys `fp:<piece>:<side>`) while it stands; a piece under 0.5 u tall is floor and is skipped. A piece missing for `GONE_READS` (2) reads in a row counts as gone and its barriers are switched off. A piece the nav was built with that goes missing is returned as newly dynamic; the loop adds it to the variant's `variant.json` `dynamic` list, and from the next match the nav is built without it, so it is then a wall only while it stands. A stamped-in piece that goes during the current match stays a wall until the match ends, since the nav cannot take a stamp out. `piece_key(name, pos)` names a piece by its tag name and its place rounded to half a unit.

### `brain/placed.py`

The scenario's own placed solid objects for Reach, H4 and H2A maps (the level mesh does not contain crates, barriers and similar). `static_boxes(objs, game)` reads `objects.json` "placed" entries, skips objects that only exist in some game types (a Megalo label with the "hide unless required" flag, or the spawn-flag bit in Halo 4 and H2A), moving machines and controls outside Reach, names that are never solid (`SKIP_NAMES`: doors, lifts, lights, markers, spawns and more), energy and hologram materials, and boxes too small to bump into. Each remaining placement becomes `(pos, frame(rot), min, max, name)` using its box from `maps/_shapes/<game>.json`. `frame(rot, roll_sign)` converts yaw, pitch and roll into forward, left and up vectors; a rolled object is added with both roll senses, because the sign of Halo's roll has not been verified.

### `brain/variants.py`

Files Forge map variants under their base map.

- `identify(base, pieces, placed, game, now, area)`: the objects of a layout read live that the base scenario does not place itself (`own`, within `NEAR` of a base placement of the same name, any name at a spawn; sky scenery excluded). Fewer than `MIN_OWN` (3) means the base map itself. Otherwise the filed variant sharing at least `SAME` (60 percent) of its objects is the same one, edited since; else a new id `v<hash>`. `variant.json` gets the object keys, count, timestamps, all pieces with their axes, and a window: the objects' extent (and the base map's own layout area, `base_area`) plus `MARGIN`, snapped out to a `TILE` grid.
- `base_of(name)`, `base_placed(objs)`, `base_area(objs)`, `info(name)`, `pieces_of(data)`, `window_of(points)`, `grown(window, pos, full)` (grow when a player comes within `EDGE` of an edge the level continues past), `save`, `save_window`.

### `brain/armory.py`

Reproduces, offline, the armor roll botcore performs inside Reach and Halo 4, so the Settings tab's profile view shows exactly what a bot wears. `table(path)` loads `maps/_looks/<game>_armory.json` (made by `tools/armory_tables.py`). `xorshift()` is botcore's 32-bit generator; `roll(seed, slots, none, catalog)` makes the same picks in the same order (slots in the none mask get item 0, then each masked slot draws an item and a variant); `appearance(picks, t)` gives the appearance-block bytes those picks write, as logged from the game's own equip (or `None` if a variant was not logged); `pieces(app, body, t)` turns the bytes into the model's (region, permutation) list for a male, female or Elite body.

### `brain/looks.py`

Each bot's identity and appearance.

- `native/bin/bot_profiles.ini` holds this install's 15 bots (`bot=<name>,<seed>[,<clan>[,<overrides>]]`) and the Settings tab's re-roll options (`experience` original or modern, `effects` share, `species`, `elites` percent). `profiles()` creates it on first use with names from `brain/names.make_names` and two or three shared clan tags (`make_clan`, `CLAN_TAGS`, the same list as `native/bots_panel.cpp`). `read_profiles`, `seed_of` (a name outside the list gets a CRC seed), `clan_of`, `emblem_of`, `overrides_of` (per-game values set by hand in the bot editor, a per-game seed salt, a preferred species).
- `look(name, game)` returns what `botctl.add_bot` sends: either one 64-byte window of player-configuration bytes rolled from `maps/_looks/<game>.json` field specs, or `("roll", seed, slot mask, none mask, effect, fields)` for games where botcore rolls from the game's own Armory (Reach, Halo 4). The roll is seeded by the bot's seed and the game, so a bot looks the same every match. `pick_field`, `roll_fields`, `allowed`, `hand_ok` implement Original versus Modern content, armor effects worn only by the configured share (`EFFECT_CHANCE`), the species share (`elite_share`, `with_share`), and hand-set values kept only where the experience allows them.
- `resolved()`, `armory_view()`, `table_pieces()` and `export_view()` produce `native/bin/bot_looks.ini`, each bot's look per game (and as the other species where the game offers both) with the model pieces it wears, and trigger `brain/emblems.export`. `reach_species()` gives the preferred Reach species (not yet applied in game: the code notes that Reach's species byte is not decoded). `original_items()` filters a slot's items by `maps/_looks/original_content.json`. Running the module runs a self-check.

### `brain/emblems.py`

Each bot's MCC emblem, drawn by MCC in every scoreboard and the post-game report through botcore's answer for the bots. `catalog()` loads foregrounds, backgrounds and colours from `maps/_looks/mcc_emblems.json`; `roll(seed)` picks a foreground, background and three colours with the primary readable against the background, and switches the secondary layer off a quarter of the time (colour 31, MCC's transparent one); `ids()` gives the five numbers MCC stores; `compose()` layers the extracted art from `maps/_models/emblems_mcc/` into an RGBA image, and `export()` writes `native/bin/emblems/<name>.rgba` for the profile view. Running the module runs `selftest()`.

### `brain/paths.py`

Finds installed software without assuming drive letters: Steam's folders from its registry keys (the user's and the machine's, then the default install folder), every library listed in `steamapps/libraryfolders.vdf` or `config/libraryfolders.vdf` (`steam_commons`; `library_paths` reads both the file's `"path"` entries in any case and its older numbered entries, and undoes VDF escapes), an app by its install folder name preferring the library whose `appmanifest_*.acf` actually lists it (`app`, `installed_in`), MCC (`mcc`), the official mod kits (`kit`, `KITS`), which MCC games are installed (`games`, `GAME_MAPS`), the map tools `bsp2obj.exe` and `model2obj.exe` (`map_tool`), and the newest Visual Studio C++ `vcvars64.bat` (`vcvars`, through `vswhere`). Each answer can be overridden with an environment variable (`HB_STEAM_COMMON`, `HB_MCC`, `HB_KIT_<NAME>`, `HB_VCVARS`, `HB_MAP_TOOLS`); `need()` stops a tool with a clear message. `python -I brain/paths.py` runs a small self-check and prints what it finds.

Which MCC folder the mod uses (`mcc()`), in order: `HB_MCC`; else the folder the player chose in the launcher (`chosen()`, the one line of `user/mcc_folder.txt`; if that folder no longer exists the answer is None, not another copy); else the first of `installs()`. `installs()` lists every MCC folder in the Steam libraries: the copies Steam has installed first (`steam_mcc()`: the folder named by `appmanifest_976730.acf` in that library), then other usable folders of MCC's name (a copy left behind or set aside), then ones that are not usable. `check(path)` says why a folder cannot be used (missing, no `MCC\Binaries\Win64\MCC-Win64-Shipping.exe`, no games installed) or None. `find_root(path)` turns the folder the player picked into MCC's own folder: the folder itself, one up to three levels above it (`MCC\Binaries\Win64` or `MCC` picked), or MCC's folder inside it (a `common`, `steamapps\common` or Steam library folder picked). `choose(path)` saves the root to `user/mcc_folder.txt` after `check` passes and answers (ok, the folder saved or why not); `choose(None)` deletes the file (back to automatic). `user/` is not part of the release, and the installer's update and the setup's Repair leave it alone. `is_steam_copy(path)` tells whether a folder is one Steam starts, and `wine()` whether the mod runs under Wine or Proton (the Linux scripts set `PPG_LINUX`; otherwise Wine's `ntdll` has `wine_get_version`).

### Map data (maps/)

Each multiplayer map has a folder `maps/<map>/` named after its scenario with a game prefix (`bloodgulch` for CE, `h2_`, `h3_`, `odst_`, `reach_`, `h2a_`, `h4_`). Shared data lives in folders starting with an underscore. A Forge map variant has a subfolder `maps/<base>/variants/<id>/` holding `variant.json` and its own copies of the per-PC learned files (`lidar.json`, `nav_learned.json`, `los_learned.json`, `oob.json`, `stations.json`, `rides.json`) and, for Forge canvas layouts, its own `callouts.json` and `positions.json`.

The last column follows the release packaging rules in `tools/make_release.py`: "release" files ship with the source, "map pack" files are built from game geometry and ship as an optional separate download (each user can rebuild them with the official mod kits), and "per PC" files are never shipped: each installation records and learns its own.

| File | What it holds | Written by | Read by | Shipped or per PC |
|---|---|---|---|---|
| `objects.json` | The scenario: netgame flags (CTF stands and returns, teleporters, hills, balls, territories, bombs, Invasion markers, with boundaries and facing), weapon and equipment placements with respawn times, vehicles, player spawns with game types and teams, scenery and placed objects | `tools/export_maps.py` and `tools/scenario_extract.py` (CE), `tools/h2_export.py`, `tools/h3_export.py`, `tools/reach_export.py` (Reach, H2A, Halo 4); `tools/refresh_objects.py`, `tools/placed_refresh.py` | `brain/maps.py`, `brain/live.py set_map`, `brain/modes.py`, `brain/invasion.py`, `brain/placed.py`, `brain/variants.py`, `brain/vehicles.py`, many tools | Release |
| `callouts.json` | `base_radius`, `roof_z`, named `points` (mid, high ground and others), team `holds`, attack `lanes`, `sneak` routes, and `zones` (polygon, side, priority, height band, long name, aliases) | `tools/make_zones.py` (Blood Gulch, hand researched), `tools/gen_zones.py` (generated landmark zones, run by the exporters), `tools/variant_strategy.py` (Forge layouts) | `brain/maps.py` (via `brain/callouts.ZoneMap`), `brain/director.py`, `tools/observer.py` | Release |
| `positions.json` | Power positions: position, score, floor seen, height over the surroundings, cover to duck behind | `tools/power_positions.py`, `tools/variant_strategy.py` | `brain/maps.py` (`positions`, `position_info`), `brain/director.py` | Release |
| `features.json` | Every feature for the LiDAR view and the bots: weapons, powerups, grenades, ammo, vehicles, objective points, teleporters, launchers, lifts, controls, doors, shields; extra teleporter pairs | `tools/map_features.py` (from `objects.json` and the scenario XML in `source/`) | `brain/maps.py` (teleporters, launch pads for `anchor_launches`), `tools/lidar.py` | Release |
| `inv_spawns.json` | Reach Invasion respawns per side and phase learned from traces (`att`, `def`), plus named spawns (name, side, weight, centre and facing per phase, points, vehicle reservation) and teammate-spawn weights (`ally`) | `tools/inv_spawns.py` (points from traces); the named entries are entered by hand and kept | `brain/invasion.py honor_spawns`, `brain/sim_modes.py`, `tools/live_bots.py` | Release (Invasion maps only) |
| `heightmap.npz` | The navigation grid source: `top`, `low`, `floors` (L, h, w), `walls` bitmask, `wall_z0`, `wall_bin`, `x0`, `y0`, `cell` | `tools/heightmap.py` from the level mesh (run by the exporters) | `brain/terrain.py` (through `brain/maps.py`), `tools/lidar.py`, `tools/paint.py`, `tools/power_positions.py` and others | Map pack |
| `topdown.png` | A top-down render of the heightmap with the map's objects, for laying out zones and for reports | `tools/heightmap.py` (with the exporters) | `tools/map_art.py` | Map pack |
| `glass.json` | See-through faces (glass, windows, fog volumes) as quarter-unit cells with their height ranges | `tools/glass_mask.py` (from `bsp2obj --glass`) | `tools/lidar.py` (cover painting leaves glass out, so the `cover` spots bots use never sit behind glass) | Map pack |
| `source/` | Raw kit exports: the level mesh (`bsp.obj`) and the scenario as XML | The exporters | `tools/heightmap.py`, `tools/map_features.py`, `tools/object_shapes.py` | Never shipped (rebuilt from the kits) |
| `lidar.json` | LiDAR's merged knowledge: walked cells by kind (`walk`, quarter-unit cells with a height step and kind, including crouch), `cover` spots, `deaths`, measured jump apexes (`jumps`), and `links` (jumps, crouch paths, recorded routes, rides: take-off, run-up, landing, apex, air time, path, who found it, human, bot and simulator success and failure counts, one or two way), run and minute totals | `tools/lidar.py` (LiDAR mode, and `HumanWatch` in every bot match), `tools/lidar_sim.py` (merges simulator jumps) | `brain/maps.py _build` (crouch cells, cover, jump apex, usable links, `people_walked`), `tools/lidar.py` view | Per PC |
| `lidar_sim.json` | The offline simulator's own scan, in `lidar.json`'s format | `tools/lidar_sim.py` | `tools/lidar.py` view and map list (the brain uses only the jumps merged into `lidar.json`) | Per PC |
| `nav_learned.json` | Learned stuck spots `[x, y, z]` | `brain/maps.py save_learned` (from `Terrain.learn_stuck`), `tools/lidar.py` (fall edges where the data claimed floor) | `brain/maps.py _build` (`learn_stuck(sure=True)`) | Per PC |
| `los_learned.json` | Learned blocked sight lines, each a pair of 2 u cell keys | `brain/maps.py save_learned` (from `Terrain.learn_blocked`) | `brain/maps.py _build` (`Terrain.blocked`) | Per PC |
| `rides.json` | What people and bots drove and flew: `drive` cells with person and bot counts, `air` cells with floor height and flown heights, height histograms `h`, `takeoff`, `landing`, `turnback` marks | `tools/lidar.py` RideWatch (in matches via `tools/live_bots.py`) | `brain/maps.py rides_layers` into `Terrain.add_rides`, `brain/bot.py`, `brain/equipment.py`, `tools/wedges.py` | Per PC |
| `wedges.json` | Where bot drivers wedged (`wedges` with sample counts) and the half-unit points removed from the vehicle ground (`nodrive`) | `tools/wedges.py` from match traces | `brain/maps.py` into `Terrain.nodrive` and `_build_vnav` | Per PC |
| `paint.json` | Hand painting on the roofless view: half-unit cells per layer (`walk`, `block`, `drive_s`, `drive_m`, `drive_l`, `fly_low`, `fly_high`) and drawn `jumps` | `tools/paint.py` (local page over `roofless/`) | `brain/maps.py _build` (`extra_floor`, `apply_paint`, painted links) | Per PC |
| `drops.json` | Drops onto something that breaks the fall (for example onto a vent), each a one-way link with a run-up | Entered by hand | `brain/maps.py` (as painted links), `brain/bot.py` | Per PC |
| `moves_review.json` | Reviewed patches of floor people walked that the nav lacks: id, kind, approved or not, cells, reason | `tools/review_moves.py` | `brain/maps.py reviewed_moves` (approved floor joins the nav) | Per PC |
| `oob.json` | Counted out-of-bounds `spots` (position, source, time, note) and pending `candidates` | `brain/oob.py Oob.save` (from `tools/live_bots.py` and `tools/lidar.py`) | `brain/oob.py`, `Terrain.set_oob`, `tools/lidar.py` view | Per PC |
| `stations.json` | Catalogued gameplay objects (`objects`), learned teleporter pairs (`teleports`), bug-report `marks` with nearby stations | `brain/stations.py Stations.save` (from `tools/live_bots.py` and `tools/lidar.py`) | `brain/stations.py`, `tools/lidar.py` view | Per PC |
| `shots.json` | Shot recipes: where to stand, where to aim and how long to fire to open something (a gate button, a lock), with the effect seen | `tools/lidar.py` ShotRec | `tools/lidar.py` (LiDAR bots replay them) | Per PC |
| `roofless/`, `roofless.json` | One top-down picture per floor level with everything above a cut height removed, and their extents | `tools/roofless.py` | `tools/paint.py` | Per PC (rebuilt locally) |
| `variants/<id>/variant.json` | A Forge layout: id, base, game, name, first and last seen, object keys, count, nav window, every piece with its axes | `brain/variants.py identify`, `save_window` | `brain/maps.py load_map` and `_build`, `tools/live_bots.py`, `tools/variant_strategy.py` | Per PC |
| `maps/_inputs/<game>.json` | Decoded input bits per button (melee, grenade, ability, crouch and others): offset, mask, press-only, and how each was confirmed | `tools/decode_buttons.py` | `tools/live_bots.py decoded_buttons` into `botctl.set_button_map`; `native/shared.h` refers to it | Release |
| `maps/_looks/` | `<game>.json`: which player-configuration bytes hold which appearance field and the allowed values; `<game>_armory.json`: armor catalogs and customization tables; `mcc_emblems.json`: emblem catalog; `mcc_items.json`: MCC item names; `original_content.json`: each game's original customization list | `tools/look_probe.py` (layouts), `tools/armory_tables.py` (armories), `tools/emblems.py` (emblem catalog); the original content list by hand | `brain/looks.py`, `brain/armory.py`, `brain/emblems.py`, `tools/look_names.py`, `tools/original_vs_mcc.py` | Release |
| `maps/_vehicles/` | Measured clearance of recorded human drives and flights from walls (percentiles per vehicle) | `tools/vehicle_clearance.py` | Reference data: the vehicle wall-clearance constants in `brain/vehicles.py` and `Terrain.VEH_PREF` were set from it (not read at run time) | Release |
| `maps/_human/` | `reference.json`: a skilled person's measured habits (aim, reaction, movement and similar numbers); `gold.json`: per-map gold-standard matches and their numbers per difficulty tier | `tools/fluidity.py --learn` and its gold-standard option | `tools/fluidity.py` (scores bot play against them) | Release (anonymised) |
| `maps/_shapes/` | `<game>.json`: each object's box (min, max, first material, tag) in its own axes; `<game>_faces.json`: every collision face; `<game>_tags_<map>.json`: a map file's tag names by index; `reach_shields.json`: hand-sorted shield groups; `reach_forge_palette.json`, `<game>_forge_all_items.json`: Forge palettes; `reach_seats.json`: vehicle seats | `tools/object_shapes.py`, `tools/reach_tag_names.py`, `tools/forge_palette.py`, `tools/vehicle_seats.py`; shield groups by hand | `brain/placed.py`, `brain/forge.py`, `brain/invasion.py`, `brain/stations.py`, `brain/live.py` (tag names through `brain/forge.py`), `brain/vehicles.py` | Map pack |
| `maps/_models/` | Character and armor models per game (OBJ with materials, regions and markers), effects, and emblem layer art (`emblems_mcc/`) | `tools/make_models.py` (model2obj exports, a staging area), `tools/fx_art.py`, `tools/emblems.py extract` | `tools/model_pack2.py` (packs the models into `native/bin/models/` for the Settings tab's 3D view), `brain/emblems.py` (emblem layers) | Per PC (extracted from each user's MCC install) |

## Starting a match and the tools (tools/)

The user-facing entry point is the launcher. The Start Menu shortcut runs `tools/launcher.py` under `pythonw.exe`; the launcher immediately restarts itself under the console `python.exe` with a hidden console (`CREATE_NO_WINDOW`) so that no child program it starts can flash a console window. It binds a small HTTP server to `127.0.0.1:8793`, serves `tools/launcher.html`, and opens that page in the project's own app window (`native/bin/ppg_window.exe`, a WebView2 host started by `tools/appwindow.py`). The page polls `/status` every 3 seconds and shows whether MCC was found and which of its games are installed, how many first-time setup parts are ready, other mods in the MCC folder that can clash, and how many maps have a LiDAR scan. Play, the setup buttons and the tool buttons are "tasks": the launcher starts the matching script as its own process with the same Python (`python -u -I <script>`), redirects its output to `logs/launcher/<task>.txt`, and the page streams that file back through `/log/<task>`. The server stops on its own about 20 seconds after the page stops sending `/ping`, unless a task that does not keep running on its own (Play or setup) is still working.

On a fresh install the user runs the first-time setup (`tools/setup.py`), which builds everything that comes from the user's own copy of MCC: the install's 15 bot profiles, the match-recording switch (`logs/trace_on`), map pictures, game logos, the 3D bot models and emblem art, armor effect sprites and each bot's rolled looks. Each step prints one `STEP <n>/<total> <name>: ...` line that the page parses to draw its checklist; Repair runs the same script with `--force`. The launcher's Game folder row lets the user choose which MCC folder the mod uses (Windows' folder picker or a pasted path, saved in `user/mcc_folder.txt` by `brain/paths.py`), or go back to the copy found automatically. Pressing Play runs `tools/launch.py`: it makes sure the bot profiles exist, starts MCC if it is not running (Steam's own copy through Steam, `steam://rungameid/976730`; a copy Steam does not start, directly), waits up to 180 seconds for `MCC-Win64-Shipping.exe`, refuses to continue if Easy Anti-Cheat is running, waits 15 more seconds for the renderer, then injects the newest `native/bin/botcore*.dll` with `native/bin/inject.exe` (restored first by `botctl.injector()` if Windows Defender deleted it). If the user ticked "Start without those mods", the launcher first moves clashing DLLs aside with `conflicts.turn_off()` and starts a detached `conflicts.py --restore-after-mcc` that puts them back once MCC has started and closed again.

From then on botcore.dll, inside the game, is in charge. It creates the shared memory block that Python talks to (`tools/botctl.py`), draws the BOTS panel in the custom-game lobby, and watches the menu state. When the menus give way to a game and botcore sees a game tick from one of the supported engines (Halo CE, Halo 2, Halo 3, Reach, ODST, Halo 2 Anniversary, Halo 4), it starts `tools/play.py` with the panel's settings: `--red`, `--blue`, `--tier`, `--minutes 600 --wait 120`, `--lidar <n>` and `--roster <native/bin/botcore.ini>`, with stdout and stderr written to `logs/brain.txt`. It terminates that process when the game returns to the menus or a Theater film starts. `play.py` works out which game is running, reads the map name and the game variant (team game or free for all), adds the panel's bots through botcore (`botctl.add_bot`, with names, teams, looks, clan tags and emblems), and then runs one of three brains as a child process: `tools/live_bots.py` for normal matches, `tools/lidar.py` for LiDAR mode, or `tools/escort_bots.py` for ODST Firefight on a map without map data.

`live_bots.py` is the live brain loop and runs at 30 Hz. Each pass reads botcore's status block and takes a **snapshot** of the game through the `brain.live` reader classes (players, positions, aim, shields, health, weapons, ammunition, vehicles and their riders, flags, hills, balls, loose weapons, score). It stops its own clock while the game is paused (botcore's tick count stands still), files any new F9 bug reports into the match folder, runs the learners (out of bounds, stations, Invasion and objective-mode watchers, people's jumps and floors for LiDAR, rides for vehicle and air meshes, a Forge variant's growing nav window and the pieces that come and go on it), feeds the Data collector if it is on, and then lets the team **directors** and every living **bot** think (`Bot.think` returns an action: forward, strafe, yaw, pitch, buttons). The action is packed into botcore's button bit layout and written to the bot's shared-memory slot with `botctl.act`; botcore applies it on the game thread on the next tick. When recording is on, the loop writes the match **trace** (`logs/trace_<map>_<date>-<time>.jsonl`): a `meta` line per bot, a `bot` line per bot per tick, a `think` line whenever a bot decides, `call` lines for callouts, `loadout` and `spawn` lines, and a `world` line with everyone four times a second. Once a minute it saves what the nav learned and the LiDAR and ride data; at the end it saves everything again, prunes the wedge cells, closes the collector and leaves every bot standing still.

The tools read what the match left behind. The Observer (`tools/observer.py`, port 8799) lists every trace in `logs/` (and in `logs/evidence`, `logs/qc_keep`, `logs/bug_reports/*/`, `logs/imported/*/`, simulator `sim_*.jsonl`), replays them on a top-down map picture built from `maps/<map>/heightmap.npz`, the nav and `lidar.json`, follows a live match while its trace is still growing, computes the person's statistics from the Data collector file (`tools/player_stats.py`) and exports or imports a match as a zip (`tools/match_export.py`). The LiDAR view (`tools/lidar.py`, port 8797) shows `maps/<map>/lidar.json` and `lidar_sim.json` in 3D, live during a LiDAR match or from storage, and the offline LiDAR Simulator (`tools/lidar_sim.py`, port 8798) serves the same page with its Simulator panel. The nav painter (`tools/paint.py`, port 8796) edits `maps/<map>/paint.json` over roofless views made by `tools/roofless.py`.

Local ports (all bound to 127.0.0.1 only):

| Port | Server | Started by |
|---|---|---|
| 8793 | Launcher (`tools/launcher.py`) | the Start Menu shortcut |
| 8799 | Observer (`tools/observer.py serve`) | launcher task `observer`, or by hand |
| 8797 | LiDAR Viewer: live LiDAR match or stored scans (`tools/lidar.py`) | a LiDAR match, launcher task `lidar_view` |
| 8798 | LiDAR Simulator (`tools/lidar_sim.py`, same page with its panel) | launcher task `lidar_sim` |
| 8796 | Nav painter (`tools/paint.py`) | launcher task `paint` |

None of these servers reuses an address (`allow_reuse_address` is off): on Windows, address reuse let a second copy serve the same port as the first. A second copy therefore fails to bind, opens a window on the copy already running and exits (a LiDAR match first asks a stored view on 8797 to give up the port, see `tools/lidar.py`), and the launcher opens a tool's window again when its task is still running, so a tool whose window was closed comes back.

Files under `logs/` that this part of the code writes:

| Path | Written by | Content |
|---|---|---|
| `logs/launcher/<task>.txt` | launcher.py | output of each launcher task (play, setup, setup_force, observer, lidar_sim, lidar_view, paint) |
| `logs/brain.txt` | botcore.dll | stdout and stderr of `play.py` and the brain it runs |
| `logs/trace_on` | setup.py (step "recording") | marker file: while it exists, matches are recorded |
| `logs/trace_<map>_<YYYYMMDD-HHMMSS>.jsonl` | live_bots.py (path chosen by play.py) | the match trace; the newest 10 are kept |
| `logs/trace_<...>.carnage.xml` | play.py `keep_carnage`, scaling_view.py | copy of MCC's post-game report for that trace |
| `logs/collect_<map>_<stamp>.jsonl` | collector.py (via live_bots.py or lidar.py) | Data collector rows: everyone every tick, people's guns and equipment |
| `logs/bug_reports/<stamp>/report.json` | botcore.dll (F9 or the pause menu) | a single report, not yet filed |
| `logs/bug_reports/<match>/trace.jsonl`, `reports.json` | bug_reports.py | reports filed into their match folder, with the recording |
| `logs/escort_<game>.jsonl` | escort_bots.py | one row per escort bot per tick |
| `logs/lidar_<map>.md` | lidar.py `report` | LiDAR report, rewritten every minute and at the end |
| `logs/lidar_sim.md`, `logs/lidar_sim_idle.json` | lidar_sim.py | one table row per simulated map; the empty view used while waiting |
| `logs/owner_pickups_<map>.jsonl` | lidar.py | the person's weapon pickups with botcore's copy of their action bytes (for decoding pickups) |
| `logs/reach_names.txt` | live_bots.py `reach_name_dump` | Reach only: UTF-16 strings in player data, a diagnostic dump |
| `logs/scaling_view.txt` | brain/scaling.py via scaling_view.py | numbers for the BOTS panel's Scaling hover box |
| `logs/observer_cache/` | observer.py | map pictures (`<map>.png`, `<map>.play.json`) and cached "You" results |
| `logs/exports/match_<map>_<stamp>[_names].zip` | match_export.py | shareable match export |
| `logs/imported/<map>_<stamp>[_n]/` | match_export.py `import_game` | an imported export, listed by the Observer |
| `logs/verify/objective_<trace>.txt` | objective_report.py `--save` | objective-play report |
| `logs/forge_label_probe_<tag>.json` | forge_label_probe.py | a developer probe's dump of a Forge variant's objects and Invasion label texts |
| `logs/launcher/linux.txt`, `logs/linux_setup.txt`, `logs/linux_play.txt` | `installer/linux` scripts | Linux and Steam Deck only: the launcher's output, the install's setup run, Play through Steam's launch option |

`play.py` also reads, but never writes, `logs/test_override.json`: when that developer file exists its keys replace the command-line options (used for scripted test matches so the user's `botcore.ini` is never touched).

Files under `maps/<map>/` that this part writes: `lidar.json` (lidar.py, live_bots.py via `HumanWatch`, lidar_sim.py link merge), `lidar_sim.json` (lidar_sim.py), `rides.json` (`RideWatch`), `shots.json` (`ShotRec`), `wedges.json` (wedges.py), `positions.json` (power_positions.py), `roofless/level_<k>.png` and `roofless.json` (roofless.py), `paint.json` (paint.py), `callouts.json` and `positions.json` inside a Forge variant's folder (variant_strategy.py), and that folder's `variant.json` `dynamic` list (live_bots.py, from `brain/forge.py PieceWatch`). Learned sight lines and walk blocks (`los_learned.json`, `nav_learned.json`), `oob.json` and `stations.json` are written through `brain/maps.py`, `brain/oob.py` and `brain/stations.py`, called from the loops described here.

| File | Role |
|---|---|
| `launcher.py` | Launcher server on 8793: status, MCC folder choice, tasks, logs, Repair, Uninstall |
| `launcher.html` | The launcher page: Play, Game folder, first-time setup checklist, tool buttons, uninstall dialog |
| `appwindow.py` | Opens a project page in `native/bin/ppg_window.exe` (or the default browser) |
| `setup.py` | First-time setup: eight numbered steps built from the user's MCC copy |
| `launch.py` | Play: start MCC (through Steam, or a copy of the user's own directly), check anti-cheat, inject botcore.dll |
| `conflicts.py` | Find clashing proxy DLLs and ASI plugins; move them aside and back; process helpers |
| `play.py` | Started by botcore per match: detect game and map, add the bots, run the right brain |
| `live_bots.py` | The live brain loop: snapshot, directors and bots think, actions out, trace |
| `botctl.py` | Python side of botcore's shared memory: commands, actions, button map, notices |
| `memread.py` | Read-only process memory access to MCC (`Game` class), data array scanner |
| `tls.py` | Thread-local storage blocks of a game DLL (engine globals of Halo 3 and later) |
| `device_probe.py` | Developer probe for map devices (doors, switches, gates) on H2A and Halo 4 |
| `forge_label_probe.py` | Developer probe: where Reach keeps a Forge variant object's label, for Invasion on Forge maps |
| `crouch_key.py` | Is the person's MCC crouch key held right now (MCC in front only) |
| `escort_bots.py` | Map-free Firefight teammates for ODST: follow the person, shoot the Covenant |
| `carnage_names.py` | Write bots' names, service tags and teams into MCC's carnage report (Reach) |
| `power_positions.py` | Score power positions on a map's nav, write `positions.json` |
| `variant_strategy.py` | Callouts and power positions for a Forge map variant's own layout |
| `scaling_view.py` | Refresh the BOTS panel's Scaling hover box (run by botcore when the panel opens) |
| `wedges.py` | Learn where bot drivers wedge vehicles; cut those cells from the vehicle ground |
| `roofless.py` | Roofless top-down pictures of a map, one per cut height, for the nav painter |
| `jumpphys.py` | Per-game run, jump, gravity and lethal-fall physics over the level data |
| `bug_reports.py` | File F9 bug reports into their match folder; list them with Observer links |
| `observer.py` | Observer server on 8799 and command-line trace queries |
| `observer.html` | The Observer page: map canvas, layers, timeline, You, Players, inspector, events |
| `player_stats.py` | The person's and every bot's measures from a collector file or trace |
| `objective_report.py` | Objective play report (CTF runs, King, Oddball, roles, goals) from a trace |
| `match_export.py` | Export a match as a privacy-scrubbed zip; import such a zip |
| `collector.py` | The Data collector writer (game memory only) and the key-row scrubber |
| `lidar.py` | LiDAR mode: tracker, recorder, Roomba mapping bots, people and ride watchers, 3D view server |
| `lidar_view.html` | WebGL 3D view of LiDAR data, maps list, simulator panel |
| `lidar_sim.py` | Offline LiDAR Simulator: Roombas on level data with jumpphys, no game |
| `lidar_director.py` | Whole-map job planner for mapping bots (regions, islands, spots) |
| `paint.py` | Nav painter server on 8796: read and save `paint.json`, build roofless views |
| `paint_view.html` | The nav painter page: layers, brush, jumps, undo/redo, save |

---

### `tools/launcher.py`

**Purpose.** The window the Start Menu shortcut opens. It reports readiness, lets the user choose the MCC folder, starts Play, runs the first-time setup and Repair, opens the tools, opens the install folder and the README, and runs the uninstaller. It is a `http.server.ThreadingHTTPServer` subclass (`Server`, with address reuse off) with one handler class; the page does the presentation.

**Usage.** `python -I launcher.py [--port 8793] [--no-window] [--setup]`. `--setup` appends `?setup=1` to the page URL; the page then starts the setup automatically if MCC is found and any part is missing. `--no-window` serves without opening a window.

**Start-up (`main`).**
1. Under `pythonw.exe` it relaunches itself under `python.exe` with `CREATE_NO_WINDOW` and exits. The constant `PY` is always the console interpreter next to the running one, so every task inherits the hidden console instead of opening its own (relevant for console programs such as `inject.exe` and the model converter run by setup).
2. `conflicts.restore()` puts back any DLLs a clean launch moved aside, in case the PC was turned off before MCC closed.
3. `appwindow.remove_old_edge_profile()` deletes the Edge profile folder that version 0.1.0 used.
4. It tries to bind the port without address reuse (with reuse, Windows let a second launcher serve the same port, and the new window talked to the old launcher). If binding fails, another launcher already runs: it only opens a window on the existing server and returns.
5. It starts the `watch_idle` thread and opens the app window at 1040 x 700.

**Tasks.** `TASKS` maps a task name to (script and arguments, keeps running on its own, the port of its window):

| Task | Command | Keeps running | Port |
|---|---|---|---|
| `play` | `launch.py` | no | |
| `setup` | `setup.py` | no | |
| `setup_force` | `setup.py --force` (Repair) | no | |
| `observer` | `observer.py serve --open` | yes | 8799 |
| `lidar_sim` | `lidar_sim.py --open` | yes | 8798 |
| `lidar_view` | `lidar.py --view --open` | yes | 8797 |
| `paint` | `paint.py --open` | yes | 8796 |

`start(task, clean)` refuses unknown names. If the task's `Popen` is still alive it answers "already running", and for a tool with a port it first opens that tool's window again (a tool keeps serving after its window is closed). Otherwise it starts `PY -u -I tools/<script> ...` with `cwd=ROOT`, output to `logs/launcher/<task>.txt` (truncated each start). For `play` with `clean=True` it calls `conflicts.turn_off()` first and, if anything was moved, starts `conflicts.py --restore-after-mcc` as a separate hidden process.

**Idle stop.** The page posts `/ping` every 5 seconds. `watch_idle` checks every 2 seconds; when no "non-persistent" task (Play, setup) is running and no ping came for `IDLE_STOP` (20 s), it shuts the server down. Tools that keep running (Observer, LiDAR, painter) do not hold the launcher open.

**Status (`status()`).** Returns JSON with: `version` (the `VERSION` file, else `dev`), `mcc` (path from `brain.paths.mcc()`), `mcc_running`, `installed` (an `unins*.exe` exists in the install root), `mcc_choice` (the folder chosen in the launcher, `paths.chosen()`, or null), `mcc_env` (whether `HB_MCC` is set), `mcc_steam` (whether the MCC in use is the copy Steam starts), `mcc_found` (every MCC folder in the Steam libraries, `paths.installs()`), `wine` (running under Wine or Proton), `missing_games` (names from `paths.GAME_NAMES` for games not found by `paths.games()`), `setup` (the step list from `setup.status()` without the game row), `map_tools` (whether `paths.map_tool("model2obj")` exists), `lidar` (`mapped`: map folders with `lidar.json`, `total`: map folders not starting with `_`), `workshop` (subscribed Workshop items), `conflicts` (each clashing file relative to the MCC folder with a reason), and `running` (each started task, alive or not).

**HTTP endpoints.**

| Method and path | Effect |
|---|---|
| `GET /` | `launcher.html` |
| `GET /status` | the status JSON above |
| `GET /log/<task>?from=<n>` | `{lines, next, running, code}`: log lines from line `n`, the next line number, whether the task is alive, its exit code once done; only known task names are accepted (the name becomes part of a path) |
| `POST /ping` | keeps the server alive |
| `POST /run/<task>` | starts a task; body `{"clean": true}` for a clean Play; answers `{ok, message, port}` with the task's window port |
| `POST /mcc` | the MCC folder choice (below): `{"browse": true}`, `{"path": ...}` or `{"auto": true}`; answers `{ok, message}` |
| `POST /folder` | opens the install folder in Explorer |
| `POST /docs` | opens `README.md` with its default program |
| `POST /uninstall` | see below |

Every POST must carry the header `X-Launcher: 1`; a plain HTML form from another site cannot set it, so cross-site requests get 403.

**MCC folder choice.** `choose_mcc(body)` handles `/mcc`. `{"auto": true}` calls `paths.choose(None)` (back to automatic). `{"browse": true}` opens Windows' own folder picker first (`pick_folder(start)`: the `IFileOpenDialog` COM object called through ctypes by vtable slot, folders only, file system paths only, titled "Choose the Halo: The Master Chief Collection folder", starting in the current MCC folder and owned by the launcher's window, found by its title); cancelling answers not OK with an empty message. `{"path": ...}` takes a pasted path, with surrounding quotes removed; under Wine a Linux path starting with `/` becomes `Z:\...` (Wine's drive Z: is the Linux root). The folder then goes through `paths.choose`, which finds MCC's own folder near it and checks it, and the answer is the saved folder or the reason it was refused.

**Uninstall.** `uninstaller()` finds the Inno Setup uninstaller (`unins*.exe`, the installer is `installer/ProjectProvingGrounds.iss`) in the install root (None in a developer copy). `/uninstall` refuses with a message when there is no uninstaller ("delete its folder") or when MCC is running (botcore is loaded into it). Otherwise it answers OK and, on a thread, waits 0.8 s, calls `conflicts.stop_inside(ROOT, keep={own pid})` to terminate every process whose executable lies inside the install folder (the mod's Python, app windows, the injector), starts the uninstaller detached (`DETACHED_PROCESS`, working directory the install's parent) and shuts the server down. The uninstaller itself asks before removing anything.

**Connections.** Imports `appwindow`, `conflicts`, `setup` and `brain.paths`. It never touches the game directly; Play is entirely `launch.py`.

### `tools/launcher.html`

The launcher's single page, plain HTML, CSS and JavaScript with no external resources.

- **Play section.** Rows for Game, Game folder, Setup and Other mods. Game shows "Found" (with "running" and the missing games), that the chosen folder is gone, or "Not found". Game folder shows the MCC folder in use and how it was set (by `HB_MCC`, chosen by the user, or found automatically; for a copy Steam does not start, that Play starts it directly and Steam must be running), lists the copies in the Steam libraries when there are several, and has "Choose folder ..." (the folder picker, hidden under Wine), a paste field with Use, and "Use automatic" (shown only while a folder is chosen); each posts `/mcc` and shows the answer, suggesting Repair after a change. Setup shows "Ready" or "k of n parts ready". Other mods lists clashing files and reveals the checkbox "Start without those mods this time" (checked by default). The Play button posts `/run/play` with `clean` set from that checkbox, warns if setup is unfinished, and then follows `logs/launcher/play.txt` in a log box. Under Wine it instead opens `steam://rungameid/976730`, since on Linux Steam's launch option loads the bots (see `installer/linux/`).
- **First-time setup section.** A step list built from `status.setup`; each line shows an icon (`OK`, `-`, `...`, `!`) and a note. While a setup task runs, `follow()` polls `/log/<task>` every 700 ms and parses `STEP n/t name: text` lines into `stepNote` so working, failed and skipped steps show live. "Run setup" posts `setup`; "Repair" posts `setup_force`. When every part is ready the list and Run button hide and "All parts are ready." shows.
- **Tools section.** Buttons with `data-task` for `observer`, `lidar_sim`, `lidar_view`, `paint`; each posts `/run/<task>`. The LiDAR Simulator row shows "Mapped so far: k of n maps." Under Wine there is no app window, so the page opens a blank browser tab before posting, waits up to 30 s for the tool's port (from the `/run` answer) to answer, and then points the tab at it.
- **Footer.** Open the install folder, Read the guide, Uninstall (shown only when `installed`), and a non-affiliation note.
- **Uninstall dialog.** An `alertdialog` with Uninstall and Cancel (Escape cancels); confirming posts `/uninstall` and shows the server's message.
- **Timers.** `refresh()` every 3 s (a failed fetch shows "The launcher stopped" in the banner), `/ping` every 5 s. Busy buttons get `aria-busy`.

### `tools/appwindow.py`

Opens a project page in its own window. `WINDOW` is `native/bin/ppg_window.exe`, a small Windows program built from `native/ppg_window.cpp` that hosts the WebView2 control of Windows 10 and 11: no browser profile, no sign-in, no extensions, no address bar; links to other sites open in the default browser.

- `command(url, size, title)` builds `[ppg_window.exe, --url, url, --title, title, --width, w, --height, h, (--icon installer/icon.ico)]`. The title comes from `TITLES` by port: 8793 "Project Proving Grounds", 8799 "Observer - ...", 8797 "LiDAR Viewer - ...", 8798 "LiDAR Simulator - ...", 8796 "Paint the nav - ...". Returns None when the executable is missing.
- `open_window(url, size, title)` starts that command and returns at once, or falls back to `webbrowser.open(url)` in a developer copy without the built window. Under Wine (`brain.paths.wine()`, Linux and Steam Deck) there is no WebView2: it only prints the address, and the Linux launcher script and the launcher's page open the pages in the system's browser.
- `remove_old_edge_profile()` deletes `%LOCALAPPDATA%\ProjectProvingGrounds\window` (best effort).
- CLI: `python -I appwindow.py <url> [width height]`.

Used by the launcher, the Observer, the LiDAR view, the simulator and the painter.

### `tools/setup.py`

**Purpose.** Builds every asset that has to come from the user's own MCC install. Nothing here ships with the mod.

**Usage.** `python -I setup.py` (build what is missing), `--force` (rebuild every step: the launcher's Repair), `--status` (one line per step, nothing built).

**Steps.** Step 1 is the game check (`game_line`): it reports where MCC is (`brain.paths.mcc()`) and which games are not installed, or fails if MCC is missing (with a note to choose its folder in the launcher's Game folder row, or that the chosen folder is no longer there) or has no games. The other steps live in the `STEPS` tuple as (name, done test, builder, needs the game, reason it does not apply):

| # | Name | Done when | Builder |
|---|---|---|---|
| 2 | bots | `native/bin/bot_profiles.ini` exists | `brain.looks.profiles()` (draws and keeps the 15 bots) |
| 3 | recording | `logs/trace_on` exists | creates the marker |
| 4 | map art | at least 100 `tools/view_art/maps/*.jpg` | `tools/map_art.py` |
| 5 | logos | `native/bin/art/ce.rgba` and `h4.rgba` | `tools/panel_art.py` |
| 6 | 3D bots | `native/bin/models/made.txt`, or `h3_spartan.mdl` plus `maps/_models/emblems_mcc` | `tools/make_models.py` (needs the map tools) |
| 7 | effects | `native/bin/art/fx_fire.rgba` | `tools/fx_art.py` (needs the map tools; skipped without Halo: Reach) |
| 8 | looks | `native/bin/bot_looks.ini` | `tools/looks_export.py` |

`tool(name, *args)` runs another tools script with the same interpreter and returns (success, its last output line). `run(force)` prints `STEP n/8 name: done | already there | skipped (why) | failed: why | working ...` for each step, catches any exception so one failed step does not stop the others, and finishes with `SETUP COMPLETE` or `SETUP FINISHED WITH k FAILED STEP(S)`; the exit code is 1 if anything failed. `status()` returns `[(name, done, note)]` for the launcher, with a step that does not apply on this PC counted as done and its reason in the note.

### `tools/launch.py`

**Purpose.** The Play task, run by the launcher's Play button: start MCC with anti-cheat off and load botcore, so the BOTS tile shows in the custom game lobbies of all six multiplayer games.

**Usage.** `python -I launch.py [--exe <MCC-Win64-Shipping.exe> [-- <arguments>]]`. `--exe` is how Steam's launch option on Linux runs it (see `installer/linux/ppg-run.sh`).

**Flow (`main`).**
1. `brain.looks.profiles()`: makes sure the install's 15 bots exist (botcore reads `bot_profiles.ini` at injection).
2. Starting MCC, by case:
   - With `--exe` (Linux, inside MCC's own Proton session): starts that program itself with the arguments after `--`.
   - Under Wine without `--exe`: prints that on Linux and Steam Deck MCC is started from Steam with the anti-cheat off option, where the launch option loads the bots, and stops.
   - MCC not running and the MCC in use (`brain.paths.mcc()`) is not the copy Steam starts (`paths.is_steam_copy`): `start_copy` starts that copy's program directly. Steam must be running (`steam.exe`), else it says so and exits with code 1. It first writes `steam_appid.txt` (976730) into MCC's folder and the program's folder where missing, so the copy starts as itself with anti-cheat off instead of handing over to Steam's copy.
   - MCC not running otherwise: opens `steam://rungameid/976730` and prints that the anti-cheat off option must be chosen.
   - MCC already running while a folder is chosen: if the running program (`conflicts.process_path`) is not inside the chosen folder, it warns that the bots load into the running copy and that playing the other copy needs MCC closed first.
3. Polls for the process once a second for up to 180 s (`conflicts.process_running`, a Toolhelp snapshot); a program it started itself that exits meanwhile ends the task with its exit code.
4. Exits with a message if `EasyAntiCheat.exe` or `EasyAntiCheat_EOS.exe` runs.
5. Sleeps 15 s, picks the newest `native/bin/botcore*.dll` by modification time, gets `inject.exe` through `botctl.injector()` and runs `inject.exe <dll>`, printing its output.
6. Prints where the BOTS tile is (next to START, or the B key) in Custom Multiplayer. With `--exe` it then waits for the game to close and exits with its code (Steam counts the game as running while this process runs).

### `tools/conflicts.py`

**Purpose.** Finds other mods that hook the same game and drawing as botcore, offers a clean launch without them, and holds the process helpers used across the tools.

**What counts as a clash (`scan`).** In MCC's root folder and in `MCC/Binaries/Win64`: any file whose lowercase name is in `PROXY` (`dxgi.dll`, `d3d11.dll`, `d3d12.dll`, `d3d9.dll`, `d3d10.dll`, `dinput8.dll`, `version.dll`, `winmm.dll`, the XInput DLLs, `dsound.dll`, `opengl32.dll`, `winhttp.dll`, `wininet.dll`, `msimg32.dll`, `dbghelp.dll`, `uxtheme.dll`, `bink2w64_.dll`), the proxy loaders that ReShade, Special K, ASI loaders and overlays use, and any `*.asi` plugin. Steam Workshop items are only counted (`workshop_count`, the `workshop/content/976730` folder of a Steam library) because MCC loads them only when started with mods.

**Clean launch.** `turn_off()` renames each clashing file to `<file>.ppg-off` and returns the list. `restore()` renames every `*.ppg-off` back when the original name is free. `restore_after_mcc()` waits up to 180 s for MCC to start, then polls every 5 s until it closes, then restores.

**Process helpers.** `processes()` lists `(pid, exe name)` through `CreateToolhelp32Snapshot` with ctypes (no child process, so no console flash). `process_running(name)` and `mcc_running()` build on it, and `process_path(name)` gives the program file of the first running process of that name (used by `launch.py` to tell which MCC copy runs). `stop_inside(folder, keep)` opens each process with `QUERY_LIMITED_INFORMATION | TERMINATE`, reads its image path with `QueryFullProcessImageNameW`, and terminates those inside the folder except the pids in `keep`.

**CLI.** No argument prints the report; `--off`, `--restore`, `--restore-after-mcc`.

### `tools/play.py`

**Purpose.** The per-match entry point that botcore starts (see `native/botcore.cpp` `start_brain`). The module docstring describes an older Halo CE-only command; the current code detects the game and supports all of them. botcore's command line is:

```
<python> -u -I "<root>\tools\play.py" --red R --blue B --tier T --minutes 600 --wait 120 --lidar N --roster "<root>\native\bin\botcore.ini"
```

`T` is one of `novice`, `average`, `strong`, `top`, `strong,average,top,novice` (Mixed) or `scaling`. botcore resets its bot slots, starts this when a supported game tick appears after the menus, writes the output to `logs/brain.txt`, and terminates the process when the menus come back or a Theater film plays. The Python used is the install's own `python\python.exe`, else the one on PATH.

**Options.** `--red/--blue` (players wanted per team, people included), `--tier`, `--minutes`, `--wait` (seconds to wait for the match to load), `--game auto|ce|h2|h3|reach|odst|h2a|h4`, `--teams`, `--ffa`, `--lidar N`, `--roster <botcore.ini>`. If `logs/test_override.json` exists, its keys are set on the options object (a developer test path; extra keys such as `max_bots`, `brain`, `collector`, `ride_only`, `aim_loose` are read only from there).

**Flow (`main`).**
1. **Game.** With `--game auto` it reads the `game` field of botcore's shared memory (`botctl.OFF_GAME`: 1 CE, 2 H2, 3 H3, 4 Reach, 5 ODST, 6 H2A, 7 H4), waiting up to `--wait` seconds because no engine ticks while a match loads. Failing that it checks which game DLL is loaded (`module_loaded`, a Toolhelp module snapshot of MCC), defaulting to CE.
2. **Reader.** Picks the `brain.live` class: `Live` (CE), `LiveH2`, `LiveH3`, `LiveReach`, `LiveODST`, or `LiveH4F("groundhog.dll" | "halo4.dll")`, and retries until `players()` returns someone.
3. **Map name.** For the Halo 2 code path (every game but CE) `"<game>_" + live.map_name()`, retried until the tag name table has filled in; for CE the last part of tag 0's path (the scenario). A map is supported when `maps/<map>/heightmap.npz` exists. ODST without map data uses the escort brain; any other unknown map exits with a list of supported maps unless this is LiDAR mode, which maps blind.
4. **botcore.** If the shared memory's magic is not `HB_MAGIC` (botcore not loaded), it injects the newest `botcore*.dll` and waits up to 5 s. Any player named `Bot ...` that botcore is not driving (left over from an earlier session) is adopted with `CMD_ADOPT`.
5. **Variant.** For H2 and later, `live.variant()` is read until its engine is non-zero (a loading match reads 0) and `teams` comes from it, unless `--teams`/`--ffa` override. For CE the halo1 global variant at `VARIANT + 0x34` (teams flag) is read.
6. **Names.** The install's 15 profile names (from `brain.looks.profiles()`) first, then made-up gamertags from `brain.names.make_names`, skipping names already in the lobby.
7. **Caps.** `botctl.player_cap(game, firefight)`: 16 players, or 4 in Firefight and ODST (more crashed ODST's renderer).
8. **Adding bots.** With a roster (the BOTS panel's list in `botcore.ini`, read by `botctl.roster`) and not Firefight or ODST, `roster_plan()` gives each listed bot its team (Halo CE team games fold teams to red and blue with `team % 2`; free for all gives each bot its own team), keeps the total at 16 with the people already in, and renames a bot whose name clashes with someone in the lobby. Without a roster, team games fill red and blue up to `--red`/`--blue`; Firefight and ODST fill only the person's team up to 4; LiDAR fills the person's team up to `--lidar`; free for all puts each bot on a free team. Every bot is created with `botctl.add_bot(m, machine, team, name, game, look=looks.look(name, game), clan=looks.clan_of(name), emblem=looks.emblem_of(name))`; `machine` starts one past the highest player index.
9. **Brain.** If the override says `brain: none`, it stops here (bots wait for `device_probe.py`). LiDAR mode runs `lidar.py <map> <seconds> --game <game>`. The escort case runs `escort_bots.py <seconds> --game odst --tier <tier>` (Scaling maps to `top`; a Mixed list maps to `average`). Otherwise it runs `live_bots.py <seconds> --tier <T> --personality rusher,flanker,camper,objector,spammer,grudger,sniper --map <map> --game <game> --quiet`, plus `--ffa` for free for all, `--roster` (each bot's own difficulty and style), `--collect on` when `botcore.ini` has `collector=1`, the override's test flags, and `--trace <path>` when recording is on.
10. **Recording.** A trace is written when `logs/trace_on` exists, or always when any bot plays on Scaling (brain/scaling.py reads traces back). `match_trace(map)` names it `logs/trace_<map>_<YYYYMMDD-HHMMSS>.jsonl`, deletes the oldest timestamped traces (and their `.carnage.xml`) so that 10 remain with the new one, and first calls `keep_carnage`: MCC overwrites one post-game report (`%USERPROFILE%\AppData\LocalLow\MCC\Temporary\mpcarnagereport1_3528_0_0.xml`) every match, and botcore kills this script when a match ends, so the previous match's report is copied beside the newest trace when the next match starts (only if MCC wrote it between 30 s before and 10 minutes after the trace's last write).
11. **Reach afterwards.** For Reach with a trace, `carnage_names.py <trace> --wait 20` runs after the brain exits (if the brain was not killed first).

### `tools/live_bots.py`

The live brain loop. Everything that makes the bots play in a real match passes through `main()`. It is large; this section is organised by topic.

#### Command line

`python -I live_bots.py [seconds] [--tier T[,T..]] [--personality P[,P..]] [--roster botcore.ini] [--map NAME] [--ffa] [--game ce|h2|h3|reach|odst|h2a|h4] [--quiet] [--callouts] [--trace FILE] [--collect on|off] [--ride-only kinds] [--aim-loose on|off]`.

Tier and personality lists are dealt out to new bots in order (cycling); a bot on the roster takes its own row's tier and style (style `any` falls back to the personality list). `--ride-only` and `--aim-loose` are test switches: the first hides every empty vehicle except the named kinds, the second sets `brain.profiles.LOOSE_AIM`.

#### Constants and module state

- `HZ = 30`: loop rate. `MAX_DT = 4/30`: the longest time step the bots think with. `think_dt(elapsed)` clamps the real time since the last thinking pass to `[1/30, 4/30]`, so turning, aiming and moving keep real-time speed on a slow PC without a hitch being made up in one jump.
- `PAUSE_TICKS = 9`: loop passes (0.3 s) with botcore's game tick unchanged mean the game is paused.
- `BOT_CROUCH = ("ce", "h3", "h4")`: games where a bot's crouch press actually reaches the game; elsewhere bots always stand, and the snapshot says so.
- Globals set in `main`: `MAP` (from `brain.maps.get_map`), `TEAMS`, `FIREFIGHT`, `RIDE_ONLY`. Caches: `GROUND` (loose weapons, re-read twice a second), `MATCH` (score, limit, time left, twice a second), `HONK` (honk stand-in state), `TALLY` (deaths counted as the other team's points where team scores are not decoded).

#### Start-up

1. **Scaling.** If any tier is `scaling` (command line or roster), `brain.scaling.update(...)` computes the skill rating from the person's recent Scaling games; the rating is printed and later written as the trace's first line `{"t": 0, "scaling": ...}`.
2. **Map and reader.** `brain.maps.PVP = True` (simulator-only jumps wait for a real landing). `MAP = get_map(--map)`. The reader class is chosen per game; `FIREFIGHT` is read from it.
3. **Forge map variants.** On Reach (not Firefight) and on Halo 4 / H2A Forge canvases, `brain.forge.live_pieces(live)` reads the placed pieces, and `brain.variants.identify` maps them to a variant folder under the base map. If the variant is new or its layout changed and it is not a built-in map's variant, `variant_strategy.build` makes its `callouts.json` and `positions.json` first. The variant's map data (its own nav from its pieces, its shields, its nav window) replaces the base map's.
4. **Terrain.** `T = brain.maps.terrain(MAP)`: the nav, line-of-sight and vehicle grounds.
5. **Loadouts.** A `Palette` is made where the reader has `LOADOUT` (Reach, Halo 4, H2A).
6. **Button map.** `decoded_buttons(game)` reads `maps/_inputs/<game>.json` (written by `tools/decode_buttons.py`) into `[(game, button, offset, mask, press_only)]` and `botctl.set_button_map` writes it into shared memory. Only decoded buttons reach the game; nothing is guessed.
7. **Map objects for names.** H2 and later get `live.set_map(MAP["objects"])`: Halo 3 and Reach name loose weapons by the map placement they lie on.
8. **Watchers and learners.** `lidar.HumanWatch` (people's floor, deaths, jumps into the map's LiDAR data), `lidar.RideWatch` (everyone's drives and flights into `rides.json`), `crouch_key.crouch_held(live.g.pid)` (falls back to "never crouched" if it fails), `collector.Collector` when `--collect on` (file `logs/collect_<map>_<stamp>.jsonl`, stamp taken from the trace name so the pair can be matched), `brain.stations.Stations` (H3, Reach, H4, H2A), `brain.oob.Oob` (out of bounds spots; known spots go into the terrain with `T.set_oob`), Reach Invasion layout and honor-system spawns (`brain.invasion`), the objective-mode watcher (`brain.modes`), and on a map variant (not Firefight) a `brain.forge.PieceWatch` over the pieces the nav was built with and the variant's known `dynamic` pieces.

#### The snapshot (`snapshot`)

`snapshot(live, now, prev, bot_ids, crouch, person_crouch)` turns raw reader output into a `brain.core.Snapshot`:

- **Players.** One `PlayerState` per player: position, velocity (difference to the previous tick times `HZ`), yaw and pitch from the aim vector, alive, shield, health, weapon, weapons carried, ammunition and magazines, vehicle, carrying the objective, bot or person, crouching (a bot from its last command; the first person from `person_crouch`), equipment and whether its ability is on, motion tracker setting, and a short camo window when active camo is on. A position that is not three finite numbers within 100,000 units is replaced by the previous good one (a mid-change read once produced a huge belief that exhausted memory).
- **Ability guard.** `ability_misread` turns off, for the rest of the match, the on-state of an ability kind that any player shows running longer than it can (`ABILITY_MAX_ON`, the tag's duration plus 3 s). Only that kind's on-state is cleared; the equipment names stay.
- **Flags.** Only in CTF (variant engine 1). On Forge canvases without known stands, `brain.modes.stands_by_spawn` assigns the loose flags to the team that spawned nearest. Stands riding vehicles (`live.live_stands`, Halo 3 Sandtrap) update `MAP["flags"]` and `returns`. Each flag becomes a `FlagState` (home within 1 unit of its stand, carried, or dropped).
- **Vehicles.** Objects of type 1. A vehicle whose parent field (`PARENT_AT`, default `+0x14`) names another vehicle is a turret riding on it: its riders count as riders of the carrier (`turret`, `gunner_seat`), and it is not listed on its own. Each listed vehicle carries `handle`, `kind` (`brain.vehicles.variant` from its name and the turrets riding it), `pos`, `occupied`, `riders`, `team`, `fwd` and `up` vectors (`vehicle_fwd`: from `ORIENT_AT` where known, else the vectors after the position, the up vector accepted only if it is a unit vector square to the facing), `gunner`, `turrets`, `manned`, `dead` (a wreck) and `left` (body health). Empty vehicles that are upside down or wrecked are dropped (`brain.vehicles.usable`). A rider's position and velocity are taken from the vehicle (the raw biped position is relative to the seat).
- **Loose weapons.** From `live.ground_weapons()` or, on Halo 3 and Reach, from objects of type 2 named by their placement.
- **Shieldless matches.** `snap.shieldless` is set when every living player has read 0 shield for 3 s.
- **Honks.** A person who stops a vehicle within 8 units of a teammate bot on foot for 1.5 s is treated as honking (the horn key is not decoded); `brain.director` reads `snap.honks`.
- **Score.** `live.match_state(raw)` twice a second, kept only if the numbers are sane (memory is reused at the end of a match). Where team scores are not decoded, deaths are tallied as the other team's points.
- **Modes.** Firefight adds the Covenant AI units as enemy players named `ai` and sets mode `firefight`. Engine 4 reads the King hill (`king_hill`), engine 3 the oddball (`balls`), which also marks its carrier as carrying the objective. Otherwise the mode is `ctf` when flags were found, else `slayer`; the Invasion and mode watchers refine it later in the tick.

#### One tick of the loop

The loop runs until `seconds` have passed. Each pass, inside a `try`:

1. **Clock.** `now` is the real time since start minus the time spent paused; while a pause is under way the clock is frozen at the pause start.
2. **botcore status** (`botctl.status`): driven bots (slot to player index), game tick count, faults.
3. **Crouch.** `botctl.owner_crouch(m)` (H2A and Halo 4 decode player 0's own crouch bit from botcore's copy of his action), else the crouch key reader.
4. **Snapshot** as above.
5. **Pause detection.** If the game tick count has not moved for `PAUSE_TICKS` passes, the pause starts; when it moves again, the paused time is added to `paused` and `now` is recomputed. Nothing reads as stuck or timed out because of a pause.
6. **Bug reports.** Once a second `bug_reports.attach_new(...)` files any F9 report saved since the brain started into this match's folder (it runs even while paused, because reports are written from the pause menu).
7. If paused: sleep one tick and continue.
8. **Out of bounds.** `oob.watch` gets every player's id, team, place, alive, health, shield and ride health (`ride_health`); deaths nobody caused become soft walls for the nav (`T.set_oob`), saved at most every 30 s.
9. **Stations** (H3, Reach, H4, H2A): `stations.watch` every tick (teleports taken), `stations.update(station_scan(...))` every 2 s, `save` every 30 s; any failure turns stations off for the match.
10. **Invasion** (Reach, not Firefight): every 5 s, on every map, `live.invasion()` decides whether the variant is Invasion. On a map whose scenario has an Invasion setup a `brain.invasion.Watch` is made or dropped (dropping clears its barriers from the nav). On a map without one (a Forge map variant's Invasion, such as one on Tempest, whose objectives are the variant's labelled objects, not read yet; see `tools/forge_label_probe.py`) the loop prints once that the bots play it as Slayer and writes an `invasion_unread` line to the trace. While it runs, `spawn_check` picks each dead bot's respawn point by the honor system and sends it with `botctl.spawn_at` (botcore moves the next unit there). Picks are made only when the sides are known and half the players are alive; a pick next to a teammate is refreshed every half second; a pick at a spawn kept for a vehicle gives the bot that vehicle as an errand for 30 s; a pick no longer valid is called off by sending NaN; new picks are written to the trace as `spawn` lines.
11. **Other objective modes** (Reach, H3, H4, H2A, H2, not Firefight): every 5 s `brain.modes.mode_of` reads the game type; Territories, Assault, Stockpile, Headhunter and Infection get a `brain.modes.Watch` that updates the snapshot each tick. Then, on a map variant, every 2 s the `PieceWatch` gets a fresh `brain.forge.live_pieces(live)` read: pieces that stood up after the nav was built become walls while they stand, and pieces of the nav that went are added to the variant's `variant.json` `dynamic` list (`brain.variants.save`) so the next match's nav leaves them out. Changes are printed; any failure turns the watch off for the match.
12. **People and rides.** `HumanWatch.update` with every person's place, alive, crouch (player 0 only), jump pressed (player 0 only, `botctl.owner_jumping`) and riding; `RideWatch.update` with the vehicles and players. When a background ride save finished with new data, the new ride layers are added to the terrain on the main thread (`T.add_rides`).
13. **Nav window.** On a Forge variant with a nav window, `brain.maps.grow` widens the window as players near its edge (checked every second) and `brain.maps.swap` installs the grown nav when it is ready.
14. **Crosshairs.** For the collector and the trace, each person's crosshair target and seat (`brain.tracefmt.crosshair`, `seat_of`).
15. **Collector.** `collector.tick(now, players, zoom, aims)`; on any error it is closed and turned off for the match.
16. **Events.** `events()` credits deaths and shield cracks to directors (live play does not see the shooter: the bot that was fighting that player gets the credit; a dying bot's killer is its fight target or its nearest belief). `flag_events()` is the announcer: flag taken, dropped, returned, and a carried flag that turns up home as a capture.
17. **New bots.** For each slot botcore drives whose player has no `Bot` yet: tier and style from the roster row by name, else from the lists; the profile from `brain.scaling.profile` (Scaling) or `brain.profiles.make_profile`. The `Bot` gets `side = team % 2` (map knowledge is red and blue), `game_team`, `liked` loadout guns, and capability flags: `can_pickup` (CE, H2, H3, Reach), `can_melee` (CE or melee decoded), `kit.pressable` (equipment decoded), `kit.sprint_ok` (sprint decoded, or Halo 4 where botcore sprints itself), `kit.decoys_listed = False`, `kit.unread` (the ability kinds the guard turned off). A `meta` line goes to the trace.
18. **Directors.** `regroup` keeps one `brain.director.Director` per `director_key`: the game team in team games; in free for all one per bot, except where `brain.modes` splits the match into two sides (Infection survivors and infected, Juggernaut hunters and the Juggernaut), which get one director per side. A director is rebuilt when its members change. Each director's `update(now, snap)` runs, and its new callouts go to the trace as `call` lines (`call_lines`, each once).
19. **Reach name dump.** Once, 20 s after the first bot appears, `reach_name_dump` writes `logs/reach_names.txt` (read only, a diagnostic for where names and service tags live).
20. **World line.** Four times a second when tracing: mode, score, limit, time left, botcore's tick count and fault counter, each director's posture, blitz rows, who reads as crouched, the `world` rows (`brain.tracefmt.Everyone.rows`: id, team, alive, x y z, shield, health, bot, flag, yaw, pitch, seconds still, formed-up teammates, enemy in sights, and for people crosshair and ride), deployed equipment, objective zones and items, flags, hill, ball, Invasion state and the vehicle rows `[handle, kind, x, y, z, riders, team, up z, health left, wreck]`.
21. **Saves.** Once a minute `save_learned(MAP)` (learned sight-line blocks and walk blocks) and, on a background thread, `save_lidar()` (rides and people's LiDAR, each in its own `try`).
22. **Power items.** Twice a second `item_check`: when a team's bot is within 25 units of a power item's spawn and nothing of that kind lies there, the team's director starts that item's respawn timer (`item_taken`).
23. **Loadouts** (Reach, H4, H2A): `loadout_check` learns each slot's guns from what bots spawn with, records how each life ended (`record_death`), and while a bot waits to respawn asks for the slot that answers its recurring problem (`want_slot`) through `botctl.set_loadout`. A refusal turns loadouts off (an old botcore). Requests go to the trace as `loadout` lines.
24. **Thinking.** `dt = think_dt(...)`. For each living bot: `a = b.think(now, dt, snap, T.los, nav, director.callouts, director.item_up)`, where `nav` wraps `T.nav` to remember the waypoint. The bot's reports are passed to its director, and `botctl.act(slot, a.forward, a.strafe, a.yaw, a.pitch, buttons(a))` writes the action. A bot whose crouch can reach the game is remembered as crouching for the next snapshot.
25. **Console.** Callouts are printed unless `--quiet` (or with `--callouts`); without `--quiet` a status line per bot every 2 s.
26. **Rate.** Sleep the rest of 1/30 s.

#### The `bot` and `think` trace lines

Per bot per tick: `t`, `id`, `pos`, `yaw`, `pitch`, `goal` and `arg` (cut to 60 characters), `veh`, `wpn`, `wp` (next waypoint), `foes` (`[id, shield, health]` of every enemy), `cmd` (`[forward, strafe, yaw, buttons, pitch]`), and when present `seat`, `turret`, `fx` (fight state), `att` (what it looks at and why), `notes` (overrides), `jw` (a planned jump's window: seconds left and landing), `eq` (equipment and on), `inv` (weapons carried), `hp` (shield, health), `uz` (the game's own zoom byte where `UNIT_ZOOM` is known, next to the zoom asked in the command bits), `ammo` and `mag`. When `b.next_decide` changed this tick the bot decided, and `brain.tracefmt.think_line` writes the `think` line: its top six scores, the choice, the flags behind it, the director order, posture and beliefs.

#### Button packing (`buttons`)

`buttons(a)` turns a `brain` action into botcore's 32-bit command word: bit 0 fire, 1 jump, 2 crouch, 3 grenade, 4 melee, 5 action (use), 6 reload, 7 equipment (only when the ability is not a hold-mode one), 11 sprint, bits 8-10 weapon slot plus one, bits 12-13 zoom level, bits 14-17 seat plus one, bit 18 turret, bits 19-20 vertical input (1 strong up, 3 up, 2 down: flying), bit 21 the vehicle's second input, bit 22 weapon cycle, bit 23 the held bit of a hold-mode ability. The bit names match `botctl.BTN` and `native/shared.h`.

#### Error handling and shutdown

Any exception in a tick is counted; each distinct error is printed once with a short traceback. After 90 consecutive failed ticks (about 3 s) the brain decides the game is gone and stops. The `finally` block always: saves learned nav data and LiDAR data, runs `wedges.prune` for the base map (nodrive cells people drove over come out), saves stations and out-of-bounds data, flushes the trace and copies the whole recording into its bug-report folder (`bug_reports.finish`), closes the collector, and sends every bot a zero action at its last yaw so it stands still. In practice botcore often terminates the whole process tree when the match ends, which is why the per-minute saves exist.

#### Connections

`brain.core` (Vec, PlayerState, Snapshot, FlagState), `brain.live` (readers), `brain.maps` (map data, terrain, learned data, nav window), `brain.bot.Bot`, `brain.director.Director`, `brain.vehicles`, `brain.loadouts`, `brain.profiles`, `brain.scaling`, `brain.invasion`, `brain.modes`, `brain.stations`, `brain.oob`, `brain.forge` and `brain.variants`, `brain.tracefmt`; in tools: `botctl`, `lidar` (HumanWatch, RideWatch), `crouch_key`, `collector`, `bug_reports`, `variant_strategy`, `wedges`.

### `tools/botctl.py`

**Purpose.** The Python side of botcore's shared memory block. Every Python process that talks to botcore (play.py, live_bots.py, lidar.py, escort_bots.py, device_probe.py) uses it.

**The block.** `shm()` opens `mmap.mmap(-1, SIZE, tagname=NAME)`, where `NAME` is parsed from `HB_SHM_NAME` in `native/shared.h`. `SIZE` is 3622 bytes (version 13 of the layout). Offsets used here:

| Offset | Field |
|---|---|
| 0 | magic, version, dll_alive, brain, game_tick (5 x u32) |
| 20 (`OFF_BOTS`) | bot_player_index[16] (i32, -1 free): slot to player index |
| 84 (`OFF_ACTIONS`) | 16 actions of 24 bytes: forward, strafe, yaw, pitch (f32), buttons, seq (u32) |
| 468 (`OFF_STATUS`) | status text (256 bytes) |
| 724 (`OFF_CMD`) | cmd, cmd_seq, cmd_done_seq (u32), cmd_arg (i32), result (i64), fault (u32) |
| 752 (`OFF_SETTINGS`) | Bots tab settings: enabled, red, blue, difficulty, seq |
| 772 (`OFF_NAME`) | the next bot's name (UTF-16, 15 characters) |
| 804 (`OFF_GAME`) | which game ticks (1-7), then a debug seq and a 256-byte copy of player 0's action (`OFF_DBG`) |
| 2360 (`OFF_NOTICE`) | notice seq and a 128-byte "TITLE\|line" text |
| 2492 (`OFF_BTN_MAP`) | button map seq and 32 entries of 16 bytes |
| 3008 (`OFF_LOOK`) | look game and offset, 64 value bytes, 64 mask bytes |
| 3144 / 3160 | clan tag (UTF-16, 7 characters), emblem (5 x u16) |
| 3170 (`OFF_SPAWN`) | 16 respawn points (x, y, z, yaw), 16 seqs, 16 done counters |
| 3554 (`OFF_CHAT`) | chat seq and 64 bytes of the person's chat line |

Publishing is always "write the data, bump the sequence number last", so botcore never reads half a command.

**Functions.**
- `status(m)`: magic, version, dll_alive, game_tick, status text, driven bots, command fields.
- `command(m, cmd, arg, timeout=5)`: writes cmd and arg, bumps `cmd_seq`, polls until botcore's `cmd_done_seq` matches, returns the status (or `timeout=True`). Commands: `CMD_ADD_BOT` 1, `CMD_ADOPT` 2, `CMD_SET_TEAM` 3, `CMD_SET_LOADOUT` 4. The argument packs machine or player index, team or slot `<< 8`, and a per-game bit (`GAME_BIT`: H2 bit 24 up to H4 bit 29) so each game's hook takes only its own.
- `add_bot(m, machine, team, name, game, look, clan, emblem)`: writes name, clan tag, emblem and the look block, then sends `CMD_ADD_BOT`. A look is either `(offset, {byte: value})` laid over the player configuration, or `("roll", seed, slot mask[, none mask[, effect[, extra bytes]]])` with the `LOOK_ROLL` flag: the armor is drawn from the game's own Armory by botcore.
- `act(m, slot, forward, strafe, yaw, pitch, buttons)`: one action for a bot slot.
- `set_button_map(m, entries)`, `set_loadout(m, index, slot, game)`, `spawn_at(m, index, x, y, z, yaw)` (Reach respawn placement; NaN calls a pick off), `notice(m, title, line)` (a notice drawn over the game by botcore's overlay).
- `settings(m)`, `roster(path)` (the `bot=<team>,<tier>,<style>,<name>` lines of `botcore.ini`; None if the file has no `roster=` line), `setting(path, key, default)`.
- `owner_crouch(m)` and `owner_jumping(m)`: H2A and Halo 4 only, from bits of the copied player 0 action at `OFF_DBG + 0x08` (crouch bit 0 alone; jump bit 1); None elsewhere or when the copy is older than 0.5 s.
- `player_cap(game, firefight)`, `MAX_PLAYERS = 16`, `FIREFIGHT_PLAYERS = 4`.
- `injector(root, restore)`: returns `native/bin/inject.exe`; if it is missing, tries `git checkout` of that file (developer copies), then building `inject.cpp` with Visual Studio's `vcvars` (`brain.paths.vcvars()`), else prints how to restore it from Windows Security and returns None.

**CLI.** `status` (also measures ticks per second), `add_bot [machine] [team]`, `set_team <index> <team>`, `adopt <index>`, `set_loadout <index> <slot> <game>`, `act <slot> <fwd> <strafe> <yaw> <pitch> [buttons] [seconds]` (holds the action, then stops).

### `tools/memread.py`

Read-only access to MCC's memory with ctypes; it never writes to the game.

- `find_pid(name)`: enumerates processes with psapi.
- `refuse_if_anticheat()`: exits if any Easy Anti-Cheat process runs.
- `Game(dll=None)`: opens `MCC-Win64-Shipping.exe` with `PROCESS_VM_READ | PROCESS_QUERY_INFORMATION`, finds the base of the game DLL (`halo1.dll` by default, or `HB_GAME_DLL`). Methods: `module(name)`, `read(addr, n)`, `u64(addr)`, `regions()` (committed read-write regions under 1 GB).
- `data_arrays(g)`: scans memory for Blam "data array" headers (signature `d@t@`) with a plausible name before them and reports name, max count, element size and address. This is how tables such as `players` and `objects` are located without static reverse engineering.
- CLI: `arrays`, `players` (also dumps the players header), `hcm` (reads known HaloCheckpointManager pointers for MCC 1.3528 Halo 1).

`brain/live.py` readers are built on `Game`; `play.py` uses `find_pid` and `PROCESS`.

### `tools/tls.py`

Halo 3, Reach and later keep engine globals in thread-local storage. `tls_index(g)` reads the DLL's `_tls_index` from the loaded image's PE TLS directory; `blocks(g)` walks every MCC thread (Toolhelp thread snapshot), reads each thread's TEB with `NtQueryInformationThread`, follows `TEB+0x58` (ThreadLocalStoragePointer) and returns `[(thread id, block address)]` for that DLL. CLI: `python -I tls.py <dll> [hex values ...]` prints each block and where the given 64-bit values occur in its first 4 KB. Read only; a research tool behind the readers.

### `tools/device_probe.py`

A developer probe for map devices on Halo 2 Anniversary and Halo 4 (switches, doors, bridges, shoot-to-open gates). It expects a match started through the test override with `brain: none`, so `play.py` adds bots and leaves them idle.

- `list [dll]`: objects by type, and for each door, control, lift, launcher or shield in `maps/<map>/features.json` the nearest live object.
- `watch <seconds> [dll]`: objects (not bipeds or weapons) that moved more than 0.05 units.
- `shoot <x> <y> <z> [--from x y] [--seconds 8] [--map NAME] [dll]`: bot slot 0 walks to `--from` by the nav, aims at the point from eye height and fires in bursts, then prints what moved.

Default DLL `groundhog.dll`, default map `h2a_ca_zanzibar`. Uses `LiveH4F`, `botctl` and `brain.maps`.

### `tools/forge_label_probe.py`

A developer probe for Invasion on a Halo: Reach Forge map variant. The mod knows Invasion's objectives, respawn zones and gates only from a built-in map's scenario (`brain/invasion.py layout`); on a Forge map they are the variant's own objects, identified by Forge labels the mod does not read yet, so `live_bots.py` plays such a match as Slayer. This probe gathers what is needed to find where Reach keeps those labels. It only reads MCC's memory: it never writes it and sends no input.

Run it on the host's PC in a Forge variant's Invasion match after the round has started: `python -I tools\forge_label_probe.py [tag]` (the tag defaults to the date and time). It writes `logs/forge_label_probe_<tag>.json` with:

- `map` and `variant`: the map name, the game variant's name, its engine icon (game globals +0x1524) and its teams flag.
- `objects`: every live object (handle, type, tag id, tag name from `brain/forge._tag_names`, position, address and its first 0x300 bytes in hex).
- `strings`: every `inv_` text, ASCII or UTF-16 in any case, in the game globals and anywhere in writable memory (up to 400).
- `pos_hits`: for up to 24 marker-like objects (`MARKERS`: respawn zones and points, hill beacons, capture plates, flag stands, the core and bomb and similar), every other place in writable memory that holds the object's exact position (up to 40 each, the objects themselves skipped), with 0x80 bytes either side; the variant's record of the object (label, team, shape) should be one of them.
- `arrays`: the engine's named data arrays (`memread.data_arrays`).

It prints a short summary as it goes. Uses `LiveReach`, `brain.forge` and `memread`.

### `tools/crouch_key.py`

The games other than H2A and Halo 4 do not expose the person's stance, so bots would aim at a crouched person's standing head height. `crouch_held(pid)` returns a function that is True while a key bound to crouch is held and MCC owns the foreground window. The bound keys come from MCC's `GameUserSettings.ini` (`%LOCALAPPDATA%\..\LocalLow\MCC\Saved\Config\WindowsNoEditor`), every `AbstractButton=9` entry of the keyboard mappings (`crouch_keys`), defaulting to Left Ctrl (162). It uses `GetAsyncKeyState` for those keys only, keeps nothing and sends nothing; keyboard only, a controller's crouch is not read. `python -I crouch_key.py` runs a self-check. Used by `live_bots.py`.

### `tools/escort_bots.py`

**Purpose.** ODST Firefight teammates on maps without exported map data (the mod kit does not export the collision geometry of ODST's Firefight areas). `play.py` runs it for ODST when `maps/<map>/heightmap.npz` is missing.

**How it works.** The loop runs at 30 Hz with `LiveODST`. It keeps a trail of the person's (player 0's) positions, one point every 0.75 units, up to 600 points; the trail is always walkable because the person walked it. Each driven bot is an `Escort`:
- **Moving.** When farther than 6 units from the person (9 while it has a target) it walks the trail point by point, rejoining at the nearest point after a respawn; otherwise it holds.
- **Fighting.** It targets the nearest Covenant unit within 28 units (`live.ai_units`), preferring its current target, and after its tier's reaction time (`TIERS`: novice 0.45 s and 0.06 rad error, average 0.30 / 0.035, strong 0.22 / 0.02, top 0.15 / 0.012) aims at chest height with a simple lead, a fresh Gaussian aim error every half second, fires in bursts and strafes. A target that took no damage over 45 firing ticks is banned for 5 s (out of sight behind cover).
- **Unsticking.** Pushing without moving for 1 s gives a jump and a random sidestep for 0.6 s.
- **Idle.** It looks where the person looks.

It logs one JSON row per bot per tick to `logs/escort_<game>.jsonl` and prints a score at the end (`score()`: fire ticks, ticks that hurt the target, likely kills, median distance to the person, stuck share). `--selftest` checks walking, holding and reaction delay.

### `tools/carnage_names.py`

MCC fills its post-game carnage report (`mpcarnagereport1_3528_0_0.xml` in `LocalLow\MCC\Temporary`) from its own records by Xbox id, so a bot's made-up id (`0xB07B07B0` followed by its player index) can come out with a blank name, a default clan tag and team 0. `fix(xml, bots, clan_of)` rewrites only rows MCC left blank (`mGamertagText=""`): gamertag, clan tag (`brain.looks.clan_of`), service tag (`bot_tag`, the same rule as botcore's `hr_bot_tag`: capitals and digits, up to 4, topped up to 3 letters) and team, all from the trace's `meta` lines (`bots_of`). Rows botcore's in-match hooks already named are left alone. `--wait S` waits for a report newer than the trace. A running MCC keeps its in-memory copy, so the fix shows after MCC restarts. Run by `play.py` after a Reach match.

### `tools/power_positions.py`

Scores power positions per map and writes `maps/<map>/positions.json`, which the director's Slayer roles hold and rotate between (`brain/director.py`).

`positions(m, T, top=8, spacing=9, cand_max=2500, samples=90)`: takes the reachable walkable nav cells, up to `cand_max` candidates, and samples floor points (weighted by `traffic`: where people walked, from LiDAR `walk` rows of kind 1 in `lidar.json`, when any exist). Each candidate's score is `0.5 * visibility` (sampled points within 45 units in line of sight) `+ 0.3 * height` over the median floor within 15 units (clipped -2 to 8) `+ 0.2` if a power item with value 0.7 or more is within 15 units, `+ 0.25` if it is on a Forge layout's own piece; all terms normalised. The best candidates at least `spacing` apart are kept, each with a `duck` flag (a floor point within 3 units that sees less than half of what this spot sees) worth 0.1 extra. Output rows: `pos`, `score`, `sees`, `height`, `duck`. CLI: `python -I power_positions.py [maps...] [--top 8] [--spacing 9]` (default every map with a heightmap). Also used by `variant_strategy.py`.

### `tools/variant_strategy.py`

A Forge map variant (a layout of placed pieces filed under its base map by `brain/variants.py`) needs its own callouts and power positions; the base canvas's would send bots to empty ground. `build(name)` loads the variant, builds its nav fresh (`brain.maps._build` over its window), runs `power_positions.positions` (smaller candidate and sample counts), and writes into the variant folder:
- `positions.json`.
- `callouts.json`: zones named after structures (`structures()`: building pieces, not `mp_*` game-type objects, with more than 5 faces, grouped in 12-unit squares and named by the most telling word in `WORDS`, e.g. Tower, Room, Bunker, prefixed by a compass direction when the word repeats), three area zones across the nav window (West side / Mid / East side or South / Mid / North by the window's long axis), a `mid` point (the reachable node nearest the centre of the layout's own pieces), `mid_hill`, holds for both teams (the top four positions) and lanes.

It stores the layout hash (`layout_hash`, SHA-1 of the objects) as `strategy_of` in `variant.json`; `stale(name)` is True when the files are missing or the layout changed. `live_bots.py` calls `stale` and `build` when it identifies a variant. CLI: `python -I variant_strategy.py <variant> [...]`.

### `tools/scaling_view.py`

Run by botcore when the BOTS panel opens (`native/bots_panel.cpp`), with `botcore.ini` and the Advanced tab's `scaling.ini`. It calls `play.keep_carnage` on the timestamped traces (so the last match's post-game report is kept now rather than at the next match start), then `brain.scaling.update(...)` with the panel's games window and settings, which counts any new Scaling game and writes `logs/scaling_view.txt` for the panel's hover box. Prints the number of games and the rating.

### `tools/wedges.py`

Learns where bot drivers wedge ground vehicles and keeps the vehicle nav out of those spots.

- `learn(paths, name)`: reads `bot` lines with `"seat": "driver"` from traces, takes the vehicle kind from the world lines, and only ground or hover vehicles (`brain.vehicles.spec`). A sample is a half-second step with throttle above 0.3 and a speed under `min(1, 0.15 * the vehicle's speed)`. Samples within 1.5 units merge; a spot counts with at least 6 samples over at least two separate stops (another bot, or the same bot 20 s later), not within 3 units of a vehicle spawn. Around each spot, half-unit cells within 2.5 units (`WEDGE_R`) that no person drove over (`driven()`: `rides.json` drive rows with a person's count) become `nodrive` cells.
- `keep_routes(...)`: keeps a spot's cut only if every pad-to-pad drive between the map's ground vehicle spawns that arrived before still arrives (each drive simulated with `T.vnav`).
- `prune(name)`: removes saved nodrive cells people have since driven over; `live_bots.py` calls it at the end of every match.
- Output `maps/<map>/wedges.json`: `{"wedges": [[x, y, z, samples]], "nodrive": [[x, y, z]], "note"}`, merged with earlier data. `brain/maps.py` hands it to `Terrain._build_vnav`; the walking ground is never cut.
- CLI: `python -I wedges.py <map> [trace ...]` (default every `logs/trace_<map>_*.jsonl`), `--prune`.

### `tools/roofless.py`

Draws a map's level mesh (`maps/<map>/source/bsp.obj`) from straight above with everything over a cut height left out, so every storey can be seen and painted.

- `build(name, px=12)`: loads the mesh, the play area (`heightmap.play_area`) and the walkable floors (`heightmap.npz` `floors`). Cuts run one unit apart from 1.6 units (`CUT_HEAD`) over the lowest walkable floor (1st percentile) to the highest (99th), plus a final view with everything. Writes `maps/<map>/roofless/level_<k>.png` and `maps/<map>/roofless.json` `{map, x0, y0, x1, y1, px, levels: [{z, cut, png}]}`, where pixel (i, j) is world `(x0 + i/px, y1 - j/px)`.
- `draw(...)`: rasterises faces with PIL in height order, keeping upward faces wholly under the cut and steep faces (walls) for their part under it; ceilings are never drawn. Each pixel's height is solved on its face's plane (ramps stay smooth). Colour comes from a seven-step ramp (blue to pale) by the share of walkable floor below that height in the full view, or over the 6 units under the cut in a cut view (deeper floors dimmed); walls are darker; contour lines every unit (half a unit in cut views) and ledges of 0.6 units or more are outlined near-white on the higher side.
- `levels_of(lz, walk)`: groups floor heights into levels (kept for reference; `build` steps by cut height instead, since floors joined by ramps never split).
- CLI: `python -I roofless.py <map> [--px 12]`, `--selftest`. The nav painter calls `build` through `/api/build`.

### `tools/jumpphys.py`

Per-game movement physics over the level data, used by LiDAR bots to call safe jumps and by the simulator to move its bots.

- `PHYS[game] = (run speed, jump speed, gravity, lethal fall height)` in world units and seconds. Gravity and jump speed were measured from arcs in real match traces; run speed comes from the kits' player globals; lethal falls for CE, H2, H3 and ODST from "harmful falling distance", for Reach, H4 and H2A inferred from the maximum hard-landing speed (marked as such in the source).
- `game_of(map_name)`: the game from the map folder prefix (`h2a_`, `h2_`, `h3_`, `reach_`, `odst_`, `h4_`, else CE).
- `Phys(game, apex=None)`: run, v0, g, lethal, `apex` (jump height) and `lethal_v`; a map's measured apex (from 20 or more LiDAR jumps) replaces the jump speed.
- `reach(ph, dz)`: how far a full-speed running jump carries before coming down `dz` higher.
- `walk_step(T, p, x, y)`: one walking step under the nav's own body and step rules (`brain.terrain.BODY`, `MAX_RISE`, `STEP_DOWN` 0.25): `ok` with the new position (heights smoothed across cells so ramps do not read as stairs), `off` into the air, or `blocked`.
- `air_step(T, ph, p, v, dt)`: gravity, faces at 0.45 and 0.65 units above the feet stop sideways motion, a slab overhead stops the rise, crossing a floor lands; returns `air`, `land` with impact speed, or `void`.
- `fly(T, ph, p, vx, vy, vz=None)`: a whole jump; `prepare(T)` caches the lowest floor for void detection.

### `tools/bug_reports.py`

**Purpose.** Files the in-game bug reports the person writes (F9 in a match, or "Report bot bug" in the pause menu) together with the match recording, and lists them.

**Flow.** botcore's overlay (`native/overlay.cpp`) saves `logs/bug_reports/<YYYYMMDD-HHMMSS>/report.json` with `{time, unix, title, how, description}`. About once a second the brain calls `attach_new(t0, now, snap, map, trace, trace_path, bots, critic_path, mode, stations, oob)`, which for each unfiled report newer than the brain's start:
- computes the match second it was saved at (`now - (time.time() - unix)`);
- records every player's id, name, team, bot or not, alive, position, vehicle, weapon, carrying, and for bots their goal, director order, tier and style, plus the map, mode and score;
- adds the stations nearest the person (`stations.near`) and turns the note into a station mark (`stations.mark`); if `brain/oob.py` reads the note as naming out of bounds (`oob.flag`), the spot becomes a soft wall and the entry gets `out_of_bounds`;
- writes a `{"t", "bug", "text"}` marker line into the trace;
- appends the entry to `logs/bug_reports/<match>/reports.json`, where `<match>` is the trace name without `trace_` and `.jsonl` (or `unrecorded_<time>` without a trace);
- brings `logs/bug_reports/<match>/trace.jsonl` up to date with `catch_up` (only the bytes added since the last copy are appended; a longer destination is replaced);
- deletes the single-report folder.

`finish(trace_path)` copies the rest of the recording at the end of the match when the match folder has reports. LiDAR runs pass no trace, so their entries carry a note that there is no recording. `_critique` and `critic_near` copy and read a director critic's notes (`critique.jsonl`, `critique.md` from `brain/critic.py`) when a critic path is given; the live loop currently passes None. `migrate()` converts the older one-folder-per-report layout.

**CLI.** No argument: every report, newest match first, with description, moment and an Observer link (`http://localhost:8799/?file=bug_reports/<match>/trace.jsonl&t=<t>`). `<stamp>`: that report in full, with every player and any critic lines within 90 s. `--migrate`.

### `tools/observer.py`

The Observer: a replay and live viewer for match traces, plus command-line queries. It is the main tool for understanding what the bots did and why.

#### Usage

```
python -I observer.py serve [--port 8799] [--open]    the page (default when no argument)
python -I observer.py at <trace> <t>                  every bot at time t
python -I observer.py bot <trace> <id> [t0 t1]        one bot's decisions over time
python -I observer.py events <trace> [t0 t1]          callouts, deaths, loadouts, coach lines, blitzes, vehicle in/out
python -I observer.py spawns <trace> [player id]      every respawn with Invasion side, phase and nearest flag
python -I observer.py you <trace> [player id]         the person's numbers (player_stats report)
python -I observer.py export <trace> [--keep-names]   one shareable zip
```

A trace argument can be a path or a name relative to `logs/`.

#### Finding traces

`trace_files()` collects, newest first, `logs/trace_*.jsonl`, `logs/evidence/*.jsonl`, `logs/sim_*.jsonl` (simulator traces), `logs/bug_reports/*/trace.jsonl`, `logs/qc_keep/*.jsonl` and `logs/imported/*/trace_*.jsonl`. Each entry has `file` (relative to `logs/`), `label`, `map`, `bytes`, `mtime` and `live` (written in the last `LIVE_S` = 15 s). Labels: `match_label` gives "Match <date time>, <difficulty>" from the timestamp and the bots' tiers in the first 400 lines (Easy, Normal, Heroic, Legendary or Mixed); `bug_label` gives "Bug reports <date>, n reports: <first description>"; imported games are prefixed "Imported:". `trace_map` reads the map from a `meta` line, else from the file name (trimmed until it matches a `maps/` folder). `safe_trace(rel)` accepts only paths that appear in this list, so the page cannot read arbitrary files.

#### Loading a trace (`Trace`)

`Trace(path)` reads every line and sorts it by kind: `meta` (bot id to name, team, tier, play style; the map), `world`, `think` (per bot), `call`, `coach` (lines from the team coach in `brain/coach.py`, except `sent`), `loadout`, and per-bot `bot` lines. Partial last lines are skipped. `Trace.at(rows, t)` is a bisect for the last row at or before `t`. `deaths()` derives deaths from alive-to-dead changes between world lines, ignoring ticks where half the players or more vanish at once (a match end).

#### Text output

- `describe_bot` and `cmd_at`: for each bot, position, facing in degrees and compass, pitch, weapon, shield and health, goal and argument, waypoint, inputs and FIRE, what it looks at (`att_text`, using `SOURCE` names for belief sources: seen, on radar, called out, shot us, radar static, promethean vision, a fake radar dot), how long it stood still and who it is formed up with (`squad_text`), its vehicle and seat, fight state, equipment, overrides of the last second, and its last decision (choice, order, posture, the weighed scores, the true flags, its beliefs). People get their position, facing, who is in their sights, crosshair and ride (`aim_text`). Then the callouts and deaths of the last 6 s and each team's latest applied coach play.
- `cmd_bot`: the bot's goal changes with the top three scores and flags, override counts, and deaths in the window.
- `cmd_events`: callouts, deaths, loadout requests, coach events, blitz changes per team, and vehicle boarding and exits with the seat, all in time order; then the most common goal switches.
- `cmd_spawns`: streams world lines to find respawns, naming the spawn from `maps/<map>/inv_spawns.json` (within 3.5 units this phase) or "ally #k" (within 1.6 units of a teammate), and the nearest Invasion respawn flag from `objects.json` (`inv_res_p1-3`), starred when it is the side's flag for the phase.

#### The map picture (`base`)

`base(map)` builds and caches `logs/observer_cache/<map>.png`, rebuilt when the heightmap or `lidar.json` is newer. The level's top surface is drawn dim and shaded by slope; floor any player can reach (the nav's highest reachable storey per cell, from `brain.maps.terrain`) is drawn as a teal height ramp with darker edges where the height steps a unit; LiDAR-walked cells are brightened, crouch cells drawn orange, and LiDAR floor the nav lacks is added. The image is flipped so north (+y) is up and scaled 2 to 6 times. The box around playable floor is cached as `<map>.play.json` so the page frames the play area, not the scenery. The answer also lists `callouts.json` zone polygons.

#### "You" numbers

`you_source(path)` prefers the Data collector file with the same stamp (`logs/collect_*_<stamp>.jsonl`), else the trace. `you_view(path)` runs `player_stats.page(player_stats.analyze(src))` and caches the JSON in `logs/observer_cache/you_<file>_<mtime>_<size>.json` once the source has not changed for 15 s (a live game is recomputed on request).

#### HTTP endpoints (`serve`)

| Method and path | Answer |
|---|---|
| `GET /`, `/index.html` | `observer.html` |
| `GET /traces` | `trace_files()` |
| `GET /maps` | map folders with a `heightmap.npz` |
| `GET /base?map=` | the map picture's metadata (`x0`, `y0`, `cell`, `w`, `h`, `img`, `zones`, `play`); 404 without level data or with a slash in the name |
| `GET /base.png?map=` | the cached picture |
| `GET /trace?file=&offset=&max=` | up to `max` bytes (default 8 MB) from `offset`, cut at the last newline; headers `X-Next-Offset` and `X-Size` |
| `GET /you?file=` | the "You" JSON (500 with the error if the analysis fails) |
| `GET /export?file=&names=0\|1` | the match zip as an attachment (`match_export.export`) |
| `POST /import` | an exported zip in the body (up to 1 GB), requires header `X-Observer: 1`; answers `{file}` of the imported trace or `{error}` |

The server binds `127.0.0.1` without address reuse and, with `--open`, opens the page in the app window. If the port is taken an Observer already runs (its window was closed): it opens a window on that one with `--open`, prints "Observer already running" and returns.

#### Connections

Reads traces written by `live_bots.py` (and the simulator in `brain/sim.py`), collector files, `maps/<map>/` data; imports `brain.maps` for the nav, `player_stats`, `match_export`, `appwindow`. `bug_reports.py` links into it with `?file=...&t=...&bot=...`.

### `tools/observer.html`

The Observer page: a canvas map with toggleable layers, a timeline, and side panels. Everything is drawn client-side from the raw trace lines.

- **Top bar.** Game picker (`/traces`, live games marked), Refresh list, Export game with a "Keep names" checkbox (downloads `/export`), Import game (a file picker that posts the zip to `/import` and adds it to the list), a map picker (`/maps`) to draw a different map under the game, and a help dialog.
- **Loading.** `loadTrace` resets state, then `pull()` fetches `/trace` chunks until the end, feeding each to `ingest()`, which sorts lines into world rows, per-bot series, think series (recording goal switches), callouts, coach lines and loadouts, and derives deaths. A live game (`info.live`) starts in "Follow live" mode and is polled every second for new bytes. The URL parameters `file`, `t` and `bot` open a game at a moment with a bot selected (used by bug report links). A game without `think` lines shows a banner that only positions, goals and facing were recorded.
- **Layers.** Map, Zones, Facing, Attention, Crosshairs, Squads, Goals, Beliefs, Callouts, Orders, Shots, Equipment, Vehicles, Trails, Labels, You (Orders and You start off). Team colours follow the games' order (red, blue, green, orange, purple, gold, brown, pink, then generated hues); goal lines are coloured by goal kind.
- **Panels.** You (the `/you` numbers, with a toggle for the You heat layer and a recompute button while the game is live), Players (everyone with health bars, attention, stillness and what each bot weighs), Selected bot (inspector: decision scores, "Because" flags as chips, fight state, overrides of the last 2 s, beliefs), Events near this moment.
- **Timeline.** Play and pause, speed, a range slider with tick marks, Follow live.
- **Keyboard and mouse.** Space play or pause, arrows step 0.5 s (Shift 5 s), comma and period 0.1 s, brackets change speed, 1-9 pick a bot, F follow the picked bot, L follow live, ? help; wheel zooms, drag pans, click picks a bot.

### `tools/player_stats.py`

Computes the person's numbers for a match and the same measures for every bot, so they can be compared side by side.

**Input.** A Data collector file (everyone 30 times a second, the person's guns, rounds and equipment) or, for older matches, a trace (world lines, 4 a second). `load(path)` returns the time base, a per-player array `[n, 12]` (team, alive, x, y, z, yaw, pitch, shield, health, riding, flag, bot; NaN where absent), the gear rows, meta and commands; key rows from old files are skipped. `companion_trace` finds the trace with the same stamp (in `logs/` or `logs/verify/traces/`) for the bots' names, tiers and trigger presses (`trace_extras`).

**Measures** (methods of `Match`, combined in `player()`):
- **Reaction** (`reactions`): an enemy enters line of sight inside a 105-degree view after 1 s unseen; time until the aim is on him (the tracefmt in-sights rule, aim point 0.35 above the feet from eye height 0.62) and, for the person, until the first shot; "pre-aimed" when already aimed there; not counted beyond 3 s.
- **Reaction to being shot** (`shot_reactions`): shields start dropping after 2 s untouched; time until the aim is on an enemy.
- **Pace** (`engagements`): engagements per minute alive (aim on an enemy, firing or being hit; closer than 3 s apart counts as one), their length, gaps, time from spawn to the first.
- **Movement** (`movement`): speed, time standing, jumps per minute, strafe in fights, 90th percentile speed.
- **Positioning** (`positioning`): time per callout zone, fight distance, height over the opponent, first look, share of time an enemy had the player in view.
- **Damage and accuracy** (`damage`): share of trigger time on the body, damage dealt (full shield plus body = 2.0), kills.
- **Deaths** and **gear** (`gear_report`, the person only): time per gun, switches, pickups, shots, ability uses. The person's shots are told by the magazine of the gun in hand going down with the same guns carried (`shot_times`); no key is read.

`analyze(path, who)` returns players, a summary table (`summary()` per player), per-tier aggregates, and for the person a heat map (2-unit cells, seconds spent) and where fights began. `page(a)` trims that to what the Observer's You section shows; `report(a)` formats text. CLI: `python -I player_stats.py <collect or trace file> [player id]`.

### `tools/objective_report.py`

Reads a trace's world, think and meta lines and reports objective play:
- **CTF** (`ctf`): every flag run (carrier, length, how it ended: captured, killed, dropped), teammates within 10 units of the carrier, players within 15 units hunting an enemy carrier, defenders within 12 units of home when the flag was pulled.
- **King of the Hill** (`king`): time on the hill per team. **Oddball** (`oddball`): time with the ball, guards around the carrier.
- **Roles** (`roles`): each bot's director orders over time; **Goals**: each team's share of bot ticks per goal.

Flag stands come from `brain.maps.get_map`. `report(path)` returns the lines. CLI: `python -I objective_report.py [trace] [--save]` (default the newest `logs/trace_*.jsonl`; `--save` writes `logs/verify/objective_<trace>.txt`). Also run by `match_export.py`.

### `tools/match_export.py`

**Export** (`export(trace, out, keep_names)`). Collects the match's files (`match_files`): the trace, the collector file with the same stamp, and MCC's carnage report if its time is between 2 minutes before and 10 minutes after the trace's last write (campaign reports excluded). `summary(trace)` reads the game, map, modes, final score, limit, length and every player marked `human` or `bot` (bots with name, difficulty and play style; people as "Player 1", "Player 2"). It runs `objective_report.report` and `player_stats` as analyses (failures are recorded, not fatal). The zip `logs/exports/match_<map>_<stamp>[_names].zip` contains `manifest.json` (format version, mod version from git, match summary, players, file sizes and sources, the row formats from `FORMATS`, what was removed for privacy, analysis errors), `README.txt`, `trace.jsonl`, `collect.jsonl` (passed through `collector.without_keys`), `carnage_report.xml` (scrubbed by `scrub_carnage`), `objective_report.txt` and `player_stats.json`. Privacy: Xbox user ids are always removed; people's gamertags, clan tags and service tags become "Player n" unless `keep_names`; the Windows user folder in paths becomes `<home>`. The zip is written to a `.part` file and renamed when complete.

**Import** (`import_game(data, logs)`). Accepts only a zip containing `manifest.json` and `trace.jsonl`, unpacked size at most 2 GB, and extracts only the known part names (`IMPORT_PARTS`) into `logs/imported/<map>_<stamp>[_n]/`, the trace renamed `trace_<map>_<stamp>.jsonl` so the Observer lists it. The map name is sanitised to `[A-Za-z0-9_]` and the stamp must match `YYYYMMDD-HHMMSS`. Raises `ValueError` for anything else.

**CLI.** `python -I match_export.py <trace or stamp> [--keep-names] [--out zip]`, `--list`. A self-test is included.

### `tools/collector.py`

The Data collector, switched on in the BOTS panel (`collector=1` in `botcore.ini`, passed by `play.py` as `--collect on`; LiDAR mode always runs one). Everything comes from game memory: positions, aims, guns, rounds, equipment and zoom. No keyboard, mouse or controller input is read.

`Collector(path, map, game, clock)` writes a start line `{"t", "collect": "start", "map", "game"}`. `tick(now, players, zoom, aims)` writes one line per tick `{"t", "p": [[id, team, alive, x, y, z, yaw, pitch, shield, health, riding, flag, bot, (people:) crosshair, ride], ...]}` and, for each person whose gear changed, `{"t", "id", "wpn", "inv", "ammo", "mag", "eq", "ab", "uz"}`. `without_keys(text)` removes the key rows and the start line's `keys` field that version 0.1.0 recorded; every shared copy goes through it. Running the file performs a self-check.

### `tools/lidar.py`

LiDAR mode: a match where bots do nothing but map the map, the shared tracker and recorder used by every LiDAR-related part, the people and ride watchers the live brain uses in every match, and the 3D view server. The file is about 3,000 lines.

#### Usage

```
python -I lidar.py <map> [seconds=300] [--game h2a]          a LiDAR match (bots already added: play.py --lidar)
python -I lidar.py --view [map] [--open]                       the 3D view of stored data (default: newest map)
python -I lidar.py --replay <trace.jsonl> <map> [--speed 4] [--human-id N] [--save] [--hold S] [--port P]
python -I lidar.py --selftest
```

#### Concepts and data format

- **Grid.** Recorded cells are 0.25 units in x and y (`CELL`) and 0.1 in height (`ZSTEP`). Exploration ("been there") uses a 1-unit grid (`COVER`).
- **Cell kinds.** `KIND_BOT` 0, `KIND_HUMAN` 1, `KIND_AIR` 2 (air paths), `KIND_CROUCH` 3, `KIND_SPREAD` 4 (floor painted around a player), `KIND_WALL` 5, `KIND_AIRSPACE` 6 (simulator aircraft), `KIND_RAMP` 7 (floor on a placed piece's walkable slope).
- **`maps/<map>/lidar.json`** (merged over runs, written atomically): `cell`, `zstep`, `runs`, `bot_minutes`, `human_minutes`, `walk` (`[ix, iy, iz, kind, samples]`), `deaths` (last 3000), `jumps` (measured apex heights, last 2000), `links`, `weapons` (`{name, pos, seen, picked}`), `cover` (cover spots in front of walls), and `objectives` (every gametype objective place with its visit and nav verdicts, see below). A link is `{take_off, land, runup, apex, air_s, path, found_by, human, bot_ok, bot_fail, t}` with optional `back` (taken the other way), `called`, `ride`, crouch or recorded-route flags, and simulator counters `sim_ok` / `sim_fail`.

#### The tracker (`Track`)

One per player. `update(t, pos, crouch, ground)` buffers positions and classifies each sample 0.25 s (`SPAN`) after it, from the vertical acceleration over a plus or minus 0.25 s window: a ramp is a straight line in height over time, a jump or fall is a parabola. A sample is air when `|acc| > 1.5` (`AIR_ACC`) or it climbs or sinks faster than the horizontal speed allows (a lift). Events:
- `ground` and `crouch` (crouch held) samples mark floor at once.
- `air` samples are held as pending. A landing needs 0.1 s of ground (`SETTLE_S`). Short flat "air" (under 0.4 s and 0.35 units) is a step or ramp corner and becomes ground. The take-off is corrected to the last pending sample at take-off height.
- A real landing waits 5 s (`CONFIRM_S`) before it is reported as `land` with take-off, landing, apex, air time, run-up point and the trail. Dying within those 5 s, or in the air, erases it (`die()` returns where it last was, where it stood, the drop and whether it was a fall, more than 3 units).
- A crouched walk of 1 unit or more becomes a `crawl` event (a crouch route) after the same 5 s.
- A jump of more than 3 units in under 0.25 s (teleporter, respawn) starts a new path.

#### The recorder (`Recorder`)

Holds a run's results and the map's stored data. Main methods:
- `mark(p, kind)` counts a cell and appends it to `events` (the live view's feed). On level data, `spread(p)` floods the walkable floor around a standing player up to 2.5 units (stops at drops of more than 0.3), painting walls where the flood meets an upright or leaning face (`wall_out`, faces checked at several heights from knee to over the head) and recording the floor in front as a cover spot (not glass: `load_glass` reads `glass.json`).
- `bumped(p, d)`: a bot pushed into something it could not climb; painted as wall, a cover spot, and where the level data claims open floor, reported to the nav (`Terrain.learn_stuck`).
- `landed(info, who)`: marks the air trail; a jump's apex is measured. Only a person's landing becomes a link directly, and only when it is a real jump or a drop of a unit or more that covers at least 0.8 units or climbs 0.3 (`LINK_MIN_XY`, `LINK_MIN_RISE`), and walking would be impossible or much longer (`worth_a_link`) unless it is a climb. A matching link (within 0.6 units, `MERGE`) is reused; the same jump the other way makes it two-way.
- `crawled`, `routed` (recorded routes), `died`, `found_weapon`, `classify` (two-way or one-way per link, `brain.terrain.jump_ways`), `apex` (median measured apex, 0.8 until 20 jumps).
- `save(bot_seconds, human_seconds)`: copies what is new under the lock, merges outside it, writes `lidar.json` via a temporary file.

#### Mapping bots (`Roomba`)

Each driven bot in LiDAR mode is a `Roomba`. Every tick `think(now, pos, rec, T, bounds)` returns `(forward, strafe, yaw, pitch, buttons)`:
1. **Trials first.** If a trial is under way (`trial_steer`): a jump being tried (walk to the run-up by the nav, run to the take-off, jump, fly at the landing), a crouch route or recorded route (`route_steer`), a ride or switch (`interact_steer`: stand on a man cannon or lift and let it throw you; press Use on a switch for 2 s), or a recorded shot (`shoot_steer`: walk to the person's stand point, aim at the impact point and fire in bursts as long as the person did). It gives up a trial whose way to the take-off runs off a deadly edge and sidesteps when caught on a corner.
2. **Goals** (`pick`): with some probability it replays a recorded shot nobody did yet this match (25%), rides an untested launcher or lift (15%) or presses an untried switch (10%, where pickups work), calls a jump (`pocket`, 30%: the nearest floor within 25 units it cannot walk to, with a take-off it can reach and room to run, whose `jumpphys.fly` arc lands alive; the call counts only if the bot lands within 0.5 units and 0.2 in height of the call), or probes floor the nav cannot reach (`probe`, 15%: walked at straight; two bots landing it makes a link). Otherwise it asks the LiDAR director for a job, then falls back to its own `frontier` (nearest unpainted reachable floor by path, away from other Roombas' goals and fall spots, searched at 40, 150 units, then everywhere), and with nothing left the best of 24 random points 6-24 units away.
3. **Way there** (`way_in`): the nav's next point four times a second; if that point is a recorded jump or route starting here, it is taken as a trial.
4. **Weapons** (`weapon_steer`): a weapon within 8 units not tried lately is walked to and Use tapped for up to 12 s.
5. **Walking safety.** Steps toward a deadly drop (level data or a known fall spot) or off an edge into a lethal fall (`walk_off_kills`) stop it and pick a new goal. Being stuck triggers a jump and sidestep; no headway of 0.4 units over 1.5 s twice blocks that direction for 20 s. `bumps` turns a stop while pushing alone into a wall mark.
6. **Jumps.** Every 4-10 s it jumps where no deadly drop lies around and `self_safe` says the arc lands alive. It crouches on and next to floor where people crouched.

Results come back through `on_events` and the Roomba's `landed`, `crawled`, `rode`, `score` (successes and failures counted on the link; a called jump that worked becomes a link every bot may use; a missed call is remembered and no bot calls it a third time) and `died`.

#### Person recordings (F6 and F7)

`PathRec` (record a route by doing it: start, do it, end, stay alive 5 s, saved as a one-way route link) and `ShotRec` (record shots that open something: every projectile leaving along the person's aim line is followed to its impact, objects that moved and a damage field that dropped are saved as a recipe in `maps/<map>/shots.json`) are created by the LiDAR loop and updated every tick. Their `key()` methods start and end a recording; in the current code nothing calls them, since no key input is read, so new recordings are not started. Existing `shots.json` recipes are still loaded and replayed by Roombas, and `ShotRec.watch` marks a recipe done once anyone performs it in the match.

#### Watchers used in normal matches

- `HumanWatch(map, rec, T)`: a `Track` per person. `update(now, people)` takes `(index, pos, alive, crouch, jump pressed, riding)`; riding restarts the track (a seat is no floor), deaths are recorded, and a landing counts as the person's jump only if jump was pressed between 1 s before and 0.3 s after the take-off (`meant`), so being pushed off a ledge by a bot does not count. `save()` merges into `lidar.json`. `live_bots.py` uses it in every match, so people's jumps teach the nav even outside LiDAR mode.
- `RideWatch(map, T)`: for every ridden vehicle, ground and hover vehicles record driven cells (counts for people and bots kept apart); aircraft record flown cells with height over the floor below, a height histogram per source, and take-offs, landings and turn-backs (heading reversed within 3 s). `save()` merges into `maps/<map>/rides.json`; `brain/maps.py rides_layers` turns it into vehicle ground and airspace.

#### Gametype objectives (`objective_points`, `Objectives`)

A LiDAR run sends a bot to every objective place of every game type on the map, so the scan covers them all even though the game only spawns the objects of the mode being played.

- `objective_points(map, stations)` lists the places, all modes at once, as `[{pos, roles, names, src}]`. The map's own come from its scenario as the editing kits export it (`objects.json` netgame flags and Forge labels: flag stands and returns, hills, oddball and bomb spawns, plant points, territories, havens, drop points, race checkpoints, Invasion zones and so on), sorted into roles by `tools/map_features.py` (`from_objects`, `role_of`). Objective objects read live by `brain/stations.py` are added (a Forge layout's own); a Forge canvas variant with no layout of the base map's own (`brain/variants.base_area`) has only those. Places closer than `OBJ_MERGE` (2.5 u) are one place, keeping all their roles and names; `src` is `map`, `live` or `map+live`.
- `Objectives(map, T, stored, stations)` holds the places for one run. For each it keeps `reached` and `given_up` from the stored list (matched by position) and the nav's verdict (`nav_of`): `floor` (the nav's floor cell there), `on` (walkable floor within `OBJ_NAV_Z`, 2.5 u, of the objective's height) and `reach` (also reachable from the spawns). Stored places of another layout are kept as they are.
- `seed(director)` gives the LiDAR director one spot per place not yet reached (`add_spot(goal, bots=1, label=role)`), where the goal is the nav's floor there, else the objective itself.
- `update(positions, now)`, at most twice a second, marks a place reached once anyone, bot or person, stands within `OBJ_REACH_R` (2.5 u) across and `OBJ_REACH_Z` (2 u) up or down of its goal, or the director's spot for it is done; a spot the director gave up on marks the place `given_up`.
- `saved()` refreshes the nav verdicts (the nav learns during a run, so new jumps can reach more) and returns the list the `Recorder` saves as `objectives`; reached stays reached over runs, and reached places are not sent again. `line()` is the status text ("objectives: r of n places reached, k not reachable on the nav from the spawns"), and `report` lists the places nobody reached or the nav cannot reach.

#### The LiDAR match loop (`main`)

1. Picks the reader for `--game`, opens the shared memory, and loads the level data (`level_data`: terrain and bounds; on a Reach Forge variant the variant's name and its pieces face by face). Makes the `Recorder`, sets whether pickups work (`PICKUP_GAMES`: CE and H2), and the physics (`jumpphys.Phys`, with the map's measured apex after 20 jumps).
2. Starts the view server (`serve(Hub(rec, "live"))`), `HumanWatch`, `Notices` (notices over the game when a person's jump is learned and when bots first do one twice), `PathRec`, `ShotRec`, the `LidarDirector` when there is level data, `Stations` (H3, Reach, H4, H2A), with level data the run's `Objectives` (from the stored list, seeded into the director and printed), `Oob`, and a Data collector (`logs/collect_<map>_<stamp>.jsonl`).
3. Each tick at 30 Hz: reads players (10 s of failed reads ends the run), vehicle places (`seat_places`: a rider's place is his vehicle's), shows a "LIDAR MODE" notice once, grows a variant's nav window, detects a new round (half or more of the bots gone at once: not deaths), re-reads lying weapons twice a second, keeps the last 2 s of botcore's copy of the person's action bytes and, when the person picks up a weapon, appends the pickup and those bytes to `logs/owner_pickups_<map>.jsonl` (for decoding the pickup fields), updates stations, the collector, bug report filing, out of bounds, people, and then each Roomba: death handling (a fall teaches the nav at once with `teach_falls`), the hub's player rows, tracker events, weapon pickups and sightings, `think`, and `botctl.act`.
4. The director plans (every 6 s, `lidar_director.PERIOD`); a bot it just sent to a spot or an objective drops its old goal unless a trial is under way, `Objectives.update` gets every player's position, and the director's status line carries the objectives line. When a variant's grown nav is swapped in, the director is rebuilt and the objectives seeded into it again. Every 2 s new usable links go into the nav (`nav_learn`: `T.add_human_links` and fresh spawn reachability). Every 60 s the recorder saves and `logs/lidar_<map>.md` is rewritten (botcore kills the process when the match ends).
5. On exit: collector closed, stations and oob saved, a final save and report, learned nav spots saved (`save_learned`), the server shut down.

#### The 3D view server (`Hub`, `serve`)

`Hub(rec, mode)` holds the players shown (name, human, position, alive, in the air, trail, trying a jump, the called landing), a session id that makes the page reset when the run changes, and a note. `stored_view()` gives the stored data; `live(since)` gives the cells marked since sequence number `since` (40,000 at most per answer), links, the last 1500 deaths, players, weapons, called-jump counts, the route being recorded, and features and out-of-bounds zones whenever stations or oob change.

| Method and path | Answer |
|---|---|
| `GET /` | `lidar_view.html` |
| `GET /maps` | `{maps: map_list(), live, mode}`: every map with level data and its Forge layouts, game, scans from matches and the simulator with runs, minutes and floor cells |
| `GET /map?name=&src=scan\|sim` | the stored view of that map (`lidar.json` or `lidar_sim.json`), or the running map's |
| `GET /art/(games\|maps)/<name>.(png\|jpg)` | logos and map pictures from `tools/view_art` (cached an hour) |
| `GET /live?since=` | the live feed, plus `sim` state when the simulator serves |
| `POST /remove?name=&src=` | the maps list's Remove: moves the scan (and for `sim`, the simulator's links' counters) into `backups/lidar/<map>_<time>_<file>`; requires header `X-LiDAR: remove` and is refused for the map a live run is recording |
| `POST /sim` | simulator commands (header `X-LiDAR: sim`) |
| `POST /yield` | a stored view gives up the port to a live LiDAR match |

`serve` does not reuse addresses. A live match that finds the port taken first asks the stored view there to yield, then retries for a few seconds; a stored view that finds it taken gives up and the launcher's window simply shows the running server. The LiDAR Viewer and a LiDAR match use `PORT` (8797); the simulator serves on its own port (8798), so a simulator left open never keeps a match's live view from starting. `view(o)` serves the newest scanned map (or the named one) in `stored` mode and exits when a live match takes over. `replay(o)` feeds a trace's bot positions through trackers and the recorder at `--speed`, with `--human-id` treating one bot as a person, as a test without the game.

#### Other helpers

`map_title` and `map_titles` (real map names from `tools/view_art`), `map_ok`, `file_name` (a variant's slashes made file-safe), `people_states` (players as `PlayerState` for the collector and bug reports), `load_features` (`features.json` plus live stations and oob zones), `report` (the Markdown report against the level data), `teach_falls`, `ground_weapons`, `level_data`, `selftest` (tracker, recorder, Roomba, view JSON, Remove).

### `tools/lidar_view.html`

The WebGL 3D view (no external libraries; it shows a message if WebGL is unavailable).

- **Header.** "LiDAR" with a status pill: CONNECTING, WAITING or LIVE (a live run with or without players), STORED, STORED SCAN or SIMULATOR SCAN (a map opened from the list), SIMULATION, REPLAY or REPLAY DONE, RECORDING PATH or SAVING PATH (a route recording), OFFLINE (the server stopped).
- **Toggles** (with keys): Earlier runs (E), Air paths (P), Deaths (D), Jumps (J), Weapons (W), Air space (A), Map features (M), Maps list (L), Grid (G), Follow you (F), Top view (T), Reset view (R). Arrow keys orbit and tilt, plus and minus zoom; the mouse drags and zooms.
- **Maps list.** From `/maps`: each map with its game logo, picture and scans, a "Scanned maps only" filter, opening a stored map (`/map`), Remove with a confirmation (`/remove`), and "Back to the live scan".
- **Simulator panel** (shown when served by the simulator): Pick a map, Every map, speed choice, Pause, Stop, "Click spots to cover" (C) and Clear spots; it posts to `/sim` with `X-LiDAR: sim` and draws the spots and the director's state from `/live`. Spots with a label are gametype objectives: the panel counts them apart ("Gametype objectives: k of n visited", and how many have no way there), and Clear spots counts and clears only the spots a person marked.
- **Live feed.** Polls `/live?since=<seq>` and appends new cells; a changed session id resets the scene. When the server stops, the message says the Simulator has stopped (open it again from the launcher) or, for the live view, how to open the stored map.
- The page title starts with "LiDAR Simulator", "LiDAR live" or "LiDAR" by the server's mode.

### `tools/lidar_sim.py`

**Purpose.** The offline LiDAR Simulator: the real `Roomba` code mapping a map's level data at high speed, without the game, watched in the LiDAR view.

**Usage.** `python -I lidar_sim.py [maps... | --all] [--game ce] [--minutes 6] [--walkers 16] [--aircraft 8] [--speed 0] [--max-real 240] [--open] [--port 8798] [--hold 0] [--no-director]`. With no map names it waits for a pick from the view (the launcher's `lidar_sim` task).

**How it works.**
- `Body` moves a walking bot by its action with `jumpphys.walk_step` and `air_step` (a small random take-off error), returning a fall when a landing is too hard and void when it falls out of the level.
- `run_map(name, ...)`: loads the terrain and teleporters, makes a `Recorder` that writes `maps/<map>/lidar_sim.json` but starts from the real `lidar.json` links (people's jumps, earlier simulator jumps), with fresh coverage, counters `sim_ok` / `sim_fail` and `found_by: "sim"`. Probes, rides and switches are off (`PROBE_P`, `RIDE_P`, `USE_P` set to 0). Walkers start on spawn points snapped to reachable floor; a `LidarDirector` plans unless `--no-director`, and with it a fresh `lidar.Objectives` sends one walker to each gametype objective place every run (marked reached from the walkers' positions, saved in `lidar_sim.json`). `Airspace` builds voxels of free air over walked floor up to the ceiling (`ceiling_of`: `maps/<map>/air.json` or 2 units over the highest surface) and `Craft` aircraft fly routes through unflown air at 6 units per second, painting it (`KIND_AIRSPACE`). New called jumps go into the nav at once; at the end `merge_links` writes them and the results on known links into the real `lidar.json` (only `links` is touched), and a row is appended to `logs/lidar_sim.md`. The simulation runs at 20 Hz of simulated time.
- `Switch` holds the hub currently served (the server reads `hub.current`); `Control` is the panel's state: `command()` handles `pick`, `all` (every map except Forge variants), `speed` (1, 2, 4, 8, 16 or 0 for as fast as possible), `pause` / `resume`, `stop`, `spot` (snapped to the nearest walkable floor within 3 units, handed to the director as a spot to cover) and `clear_spots`; `state()` is added to each `/live` answer.
- `main` orders maps by game, starts the view server on `PORT` (8798, not `lidar.PORT`), opens the window with `--open`, exits if another simulator already holds the port (two would save the same maps; the window just opened shows the running one), and runs maps from the queue. Without named maps it waits for picks and exits 90 s after the window stops polling. One failing map is logged and the tour continues.

### `tools/lidar_director.py`

Plans the whole map for the mapping bots, every 6 s (`PERIOD`), in LiDAR matches and the simulator.

`LidarDirector(T, rec, spawns)` samples every second nav cell (0.5 units apart). `plan(now, bots)`:
- computes which sample cells are reachable by walking, teleporters and landed jumps from the spawns (`_reach`, over `graph_h`);
- splits unpainted reachable floor into connected regions per floor level (`_pieces`, SciPy `label`; pieces under 6 cells ignored) and unpainted unreachable floor into islands;
- gives each bot a region job (keeping its own until painted, else the best free one by size and distance, never two bots on one region while another has none; a bot's own region is worth 25 path units in `region_bias`), and once 70% of reachable floor is painted gives up to two bots within 30 units of an island a jump job (walk to the take-off side, then call the jump; dropped after 40 s);
- sends the 3 nearest free bots (`SPOT_BOTS`) to each spot a person marked in the simulator view, marking it covered within 2.5 units or given up after 120 s;
- sends one bot to each gametype objective spot (`tools/lidar.py Objectives`), pairing the nearest free bot and objective first, with at most `OBJECTIVE_SHARE` (half) of the bots on objectives at a time (at least one) so the rest keep painting the map.

`add_spot(pos, bots, label)` adds a spot for `bots` bots and returns it; a `label` (the objective's role) marks a gametype objective, None a spot a person marked. `clear_spots()` removes only the marked spots and keeps the objectives. `spot_view()` lists the spots with their label for the view.

`job(index, pos)` returns `("go", target)`, `("jump", take-off)`, `("call", None)` at the take-off side, or None; `Roomba.pick` calls it. `line(now)` prints a status line every 30 s.

### `tools/paint.py`

**Purpose.** The nav painter server: hand corrections to the nav on a map's roofless view. Port 8796.

**Layers** in `maps/<map>/paint.json` (`{map, cell: 0.5, layers, jumps}`, cells `[x, y, z]` with z the floor under the cell):
- `walk`: floor the level data lacks, added to the nav's floor.
- `block`: floor bots must not walk (entering costs a wall).
- `drive_s`, `drive_m`, `drive_l`: ground for small, medium and large vehicles (all added to the vehicles' ground at present).
- `fly_low`, `fly_high`: airspace for attack runs and for travel.
- `jumps`: `[x, y, z, x2, y2, z2]` take-off and landing pairs, added to the nav as one-way people's jumps.

`brain/maps.py terrain()` applies the file through `Terrain.apply_paint` at the next match start.

**Snapping.** The page sends each cell with the cut height it was painted at. `to_cells` puts it on the half-unit grid (one cell per spot and layer) and snaps z with `snap_z` to the highest walkable floor of `heightmap.npz` at or under the cut, or keeps the cut's floor height where the data has no floor. `to_jumps` snaps each end on its own cut, using `surface_z` (the highest upward face of the level mesh wholly under the cut, as the roofless view draws it). Saves are atomic under a lock (a match may read the file at any time). Limits: 400,000 cells, 2,000 jumps, 64 MB per request.

**HTTP endpoints.**

| Method and path | Answer |
|---|---|
| `GET /` | `paint_view.html` |
| `GET /api/maps` | maps (plain `[a-z0-9_]` folder names) with a roofless view or a mesh plus heightmap: `{name, view, painted}` |
| `GET /api/map?name=` | `{view: roofless.json, paint: layers, jumps, links: recorded_links, marks: objectives}` |
| `GET /view/<map>/level_<k>.png` | a roofless picture |
| `POST /api/build?name=` | runs `roofless.build(name)` |
| `POST /api/paint?name=` | saves the posted layers and jumps; answers the counts |

`recorded_links` lists people's LiDAR jumps with their status (used by a bot, untried, retired by `brain.maps.usable_links`); `objectives` lists Invasion territories, core and delivery point. Map names are validated against `^[a-z0-9_]+$` and an existing folder, so the page cannot address other paths. CLI: `python -I paint.py [--port 8796] [--open]`, `--selftest`. The server does not reuse addresses: when the port is taken a painter already runs, and this copy opens a window on it (with `--open`) and returns.

### `tools/paint_view.html`

The nav painter page: a map picker; Undo (Ctrl+Z), Redo (Ctrl+Y) and Save (Ctrl+S, enabled when there are changes); and a side panel:
- **Paint**: one tool button per layer.
- **Brush**: a size slider from 0.5 to 5 units; holding Shift erases the selected layer only.
- **Jumps**: "Draw a jump" takes a take-off click and a landing click; the cut height may change between the clicks for a jump up or down; Shift+click deletes a jump, Esc cancels.
- **Show**: Paint on other heights, Hide paint, Jumps people made (the recorded links with their status), Objectives.
- **Colours**: the height ramp legend (the same ramp as `roofless.py`) and the jump colours.
- **Counts**: cells per layer.

The canvas shows the roofless picture for the chosen cut height. A map without a roofless view shows "Make the roofless view", which posts `/api/build`. Saving posts the whole paint state to `/api/paint`.

## Art and models made on each PC (setup builders)

Project Proving Grounds ships no art, models or textures taken from Halo: The Master Chief Collection. Everything the
launcher, the LiDAR tools and the BOTS panel show that comes from the games is built on each PC from that PC's own copy
of MCC. Most of it is built by the first-time setup (`tools/setup.py`, which the launcher runs and the installer offers
to run when it finishes). A few builders are also run by `native/build.bat`, and a few are map data builders whose
output reaches a player through the map pack, not through the setup.

How the setup drives them: `tools/setup.py` has a table of steps (`STEPS`). Each step has a test that shows it is
already done (a file that exists), a builder, and optionally a reason it does not apply on this PC. The builders that
are separate programs are run with the same Python (`python -I tools/<name>.py`) and report through their last printed
line. Each step prints one line for the launcher:
`STEP <n>/<total> <name>: done | already there | skipped (<why>) | failed: <why>`. `--force` rebuilds every step and
`--status` lists what is there without building anything. The steps, in order:

| Step | Builder | Done when |
|---|---|---|
| game | (finds MCC through `brain/paths.py`) | MCC is found and has at least one game installed |
| bots | `brain/looks.py` profiles | `native/bin/bot_profiles.ini` exists |
| recording | creates `logs/trace_on` | that file exists (`tools/play.py` records matches while it does) |
| map art | `tools/map_art.py` | at least 100 pictures in `tools/view_art/maps` |
| logos | `tools/panel_art.py` | `native/bin/art/ce.rgba` and `h4.rgba` exist |
| 3D bots | `tools/make_models.py` (which also runs `tools/emblems.py extract`) | `native/bin/models/made.txt`, or the Halo 3 model and the emblem art |
| effects | `tools/fx_art.py` | `native/bin/art/fx_fire.rgba`; does not apply without Halo: Reach |
| looks | `tools/looks_export.py` | `native/bin/bot_looks.ini` exists |

A failed step does not stop the steps after it. Steam installs MCC's games one by one, so anything that needs a game the
PC does not have is skipped, not failed.

### `tools/map_art.py`

Builds the pictures for the LiDAR view's map list: one logo per game (`tools/view_art/games/<game>.png`) and one menu
thumbnail per map (`tools/view_art/maps/<map>.jpg`). It also completes `tools/view_art/names.json`, the table of real
map names keyed by map folder.

How it works:

- `pack(path)` reads one of MCC's UI texture packs in `data/ui/texturepacks`. A pack is a `.perm.bin` made of segments,
  each with a 16-byte header whose size field is at offset 8. A texture's 464-byte name record holds its name at +52,
  its data size at +120 and its offset into the `.temp.bin` at +128. Streamed packs have no `.temp.bin`; their data
  sits in the segment three before the name record. The result is `{texture name: raw block data}`.
- `dds(data, w, h, fourcc)` wraps the raw BC1 or BC3 data in a minimal DDS header so Pillow can decode it.
- The game logos are the `HALO...GAMEICON` textures of `globaluitexturepack` (120 x 120, BC3). Each is cropped to its
  visible pixels. Where the pack is missing, `drawn_logo()` draws a plain framed short name instead (CE, H2, H3 and so
  on).
- The thumbnails come from `ingamechapterpack` (BC1, 316 x 158 or 668 x 292, recognised by data size).
  `thumbnail(folder, name, thumbs)` finds a map's texture by its game's prefix (`H1MP_`, `H3MP_`, `HREACHMP_`,
  `ODSTFIREFIGHT_` and others) followed by the map's real name in capitals without spaces or punctuation, with an
  optional `S3D_` before it and an optional `LARGE` after it (the small one is preferred). `ODD_THUMBS` lists the few
  maps whose thumbnail is named differently.
- `info_name(mcc, folder)` reads a map's English name from MCC's `maps/info/<map>.mapinfo` (UTF-16, at byte 69) for
  Halo 3, ODST, Reach, Halo 4 and Halo 2 Anniversary. Halo: CE and Halo 2 have no such files, so their names come only
  from `names.json`, which ships with the project.
- Only map folders that have a `heightmap.npz` (from the map pack) get a picture. A map MCC has no thumbnail for gets
  its own `topdown.png` shrunk onto a dark 316 x 158 card. Large thumbnails are scaled down to 316 pixels wide.

Command line: `python -I tools/map_art.py [--mcc <MCC folder>]`. MCC's folder defaults to `brain/paths.mcc()`. When
the menu art is missing from the copy of MCC, it says so and suggests Steam's file check. `tools/lidar.py` reads these
files and reports when the real map names are missing.

### `tools/panel_art.py`

Converts the game logos from `tools/view_art/games/*.png` into raw pixel files the BOTS panel can load without an
image library: `native/bin/art/<game>.rgba`, laid out as uint32 width, uint32 height, then width x height RGBA bytes
(`write_rgba()`). It also writes `native/bin/art/stage.rgba`, the backdrop behind the 3D bot in the profile view.
`backdrop()` draws it procedurally with numpy (a blue gradient room, five fanned light shafts, a soft pool of light
behind the figure and on the floor, a vignette and a little noise against banding). It is the project's own drawing,
not MCC's art.

Command line: `python -I tools/panel_art.py`, printing `panel art: <n> logos -> native/bin/art`. Both the setup's logos
step and `native/build.bat` run it. It needs `tools/view_art/games`, so on a fresh checkout it only has logos to
convert after `map_art.py` has run; the setup runs map art before logos for that reason.

### `tools/fx_art.py`

Makes the armor effect sprites of the profile view (fire, hearts, flies, smoke and a flash) from Halo: Reach's own
particle bitmaps. It reads Reach's Sword Base map (`haloreach/maps/20_sword_slayer.map`) through
`model2obj --bitmaps` (the map tools, below) and writes `native/bin/art/fx_<name>.rgba` in the same layout as
`panel_art.py`. `native/bots_panel.cpp`'s effect layer draws them.

How it works:

- `TAGS` names the bitmap tags used by Reach's `armor_fx` effects: `fire_large`, the `fire` and `covenant_fire`
  gradients, `flying_heart`, `bugs`, `soft_smoke_small` and `flash_soft`.
- `exported(key)` exports a bitmap once into `maps/_models/fx` (as `<tag path with underscores>_0.png`) and returns
  its first submap as a float RGBA array. A failed export stops with the map tools' exit code and last message.
- `palette_fire()` bakes the grayscale fire through a gradient row: a pixel's brightness picks its colour and also
  becomes its alpha. Three fires are made: orange (`fx_fire`), blue (`fx_fire_blue`, the Covenant gradient) and purple
  (`fx_fire_purple`, the Covenant gradient tinted).
- The hearts and flies are written as drawn. `white_alpha()` turns the smoke and flash into white sprites with their
  own alpha (128 x 128), which the panel tints when it draws them.

Command line: `python -I tools/fx_art.py [MCC folder]`. It stops with a clear message when Reach is not installed;
the setup marks the step as not applicable in that case. `native/build.bat` runs it when `fx_fire.rgba` is missing.

### `tools/make_models.py`

Builds the 3D bots of the BOTS panel's profile view (`native/model_view.cpp`): each game's Spartan and, where the game
has one, Elite, exported from MCC's own map files, posed holding a weapon, and packed into
`native/bin/models/<game>_<species>.mdl` with textures in `native/bin/models/tex/`. The full run takes a few minutes and
writes roughly 450 MB, because Reach, Halo 2 Anniversary and Halo 4 carry every Armory piece the bots can roll.

The first-time setup runs it with `--clean-exports`: once every model is packed it deletes the exported meshes in `maps/_models/<game>` (about 2.4 GB of working space), keeping `maps/_models/emblems_mcc` and `maps/_models/fx`; run by hand without the flag, the exports stay for inspection.

How it works:

- `MODELS` is the list of models: output name, species (`spartan` or `elite`, which decides the pose), game (the
  texture name prefix), the map file to read, the end of the character's render model tag name, the end of the held
  weapon's tag name, and the options passed to `model_pack2.py`. Sources include Blood Gulch (CE), Lockout (Halo 2),
  Construct (Halo 3), Lockout Anniversary (H2A), Sword Base (Reach) and Warhouse (Halo 4). Each entry carries its own
  hold (`--hold "grip=...;barrel=...;pole_r=...;pole_l=..."` and stance values), Elites hold the energy sword
  one-handed (`--one-hand`), and the H2A Spartan drops permutations no bot wears (`--drop`).
- `GEAR` adds models the game hangs on the body by a marker: Halo 3's backpacks are the `mp_masterchief\gear\gear`
  model's `chest_flair` region on the body's `backpack` marker, read from Guardian, whose copy lists all of them.
- For each model, `main()` runs `model2obj` twice (body with `--uv --skin --tex`, weapon with `--uv --tex`, plus the
  gear model where there is one) into `maps/_models/<game>/`, then runs `tools/model_pack2.py` on the result. A model
  whose map is not installed is skipped and listed. A failed export prints the tail of the tool's output and moves on.
- `prune(out)` then removes textures in `tex/` that no version 2 model names (it reads each `.mdl` header and material
  records), because each export numbers textures anew.
- On a full run (no `--only`) it runs `tools/emblems.py extract` and writes `native/bin/models/made.txt` listing the
  models made and those skipped; the setup uses that file to know the step ran.

Command line: `python -I tools/make_models.py [MCC folder] [--only h3_spartan,h3_elite] [--out <models folder>]`.
`--out` builds somewhere else, for example while a running MCC holds the models open. `native/build.bat` runs it when
`native/bin/models/h3_spartan.mdl` is missing; the setup's 3D bots step runs it when the map tools are found.
`tools/test_model_pose.py` imports `MODELS` and `prune()` for its checks.

### `tools/model_pack2.py`

Packs one exported character with its textures, posed and holding its weapon, into a version 2 `.mdl` that
`native/model_view.cpp` reads straight into GPU buffers.

Inputs: the body OBJ from `model2obj --uv --skin --tex` (with `<obj>.skin`, `<obj>.mat.json`, `<obj>.markers.json`,
optionally `<obj>.regions.json`, and the PNG textures), and the weapon exported the same way. OBJ groups are named
`region|permutation index|permutation|material`.

The pose:

- `read_skin()` and a `Skeleton` class give the bind pose, bones and weights. `read_markers()` and `gun_markers()` read
  the game's own hand and weapon markers.
- `pose_hold()` puts the gun's grip in the right hand by the hand marker and, for a two-handed gun, its fore-end in the
  left. `mount()` bends each arm to reach by two-bone IK with a pole direction, `roll_forearm()` rolls the forearm for a
  straighter wrist, and `curl()` closes the fingers. A turn of the chest and head and a leg stance follow.
  `apply_hold()` applies a model's own hold string from `make_models.MODELS` over its species' defaults.
- The body is skinned with linear blend skinning and the game's own weights (`Skeleton.skin`), and the weapon is moved
  into the hands.

The packing:

- Body, weapon (region `weapon`, always drawn) and gear meshes are merged. Weapon parts with no texture maps at all are
  left out (Halo 2's ammo digits), as are non-default weapon permutations where a default exists, and meshes in
  `HIDDEN` (Reach Elite's assassination knife blades). An energy sword's blade becomes kind 6 (drawn glowing).
- Reach's instanced flair (`model2obj`'s `<Instances>` group) is filed under each region and permutation that wears it,
  from `<obj>.regions.json` `owners` (`instance_owners()`), so the panel shows it with its piece.
- `materials()` maps each material's textures to five slots (`diffuse`, `color_change`, `normal`, `self_illum`,
  `normal_detail`) and shrinks them into `tex/` (`shrink()`, 512 or 256 pixels on a side, normals as JPEG).
  `slot_of()` and `shrink()` handle game-specific layouts: Halo 2 Anniversary's paired `_s` / `_d` armor maps, Halo 4's
  control map (green the albedo, red the specular mask, alpha the colour mask), and Halo CE's multipurpose map whose
  channels hold colour change and self-illumination. `flat_part()` makes small flat textures for gun parts the game
  colours from shader settings rather than maps (`FLAT`).
- File layout: header `HBMD`, uint32 version 2, group, vertex, index and material counts, six floats of bounds; per
  material a 48-byte name, five 48-byte file names and two floats (detail tiling, spare); per group a 24-byte region,
  a 32-byte permutation, permutation index, kind, first index, index count and material index; then vertices (position,
  normal, UV as floats) and uint32 indices. Kinds: 0 armor, 1 under-suit, 2 visor, 3 lights, 4 skin, 5 decals (not
  drawn), 6 a glowing blade. File names are limited to 47 characters (`flat_part()` falls back to a CRC name).

Command line: `python -I tools/model_pack2.py <spartan|elite> <body.obj> <weapon.obj> <out.mdl> [--prefix h3]
[--drop el_] [--one-hand] [--hold "..."] [--gear "<obj>|region=marker"] [--preview p.png] [--sticks p.png]`.
`--preview` writes a quick point render of the posed model and `--sticks` writes the posed skeleton front and side
with the hand targets (and skips the packing), both for checking a pose without the panel. It is normally run only by
`make_models.py`. `tools/test_model_pose.py` imports it to check the IK, the hold and the packed models.

### `tools/model_pack.py`

The first version of the packer: an untextured, unposed version 1 `.mdl` (header `HBMD`, version 1, groups with
region, permutation, permutation index, kind, first index and count, then position and normal per vertex, then uint32
indices). Command line: `python -I tools/model_pack.py <in.obj> <out.mdl> [permutation prefixes to drop]`.

Nothing runs it as a program any more: `make_models.py` calls only `model_pack2.py`. It is still needed because
`model_pack2.py` imports its `kind_of()` (the material name to drawing kind table, `KINDS`), so the two must stay
together. `native/model_view.cpp` still accepts version 1 files (geometry only, drawn as clean figures in the bot's
colours), and the comment at the top of `native/model_view.h` still names `model_pack.py`.

### `tools/emblems.py`

Extracts MCC's own player emblems for the bots. Every game's scoreboard and MCC's post-game report draw a player's MCC
emblem, which MCC renders from its player lookup by Xbox id; `native/report.cpp` answers that lookup for the bots, so a
bot's emblem has to be one of MCC's. `brain/emblems.py` rolls and composes them.

`extract` mode:

- `catalog(xml)` reads `Data/UI/playercustomization.xml`: the foregrounds (with both layers and their small versions),
  the backgrounds and the emblem colours, with readable names made from the name keys (`pretty()`).
- `layers(mcc, wanted)` reads the 256 x 256 layers from `Data/UI/texturepacks/mainmenuandcampaigntexturepack`: 480-byte
  entries in `.perm.bin` (name at 0x44, format at 0x68 where 3 is BC3, width and height at 0x74, data size at 0x88 and
  offset into `.temp.bin` at 0x90), decoded with `bc3()`.
- Only emblems whose every layer was found are kept (MCC will not render one with a layer missing). Each layer's alpha
  channel (the shape; MCC tints it) is saved as `maps/_models/emblems_mcc/<layer>.png`, and the catalog as
  `maps/_looks/mcc_emblems.json` (`brain/emblems.ART` and `brain/emblems.CATALOG`).
- A copy of MCC without these menu files is reported and skipped, not treated as an error.

`sheet` mode draws every bot's rolled emblem on one picture with its name, as a visual check.

Command line: `python -I tools/emblems.py extract [MCC folder]` (run by `make_models.py` on a full run) and
`python -I tools/emblems.py sheet <out.png>`.

### `tools/looks_export.py`

Writes `native/bin/bot_looks.ini`: every bot's look as rolled, per game, for the profile view
(`brain/looks.export_view()`). Each line is `<name>|<game>|<view>|field=value...`, where the view is `own` (the bot's
preferred species) or `other`; Halo 3, Reach, H2A and Halo 4 lines end with the model pieces the bot wears. The panel
therefore never shows "Random" for something the roll already decided.

Command line: `python -I tools/looks_export.py [profiles.ini] [out.ini]`, defaulting to `native/bin/bot_profiles.ini`
and `native/bin/bot_looks.ini`. The setup runs it once. After that `native/bots_panel.cpp` (`looks_refresh()`) runs it
in the background whenever the file is missing or older than `bot_profiles.ini`, and after every change in the profile
view.

### `tools/heightmap.py`

Builds a map's top-down height data and picture: `maps/<map>/heightmap.npz` and `maps/<map>/topdown.png`. This is the
level data the brain's terrain model (`brain/terrain.py`, loaded through `brain/maps.py`) uses for ground height, line
of sight, floors and walls. The setup does not run it: its outputs are part of the map pack (see the developer kit),
which is unzipped over a source checkout or installed by the installer.

Inputs: a level mesh as OBJ in the Halo CE mod kit's axis convention (`tool.exe export-structure-mesh-obj`; the OBJ's
X, Y, Z are Halo's x, z, -y; `load_obj()` converts back), the map's `objects.json`, an output
folder, a cell size (default 0.25 world units) and optionally a callout zones file to draw.

How it works:

- `play_area()` limits the grid to where players can be (spawns, flags, equipment, vehicles) plus a 40-unit margin, so
  a huge ocean plane or geometry far under a map does not blow up the grid. It also sets the bottom of the wall range
  16 units under the lowest player object.
- `rasterize()` walks every triangle and records, per cell, the top and lowest surface heights, and collects walkable
  surfaces (normal z at least 0.7, about 45 degrees). `stack_floors()` groups those into up to `MAX_FLOORS` (4) floor
  levels per cell, a new level starting `LAYER_GAP` (1.0 unit) above the previous one (a doorway, the roof over it, a
  catwalk above that).
- `rasterize_walls()` samples every steep face densely and sets bits in a 256-bin height bitmask per cell (4 uint64
  words, 0.25 units a bin), so thin walls that the top-down layers miss still block.
- `render()` draws the height bands with hill shading, contour lines every unit, a 10-unit grid, the zones, flags,
  teleporters, King hill markers, equipment, rocks and trees, and spawns.

The `.npz` holds `top`, `low`, `floors`, `walls`, `wall_z0`, `wall_bin`, `x0`, `y0` and `cell`. Command line:
`python -I tools/heightmap.py <bsp.obj> <objects.json> <out_dir> [cell=0.25] [zones.json]`. The per-game export
scripts that drive it from the mod kits are research tools and are not part of the public repository.

### `tools/reach_tag_names.py`

Reads the tag names of a map, by tag index, from its MCC `.map` file (Reach, Halo 3, Halo 4, Halo 2 Anniversary). The
games keep no tag names in memory, so a live object's tag id (its low 16 bits are the tag index) is named through this
list. `brain/forge.py` uses it to identify Forge pieces, `brain/live.py` to name guns and objective items, and
`brain/stations.py` to name objects in the object table.

How it works: `names_of(path)` reads the cache file's header for the tag name count, the names buffer pointer and the
index pointer, adds the first section's offset from the section table (at 1228 for Reach and Halo 3, 1220 for Halo 4
and H2A; `LAYOUTS` tries both, wrapping at 32 bits), then follows the index entry by entry (one int32 offset per tag,
-1 for none) into the buffer of null-terminated paths. The index must be followed because the buffer is not stored in
index order. The first layout whose sample reads as printable tag paths wins; none stops with a message that an MCC
update may have moved the table. `cached(map_name, game)` returns the list from
`maps/_shapes/<game>_tags_<map>.json`, creating it from the `.map` file the first time.

So this builder runs on demand rather than in the setup: the map pack carries the saved lists under `maps/_shapes`, and
a map without one gets it the first time the brain asks. Command lines: `python -I tools/reach_tag_names.py <map>
[reach|h3|h4|h2a]` and `python -I tools/reach_tag_names.py --check` (rereads every saved list's `.map` file and
reports the first differing index; exit 1 on any difference).

### The map tools: `bsp2obj.exe` and `model2obj.exe`

Two command-line exporters that read MCC's `.map` files. They are a separate project, Proving Grounds Map Tools,
because they are built on Reclaimer, a Halo map library under the GNU General Public License v3.0, so they are GPL-3.0
too. Project Proving Grounds contains none of their code and only runs them as separate processes.

| Program | Writes | Used for |
|---|---|---|
| `bsp2obj.exe` | a map's level geometry (every structure BSP and its instanced geometry) as one OBJ, optionally its see-through triangles (`--glass`) | rebuilding level data (height maps, glass masks) for games whose official kits cannot export these meshes (H2A, Halo 4, ODST) |
| `model2obj.exe` | a render model with every permutation, skeleton, skin weights, markers and textures; or bitmaps as PNG | the 3D bots (`make_models.py`) and the effect sprites (`fx_art.py`) |

Usage, from that project's documentation:

```
bsp2obj <file.map> <out.obj> [bsp name filter] [--glass <glass.txt>] [--list]
model2obj <file.map> <tag name filter> <out.obj> [--uv] [--skin] [--tex <dir>]
model2obj <file.map> --list <filter>
model2obj <file.map> --bitmaps <filter> <dir>
```

Finding them: `brain/paths.map_tool(name)` returns the first `<name>.exe` found in the folder named by `HB_MAP_TOOLS`,
then `tools/map_tools` (where the installer puts them), then `proving-grounds-map-tools/bin` in a checkout beside this
project. `brain/paths.need()` turns a missing tool into a clear stop. The setup's 3D bots and effects steps check for
`model2obj` first and report the tools as missing instead of failing inside the builder, and the launcher shows whether
they are present. `tools/build_installer.py` copies the whole folder holding `model2obj.exe` (with its runtime) into the
installer's `tools/map_tools`. The release rules keep `tools/map_tools` out of the public repository.

Building them needs Windows, Git and the .NET 10 SDK: clone that project with its `reclaimer` submodule
(`git clone --recurse-submodules`, or `git submodule update --init`) and run its `build.bat`, which publishes both as
self-contained x64 programs into its `bin` folder, so they run without a .NET install.

## The developer kit (public repository only)

These files are in the public repository but not in a player's install: `tools/build_installer.py` filters them out
with its `DEV_ONLY` list (the tests and their helpers, the build and release tools, the simulator `brain/sim.py`,
`brain/sim_modes.py` and `brain/simgear.py`, the panel preview, `native/tests`, the community files and the
requirements files).

### `tools/make_release.py`

Builds the public copy of the project into a folder of its own, then scans it for private data. The working folder is
never changed.

Rules: `RULES` is an ordered list of `(pattern, destination)` pairs, first match wins. Paths are relative with forward
slashes; `*` stays within one folder and `**` crosses folders (`match()` turns a pattern into a regular expression).
`where(path)` returns `"release"`, `"pack"` or `None` (left out).

- Left out: everything in `NOT_SHIPPED` (below); `logs`, `backups`, `downloads`, `reference`; caches and compiled
  Python; `native/bin` and build objects; `ghidra`; `tools/menu_titles`; every file in `docs` except
  `docs/CODE_GUIDE.md` and `docs/BOT_STATUS.pdf`; the map tools' folders (`tools/bsp2obj`, `tools/model2obj`,
  `tools/map_tools`); the MCC art `map_art.py` builds (`tools/view_art/games`, `tools/view_art/maps`); local backup and
  verification scripts; batch files and shortcuts at the project root; and per map the variants, LiDAR scans, learned
  files (`nav_learned`, `los_learned`, `rides`, `wedges`, `shots`, `paint`, `oob`, `stations`, `variant`,
  `moves_review`) and raw geometry and scenario dumps (`*.obj`, `*.xml`).
- Map pack: `maps/*/heightmap.npz`, `maps/*/topdown.png`, `maps/*/glass.json` and `maps/_shapes/**` (Forge piece
  shapes and tag name lists). These are made from the games' own geometry, could be rebuilt by each user with Halo's
  official mod kits, and are too big for the repository.
- Release: per map `callouts.json`, `positions.json`, `features.json`, `objects.json` and `inv_spawns.json`; the
  shared tables `maps/_inputs`, `maps/_looks`, `maps/_vehicles` and `maps/_human`; `brain`, `tools`, `native`,
  `installer`; and the root files `VERSION`, `README.md`, `LICENSE.md`, `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `requirements.txt`, `requirements-dev.txt` and `.gitignore`. Anything else under `maps` is left
  out.

`NOT_SHIPPED` lists research, probe and test-automation scripts and old versions the mod does not run (nothing in the
launcher, the bots, the setup or the tools imports or starts them), plus the tests of those. It includes, for example,
the reverse-engineering helpers (`tools/disasm.py`, `tools/xref.py`, `tools/pe_xref.py` and others), the per-game map
exporters (`tools/export_maps.py`, `tools/h2_export.py`, `tools/h3_export.py`, `tools/reach_export.py`,
`tools/glass_mask.py`), probes, live QC scripts, the native diagnostic programs (`native/diag.cpp`,
`native/filemon.cpp`, `native/watch.cpp`, `native/build_diag.bat`), and the tests of those scripts. Before adding a file to it, check that nothing shipped imports or runs
the file.

`build(out)`:

1. Stops if there are untracked files under `brain`, `tools`, `native` or `installer` that the release would carry,
   because the copy is made from git's tracked files (`git ls-files`): uncommitted new code would be missing.
2. Empties and recreates `out` and `out-map-pack`, but only folders it made itself: each gets a `.release-build` marker
   file, and a folder without one is never touched.
3. Copies every tracked file to its destination (a folder entry such as the bundled MinHook source is copied without
   `.git` or build objects), writes the public `.gitignore` (`PUBLIC_GITIGNORE`: logs, builds, the map tools, a bundled
   Python, the art built from MCC, the map pack files and every PC's own scans and learned data), and prints file
   counts and sizes for release, map pack and left out.

The privacy scan (`scan()`, `scan_text()`, `report()`) reads every text file (by extension) in a folder and fails on:
an e-mail address at the common webmail domains; a path into a user's folder (`C:\Users\<name>`, except `Public`,
`Default` and placeholders such as `%...%` or `<...>`); paths on the development PC's own drives; references to local
development tooling folders; any personal term listed in `.private_terms` (one per line, `#` comments, matched without
case); and Xbox user ids (`0009` followed by 12 hex digits), except the two made-up ids the tests use. E-mail hits are
ignored under `third_party`, where other projects' credits name their authors. `.private_terms` sits at the project
root, is never committed, and is the only place the real terms exist. The scan also counts comments that still quote
development messages; that count is reported but does not fail the scan.

Command lines: `python -I tools/make_release.py [out_folder]` (default: a `release` folder beside the project folder,
plus `release-map-pack`), and `python -I tools/make_release.py --scan <folder>` for the scan alone. Exit code 1 when the
scan finds private data. `build_installer.py` and `human_data.py` import it.

### `tools/build_installer.py`

Builds the Windows installer for a release, `ProjectProvingGrounds-Setup-<version>.exe`, and the Linux and Steam Deck
download, `ProjectProvingGrounds-Linux-<version>.tar.gz`: everything a player needs in one file, with no Python, build tools or anything else to install. Everything is staged in `installer_build` beside the
project folder.

Steps in `main()`:

1. `stage_project()`: runs `make_release.build()` into `installer_build/release`, stops if the privacy scan finds
   anything in the release or the map pack, copies the release into `installer_build/payload` minus `DEV_ONLY`, and
   merges the map pack in.
2. `stage_native()`: runs `native/build.bat` and `native/build_window.bat` (unless `--skip-native`), requires
   `BUILD OK` in each one's output, and copies `botcore.dll`, `inject.exe` and `ppg_window.exe` into the payload's
   `native/bin`.
3. `stage_map_tools()`: copies the folder holding `model2obj.exe` (found by `brain/paths.map_tool`) into the payload's
   `tools/map_tools`; stops if the map tools are not built.
4. `stage_python()`: downloads the official embeddable Python of this PC's exact version
   (`python-<ver>-embed-amd64.zip`, cached in `installer_build/cache`, its SHA-256 printed), extracts it to `python/`,
   rewrites its `._pth` file to the standard library zip, the folder and `Lib\site-packages`, downloads wheels for
   `PACKAGES` (numpy 2.5.3, scipy 1.18.1, Pillow 12.3.0, the same pins as `requirements.txt`) for `win_amd64` and this
   Python version, installs them into the bundled site-packages, and checks that the bundled Python imports numpy,
   `scipy.sparse.csgraph`, PIL, ctypes, winreg and sqlite3.
5. `stage_texts()`: writes `installer_build/license.txt` from `NOTICE.md` and `LICENSE.md` for the installer's license
   page, and the payload gets `VERSION`.
6. `compile_setup()`: finds Inno Setup's `ISCC.exe` (`iscc()`: the per-user and machine-wide Inno Setup 6 folders,
   then the PATH) and runs it with `/DAppVersion=<VERSION>`, `/DPayload=<payload>` and `/DBuildDir=<installer_build>`
   over `installer/ProjectProvingGrounds.iss`; prints the size and SHA-256 of the result.
7. `linux_bundle()`: the Linux and Steam Deck download, `installer_build/ProjectProvingGrounds-Linux-<version>.tar.gz`.
   It holds `install.sh` and `uninstall.sh` from `installer/linux` at the top of a
   `ProjectProvingGrounds-Linux-<version>/` folder and the same payload under its `payload/` folder (the mod's Windows
   parts run through Proton). User and group ids and names are blanked, folders get mode 755, shell scripts get LF line endings and
   the executable bit (a Windows checkout may have CRLF), other files 644. It prints the size and SHA-256.
8. `zip_map_pack()`: zips `installer_build/release-map-pack` into
   `project-proving-grounds-map-pack-<version>.zip`, the separate download developers unzip over a source checkout.

Command line: `python -I tools/build_installer.py [--skip-native]`; `--linux-only` makes only the Linux tar.gz, from
the payload already staged. It needs the map tools built, Visual Studio's C++
build tools (unless `--skip-native`), Inno Setup 6, and internet access the first time (for the embeddable Python and
the wheels).

### `tools/human_data.py`

Builds the optional human play dataset for a release, `human-play-data-<version>.zip`. It contains:

- `collect/<file>.jsonl`: every Data collector recording on the PC (`logs/collect_*.jsonl`), passed through
  `collector.without_keys()` so no key data from older recordings is included;
- `matches/<match>.zip`: every recorded match still on the PC (`logs/trace_*_<date>-<time>.jsonl`), exported by
  `tools/match_export.py` (names replaced by Player 1, Player 2 and so on, Xbox ids removed);
- `human/`: the human reference numbers in `maps/_human`;
- `README.md`: taken from `docs/HUMAN_DATA.md`, which describes the format.

Every text that goes in is scrubbed of the Windows user folder (`match_export.scrub()`) and scanned with
`make_release.scan_text()` and the `.private_terms` terms; a single hit stops the build. The zip is written as `.part`
and renamed when complete. Command line: `python -I tools/human_data.py [out.zip]` (default:
`installer_build/human-play-data-<version>.zip`).

### `tools/run_tests.py`

Runs every `tools/test_*.py` in sorted order, each in its own process (`python -I <test>` from the `tools` folder, 900
second timeout), prints one line per file (`ok` or `FAIL`, seconds taken, the last line the test printed), then the
last 12 lines of each failure, and exits 1 when any test failed. An optional argument is a substring filter on file
names. Command line: `python -I tools/run_tests.py [name-filter]`.

### `tools/testdata.py`

The helper for tests that need data the public repository does not ship: each user's own LiDAR scans and the learned
files beside them, recordings in `logs/`, built binaries, or the map pack. A test calls one of these before using the
data:

- `need(*paths, why="")`: every path (relative to the project) must exist; otherwise it prints
  `SKIP <test>: needs <missing paths> (<why>)` and exits with code 0.
- `need_lidar(*maps)`: `need()` on `maps/<map>/lidar.json` for each map, with the hint to run LiDAR mapping on them.

Because a skip exits 0, a fresh copy of the project passes its own suite, while a PC with the data runs every test in
full. About twenty tests use it (LiDAR scans of Spire, Boneyard, Construct, Guardian, Sidewinder and others; the built
`inject.exe`; recorded traces; Forge recordings; the map pack). A few other tests skip in the same way by their own
checks: the panel tests without `panel_preview.exe`, and the tag name tests without MCC's map files.

### `tools/baseline_compare.py`

Compares test results across two commits, to show which old expectations a change broke. It runs three suites: (1) the
old commit's code with its own tests, (2) the new commit's code with its own tests, and (3) the old commit's tests
against the new commit's code. Every failure in (3) is either a deliberate, reviewed change of expected behaviour or a
bug the change fixed.

Each run is a `git archive` extract of `brain`, `tools` and `native/shared.h` in a temporary folder. `maps` is rebuilt
there with a directory junction per map folder pointing at this repository's maps (read only), except `maps/_inputs`,
which is taken from the commit itself because the decoded button tables change with the code. `remove()` deletes the
junctions first and never follows them, and stops before any delete if a junction could not be removed. Results go to
`logs/verify/baseline_<old>_<new>.txt` and the console. Command line:
`python -I tools/baseline_compare.py <old commit> <new commit>`.

### `tools/clean_bin.py`

Removes old builds from `native/bin`: every `botcore*.dll` except the newest two by date (the launcher and
`tools/play.py` inject the newest; the one before may still be loaded in a running MCC), per-run copies of diagnostic
DLLs, objects whose source file is gone, and `test_*.exe` programs whose `.cpp` is gone. Files that are locked (loaded
in MCC) are skipped and listed. The removed DLLs' `.log` files are kept, moved to `logs/botcore_logs`. Command line:
`python -I tools/clean_bin.py [--dry]` (`--dry` lists what would go).

### `tools/zoom_match.py`

Checks a match recording for how the game took the bots' zoom requests. For each bot it pairs the zoom level the brain
asked for (trace field `cmd`, bits 12 and 13 of the button word) with the game's own zoom byte one tick later (trace
field `uz`, recorded for CE, Halo 2 and Halo 3), because the game takes a request on the next tick. Asked 0, 1 and 2
should read 0xFF, 0x00 and 0x01. Gaps over 0.1 s (deaths, respawns) are skipped. It prints the match rates per level and
the zoom ticks by weapon, and writes `logs/verify/zoom_match_<trace>.txt`. Command line:
`python -I tools/zoom_match.py logs\trace_<map>_<stamp>.jsonl`.

### `installer/ProjectProvingGrounds.iss`

The Inno Setup 6 script. `build_installer.py` compiles it with three defines: `AppVersion` (default `0.0.0`),
`Payload` (the staged files; required, compilation stops without it) and `BuildDir` (where `license.txt` is and where
the Setup file is written).

Setup settings: a fixed `AppId`; installs per user without administrator rights (`PrivilegesRequired=lowest`) into
`{autopf}\Project Proving Grounds`, which for a per-user install is `%LOCALAPPDATA%\Programs\Project Proving Grounds`
(the dialog may still offer an all-users install); x64 only, Windows 10 or later; LZMA2 ultra solid compression; the
license page from `license.txt`; modern wizard style; and `CloseApplications=yes`.

Pages and what they do:

- The usual license, folder and tasks pages. The one task is an optional desktop shortcut. The Start Menu shortcut
  (always) and the desktop one run `python\pythonw.exe -I tools\launcher.py` from the install folder with the
  installer's icon.
- The Windows Security exclusion page (required), created in `InitializeWizard` after the tasks page. It explains that
  the bots are loaded into MCC by a small injector, that Windows Security treats injectors as suspicious and usually
  deletes them, that Setup adds one exclusion for the mod's own program folder (`native\bin`) and nothing else, that
  Windows asks for administrator permission when it is added, that uninstalling removes it, and that users of another
  antivirus should add the same folder there. Its one option is ticked. Unticking it and pressing Next shows a
  confirmation (No is the default) explaining that the injector will most likely be deleted and how to add the
  exclusion by hand. `ShouldSkipPage` skips the page on an update when the install folder already has the marker file
  `installer\windows-security-exclusion.txt`.
- The finish page offers to open the launcher with `--setup` (the first-time setup), not in silent installs.

Install logic:

- `PrepareToInstall`: on an update (the install already has `native`), it refuses to continue while
  `MCC-Win64-Shipping` is running, since MCC with the bots loaded holds `botcore.dll`, and it ends the mod's own
  processes running from the install folder (the launcher, the tools' servers and windows), which Restart Manager
  cannot close.
- `CurStepChanged(ssInstall)`: when the exclusion is wanted (`WantExclusion`: not already added; silent installs add it
  unless `/EXCLUSION=no`; otherwise the page's option), it runs `Add-MpPreference -ExclusionPath <app>\native\bin` in an
  elevated PowerShell before the files are copied, so Windows Security does not delete the injector while they are. If
  that fails (permission refused, or another antivirus manages Windows Security), a message explains how to add it by
  hand. At `ssPostInstall` the marker file is written with the excluded folder when it was added.
- `[InstallDelete]`: an update first removes the previous version's code and documents so files a release dropped do
  not stay behind: the `docs`, `ghidra`, `native\tests`, `tools\menu_titles` and `__pycache__` folders, and
  `tools\*.py`, `tools\*.html`, `tools\*.ps1`, `brain\*.py`, `native\*.cpp`, `native\*.h`, `native\*.bat`, the
  community files and `requirements*.txt`. The player's logs, maps, LiDAR scans and the art the setup built are kept.
- `[Files]` copies the whole payload recursively.

Uninstall logic (`CurUninstallStepChanged`):

- It ends the mod's processes still running from the install folder, removes the Windows Security exclusion named in
  the marker file (elevated `Remove-MpPreference`), and asks whether to keep the LiDAR scans, learned map data and
  recorded matches. A silent uninstall keeps them (`/SUPPRESSMSGBOXES` answers Yes).
- Keeping: after the uninstall, `native`, `python`, `tools` and `brain` are deleted and the `maps` and `logs` folders
  stay in the install folder for a later install. Not keeping: the whole install folder is deleted.
- `[UninstallDelete]` also removes `%LOCALAPPDATA%\ProjectProvingGrounds`, the app window's WebView2 data
  (`tools/appwindow.py`).

### `installer/linux/` (Linux and Steam Deck)

Bash scripts that install and run the mod on Linux and Steam Deck (SteamOS), for MCC on Steam through Proton. They ship
in the Linux tar.gz (`tools/build_installer.py linux_bundle`) and in every install. `.gitattributes` keeps `*.sh` at
LF line endings. Nothing goes into MCC's own files or its Proton prefix, and no root rights are needed.

How it fits together: MCC runs through Proton (Wine), and so do the mod's Windows parts (the bundled Windows Python,
`inject.exe`, `botcore.dll`). In the game, Steam's launch option runs `tools/launch.py` inside MCC's own Proton session
(same prefix, same wineserver), which starts the game and loads the bots; botcore then starts the brain inside that
session as on Windows. Outside the game (the launcher, the first-time setup, the tools) the mod uses a Wine prefix of
its own, run with MCC's Proton, so MCC's prefix (`compatdata/976730`) is never changed or held open. Wine reaches the
mod's folder as drive Z:.

- `common.sh` (sourced by the others). `ppg_steam_roots` finds Steam's folders (native `~/.steam/steam`,
  `~/.steam/root`, `~/.local/share/Steam`, and Flatpak Steam); `ppg_libraries` lists every library in
  `libraryfolders.vdf` (SD cards included); `ppg_winpath` turns a Linux path into the Windows path Wine sees.
  `ppg_find` sets Steam's folder, MCC's folder and library (the library whose `appmanifest_976730.acf` names an
  existing install folder), MCC's `compatdata`, the Proton to use (the one MCC last ran with, from line 3 of
  `compatdata/976730/config_info`, else the newest Proton in the libraries or `compatibilitytools.d`) and the Steam
  Linux Runtime that Proton asks for in its `toolmanifest.vdf` (sniper or soldier), stopping with a clear message when
  Steam, MCC or Proton is missing. `ppg_data_dir` is where the mod lives:
  `~/.local/share/project-proving-grounds` (with `XDG_DATA_HOME` honoured), or inside Flatpak Steam's own data folder,
  the only place its launch option can reach. `ppg_wine` runs a Windows program of the mod in the mod's prefix
  (`<data>/prefix`) with MCC's Proton, through the runtime when there is one, with `PPG_LINUX=1` and `HB_STEAM_COMMON`
  set to the folder MCC is in, and waits for it. `ppg_port_open` and `ppg_mcc_running` are small checks. Overrides:
  `PPG_STEAM`, `PPG_MCC`, `PPG_PROTON`.
- `install.sh [--download] [--payload DIR] [--no-setup]`. Finds the payload beside it (the unpacked tar.gz, or the
  install it is in), else downloads the newest Linux release from the project's GitHub releases with `curl`. Stops if
  MCC is running. Copies the payload to `<data>/app`; an update first deletes the previous version's code and documents
  (`docs`, `ghidra`, `native/tests`, `tools/menu_titles`, the code files in `tools`, `brain` and `native`) and keeps the player's logs, maps, LiDAR scans,
  `user/` settings and the art the setup built. Runs the first-time setup in the mod's prefix (output also in
  `logs/linux_setup.txt`), writes the "Project Proving Grounds" menu entry (and a desktop copy when there is a Desktop
  folder) that runs `ppg-launcher.sh`, and prints the Steam launch option to paste (copied to the clipboard with
  `wl-copy` or `xclip` when present).
- `ppg-run.sh`, the Steam launch option (`"<app>/installer/linux/ppg-run.sh" %command%`). When Steam's command runs
  `MCC-Win64-Shipping.exe` (the anti-cheat off choice), it keeps the Proton part of the command and swaps the game's
  program for the mod's Windows Python running `tools/launch.py --exe <MCC's program> -- <its arguments>`, with
  `PPG_LINUX=1` and `HB_MCC` set to that MCC folder; output goes to `logs/linux_play.txt`. Any other command (the
  anti-cheat on choice, `mcclauncher.exe`), or a mod folder missing its Python or `launch.py`, runs exactly as Steam
  asked, so the bots never load into an anti-cheat session.
- `ppg-launcher.sh`, run by the menu entry. If the launcher already answers on 8793 it opens the page again; else it
  starts `tools/launcher.py --no-window` in the mod's prefix (output in `logs/launcher/linux.txt`), waits up to 180 s
  for the port and opens the page in the system's browser with `xdg-open` (there is no WebView2 under Wine).
- `uninstall.sh [--yes]`. Stops if MCC is running. Asks whether to keep the LiDAR scans, learned map data and recorded
  matches (`--yes` keeps them without asking): keeping leaves `maps`, `logs` and `user` in the app folder, not keeping
  deletes it. Removes the mod's prefix and menu entries, and leaves a stand-in `ppg-run.sh` that only runs Steam's
  command, so MCC keeps starting until the player clears the launch option.
- `icon.png`: the menu entry's icon.

### `native/panel_preview.cpp` and `native/build_preview.bat`

`panel_preview.exe` draws the BOTS panel (`native/bots_panel.cpp`, with `native/model_view.cpp` for the 3D bot)
offscreen without MCC, to check its look in every state and size, and self-tests the roster operations. It creates a
D3D11 device (hardware, else WARP), renders into an offscreen target with Dear ImGui's DX11 backend, the Bahnschrift
font scaled to the height, and writes the frame as a PPM file (tests convert it to PNG). It reaches into the panel
through debug entry points (`bots_panel_debug_*`) to select tabs, popups, the edited bot, the view's yaw and zoom, and
the effect time. The panel's sounds are printed (`sound <kind> <volume>`) instead of played.

Options:

- `--selftest`: roster checks (filling teams, names, removing, tiers, saving and loading profiles, per-bot overrides);
  prints failures and exits nonzero on any.
- `--state <name>`: `normal`, `empty`, `off`, `lidar`, `scaling`, `collector`, `collectoroff`, `ce`, `eight`, `full`,
  `long`, `quick`, `quickscaling`, `clear`, `advanced`, `advancedprof`, `mod`, `reroll`, `rerollerr`, `modnone`,
  `edit<game>[flags]` (the profile view of a game as rolled), `bugbutton`, `bug`, `bugtext`.
- `--size WxH`, `--out <file.ppm>`, `--yaw <radians>`, `--zoom 0..1`, `--time <s>`, `--bot <n>`,
  `--set h3.elite_helmet=12,...` (hand-set looks).
- Input replay: `--click x,y;x,y` (real mouse clicks in order), `--keys tab*3,stab,space,down,enter,esc,pad_a,...`
  (keyboard and controller presses after the clicks), `--hover x,y`.
- `--readonly` (the profiles file made read-only, to test a failing save), `--sounds 0-100`, `--wavs <dir>` (writes the
  panel's five sounds as WAV files and exits).

`native/build_preview.bat` finds Visual Studio's C++ tools with `vswhere`, then builds `native/bin/panel_preview.exe`
(objects in `native/bin/preview`) and `native/bin/test_zoom.exe`, an offline check of how a bot's wanted scope level
reaches CE, Halo 2 and Halo 3 (`native/shared.h` `hb_set_zoom`). Each prints `BUILD OK <file>`. `test_pad.py`,
`test_panel_sounds.py` and `test_backpack_view.py` drive `panel_preview.exe` and print a skip line without it.

### The tests: `tools/test_*.py` and `native/tests/`

How tests are written:

- One file per subject, a plain Python program with no test framework. The module docstring states what it checks as a
  numbered list, and a `usage:` line gives the command and its success line (`python -I test_x.py -> "x OK"`). Each
  numbered check is written so it fails on the code before the change it covers.
- A test puts the project root on `sys.path`, imports the brain or tool modules directly, builds the situation it
  needs (made-up players and snapshots from `brain/core.py`, real map knowledge from `maps/` through
  `brain/maps.get_map()`, fake game memory for the readers, or a short fixed-seed match in the offline simulator
  `brain/sim.py`), and checks with `assert` or a list of failures. It prints one success line and exits 0, or prints
  what failed and exits nonzero.
- Tests needing per-PC data call `testdata.need()` / `need_lidar()` first and skip with exit 0. Many tests use real
  level data, so unzip the map pack before running the suite.
- The C++ tests in `native/tests` are small programs wrapped by Python tests that compile them with
  `cl` (through `brain/paths.vcvars()`) into a temporary folder and run them. Without Visual Studio's C++ tools these
  two tests fail rather than skip.
- Run one test with `python -I tools\test_<name>.py`, all with `python -I tools\run_tests.py`, a subset with
  `python -I tools\run_tests.py <filter>`. Any change that touches logic should come with a test that fails without it.

`native/tests/`:

- `test_faults.cpp`: includes `native/h4f.cpp` and `native/h3.cpp` directly and runs botcore's Halo 4 / H2A hook on fake
  game memory in the same process: faults in a bot's boarding, in a command and elsewhere in the players-update hook
  are caught, logged and reported (`cmd_fault`); H2A's first-tick hold; Halo 4 and H2A vehicle exit through the game's
  own exit function (a stand-in at its address) and refusal when the code bytes differ; Halo 4's boarding pick; Halo
  3's seat interaction (`h3_board`) and flag pickup on an Elephant (`h3_pickup_target`). Prints `faults OK`. Built and
  run by `tools/test_native_faults.py`.
- `test_pick.cpp`: the `native/shared.h` helpers `hb_pick_loose` (which loose weapon a bot's Use takes, by view and
  distance) and `hb_spawn_take` (when a bot's new unit moves to its Invasion spawn). Built and run by
  `tools/test_native_pick.py`.

Overview of the Python tests by area (one line per file, without the test names `make_release.py` leaves out):

Game reading, the live loop and the brain's plumbing

- `test_buttons.py`: decoded button tables (`maps/_inputs`) reach `botctl.set_button_map` in `hb_btn_entry` layout, with the clear-then-set apply rule.
- `test_live_bots.py`: the live glue (snapshot, flag and death events, button encoding) against a fake game reader.
- `test_think_dt.py`: the brain keeps real-time speed on a slower PC (`live_bots.think_dt`), checked in the simulator.
- `test_bad_places.py`: positions read as NaN or millions of units out are rejected or kept from the last good read; huge sight lines and NaN nav queries are harmless; bug report copies grow incrementally.
- `test_weapon_names.py`: how the Halo 3, ODST, Reach and Halo 4 readers name guns from fake game memory.
- `test_objective_names.py`: objective tags seeded from the map's tag names (Halo 4, H2A) and `flags_by_stand`.
- `test_h2_objectives.py`: Halo 2 Assault bombs found by tag name on a stub of the game's memory.
- `test_vehicle_up.py`: a vehicle's up vector derived from its facing where the reader has no orientation (Reach), with bad reads rejected.
- `test_loadouts.py`: loadout changes (`brain/loadouts.py`, `live_bots.loadout_check`).
- `test_route_memory.py`: route field caches stay within a memory budget sized from the PC's memory, with the same answers as an unbounded cache.
- `test_free_names.py`: every brain and tools file is parsed and no name is read that nothing binds.
- `test_roster.py`: `botcore.ini` bot lines parse and `tools/play.py` adds exactly those bots.
- `test_injector.py`: `inject.exe` restored when Windows Defender deletes it (`tools/botctl.py injector`); needs the built injector.
- `test_conflicts.py`: the mod conflict scan finds proxy DLLs and ASI plugins in a made-up MCC folder, moves them aside and restores them.
- `test_mcc_folder.py`: how the mod finds MCC (`brain/paths.py`) on fake folder layouts: Steam libraries in both `libraryfolders.vdf` formats, several MCC copies, the folder the player picks or one near it, `HB_MCC` over the choice, back to automatic, and how Play starts a copy Steam does not (`tools/launch.py`).
- `test_linux_install.py`: the `installer/linux` scripts run with bash on a fake home (a library on an "SD card", a fake Proton and Steam Linux Runtime): the install finds them, copies the mod, runs the setup in the mod's own prefix and writes the menu entry; the launch option swaps MCC's program for `launch.py` in the same Proton command and leaves the anti-cheat on command alone; the uninstall keeps the player's data and leaves the stand-in. Skipped without bash.
- `test_carnage_names.py`: `tools/carnage_names.py` fills in bot rows MCC left blank in the post-game report and leaves other rows alone.

The BOTS panel, profile view and models

- `test_pad.py`: every panel menu works by controller on the offline panel (`panel_preview.exe --keys pad_...`).
- `test_panel_sounds.py`: the panel's sounds come from ImGui's state once per frame, checked on the offline panel's printed sounds.
- `test_backpack_view.py`: picking a Halo 3 backpack turns the 3D bot so it shows; needs the offline panel and the models.
- `test_model_pose.py`: the 3D bots hold their guns by the game's hand markers (IK mount, wrist roll), `prune()` keeps used textures, and the exported models pass the hold checks where they exist.
- `test_emblems.py`: each bot's own MCC emblem roll and composition (`brain/emblems.py`), with the extracted art where present.
- `test_native_faults.py`, `test_native_pick.py`: build and run the two C++ tests above.

Difficulty, aim and combat

- `test_scaling.py`: Scaling difficulty (`brain/scaling.py`): reaction, aim error and tremor scale with the rating, other behaviour is Legendary's, with its limits and custom profiles.
- `test_brain_tactics.py`: every tier shares the same hands and differs in behaviour; commitment to a kill; situational cover.
- `test_easy.py`: Easy bots take no detours for guns and remember a man they saw for a few seconds.
- `test_easy_aim.py`: Easy aims for the head 20% of the time and zooms only with sniper-type weapons.
- `test_turn_speed.py`: turn speed rises by tier, large turns are limited per tick, and walking is re-aimed.
- `test_focus.py`: a bot with an order keeps fighting the enemy it sees, through short losses of sight.
- `test_clear_line.py`: no shot without a clear line, and nothing run into.
- `test_close_combat.py`: close-range fixes: armor lock release, melee at arm's length and related cases.
- `test_combat_oct31.py`, `test_combat_oct31b.py`: two rounds of combat behaviour fixes (sword charges, pulling back when outnumbered and hurt, and others), each check failing on the code before.
- `test_crouch_aim.py`: aim points on crouched targets across body sizes.
- `test_preaim_moves.py`: jump and strafe rates by role and pre-aiming.
- `test_tracker.py`: Legendary bots use the motion tracker, never when the match settings hide enemies from it.
- `test_sword.py`: when the energy sword comes out, is kept, and runs a man down.
- `test_weapons.py`: gun handling (dry weapons, rockets near oneself, burst fire, DMR pace, charge weapons, zoom).
- `test_pickup_swap.py`: with both slots full, a bot holds the gun to discard before pressing pick up.
- `test_objective_nades.py`: grenades thrown into the objective in a short simulated Spire Invasion.
- `test_spec_pending.py`: two weapon-fire expectations (SMG bursts at medium range, a shotgun holding fire at 3 units) kept apart from their suites until the expected behaviour is confirmed.

Equipment and armor abilities

- `test_equipment.py`: equipment, armor abilities and their counters (`brain/equipment.py`).
- `test_equipment_audit.py`: the equipment rules of the behaviour audit (camo, radar and others), each failing on the code before.
- `test_ability_hold.py`: abilities pressed or held the right way in every game, and the jetpack used well; needs LiDAR scans.
- `test_player_abilities.py`: Reach abilities used as a skilled human uses them (sprint hold times, evade distance and others).
- `test_live_misses.py`: press shapes by the game's hold rules, sprint only at full stick, release of refused armor lock.
- `test_grenade_dash.py`: evade and thruster out of a grenade's blast and in to finish.
- `test_jetpack_moves.py`: jetpack chases and high ground; needs LiDAR scans.

Movement, navigation and terrain

- `test_edge_guard.py`: the edge guard on H2A Lockdown: braking at deadly edges, dropped fight jumps, steering back.
- `test_brake_pingpong.py`: the edge guard does not brake against motion its own brake made.
- `test_fall_steer.py`: falls onto Spire's heat vents steered to land; needs LiDAR scans.
- `test_drop_stuck.py`: a walker stuck stepping down reports the landing as the stuck spot.
- `test_step_down.py`: the nav's planned step down onto a ledge passes the edge guard.
- `test_stairs.py`: stairs on Halo 4 and H2A levels (`terrain.stair_rule`).
- `test_rails.py`: handrails cost extra in the nav and are seen by the waist ray.
- `test_links.py`: a jump a person landed (a LiDAR link) is offered to bots by the nav.
- `test_exit_held.py`: big drops are taken only when the exit is held (`Bot.exit_held`).
- `test_carrier_exits.py`: carriers ride lifts, cannons, drops and teleporters only to exits a teammate holds.
- `test_nav_z_forge.py`: simulated walkers stay on a Forge canvas floor and climb its stairs.
- `test_terrain_guards.py`: no sight line to a NaN position, long planned drops, and a carrier's safe nav; needs LiDAR scans.
- `test_stuck_learning.py`: stuck spots are learned only from several reports by several bots, with a per-match cap.
- `test_oob.py`: out-of-bounds deaths are detected, learned and kept off.
- `test_runup_lineup.py`: a carrier lines up behind a person's run-up before a running jump.
- `test_carrier_jump.py`: the core carrier's jump onto Spire's delivery platform.
- `test_spire_drops.py`: Spire's way down (drops onto the vents, one-way lifts); needs LiDAR scans.
- `test_spire_lift.py`: Spire's gravity lifts ridden as lifts, not jumped as links.
- `test_tele_watch.py`: a bot chased through a teleporter steps off the exit and watches it.
- `test_arrival.py`: ambushing the landing of an enemy on a teleporter, cannon or lift; needs LiDAR scans.
- `test_pit_targets.py`: Construct's pit: callouts of a man on the top floor do not send listeners into the pit.

Objective modes and team directors

- `test_modes.py`: objective game types (`brain/modes.py`): variant names, places, Territories capture, Assault goals, Infection teams.
- `test_modes_reading.py`: objective state reads such as One Bomb's attacking team.
- `test_director_map.py`: map rules in the director on Blood Gulch (power positions and others); needs LiDAR scans.
- `test_ffa_sides.py`: one director per team, side or bot, including Infection and Juggernaut lobbies with teams off.
- `test_alt_post.py`: a post the bot gave up on is replaced by a spot beside it, never a roam.
- `test_backup.py`: holders call for backup when outnumbered, and the carrier's escorts stay with him.
- `test_blitz.py`: when the team blitz applies in each mode.
- `test_carry_play.py`: the carry as a team play (escorts, screens, cutoffs) and the score posture.
- `test_ctf_effort.py`: CTF effort, split attacks and area defense; needs LiDAR scans.
- `test_ctf_grab.py`: CTF runners go in for the flag.
- `test_ctf_roles.py`: CTF roles: play the objective, help the carrier, defend while others pull; needs LiDAR scans.
- `test_ctf_wave.py`: the CTF attack as a wave.
- `test_flag_returns.py`: where a CTF carrier scores (`Director.capture_point`).
- `test_one_flag.py`: One Flag played in the simulator and by the director.
- `test_king_take.py`: King of the Hill: taking a hill the enemy holds.
- `test_sim_spot_modes.py`: King of the Hill, Oddball and VIP in the offline simulator (`brain/sim_modes.py`).

Invasion

- `test_invasion.py`: Reach Invasion setup read from each map's scenario, one-way shields on the nav; needs LiDAR scans.
- `test_attack_push.py`: Invasion attackers keep to the objective and come at it more than one way.
- `test_boneyard_spawns.py`: Boneyard respawns by its spawn screen names per tier.
- `test_honor_spawn.py`: Invasion respawns by tier and side preference.
- `test_round_change.py`: Invasion's round change read correctly.
- `test_loose_core.py`: attackers take a loose Invasion core.
- `test_invasion_pileon.py`: urgency and pile-on in Spire Invasion; needs LiDAR scans.
- `test_spire_flags.py`, `test_spire_flags2.py`, `test_flags_094415.py`: reported moments from recorded Spire Invasion matches (man cannons, swaps, stalls), each checked at its moment; need LiDAR scans.

Vehicles

- `test_vehicles.py`: vehicle kinds per game, doors and seats (`brain/vehicles.py`, `Director.vehicle_orders`).
- `test_vehicle_crew.py`: crews, including a Reach Falcon pilot who has no gun.
- `test_vehicle_jobs.py`: vehicles driven with a job, riders called, tanks kept and aimed.
- `test_vehicle_roles.py`: roles by vehicle (artillery, splatter and others).
- `test_vehicle_targets.py`: target scoring for each seat.
- `test_vehicle_threats.py`: rams and threats, such as never ramming a man in armor lock.
- `test_vehicle_dead.py`: wrecks from each game's destroyed bit (`DEAD_AT`, CE from its body field), health where `object_get_health` reads it, and wrecks and duds avoided by drivers' orders and the bots' own picks.
- `test_vehicle_wedge.py`: a wedged driver backs out.
- `test_wedges.py`: wedge spots learned from recordings and kept off the vehicles' ground; needs LiDAR scans.
- `test_boarding.py`: boarding and anti-tank play on foot: when a bot boards (a slow tank looking away from farther), a tank boarded from its front, melee aboard (a press every 0.55 s, no grenade in Reach), the plasma launcher's lock on a vehicle.
- `test_anti_vehicle.py`: the Grenadier's anti-vehicle mission and grenades.
- `test_elephant.py`: Sandtrap's Elephants as a way in and for flag delivery.
- `test_air_guard.py`: pilots do not fly into structures beside them.
- `test_air_stuck.py`: pilots that hit a wall get unstuck and do not fly back into it.
- `test_flee_stall.py`: fleeing boarders and boarding that never takes do not stall drivers.
- `test_getaway.py`: the getaway ride for a carrier; needs LiDAR scans.
- `test_runner_exit.py`: a runner at the wheel gets out at the enemy flag.

Map knowledge, LiDAR and Forge

- `test_forge_shields.py`: Forge shields by their groups (two way, one way, no pass) on Forge World.
- `test_forge_surfaces.py`: Forge building pieces face by face (`brain/forge.py`, `Terrain.add_faces`).
- `test_forge_dynamic.py`: Forge pieces that come and go (`brain/forge.py PieceWatch`): a wall standing up after the nav was built is a wall while it stands and open again once gone; a built-in piece that goes is filed as dynamic once and left out of the next match's nav.
- `test_variants.py`: map variants filed under their base map with a nav that grows; needs Forge recordings.
- `test_stations.py`: stations classified from real tag names in each Forge game, kept and saved.
- `test_tag_names.py`: every saved tag name list matches its `.map` file; skips without MCC.
- `test_reach_tag_names.py`: Reach tag names checked against tag ids read on Forge World; skips without the map.
- `test_paint.py`: hand painting, roofless views and the LiDAR Roombas.
- `test_rides.py`: driven and flown rides added to the map's LiDAR data.
- `test_shot_recipes.py`: shot recordings and their replay.
- `test_lidar_spots.py`: the LiDAR simulator's controls and spots to cover; needs the map pack.
- `test_view_port.py`: the LiDAR 3D view's server port shared correctly between a stored view and a live match.
- `test_lidar_objectives.py`: every gametype objective place found (`objective_points`), one bot to each at a time within `OBJECTIVE_SHARE`, reached places saved in `lidar.json` and not sent again, Halo 3's flag and bomb stands classed as objectives (`brain/stations.py`), and the Simulator on its own port.

The Observer, recordings and release tools

- `test_observer.py`: the Observer's server endpoints and text mode; needs a recorded trace.
- `test_observer_export.py`: the match export removes names, Xbox ids and user folders.
- `test_crosshair.py`: a player's line of sight and crosshair for the Observer, with no key reading.
- `test_collector.py`: the Data collector records no keyboard, mouse or controller input, and the player stats are right.
- `test_bug_reports.py`: bug reports filed per match with the recording.
- `test_make_release.py`: the release rules and the privacy scan.

## Building from source

### What you need

| Requirement | Needed for |
|---|---|
| Windows 10 or 11, 64-bit | everything |
| Halo: The Master Chief Collection (Steam) | playing, the first-time setup and the map tools' input |
| Git | the source; the release builder also reads git's tracked files |
| Python 3.14, 64-bit, with `requirements.txt` | the brain, every tool and the tests |
| Visual Studio 2022 Build Tools with "Desktop development with C++" (MSVC) | `native/build.bat`, `build_window.bat`, `build_preview.bat`, the C++ tests |
| The map tools (`bsp2obj`, `model2obj`) and the .NET 10 SDK to build them | the 3D bots, the effect sprites, rebuilding level data |
| Inno Setup 6 | building the installer only |

`requirements.txt` pins the three packages the mod uses: numpy 2.5.3, scipy 1.18.1 and Pillow 12.3.0
(`python -m pip install -r requirements.txt`). `requirements-dev.txt` adds capstone 5.0.7 and pefile 2024.8.26 for
disassembling MCC's DLLs; the scripts that use them are not part of the public repository, so building and testing do
not need them.

`python -I brain/paths.py` prints what this PC has: Steam's libraries, MCC, each official mod kit, Visual Studio and the
map tools. Every path is found automatically (Steam's registry key and library list, `vswhere` for Visual Studio), and
an environment variable overrides each: `HB_STEAM_COMMON`, `HB_MCC`, `HB_KIT_<NAME>` (for example `HB_KIT_H3EK`),
`HB_VCVARS` and `HB_MAP_TOOLS`.

### First build

```
git clone <repository>
cd project-proving-grounds
python -m pip install -r requirements.txt
rem unzip the map pack over this folder (it fills maps\)
native\build.bat
native\build_window.bat
python -I tools\setup.py
python -I tools\launcher.py
```

1. The map pack. Height maps, top-down pictures, glass masks, Forge shapes and tag name lists (about 490 MB) are a
   separate download beside each release, too big for the repository. Unzip it over the project folder. Without it
   the bots still run, but on fewer maps and with less map knowledge, and many tests cannot load their levels.
2. The map tools. Build Proving Grounds Map Tools (its `build.bat`, .NET 10 SDK) in a folder named
   `proving-grounds-map-tools` beside this one, or copy an installed release's `tools\map_tools` folder into
   `tools\map_tools`, or point `HB_MAP_TOOLS` at the folder holding the two programs.
3. `native\build.bat [tag]` finds Visual Studio with `vswhere`, loads `vcvars64.bat`, and builds
   `native\bin\botcore.dll` (from `botcore.cpp`, `overlay.cpp`, `bots_panel.cpp`, `model_view.cpp`, the per-game files
   `h2.cpp`, `h3.cpp`, `reach.cpp`, `odst.cpp`, `h4f.cpp`, plus `spawnhook.cpp`, `report.cpp`, `film.cpp`, Dear ImGui
   and MinHook from `native\third_party`, static runtime) and `native\bin\inject.exe`. A tag builds
   `botcore_<tag>.dll` instead: a new file name while a running MCC still holds an older DLL. The launcher and
   `tools/play.py` load the newest `botcore*.dll` by date, and `tools/clean_bin.py` removes old ones. After compiling,
   it runs `tools/panel_art.py`, then `tools/make_models.py` if the Halo 3 model is missing and `tools/fx_art.py` if
   the fire sprite is missing. Those steps use the `python` on the PATH, and their failures do not fail the build: it
   ends with `BUILD OK bin\<name>.dll` once both programs compiled.
4. `native\build_window.bat` builds `native\bin\ppg_window.exe`, the app window (WebView2, linked with the static
   WebView2 loader in `native\third_party\webview2`) that the launcher and the tools open their pages in.
5. `python -I tools\setup.py` builds everything that comes from your own copy of MCC (bot profiles, map pictures,
   logos, 3D bots, effects, emblems, the looks file) and switches match recording on. `--status` shows what is there;
   `--force` rebuilds everything.
6. `python -I tools\launcher.py` opens the launcher. A developer copy runs with the Python it was started with; an
   installed copy uses its bundled `python\pythonw.exe` (the launcher restarts itself under `python.exe` with a hidden
   console, so the programs it starts do not open console windows).

For the C++ panel preview and the scope check, run `native\build_preview.bat`; it builds `panel_preview.exe` and
`test_zoom.exe` into `native\bin`.

### Running the tests

```
python -I tools\run_tests.py              every tools\test_*.py, one line each
python -I tools\run_tests.py scaling      only the files whose names contain "scaling"
python -I tools\test_scaling.py           one test on its own
```

Each test runs in its own process. Tests that need data each PC makes for itself (LiDAR scans, learned files, recorded
matches, built binaries, MCC's map files) print `SKIP` with what would enable them and pass. Build `native\build.bat`
and `native\build_preview.bat` first to run the injector and panel tests in full, and unzip the map pack. The two native
tests compile their C++ programs themselves and need Visual Studio's C++ tools. To see which expectations a change
broke, compare two commits with `python -I tools\baseline_compare.py <old> <new>`.

### Making a release and the installer

1. Set the version in `VERSION`.
2. Commit every new file under `brain`, `tools`, `native` and `installer`: the release is made from git's tracked
   files, and the builder stops when the release would miss uncommitted code.
3. Make sure `.private_terms` at the project root lists the personal terms (names, gamertags, Xbox ids) the privacy scan
   must never let through. It is never committed.
4. `python -I tools\build_installer.py` makes the public copy and the map pack (`tools/make_release.py`, stopping on any
   privacy hit), builds the DLL, the injector and the app window, copies the map tools, stages the embeddable Python
   with the packages, compiles `installer\ProjectProvingGrounds.iss`, packs the Linux tar.gz, and zips the map pack. The results are in
   `installer_build` beside the project folder: `ProjectProvingGrounds-Setup-<version>.exe`,
   `ProjectProvingGrounds-Linux-<version>.tar.gz` and `project-proving-grounds-map-pack-<version>.zip`. Use `--skip-native` to package DLLs already built.
5. `python -I tools\make_release.py [folder]` writes the public copy and the map pack on their own, for updating the
   public repository. Its `.gitignore` is the public one. `python -I tools\make_release.py --scan <folder>` rescans any
   folder.
6. Optionally, `python -I tools\human_data.py` builds `human-play-data-<version>.zip` from the recordings on the PC,
   scrubbed and scanned in the same way.
7. Publish a release on GitHub with a version tag (for example `v0.2.0`) and attach the Setup file, the Linux tar.gz (`install.sh --download`
   looks for a `-Linux-` `.tar.gz` on the newest release), the map pack zip and, if built, the human play data zip.

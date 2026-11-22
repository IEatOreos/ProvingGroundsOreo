# Custom release history

## Unreleased

### Reach Forge Printer: Phase 4 milestone 1 passes in the game, 2026-11-21

- The owner edited Guardian in the Blender add-on (a Block 5x5 Flat turned -33 and tilted 27.5 degrees, a Block 3x1 Flat moved 4.47), the export ("FP Guardian test") loaded in Reach Forge and his changes showed as in Blender. An unedited export loaded and played before it. The plan's checklist and its "Phase 4, milestone 1" note mark item 8 done; no code changes. Milestones 2 and 3 wait for the owner.

### Project Noble: the new name, banner and icon, 2026-11-21

The owner sent his new banner, PROJECT NOBLE over Noble Team: "Here is the new Banner for our github banner. And also use the project noble logo as our launchers emblem on the desktop or file". Asked whether the project is now called Project Noble (yesterday it became Project Reach): "Yes, Project Noble".

- **The name:** every visible "Project Reach" now reads "Project Noble" (254 places in 60 files), the same way as yesterday: text only, the same protected credits. Halo: Reach and every other Reach are untouched. The title screen reads PROJECT above NOBLE.
- **Missed yesterday, now right:**
  - The installer's Start-menu and desktop shortcut names and its default folder still said Project Proving Grounds: yesterday's rename took `{autoprograms}\…` for a folder path. They now say Project Noble. An existing install keeps its folder on an update.
  - Five places where the name broke across two lines (README, two comments, a lobby message, the launcher's README) now read Project Noble. The owner's own words from when he named the mode ("We will name the new selection Proving Grounds") stay as said.
- **The banner:** `docs/banner.jpg`, at the top of README on GitHub, is his new 2000 x 500 banner; its alt text is "Project Noble: bots for Halo: The Master Chief Collection".
- **The icon:** his PROJECT NOBLE logo, cut from the banner, on a dark tile with a gold rim, its own sky blurred behind it. It replaces `installer/icon.ico` (the Start-menu and desktop shortcuts, the app windows, the setup program, the uninstall entry; 16 to 256 px) and `installer/linux/icon.png`. The standalone launcher's `ppg_launch.exe` now carries it as its file icon. The wordmark reads at 48 px and up; at 16 px it is only the tile.
- **The standalone launcher** (its own repository): boot screen and splash read PROJECT above NOBLE, and its text says Project Noble.
- **Validation:** the full suite (1237 tests) passes. `tools/test_service_record.py` stops at `test_game_reads_the_sites_challenges`, as yesterday: its one test match makes no progress on today's drawn daily challenges. `build.bat pg38` builds `botcore_pg38.dll`. The title screen and a lobby's message were checked in the preview. The launcher builds, its boot tests pass, and the icon was read back out of the built exe. The site was rebuilt as "Project Noble Service Record". Not pushed: GitHub shows the banner once this is uploaded.

### Reach Forge Printer add-on: floors, slopes, walls and ceilings of the backdrop switch on and off, 2026-11-21

- The owner found Guardian's wire backdrop (its trees, roots and cliffs) covering the pieces. Under Wire / Solid floors / Hidden the Forge panel now has four switches, **Floors / Slopes / Walls / Ceilings**, each showing or hiding that kind of reference surface; ceilings start hidden as before, the rest shown. Only `tools/forge_printer/blender_addon/ui.py` changes what the add-on does; nothing about export.
- **Validation:** `headless_check.py` gained a check (walls hide and come back, floors stay, ceilings start hidden); its full Guardian round trip in Blender 5.1.1 headless: 0 failed, still 292 of 292 equal to `print`. Forge Printer tests 173 OK. Not yet looked at in the owner's Blender window.

### Reach Forge Printer: a Blender add-on that opens, edits, counts and exports (Phase 4, milestone 1), 2026-11-21

Milestone 1 of `docs/REACH_FORGE_PRINTER_PHASE4_BRIEF.md`: edit an auto-built map in Blender and export it as a `.mvar`.

- **`tools/forge_printer/blender_addon/` (new):** installed by one step, `python\python.exe tools\forge_printer\blender_addon\install.py` with Blender closed (a link from Blender's add-ons folder to this folder, enabled and saved in its preferences; `--remove` undoes it). Sidebar (N), tab Forge: **Open fit.json** (one object per placement at Forge's placing point, in a collection per part, the reference's play space behind it as an unclickable backdrop, wire by default), a **palette** of the 99 pieces with known menu names (adds at the 3D cursor), **live counts** (objects of 651, pieces per category of 255, budget with unpriced pieces shown apart), **Export .mvar** (a new file each time, never over one).
- The export goes through the proven code only: `fit.within_limits` chooses, `fit.add_to` writes into a fresh copy of the template, `problems()` must be empty. Pieces that cannot be written (scaled, mirrored, reshaped, leaning past what an up value holds, outside Forge World) and pieces that do not fit are listed in a dialog and selected first; nothing is written unless the owner presses "Export the rest".
- `convert.py` and `export.py` hold everything that does not need Blender; `ui.py` only moves numbers between Blender and them. `mvar.py` and `fit.py` are unchanged.
- **Validation:** `tools/test_forge_printer_addon.py` (22 tests) and `tools/test_forge_printer_addon_blender.py` (runs `headless_check.py` in Blender 5.1.1 headless, about a second; skips without Blender); full suite 1229 OK. Guardian, opened and exported unedited in headless Blender (Bot Testing Grounds, offset -39 -135 8): 336 objects, 292 written, equal to `print`'s 292 (310 of 311 objects identical raw, one position one step off), the same 44 fill blocks left out and named. The eight slope-test orientations export the slope test's raw turn and up exactly. The install step was tried in a throwaway Blender profile (enabled at the next start, removed cleanly). Blender's window was run once by script: the counts react to adding, scaling and moving, the export dialog lists and selects before writing.
- **Untested in game:** no variant exported from the add-on has been loaded yet; the owner's check is an export with pieces moved and turned by hand, compared with Blender.

### Reach Forge Printer: Phase 3 closed, Phase 4 brief written, 2026-11-21

The owner: "can we prep for Phase 3 or do we need to keep going through these steps?" (the next phase, Phase 4 in the plan). The plan's Phase 3 items are met, so the remaining fit work is polish and need not hold the next phase up.

- `docs/REACH_FORGE_PRINTER_PLAN.md`: status and checklist brought up to date (Phase 3 ticked, with what is still polish left unticked); a "Phase 3 → Phase 4" note at the end with what is proven in the game, the limits a writer must keep, what has not been seen yet, what a Guardian first pass still leaves bare, and where everything is. The older "For Phase 4" list in part 7 is marked as replaced: its "only upright up vectors" rule no longer holds.
- `docs/REACH_FORGE_PRINTER_PHASE4_BRIEF.md` (new): the task for the Phase 4 session in three milestones with a stop after each (open, edit, count and export in Blender; gameplay objects; gap, overlap and lip finders), its rules, a checkable "done when" list for milestone 1, and what is carried over.
- The scripts this phase measured with were copied from a temporary folder to `E:\Proving Grounds\re_tools\forge_printer\checks\` (local, not in the repository).
- **Validation:** documents only; no code changed. The brief's facts were checked against the code as it stands (commands, function names, 336 placements, 150 Forge Printer tests of 1206).
- **Not done:** floor from walls laid on their side, which the owner agreed to ("That would be fine"), is listed as carried over, not built. The eighth print is still not loaded in the game.

## 0.2.2-custom.13 — Bots that hit what they aim at, matches that start at once, and the Reach Forge Printer, 2026-11-21

### Reach Forge Printer: fuller floors, curved ramps joined, and a 255-piece limit per category, 2026-11-21

The owner, on the seventh Guardian print (HUD $27,170, as predicted): "The Ramps were all good. Some of the floor just seems like its not all there yet. Maybe just because were going in steps but Im assuming its spots that have very small inclines like from the original guardian".

- **Measured:** of 693 u2 of walked ground 284 was bare. 150 of it is level floor, 9 leans 1 to 10 degrees, 42 is gentle slope in small facets (curved ramps), 82 is steep rims and braces that are not floor. About 74 u2 of the bare level floor is strips under half a block wide.
- **`tools/forge_printer/fit.py`:**
  - a fourth floor pass: 1x1 and 2x1 blocks put where each covers the most bare floor, a quarter of the block allowed past the edge, kept off the heads of ramps (`FILL_*`); such placements carry `fill`;
  - `_joined_slopes`: small sloping patches that touch and lean nearly alike are fitted as one tilted slope (8 on Guardian);
  - `fit_slopes` reports why each unfitted slope was left; `_onto_slope` counts tucked blocks too.
- **A limit found:** a variant counts a palette row's pieces in 8 bits, and every Forge World flat block is in one row, so 255 Building Blocks is the most a file can hold. The fit asked for 299 and the writer failed. `within_limits` now takes the room left in each row and drops fill blocks first; `mvar.problems()` names a row over `ROW_MAX`. Noted in `docs/reach_mvar_format.md` 3.5.
- **Guardian:** fit 336 pieces, floor coverage 75% (68% before), covered ground 448 of 693 u2. Printed 292: 44 fill blocks left out for the row limit.
- **Made for the owner:** `FP_Guardian_8.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 311 objects; `check` reads it back with no problems. Expected HUD $26,950.
- **Validation:** new tests for the fill pass, joined facets, and the row limit in both places; full suite 1206 OK.
- **Untested in game:** the eighth print, and 255 pieces in one row (233 is the most seen loading).

### Noble: the game-time speed checked in a 1v1; the sprint tap after its own held sprint, 2026-11-21
- The owner's 1v1 against Cedercare (Noble) on Asylum, him using a jetpack too (logs/trace_reach_forge_halo_20261121-165238): Noble DMR rounds at him landed 33 of 38 within 15 u (87%); with him moving sideways over 1.5 u/s 11 of 14 (79%; the match before 7 of 21, 33%); rising or falling 5 of 6, 1 u or more over it 9 of 10; his reticle on it 16 of 19. One short match: a small sample.
- The sprint tap (`Bot.noble_sprint_off`) fired 3 times; twice the run away's own sprint button was still down, so the tap was no new press and the sprint stayed on 0.4 s to the retap (a trigger press lost at 108.04 s). Now with the button down the tick before it lets go first and taps the next tick.
- Validation: `SprintOffTests.test_button_still_held_lets_go_first` (new); full suite 1204 OK. **Untested in game.**

### Noble: a man's speed over the game's own time between reads, 2026-11-21
- The read-age lead (above) in the owner's next Asylum match (logs/trace_reach_forge_halo_20261121-163837; won 50-45, "felt better"): Noble's `lead` ran 0.029 s median, 0.019 p10, 0.073 p90. Its rounds at him with him moving sideways over 1.5 u/s landed 7 of 21 (33%; before 3 of 19), slower 20 of 37 (54%). His reticle on the shooter no longer mattered (30 of 51 vs 36 of 64).
- His report "Queen of darkness missed two while hard strafing left": at 146.7 and 147.1 s Queen of Dark's two head shots for the kill, 10 u off, his shield already down and him strafing left at 2.0 u/s, both missed (its body shots in that fight landed 4 of 5).
- Cause found reading the lead's other half: `tools/live_bots.py` `snapshot` made every player's velocity his move since the last read x HZ (30), every read gap taken for 1/30 s; the loop runs 34 ms median, 77 ms p90 (2.3x his speed), and two reads of the same game tick gave 0. Now each read also gets `vel_t`, his move over the game time between the reads (botcore's tick count, GAME_HZ 60; a re-read of one tick keeps the last), and Noble's `lead_ray` leads with it. Demon and everything else keep `vel` as it was.
- Validation: `test_noble_difficulty.py` `GameTimeVelocityTests` (2 new: a 5-tick gap read right where x HZ read 2.5x, a re-read kept; Noble led by it, Demon not); full suite 1202 OK; `live_bots` imports. **Untested in game.**

### Reach Forge Printer: the slope test passed in game; Guardian's ramps are tilted faces, 2026-11-21

The owner, on the slope test: "It loaded and here is one side, and one from the top. Each was all flush so I dont think I needed to capture them all. What is our next step?" HUD $29,630 as predicted.

- **Seen:** in his top-down picture all eight tilted ramps lie straight between their platforms, the four leaning in x and y at once included; his side-on picture, enlarged, shows one ramp meeting both platforms with a clean crease. The other joins rest on his word. `docs/reach_mvar_format.md` 4.2 and 4.3 now say the step law and the turn rule are seen working.
- **`tools/forge_printer/fit.py`:** `fit_slopes(..., tilted=True)`, which `build` now uses. A slope up to 44 degrees is one flat face from the upper floor's edge to the lower floor's, at the slope's own angle: 1-wide flat blocks (5x1, 3x1, 2x1, or a 2x2 across two lanes) tilted to it, laid from the top edge down, the last running on under the lower floor (`_tilted_lengths`). Steeper slopes keep the ramp pieces. A placement carries `up`; `add_to` writes it and the boxes OBJ draws it.
- **Guardian:** 21 tilted blocks in 13 runs (10 to 29 degrees) replace 48 ramp pieces; 270 pieces in all, budget 2,700. A check that reads `fit.json` alone: every run's top edge within 0.006 of the floor or landing past it, no upper floor block on a ramp's face, every foot under its floor. Two ramp tops still have no floor past them.
- **Made for the owner:** `FP_Guardian_7.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 289 objects; `check` reads it back with no problems. Expected HUD $27,170.
- **Validation:** `TiltedRamps` (4 tests) and two command tests updated in `tools/test_forge_printer_fit.py`; full suite 1200 OK.
- **Untested in game:** the seventh print. Guardian in the sixth print was never pictured, so the floor heights changed then are first seen here too.

### Reach Forge Printer: a slope test print for tilted ramps, 2026-11-21

The owner, after the tilt test was read: "What do you need me to do". A small print to load, before Guardian's ramps are changed.

- `tools/forge_printer/turn_test.py`: a third test, `turntest --test slope`. Eight tilted ramps (`SLOPE_CHECKS`), each a Block 5x1 Flat written to lie from the top edge of a lower Block 2x2 Flat platform to the top edge of an upper one: three climbing +x at 10, 20 and 35 degrees, one climbing +y, four climbing at 30, 60, 150 and 240 degrees round. `add_to` now takes raw turns and up vectors, so the first two tests write what they wrote before.
- **What it settles:** the tilt test's reading is good to about 2 degrees and has not been seen for an up vector leaning in x and y at once. If it is right, every ramp meets both platforms flush with its sides in line; one degree out is 0.04 of lip at each end, a wrong turn a ramp lying askew.
- **Made for the owner:** `FP_Slope_Test.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 43 objects; `check` reads it back with no problems. Expected HUD $29,630.
- **Validation:** one new test in `tools/test_forge_printer_turn_test.py` (10 in all): from what the variant holds, each ramp climbs the way and at the angle asked, its sides are level, and each end of its top lies on its platform's edge to 0.01. Full suite 1196 OK.
- **Untested in game:** all of it. The test checks the code against itself; only the game can say the reading is right.

### Noble: leads a strafing man by the read's real age; the reticle fix seen live, 2026-11-21
- The reticle-target fix (botcore_pg41) in the owner's next Asylum match (logs/trace_reach_forge_halo_20261121-153537; "it was the better match"): Noble rounds at him landed 55% (32 of 58; before 45% in both matches), 50% with his reticle on the shooter and 62% without (before 27-36% vs 47-55%).
- The owner: "It seems like noble only misses when Im strafing at full speed, doesnt have to be back and fourth just max speed to one side". With him moving sideways over 1.5 u/s Noble hit 0 of 3 that match and 3 of 16 the one before (about 35-40% slower). Noble's precision shot (the final snap and the fight aim, `lead_ray`) led him by the fixed DEMON_LEAD_S, 0.034 s; the snapshot is older than that by the time a bot's action goes out (`tools/live_bots.py` reads the game, does the tick's other work, then thinks and sends bot by bot; the loop 34 ms median, 77 ms p90), and a full strafe moves about 0.1 u, a head's half-width, in 0.04 s. Its own view follows a sent aim within one row (measured: median error 0 at 0.01-0.03 s), so the gap is the read's age, not the turn.
- Now `live_bots` stamps each snapshot with when it was read (`snap.read_wall`), and Noble leads by that age when it thinks plus NOBLE_APPLY_S (one 60 Hz game tick, botcore's write), capped at NOBLE_LEAD_MAX 0.15 s (`Bot.noble_lead_s`, `lead_ray(..., lead_s)`). Noble only; Demon keeps DEMON_LEAD_S; without a read time (simulator, tests) as before. The trace's bot rows carry `lead` (s) for Noble to check it.
- Validation: `test_noble_difficulty.py` `LeadTests` (2 new); full suite 1195 OK; `live_bots` imports. **Untested in game.** The check: Noble's hit rate on the owner while he strafes over 1.5 u/s, up toward the slow rate.

### Reach Forge Printer: the tilt test read; up vectors and turns for tilted pieces, 2026-11-21

The owner loaded the sixth Guardian print (HUD $26,650, as predicted) and sent the tilt test from straight above.

- **Read with a fitted camera, not by eye:** the three upright pillars give 17 known points; a pinhole camera fits them to 1 pixel rms. Each antenna's direction was solved from where its tip is seen, and each ramp's corners were projected for every way it could lie and compared with the picture.
- **Settled:**
  - a point on a cube face is the direction (1, u, v), so a step leans the up vector by atan(steps / 208): half way across a face measured 25, 29 and 28 degrees (26.6 expected), the edge 47 (45 expected). The earlier "9 and 14 degrees for 90 steps", read by eye, is withdrawn;
  - on face +X, u runs along +y and v along +z;
  - a turn with a tilted up is counter-clockwise about up from `Y x up` (when up leans no more along y than x) or `up x X`. Three ramps and two leaning antennas fit.
- `tools/forge_printer/mvar.py`: `up_vector`, `up_raw`, `reference_axes`, `axes`, `turn_for`. `docs/reach_mvar_format.md` 4.2 and 4.3 rewritten with the measurements; the plan has phase 3 part 11.
- **Not settled:** the step size to better than about 2 degrees; u and v on faces +Y, -X, -Y, -Z; the turn's reference for an up vector leaning in x and y at once. Nothing is printed with a tilted piece yet.
- **Validation:** four new tests in `tools/test_forge_printer.py` (32 in all) hold each thing seen in the game; full suite 1193 OK.
- **Not seen:** Guardian itself in the sixth print (no picture yet), and the tilt test from the side.

### Reach Forge Printer: ramp tops clear of overhanging floor blocks; floor levels by real height, 2026-11-21

The owner, asked whether to read the tilt test or fix the angled ramp tops next: "You pick". The tilt test needs two screenshots from him, so the ramp tops were done meanwhile.

- **Measured first:** Guardian's floor is not at an angle. 44% of the walked floor's outer edges run square to the map, 11% at 45 degrees, the rest every way (round platforms). So no turned floor grid; the fault is where a ramp meets blocks that hang past the floor's edge.
- **`tools/forge_printer/fit.py`:**
  - `_onto_slope`: a run's top edge is now the furthest corner of the upper floor's blocks hanging out over the slope within its lanes (up to 0.6), not the reference's edge. Block corners stood 0.05 to 0.12 proud of two ramps that meet their floor at an angle, and of one square-on Ramp 2x2. The turned landing fills the notches between corners.
  - `LEVEL_NEAR`: a level takes only floor within 0.105 of its height by real distance. Levels were grouped by rounded height steps, and two neighbouring steps can be 0.2 apart. The lower floor of the ramp in the fourth print's screenshot is at 16.13 in the reference and had been laid at 16.24: most of that picture's 0.15 lip. A floor at 17.84 had been laid at 17.65, which gave its ramp the wrong piece and a 0.22 lip.
- **Guardian:** 192 floor blocks at 23 heights (18 before), 68% of the walked floor (70% before: small floors once swept into a neighbour's level are now too small for a block); 48 ramp pieces, 19 landings, 37 walls; 296 pieces, budget 2,960. The check that reads `fit.json` alone finds no floor block edge across a ramp's upper face.
- **Still flagged by that check, not fixed** (plan, phase 3 part 10): one ramp's sunk foot coming out 0.26 under a one-unit-deep floor block's far edge; floors at another height overlapping five ramps' sides; three ramp tops with no floor block past them.
- **Made for the owner:** `FP_Guardian_6.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 325 objects; `check` reads it back with no problems. Expected HUD $26,650.
- **Validation:** three new tests in `tools/test_forge_printer_fit.py` (44 in all); full suite 1189 OK.
- **Untested in game:** the sixth print. Floors the owner saw as good in the fifth print have moved where they had been levelled with a neighbour more than 0.1 away.

### Reach Forge Printer: no floor standing proud of a ramp; landings where the floor blocks stop short, 2026-11-21

The owner loaded the fourth Guardian print (HUD $26,980, as predicted) and sent two screenshots. Enlarged, the ramps reach their floors, but on the 4.15-long ramp the lower floor block still stands about 0.15 proud of the ramp where they meet; the fitter's own numbers say the same (run at 16.09 at the floor's edge, floor at 16.24).

- **Found:**
  - The mix of ramp pieces was chosen for the run's whole length, but a run is longer than its slope (the last piece goes on under the lower floor), so the drop it was matched to is reached under the floor, not at the floor's edge where the two meet.
  - A second check that reads `fit.json` alone, every floor block edge against every ramp face, found what the fitter's arithmetic cannot: floor blocks sit on a quarter-unit grid and cover 70% of the floor, so they can stop short of a ramp. The ramp's sunk foot then shows in a gap in front of the block, or a ramp top has no block past it.
- **Fixed in `tools/forge_printer/fit.py`:**
  - `_best_run(rises, length, rise)` now returns (run, lift) and judges a run where it stands at the lower floor's edge. Above the floor there is fine: the ramp comes up out of the floor a little further on. Under it, up to 0.06 in all is let pass (half moved to the top by lifting the run), more is all but ruled out. So a slope the pieces do not fit becomes a slightly longer, shallower ramp instead of one with a lip.
  - Landings: with fitted floors, `fit_slopes` adds a flat block (part `landing`) at a run's foot and top, turned with the ramp, 1 long and 0.005 under the floor's height, where the reference has walked floor at that height and no fitted block already covers the spot. `within_limits` ranks them with the ramps.
- **Guardian:** 190 floor blocks, 45 ramp pieces, 19 landings, 37 walls: 291 pieces, budget 2,910. By the fitter's arithmetic no run is more than 0.02 under its lower floor at the edge. The 4.15-long ramp is now three shallow rows that reach the floor 1.5 past the reference's foot: a deliberate change of shape.
- **Still wrong, measured, not fixed** (listed in the plan, phase 3 part 9): floor block corners 0.05 to 0.12 proud of two ramps that meet their floor at an angle (needs turned floor blocks); floor blocks hanging 0.1 over one ramp top (0.05 proud); one ramp foot in a tangle of small floors with the floor 0.22 proud over half its width; three ramp tops with no floor past them; floors at another height overlapping four ramps' sides.
- **Made for the owner:** `FP_Guardian_5.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 320 objects; `check` reads it back with no problems. Expected HUD $26,700.
- **Validation:** `tools/test_forge_printer_fit.py`: the best run judged at the floor's edge over a sweep of lengths and rises, the gentle, steep and odd-length slope tests updated for the new rule, four landing cases; 43 tests. Full suite 1186 OK.
- **Seen in game (owner, three screenshots, "All seem pretty good"):** HUD $26,700 as predicted. Enlarged, three ramp feet come up out of their floor blocks with no step, two ramp tops are level with their floors as far as the pictures can show, and a far run of three pieces joins end to end.
- **Not seen in game:** the faults listed above are not identifiable in those pictures. Whether a landing flickers cannot be judged from a still; none in view shows a torn surface.

### The bots' terrain from a cache at match start; start-up times in the brain's log, 2026-11-21

The owner: "We have to figure out why the bots dont play the game right from the start. It happened on my last asylum game. It happens quite a bit still", then "They stand still"; then "Yes, add both".

- **Found:**
  - The brain gave its first command 10-17 s into every match: the first recorded row showed 703-710 s of a 720 s match left in all nine recent recordings. Today's Asylum match (`reach_forge_halo/variants/v8e4a8930`, 13:55) lost 14.6 s; until then the bots stood at their spawns.
  - `botcore` starts `tools/play.py` once the match ticks. It polls for the game, map and variant, adds the bots one by one, then starts `tools/live_bots.py`. That process identifies the layout and builds its terrain, **7.3 s on Asylum, every match**, before its first tick. The rest of the time is not measured yet.
  - The build is `Terrain.__init__` (nav graph 4.9 s, the layout's 223 pieces 3.1 s).
- `brain/maps.py`: the terrain cache (`CACHE_DIR` logs/terrain_cache, `cache_key`, `_cache_load`, `_cache_save`, `prebuild_after_match`).
  - **Key:** a hash of the map code (`CACHE_CODE`), every file in the map's data folders except those the build never reads that change each match (`CACHE_SKIP`), the piece shapes, and the loaded map, with its variant's first and last seen left out.
  - **Hit:** loads the terrain and what `_build` sets on the map (blocks, shields, snapped points, lanes, holds, zone centres, items' reachability). On Asylum that is 0.77 s instead of 7.5 s, with the same nav answers.
  - **Building it:** a match changes its own data (the people's LiDAR walk, what bots learned), so after a match, its data saved, `live_bots` starts `tools/terrain_prebuild.py`. It builds the next match's terrain from this match's starting inputs and current window, in the background (about 9 s, during the post-game).
  - The next match on the same layout and game type starts from it; anything else changed builds as before. `CACHE_KEEP` 6 files are kept (about 72 MB each on Asylum), newest first. Nothing is filed at a match's start: that pickled 640 MB mid-match for a key the next match never asks for.
- Start-up times:
  - `tools/play.py` stamps its lines (game, map, variant, each bot added, "starting the brain") with the clock and seconds since it began.
  - `tools/live_bots.py` adds `startup` marks: brain started, game attached, variant identified, terrain ready (with "from the cache" or "building"), first tick.
  - The next match's `logs/brain.txt` shows where the rest of the start goes.
- Validation:
  - `tools/test_terrain_cache.py` (new, 4): the key follows the build's inputs, not each match's other files; the round trip puts the map settings back, and another key or a map that does not fit loads nothing; one file per map and the newest kept; after a match, the next build gets this match's inputs with the grown window.
  - Live data: the key is the same in two processes (0.05 s); the match-start copy keys the same; the background build found it cached.
  - `live_bots`, `play` and `terrain_prebuild` import. The full suite runs 1184 tests: 1183 pass, and `test_forge_printer_fit` fails on another session's uncommitted Forge Printer work.
  - **Untested in a match.** The first Asylum match after this still builds (this change is in the key); the one after should start from the cache.

### Reach Forge Printer: ramps tied to the floors they join, floor blocks flush, 2026-11-21

The owner, on the third Guardian print's screenshots: "Two of those screenshots showed the floor not sitting flush on another object? and one of the ra[m]ps didnt connect to the the other floor?" He was right; the entry below, which reads those pictures as fine apart from the fixed step, was wrong about that.

- **Found, by comparing every fitted slope's ends with the floor blocks beside them:** the reference mesh has each slope's ends at its floors' heights to within 0.01, so the fault was the fitter's.
  - A ramp piece is 2 long and Guardian's ramps are 1.3 to 5.5 long. The run was centred on its slope, so it stopped short or overshot: on a 2.9-long ramp one piece sat with its foot 0.24 above the lower floor and 0.45 away from it, its top 0.32 under the upper floor.
  - A run's rise was whatever its pieces added up to, not what the two floors differ by.
  - Each floor block took the middle height of the cells under it, so neighbours on one floor could differ by a tenth or two.
- **Fixed in `tools/forge_printer/fit.py`:**
  - every floor block of a level sits at the height most of that level's floor is at, and a level now takes floor within 0.1 of its busiest height (was 0.2), so a kerb is levelled and a ledge of a quarter unit stays a ledge;
  - `fit_slopes` takes the fitted floors: a run's ends take the height of the floor block just past each end; it starts at the slope's top edge and is laid downhill over the whole length, the last piece running on under the lower floor; the mix of pieces is the one whose total rise is nearest the slope's (every mix tried for runs of up to six pieces), and what it is still out by, a quarter unit at most, is shared between its ends;
  - a slope whose foot is a unit or more under the floor over it is not given ramps (two were roots or braces).
- **Guardian:** every ramp top within 0.11 of the floor block it meets, most within 0.05, feet at or under the lower floor; floor blocks at 18 heights instead of one per block; 190 floor blocks (70%), 36 ramps, 37 walls, 263 pieces, budget 2,630.
- **Made for the owner:** `FP_Guardian_4.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 292 objects; `check` reads it back with no problems.
- **Validation:** six new tests and five updated in `tools/test_forge_printer_fit.py`; full suite 1179 OK.
- **Untested in game:** the fourth print.

### Reach Forge Printer: slot and budget limits when printing; the third print seen in game, 2026-11-21

- **In game, the owner's four screenshots of `FP Guardian 3`:** the two ramps that stepped now join (a Ramp 1x2 Shallow running into a Ramp 2x2), a ramp's low tip meets the floor block below it, the long walkway ramp runs unbroken, and the HUD reads $27,020 as predicted.
- **New `fit.within_limits`:** keeps the pieces a variant has free slots and budget for, floors before ramps before walls and larger floor blocks first; a piece with no known price counts as free and is named. `forge_printer print` uses it, raises the variant's stored budget by the cost of what it placed, prints the budget, and says in capitals what it left out and whether slots or budget ran out. Guardian needs 259 of 632 free slots and 2,590 of the budget, so nothing is left out.
- **`docs/REACH_FORGE_PRINTER_PLAN.md`:** where phase 3 stands against the plan, what a first pass still leaves for hand work, and what phase 4 needs from this code.
- **Validation:** seven new tests in `tools/test_forge_printer_fit.py` (limits by slots and by budget, the order pieces are dropped in, an unpriced piece named, print's stored budget and its left-out line); full suite 1174 OK.
- **Not applied:** per-piece or per-category limits, because none has been seen (185 Building Blocks loaded). **Still unread:** the tilt test.

### Reach: a bot no longer takes the player's reticle target as its own (missed rounds), 2026-11-21
The owner's reports "Sword shoots the ground twice" (with theater screenshots: Sword117's view on him, its rounds into the grass at its feet), "Sword missed 2 shots on me" and the 1v4 he could not be killed in.
- Cause: `native/reach.cpp` builds each bot's action from the player's own action of the tick and overwrites it field by field; of the aim-assist block it zeroed only the weights (+0x8C / +0x90) and left his +0x78 (target set), +0x80 (the unit under his red reticle) and +0x88 (weight 1.0). A bot he aimed at had itself as its target.
- Evidence (logs/trace_reach_forge_halo_20261121-135535 and -150927; the owner's own trace row carries the player under his reticle): Noble DMR rounds at him within 15 u, counted a hit when his shield or health fell within 0.25 s: with his reticle on the shooter 11 of 41 and 24 of 66 (27%, 36%), with it elsewhere or on nobody 36 of 66 and 28 of 59 (55%, 47%). Every difficulty used the same action path: not Noble's alone.
- Fix: every bot's action gets the block as the player's carries it with nobody under the reticle (5659 of 5659 ticks of logs/reload_capture_20261120-234526): +0x78 0, +0x7C / +0x80 / +0x84 0xFFFFFFFF, +0x88..+0x9F 0. A bot's own red-reticle target (hb_target: sword, hammer and melee lunges) is still written after it, unchanged.
- Validation: `build.bat pg41` builds `botcore_pg41.dll` (the native files also hold the collaborator's uncommitted lobby edits, the same ones already in pg40). Full Python suite unchanged. **Untested in game:** from MCC's next start; the check is Noble's hit rate on the owner with his reticle on the shooter, up to the rate without.

### Noble: taps a running sprint off to shoot; the close lock checked live, 2026-11-21
From the owner's next Asylum match (logs/bug_reports/reach_forge_halo_20261121-150927, owner + 3 Demon vs 4 Noble):
- The close-range lock above, live: ticks of a DMR fight with a clear line where Noble's trigger was free, under 3 u 30% -> 91%, 3-6 u 70% -> 90% (Demon 100%). Reloads again 68 of 75 Noble, 61 of 65 Demon, median 1.2 s.
- "queen just refuses to shoot me": Queen of Dark pressed sprint for 0.6 s at 33.6 s while running from a fight; the game's sprint came on at 34.7 s and stayed on to 38.3 s with the button let go, through a fight with the owner 2.5 u off: 7 trigger presses, the magazine never left 15, dead at 38.6 s. In that match 0 of 45 DMR presses made with sprint on fired (40 Noble, 5 Demon). A second press ended a running sprint within 0.2 s in 77 of 79 cases (the last six Reach traces). New `Bot.noble_sprint_off`: Noble in a fight with a man in view taps the button once while the game reads its sprint on, again after NOBLE_SPRINT_RETAP (0.4 s); not while its own sprint is held to close a gap. Noble only; Demon unchanged.
- "Sword missed 2 shots on me" and "The entire blue team couldnt kill me in a 1v4": both are Noble rounds that do not land although the trace has the view on the owner's head. Counting each Noble DMR round at the owner within 15 u as a hit when his shield or health fell within 0.25 s: 45% hit in both matches, 31-33% when the shooter looked up more than 8 degrees (the owner on higher ground; in the 1v4 his shield recharged to full twice), about 50% level. With the owner's theater screenshots of Sword's two ground hits at 71.6 / 72.1 s (its view on his head in its own theater view), the game sends some rounds away from where the view points. The trace does not record where a round goes: not fixed, open. Next: capture the shot's own path (or a still owner on a ledge vs on the level).
- Validation: `test_noble_difficulty.py` `SprintOffTests` (2 new); full suite 1188 OK. The sprint tap is not checked live yet.

### Noble: locks on up close, and joins a teammate's fight instead of waiting, 2026-11-21
From the owner's bug reports on Asylum (logs/bug_reports/reach_forge_halo_20261121-135535, owner + 3 Demon vs 4 Noble, 50-25):
- "Cedercare doesnt shoot while jetpacking": at 225.5-226.6 s Cedercare's view sat within a few degrees of the owner 2-3 u off for over a second and it never fired. Noble presses a precision gun only on its exact lock (Aim.noble_lock); up close the man's move each tick was bigger than NOBLE_LOCK_R (1.5 deg) and the view read back is a tick behind, so the swing never got inside it. Across the match, ticks of a DMR fight with a clear line where the trigger was free: Noble 30% under 3 u, 70% at 3-6 u, 86% at 6-12 u; Demon 100% at every range. Now the lock takes him once the gap left is no more than his own move over two ticks (NOBLE_LOCK_TICKS) plus his part's half-width at his range (NOBLE_PART_HALF 0.1 u). Noble only.
- "Cedercare and Morshix didnt shoot at me": Morbix took a third party on the owner (fighting Cedercare 3 u off), and peek_timing cancelled it because his face was turned its way, so it waited out of sight. Noble now does not wait for a man a teammate fights right now (TEAM_TARGETS, TEAM_FRESH). Demon unchanged. Cedercare's own 1 s without a round there was the gun coming back up after its pre-nade, not a bug.
- "Sword shoots the ground twice" (the owner's theater shots, 71.6 s and 72.1 s): the trace has Sword's view on the owner's head both times (within 1 deg, steady 0.5 s), matching its theater view; the owner's shield was untouched by those two, hit by the next two. Where the game sent those rounds is not in the trace: not fixed, open.
- Validation: `test_noble_difficulty.py` `test_locks_on_a_man_circling_it_up_close` (failed before the change at 1/30 s and 0.1 s ticks), `test_reach_team_demon.py` `test_noble_does_not_wait_for_a_man_a_teammate_fights`; full suite 1169 OK. Not checked in a live match yet.

### Reach Forge Printer: ramps that join end to end, 2026-11-21

The owner sent three screenshots of the second Guardian print's ramps. They climb the right way and reach the floors, but in one, two Ramp 2x2 on the same slope did not join: the second started about half a unit below where the first ended.

- **Found:** `fit.fit_slopes` set each ramp in its slope's plane on its own. That slope is about 20°, between the Shallow ramp's 13.9° and the Ramp 2x2's 26.6°, so a 26.6° ramp overshot at its top and undershot at its foot, and the next one did the same from lower down. (It had also taken the larger ramp rather than the nearer angle.)
- **Fixed:** a slope is climbed in steps of one ramp's run, each starting where the last stopped and taking whichever piece of its family brings the run of ramps nearest the slope's height at the step's end: for gentle slopes a flat block, Ramp 1x2 Shallow or Ramp 1x2 (two lanes of Ramp 1x2 side by side become one Ramp 2x2), for steeper ones Ramp 2x2 or Ramp 2x2 Steep. Ramps now join whatever the slope's angle, and slopes between the ramps' own angles (the 33° to 38° ones included) are followed by a mix.
- **Guardian:** 37 ramps again, now 26 Ramp 1x2 Shallow, 5 Ramp 2x2, 6 Ramp 2x2 Steep; 259 pieces, budget 2,590.
- **Made for the owner:** `FP_Guardian_3.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 288 objects; `check` reads it back with no problems.
- **Validation:** five new tests in `tools/test_forge_printer_fit.py` (a 20° slope takes a Shallow then a Ramp 1x2 and their ends meet; a 36° one a Ramp 2x2 then a Steep; a very gentle one a level step now and then; two lanes of Shallow stay two wide; a 49° slope is left); full suite 1167 OK.
- **Untested in game:** the third print.

### Reach Forge Printer, phase 3 part 6: ramps and walls fitted, 2026-11-21

The owner, asked whether to fit Guardian's ramps and walls next: "Yes, ramps and walls".

- **`tools/forge_printer/pieces.py`:** `--measure` now also measures each incline's sloping face (its lean, the way it climbs, its run and width, its low and high edge) into the table as `slope`. Ramp 1x2 and Ramp 2x2 climb at 26.6°, Ramp 1x2 Shallow at 13.9°, Ramp 2x2 Steep at 45°.
- **`tools/forge_printer/fit.py`:**
  - `fit_slopes`: each walked sloping patch of 1.5 u² or more takes the ramp whose lean is within 7° of its tilt, turned to climb the same way (any turn, not only quarter turns) and repeated along and across it, the ramp's sloping face set in the patch's plane.
  - `fit_walls`: an upright, roughly rectangular wall at least 1.5 long and high with walked ground at its foot takes Wall Double and Wall pieces along it, up to two rows high; the two faces of a thin wall make one wall.
  - `fit.json` placements carry `part` and `origin`; the report is split into floors, slopes and walls.
- **Guardian:** 37 ramps on 60 of its 224 u² of walked slope (27%: the straight walkway ramps; curved ramps and in-between leans are left) and 37 wall pieces along 64 units of wall, on top of the 185 floor blocks: 259 pieces.
- **Made for the owner:** `FP_Guardian_2.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository), 288 objects; `check` reads it back with no problems.
- **Validation:** 9 new tests in `tools/test_forge_printer_fit.py` (ramps chosen by lean and width and turned to the slope, walls by length and height, walls nobody walks beside left alone); full suite 1162 OK. `pieces --measure` re-ran: 109 of 109.
- **In game, the owner, 2026-11-21:** the print loads and the HUD shows $27,020 left, exactly what 259 pieces at 10 each give, so every piece was counted. `pieces.PRICES` now holds the sixteen prices four such HUD totals agree on (fifteen pieces at 10, the small antenna at 50), with `pieces.cost()`; `fit` reports the budget of what it placed. Whether the ramps meet the floors has not been reported. **Known limits:** a ramp piece is a solid wedge, so it fills the space under a thin sloping bridge; some ramps land on tree roots; railings, kerbs and ceilings get nothing.

### Reach Forge Printer, phase 3 part 5: Guardian's floors fitted with Forge blocks and printed, 2026-11-21

The owner, asked whether to start fitting pieces to Guardian's floors: "Yes, start fitting"; and of which test to run, "you pick".

- **New `tools/forge_printer/fit.py`:**
  - `python\python.exe tools\forge_printer fit <reference folder>` covers a reference's walked floors with flat Forge blocks, largest first, and writes `fit.json` and `<map>_fit.obj` (the pieces as boxes) beside the reference; both are made from the game and stay local.
  - `python\python.exe tools\forge_printer print <folder> <template> <out> --offset DX DY DZ [--title TEXT]` writes the pieces into a copy of a Forge World variant (the template is never changed, the output never overwritten).
  - The floor is sampled on a quarter-unit grid with every floor height kept; floor within 0.2 of a height is one level; each block goes to the first place wholly on uncovered floor, then a pass lets a tenth of a block hang past an edge, then strips between blocks are filled by a block tucked 0.01 under its neighbours.
- **`surfaces.analyse()`** is the surface work without writing files (the fitter uses it; `surfaces` writes the same bytes as before). **`blender_import_reference.py`** also loads the fitted boxes. **`turntest --test tilt`** is a second rotation test: antennas at a face's edge and half way, and ramps turned under a tilted up.
- **Guardian:** 71% of its 484 u² of walked floor covered by 185 flat blocks (a 1x1 lying wholly on floor can reach 76%); a second run writes the same bytes; a top-down render shows the blocks on the platforms.
- **Made for the owner:** `FP_Guardian_Floors.mvar` in `E:\Proving Grounds\re_tools\forge_printer` (not in the repository): his own variant with Guardian's floor blocks hanging about 18 units above its floor, and the tilt test below. `check` reads it back (214 objects, no problems).
- **Validation:** `tools/test_forge_printer_fit.py` (new, 17 tests on hand-built floors) and one more turn-test test; full suite 1153 OK.
- **In game, the owner, 2026-11-21:** the print loads and "the floor is somewhat printed". His screenshot from above matches a render of the file from the same viewpoint, and the HUD's budget (2,240 spent) is exactly the thirteen walls, all 185 floor blocks at 10 each and the tilt test, so the game counted every block and more Building Blocks than any variant on this PC holds (92) do load. Each block cannot be checked by eye from that height. **Known limits:** blocks square to the map's axes only, flat blocks only, no slopes, walls or ceilings, and no piece limits (185 Building Blocks where no variant on this PC holds more than 92).

### Reach Forge Printer, phase 3 part 4: a test map for turns and tilts, 2026-11-21

MCC would not save the owner's calibration map, so the rotation test runs the other way round: the tool writes the pieces and the owner looks. Asked whether to, the owner: "Write it."

- **New `tools/forge_printer/turn_test.py`, run as `python\python.exe tools\forge_printer turntest FILE OUT --origin X Y Z [--title TEXT]`:** adds eleven pieces to a copy of a Forge World variant (FILE is never changed, OUT never overwritten): three Ramp 1x2 turned 0, +90 and +45 degrees; five small antennas whose "up" is set to cube faces 0, 1 and 5 and to face 2 pushed along u and along v; three tall pillars as a marker for +y. Quotas are recounted and the budget raised by a guessed 10 a piece.
- **`tools/forge_printer/mvar.py`:** `MapVariant.add_object` (first free slot) and `join_up` (a raw up vector from face, u, v).
- **Made for the owner:** `FP_Turn_Test.mvar` from his own variant, on its floor in front of its spawn points; kept in `E:\Proving Grounds\re_tools\forge_printer`, not in the repository. `check` reads it back (30 objects, no problems).
- **Validation:** `tools/test_forge_printer_turn_test.py` (new, 8 tests on a hand-built Forge World variant); full suite 1135 OK.
- **Tested in game by the owner, 2026-11-21:** "It loaded fine": a file with eleven objects added (three palette rows, quotas recounted, a guessed budget) loads in Reach Forge. His screenshot (Forge monitor view from the south) then showed the guesses held: a turn is counter-clockwise from world +x seen from above (the three ramps), and the up vector's faces are +X, +Y, +Z, -X, -Y, -Z (antennas on faces 0, 1, 2 and 5; 3 and 4 by the pattern). `docs/reach_mvar_format.md` 4.2 and 4.3 now say so. **Also seen:** the game shows its own budget (440 spent where the file said 240), so the stored figure is not what counts and prices can be read off the HUD. A second screenshot from above confirmed those and showed that on face 2, u leans the up vector towards +x and v towards +y. **Still open:** how far a step leans it (measured at about 9° and 14° for 90 steps, where 23° was expected), and what a turn means once up is tilted; until a second test, only upright, on-its-side and upside-down up vectors are safe to write.

### Reach Forge Printer, phase 3 part 3: which palette row and item each piece is, 2026-11-21

The owner on his calibration map, which MCC refused to save ("private storage is full"): "It probably wont let me save it." So what the map was for was looked for in files already on the PC.

- **Found:** ten Forge World variants on today's palette (MCC's five built-in Forge World maps as its session copies under `LocalLow\MCC\Temporary`, and five in the private folder) keep every building piece in quota rows 70 to 76, and the highest item each row uses is exactly one less than the number of models the map file has for the matching category (26, 21, 11, 16, 12, 15, 8). With Wall Coliseum = row 74 item 8 in the owner's own variant, a piece is (its category's row, its place in the category).
- **`tools/forge_printer/pieces.py`:** the rows (`ROWS`); every piece in the table now has `row` and `item`; `pieces.at(row, item)` finds a piece; the sixteenth decorative model (`ff_dish_antenna`) is added, so the table has 109 pieces. `forge_printer info --objects` names each building piece of a Forge World variant (the owner's own lists thirteen "Wall Coliseum").
- **Validation:** three new tests in `tools/test_forge_printer_pieces.py` (18 in all); full suite 1127 OK. `pieces --measure` re-ran: 109 of 109.
- **Unsure:** where the decorative pieces the owner did not place sit in row 73. **Still needs the game:** which way a turn and a tilt go (the calibration map, or a test file this tool writes for the owner to look at), and prices. The plan also notes what the storage numbers suggest (a 2,000,000-byte or 100-file limit), which is not proven.

### Reach Forge Printer, phase 3 part 2: the Forge World pieces' sizes, 2026-11-21

The owner, asked whether to work out the 97 pieces' sizes while his calibration map is unsaved: "Yes, piece sizes". A separate tool: nothing in the bot imports it.

- **New `tools/forge_printer/pieces.py`, run as `python\python.exe tools\forge_printer pieces [--measure] [--keep FOLDER]`:** `--measure` exports each piece's model from MCC's `forge_halo.map` with `model2obj` (run as its own program), measures the box it fills and rewrites the table; without it the command prints the table. The exported models are made from the game and stay in `E:\Proving Grounds\re_tools\forge_printer\pieces`.
- **New `tools/forge_printer/forge_world_pieces.json`:** names and sizes only, 108 pieces in the Forge menu's order by category: the owner's 97, Block 4x4 Short and Window Coliseum (not in his notes), and nine decorative pieces known only by model name. Each has the box it fills in world units, measured from the point Forge places it by.
- **Found:** a block's name is its footprint in world units (Block 2x2: 2.00 x 2.00 x 1.00; Flat 0.2-0.3 tall, Short 0.5, Tall 2.5-3.0). Wall Coliseum is 10 x 0.5 x 12, which agrees with the owner's own variant laying them 10 by 12 apart as a floor. Many pieces are not centred on their placing point.
- **How names were paired with models:** by the map file's order and likeness of name (the plan lists where that is argued rather than seen); the notes' "Block 5x1 Short" is the flat model. The owner then named the six door, window and wall models from a picture, in the same order the table has them (Door is the tall arch, Door Double the low piece).
- **Validation:** `tools/test_forge_printer_pieces.py` (new, 15 tests: a stand-in exporter, and checks of the kept table such as every "Block AxB" measuring A by B); full suite 1123 OK. `pieces --measure` ran on this PC: 108 of 108 exported and measured.
- **Not done:** prices; the calibration map (row numbers, items, rotation); piece fitting.

### Reach Forge Printer, phase 3 part 1: Guardian's play space cut out and sorted into surfaces; reference mesh turned Z up, 2026-11-21

The owner started phase 3 of `docs/REACH_FORGE_PRINTER_PLAN.md` with what does not need his calibration map (not saved yet): "cropping Guardian's backdrop and surface classification". A separate tool: nothing in the bot imports it.

- **Fixed: the reference mesh lay on its side.** `bsp2obj` writes its OBJ Y up; phase 2's `reference` kept that, while the spawns, weapons and objectives beside it are in the game's Z-up axes, so in Blender the level stood at right angles to its own placements (its "long y side" was the trees' height). `h3_reference.scale_obj` now writes the game's axes (`x, -z, y`, as `tools/heightmap.py` reads the same files). Proof: with that turn all 58 of Guardian's spawns have ground right under them; with the 47 other axis orders at most 11 do. Guardian's box is now x -18.95..20.08, y -35.27..6.07, z -38.23..91.45.
- **New `tools/forge_printer/surfaces.py`, run as `python\python.exe tools\forge_printer surfaces <reference folder> [--side 4] [--below 3] [--above 8]`:**
  - finds the play space by following the walkable ground under the spawns outward on foot (jump 1 u up, drop 4 u, gap 2 u; ground counts only where it covers 40% of a half-unit cell, which keeps leaves and branches out);
  - cuts the mesh to a box around that ground (triangles crossing the box are cut at it);
  - sorts every triangle by how far it leans: floor (to 10°), slope (to 55°), wall, ceiling (from 125°);
  - groups touching triangles that lie in one plane into patches, and marks the floors and slopes players actually walk on.
  It writes `<map>_play.obj` (one group per kind) and `surfaces.json` (the box, each kind's area, every patch of 0.25 u² or more with its plane, tilt, uphill direction and box) beside the reference; both are made from the game and stay local. It refuses a mesh whose spawns do not stand on ground, the check that would have caught the axis mistake.
- **`blender_import_reference.py`** also loads the play-space mesh when it is there (collection `play`: floor, slope, wall and ceiling as coloured objects) and hides the whole level behind it.
- **Guardian:** 58 of 58 spawns on ground; play box 39.5 x 36.0 x 23.3 u (z 8.4..31.7 of the mesh's -38..91); 99,022 of 115,250 triangles and 8,326 of 20,187 u² kept; floor 566 u² (509 walked), slope 377 (224 walked), wall 6,532, ceiling 852. A second run writes the same bytes. Blender 5.1 headless loads it (floor 7,696, slope 8,802, wall 64,892, ceiling 17,334 triangles); a top-down render shows the map's layout.
- **Validation:** `tools/test_forge_printer_surfaces.py` (new, 23 tests on a hand-built yard in a "forest") and two changed or new tests in `tools/test_forge_printer_reference.py`; full suite 1108 OK.
- **Not done / known limits:** the big tree trunks inside the box are still there, as walls (the mesh names no materials to tell them from the structure); a patch's area can exceed its outline where the render mesh stacks layers; no piece fitting yet. Only Guardian was run.

### Reach Forge Printer, phase 2: a Halo 3 map as a Blender tracing reference, 2026-11-21

Phase 2 of `docs/REACH_FORGE_PRINTER_PLAN.md` (brief: `docs/REACH_FORGE_PRINTER_PHASE2_BRIEF.md`). A separate tool: nothing in the bot imports it, and nothing under `brain/`, `native/` or `maps/` changed.

- **New `tools/forge_printer/h3_reference.py`, run as `python\python.exe tools\forge_printer reference <map> [--out FOLDER]`:** runs `bsp2obj` as its own program and writes the map's level mesh (`<map>.obj`) plus `reference.json` (spawns, weapons, objectives and other placements from `maps/<map>/objects.json` and `features.json`, facings converted from degrees to radians), all in Reach units through one constant, `H3_TO_REACH_SCALE`. Output goes to `E:\Proving Grounds\re_tools\forge_printer\reference\<map>\` by default and is never committed. Halo 3 maps only.
- **New `tools/forge_printer/blender_import_reference.py`:** `blender --background --python <script> -- <folder>` loads the mesh (Z up, 1 Blender unit = 1 world unit) and one named empty per placement in the collections spawns / weapons / objectives / other.
- **Validation:** `tools/test_forge_printer_reference.py` (new, 13 tests on hand-built inputs, one real-Guardian test that skips without MCC); full suite 1084 OK. Guardian: 115,250 triangles (as `bsp2obj` reports), 58 spawns, 21 weapons, 23 objectives, 14 other, none outside the mesh box; a second run is byte-identical; Blender 5.1 headless loads it with a mesh box equal to `bounds`.
- **Scale: 0.975, the owner's choice (same day):** `H3_TO_REACH_SCALE` went from 1.0 to 0.975, the ratio of the player models (0.742 u Reach / 0.761 u Halo 3; the numbers are in the plan's Phase 2 handoff note). Guardian re-exported at 0.975: 39.0 x 129.7 x 41.3 u, same counts, none outside the box, repeat run identical, Blender box matches; full suite 1084 OK. **Untested:** any map but Guardian, and Blender with its UI open.

### Reach Forge Printer, phase 1: read and write Reach map variants (.mvar), 2026-11-21

The owner's plan (`docs/REACH_FORGE_PRINTER_PLAN.md`): build Halo: Reach Forge maps in Blender and write the map variant file MCC loads, with no keystroke bot. Phase 1 is the file itself. A separate tool: nothing in the bot imports it.

- **New `tools/forge_printer/`:** `mvar.py` reads and writes a whole `.mvar` (the BLF chunks, plain or zlib-packed; the bit-packed content header, bounds, budget, Forge label table, all 651 object slots and the quota table), with every field kept as the file's raw number and helpers for world positions, turns and boundary sizes. `bitstream.py` is the bit reader/writer. `python\python.exe tools\forge_printer info|check|move` describes a variant, round-trips files and compares bytes, or writes a copy with one object moved (it never changes its input).
- **New `docs/reach_mvar_format.md`:** the layout field by field, how each value turns into world units, and what is still unknown (what MCC puts in the hash field, a 128-bit block version 32 adds, the up-vector axes, which palette row is which Forge piece and its price).
- **Validation:** `tools/test_forge_printer.py` (new, 28 tests, variants built by hand in the test); full suite 1071 OK. `check` on the 34 Reach map variants in this PC's MCC folder (Xbox 360 era and MCC-saved, seven maps): each parses to its last bit, its object counts match its own quota table, and each written back is byte for byte the same.
- **Tested in game by the owner, 2026-11-21:** a copy of an MCC-saved Forge World variant with a new title and one wall lifted 6 units ("FP Move Test A", made by `move`, kept in `E:\Proving Grounds\re_tools\forge_printer`, not in the repository) listed in Reach Forge, loaded, and showed the wall moved. **Still untested in game:** adding or removing objects, rotations, labels and budget changes.
- **New `docs/REACH_FORGE_PRINTER_PHASE2_BRIEF.md`:** the brief for phase 2 (a Halo 3 map as a tracing reference).

## 0.2.2-custom.12 — Project Reach: Reach's own menus, Noble, the Banshee pilot, bot simulation and Service Record, 2026-11-21

### Release build: map-pack tests skip without the map pack, 2026-11-21

- `tools/build_installer.py`'s test gate runs on a clean `git archive` copy, which has no git-ignored heightmaps. Eleven tests that load Blood Gulch, Launch Station, Boneyard or Headlong's heightmap errored there (`test_tank_drive`, `test_owner_routes`, `test_shoot_back`, `test_legendary_power_fetch`, `test_map_memory`, `test_layout_lifts`); they now skip without it, as the other map-pack tests do. Test files only.
- Validation: full suite 1043 OK in the working tree; 1043 OK, 45 skipped on a clean HEAD copy.

### Reach bots' reload press reaches the game, 2026-11-20

- Found: `maps/_inputs/reach.json` had no `reload` entry and `native/reach.cpp` writes none, so a bot's reload press never reached the game (of ~190 "reload between fights" presses a match, 8-26 were followed by a fuller magazine: the game's own reload of an empty one; Asylum 20261120-232338).
- New `tools/reload_capture.py` (read-only, player 0's raw action and magazine each tick) decoded the owner's own reloads: +0x40 bits 4, 16, 20 for ~0.12 s. Bit 20 is Use held (reach.cpp's), so `reach.json`'s new `reload` entry is +0x40 mask 0x10010 only.
- Validation: `tools/test_reload_capture.py` (new) and `tools/test_reload_timing.py` `test_reach_reload_reaches_the_game`; full suite 1043 OK. **Live check pending:** a bot's magazine up within ~1.2 s of its press.
- Live check Nov 21 (logs/trace_reach_forge_halo_20261121-135535, Asylum, owner + 3 Demon vs 4 Noble): 102 of 110 between-fight reload presses filled the magazine (Demon 50 of 52, Noble 52 of 58), median 1.19 s / 1.22 s after the press, the owner's own 1.11-1.16 s. Before: 8-26 of ~190 a match. Reach reloads confirmed working.

### Sword Base: the owner's patrol points and spots, 2026-11-19

- `maps/reach_20_sword_slayer/infantry_patrols.json` (new, 3 shared patrol points), `positions.json` and `callouts.json` (empty red/blue sneak lists) from the owner's Edit spots session. Map data only; untested in a match.

### Noble: eyes at head height, and only real rounds learned from, 2026-11-20

The owner's live Asylum game (`logs/bug_reports/reach_forge_halo_20261120-232338`; he and 3 Demons beat 4 Nobles 50-30) and his two reports. "Staticwolf shot the ground then stared at me" (killed at 35 s): at 27.17 s StaticWolf met him 11 deg under his head and swung up (0.17 s) before its first shot. Then, at no shield, it held "cover" 9 u from him for 3 s until its shield was full (Demon's recharge rule): the level's line from its middle was blocked 0.2 u in front, but he could see it. "Pwnagetv struggled to shoot me" (276-282 s): it fought him with 3, 2, 1 and 0 rounds in its DMR, then swapped back from the AR to reload while he was 5 u off. Both Nobles also pressed 10-12 times while a grenade left the hand (the game fires nothing then), and shot learning counted every press a miss.

- **Eyes at head height** (`Bot.noble_head_height`, in the walking and watching look): off a fight, a Noble looks at a standing man's eyes over the floor where it looks (`EYE`), never lower, and without the person-like up and down wander (-7.5 to +9 deg). Its look points were chest high over a man's feet or a corner's floor. Demon unchanged.
- **Only rounds that left the gun are learned from** (`noble.ShotWatch`): a press whose magazine never went down (a grenade in the hand, an empty magazine) is not a shot (`dry_presses`). Tonight's record (`user/noble_shots.json`, 420 "rounds", 56%) is set aside as `user/noble_shots.before_nov20_mag_check.json`, so it learns again from clean shots.
- Found, not changed: **reloads rarely happen, for every difficulty in Reach.** Of the "reload between fights" presses in tonight's game, 8 of 200 (Demon) and 26 of 186 (Noble) were followed by a fuller magazine within 3 s, about the same back to Nov 13 (Easy to Legendary alike). So bots start fights on part-spent magazines. The press goes through the Reach button map (`native/reach.cpp` `hb_apply_buttons`), not checked live yet. Also found: the cover a recharging Demon or Noble takes is tested from its middle only (`cover_from` / `hidden_spot`), so a shoulder past a pillar's edge shows.
- Validation: `tools/test_noble_learning.py` (a press that fired nothing is not a shot; an unread magazine still counts; eyes at head height over the floor, kept when higher or with no floor near). Full suite 1040 OK; a simulator game runs. **Untested in game.**

### Noble learns: self-play tuning, shot learning, winning spots; Demon's positioning back, 2026-11-20

The owner: "I want Noble to be our testing bot. So anything self learning we can give it ... we can try here", then "DO 1,2 and 4" (self-play tuning, shot learning, where it wins fights). Before it: 4 Noble vs 4 Demon, DMR Team Slayer on Asylum, lost 4-0 in the simulator and 3-0 live (the owner's games 20261120-210044/-210713/-211401: 50-24, 50-35, 50-43). Whoever hit first won every sim kill, and Noble's push walked into held angles. Live, Noble deaths "started hurt" 17% (Demon 6%) and "breaking off" 3% (Demon 58%) (`tools/death_autopsy.py`). The owner's C2IR report (game 2, 40 s: it kept a fight on Havoc94 out of sight 1.9 s with two more men on its radar, was shot by OutlawMarine, fought on at no shield) was Noble's chase limits being off.

- **Noble's settings from a learned file** (`brain/noble.py`, new; `tune`, `skips`): which of Demon's rules Noble keeps (`recharge`, `no_new_fight`, `break_second`, `odds`, `peek`, `objective`, `chase`), its `push` and `push_shield`, `long_pace`, `spots`, `spot_hold_s`, `shot_learn`, `explore`. Read from `user/noble_tune.json` over `DEFAULTS`: every Demon rule on, push 0. `brain/bot.py`'s Noble guards now read it (`noble.skips`), and `noble_push` pushes only by the tune and at `push_shield` or more. Demon unchanged.
- **Self-play tuning** (`tools/noble_tune.py`, new): 4v4 Noble vs Demon on Asylum (banshee_sim's match loop), every set on the same seeds with sides swapped; neighbours of the best tried, the best saved with `--save`. Workers run at below-normal priority, and their Nobles write nothing. First run (24 games to 30): the defaults won 4 of 4, **+4.8 kills a game over Demon**; spots off -1.0, chase off -2.0, recharge off +1.5, recharge and second-man off -4.2. Nothing beat the defaults, so no file was written.
- **Shot learning** (`noble.ShotWatch`, `noble.gap`, `noble.part`; `Bot.noble_fired`/`noble_learn`): every press of a precision gun is watched for his shield or body dropping within 0.3 s (a hit) or not (a miss). Shots a teammate firing at him may have landed are not counted. They are counted by distance band, by the pace since the last shot (x the paced gap) and by the part, into `user/noble_shots.json`. From it, `fire_gap` uses the pace that lands the most rounds a second, and while his shield holds it aims at the head or the chest, whichever lands more (head once his shield is down, and until learned). `explore` 12% of shots try another pace or part. `tools/noble_report.py` (new) prints the real per-round accuracy by gun and range.
- **Winning spots** (`noble.spot_for`, `Bot.noble_spot`): from the layout's map memory (`brain/lore.py` kills: 354 on Asylum, 14 cells won 60%+), each 2 u cell's wins and losses. A Noble with nobody in view about to walk at a man it knows of instead holds the best winning cell within 7 u with a line onto him, for 3 s, then goes on (live C2IR at 61 s walked at a radar dot and was shot first). It updates live as the map memory takes new kills.
- Not changed: the ~12 deg look at the floor as C2IR turned to a radar dot at 59.4 s (not explained); the simulator's spread is ASSUMED and has no bloom, so pace and aim are learned live only.
- Validation: `tools/test_noble_learning.py` (new, 18: tune file and override, hit, miss, kill, teammate's round, pace choice, part choice, spot choice, cache, the bot's hold and walk-on, the press hook); `tools/test_noble_difficulty.py` updated (defaults keep Demon's rules; push by tune). Full suite 1038 OK. Sims as above. **Untested in game.**

### Rebrand: Project Reach, 2026-11-20

The owner: "Starting here I would like to rebrand Everything that says Project Proving Grounds, or anything similar in code, on launchers, anywhere to our new title. Project Reach". Asked, he chose to rename it all, the matchmaking mode's name included; to change text only (file names, identifiers such as `proving_grounds.cpp`, `pg_*` and `botcore_pgNN`, the installer's data folder `ProjectProvingGrounds` and its `ProjectProvingGrounds-Setup-*` file names stay); and to keep the folders and the GitHub repository's name for now.

- **What a player or reader sees** now says Project Reach (252 places in 58 files): the in-game screens, the Service Record site's title and brand, the launcher's and tools' windows, the installer's name, shortcuts and default folder, README, the docs and code comments. Possessives read "Project Reach's"; the title screen and the standalone launcher's boot screen and splash read PROJECT above REACH.
- **Kept as they were:**
  - NOTICE.md's "Required Notice: Copyright 2026 the Project Proving Grounds contributors" (the PolyForm license wants it word for word), and every "Project Proving Grounds contributors" credit, the installer's publisher included;
  - the upstream credit ("a customized build of [Project Proving Grounds](https://github.com/AyoItzKye/project-proving-grounds)", "upstream Project Proving Grounds 0.2.2-s181"), and the 2026-11-05 handoff's sentence about customizing the upstream mod;
  - the separate GPL project's name, Proving Grounds Map Tools;
  - every folder path (E:\Proving Grounds\...);
  - this changelog's past entries, as history.
- **The standalone launcher** (E:\Proving Grounds\PPG Launcher, its own repository) got the same rename in its README, settings comments, console title, boot screen, route status lines and tests; its splash was drawn again.
- **Not changed:** pictures with the old name drawn into them (docs/banner.jpg, the launcher art), and on an existing install the old Start-menu shortcut's name stays until the next install.
- **Validation:** the full suite (1038 tests) passes. `tools/test_service_record.py` stops at `test_game_reads_the_sites_challenges`: its one test match makes no progress on today's drawn daily challenges, which comes from the date and not from the rename (that file's only changes are docstrings). `build.bat pg37` builds `botcore_pg37.dll`. The preview's title, Proving Grounds menu (now PROJECT REACH), Matchmaking and Start menu screens were checked by eye. The standalone launcher builds and its boot tests pass. The site was rebuilt with the new title.

### Noble: a smooth swing then a lock, never a miss with precision guns, and it takes the fight, 2026-11-20

The owner's Forge World report (`logs/bug_reports/reach_forge_halo_20261120-172336`, read by the bug-report session): four Nobles were in a fight goal 1-12% of the time, "they should be killing me quicker", and their aim "flick[s] directly at the ground". Then: "make noble as good as humanly possible ... never miss a shot from here on out with precision weapons."

- **No flick** (`brain/bot.py` `Aim.noble_lock`, `brain/profiles.py` `NOBLE_TURN`): the 3000 deg/s turn (a ~100 deg jump in one tick onto a new man) is back to Demon's 700. The swing onto a man is eased in (`NOBLE_EASE_S` 0.06 s, within the turn speed) and locks within `NOBLE_LOCK_R` (1.5 deg). Locked, it follows him exactly while he moves under `NOBLE_HOLD_R` (20 deg) a tick. `s.goal` stays the exact point.
- **Never a miss with precision guns** (`PRECISION`: DMR, magnum, needle rifle, BR, carbine, sniper...): Noble presses only on the tick its lock is on him (`noble_on`), never while it swings on, so Demon's protected DMR/sniper head snap after the turn cap moves it by nothing. `Bot.fire_gap`: the paced cadence at every range (DMR 0.4 s; x`NOBLE_LONG_PACE` 1.2 past 10 u), never the Short band spam, so each shot's bloom has settled. The head from the first shot (as before).
- **It fights** (`Bot.noble_push`, new): on foot, not carrying, a man in view is fought `NOBLE_PUSH` (0.25) over its best other choice (retreat, gun, objective, hunt). Demon's back-off rules are off for Noble: the odds break-off, "not taking him on", the hunt into a group and the full-shield re-peek (`demon_odds_rules`: the team's trades and callouts kept), cover until full (`demon_recharge`), no new fight hurt (`demon_no_new_fight`), out of a second man's sight (`demon_break_second`), the peek wait (`peek_timing`), the objective cap (`demon_objective`) and the chase limits (`chase_ok`). Demon unchanged.
- Not changed: the game's own spread beyond bloom, a head the bots' level data does not know is covered (the report's 9 rounds at 24-28 u that did nothing are not explained), and Reach riders' heads (not read: chest).
- Validation: `tools/test_noble_difficulty.py` (smooth swing from 120 deg round within the turn speed, eased, locked in under 0.45 s; no press while swinging; paced at every range; a man in view first; the back-off rules off; the earlier lead tests on the lock's point). Full suite 1020 OK; `live_bots` imports. **Untested in game.**

### Noble aims like an aimbot: every gun, seat and vehicle, 2026-11-20

The owner: "I want you to make the noble difficulty to practically be an aimbot. I want their accuracy to be close to 100%. With all vehicles and all weapons that are precision based."

- `brain/bot.py` `Aim.noble_lock` (new), called from `Aim.step` for a Noble with a target: the view is set every tick to the exact angles from the shot's origin (the eye, a turret's pivot, a vehicle's camera) to the caller's point (head, chest, an explosive's feet, Halo 4's real point), with no error, tremor or flick. It leads by the shot's whole flight to where he will be (solved three times, `NOBLE_LEAD_ITERS`) plus the 0.034 s read delay (`DEMON_LEAD_S`) where the caller had not led it already. Hitscan precision guns (`PRECISION` without a `PROJECTILE_SPEED`) lead by no flight. Every caller of `Aim.step` with a target gets it: on foot, driver guns (Banshee, Ghost, Wraith, Scorpion, Reach's own bolt speeds), gunner and passenger seats. Demon itself leads nothing (`DEMON_AIM` lead 0); Noble's lead is the main change for projectiles and vehicles.
- `Bot.aim_head`: Noble with a precision gun aims at the head of a man on foot from the first shot (Demon: the chest until his shield is down, 97%).
- `brain/profiles.py` `NOBLE_TURN` 3000 deg/s (Demon 700): `Bot.turn_cap` lets the lock reach a new man in about two ticks.
- Kept: Demon and every other difficulty unchanged; Noble keeps Demon's DMR/sniper head correction, Reach direct fire, Halo 4 lock and Warthog-gun lock (it is a Demon to those). Firing pace (DMR bloom pacing) and the game's own spread are not changed, so real hit rates will be under 100%.
- Validation: `tools/test_noble_difficulty.py` aimbot tests (a still head at once, a strafing man with the DMR, a Banshee-speed bolt meeting a running man within 0.02 u where Demon's misses by over 1 u, rockets at the feet, a caller's point kept, a juking man tracked every tick within the turn cap, the head from the first shot). Full suite 1014 OK; `live_bots` imports. **Untested in game.**

### Vehicle guns skip men they cannot hit; boarded gunners get out; tanks run boarders down, 2026-11-20

The owner's F9s on Boneyard (`reach_70_boneyard_20261120-164229`): a screenshot of a Warthog gunner (Partyland) "the gunn aims straight down even when their reticle in the right plac.e", and "Acsencion didnt shoot at the bot closest to him when in the scorpion and got jacked"; then "Yes, fix it".

- **Found:**
  - At 341.7 s Tower 2 (the other team) boarded Partyland's Warthog. Partyland, in the turret (Demon, with the chaingun lock), kept him as its target and aimed at his chest inside its own Warthog, as far as 65° down (343.6-346 s, 5:47 on the theater bar); also at 331.6 s at a man 0.8 u beside it.
  - In that match gunners spent 149 aiming ticks on a man inside their own vehicle and 168 more than 0.6 rad down. Normal-aim gunners never went past 0.36.
  - Ascension (Demon) driving a Scorpion backed away at full reverse from Sh4d0wLux walking at it (3.9 → 0 u, 248-251.7 s). It never fired, since the cannon's 0.1 s settle never held, and it was jacked.
- `brain/bot.py`:
  - `Bot.gun_reach`, used by `crew_target`: a vehicle seat takes no man in its own vehicle. A mounted gun also takes none more than `GUN_DEPRESS` 0.6 rad below where its shot leaves (`turret_origin`, else the seat's gun height); another man in sight is taken instead.
  - `Bot.boarded_by`: a gunner or passenger with an enemy in its vehicle holds Use to get out (as every get-out) and fights on foot, with no ride again for 5 s.
  - A Scorpion's or Wraith's driver (the artillery role) runs a man on foot within `vehicles.BOARD_D` (6 u) down, at full throttle toward where he will be, with no shell at that range. Not a man in Armor Lock (the rammer dies); Easy backs off as before.
- Validation: `tools/test_vehicle_gun_reach.py` (new, 6):
  - not a man in our own vehicle nor one at the wheels under the gun, another taken;
  - a boarded gunner gets out, none without a boarder;
  - a tank runs a man at 3 u down without a shell;
  - Easy and Armor Lock still back off, and far men are shelled as before.

  Full suite 1006 OK; `live_bots` imports. **Untested in a match.**

### Noble: a testing difficulty, Demon's base, in game only, 2026-11-20

The owner: "Add a new difficulty only to our in game. It's our new testing difficulty We will call it Noble. Make its base the same as a demon bot and then we will train it."

- `brain/profiles.py`: `NOBLE = "noble"`; `make_profile("noble", ...)` is `make_profile("demon", ...)` with `label="noble"` (tier `demon`, extra None), so every Demon rule, aim, hand and timing applies unchanged (`fixed_demon`, `demon_rules`, `demon_eyes` all true; never a Wheelman). New `fixed_noble(prof)` is where its training goes, so Demon stays as it is. `brain/odds.py`: Noble's Reach pace share and own pace are Demon's.
- BOTS panel (`native/bots_panel.h`, `bots_panel.cpp`): `HB_TIER_NOBLE 9`, `HB_TIERS 10`; "for everyone" difficulty 10 (`shared.h`, `botcore.cpp` launch table and ini read, `% 11`). Noble has its own gold row under Scaling in the bot inspector, and a button after Demon in Quick setup and the footer (`DIFF_CHOICES 11`; Quick setup 680 -> 740 px wide, footer row 660 -> 720). Like Demon: no Wheelman style, 12 matchmaking points, counted as a Demon by the team balance's Demon stacking, five chevrons, Demon's rank tours (10-11), Demon's lobby "sweat" (`proving_grounds.cpp`). Not in Mixed. `overlay.cpp` lobby line names it; `tools/botctl.py` keys; `observer.py`, `player_stats.py`, `match_export.py` show "Noble".
- **Not on the Service Record site:** its difficulty editor (`service_record.TIER_KEYS`, `app.js` `TIER_NAMES`) and the bot simulation (`tools/bot_sim.py`, `sim_engine.py`) are unchanged. A pool bot saved as Noble in game shows no difficulty name on the site and is simulated as a Mixed bot.
- Validation: `tools/test_noble_difficulty.py` (new: a Noble equals a Demon from the same seed field for field except the label; panel, launch and points tables; not on the site); difficulty, ranks, Wheelman, matchmaking and Tactician table tests updated. Full suite 1000 OK. Native pool checks pass (`build_pool_test.bat` itself fails to link: it lacks `armory.cpp` since the Armory change, run here with it added). Built `native/bin/botcore_pg39.dll`. **Loads at MCC's next start; not yet seen in game.**

### Reach Banshee pilot: kills first, and a Boneyard flight simulator to tune it, 2026-11-19/20

The owner's goal: one bot 18-20 Banshee kills a game, three games in a row, in an 8v8 Slayer to 100 on Boneyard (the live variant `v8d2f4510`), the Banshee's team all Demon and always seated, the other team all Normal. Then: "prioritize getting as many kills as possible a match inside the Banshee instead of survivability ... at least 10 kills in one life, that is a net positive. I don't want the Banshee to survive long if they have zero presence on the map." **Not reached:** best sim game 14, best batch average 6.2. Paused for the owner's live test.

- New `tools/banshee_sim.py`: its own match loop running the real `Bot.think` and `Director` for 16 players and Boneyard's Banshee (walk, DMR hitscan, the Banshee's turn, boost, bolts and bomb from the owner's captures; `--seat-team`, `--red-tiers`, `--pilot`, `--trace`). The Banshee's body is **ASSUMED** 82 DMR rounds: the owner counted 38 but thinks it has damage thresholds that reset, "Just average it in the middle", between 38 and the ~125 that matched live ride lengths. Wing tips (`HULL_HALF`) in its collisions.
- Flying (`brain/bot.py`, `brain/terrain.py`, `brain/vehicles.py`, Nov 19): Boneyard's own pass length (`CLEARANCE_MAP` `extend`/`out_s`, the owner's), runs on men the team knows of (`air_hunt`), the no-fly box over the scaffolding west of the middle (`vehicles.AIR_NOFLY`, `in_nofly`), headroom under kill volumes (`terrain.AIR_HEADROOM`), traps it was boxed in at and the way back out along its trail (`air_trap_note`, `air_backtrack`), wing-tip probes for recoveries (`wide_clear`, `fly_probe`), a no-headway check in `oob_escape`, and open-air spots (`air_loiter_spots`).
- Reach bomber (`Bot.reach_bomber`, Nov 20): full throttle into a run, no 6 u/s governor, boost on straight legs inside gun range, a rolling turn (`AIR_BOMBER_TURN` 0.6) only for a man within 25 u; never breaks off when shot (`air_hot` off for it); its pick prefers a bunch the bomb can kill several of (`AIR_BUNCH_R`/`W`; the 17-, 15- and 14-kill sim games each opened with one bomb on Normal's team leaving spawn, 3-5 kills); men under a roof are not its (`air_open_sky`: `shot_los` up a steep line reads blocked everywhere, so `aim_hit` rays); with no line to its man it flies level over the top and bombs from over him (`air_line_clear`, `AIR_OVER_R`); a man never seen for 8 s of a run is let go (`AIR_CHASE_S`); with nobody in sight it flies to the most open spot by their base and holds there facing it (`air_seek`, `air_open_spots`: 12 u open, 8 u off the no-fly box; their flag itself is inside their base's walls), not over its own team, where it sat boxed in for 100-220 s of a ride; round the no-fly box by its corners, not through it (`nofly_detour`); boost only with 20 u open ahead (`boost_open`: boosted across their spawn it overshot into a slot it never left); its run's bomb no farther than 11 u (`AIR_BOMBER_DROP_R`: in the sim 15-18 u flat killed 1 in 14, the 2-3 kill bombs came from 8-9 u flat) and only with the craft's own nose on him; inside bomb reach the nose stays on him (no climbing).
- After the owner's live test (Boneyard 20261120-164229, Partyland: "it gets a glimpse of one shoots at it then flicks away ... by shooting then gaining height it moves its reticle upwards"): its view left its man within 1.2 s of finding him 39 times, 18 on air_guard's "the ground on the run, pulling out", 10.5 u over him and 17 u off. A Reach bomber's dive now looks for the ground only to `AIR_BOMBER_PULL_SPARE` (5 u) short of its man, never under `AIR_PULL_MIN_S` (0.4 s) of flight (the ground at his feet is the aim; a hill or deck between still pulls it out). And its selected bomb waits up to `AIR_BOMB_HOLD` (0.4 s) for a man under its aim (`bomb_lined`), else goes back on the cannons unfired, the bomb kept (the owner: "the third shot was a miss because he shot right as he flicked his aim away"); not on Invasion's room bombs. Sim, 10 games each: the pull-out alone 10, 5, 7, 7, 6, 7, 4, 12, 2, 3 (mean 6.3, opening rides 4.0 kills, were ~2.4); both 4, 9, 3, 6, 10, 6, 12, 7, 5, 4 (mean 6.6, worst 3; 104 men hit by 119 bombs, was 64 by 127). Full suite 1000 OK. **Untested in game.**
- The setup first handed to the owner for live testing was the best sim batch, `s4`: 10 games 5, 12, 2, 10, 10, 3, 3, 5, 9, 3 (mean 6.2, three games 10+). Tried after it and taken back out: the snap bomb (`air_snap_bomb`) on the craft's nose and 11 u (bombs dropped to 0-9 a game: the nose rarely lines up in that window); skipping over-the-top runs across the box; and the feet-floor rule in `Terrain._ray` lifted for aircraft. That rule reads every line from a Banshee to a man more than ~51 deg under it (and from him up to it) as blocked, so a pilot never sees a man straight under it and men never see a Banshee straight over them; lifting it both ways cut the sim pilot's kills (5.2 and 4.3 a game), so it is left as it was. **Worth a decision**: it is a live perception bug for every aircraft.
- Tried and removed the same day: waiting out of their sight / out of their DMRs' reach (exposure counts, cover spots). It kept the Banshee alive but killing nothing, which the owner ruled out.
- Sim results, 8 games each (best pilot's Banshee kills): aggressive 8, 6, 2, 4, 1, 12, 6, 1; with open sky 8, 8, 3, 11, 6, 5, 0, 5; with over the top 4, 9, 9, 3, 12, 5, 5, 3. The limit now is targets: of the Normal men within 40 u of the Banshee about 1 in 5 had a round's line from it, the rest behind Boneyard's structures.
- Tests: `test_reach_boost` / `test_banshee_owner_bombs` changed for the bomber's new rules (bomb reach 11 u, boost in the dive, the near-man turn); full suite 1000 OK. **Untested in game**: every brain change runs in the owner's next Reach match with a bot Banshee.

### Bot simulation: a clan queues as one group, 2026-11-20

The owner: "Do the bots simulations ever take clans into affect? I don't think I see clans playing together" (then "Yes I think that would be a good change"). Clanmates were partied 85% of the time, but only from those who had each rolled to play that round and each picked the same playlist: in the 984 stored simulated matches two clanmates met in 37, and clan bots had a clanmate on their team in 87 of 338 games.

- `tools/bot_sim.py` `clans_together` (`CLAN_TOGETHER` = 0.85): once a round, each clan of two or more queues as one group or not. A grouped clan plays the round when any member would (members in your match still sit out), goes to one playlist (by its members' average lean), and is partied by `parties_of(together=...)` as before (a team at most).
- `team_split` / `lobbies_of`: a lobby takes a party only while its teams can still be made (3 + 3 + 2 cannot be 4 + 4: that full lobby had waited), the parties of two or more are put on the teams that balance skill best, the lone bots dealt after. A Demon's clan party left in a short lobby may now change places with as many lone non-Demons of a full one, when that lobby still splits.
- Measured on the owner's pool, 200 rounds of who plays and the lobbies (no matches played, nothing stored), against the same settings without the change: clan bots with a clanmate on their team 87% of their games (was 58%; most clans of the pool are Demons, who meet anyway now that they play every round); clan bots 0.76 games a round (was 0.63), e.g. SuperWoman 0.04 → 0.83, Tower 2 0.14 → 0.81; about 318 bots seated a round (313); Demons still 1.00.
- Validation: `test_bot_sim` 17 OK (new `test_a_clan_queues_as_one_group`: a clan of one never groups, 85% of rounds, clan ABC whole on one team most rounds at a pace that alone almost never plays; `test_demons_play_a_game_every_round` holds). `bot_sim` imports. **Not yet seen after a real match.**

### Bot simulation: grinders rolled by difficulty; Scaling bots now Tactician or Heroic, 2026-11-20

The owner: "every single bot doing like a percentage roll to see if they get the trait ... every single demon will have a 75% chance to have the grinder trait", then Mythic 65%, Legendary and Tactician 50%, Heroic and Normal 25%, Easy 5%; and "I want all of the bots that are scaling to be changed into the heroic and tactician categories ... 60% being in favor to tactician."

- `tools/bot_sim.py` `GRINDER_CHANCE` / `grinder_chance`: a bot grinds when its name's fixed roll (`hfloat(name, 41)`, unchanged) falls under its difficulty's chance, so each bot keeps its trait until its difficulty changes. Blind and Scaling, not named, take Legendary's 50%. `sim.grinder_<tier>=` in `proving_grounds.ini` changes one. The old `grinder_top` (30%, Legendary and above) / `grinder_other` (10%) settings are gone. `--stats` lists grinders by difficulty.
- Owner's pool now: 402 of 753 bots grind (53%; was about 20%). Demons grind at 75% but already play every round, so it changes nothing for them.
- The round grows instead of the grinders shrinking (the owner: "Yeah, make it bigger"). `population`: grinders always get `grinder_pace`; the others get whatever brings the average to `pace`, but never less than the new `other_pace` (0.074, what they had under the old chances). The old 90% cap that scaled grinders down is gone. Under the old cap, twice as many grinders had cut a grinder to 40% of rounds. Owner's pool now: grinders' median pace 1.00 (about 63% of rounds, as before), the others' 0.078 (about 7.5%), about 321 bots a round (was about 225 before today, 248 with the cap): 26 Arena and 7 Big Team Battle lobbies. A round takes roughly that much longer after each match (not timed).
- **Local data only (git-ignored `native/bin/`):** the 80 Scaling bots were shuffled (seed 202611201) and saved 48 Tactician, 32 Heroic with `service_record.set_bot_difficulty`, MCC closed. Backups `bot_pool_saved.ini.before_scaling_split_20261120`, `botcore.ini.before_scaling_split_20261120`. Pool now: Legendary 187, Tactician 168, Heroic 125, Mythic 106, Demon 86 lines, Blind 59, Normal 19, Easy 2.
- Validation: `test_bot_sim` (16 OK; `test_pace_averages_what_is_asked` now checks every bot's roll against its tier's chance and an ini override, that few grinders still average `pace`, and that many keep full pace with the others at `other_pace` or more). Full suite: 4 failures, all in the Banshee/boost tests (`test_reach_boost`, `test_banshee_owner_bombs`) over other sessions' uncommitted `brain/` work; none in the simulation. `bot_sim` imports. **Not yet seen after a real match.**

### Any gametype can fill any vote option, 2026-11-19

The owner: "Make it to where any mode can appear on any vote tab. So if a 46% chance happens to be slayer all three times make it so."

- `native/proving_grounds.cpp` `take_options`: the first pass now keeps only the maps apart, so each of the three options is its own roll of the playlist's weights and a gametype can come up more than once (on different maps while there is a choice; never the same map and gametype twice). The ini weights are unchanged. `tools/bot_sim.py` `draw_options` matches, so simulated matches vote the same way.
- Measured over 20,000 draws of the simulator's port with the owner's ini and pool. Slayer's share of slots 1/2/3 went from 34/24/17% to 34/33/33% in 4v4 (weight 33%) and from 36/25/17% to 36/35/35% in 8v8 (weight 35%). All three options are Slayer 3.5% / 4.3% of the time. Slayer is played 54% / 62% of games with bots alone voting (51% / 61% before; the bots favour it).
- Built as `botcore_pg38.dll`. Full `tools/test_*.py` suite OK. **In game from MCC's next start; not yet seen live.**

### Proving Grounds rows show the Reach rank only, 2026-11-19

The owner: "can we remove their mcc ranks from our proving grounds matchamking? Like leave the reach ranks but remove the ones mcc has from inside our mod launcher".

- `native/proving_grounds.cpp` `player_row`: the MCC tour/level badge left of the team bar is no longer drawn. The Service Record's Reach rank in its cell past the nameplate stays. MCC's own session list (`overlay.cpp`) and the BOTS panel keep theirs.
- Built as `botcore_pg37.dll`. `pg_preview` lobby, roster and vote screens drawn: the rows carry the Reach rank only. **In game from MCC's next start; not yet seen live.**

### The Mixed bots get their own difficulty, Heroic to Mythic; the simulation finds every saved one, 2026-11-19

The owner: "Distribute the mixed difficulties randomly across Heroic up to Mythic. Make the cooler names mythics."

- **Local data only (git-ignored `native/bin/`):** the 571 pool bots with no saved difficulty (they took the lobby's Mixed) each got a `saved=` line in `bot_pool_saved.ini`, written by `service_record.set_bot_difficulty` with MCC closed (so `botcore.ini`'s lobby list follows too). 91 hand-picked names are Mythic (the edgier ones: Reaper343, VoidHunter9, GodofInjustice, Bl4dePh4ze, NullExecution, ScytheWarden and the like); the other 480 were shuffled (seed 20261119) and dealt evenly, 80 each, to Heroic, Legendary, Scaling, Demon, Blind and Tactician. Bots already saved kept theirs. Backups: `bot_pool_saved.ini.before_mixed_deal_20261119`, `botcore.ini.before_mixed_deal_20261119`. Pool now: Demon 127, Blind 117, Legendary 109, Mythic 106, Tactician 100, Heroic 93, Scaling 80, Normal 19, Easy 2.
- `tools/bot_sim.py` `population` / `tier_of`: a saved line is found as the BOTS panel finds it (`pool_name`, no case). Five pool names cut to 15 with a trailing space (`ii Toxic Moose `) and `Death Adder` (saved as `Death adder`) had been dealt a Mixed tier by the simulation; the site and the simulation now count the same tiers.
- Validation: `test_bot_sim` `test_saved_difficulty_found_as_the_panel_finds_it` (new); every one of the 571 read back with its dealt tier; site rebuilt. Full suite 993 OK; `bot_sim` imports. **In game from MCC's next start; not yet seen in a lobby.**

### Bot simulation: Demon bots play one game to each of yours, 2026-11-19

The owner: "I would like all the demon difficulties to play just as much as me. So they play 1 game to my 1 game."

- `tools/bot_sim.py` `EVERY_ROUND = {"demon"}`: a Demon bot (its saved difficulty, or the lobby's when it has none) plays a game every round; one round runs per Proving Grounds match of yours. `games_this_round` replaces the pace draw for them; the other bots' pace is worked out without them, so theirs is unchanged (about a third of yours on average). One game a round at most and the bots of your match sitting that round out still hold.
- `lobbies_of(first=...)`: parties are shuffled into lobbies, so a short lobby left a few bots waiting. A Demon in a short lobby now changes places with a non-Demon party of the same size in a full one, so Demons still play mixed lobbies. A clan party of Demons with no same-size party to change with can still miss a round.
- Validation: `test_bot_sim` `test_demons_play_a_game_every_round` (new: always entered; never two games a round; 95%+ of rounds played, none missing two of four; sits out the owner's match), `test_pace_averages_what_is_asked` updated. A 750-bot test world: 131 Demons played 783 of 786 possible games over 6 rounds. Full suite 992 OK; `bot_sim`, `sim_engine`, `bot_career`, `service_record` import. **Not yet seen after a real match.**

### Bot simulation: a bot plays at its difficulty's strength, 2026-11-19

The owner: "Banevent has a 0.40 kd when he is a demon", then "Simulated strength should be based on their difficulty".

- **Found:** the simulation started each bot at its tier's skill (`TIER_SKILL`) and then fitted it by name from its real matches, all of them kept through stat resets. Banevent's 7 real games (56 kills, 112 deaths; the four on Nov 15 at a tier the logs do not record) put a Demon (+1.1) at −0.36, below Heroic, so he went 37-93 in his 5 simulated games. The logs record no tier per match, and the fit counts each kill and death as one fight, so a few games outweighed the difficulty.
- `tools/sim_engine.py` `Model.inputs_of` and `tools/bot_sim.py` (team balance): a bot's strength is its difficulty's `TIER_SKILL` only. A change on the site's difficulty picker applies from the next simulated round. `fit` still works out `Model.skill`; nothing simulated uses it. Pace, assists, weapons and the other per-bot numbers still come from real matches. Simulated matches already stored keep their own numbers.
- Validation: `test_bot_sim` `test_the_model_learns_from_real_fights` also checks that `inputs_of` gives the tier's strength for a bot whose fit is far above or below it. Full suite 991 OK; `sim_engine` and `bot_sim` import. **Not yet seen after a real match** (the next round runs after your next Proving Grounds match).

### A man half in view is still noticed (the notice timer through short gaps), 2026-11-19

The owner's F9 "Partyland doesnt shoot at me again when he can clearly see my head" (Sword Base `20261119-211332`), and "he could clearly see my head even when crouching"; then "Yes, fix it".

- **Found:** at 143.6-145 s Partyland (Demon) walked toward the owner 7-9 u off, 5-14° from the middle of its view. The bots' data had the owner's head clear and his chest flickering between clear and blocked behind a glass ledge. A bot notices a man only once it has seen him through its reaction time (`Perception.pending`; Demon's is 0, so two seen ticks in a row), and any unseen tick dropped the notice. A Demon seeing a man every other tick never noticed him; it held only a radar dot of him.
- `brain/bot.py` `Perception.update`, `NOTICE_GAP` 0.4 s, `Perception.pending_gap`: the notice runs on while the man is out of sight for up to 0.4 s at a time and still inside the view. The deadline set at the first sight is kept, so a bot notices him on the next tick it sees him after it. A longer gap, leaving the view, or a miss through active camo (still only a shimmer past 4 u) starts it again, as before. Every tier.
- Validation: `tools/test_notice_gap.py` (new, 5: a Demon notices a man seen every other tick within 4 ticks, and with no grace it fails as before; a gap over `NOTICE_GAP` starts it again; Legendary's real reaction time kept through short gaps; leaving the view; active camo). Full suite 991 OK; `live_bots` imports. **Untested in a match.**

### Sword Base: level data rebuilt (8 floor levels, its render glass), 2026-11-19

The owner's F9 "Partyland doesnt shoot at me again when he can clearly see my head" (`reach_20_sword_slayer_20261119-211332`, 166 s), and "some ledges are glass see through but he could clearly see my head even when crouching. I could shoot him if I wanted"; then "Yes, rebuild it".

- **Found:** 26 of the 28 Reach heightmaps were built on Oct 22, when `tools/heightmap.py` kept 4 floor levels per cell (it keeps 8 now); only Island and Boneyard were rebuilt (Nov 5). Sword Base stacks 8-9 levels and lost the most: 37 of its 310 spawn spots had no floor. The old grid also ended 1-2 u past the play area, with the sword alcove on its edge. Its `wall_kinds.json` came from the kit's collision materials only (5 glass and grate shaders). The map's render glass (`conference_table_glass` 30,924 triangles, `table_top_glass`, `m20_glass_panel_high_opacity` and others) was solid to the bots. The bots' data blocked 25 of 46 real kill lines there at chest and head (last night's map 8%).
- **Rebuilt** from MCC's `20_sword_slayer.map`, the main and `_shared` structures (`_hidden` cannot be read by the tool and is not used):
  - the mesh with `tools/map_tools/bsp2obj.exe`, into `maps/reach_20_sword_slayer/source/`;
  - `heightmap.npz` and `topdown.png` with `tools/heightmap.py` at today's 8 floor levels and a 6 u margin. The default 40 u would have made a grid 28 times the old one for nothing; the new one is 150 × 153 cells against 108 × 119.
  - `wall_kinds.json`: the render glass merged in (`bsp2obj --glass`; upright faces as windows, flat ones as glass decks). That adds 889 window cells and 637 deck cells, and widens 1,087 existing ones. All see-through triangles are taken, since the export names no material per triangle; lights and high-opacity panels are about 1,400 of the 35,260. Also `glass.json`.
  - The old files are in `logs/sword_base_rebuild_20261119/before`.
- **Measured** (base map and variant `v04abd98b`): spawn spots off the floor 37 → 0 of 310. The sword is reachable, and paths end 0.1-0.55 u from it. Kill lines blocked 25 → 22-23 of 46. On Partyland's line from 140-167 s, the exact level mesh (glass left out) shows a clear line in 67 of 100 rows, the bots' data 57 before and 58 after. The terrain builds in 0.7-4 s; three walks to the sword take 0.02 s.
- **Partyland, not fixed by the data alone:** at 143.6-145 s he faced the owner (7-9 u, 5-14° off) with the owner's head clear in the bots' data and his chest flickering between clear and blocked. One unseen tick drops the notice timer (`Perception.update`, `pending`), so a man showing only his head over a ledge is never noticed. At 166 s itself a real solid wall stood between them (the mesh agrees).
- `heightmap.npz`, `topdown.png`, `glass.json` and `source/` are map-pack data (git-ignored): this checkout has them; a release needs them in the map pack. Validation: 986 tests OK; `live_bots` imports. **Untested in a match.**

### Proving Grounds: Reach's Custom Game lobby, and the other game lobbies (phase 5), 2026-11-19

The owner: "Next phase", after the frames of Reach's CUSTOM GAME, SELECT GAME TYPE, GAME OPTIONS, FIREFIGHT, FORGE and THEATER lobbies. Then he sent four paintings: "Four original screens for the game menus as well".

- **CUSTOM GAME** (`native/proving_grounds_reach.inc`; the main menu's CUSTOM GAME opens it instead of leaving for MCC's lobby):
  - The banner shows the map's picture with the game type's icon. GAME TYPE and MAP come from MCC's own lists, the variant library that `pg_lobby.cpp` copies: built in, MCC's own and the player's saved ones.
  - The picks are saved in `native\bin\reach_menus.ini` `[custom_game]`.
  - START GAME starts the game through MCC's own lobby, the way matchmaking's vote winner starts (`pg_lobby_launch`). Proving Grounds then closes, as for any custom game: it is not a matchmaking match and is not on the Service Record. If MCC refuses the game, the lobby shows MCC's reason.
- **SELECT GAME TYPE:** the families MCC has, in Reach's order. Right or A opens a family's game types, with the player's own ones marked YOURS. The picked one has a gold diamond. The card at the right holds the family's icon, the name, team game or free for all, and where it is from.
- **SELECT MAP:** MCC's maps, 15 at a time. Maps the game type does not go on are dimmed and refuse A; this is MCC's own check (`pg_lobby_check`), asked 64 maps at a time. The map's picture is shown, with built in, MCC's or yours, and for a saved variant the map it is made on.
- **GAME OPTIONS:** the game type, its kind of game, teams and where it is from. The rules are changed in MCC's own lobby and saved with the game type; the page says so.
- **CAMPAIGN, FIREFIGHT, FORGE, THEATER:** their lobbies' looks only. The banner shows the mode's painting. Each has Reach's rows, dim: Forge shows the Custom Game map, Theater the newest film in Temporary History. Each says the mode is played from MCC's own menus. The main menu's six entries are all on now.
- **Paintings:** the lobbies use `native\bin\pg_backgrounds\custom_game`, `campaign`, `firefight`, `forge` and `theater` (.png or .jpg), never in git. Where one is missing, the matchmaking painting is used. The owner's four paintings came only as pictures in the chat, so he saves them there himself.
- **Validation:** preview screens 39-43 were checked by eye with the preview's stand-in lists; the full suite (986 tests) passes; `build.bat pg36` builds `botcore_pg36.dll`. **Untested in game:** the start from this lobby, and MCC's map check of a game type.

### Proving Grounds: Reach's File Browser, Controller and Network Status (phase 4), 2026-11-19

The owner sent 17 more frames of Reach's menus: FILE BROWSER, the Start menu on CONTROLLER, NETWORK STATUS and HALO WAYPOINT, the CONTROLLER page, and the Firefight, Custom Game, Forge and Theater lobbies with their game type, mission and option pages. He was asked which to build and chose the Start menu's pages. The lobbies are not built.

- **FILE BROWSER** (`native/proving_grounds_reach.inc`):
  - It lists this PC's own Halo: Reach files. **TEMPORARY HISTORY** is MCC's `Temporary\UserContent\HaloReach`: the game types, maps and films of recent games (here 50, 50 and 12). **LOCAL FILES** is MCC's `LocalFiles\<id>\HaloReach`: the saved ones.
  - The second page shows the kinds with their counts; Right or A goes into the files, 15 rows at a time. The right side holds a card with our own mark for the kind, then the file's name, description, creator, last editor, date and size.
  - These come from the file's own content header (`chdr`): the name at 0xC0 and the description at 0x1C0 (UTF-16, big-endian in map variants), the creator at 0x88 and the editor at 0xAC.
  - File Share, Active Transfers, Recommendations and the searches were Bungie.net's, so they are shown dim.
- **CONTROLLER:**
  - The Start menu lists its rows beside a controller we drew. The page shows Halo: Reach's controls as MCC keeps them in `Saved\Config\WindowsNoEditor\GameUserSettings.ini`, entry 6 of each list (Reach). For example: look sensitivity 10 across and 11 up and down, hold to crouch, clench protection off.
  - The button layout shows as MCC's preset number, because MCC's names for its numbers are not known.
  - It only shows them: they are changed in MCC's own Settings, which writes that file.
  - **Later the same day,** the owner: "Use this image for the controller on there instead of whatever you drew". His picture is drawn on the Start menu and the Controller page instead. It is cut out of its white ground (the white touching the edges made clear, the light body kept) and kept in this PC's `native\bin\pg_backgrounds\controller.png`, never in git. Our drawing is still used where that file is missing. Then: "controller typed out is cut off in the second photo. Remove the word". The Start menu's controller picture has no name across it now, and the other entries' names shrink to fit their panel (THE ARMORY was cut too).
- **NETWORK STATUS** is on the Start menu, as Reach's was. Matches: THIS PC. Connection needed: NONE. Your party: from MCC's own list. **SERVICE RECORD SITE** (where Reach had Halo Waypoint) is now a line of text, as Reach's entry was.
- **Validation:** preview screens 34-38 were checked by eye with this PC's real files and settings. `build.bat pg33` builds `botcore_pg33.dll`. Untested in game.

### Sword Base: bots can reach the energy sword, 2026-11-19

The owner's F9 reports on Sword Base (`reach_20_sword_slayer_20261119-203930`: "Bots congregate on swordbase here and get stuck", "I defy evil wouldnt shoot me at all. barely moved"), then: "the lidar doesnt allow the bots to get to the sword".

- **Found:** the energy sword's alcove floor (z 24.0) sits under a surface at 26.0, and the level data kept only that upper surface. The row at y 28.0-28.25, the way in, had no floor either. The bots' path ended 2.35 u from the sword at (-123.2, 26.15, 24.13). Two Demons and a Blind stood there 40-52% of the match, held by the power-weapon run (`Bot.power_commit`), and nobody got within 1 u (345 s within 4.5 u). In the variant the alcove was an island no path entered; the base map reached it only because spawn points sit inside it.
- `maps/reach_20_sword_slayer/moves_review.json` (new): an approved floor review (`maps._build` reviewed floor, read for the base map and its variants). It holds the owner's own LiDAR walk in the alcove (30 cells, `variants/v04abd98b/lidar.json` kind 1), plus 6 cells at the way in where players stood in that match ((-123.25, 28.25, 24.0) 167 times). The owner confirmed the floor is real.
- Also checked: the window and fence labels never block walking; Sword Base's walkway glass is real (the owner), so a bot that sees a man through it holds fire as it should. Sword Base is still missing other floor: 37 of 310 spawn spots (12%, other Reach maps 0-1%), including part of Red's spawn room (x -120 to -117, y 47-51) and the lower level (z 22). Not changed.
- Validation: both builds (the base map and variant `v04abd98b`) now walk the nav to within 0.54 u of the sword from the old path end, the atrium (-128, 33) and Red's spawn (-120, 50). The sword item reads `reachable`. 986 tests OK; `live_bots` imports. **Untested in a match.**

### Fix: bots froze in every match after the first kill, 2026-11-19

The owner: "The bots have frozen atleast two games in a row now in matchmaking". `logs/brain.txt` (Aftship, TU TEAM SLAYER DMR, 20261119-203501) shows the cause: `8.7s tick failed (TypeError: slice indices must be integers ...)` at `for c in comms[said:]`, then "game gone, brain stopping".

- **Cause:** Map memory (3cf3035) stored each kill's `kill_record.read(...)` result in `said`. That name was already the director's count of callouts spoken, so after the first kill the count held a tuple, the callout slice threw, and the brain stopped with the bots standing.
- **Fix (`tools/live_bots.py`):** the kill record's variable is now `rec`. Nothing else changes.
- **Checks:** the file parses and imports, and `unittest discover` over `tools` passes 986 tests. Not yet seen in a match. It applies from the next match, since botcore starts a fresh brain for each one.

### Proving Grounds: the player's own Spartan on the cards, and Reach's Armory (phase 3), 2026-11-19

The owner: "Do the in game cards first, then start the Armory. all one phase". His Armory design: "everything on MCC is actually already unlocked, but we make it to where you can't equip it until you purchase it through our menu ... when we go to equip an item that we have not purchased or locked, it just doesn't do anything. So it's not changing the options inside the MCC menu."

- **The cards (`native/bots_panel.cpp` `person_figure`, now given the name):** the player's own Spartan instead of Reach's default one: their colours, body and visor from `my_look_reach.txt`, wearing what the Armory has equipped. Anyone else on a card is still the default Spartan. Shown wherever a person's figure is drawn: the player card, the credits after a game, the Start menu's Armory picture.
- **Prices (`tools/reach_prices.py` -> `maps/_looks/reach_prices.json`):**
  - Read from the Halo: Reach Editing Kit's own `ui/supply_depot.cookie_purchase_globals`, taken from `HREK.7z` with 7-Zip. A reader for the kit's tag files works from the tag's own layout. For each item: its credit cost, its rank gate (grade and sub grade), the items it needs first, and its default and auto-buy flags.
  - Each family lines up one to one with the Armory catalog botcore logged (`reach_armory.json` "writes"), so each item carries its exact configuration bytes.
  - 189 items: 142 at Reach's own price, 47 at ours. Ours are the unlock-only originals (Military Police, CQB, Recon / UA/HUL(3), the [W] chests, Legendary and Eternal, the Officer Elite) and MCC's additions: 26 helmets in five sets, the [R] chests, Condemned, UA/Base Security, UA/Multi-Threat and the Vacuum Flask. They are in one table at the top of the tool.
  - Examples: Mark V (internally John-117's) 130,000 cR at Major; Haunted 1 cR at grade 21 once every other helmet's last variant is owned.
- **`tools/service_record.py` `write_game_armory`** (with every site build) writes `logs/service_record/armory.txt` with:
  - the person's rank step and credits earned;
  - every item with its gate as a step of the one rank table (`armory_gate_step`: grade 7 is Major);
  - the customization table's pieces, so the game can dress the figure.
  The game works out no rank of its own.
- **`native/armory.cpp` / `armory.h`** (new, in both builds):
  - Loads that file. Owned means a default item, bought, or auto-bought once its rank and its needs are met.
  - Buying appends to `native\bin\service_record\armory_ledger.txt`. The credits to spend are the credits earned minus that ledger; the rank stays on the credits earned, as in Reach.
  - Equipping writes `armory_equipped.txt` (a slot not set wears its free default). Equipping a locked or unbought item does nothing.
  - Lays the equipped and tried-on bytes over the player's look, and works out the model's pieces as `brain/armory.py` does.
- **`native/proving_grounds_reach.inc`, phase 3 pages** (the Start menu's THE ARMORY is now on):
  - **ARMORY:** the ten slots (Emblem and Colours dim: Reach never sold them, MCC's stay). The Spartan is large; the slot's equipped item and how many are owned are listed. ELITE ARMOR shows the Elite.
  - **A slot's page:** each item EQUIPPED (gold), PURCHASED, or its price, with a padlock when the rank or a needed item is missing and the price in red when short of credits. The list shows 15 rows at a time, with arrows. The focused item is tried on the Spartan, and RS (or Q / E) turns it.
  - **The description box:** where the price comes from, PREREQUISITES with the rank and the needed item marked MET / NOT MET, the COST and the credits on hand.
  - **HELMET** lists the helmets (n of m variants owned); A opens one's own page, the base and its variants.
  - **Buying:** A asks first: PURCHASE AND EQUIP or CANCEL, with the cost and what is left. A locked item's A plays the error sound and changes nothing.
  - The player's band shows the credits to spend and the credits earned.
- **`native/reach.cpp` `hr_wear_armory`:**
  - Each tick of a Halo: Reach match, the equipped pieces' bytes are laid over player 0's configuration (game globals +0x2D8) and over the copies of it in the player's own record. The copies are found once a match by name and service tag. botcore's log notes them.
  - `native\bin\reach_menus.ini` `[armory] wear=0` turns this off.
- **Validation:**
  - `tools/test_service_record.py` +2 (40 pass): `armory.txt`, the gate steps, the price list (each item sets its slot's own byte, one free default a slot, needs listed, all 90 helmets). The whole suite, 986 tests, passes.
  - A scratch program against copies of the files: a rank-locked item and a variant before its base are refused, a second purchase is refused, the purchase lands in the ledger, CQC (auto-bought at grade 1) equips free, and the wear bytes carry the bought chest.
  - Preview screens 30-33 (the Armory, the helmets, Mark V's variants, the purchase dialog) were checked by eye. The figure tries Mark V on (the Halo CE-style helmet).
  - `build.bat pg32` builds `botcore_pg32.dll`.
- **Live, the same day (`botcore_pg32.log`):** the owner bought Tactical/Recon (1,500 cR, in the ledger) and equipped the CQC helmet. botcore logged "24 byte(s) laid over the player's configuration; 2 copies in the player's record (+0xB0 +0x130)", and the saved look read helmet 3 and chest 6 instead of his MCC armor. The owner: "My spartan was wearing the armor I set before and after death". So it is worn from the first spawn and after a respawn.
- **Untested in game:**
  - Other machines still see MCC's choice.
  - With nothing bought, every slot is on its free default (Mark V [B] and so on). The owner's own MCC look (Drengr Valdemar and the rest) is not worn in matches until it is bought here, or `wear=0` is set.
  - The site does not show the credits to spend yet. Armor effects are not drawn on the figure.

### Service Record: the player's own Reach armor, read from the game, 2026-11-19

The owner: "what the service record shows as my armor, is not correct. I do no wear what it shows on my profile. All the other bots are correct but not mine."

- **Found:** the site gave every listed name without a bot profile the look a bot of that name would roll (`all_looks` -> `brain/looks.py armory_view`), the person included: the owner's helmet 53, chest 4 and colours were made up from the name. Nothing read the person's real armor.
- **`native/reach.cpp` `hr_save_my_look`:** when the bots are added to a match, player 0's configuration as they joined (`globals + 0x2D8`, the one every bot starts from) is saved to `native\bin\service_record\my_look_reach.txt` whenever it changes: the name (+0x20), service tag (+0x64) and the 0xA0 bytes.
- **`brain/looks.py` `armory_from_config`:** a look from those bytes, each field of `maps/_looks/reach.json` read at its own byte (the colours at 0x49 / 0x4A, the body at 0x4C, each armor slot's), as a bot's look writes it, and the model pieces they put on (`brain/armory.py`), as the Spartan and as an Elite.
- **`tools/service_record.py` `load_my_look`, `all_looks`:** the person named in that file gets that look on the site instead of the made-up one; everyone else as before.
- **Validation:** `tools/test_service_record.py` +1 (38 pass); the whole suite, 986 tests, passes. `build.bat pg31` builds `botcore_pg31.dll`. **Live, the same day:** after a match the owner's profile on the site showed his own armor ("My armor updated on the site so thats good"). Gender 1 read as female is still unconfirmed. The game's own player card still draws Reach's default Spartan for a person.

### Service Record: Denied and Mission First get their art, 2026-11-19

The owner sent a tier sheet for each: "Here is denied and mission first". Each sheet is six emblems in a row, Iron to Max, already cut out: see-through around them (white under the clear part), with no title and no names.

- **`tools/service_record_art.py` `emblems`:** a sheet that is see-through over a fifth of it or more is cut by its own transparency, each emblem's pixels kept as they are. The earlier sheets (MVP, Game Changer, Positive Thinking, Loyal Soldier) were on black or night blue and are cut as before, by lifting the emblem off that background. That way would have thrown away these sheets' dark edges.
- Cut for real into this PC's art store (`native/bin/service_record/art/commendations`, not in git): `tiers/<tier>/denied_<tier>.png` and `mission_first_<tier>.png`, the grey "not started" banners `denied.png` and `mission_first.png` (from Victor's, as the others), and the sheets kept under `sheets/`.
- Validation:
  - `tools/test_service_record_art.py` +1 (12): a cut-out sheet with white under its clear part gives six emblems on 448 squares, clear around them and inside the ring, each one's colour kept, its dark rim kept dark.
  - Both rows were checked by eye on the banners' blue against the sheets, along with both grey banners.
  - The real site rebuilt with all twelve tier banners. A bot's Commendations page in a browser shows both cards with their Iron emblems in the Iron frame, no console errors.
  - `logs/service_record/commendations.txt` lists all six tier banners of each for the game's Commendations page.
- **Untested:** the game's own Commendations page drawing them. The tiers above Iron were only seen in the cut rows: no bot has reached Bronze in either yet.

### Proving Grounds: Halo: Reach's menus, phase 2 (the Start menu, Service Record, Career, party details), 2026-11-19

The owner sent ten more frames of Reach's menus: MY PARTY DETAILS, MENU, SERVICE RECORD, CAREER (on Campaign, Arena, Matchmaking and Firefight), CAMPAIGN and FIREFIGHT by difficulty, and COMMENDATIONS.

- **`tools/service_record.py` `write_game_career`** (with every site build): `logs/service_record/career.txt`, each listed person's games, wins, kills, deaths, assists and seconds for Matchmaking (every match on the Service Record: it counts only Proving Grounds' own, `matchmaking.txt`), Arena (those of the ARENA playlist, The Arena) and Big Team Battle. `tools/test_service_record.py` +1 (37 pass). The real site: 19 games, 11 won, 360 kills, 13 in Arena, 6 in Big Team Battle.
- **`native/proving_grounds_reach.inc`**, new pages:
  - **MENU** (the Menu prompt, Start or M, now opens it; Exit or B goes back): THE ARMORY (its pieces listed dim, the player's Spartan in the picture; dim: the player's Spartan is MCC's Customization, the bots' looks the BOTS panel's), PLAYER, FILE BROWSER, CONTROLLER, AUDIO VIDEO (dim: MCC's own), CHALLENGES with Reach's star while there are live ones (the Challenges page), NETWORK STATUS (dim: offline), SERVICE RECORD SITE (where Reach had Halo Waypoint: the site in the browser; Microsoft's name is not used for it) and PROVING GROUNDS (its own options page as before).
  - **SERVICE RECORD** (PLAYER): CAREER..., COMMENDATIONS... (the Commendations page), LEGACY (not here yet); the player's card (emblem, name, rank, the rank's insignia large), Matchmaking Games Won and MP Kills, the campaign's two rows "Not recorded", and Top Commendations: the three furthest along (highest tier, then nearest the next), their banners and bars.
  - **CAREER**: CAMPAIGN... and FIREFIGHT... (Reach's rows, "Not recorded", and their NORMAL / HEROIC / LEGENDARY pages the same), ARENA (Games Won, Kills, Deaths, Assists, % of Matchmaking Games Played in Arena), MATCHMAKING (the same, Time Played, Top Commendations), CUSTOM GAMES (they are not on the Service Record, it says).
  - Each with Reach's upright breadcrumb (cut to fit above the player's band), the player's band and Exit.
- **`native/proving_grounds.cpp`:** MY PARTY DETAILS (the roster's header panel) now lists Reach's "Matchmaking Social Preferences" under the party: the Psych Profile's four, in Reach's title case. The new pages' states; preview screens 23-27.
- **Later the same day,** the owner, with Reach's Psych Profile and its beta's Start menu (DAILY CHALLENGES): "I would like the proving grounds options (Simulate Matches 1 round, 2 round, etc) to be on the pysch screen. I would like the option (Challenges to look like this) And I would like the commendations tab to also be between Psych profile and start mathcmaking options."
  - **Psych Profile:** SIMULATE MATCHES (Left / Right the rounds, 1 to 20; A plays them; PLAYING... and DONE: n MATCHES as before) and INVITE PLAYER (the invite list over the page) under the four preferences; the description moved down, the map unchanged.
  - **Start menu, CHALLENGES:** the right side lists the live challenges as Reach's did: DAILY, then WEEKLY, each its icon in a ring, its name, what to do, its credits, a thin bar and [n/need] (DONE and the credits in gold when finished). A opens the full Challenges page.
  - **Matchmaking:** COMMENDATIONS (its progress %) between PSYCH PROFILE and START MATCHMAKING, opening the Commendations page; back from it lands on that row (and on the Service Record's, from there).
  - The Start menu's PROVING GROUNDS entry is gone: each of its options now has its place in Reach's pages (the game size is the playlist, PLAY is START MATCHMAKING).
- **Validation:** all 29 preview screens render; the new ones and MY PARTY DETAILS checked by eye against the owner's frames (a crumb into the band and the Exit prompt past it fixed). `build.bat pg30` builds `botcore_pg30.dll`. **Untested in game.**

### Proving Grounds: the Psych Profile's world map, with the Service Record's home states as heat, 2026-11-19

The owner, after trying the Reach menus ("It works so far"): "On the pysch profile page id like the same world map. and then a static heat map of the service websites player locations". The Service Record's only locations are its home states (states.json: each player's US state, picked from the name by population or set by hand in edit mode).

- **`native/world_map.h`** (new, 83 KB, made by **`tools/world_map.py`**): the world's land (127 outer rings) and the 50 US states and DC (outlines and Natural Earth's label point) at a tenth of a degree, from Natural Earth's 1:110m `ne_110m_land` and `ne_110m_admin_1_states_provinces` GeoJSON (public domain; downloaded on the owner's OK from github.com/nvkelso/natural-earth-vector, not kept in the repository). `NOTICE.md` credits it.
- **`tools/service_record.py` `write_game_locations`**, run with every site build: `logs/service_record/locations.txt`, each state's count of listed players (bots and people) and each person's state.
- **`native/proving_grounds_reach.inc` `rm_world_heat`:** the Psych Profile's panel is now the world, filled dark grey with its coasts, the states' borders faint, Reach's lines of latitude (80 to 40) over it, and the heat as Reach's own map had it: fine specks every 0.8 degrees inside the states, each coloured by a muted colormap (ember red, orange, soft amber; never full brightness) of the players around it, every state's players spread from its label point (a Gaussian, 2.2 degrees). Worked out once when `locations.txt` changes (`heat_build`). The player's own state has a thin, quiet ring; a line under the map says how many players, the most-lived-in state and its count. The random dots it had are gone.
  - First drawn as glowing circles per state; the owner: "more of a lowkey vibrance to the orange. Make it more of a colormap instead of a popout circle. similar to the og".
- **Validation:** `tools/test_service_record.py` +1 (36 pass): every state of states.json in order with the right counts, the person's state, every code also in `world_map.h`, the page reading `locations.txt`. The site rebuilt for real: 754 players, the most in CA (77), the owner's NY. The preview's Psych Profile drawn and checked by eye (the land, the speck colormap over the US, NY ringed). `build.bat pg27` builds `botcore_pg27.dll`. **Untested in game.**

### Proving Grounds: Halo: Reach's own menus, phase 1 (title, main menu, matchmaking), 2026-11-19

The owner sent seven frames of Halo: Reach's menus (its title screen, MAIN MENU, MATCHMAKING, PLAYLIST twice, SEARCH RESTRICTIONS, PSYCH PROFILE): "Starting here. This is the main menu. And the matchmaking menus all phase 1".

- **`native/proving_grounds_reach.inc`** (new, included once by `proving_grounds.cpp` after `menu_screen`): Proving Grounds' menu stage (`S_MENU`) now shows Reach's pages, `g_rpage`:
  - **Title** (the first open of a session; the PPG Launcher's route lands here): PROJECT / PROVING GROUNDS spaced wide over the painting with a band of light under it, START SOLO CAMPAIGN (not in Proving Grounds yet) and MAIN MENU, the Menu prompt, the mod's version at the bottom right.
  - **Main menu:** our winged mark, MAIN MENU, "This party is offline: you and the bots you invite.", CAMPAIGN, MATCHMAKING, FIREFIGHT, CUSTOM GAME, FORGE, THEATER with a line on each, MY PARTY at the right ("In Main Menu Lobby", the roster as before). MATCHMAKING opens matchmaking; CUSTOM GAME closes Proving Grounds onto MCC's own Halo: Reach custom game lobby; the other four are dim and say they are not in Proving Grounds yet. Later opens in the session start here.
  - **Matchmaking:** the playlist's maps in a banner with the pool's count and the playlist's size, MAIN MENU upright at the left (Reach's breadcrumb), "Ready", PLAYLIST (its name), SEARCH RESTRICTIONS (NONE (FASTEST) or the ticked ones), PSYCH PROFILE, START MATCHMAKING (the search, the vote and the game as before), MY PARTY ("In Matchmaking Lobby"). Back from the search or the vote comes here.
  - **Playlist:** STANDARD, EVOLVED, ANNIVERSARY, COMMUNITY, COOPERATIVE, then the category's playlists (Right or A in, Left or B out), the picked one's picture with its name cut at the edge, our words for it, Team Size, Max Party Size, the pool and the vote's time, and the player's band (emblem, rank insignia, name, rank, credits, next rank, from the Service Record). Reach's Standard and Evolved lists are shown; Proving Grounds plays BIG TEAM BATTLE (8v8) and THE ARENA (4v4), the rest are dim with "Not in Proving Grounds yet". Picking one sets the game size as GAME SIZE did.
  - **Search Restrictions** (GOOD CONNECTION, LANGUAGE, SKILL: ticks) and **Psych Profile** (CHATTINESS, MOTIVATION, TEAMWORK, TONE: No preference and two choices each, Left / Right or A) are saved in `native\bin\reach_menus.ini`. The search does not use them yet, and both pages say so.
  - **Proving Grounds' own menu** (invite, challenges, commendations, simulate matches, game size) is still there, from the Menu prompt (the pad's Start, M, or a click) on the title, the main menu and matchmaking. B goes back one page; from the title it closes Proving Grounds.
- Our own drawing and words: no Bungie or 343 art, logos or icons (the header marks, the caution sign and the diamond lattice are drawn shapes). The title, main menu and matchmaking use this PC's paintings (`native\bin\pg_backgrounds\title`, `main_menu`, `matchmaking_lobby`, else the `menu` and `matchmaking` ones); the sub-pages draw a dark steel-blue ground with a faint lattice.
- `proving_grounds.cpp`: the page state and its hooks (`pg_open`, `to_menu`, `pg_back`, the frame's ground, the S_MENU case, where the roster can open), the preview's screens 16-22 (`pg_preview_stage` 15-21). `pg_preview.cpp`: the seven new screens, and `PG_ONLY=<n>` to draw one.
- **Validation:** `build_pg_preview.bat` and `build.bat pg25` (`botcore_pg25.dll`) build without new warnings; all 22 preview screens render, the seven new ones checked by eye against the owner's frames (the playlist name overflow and a hard edge in the sub-pages' ground were fixed after the first look); the older screens unchanged (Proving Grounds' own menu draws as before). **Untested in game:** the controller on every page, the roster on the main menu and matchmaking, the title on the launcher's route, CUSTOM GAME closing onto MCC's lobby.

### Service Record: Mission First and Denied, two commendations for objective play, 2026-11-19

The owner, from a list of commendations the site lacked: "Do mission first, and Denied."

- **Why:** nothing counted objective play. Reach had no multiplayer objective commendations, and Game Changer only rewards the top Score of an objective game.
- **What MCC's Reach reports carry** (the store's 28 objective games up to Nov 19: 9 CTF, 6 Assault, 6 King of the Hill, 4 Territories, 3 Stockpile):
  - Five objective medals only: Flag Captured, Bomb Planted, Flag Carrier Kill, Bomb Carrier Kill and Flag Kill.
  - A flag brought home in Stockpile is a point of the player's Score there; no medal says it.
  - Territories record nothing: Score 0 for all 40 player rows, no medal. There is no medal for a flag return, a bomb defuse or defense either.
- **Mission First** (`tools/service_record_site/commendations.json`, set "pg"): flags captured, bombs planted and Headhunter's 10-skull banks by MCC's medals, plus the flags brought home in Stockpile.
- **Denied:** flag carrier kills and bomb carrier kills by MCC's medals.
- Both are narrower than the sketch the owner chose from, which also named territories taken, flag returns, defuses and defense: the reports do not say those. `commendations.json` `objective_note` records what is and is not counted.
- Tiers for both: 5, 25, 100, 500, 1,500, 3,000, with First Blood's credits (150, 400, 1,000, 2,000, 2,000).
- `tools/service_record.py`: `stockpile_flags` (new) reads a Stockpile game's Score; a match's flags are summed as `deeds["stockpile"]`; `commendation_counts` adds `count.plus_deed` to a medal count.
- No art yet: both cards show the drawn placeholder until the owner sends a tier sheet for each (`service_record_art.py emblems <sheet> mission_first`, `denied`).
- Each Iron adds 150 cR to a bot's credits, and the Overall Commendation Progress is now out of 25 commendations, so it falls a little for everyone.
- Validation:
  - `tools/test_service_record.py` +1 (35): the medals and the Stockpile flags summed, a Score outside Stockpile adding nothing, None while MCC's medal list is unread, the tiers, and both counts through a build of a Stockpile and a CTF game. All 107 `tools/test_*.py` files pass.
  - The real site rebuilt: of 680 bots with a counted match, 341 have a count in one of the two; 34 are at Iron in Mission First and 49 in Denied; the highest counts are 15 and 13.
  - A bot's Commendations page in a browser: both cards in the Proving Grounds set, at Iron with their counts, no console errors.
- **Untested:** Skullamanjaro (the store has no Headhunter game) and Oddball (none either). The game's own Commendations page, which reads the site's table.

### Service Record: Medal Collector counts every medal, 2026-11-19

- The owner asked for Medal Collector to count total medals, not unique ones, with the tiers left to Claude.
- **`tools/service_record_site/commendations.json`:** Medal Collector now counts `{"stat": "medals"}`, the medal total from MCC's post-game reports (the card says "report"). Its text is now "Earn any medal."
  - New tiers: Iron 250, Bronze 1,000, Silver 5,000, Gold 20,000, Onyx 50,000, Max 100,000.
  - Credits per tier are unchanged.
- **Why these numbers:** a bot earns about 12 medals a game (median; 22 at the 90th percentile). At that rate Iron comes after about 20 games, Gold after about 1,600 and Max after about 8,000. That is close to Loyal Soldier's pace (25 to 8,000 games).
- The `distinct_medals` count in `tools/service_record.py` stays in place but is now unused.
- **Effect:** with today's data 77 bots reach Iron; the top bot has 758 medals.
  - Nobody had Silver (40 kinds); the most any bot had was 39.
  - Bots with 25 or more kinds had Bronze (200 + 500 cR). They now have Iron or nothing, so they lose 500 or 700 cR.
  - Bots with 10 to 24 kinds lose Iron's 200 cR unless they have 250 medals.
- **Validation:**
  - `test_service_record.py`: 34 tests pass. The Proving Grounds commendation test now checks the medal total, the new tiers and the "report" source.
  - Full suite: 986 tests pass.
  - The site was rebuilt and the new tiers were checked in `data.js`.

### Proving Grounds: the credits after a game as Reach's own sequence, 2026-11-19

The owner sent ten frames, in order, of Halo: Reach's screen after a game (a Reddit video). `native/proving_grounds.cpp` `credits_screen` now runs that sequence, with the same data as before (`last_match.txt`, the site's own lines and rank steps):

- **Look:**
  - Reach's dark slate over the postgame painting (kept faint) and its fine hex pattern, brightest in the middle.
  - The player's Spartan at the right (bots_panel's person figure), turning toward the camera on a promotion.
- **Sequence:**
  1. Each line in turn, 1 s each. Its name and "+n" counting up in the middle, a huge faint word behind ("TIME SPENT" for Game Completed, "TEAM PLAYER" for Assists, else the line's name), then into the list at the bottom left.
  2. CREDITS EARNED at the top, the list rising under it, and TOTAL counting up, with "TOTAL CREDITS" faint behind.
  3. The total flies to the player's band along the bottom: emblem, rank insignia, name, rank, credits counting up, and "Next: <rank> in n cR" or MAX RANK. The owner's level-up bar (Nov 17) is now a thin bar under the band, filling toward the next rank.
  4. On a promotion: the header turns to PROMOTED, the list dims, "<RANK> PROMOTED" appears faint behind, and the new insignia comes in large with its name and a gold ring.
- **Controls:**
  - A, Enter or a click skips to the end (Reach's Skip), then goes on.
  - B goes on.
  - It goes on by itself 6 s after the end.
- **Commendations page:** each bar is now the colour of the tier reached, grey before Iron. It was the next tier's colour. (The owner: "the color of the tier it's at currently".)
- **`native/pg_preview.cpp`:** the credits drawn three times (a line, the total, the promotion: screens 10, 13, 14). The friend's vote is now screen 15.
- **Validation:**
  - The preview renders every phase, checked by eye against the owner's frames.
  - `build.bat pg23` builds `botcore_pg23.dll`.
  - **Untested in game:** the timing, the figure's turn and the sounds.
- **Later the same day:**
  - The owner asked for the new rank's insignia "a tad slower", since it felt too instant. Now:
    - it waits 0.35 s after PROMOTED;
    - it fades in over 0.6 s while settling from larger over 0.8 s;
    - its name and the gold ring follow it;
    - the sequence ends 0.6 s later (`botcore_pg24.dll`).
  - `pg_preview video <out.mp4> [screen] [seconds]` records a screen as it plays: 30 fps H.264 through Media Foundation, no sound (`build_pg_preview.bat` links mfplat, mfreadwrite and mfuuid). `logs/previews/pg_levelup.mp4` is the credits sequence.

### Proving Grounds: Reach's Service Record Commendations page, from the site, 2026-11-19

The owner sent a picture of Halo: Reach's Service Record Commendations screen: "Let's add it to ours with its own menu option, and keep it connected to the service record site."

- `tools/service_record.py` `write_game_commendations`, run with every site build beside `ranks.txt` and `challenges.txt`, writes `logs/service_record/commendations.txt`. It holds:
  - the site's tiers and table, with each commendation's Reach banner and its tier banners;
  - for each listed person: their counts with the tier reached as the site counts it (`commendation_tier`, the same as `app.js` commState), their Overall Commendation Progress, credits, rank and next rank.
- `native/proving_grounds.cpp`: a COMMENDATIONS row on the menu, between CHALLENGES and SIMULATE MATCHES, showing the progress %. The rows are now 44 tall and 6 apart, and the games and category tiles a little smaller, so six rows fit.
- The page is laid out like Reach's:
  - **Header:** "SERVICE RECORD".
  - **Lists, at the left:** Top Commendations (all), Multiplayer, Proving Grounds (the site's two sets).
  - **Commendation list, at the right:** six rows at a time, sorted as the site sorts them (tier, then progress, then name). Each row has:
    - the banner of the tier reached (the site's tier banner), else Reach's own;
    - the tier name in the site's tier colour;
    - a bar toward the next tier in that tier's colour, with n/need.
  - **Player band, at the bottom:** emblem, rank insignia, name, rank, credits, and "Next: <rank> in n cR".
  - **Footer:** the focused commendation's description and "n of need for <tier> (+cR)", worded as on the site.
  - **Controls:** Up and Down (or the stick) move and scroll, with chevrons when more is above or below. Left and Right or LB and RB change list. Y or Tab opens the player's Commendations page on the site (`open_site_page`, shared with Challenges). B goes back to the menu's COMMENDATIONS row.
- `native/pg_preview.cpp`:
  - The page is preview screen 12 (the friend's vote is now 13).
  - The preview's link loopback now answers only on the friend's screen. A screen drawn after the credits used to follow its stale state, so `pg_11_challenges` had drawn the credits.
- **Validation:**
  - `tools/test_service_record.py` `test_game_reads_the_sites_commendations`. The file's own run passes (34 tests).
  - A real site build wrote 23 commendations with the owner's counts.
  - The preview draws the page with them, checked by eye.
  - `build.bat pg22` builds `botcore_pg22.dll`.
  - **Untested in game.**
- **Not done:** the owner's Reddit video of Reach's level-up screen could not be opened from here (Reddit refuses the fetch, and video can't be watched), so the credits screen is unchanged.

### Proving Grounds over Reach's own painted backgrounds, see-through as Reach's menus, 2026-11-19

The owner sent pictures of Halo: Reach's matchmaking, main menu and custom game lobby ("The background is more seemless and fluid ... I want the background to be like that") with upscales of three of Reach's menu backgrounds to use.

- `native/proving_grounds.cpp`:
  - **Backgrounds:**
    - One painting across the whole screen, bright: `menu` for Proving Grounds' own screens, `matchmaking` for Find Game, the vote and the next game, `postgame` for the credits after a game.
    - Each drifts slowly, 9-11% larger than the screen and moving about in that room, and a new screen's painting fades in over the last in 0.9 s (not when the screens were just put up).
    - Over it, Reach's treatment: a light dimming, darker on the left behind the menu and at the bottom under the prompts, a touch at the top and right.
    - The pictures are this PC's only, in `native\bin\pg_backgrounds\` (menu, matchmaking and postgame, `.png` or `.jpg`). That folder is git-ignored: Reach's art is never committed. Without a picture, a screen keeps the playlist's maps, faint, as before.
  - **See-through:**
    - Panels at alpha 176 (214 before); the menu's info panels lighter too.
    - A plain list row is nearly clear.
    - The focus is Reach's light band with a white line at its left, on the menu, the error screen's buttons and the vote's options. This replaces the solid grey bar and pointer from this morning.
    - Reach's thin line over the button prompts.
- `native\bin\pg_backgrounds\` (not committed): the owner's three pictures. menu.png is the Halo over Reach, matchmaking.png the Covenant over the glassing (swapped at the owner's word), postgame.png an Elite and a Spartan (1672x941 each).
- **Validation:**
  - The preview renders all 12 screens with the paintings (no fade there), checked by eye at 1920x1080.
  - `build.bat pg21` builds `botcore_pg21.dll`.
  - **Untested in game**, including how the drift and the fades feel live.

### Proving Grounds in Halo: Reach's look, livelier, and fully on the controller, 2026-11-19

The owner asked for the bot matchmaking screens to be "more vibrant and true to the original", then chose Reach's steel grey for every screen ("I want the vibe of reach as much as possible"; this replaces the Nov 17 MCC navy for the menu, search, vote, result and error screens), and "Make the menu also compatible with controller. Since we mostly use controllers." The player card's stats over the figure and the PARTY tag on bright nameplates were left for later at the owner's word.

- `native/proving_grounds.cpp`:
  - **Look:**
    - Reach's palette everywhere: grey see-through panels, lighter at the top; light grey text; a pale steel accent in place of MCC's blue.
    - A focused row is lit grey with a white edge. The menu's rows carry Reach's pointer toward the stats panel. The vote's focused option matches, and the invite buttons too.
  - **Background:** a grey wash in place of the navy one. The map art is about twice as strong: alpha 0.16 -> 0.30, tint near its own colours, the left and bottom darkening lighter. The menu card's map is at 0.85, up from 0.55.
  - **Find Game:**
    - Empty seats are faint outlines with a soft light passing down them, with "SEARCHING FOR PLAYERS..." on the first one only.
    - A bot that is found slides in from the right with a white flash, and a tick sounds as players arrive.
  - **Vote:**
    - Each option has a bar along its foot sized by its share of the votes: yours gold, the leader brighter.
    - The last five seconds of the clock are gold, swell on each second and tick.
  - **Credits:**
    - The promotion now reads "PROMOTED TO <RANK>", in gold that settles to its size, with a white flash along the bar.
    - The new insignia comes in large with a gold ring.
  - **Names:** the roster's header is "IN PROVING GROUNDS LOBBY" (menu) and "IN MATCHMAKING LOBBY" (search and vote), as when it is opened Reach's way. It was "MY GAME SESSION", "IN LOBBY n/m" and "SETTING UP MATCH...".
  - **Error:** its title is "GAME DIDN'T START" ("SOMETHING WENT WRONG" before).
  - **Controller:**
    - Pad prompts are drawn as Reach showed them: A green, B red, X blue, Y yellow discs, and bumper or trigger pills.
    - The left stick also moves left and right. RB (or the footer's new "Players" prompt) opens the roster, and LB closes it.
    - The invite list scrolls with the left stick and pages with LB and RB (Page Up and Page Down on the keys). It shows "1-12 of 752" and pad-aware help.
    - The error screen's two buttons also move with Left and Right.
- `native/overlay.cpp`: both triggers together (LT+RT) open Proving Grounds in Halo: Reach's custom game lobby, as both sticks open BOTS. The tile's prompt shows LT+RT on the pad; it showed nothing on the pad before.
- `native/pg_preview.cpp`: `PG_PAD=1` draws the pad's prompts.
- **Validation:**
  - `build_pg_preview.bat` renders all 12 screens, with the keys and with `PG_PAD=1`, checked by eye at 1920x1080.
  - `build.bat pg20` builds `botcore_pg20.dll`. It loads at the next MCC start.
  - **Untested in game:**
    - the pad in MCC itself;
    - whether LT+RT does anything of MCC's own in the Reach custom lobby before Proving Grounds takes the pad;
    - how the brighter art reads behind text on every map.

### Map memory: spawn spots follow a flip in this match, 2026-11-19

The owner: "Just to be aware some maps and modes spawns flip if they take it over." The history files respawns by team, so after a flip the spot a bot watched after a kill could be its own side's spawn.

- `Lore.add_spawn(..., now)`: `tools/live_bots.py` passes the live clock, so the match's own respawns are also kept in memory (the newest 200; a new match starts with none). They are not saved twice.
- `Lore.spawn_spots(mode, not_team, now)`:
  - The other teams' respawns of the last 75 s count 4 each over the history, so one recent respawn is a spot by itself and leads.
  - A spot the bot's own side came back within 8 u of in that time, with none of the others there, is left out: it is ours now.
  - Past 75 s it is the history again.
- `Bot.spawn_look` also leaves out a spot a living teammate stands within 10 u of (`SPAWN_MATE_R`), since the game will not spawn an enemy right beside a player of the other side.
- **Validation:** `tools/test_map_memory.py` 21 tests (2 new: a flip this match leads the history and falls back after 75 s; a teammate's spot not watched). Full suite: 986 tests OK; `live_bots` imports. **Untested in a match.**

### Map memory for Legendary and up: danger spots and lanes, enemy spawns, jumps that keep failing, 2026-11-19

The owner chose three things for bots to learn per layout over matches (danger map, spawns, movement facts), "only give it to legendary and up". New `brain/lore.py`: one file per layout, `maps/<layout>/lore.json` (this PC's own, git-ignored like `nav_learned.json`). It holds the matches filed, every credited kill's two places, every respawn (mode, place, team), and each jump's lands and shorts. `profiles.map_memory` = `fixed_high`: Legendary, Mythic, Blind, Tactician and Demon. Scaling and Heroic down are unchanged. `MAP_MEMORY` False turns it all off.

- **Danger spots**, when nobody is known: `Bot.danger_look` looks first at the spots men shot from when people died within 6 u of where the bot is (a 2 u cell with 3+ such kills). It looks 0.8 s, then at the next spot, and leaves a spot it checked for 8 s. A spot must be within 60 u and in sight; when walking, within the 50° walking cone. In `radar_threat` (Demon and Mythic), a dot within 6 u of such a spot with a line to the bot has that spot watched instead of his corner, unless the corner is 0.5 s sooner.
- **Danger lanes**: `Terrain.nav(avoid=...)` goes round the 4 u cells where the most people died (8+ deaths and 2% of all, at most 10, 2.5 u disks). It does this only when the way round is at most 1.25× the plain way plus 6 u. Starting inside a lane, or with the goal in one, it takes the plain way. `_hazard_edges` now keeps its edges per hazard set, since the lanes are the same on every call.
- **Danger trust**: spots and lanes are used only once 3 matches with recorded kills are filed for the layout. Kills are recorded in Reach only, since Nov 15. **No layout has 3 yet** (2 at most), so these switch on by themselves after the next recorded Reach matches on a layout.
- **Spawns**: after the man it was fighting goes down (`kill_check`), for 6 s `Bot.spawn_look` watches the spot in sight within 35 u where the other teams respawn most in this mode. When walking, that spot must be within the walking cone. Not done: keeping clear of spawns behind it.
- **Jumps**: `judge_jump` and `judge_route` file each outcome. A take-off short 3+ times, and twice as often as made (`Lore.jump_bad`), is banned for that bot by `jump_learned_bad` when a walking way exists, just as two shorts of its own would ban it (`jump_fails`, 60 s). Without a walking way it is still tried.
- **Learning**: `tools/live_bots.py` files the live match's kills (as `kill_record.read` counts them) and respawns (the place 0.25 s after coming back). It saves the file with `save_learned` once a minute and at the end. `tools/lore_seed.py` files old recordings by stamp, once each, and can be run again. Forge recordings from before Nov 18 name no layout, so they are skipped. It filed 45 recordings across 24 layouts: 907 kills from 11 Reach matches, and 5,704 respawns.
- **Validation**: `tools/test_map_memory.py` (19). It covers trust, spots, lanes, the spawn team filter, the jump rule, the save round trip, the tier gate, the danger and spawn looks, the radar spot, jump bans and filing, and `nav` avoid on Boneyard (round a lane within the limit; the plain way with the goal in one). Full suite: 984 tests OK; `live_bots` imports. **Untested in a match.**

### Quicker reactions, rougher aim: Easy, Normal, Heroic (and Legendary, Tactician quicker), 2026-11-19

The owner: "A bad player still has a pretty fast reaction time of 100-135ms. But some are still bad and go 2-25 in game. I dont like shooting bots that dont shoot back like a bullet sponge. SO lets make them Faster but counter weight it with bad accuracy". Then he chose Legendary quicker too so the ladder stays in order, the clearly worse aim, and "Make tactician just faster and dont touch its accuracy".

- `brain/profiles.py` `REACTION_S`: median reaction (each sighting still varies log-normally, about ±25%) Easy 220 -> 135 ms, Normal 194 -> 125, Heroic 172 -> 115, Legendary 154 -> 100. Demon (0) unchanged.
- `ROUGH`: Easy, Normal and Heroic aim worse. Aim error ×1.8 / ×1.6 / ×1.5 (0.009 / 0.009 / 0.0068 -> 0.0162 / 0.0144 / 0.0102 rad), so about 30% / 33% / 46% of first shots land on a body at 20 u instead of about 51% / 51% / 65%. Aim still tightens while a bot stays on a man. Flick overshoot goes from 30% to 50% / 45% / 40%. Legendary's aim is unchanged; only its reaction moved.
- Tactician: reaction 171 -> 108 ms (`TACTICIAN_REACTION`, halfway between the new Heroic and Legendary). Its accuracy is unchanged: its hands still come from Heroic's hands before `ROUGH` (`TACTICIAN_HEROIC`).
- Blind and Mythic are unchanged: their Legendary end keeps the former 154 ms (`LEGENDARY_BASE_REACTION`). A slow-rolled Blind now reacts slower than a Legendary.
- Scaling is unchanged (it draws from `HANDS`, not the tier rows).
- Validation: `tools/test_reaction_speed.py` (new reaction times, the rougher aim, Blind and Mythic unchanged), `test_tactician_difficulty.py`, `test_mythic_difficulty.py` and `test_difficulty_separation.py` (the upstream Legendary fingerprint still matches with the stock reaction put back). Full suite: 965 tests OK; `live_bots` imports. **Untested in a match**: whether low tiers now shoot back without becoming too deadly is the owner's test.

### Bot simulation: one game a round, and your match's bots sit its round out, 2026-11-19

The owner asked how bots had 30-48 games when he had 19, and why the bots he partied with seemed to double; he chose both fixes. 20 rounds had stored 464 matches: grinders' paces ran up to about 4 games a round (iTzYaBoiClutch 3.9, 48 games, all simulated), four matches at once inside one of his; and the round alongside his match never looked at who played it (his last match: 6 of its 15 bots also played that round, Slayer117 four times).

- `tools/bot_sim.py` `play_round`: a bot plays one game a round at most (its Poisson draw capped at 1: its pace is now its chance of a game). New `sit_out`: the bots of the match a round goes alongside play none of it (names matched without case); a queued one keeps its place for the next round. `bots_in` reads those names from the ledger (bot_career adds the match before `--after` runs); `run` passes them for `--after` rounds only (button rounds have no match of yours). `--stats` counts seats with the cap.
- Effect: about 167 seats a round (14 Arena and 4 Big Team Battle lobbies) instead of about 250; a grinder at its median pace (0.91) plays about 60% of rounds, the fastest nearly every round. Games already played are unchanged.
- Validation: `tools/test_bot_sim.py` `OneGameARound` (pace 3 for everyone: no bot twice in a round; your match's bots and two queued ones sit out, the queued keep their place; `bots_in`). 14 simulation tests and the full suite (964) pass. Not yet seen after a real match: the next round alongside one of the owner's matches is the first.

### Demon and Mythic Gauss Warthog gunners lock on too, 2026-11-18

The owner: "DO the same for the gauss hog. for those same difficulties".

- `brain/bot.py`: the lock above (`Aim.lock`) now covers the Gauss Warthog's gun as well as the chaingun. `Bot.chaingun_lock` became `Bot.hog_gun_lock`, with `HOG_LOCK_GUNS` the chaingun and the Gauss as `vehicles.gunner_gun` names them ("assault_rifle", "sniper"), so it is led by the Gauss round's speed. It applies to Reach's Gauss (the Warthog's body with the gauss on it) and Halo 3's own kind; the Rocket Warthog is still left out. Demon and Mythic only.
- Live, no mount is read for the Gauss (`turret_origin` is the chaingun's only, and `GUN_HEIGHT` has no Gauss), so it aims from the gunner's eye as before. The lock is exact from there; how far the Gauss's real muzzle sits from that is not measured.
- Validation: `tools/test_chaingun_lock.py` (now 4: the Gauss for Demon and Mythic, both kinds, dead on from 2 rad away, led, firing; not the Rocket Warthog, nor Legendary on the Gauss). The full suite passes except one Wheelman check of `native/bots_panel.h`, which another session is editing now. **Untested in a match.**

### Demon and Mythic Warthog chaingunners lock on, 2026-11-18

The owner: "I would like Mythic and Demon chain gunners to have aimbot with the warthog gunner seat".

- `brain/bot.py` `Bot.chaingun_lock`, `Aim.lock`: a Demon or a Mythic in a Warthog's chaingun seat aims dead on the man's chest every tick. It aims from the gun's mount (`turret_origin`), or in Halo 4 at the real point on him, led by the round's flight and the 0.05 s read delay. There is no aim error, tremor, turn limit or flick, and it fires whenever the sent aim is on him. The seat must have the Warthog's chaingun (`vehicles.gunner_gun` "assault_rifle"), so not the Gauss or Rocket Warthog; this applies in every game. Who it shoots, the clear-line check and the Reach chaingun's heat are unchanged; the spin-up on a man just out of sight is unchanged.
- Note: this is exact aim at the point the bots compute. It does not explain or change the 606-611 s misses above, which were already on that point from the calibrated mount.
- Validation: `tools/test_chaingun_lock.py` (new, 3: Demon and Mythic dead on at once from 2 rad away, led, firing; Legendary still turns onto him; not the Gauss or Rocket Warthog). With only this change on HEAD all of those, `test_warthog_spin`, `test_h4_vehicle_aim` and the Demon / Mythic rule tests pass. In the shared tree 4 Demon / Mythic rule tests fail from another session's uncommitted `demon_rules` change. **Untested in a match.**

### Mythic plays by Demon's rules, 2026-11-18

The owner: "Give mythic the same ruleset as demons. such as the vehicle bans fight commit, pickups and regen reads".

- `brain/profiles.py` `demon_rules` (new): Demon or Mythic. Each Demon-only rule check across `brain/bot.py`, `brain/director.py` and `brain/equipment.py` now uses it (37 sites). Rules covered: the Warthog/Mongoose/Ghost wheel ban and its director orders, never a Wheelman (`mythic_profile` makes one a Flanker, `driver_priority` None), standing its ground, sidearm cover, mending and recharging to full, no new fight while hurt, breaking from a second watcher, the radar threat, dot glance and open dots, regen reads (`learn_regen`), the anticipated guess, the hunt's held look, the blade draw range, target choice, waiting on a man out of sight, on-the-way fights, playing the objective, the gun fetch commit, the corner chase, the power-weapon commit, the pre-nade's predicted path, cover from threats, no thruster in a gunfight, the Team Slayer anchor and Demon pairs, Halo 4's rules (`h4_demon`: Boltshot swap, melee range, power grab) and the fight odds and team play in every game (`team_demon`).
- **Kept Demon-only (aim and hands):** Reach direct fire, the precision and Halo 4 head snaps, unerring lead, the fixed decision timing. Mythic keeps its halfway hands and Legendary's protected head/turret precision (`precision_profile`). Its own odds pace stays 0.9 (`odds.own_acc`), now in Halo 4 as well (`own_pace`, the posted sightings pace).
- Validation: `tools/test_demon_objective.py`, `test_demon_radar.py`, `test_reach_team_demon.py` and `test_wheelman.py` now expect Mythic with Demon's rules. Full suite: 961 tests OK; `brain.bot`, `brain.director` and `brain.equipment` import. **Untested in a match.**
- Follow-up, the same evening (the owner: yes to the panel and the site): **no Wheelman for a Mythic in the BOTS panel or on the site either.** `native/bots_panel.h` `hb_style_fits` refuses Demon and Mythic Wheelmen (a bot's style, saved lines, the roster fill and the style picker turn it to Any), and Quick Start's style list greys Wheelman out for all Mythic as for all Demon. `tools/service_record.py` `NO_WHEELMAN`: a site difficulty change to Mythic saves a Wheelman as Any, as for Demon. `native\build.bat pg19` built `botcore_pg19.dll`, loaded at the next MCC start (the known `tools/panel_art.py` PIL failure aside; it also carries the uncommitted `reach.cpp` round-pause change already in pg18). `test_wheelman.py` checks the new rule; `set_bot_difficulty` checked on scratch files (Mythic and Demon to Any, Legendary keeps Wheelman). Full suite: 962 tests OK. **Not seen in game.**

### Warthog chaingun: no spray at the newest radar dot, 2026-11-18

The owner's F9 "Majorgunner in the turret shooting the ground why" (reach_dlc_medium `20261118-220316`, 619.2 s; he added "The gunner shooting the ground was about several seconds before killing me").

- **Found:** with nobody in sight, the Warthog gunner's "stay spun up" rule aimed at whoever's belief was newest and held the trigger whatever the gun pointed at. That meant any man known in the last 2 s within 30 u, a radar dot too, picked again every tick. At 615.9-616.2 s MajorGunner swung between three men it never saw (#4, #14, #9) with the gun 12° down, into the ground. In that match 6 gunners fired 67 ticks this way, and only 1 was at the man the gun had been on with the gun on his spot.
- `brain/bot.py`: the gun keeps to the man it was last aimed at (`Bot.spin_on`, set in the aim branch), for `SPIN_KEEP` 2 s after it was last on him, while he is alive, known within 2 s and within `SPIN_R` 30 u (`Bot.spin_target`). It fires only once the gun is on where he went (`aim.on_target`, `SPIN_SLACK` 4, the held turret window). Radar dots alone turn and fire nothing.
- **Not fixed:** the 606-611 s rounds. From the Warthog driving away up the slope, the gun turned back and 12-18° down, 57 presses did nothing while the owner recharged from 0.22 to a full shield. Those were aimed at his chest from the calibrated gun mount, and the map's data shows a clear line every time; the cause is not known (a guess: `GUN_HEIGHT` was measured at 6 u on level ground).
- Validation: `tools/test_warthog_spin.py` (new, 4: on him, not the newest dot; no fire while the gun swings there; not after `SPIN_KEEP` nor once he is dead; dots alone spin nothing). Full suite OK; `live_bots` imports. **Untested in a match.**

### Bomb carriers: drop to fight in one-bomb Assault, and nothing but the plant near the goal, 2026-11-18

The owner: "Add the ctf rule where the runner drops the flag but for neutral bomb assault and one bomb to fight when running. Also Make it to where the bomb planter doesnt leave the bomb site if theyre planting or within 4 units of planting to avoid a fight. That should be the only priority is too plant the bomb that close."

- **Drop to fight** (`brain/bot.py`): `Bot.flag_fight_check` now also runs in Reach Assault when one bomb is in play (`Bot.single_bomb`: Neutral Bomb's bomb, team 8, or One Bomb's, with one goal left to plant on). The rule is unchanged: dying before it gets there, more than 4 u out, an enemy within 10 u. Home is the enemy goal it plants on (`flag_home`, `modes.carry_goal`). Going back after the fight, it takes the loose bomb but not one armed on a goal (`flag_dropped_at`). Two-bomb Assault is left as it was.
- **Plant first** (`Bot.plant_point`, `plant_hold`, `plant_stay`, `PLANT_HOLD_R` 4 u, `PLANT_HOLD_SCORE` 9.0): in Assault in every game, a carrier on foot within 4 u of the goal it plants on has one goal, the plant. `decide` drops every other score as its last step (fights, retreats, regroups, hunts, the close-fight rule) and calls off a drop to fight not yet made. `plan` decides again at once when the bot comes within 4 u with another goal, then puts the walk onto the goal back after the carrier's swing, the kit, the give-way and a grenade's step away. **A frag at its feet no longer moves a planter** (the owner's "only priority"). The carrier's melee swing at a man within reach still goes; it does not walk it off the goal.
- Validation: `tools/test_bomb_plant.py` (new, 10). It covers the Neutral Bomb and One Bomb drops, two-bomb and other games unchanged, back for a loose bomb but not an armed one, within 4 u only the plant, every Assault, not past 4 u or without the bomb, a drop under way called off, the walk put back, and through `plan` a fight goal turned into the plant and a frag's step undone. Full suite: 954 tests OK; `live_bots` imports. **Untested in a match**, and not replayed on a recording.

### Forge World One Flag: bots no longer freeze 10 s in, 2026-11-18

The owner, mid-match on Forge World TU ONE FLAG CTF (4-10) (recording 20261118-205428): "Bots are frozen currently in game".

- **Found** (`logs/brain.txt`, from the new `tick failed` logging): from 10.7 s every tick failed with `KeyError: 1` in `brain/director.py` `role_slots` (`s.map["flags"][enemy]`), so no bot got a command. A Forge variant's stands come from where its flags lie at the start (`tools/live_bots.py` `snapshot`, `stands_by_spawn`), and One Flag has one flag: after 10 s the map got `{0: stand}` and no stand for team 1. The 17:47 freeze ("All the bots are frozen", "100 sporks is bugged") was the same gametype on Forge World, stopping 10.1-10.7 s in, so very likely the same cause.
- `brain/modes.py` `spawn_bases` (new): each team's middle where its players stood at spawn. `tools/live_bots.py`: the first positions of the match are kept (`MAP["forge_spawn_at"]`); a team the stands leave out gets its spawn middle as its stand. The flag's own team keeps its real stand.
- Validation: `live_bots` and `brain.modes` import; that match's one stand at (38.07, 181.04, 37.2) gives team 0 the stand and team 1 its spawn middle. **Untested in a match:** where One Flag's attackers score on a Forge layout (the capture point is now the attackers' spawn middle unless the map lists a flag return).

### Power weapon runs finished unless an enemy is close, 2026-11-18

The owner, on the rockets of Forge World 20261118-180057: "Why do they need to be taught that though ... a bot got rockets once that match didnt they", then "Yes commit to them unless an enemy is close".

- **Found** (that match's trace, and the layout's nav offline): the bots could reach the rocket launcher. The nav's way goes up the east ramp onto the 46.1 u deck, the way Cedercare walked to them at 206 s. About 170 runs at them ended after 1-4 s for a hunt (78), a retreat (35) or a fight (30) and began again from farther off; only McXglossy's 23 s run looked stuck. (An earlier reading here, that the bots kept getting stuck under the raised spot, was wrong: those "unstuck" and "step down" notes were mostly elsewhere on the map.)
- `brain/bot.py` `Bot.power_commit` (`POWER_COMMIT`), in `decide` before the flip-flop rule: on its way to a power weapon (`power_at`), while that item is still scored (believed there, not given up as unreachable), the run goes `POWER_COMMIT_MARGIN` 0.5 over every other goal, unless an enemy it knows of (seen, radar, a callout or his shots, under 1.5 s old) is within `POWER_COMMIT_CLOSE` 8 u, or it was hit in the last 2 s, or the run has gone `POWER_COMMIT_MAX` 25 s. A man seen farther off is still shot at on the way. Not in a vehicle nor carrying. Every tier.
- **Measured on that trace:** of 174 runs that ended, 117 would have gone on (59 for a hunt, 19 for a retreat, 18 for another item, 17 for a fight with nobody within 8 u, 4 for a post); 37 ended with an enemy within 8 u, 19 under fire, 1 dying. The 19 retreats include Demon's "cover until the shield is full" with nobody within 8 u: the run now goes on with its shield coming back on the way.
- Validation: `tools/test_power_commit.py` (new, 5: the run over hunts, retreats and far fights; a close enemy by each source, a hit, an old dot; only a power weapon still scored, on foot, the switch; the 25 s limit and a new clock; the order in `decide`). All regression tests pass. **Untested in a match.**

**Same day, the push and the recharge.** The owner: "if the bot thinks it can win the fight from any range it commits to the push", and (on "a cracked shield with a bad guy near: hide until it's fixed, then go") "implement that". A check first: the 19 retreats above were at a full shield, breaking off from men 8-17 u off, not recharging.

- `Bot.power_commit` now keeps the run while the men who can fight it are a fight it wins: those known under 1.5 s old within 8 u whatever the walls, with an open line to it within `DEMON_WATCH_R` 40 u, or the man who just shot it, all on it at once by the fight odds (brain/odds.py, `odds_threats` with all aware), `POWER_PUSH_ODDS` 1.0 or better. Losing: the usual choice (break off, cover, the fight). An enemy close, or a hit, no longer ends the run by itself.
- With its shield under `POWER_RECHARGE_SHIELD` 0.5 and an enemy known within `POWER_RECHARGE_R` 20 u, the run is let go, so the recharge rules take it to cover; no enemy that near, it goes on with its shield coming back on the way. Not in shieldless modes.
- Only Demon shoots men in view on its way to a gun (`on_way_target`); every other tier now keeps its fights, the run going over the rest only (before this, a Legendary's run outranked a fight with a man in view it would not shoot).
- **Replayed** on Forge World `v4b705611` at each end of the 173 runs of that match (world rows for everyone, each bot's own beliefs, the layout's terrain, every gun a DMR): 153 kept (Demon 133, Legendary 10, Blind 10); Demon let go 17 for a losing fight and 3 for its shield.
- Validation: `tools/test_power_commit.py` (now 9: no one who can fight it; a line at 12 and 30 u, won and lost; close behind a wall and the shooter; past 40 u, an old dot; hurt with a man near, none near, half a shield, shieldless; power weapon only, on foot, the switch; other tiers' fights; the 25 s limit; the order in `decide`). All regression tests pass. **Untested in a match.**

### Service Record: every bot has its emblem, 2026-11-18

The owner: "Distribute an emblem to every bot on the site so they have one show on the leaderboards." 138 of 753 bots had no picture: a bot's emblem picture (`native/bin/emblems/<name>.rgba`, and its lobby numbers `.ids`) was made only when the bot was first seated in a lobby.

- `tools/service_record.py` `make_emblems`: each build makes the missing ones with `brain/emblems.py` `export`, the same emblem the bot would get when seated (its pick, else its seed's roll), so bots added to the pool later get one too. It writes only into the mod's own emblem folder (paths elsewhere, as in tests, make nothing) and skips names a file cannot hold. A name the site lists with a trailing space ("ii Toxic Moose ") is made and found under the game's spelling (`pool_name`), so the site shows the emblem the game uses; `export_emblem` falls back to that spelling.
- Validation: `tools/test_bot_emblem.py` `test_every_bot_gets_one` (missing made with its roll's numbers, an existing picture kept, the trailing-space name, nothing outside the mod's folder). Full suite: 935 tests OK. The real build made 135 pictures (621 → 756). All 753 bots have an emblem in data.js; all 753 files load from the editor; leaderboard rows: none without an emblem, none broken. AimBotAdjacent (none before) shows its emblem. Not checked in game: the new `.ids` are what the game would write on seating them.

### Simulated matches reach the site and career totals under `python -I`, 2026-11-18

- Found: MCC runs the tools as `python -I`, which leaves the tools folder off `sys.path`. `tools/service_record.py` `build` and `tools/bot_career.py` `main` caught the failed `import bot_sim` and went on without a simulated match, so every bot showed only the games it played with the owner.
- Both now put their own folder (`HERE`) on `sys.path` before that import.
- Validation: `tools/test_sim_isolated.py` (new, 1 test) runs both under a fresh `python -I` on a made-up install and finds simulated matches on the site and in the totals. Full suite: 935 tests OK. Not yet seen on the live site after a real MCC run.

### Reach Banshees: more room under a soft-kill roof, 2026-11-18

The owner, Boneyard: Ashenblade (Blind) flew the Banshee for one kill; the next game PwnageTV (Demon) "not even shoot a banshee bomb once".

- Found (trace_reach_70_boneyard_20261118-185212, PwnageTV's 84 s ride): two bomb cycles. 13 of its 15 attack runs ended 22-29 u from its man; the bomb now goes only from 6-18 u (`REACH_BOMB_R`, Nov 17, from the owner's bomb kills), so it had no chance. The runs ended on the run's ground look ("the ground on the run, pulling out"): Boneyard's soft_safe zone tops out at 4.0 z, and 2.5 u off it (`AIR_ROOF_M`) with no climb in the 1.5 u under that held the Banshee under 0 z, the height of the big structures' tops, 0.5-1 u over them. AshenBlade11 the match before: inside 18 u on 2 of its 11 runs, a bomb cycle on both. The owner's 21 Boneyard bomb kills dive from 10 u over him at 14-21 u off, the nose 0.4-0.9 rad down.
- `brain/terrain.py`: `air_roof_soft(x, y)`, whether the roof there is a soft one (a soft_safe top or a soft kill's bottom: a countdown over it, not instant death); `air_roof` unchanged.
- `brain/bot.py` (Reach only): under a soft roof the margin is `AIR_ROOF_SOFT_M` 1.5 u and the no-climb band `AIR_ROOF_SOFT_BAND` 0.5 u (`Bot.roof_margin`, used by `air_ceiling`, `air_roof_guard`, the wall climb and the deck height). Boneyard's pilots may now cruise to 2.0 z, about 2 u over the structures. Hard roofs and the other games keep 2.5 u and 1.5 u.
- Tried and left out: on a run, flying level over a roof under the nose instead of ending the run. In `tools/air_replay.py` (the map's volumes on, 4 seeds, 4.5 u/s) it cut bomb starts 28 to 22 and raised ticks into the level 39 to 193.
- Validation: `tools/test_reach_banshee_room.py` (new, 4 tests: Boneyard's safe top reads soft, a hard safe zone's does not, the margins by roof and game, the soft no-climb band). All 101 test files pass. Replayed, the margin change did not raise bomb starts: PwnageTV's ride 28 to 26 (ticks into the level 39 to 13), AshenBlade11's 23 to 17 (5 to 28). The replay does not reproduce the live failure, though (4-7 bomb starts a ride against PwnageTV's 2), so the live Boneyard test the owner is running decides it. Untested in a match.

### Forge-placed man cannons and grav lifts: markers, their throws ridden; the chance picks cannons, 2026-11-18

The owner: "What about the cage the forge map?"

- Found: The Cage (Forge World `vd7eaef53`, "$HReach_MPMap_R-25_Title") has one Forge piece `ff_man_cannon_forge` at (17.8, 180.9, 35.4) and no lift. Bots had no marker for it: features.json holds the scenario's lifts and cannons, never a layout's Forge pieces. People's LiDAR walking recorded its throw, (17.8, 181.6, 35.5) to (18.4, 166.1, 37.9): 15.5 u in 3.17 s. To the nav that was a plain 15.5 u jump (cost 24.3), still cheaper than walking round (67-79 from by the pad to by its landing), so the nav did send bots there. They ran it as a jump, though, and the jump check called it short 1.5 s into the 3.2 s flight (the failure `ride_cannon` was made for: the owner's Adrift cannon). No trace of a Cage match names its layout, so what bots did at that pad is not seen.
- `brain/maps.py` `forge_pads` (load_map): each lift or cannon piece of a variant's layout (name `man_cannon` / `mancannon`: launcher; `grav_lift` / `gravlift` / `gravity_lift`: lift; no doors) with no lift or launcher marker within `LAYOUT_PAD_SAME` 1.5 u becomes one, group "forge". That gives `Bot.lift_near` / `lift_base`, the nav's lift columns and `anchor_launches`' ride marking. `forge_throws` (`_build`): a link from within `CANNON_PAD_R` 2 u of a Forge cannon's piece (3 u in height) going `CANNON_THROW` 7+ u on the flat is its throw: ride, launch, its recorded airtime (at least 1 s). The nav prices it by airtime (The Cage's: 8.1). The bot steps on and is thrown (`cannon_of`, `ride_cannon`). Base-map cannons (Tempest, Breakneck) are as before.
- `brain/bot.py` `lift_detour`: the lift chance takes a man cannon's throw too (any ride link flagged launch: Forge cannons, the owner's drawn ones), on any trip, not only up; on a win it walks to the take-off and starts `cannon_ride` ("lift chance: on the man cannon"). A cannon this bot found short or never thrown is skipped (`jump_fails`). Stand-in terrains without a list of links are skipped, and whether a map has a throw at all is cached per link list.
- Other layouts this gives markers to: Wayont (four ff_grav_lift), Delta Facility, Rasu, Mt. Lam Lam, Utopie, Brick and others (lifts and cannons listed in the lift entry below). Without a recorded ride there is still none to take: those pieces have no phantoms (no HREK kit here).
- Validation: `tools/test_layout_lifts.py` 17 tests (new: Forge pieces become markers, doors and pieces on a marker not; a Forge cannon's long link is its throw, a hop off it and a base map's cannon not; The Cage: one marker, one throw costed under 10, the nav's way from north of the pad is the throw and `cannon_of` gives its 3.17 s, the chance walks to its take-off and starts the cannon ride). All 936 regression tests pass. Untested in a match. (Commit 1539a23's `brain/bot.py` had four lines of the cannon branch put into the wrong block when its hunks were applied without context, so it did not parse; the next commit puts them back. The working file, what the game runs, was right throughout.)

### No sight or shots through a Forge piece's sloped top (Pinnacle's centre dish), 2026-11-18

The owner: "Pinnacle bots still shoot through the side of the forge bowl in the middle of the map."

- **Found,** offline on Pinnacle's layout (Forge World `v079e8abd`): the bowl is the `ff_dish` and `ff_dish_door` pieces. Their rim stands about 1 u over the floor round it, and is in the terrain all the way round, except the door piece's real doorway at about 45°. Its slopes go in as floor (walkable, no wall bins).
  - `Terrain._ray`'s floor test compares each sample of a line with its own cell's floor only. A nearly level line that slid in under the rim's rising slope crossed no cell's floor, so it went through the solid rim unseen.
  - Of 283 open lines from 7-14 u out to the bowl's middle, 148 went through the rim, a few hundredths under its top.
  - All 40 shoot-through cells learned on this layout (`walls_learned.json`) were inside Forge pieces: the dish, its rocks, bridges, ramps and the tower. A hit put down to the wrong man teaches one (`Bot` `shot_line`: the man aiming nearest our way).
- **`brain/terrain.py`:**
  - `_slides_under` (new, `SLIDE_STEP` 0.5) is called by `_ray`. A line going from over a placed piece's floor surface to under it, or back, between two neighbouring samples is shut, when the surface is continuous there (its levels within 0.5). This covers placed pieces only; the level's own floors are as before.
  - Faced pieces' wall bins are kept per cell (`_note_piece_walls`, `piece_wz`, `piece_solid`). `learn_shot_through` learns none in a piece's walls or floors. Solid boxes, which are approximate, still learn.
- **`brain/maps.py`:** at load, learned cells inside a Forge piece are not used. They are kept in the file.
- **Validation:**
  - `tools/test_piece_slide_los.py` (new, 5 tests):
    - a line under a sloped ridge is shut (and was open without the test);
    - lines over it and down its far side stay open, and nothing changes without pieces;
    - a piece wall at a railing's height learns no shoot-through, while the same wall in the level does.
  - On Pinnacle the lines through the rim went from 148 to 3, the 3 skimming the doorway's edge by 0.02. The 10 lines the learned cells opened are shut, and all 40 learned cells are now unused.
  - **Every pair of real positions** in three recordings: Pinnacle 677 open lines, 13 shut; Forge World `v8e4a8930` 1041, 3 shut; `v4b705611` 896, none. Every shut line ran under a piece's top.
  - A sight test takes 79 µs instead of 70.
  - All 932 regression tests pass.
  - **Untested in a match.**

### The lift chance; lifts nobody rode are in the nav, 2026-11-18

The owner: "CAn we just make it to where the bots take the lifts more? Like add a scoring chance. Weve messed with it before Ive never seen them ever use one".

- Found (traces): the nav takes a lift only when it is the cheapest way. Damnation Anniversary 20261118-172112 had 5 real rides of its tall lift in 4 minutes, six bots. (The entry below counted "30+": that counted bots on the floor over its top, not rides.) Ivory Tower 174341 had 3, Launch Station 20261113-231630 none. In matches a lift was known only from a recorded ride. Launch Station's main lift had none, and Prisoner Anniversary's five lifts had recorded rides from one. The rides solved from the lifts' tags (`tools/lidar_rides.py`, the committed phantoms.json) were added only in LiDAR runs.
- `brain/bot.py` `lift_detour` (move_to, before the nav): a trip to a goal `LIFT_UP` 1.5+ u over the bot rolls `LIFT_P` 0.6. One roll covers a goal within `LIFT_GOAL_R` 3 u for `LIFT_ROLL_S` 10 s. On a win, the bot takes the cheapest gravity-lift ride (a ride link with a lift marker by its take-off, none this bot found dead) whose take-off is within `LIFT_REACH` 30 of it, whose landing is nearer the goal, and whose whole way costs at most `LIFT_DETOUR` 15, or `LIFT_DETOUR_SHARE` 0.75 of the trip if less, more than the nav's (field costs, people's links on; trips under `LIFT_MIN_TRIP` 6 not). It walks to the take-off and starts the ride there (`s.via_lift`, then `s.lift_ride`: `ride_lift`, its stalled and dead checks), with notes "lift chance: ...". It goes back to the nav's own way if the goal moves on or the walk overruns.
- `brain/maps.py` `map_lift_rides` (`_build`): the map's gravity lifts' solved rides (`lidar_rides.ride_links`, a variant's layout's lifts) rising `MAP_RIDE_RISE` 1.5+ u, from lifts that no ride in the map's links starts within 2 u of. None lands in a kill zone (`T.oob`, as `nav_learn`). Man cannons are not added. About 0.02-0.25 s a map.
- Offline, every roll won, 300 random trips from beside a lift to a floor 1.5-2.5+ u up: Damnation Anniversary 88 took the tall lift (detours 0-11 u), Launch Station 147 (0 before), Prisoner Anniversary 157 (0 before), Zealot 271, Ivory Tower 275, Highlands 23, Condemned 7. In a match about 60% of that, plus the nav's own rides.
- Not fixed: three of Ridgeline's four lifts, and Condemned's hangar lift, have no solved ride (`lidar_rides.solve` finds no landing from their step-in). Ridgeline's one solved ride lands 1.85 u up. Forge-placed lifts have no phantoms (no HREK kit here).
- Validation: `tools/test_layout_lifts.py` 13 tests (new: won rolls on Damnation go up the tall lift; a lost roll holds for the goal; the ride starts at the take-off; no roll for a goal not above; Launch Station's lift is in the nav; none added where a ride is recorded or the lift is gone). All 921 regression tests pass. Untested in a match.

### Reach's bombs and ball found by name on every map, 2026-11-18

The owner: the bots don't play Multi Bomb, Stockpile or Oddball right. On Sword Base, "even though the map has been scanned they have no idea where to go"; they go to the wrong place, and lose it after picking it up. And: "I dont want to have to fix every single map".

**What was found.**
- Every Reach map's export lists each mode's places in full: 5 bomb stands, 4 bomb goals, 7-13 Stockpile stands, 4 Stockpile goals, 2-9 ball spawns. Sword Base's two variants list the same as its scenario. So the places were not missing.
- How the objects were found was the problem: the first weapon object seen lying on a stand or ball spawn taught the mode's object tag, one tag a match.
  - The owner's Pinnacle Stockpile (20261117-205817) shows the result: the brain counted 8-17 "flags" on most ticks against Reach's 4-5. Most were guns in hands (read at 0, 0, 0) or dropped ones, and some lay under the map, so the bots ran to guns.
  - Another session's fix of Nov 17 already names Stockpile's flags (`LiveReach.OBJECTIVE_NAMES`). The bombs and the ball still learned the old way.

**The change.** `brain/live.py` `LiveReach.OBJECTIVE_NAMES` now also has:
- Assault's bombs, `assault_bomb`, as read in hand live on Forge World One Bomb today;
- Oddball's ball, `skull`: Reach's ball, as Headhunter's.

So no gun on a stand or spawn is ever taken for one, on any map. `balls()` also finds the ball by name on a layout that lists no ball spawn.

**Tests.** `tools/test_reach_objective_names.py` (new, 9 tests) uses Sword Base's real stands and ball spawns:
- both Multi Bomb bombs found;
- a magnum dropped on the neutral stand never a bomb;
- the carried bomb's carrier read;
- the old way taking the magnum, kept as the bug;
- a loose ball found, and its carrier read;
- a gun on a ball spawn never the ball;
- no ball spawns listed, still found;
- the old way missing a loose ball.

Two full runs: 915 tests OK. One earlier run had one error that did not recur, test not identified.

**Not tested in a match:**
- the tag names' exact paths for the bomb and the ball (the bomb's name is seen live in hand; the ball's comes from Headhunter's notes);
- whether this cures the losing of the object after the pickup;
- Pinnacle's Stockpile recording is mostly the bots stuck on its Forge pieces (step down, edge stops, teleporter waits), which this does not touch.

### Lifts a map variant's layout lacks are left out; a lift that does not lift is given up, 2026-11-18

The owner: "Can you go through and fix the lifts In halo reaches lidar? Im tired of having to manually show bots how to use it. They just play damnation all stuck in the bottom of the map because they dont want to use the lift and then three on my team are stuck elsewhere. even though the entire map was scanned. Was a bug report" (F9 report 20261118-172222, "Bots stuck on damnation", Damnation Anniversary `reach_cex_damnation/variants/v08b84b0d`).

- Found (the match's trace, logs/trace_reach_cex_damnation_20261118-172112): Grivn, NoMedalsNeeded and John S117, his three teammates in the report, stood in the short grav lift's spot (-7.3, -7.4, -0.2) 105.6, 114.1 and 156.8 s, 0.2-0.3 u off its middle, never lifted; the tall lift worked (bots rose in it 30+ times). The layout's .mvar ("Damnation Anniversary") has the tall lift and no short one. The bots had it from the base map: its features.json marker, and the base lidar.json's simulator ride from it (the variant's nav reads the base's data, `data_names`). `Bot.ride_lift` called a ride failed only beside the column, so a bot in its middle ran out the 12 s limit and the nav sent it in again. Offline nav (people's links on) did route through both lifts; the walking way up was there.
- Other layouts of his with base lifts their .mvar lacks: Beaver Creek Anniversary (both `gravity_lift`), Hang 'Em High Anniversary (`heh_gravlift`, `_tunnels`, `_catwalk`). Battle Canyon keeps both: one base lift is a `gravity_lift_blue` piece on the same pad.
- `brain/maps.py`: `layout_lifts` leaves out a base lift or launcher of the scenario's crates (features.json group "crates") with no lift or cannon piece within `LAYOUT_PAD_SAME` 1.5 u of its pad, only when the layout's pieces carry the base's placed objects at all; their pads go in `m["lifts_gone"]`. `off_gone_pads` drops the ride links from a gone pad (flagged ride or launch, or rising `LIFT_RISE` 2+ u, from within `LAYOUT_PAD_R` 2 u). Netgame-flag launchers (Spire's inv_mancannon), machines (Ivory Tower's elevator) and built-in maps are as before; the owner's drawn rides still add their pads after.
- `tools/lidar_rides.py` `layout`: the map's phantoms.json less the gone objects, for `ride_links` (LiDAR runs) and `tools/lidar_sim.py` (the simulator's pushes), so neither rides a lift the layout lacks again.
- `brain/bot.py` `ride_lift`: in the column's middle (0.6 u) `LIFT_DEAD_S` 3 s and no higher than 0.5 u over where the ride began, the ride is over and every take-off into that column is left `LIFT_DEAD_BAN` 300 s (`jump_blocked`; note "lift: in it and not lifted, no lift here"): a lift switched off in a mode, or any not in the data.
- Not done: lifts and man cannons placed in Forge (Forge World's Wayont, Delta Facility, Rasu and others: `ff_grav_lift`, `ff_man_cannon_forge*`) still have no push data. Their tags need the HREK kit, which is not on this machine, so bots ride them only after a LiDAR ride.
- Validation: `tools/test_layout_lifts.py` (new, 7 tests: the layout rule, the ride filter, Damnation's real data for the nav, LiDAR and the simulator, a dead lift given up in 3 s with its take-off left 300 s, a working one ridden on). The regression suite ran 906 tests: 905 pass. `test_demon_fire` `test_armor_lock_stops_an_automatic_burst` errors only with this machine's `user/grenade_flights.json`, which git ignores and today's match wrote at 18:52. It passes on a clean HEAD copy without that file, and none of the code it runs changed here. Untested in a match; a match was running, so the change loads at the next one.

### Demon's radar attention by threat on the map, 2026-11-18

The owner, on the last-place Demon of Forge World 20261118-180057: "I want the bot to only watch the dot on the radar ... if the bot cant see someone else, or is getting shot or in a fight", "Is there a way to implement the map layout in the bots radar skills? ... if one is behind the wall and the other cant see him what happens then?", and "I want to maximize a demon bot shooting at the targets he can see while minimizing every unneeded death".

- **Found** (that match's trace): in all 8 of N1ghtR4ven's deaths where he was shot first, his radar had the killer within 0.5 u at the first hit; in 7 of 12 deaths the killer was 50-113 degrees off his view. `dot_glance` (Nov 7) looked 0.7 s at the nearest dot outside the view, then not at that man again for 2 s, and the walk went on between glances: at 88.2 s it turned him from the owner's dot about 5 u off to PacMan's 14 u off, and Oreo's sniper hit him 1 s later from 3.8 u.
- `brain/bot.py` `Bot.radar_threat` (Demon, `DEMON_RADAR`): in `look_point`, only when nobody is in view and nothing just hit it (both keep their priority), the 3 nearest dots or team callouts within 20 u, under 2.5 s old, at the Demon's guess of where each is now, ranked by the map: an open line to it first (looked at); else the soonest into view on his walk at 2.5 u/s (`dot_corner`, one walk down its way to him per dot): his corner looked at, or down a way that turns out of its sight right by it; over 4 s from view: left, its eyes on its own way. The man watched keeps the eyes until another is 0.4 s sooner; no 2 s lockout. Its look is free of the walking cone and of the slow-down for walking 60 degrees off the view: it goes on its way at full speed with its aim on his corner. `dot_glance` is off while `DEMON_RADAR` is on. Only the dots, where they went and the map are used, not the enemy's real facing.
- `Bot.open_dots` / `demon_break_second`: in a fight, a dot under 1 s old with an open line on it counts as a second man (the rule from earlier today, which counted men in view only): it steps out of that line onto a spot the man it fights still sees, and keeps shooting him.
- Cost: `dot_corner` is 3-7 ms on Forge World; one new walk a bot a tick, each kept 0.5 s while he moves under 1.5 u and it under 1 u (another dot keeps its last answer up to 1 s more meanwhile).
- **Replayed** on Forge World `v4b705611` with that match's beliefs and positions, at 10 moments before N1ghtR4ven's deaths: the new watch was on the killer at 6 (88.3 s and 88.9 s, where dot_glance looked at PacMan; 28.8 s, 98.6 s, 175.5 s, 176.0 s). At 122.0 s and 247.5 s it watched a man 2.8 u and 1.8 u off, not the killer 11 u and 4.4 u off; at 11.0 s one of four men within 10 u; at 225.4 s he was fighting a man in view (not radar's).
- Validation: `tools/test_demon_radar.py` (new, 13: the open line first, the soonest corner and its point, a long way round left, a way out of sight right by it, the hold and the switch, 3 ranked, stale and heard dots, other tiers, the switch, carrying, look_point under a man seen and a hit, the wiring, open dots, the second man in a fight and not through a wall, one walk a tick). `tools/test_demon_dot_glance.py` tests the old glance with the switch off (+1: off while it is on). 898 of 899 regression tests pass; the one failing, `test_demon_fire` `test_armor_lock_stops_an_automatic_burst`, fails the same with `DEMON_RADAR` off: since `user/grenade_flights.json` holds 3 Reach flights (18:46), the solved throw runs in that test and its made-up level has no `live_head`. Fixed after: `tools/test_demon_fire.py` now keeps `nade.model` off (its tests are the trigger's; the solved throws have `tools/test_nade_throw.py`), and the whole suite passes (915). **Untested in a match.** Mythic is not changed (its own tier).

### Reach grenade flights: the watch follows grenades, not the bots' rounds, 2026-11-18

The owner, after a few matches: "How does the gernade arc update look?" The solved throws (below, "Grenades thrown on a solved arc") never came on.

- **Found** (today's 7 Reach traces, 17:21-18:00, and `user/grenade_flights.json`):
  - The bots pressed grenade about 240 times on foot: Damnation 16, Forge World 38, 3, 3, 67, 75, Ivory Tower 37.
  - `nade.FlightWatch` kept 2 flights, both in the Damnation match. A game needs `MIN_FLIGHTS` (3), so every throw stayed the old one along the aim.
  - The 2 disagree: 4.8 and 10.7 u/s, 28 and 14 degrees off the view. They are likely not the throws.
  - The likely cause: the watch was fed every type-5 object (`live.objects((5,))`), and Reach names them all "unknown". At a press it takes the newest projectile at the bot's eye, which is often the DMR or AR round fired that tick. That round is gone or far a tick later, so the press ends unfitted and the grenade after it is never looked at.
  - The traces do not record projectiles, so this is read from the code and the numbers, not seen.
- `brain/nade.py`:
  - `watch_objects(live, now)`: in Reach, the hand grenades only (`LiveReach.grenades`, frag and plasma by their own tag name, from "Reach bots read live grenades" above). Elsewhere every type-5 object, as before.
  - `FlightWatch.observe`: a followed object that is gone, or moves over `FAST` (60 u/s), before 4 samples is not the throw. It is left out and the watch looks again until `FIRST_S`. This holds in every game.
- `tools/live_bots.py`: the watch is fed `nade.watch_objects`.
- `user/grenade_flights.json` (machine data, not in Git) is renamed `grenade_flights.before_nov18_fix.json`, so the 2 doubtful flights are not in Reach's medians.
- Validation:
  - `tools/test_nade_throw.py` +2 tests: a round at the eye first, then the grenade, which is learned (the old watch kept 0); and Reach watching its grenades only, other games and `GRENADE_READ` off as before.
  - 882 of 886 tests pass. The 4 failures are `test_demon_dot_glance`, against another session's uncommitted Demon radar change in `brain/bot.py`, which this change does not touch.
- **Untested in a match:** whether `LiveReach.grenades` names Reach's frags live (the console's `grenades read live (frag_grenade)`), and the learned numbers. The brain prints `grenade flight learned` for each throw kept. After 3 of them, the next match aims the solved way.

The owner, after Forge World Team Slayer DMR 20261118-180057, where the last-place Demon N1ghtR4ven went 7-13: "make them read enemy grenades".

- **Found** (the match's trace and `tools/death_autopsy.py`): frags killed 3 of N1ghtR4ven's 13 deaths and he never moved for one; grenades were 16% of the Demons' deaths against 5% of the two people's. No bot could react to one live: `snap.grenades` had only ever been filled in a simulator that is gone, so equipment's grenade cue saw only a bot's own throws.
- `brain/live.py` `LiveReach.grenades`: the hand grenades lying or flying loose, read from the objects of type 5 (the projectiles, which `tools/live_bots.py`'s grenade watch already reads to learn throws) by their own tag name, `objects\weapons\grenade\frag_grenade\frag_grenade` or `...\plasma_grenade\plasma_grenade` (`_grenade_kind`: a tag whose own index names another object, the frag's detonation_hack say, is not taken for the grenade). Each comes with its position, its speed from the last read, and where and when it was first seen. A plasma stuck to someone is left out. `GRENADE_READ` is off for `LiveH4F` (Halo 4 / H2A: not checked there).
- `tools/live_bots.py`: `snap.grenades` from it 10 times a second in Reach; the console says `grenades read live (frag_grenade)` the first time one is read in a match, and a read error is printed once and never stops the bots.
- `brain/bot.py` `Bot.nade_danger` / `enemy_grenade`: a grenade within `NADE_DODGE_R` 4 u (flat) and 2.5 u of its height, or one still moving that will be there in 0.4 s, is run from: straight away, or the nearest turn off that line with room (`blocked_way`). The view and the trigger stay on the fight, so it shoots as it goes; `edge_guard` after it still stops it at a drop. It reacts after its tier's reaction plus 0.3 s × (1 − aware), never under 0.2 s (Demon and Legendary 0.2 s, Normal about 0.39 s); Easy never. Its own throw (first seen within 1.5 u of it in the first 0.3 s) is left to `own_grenade`. Called in `plan` after `keep_in_zone` (a frag outranks a post) and before `obstacle_guard` and `edge_guard`. Halo Infinite's bots have the same reflex (its Avoid behaviour, ODST and Spartan only).
- `brain/equipment.py`: the grenade cue (dash, jetpack, armor lock at its feet) now goes through `Bot.nade_danger`, so it has the same notice time and never locks or dashes at the bot's own throw.
- Validation: `tools/test_enemy_grenade.py` (new, 11: notice times by tier and Easy never, far, high and in-vehicle grenades left, a flying one counted where it lands, its own throw left, a wall turning the escape, the equipment cue, the order in `plan`, the tag naming, a made-up memory read with speed, first sight and forgetting, Halo 4 off). The tag naming checked on Forge World's own tag names. All 884 regression tests pass. **Untested in a match:** that Reach's live projectiles carry these tag indexes, the 10-a-second read's cost, and how well the escape saves a bot.

### Reach Assault round two: bot members kept over the round change, 2026-11-18

The owner, after One Bomb (TU) on Pinnacle with Sakallis joined: at round two players were "skating" and the red enemy reticle showed over teammates.

- **Cause** (`native\bin\botcore_pg14.log`, the match's last ~1,700 lines). The netbots member guard (`h_hr_localdrop`) took Assault's round change for the match's end.
  - The guard kept the bot members only while a players update had run in the last 3 s.
  - At the round change that pause reached 3 s. The log then shows `netmembers: the match is over: bot member 2 (user slot 1) dropped by the game`, `netpeers: stand-in peer 16 removed`, `removed all 6 bot member(s) and 1 stand-in machine(s)`, while round two was still to be played.
  - On the host: bots 2-4 (AtomicKiwi, MoonCheeseAttor, MtnDewMarauder) were marked gone (`player update ... type 0 ... team -1/-1 -> applied`), had no unit for the rest of the match, and never respawned.
  - On the friend's screen: with no bot members, no bot input was relayed (`hr_net_relay` relays members only). That is the same "skate, red reticle over his team's bots" picture as before members and netrelay existed. The host's log has no record of the friend's screen, so this is inferred, not seen.
  - It happened only here. In every other netbots match in pg13, pg14 and standin1, `report: results` came before the drop; in this one the drop came first and the results came at the real end.
- **Fix**:
  - `native/report.cpp`: `report_results_built()` counts MCC's post-game results builds (`h_build`). It returns -1 while that hook is off.
  - `native/reach.cpp`:
    - `hr_mb_add` notes that count when it makes a bot member.
    - The guard still keeps the members while a players update ran in the last 3 s. With no results built since then, it now also keeps them over a pause of up to 30 s, and logs `kept the bot members over a N s pause: no post-game results yet (a round change)`.
    - A real match end is unchanged: the results come first, then the 3 s rule.
    - With the results hook off, the guard works as before.
    - The drop line now gives the pause and whether the results were built.

Validation:
- `native\build.bat pg16` built `botcore_pg16.dll`. A `/W3` syntax pass of `reach.cpp` and `report.cpp` shows no warnings. `tools/panel_art.py` failed in that build (no PIL in the system Python); that step is not part of this change.
- No Python changed.

Not tested:
- Nothing of this is tested in game yet. The next multi-round Reach match with a joined friend on `botcore_pg16` should show the new "kept ... pause" line at each round change and no "match is over" line before `report: results`. Round two should have all bots on both screens.
- A host quitting mid-match (no results) keeps the bot members up to 30 s after the last tick instead of 3 s. The next match's `hr_mb_add` sweeps any left over.

Follow-up, the same evening (F9 reports 20261118-202245, "One Flag round switches players (bots) get booted from each team", Ivory Tower, and 20261118-203514, "Second example of bots getting kicked from round to round", Assault on Condemned):
- **Found** (`native\bin\botcore_pg17.log`): at both round changes the guard logged `kept the bot members over a 3.0 s pause: no post-game results yet (a round change)`, then `the match is over: ... (30.0 s without a players update, post-game results not built)` and `removed all 7 bot member(s)`. These round changes paused the players update for over 30 s. The 3 bot members (Wannada, Deadly Stealth, RancidMeteor in the One Flag game) were gone for the rest of the match; the 4 local bots stayed. No friend was in that lobby, so any multi-round Reach game with netbots members was hit.
- **Fix** (`native/reach.cpp` `h_hr_localdrop`): with no post-game results built since the members were made, the pause that keeps them is now `HR_ROUND_PAUSE_MS` 180 s (was 30 s). A real match end is unchanged (results first, then the 3 s rule). Only a match left midway keeps them longer, up to 3 min; the next match's `hr_mb_add` still sweeps any left over.
- Validation: `native\build.bat pg18` built `botcore_pg18.dll` (the known `tools/panel_art.py` PIL failure aside). No Python changed. **Untested in a match:** the next One Flag, Assault or other multi-round Reach match should show one `kept ... pause` line per round change and no `match is over` line before `report: results`, with all bots in every round.

### Proving Grounds on a joined PC friend's screen, 2026-11-18

The owner, after the link test worked live ("Yes, start it"): build Proving Grounds' screens for a PC friend on the link. The friend's copy shows the host's search, vote and loading screens, following the host, and votes in the host's vote.

- `native/pg_link.cpp` (new, in botcore) is the link test's tested channel cut down: MCC's Party text chat.
  - **Hiding.** `PartyStartProcessingStateChanges` and `PartyFinishProcessingStateChanges` are hooked, and texts starting `pgl2 ` are kept from MCC.
  - **Messages.**
    - `hello` and `ok` make the handshake.
    - `st` carries the host's state as a data buffer, sent on a change (at most 5 a second) and once a second.
    - `vote` carries the friend's vote to the host.
  - **Safety, from the live crash.** No text ever goes to an MCC without the hook.
    - Only `pglink=2` speaks first. It does so only when this PC joined someone's Party network (connected to it, did not make it), with exactly one other player in the lobby, 3 hellos at most, 20 s apart.
    - `pglink=1` (the default) only answers. `pglink=0` hooks nothing.
    - Each chat control's PlayFab entity id is checked every poll, so a handle MCC hands to the next player who joins never inherits a link.
- `native/proving_grounds.cpp`:
  - **The host's copy** fills a `pgs_state` (about 2 KB) each frame:
    - stage, playlist size, round, None of the Above;
    - the three options;
    - each bot seat's name, clan, team, tier, party flag, arrival time and scheduled vote;
    - the people and their teams and votes;
    - its own vote and the vote round's key;
    - the clock.
  - **A friend's vote** is counted in `counts()`, so it is in the tally. It is accepted only for the current round's key.
  - **The friend's copy follows** (`follow_update`). Its screens are drawn from the host's state with a roster of its own (`g_f_roster`), and its own bot list is never touched.
    - Nothing of its own runs: no search, deal, vote count or MCC launch, and no `pg_after_match`.
    - Its own vote goes back on a change and every 2 s.
    - The host is shown as a person, with a look from MCC's list by name and none if it is not there.
    - Its own settings (size, vote length) come back when the following ends.
    - Following ends after 4 s without word, or when the host leaves a match's stages.
  - **After a followed match**, the friend's own credits screen comes first (its own MCC report, marked when the host's launch became a game).
  - **Esc / B** put the host's screens away until its next stage; the PROVING GROUNDS tile brings them back.
- `native/overlay.cpp`: `pg_follow_poll()` every frame. The following draws in MCC's menus (`mcc_menu_state() == 0`), without the lobby probe or title read, which may not see a guest's lobby.
- `native/botcore.cpp`: `pglink=` in botcore.ini (default 1), and `pg_link_watch()` in the main loop. `native/build.bat` builds `pg_link.cpp`.
- `native/pg_preview.cpp`: the link as a loopback, and a 12th picture, `pg_12_friend_vote.png`: the friend's copy following a host's vote.

Validation:
- `native\build.bat pg15` builds `botcore_pg15.dll` with no new warnings. tools/launch.py injects the newest botcore, so it is live at the next MCC start.
- `native\build_pg_preview.bat` built and drew all 12 pictures. In `pg_12_friend_vote`, the friend's copy followed the host's vote:
  - 3 options and 7 bots, with their clan tags;
  - the host's vote counted (Territories 2);
  - the friend's own vote in its own box (Team Crazy King).

Not tested:
- Live in MCC, with two PCs:
  - the handshake through botcore;
  - the friend's screens over a guest's lobby;
  - the friend's vote reaching the host's tally;
  - the launch screen over the friend's countdown;
  - the friend's credits after a match.
- The friend needs this botcore and `pglink=2` in its botcore.ini.

First live run (friend on botcore_pg15): the friend's controller did nothing once the match loaded, though it worked in the vote and after the game.
- **Cause.** `overlay.cpp` keeps MCC's own XInput reads at rest while our screens take the pad (`g_pad_held`), but `pad_frame` only runs inside our ImGui frame. The friend's last frame was the launch screen, which holds the pad, and the match draws no frame of ours. So the hold stayed on through the whole match. The host's launch screen could do the same with a pad.
- **Fix.** A present with none of our UI up lets the pad go (`g_pad_held = false`). The button that closed a panel is kept from MCC only in the menus (`mcc_menu_state() == 0`).
- Built as `botcore_pg17.dll`, which also has the other session's Assault round-change fix. `ProvingGrounds_FriendView.zip` was remade with pg17. Untested in a match.

Bug reports of 17:51, "All the bots are frozen" and "100 sporks is bugged". The cause is not found yet.
- **What the logs show.** Two Proving Grounds matches on Forge World with the friend (17:47:59 and 17:50:28, variant `v8e4a8930`). Each brain's recording stopped 10.1-10.7 s in, with no error in it.
  - botcore's per-tick hook kept running (netwatch lines through the match), so the game ticked on and the bots stood still.
  - Windows logged no crash of the brain.
  - `logs/brain.txt`, which held the error, was overwritten by the next match.
- **Ruled out:**
  - The map variant: the 17:53 match on it played fully.
  - The solved grenades: dormant with 2 learned flights.
  - The flight watch: its errors are caught.
  - Brain file edits: none after 17:30.
  - The bot simulation's process check: it is Windows-safe.
- **Not ruled out:** both came right after the Proving Grounds counting run, which runs the simulation, and with the friend's link up. Both also came within 1.3 s of a bot's grenade press.
- **The change** (`tools/live_bots.py`): a tick's error and its traceback, the brain stopping after 90 failed ticks, and a pause the brain reads from botcore's still tick count now go into the match's own recording (`tick_failed`, `brain_stopped`, `paused` / `resumed`), which is kept per match. The next freeze names its cause.
- Checks: `live_bots.py` parses; 873 tests pass.

### Grenades thrown on a solved arc, Halo Infinite's way, 2026-11-18

The owner: Halo Infinite's bots "throw really good grenades", then "try to copy what they did but in a way that works with our code and doesn't break it".

- **Found** in `HaloInfinite.exe` (build HI_1_13_0, decompiled with Ghidra 12.2 for comparison only; no 343 code is in the mod):
  - A landing point, not the man (`FUN_1426fb7c0`, bouncing grenades only): past 8 it aims 3 in front of him on the thrower's side; closer, 0.8 of the way back toward the thrower; 0.2 lower.
  - A ballistic solve (`FUN_14316427c`) from the grenade's own launch speed and gravity (its `proj` tag): low or high arc, none out of reach.
  - The throw only within 30 degrees of the facing (cos 0.866).
  - The arc walked in 0.2 s steps through the level with a grenade-sized sweep (`FUN_14263e95c`); a blocked arc is not thrown.
- `brain/nade.py` (new): `landing_point` (Reach-sized numbers: 1 u short past 8 u, 15% back closer in; Infinite's own kept in `INFINITE`), `solve`, `arc_points`, `arc_clear`.
- **Physics learned, not guessed:** no editing kit is installed and the map files' projectile tags are not read, so each game's grenade speed, gravity, launch-over-view pitch and release delay are learned from the bots' own throws. `nade.FlightWatch` in `tools/live_bots.py` follows the new projectile after a bot's press (Reach, Halo 3, ODST, Halo 4: where objects are read), fits its first 0.6 s to a parabola (`fit`, bounces dropped) and keeps it in `user/grenade_flights.json` (60 per game). `model(game)` gives their medians from 3 throws up; the brain prints "grenade flight learned" for each.
- `brain/bot.py` `think`, every tier, on foot, at a man believed within 3-30 u near the plan's aim (`nade_target`):
  - `nade_steer` (before the turn cap): the press held back while the view turns onto the solved launch, up to `NADE_TURN_S` 0.5 s, the low arc first, the high one if the low is shut, led by 60% of his way over the flight.
  - `nade_release` (after the turn cap): the press once within `NADE_ON` 0.05 rad; the view held the learned delay + 0.15 s.
  - No open arc, a teammate by the landing (`nade_clear`), the arc past 30 degrees of the facing, or not lined up in time: not thrown, another try 1 s on.
  - No shot lock over a throw's view.
- Unchanged: every throw until a game's physics are learned (then exactly as before), the doorway pre-nade, throws with no man in sight (a landing, a counter spot), vehicle seats. `NADE_ARC = False` turns it off.
- Validation: `tools/test_nade_throw.py` (new, 14 tests: Infinite's rule as decompiled and ours; the solve lands where asked; the high arc and out of reach; the arc walk under a ceiling; the fit through a bounce; the watch keeping a bot's throw and not a bullet; the bot unchanged without a model, turning, pressing and holding with one, refusing off the facing, shut or onto a mate, lobbing over a wall, untouched without a man, in a vehicle, in a pre-nade or switched off). All 873 regression tests pass. **Untested in a match:** the first matches only collect flights; whether the fit sees Reach's frags; the landing numbers; plasma grenades are aimed the same way (the bots' grenade type is not read).

### Link test: can two PCs' mods talk in MCC? 2026-11-18

The owner wants Proving Grounds on PC friends' screens: the search, the vote, the loading hold and the level-up, following the host. ("Yes we need this to work in order to expand it even further.") Xbox friends can't run the mod. A PC friend's mod needs a channel to the host's mod.

What a static read found (MCC Oct 31 build):
- MCC uses PlayFab Party 1.4.13 (`PartyWin.dll`) for voice and text chat only. Its network allows 0 message endpoints a device (the `PartyCreateNewNetwork` call at rva 0x25F58F).
- Halo: Reach's session still carries Reach's own matchmaking vote: the `matchmaking-voting-*`, `countdown-timer` and `game-start-status` parameters, made near haloreach rva 0x3E2800. Whether Reach sends them in a custom game is unknown.

What an offline run of `PartyWin.dll` found:
- Every property call answers "API not implemented": device, network, endpoint and chat control.
- `PartyChatControlSendText` works, to chosen chat controls, up to 1023 characters, with data buffers.
- MCC gives its chat controls text permissions itself (rva 0x261D98), so an unmodded MCC would receive any text sent to it.

The kit (`native\build_linktest.bat` builds it into `native\bin\linktest`):
- `native/pglink.cpp` builds pglink.dll, a DLL of its own, so a friend on an older install can run it. It changes nothing in the games and logs to pglink.log next to it.
  - **Party.** It hooks MCC's `PartyStartProcessingStateChanges` and `PartyFinishProcessingStateChanges`. Each other chat control first gets one hello, 3 at most, a minute apart. One that answers gets a post every 3 s, carrying a sequence number and an echo, so a round trip shows in one log. Size tests follow: a 1023-character text, then texts with 1000, 4000, 16000 and 60000 data bytes. pglink texts are taken out of the state changes before MCC sees them: MCC finishes a copy, the test finishes the original. It also logs each chat control's entity id and device, and the permissions MCC gave it.
  - **Reach, read only.** The session's state, peers and members, and whether the vote and countdown parameters change, hashed 4 times a second.
- `native/pglink_load.cpp` builds pglink_load.exe, which loads pglink.dll from its own folder into a running MCC. It refuses while Easy Anti-Cheat runs or when pglink.dll is already loaded.
- `native/pglink_readme.txt` becomes the kit's README.txt.

Validation:
- Built with VS 2022.
- In a test process, it loaded, hooked a real `PartyWin.dll` and passed its calls through. With an offline Party handle, local user and chat control, the poll read the chat control and its entity id without a fault.

Not tested:
- With MCC, and between two PCs.
- The hiding of received texts: a loopback isn't possible offline.
- The Reach probe.
- Whether MCC keeps a Party network in a custom game lobby.

First live run, 2026-11-18 (host only), and the change it led to (test 3):
- The host's pglink.log: MCC kept a Party network in the custom game lobby, the friend's chat control appeared, and the host's hello to it sent without an error. The friend's MCC dropped out 10 s after the first hello and 5 s after the hello on the rejoin. No pglink text ever came back from the friend's side. So a hello reaching an MCC without the test, or the friend's copy itself, may crash it; the friend's log is not read yet.
- Now only the friend's copy speaks first. A file `pglink_friend.txt` next to the DLL marks it, and only the friend's zip has it. The host's copy (`native\bin\linktest`) never messages first and only answers a chat control whose pglink sent it a pglink text. The log's second line says which role a copy has.
- The README now has the host load the test before the friend joins, the friend load theirs before joining, and only the two of them in the lobby.
- Rebuilt with `native\build_linktest.bat`. `native\bin\ProvingGrounds_LinkTest.zip` was remade with pglink_friend.txt. The DLL has the new strings.

Live run of test 3, 2026-11-18, 17:01 to 17:13, host and one PC friend, both running it. The roles were swapped: the host ran the friend's copy. Results:
- A lobby join with neither copy speaking first (16:44): no crash, and a full Proving Grounds match played.
- HANDSHAKE within 1 s of the join, both ways. The hello and every later pglink text were "kept from MCC" on both PCs. No crash and no chat text shown.
- Sizes: the 1023-character text and texts carrying 1000, 4000, 16000 and 60000 data bytes all arrived with the data intact, both ways.
- The posts kept flowing through two Proving Grounds matches, though MCC lowers the chat permissions from 0x1F to 0x10 in a game.
- Round trip: about 0.4-0.6 s (the friend's side's figure). The host's figure of about 2.5-3 s includes the wait for the friend's next 3 s post.
- Reach's vote and countdown parameters didn't change in the custom lobby. They stay unused, and Party chat text is the channel.
- On the friend's PC, Reach's session counted 8 members and 3 peers in a match with bots.

### No drive sample high over the floor: flying is no owner route, 2026-11-18

The owner: "Does my new routines in vehicles look good on breakpoint and boneyard?" ("not boneyard, I did renegade"), then "Yea fix it".

- Found (offline, the maps' terrain and `Terrain.vnav`): Renegade (Forge World `vf1ed8bb6`) 1,676 of the 1,686 route cells on the vehicles' ground; 43 drives between its route ends 99% on the routes (66% without them), all arriving. Breakpoint (`veae7463a`): its ground routes one network base to base (2,303 cells), 21 drives between the vehicles' spawns 90% on them (86% without), all arriving; but 1,949 of its 4,260 route cells 5-19 u over the floor, one track over the whole map where people fly (1,556 within 1 u of a flown cell, at its height): the owner's flying saved as drives (which way the flight came in as a drive not found: the kinds read as aircraft). No floor within 1 u of them, so never the bots' roads; drawn orange in the LiDAR view. Also: the Elite Wraith and Ghost on Breakpoint spawn on a 70-cell piece of vehicle ground 3.5-4.7 u off the rest (a bot there drives about 2 u and stops, with or without routes; left to a LiDAR drive off that pad).
- `tools/lidar.py` `RideWatch`: a drive sample over `DRIVE_MAX_H` 3 u over the floor under it (`Terrain.height_over`) is not kept (live_bots and LiDAR mode alike; a ground vehicle's bump or short jump within it still is). The cells already saved are left in rides.json.
- Validation: `tools/test_owner_routes.py` (new: a LiDAR-mode drive 11 u up saves nothing; on the ground and a bump within 3 u kept). All 859 regression tests pass. Untested in a LiDAR run.

### Service Record: a bot's difficulty set on the site, 2026-11-18

The owner: edit a bot's difficulty on the website and have it change in the game as well.

- `tools/service_record.py` `set_bot_difficulty`: writes the bot's `saved=<difficulty>,<style>,<name>` line in `native/bin/bot_pool_saved.ini` the way the BOTS panel does when its difficulty changes (`bots_panel.cpp` `bot_pool_remember`): Bot Matchmaking seats the bot at that difficulty. Its play style is kept, except that Demon never drives (wheelman becomes any). The bot's tier also changes in the lobby list's `bot=`/`ffbot=` lines of `botcore.ini` when it is on it. The bot's line is added if it has none, and the names match without case. "" takes the saved line out, so the bot plays at the lobby's difficulty again (the lobby list is left). It is refused while MCC runs, because botcore holds both files and writes them back; the change is played from MCC's next start. A copy of each file as it was is kept as `.before_site_edit`. `Paths.botcore` is new.
- `tools/service_record_edit.py`: `POST /api/bot-difficulty {"name", "difficulty"}`, for bots the built site lists only (409 while MCC runs), then the site rebuilt.
- `tools/service_record_site/app.js`: in edit mode each bot's card has a Difficulty picker (The lobby's, Easy ... Mythic, the panel's names) that saves and reloads the page. The profile shows the panel's names (Legendary rather than "Top"; "The lobby's" when none is saved).
- Fix, the same day, after the owner saw a bot's difficulty shown as "The lobby's": most bots (573 of 753) have no saved difficulty and play at the lobby's "for everyone" difficulty, which the page did not name. Three bugs also showed: saved lines were matched by exact case (Death Adder is saved as "Death adder", so the site showed "The lobby's" while the game uses Demon); names the site lists with a trailing space ("ii Toxic Moose ") could not be saved; and a bot already in the lobby list showed nothing about its seat there. `pool_name` (the panel's `pool_clean`) and matching without case now find and save names as the game does, keeping the line's own spelling. `read_lobby` reads `botcore.ini`'s `difficulty=` (data.js `lobby_difficulty`, e.g. Mixed) and the lobby-list tiers (`lobby_tier`). The page shows "The lobby's (Mixed)" and, for a bot in the lobby list, e.g. "Easy in the current lobby". 181 bots now show a saved difficulty (180 before). A live save and removal for "ii Toxic Moose " left both files as they were.
- Validation: `tools/test_bot_difficulty.py` (new: the panel's file format and line endings kept, style kept, Demon not Wheelman, both lobby-list line kinds, a new line, "" removal, bad names and difficulties, refused while MCC runs; the route's 403/400/409/200). `test_service_record.py` (33), `test_home_state.py` (2) and `test_bot_emblem.py` (2) pass. In the browser on the editor with MCC closed, Lone Fox went Legendary → Mythic: both files showed `mythic` and the page reloaded showing Mythic. Back to Legendary left both files byte-identical to before. No sideways scroll at phone width. Not tried in a match: the bot seated at the new difficulty from MCC's next start is untested in game.

### Service Record: home states set by hand, 2026-11-18

The owner: edit a bot's or player's location; saving refreshes the site so it lists them in the right places.

- `tools/service_record.py`: `load_home_states` / `save_home_state` keep the owner's picks in `native/bin/service_record/home_states.json` ({name: state code}, only codes `states.json` lists; "" goes back to the state the name picks). The build uses a pick over `home_state` and marks it (`state_set`).
- `tools/service_record_edit.py`: `POST /api/home-state {"name", "state"}` for any name the built site lists (bots and people), then the site rebuilt.
- `tools/service_record_site/app.js`: in edit mode each record card has a Home state picker (states grouped by region), Save and, for a state set by hand, Back to its picked state; a save reloads the page, so every state board, region and the Hometown Hero badge use the new state. The placements and state-board notes say when a state was set by hand.
- Validation: `tools/test_home_state.py` (new: save, back to the pick, a bad state, a bad saved entry, the route's 403/400/200 for a bot and a person). `test_service_record.py` (33) and `test_bot_emblem.py` (2) pass. In the browser on the editor, Pistol Queen was moved Vermont to Texas: the page reloaded with her in Texas (state, region, the Texas count), then Back to its picked state returned her to Vermont. The owner's page gets the picker too; no sideways scroll at phone width.

### Service Record: the emblem editor's preview no longer stacks old picks, 2026-11-19

The owner: picking a new background (or primary colour) left the old one showing under it, piling up with each pick; the saved emblem was right.

- `tools/service_record_site/emblem_editor.js` `redraw`: the preview canvas is cleared before the new emblem is drawn. `drawImage` blends over what is there, so wherever the new emblem is see-through, the earlier picks showed. Saves were never affected (the editor saves the ids, and the server draws the picture fresh).
- Validation: in the browser on the editor, background A → B → A and primary colour A → B → A each give a pixel-identical preview (difference 0), while A and B differ. Nothing was saved.

### Service Record: an emblem editor for each bot, 2026-11-18

The owner: an emblem editor on the site for each bot, like MCC's own (foreground, background, primary/secondary/background colours, secondary on or off), in edit mode only. A saved emblem should show on the site, in MCC's lobby and in matches.

- **`brain/emblems.py`:**
  - **Saved picks:** `native/bin/emblems/chosen.json` (not in git), with `chosen`, `valid` (every id checked against the catalog; secondary may be OFF), `save_chosen` and `emblem_for` (the bot's pick, else its roll).
  - **`export` uses it:** the lobby's `<name>.ids` and the `<name>.rgba` picture follow the pick.
  - The other chat's `draw()` is untouched.
- **Other readers:**
  - `brain/looks.py emblem_of` uses `emblem_for`, so `tools/play.py` adds the bot to a match with its pick.
  - `tools/emblems.py sheet` draws picks too.
  - A bot with no pick gets exactly its roll as before.
- **`tools/service_record_edit.py`, new routes:**
  - `GET /api/emblem-catalog`.
  - `GET /api/emblem-art/<layer>.png`: only layer names the catalog has. The layer art stays on this PC and is never in the built site.
  - `GET /api/bot-emblem?name=`: a listed bot only, not a person.
  - `GET /api/emblem-editor.js`.
  - `POST /api/bot-emblem`: the five ids or `{reset: true}`. It needs the edit header and a bot the site lists; it saves, writes that bot's `.ids` and `.rgba` again, then rebuilds.
- **`tools/service_record_site/emblem_editor.js` (new):** served only by the editor, so it exists in edit mode alone.
  - **Picking:** foreground and background grids with thumbnails, three palettes of MCC's 30 colours, and a secondary on/off switch.
  - **Live canvas preview:** layered as `compose` does, beside the bot's rolled emblem.
  - **Buttons:** Save emblem, and Back to its rolled emblem.
- **`app.js`:** an "Edit emblem" button on a bot's record card in edit mode (not for a person). It loads the editor and opens it under the card.
- **Validation:**
  - **Tests:** `tools/test_bot_emblem.py` (new, 2 tests). It covers picks and reset, names in any case, `emblem_of` and the `.ids`, refused bad ids, and a bad saved entry left out. On the editor routes it covers save, reset, a bad foreground, an unknown bot, a person, no edit header (403), the catalog, and art for unknown or `..` layer names (404). `test_service_record.py` still passes (33); `emblems.selftest` passes; `node --check` passes on both scripts.
  - **In the browser on the editor at localhost:8766:**
    - The preview matches the site's own emblem picture to within 0.27 of 255 per channel.
    - Picking the skull, turning the secondary off and choosing a cyan primary, then saving, wrote `chosen.json`, `Pistol Queen.ids` (`2 536 14 31 29`) and the picture; the site showed the new emblem after its rebuild.
    - "Back to its rolled emblem" restored `57 536 23 10 29` and an empty `chosen.json`.
    - No sideways scroll at phone width.
  - **Not tested in MCC:** a saved emblem should show from the bot's next lobby or match. The bots panel keeps the pictures it already loaded, so its old picture may stay until MCC restarts.

### Reach Demon and Mythic: Halo 4's team play, the other bots' difficulty, the peek as he looks away, 2026-11-18

The owner, on how he plays low bots: "I know if a low level bot won't push, or how long it takes for them to look away. Or I hear gunfights and push to that and usually steal others kills", after "if we could give the daemon bot the ability to always know the attributes of the other bots and the difficulty, I think that could also help it", then "Yea add all of that to reach demons and mythics".

- **Halo 4 Demon's fight odds and team play now run for Reach Demon and Mythic too** (`Bot.team_demon`; Halo 4 Demon as before):
  - the odds break-off and "not taking on a man it would not beat", and dropping a hunt into a group;
  - the trade rule, re-peek with a full shield, one-shot callouts, instant trades and third party (`team_play`);
  - regroup cover, chasing a man out of sight only in a fight it wins (`chase_ok`), the team's sightings as beliefs, the two-in-view press and the retreat juke.
  - Halo 4's Boltshot swap, melee range and power grab stay Halo 4's (`h4_demon`).
  - Mythic gets Demon's cover search where a map has no painted cover (`cover_from`), so its break-offs have somewhere to go.
- **Reach's guns in the odds** (`brain/odds.py REACH_GUNS`, `kill_time(..., game=)`): DMR 1.2 s from full (the fastest quarter of 31 measured one-on-one kills in the 4 Reach traces with kill rows: 1.21 s). The other guns are Halo 4's analogue and not measured yet.
- **Every bot's difficulty is known to the team** (`BOT_PROFILES`, posted by every bot in `share_sightings`).
  - In Reach, an enemy bot's share of the odds' pace is set by its difficulty (`odds.acc_of`, `REACH_ACC`), from Easy 0.17 to Demon 0.52; a person is 0.8. These are first estimates, not a replay calibration: each difficulty is scaled by the square root of its K/D against the owner's, from `tools/death_autopsy.py`.
  - Mythic's own pace is 0.9, Demon's 1.0 (`own_acc`).
  - **A weak enemy** (`Bot.weak`: under `DANGER_ACC` 0.3, i.e. Normal and below, Blind and Tactician, with a posted profile) does not count as the "second man" in `demon_break_second`, and a hurt Demon may still take on a man in view when every man in view is weak (`demon_no_new_fight`).
- **`Bot.peek_timing` (new; `PEEK_*`), Reach Demon and Mythic:** when its top choice is a hunt or push onto a man out of its sight, and the team sees him (`TEAM_FACING`, posted by whoever has him in view, under 0.5 s old) facing its way within 35° and within 25 u, it waits where it is (`PEEK_WAIT_SCORE` 3.45) until he looks away, 2 s at most.
  - It never uses a facing nobody on the team sees (no wallhack).
  - It doesn't wait for a weak man.
- **Validation:** `tools/test_reach_team_demon.py` (16 tests):
  - who has the team play: Reach Demon and Mythic, Halo 4 Demon; not Reach Legendary or Heroic, not Halo 4 Mythic;
  - Reach's guns, and a difficulty's pace (the same man as an Easy bot gives more than twice the odds of a Legendary);
  - Reach Demon and Mythic one shot don't peek a full man; Reach Legendary is unchanged;
  - a weak second man is ignored and a Legendary one is not; a hurt Demon takes on a weak man;
  - peek: waits while he looks this way, goes when he looks away or after 2 s, not for a weak man, not without a team sighting; Mythic waits; Reach Legendary and Halo 4 do not.
  - `test_demon_odds.py`'s "Reach Demon unchanged" checks now check Reach Legendary. `test_demon_anticipate.py`'s radar-dot nearness test holds `chase_ok` aside, because the ported "no friend of his near" check would trip on its dot.
  - All 858 regression tests pass. **Untested in a match;** the odds thresholds are Halo 4's calibration.

### Service Record: clan rewards, 2026-11-18

The owner: make people and bots want to join a big clan (a clan's cR stays its members' added up), "add everything you stated", and each item changeable in edit mode so he can test it himself. Site only, nothing in game.

- **`tools/service_record_site/clan_rewards.json` (new):** the ten rewards and 10 clan weekly challenges. Each look reward lists the clan ranks that unlock its levels, on the players' ladder with every step ×10.
- **Looks:**
  - **Card frame:** a coloured, glowing, then moving edge on the Clans card.
  - **Tag colour:** cyan, gold, then gold glow, on every clan tag on the site (leaderboard, carnage reports, player card, profile).
  - **Clan banner:** five CSS-drawn banners behind the clan page header, no art.
  - **Member ribbon:** "Member of [clan] · rank" on each member's card.
  - **Clan emblem:** a member's emblem, picked in edit mode; the top member's until then.
- **Play:**
  - **Clan weekly challenge:** one a week, drawn by the date, every member's Reach matches of that week together. Finished, its cR is added to the clan's cR; members' own cR is unchanged.
  - **Rivals:** the clans just above and below, with the cR gap.
  - **Hall of fame:** top member, best K/D (10+ games), most games, this week's MVP.
- **Prestige:**
  - **History:** first match, ranks reached, games played milestones, weeks as the top clan.
  - **Top-clan crown:** on the first clan's card, title and tags.
  - **How the history is dated:** worked out from the counted matches. A rank's date comes from the clan's cR growing match by match, with commendation and personal challenge cR spread over the matches alike, so its last step is the rank the clan holds now. A reset clears it too.
- **`tools/service_record.py`:** `load_clan_table`, `load_clan_settings`, `clan_rewards`, `clan_block`, `match_credits`, and the saves `save_clan_rewards`, `save_clan_week`, `save_clan_emblem`. `data.js` gains `clans`, `clan_week` and `clan_rewards`.
- **The owner's changes** go to `native/bin/service_record/clan_settings.json` (not in git).
- **Edit mode:**
  - **Clans page:** each reward on/off and its unlock ranks, with "Back to defaults"; this week's clan challenge picked by hand.
  - **Clan page:** a preview that shows the clan at any rank and with the crown on or off, on every page until reload (never saved); the clan emblem picker.
  - **`tools/service_record_edit.py`:** `/api/clan-rewards`, `/api/clan-week`, `/api/clan-emblem`. An emblem must be a member of that clan.
- **Validation:**
  - `test_service_record.py test_clan_rewards` (new). All 33 tests in the file pass, and `node --check app.js` passes.
  - **In the browser on the editor:** the rewards list and clan challenge show on the Clans page. The preview showed the frames, gold tag, starfield and grid banners, ribbon, emblem and crown. The hall of fame, rivals and history were checked with in-page sample numbers, since every clan is near 0 after the reset.
  - **Saves:** the three saves were checked against the live editor: a falling unlock and a non-member emblem are refused. All were put back to defaults.
  - No sideways scroll at phone width.
  - Not checked yet with real clan progress from matches.

### Service Record: the Challenges page, 2026-11-17

The owner: "Add these to the achievements page, But rename it to challenges. And we will make a plethora of daily and weekly challenges", with 4 dailies and 1 weekly counting toward the rank.

- **`tools/service_record_site/challenges.json` (new):** 52 daily and 18 weekly challenges.
- **How they are drawn:** each day's and week's are drawn by the date (`challenge_pick`). A day runs local midnight to midnight; a week starts Monday.
- **Credits:** a finished challenge's cR counts in the rank (`ranks.json challenge_credits`), worked out again from the counted Reach matches at each build.
- **The page:** a player's Challenges page (old `achievements` links still work) with the time left, cR and progress for each.
- **Handoff:** `docs/CHALLENGES_IN_GAME.md` is a short note for adding them to the game from the site's build output.
- **Validation:** `test_daily_and_weekly_challenges`, checked in the browser.

### Demon steps out of a second man's sight; Forge pieces in the analysis line of sight, 2026-11-18

The owner: "a good player knows how to shorten angles, or force an angle that allows them to make a 2v1 their advantage", then "I think we should add line of sight checks to the forge world pieces and then make that rule at the same time".

- **Forge pieces:** in a match, the bots already see a Forge layout's pieces. `live_bots` switches to the layout's own terrain once it identifies the layout (`map variant ...: 143 pieces in the nav`). Only the analysis tools read the bare canvas, because a recording never said which layout it was.
  - **Now the recording says:** `tracefmt.meta_line(..., variant=)` writes `"variant": "<map>/variants/<id>"` into each bot's meta row (`live_bots`), and `"map"` stays the base map's name.
  - **Older recordings:** `death_autopsy.variant_of` finds the layout whose `variant.json` was last (or first) seen at the recording's start minute. `terrain_los` reads the line of sight on that layout, else on the base map.
  - **Checked on Forge World 20261117-205817 (`v079e8abd`):** of 2916 pairs of real player positions, 63% were clear on the bare canvas and 14% with the pieces. All 622 moments the live game recorded a man with an enemy in his sights are clear on the layout's terrain too.
- **The numbers with Forge pieces** (4 Reach traces): the owner was seen by 2+ enemies at once 22.1 times per 10 minutes alive, the Demon 29.5 (it was 33.7 vs 31.9 with the bare canvas). He died in 12% of those moments, the Demon in 26%. A per-moment pass (every world row) gave 17% of his 47 and 24% of the Demon's 157. Through such a moment he was shooting a median 50% of the time, the Demon 100%: it stays in the duel with the second man on it. The earlier "4.3 s" for the Demon's fatal Forge World moments came from the missing pieces.
- **`Bot.demon_break_second` (new; `DEMON_WATCH_*`, `DEMON_BREAK_*`), all games, on foot:** when two or more men in view have the Demon in their view (within 40 u, facing within 52.5° of it), it drops its fights and hunts. It goes at `DEMON_BREAK_SCORE` 3.55 to the nearest spot within 1-6 u, a short walk off, that no watcher but the man it fights has a line to.
  - In each ring it takes first a spot the man it fights still sees (the 2-on-1 becomes a 1v1, and the retreat keeps shooting him). Otherwise it takes one nobody sees.
  - It keeps the spot 1.5 s while that spot stays out of the others' sight.
  - **The usual rules decide** with a kill about to land (`finishing`), a watcher within 2 u, no such spot, or while the recharge hold runs. It does not apply in a vehicle, while carrying, on a loose objective, or in Race and Infection.
- **Validation:** `tools/test_demon_break_second.py` (7 tests): it steps 1 u off, out of B's sight, still in A's; the spot is kept; the second man looking away, a kill about to land, a man on it, or no hidden spot leave the fight; Legendary and Race are unchanged. `test_death_autopsy.py` has a new test for the meta's layout. All 842 regression tests pass. Untested in a match.

### Death autopsy: the owner's deaths beside every bot tier, 2026-11-18

The owner: "Just as you have the demon autopsy report, you also have one for me, and then we can compare the demon difficulties to what I do as well."

- **`tools/death_autopsy.py` now reads everyone from the world rows** (4 a second), so a person and a bot are measured the same way:
  - the fatal fight and the shield and health going in;
  - "saw him": the killer in his field of view (105°, the owner's MCC setting) with a line of sight on the map's terrain;
  - "took the fight": an enemy in his sights in the second before the first damage.
  - A bot's own rows still add its goal.
  - A trace's one person is "you"; with two or more people they are "people".
- **The default run is the comparison:** you and each bot tier side by side.
  - Rows: deaths, K/D, deaths per 10 minutes alive, each cause's and condition's share, and the killer's distance and fight length.
  - **Exposure:** the share of time alive on foot that 0, 1 or 2+ enemies within 40 u had him in view with a line of sight.
  - **2-on-1 moments:** each time 2+ saw him at once, how often per 10 minutes, how many he died in (or within 2 s after), and how long they lasted.
  - `--tier demon|top|you|...` gives one group's full report.
- **What it shows**, from the 4 Reach traces with kill rows (16 of the owner's deaths, 48 Demon):

  | | you | Demon | Legendary |
  |---|---|---|---|
  | K/D | 5.00 | 2.15 | 1.51 |
  | deaths per 10 minutes alive | 8.8 | 11.6 | 14.5 |
  | deaths with 2+ enemies shooting (first cause) | 25% | 62% | 41% |
  | 2-on-1 moments per 10 minutes alive | 33.7 | 31.9 | 49.0 |
  | died in a 2-on-1 moment | 11% | 25% | 21% |

  He is seen by two at once as often as a Demon; he lives through it more than twice as often. His deaths are mostly lost 1v1s (44%, median 2.2 u).
- **Validation:** `tools/test_death_autopsy.py` rewritten for world rows (2 tests: a Demon outnumbered, the owner started hurt, a Demon shot from behind; the 2-on-1 that killed it; the comparison and the "you" report; the 0 shield read counts as full). All regression tests pass. The terrain line of sight leaves Forge pieces out, so Forge World reads a little more "seen".

### Proving Grounds stays up while the game starts, 2026-11-18

The owner: "is there a way for it to leave the bot matchmaking screen up as the game starts?" After the vote, Proving Grounds went away for a moment and MCC's custom game lobby showed before the load.

- **Why:** MCC's countdown greys the lobby's OPTIONS tile. The overlay's lobby probe (`probe_lobby`) looks for that tile's frame line, so it read the lobby as gone (log: `OPTIONS 0 ... -> not seen` right after `MCC's countdown started`). Proving Grounds then hid and moved to the match stage while MCC's lobby counted down.
- **`native/overlay.cpp`:** `pg_hold` keeps Proving Grounds drawn during its launch. It holds while Halo: Reach's menus are up (`mcc_menu_state() == 0`), whatever the probe reads. `pg_env.in_game` (new) passes MCC's menu state on.
- **`native/proving_grounds.cpp`:** the launch ends when MCC is in the game (`e.in_game`), not when the lobby probe fails. It falls back to the old rule after a minute without a game, and logs it.
  - `pg_launching()` (new) tells the overlay the launch is on.
  - The "GAME STARTING" screen no longer fades in a second time when the launch begins, and it says "Loading..." instead of "MCC's lobby is counting down...".
- **Validation:** `botcore_pg14.dll` and the preview build. Untested in game: whether MCC's loading screen comes before or after its menu state turns to a game (if before, Proving Grounds' screen covers the load as well).

### Death autopsy tool; hurt Demons start no new fight, 2026-11-18

The owner asked for ideas to make a Demon "that puts it staying alive as most important", then: "Let's start by making the tool. And then the full shield bullet also."

- **`tools/death_autopsy.py` (new):** every recorded death of a bot, from the traces with kill rows (`tools/kill_record.py`). For each death it finds:
  - the fatal fight (the bot's own damage since its last 2 s without any) and the shield and health it went in with;
  - the enemies whose damage is on the body, and whether it saw the killer by eye before his first damage;
  - its goal when the fight started and when it died, what killed it, how far off he was, its time alive, and the killer's own shield.
  - It gives each death one cause (no killer, vehicle, outnumbered, grenade, never saw him, started hurt, power weapon, lost a 1v1), counts every overlapping condition, and gives K/D and deaths per 10 minutes alive. `--tier all` lists the tiers side by side; `--list` prints one line per death.
- **What it found** in the 4 Reach traces with kill rows (Nov 15-17), 48 Demon deaths (K/D 2.15, 11.5 deaths per 10 minutes alive; the other tiers 18):
  - 32 of 48 (67%) had 2 or more enemies' damage on the body. For the other tiers it was 23-60%.
  - 6 went into the fight under full shield (median 0.89), and 8 never saw the killer first.
  - 16 were caught on their way to something else, not in a fight they took. 9 were lost 1v1s, at a median of 1.3 u (Melee is its second killer).
- **`Bot.demon_no_new_fight` (new; `DEMON_FRESH_COVER_R`), all games:** a Demon that is hurt (within `SHIELD_BACK`), with its shield under `DEMON_FULL` 0.95 and in view only of men it is not fighting yet, opens no new fight.
  - It drops its fights and hunts and goes into cover from those men (`cover_from` / `hidden_spot`, at most 10 u off) at `DEMON_RECHARGE_SCORE` 3.5. Once it is out of their sight, `demon_recharge`'s hold keeps it there until the shield is full.
  - The usual rules still decide in these cases: the man it fights (its target, the one carried through a hunt or retreat, the last to hurt it within 10 s), a man within `DEMON_STAND_R` 6 u, a shot in the last 1 s, and no cover in reach (turning away in the open is a shot in the back).
  - It does not apply in a vehicle, while carrying, on a loose objective, in Race or Infection, without shields, or while the recharge hold already runs.
- **Validation:** `tools/test_demon_no_new_fight.py` (9 tests: cover from a new man, out of his sight; full, it fights; its own man, the man who hurt it, a man on it, a fresh hit, and no cover are all left to the usual rules; the recharge hold takes over; other tiers and Race unchanged) and `tools/test_death_autopsy.py` (2: three deaths, three causes; the 0 shield read counts as full). All 834 regression tests pass. Untested in a match.

### Bot simulation: the pool's bots play matches of their own for the Service Record, 2026-11-17/18

The owner: bots "only play when I play and its against me", so a bot gets a game or two a session while he logs 8-10; "I want to implement a system like this so that the website tracker gives bots a chance to keep up", true to the players and the bots. The design was agreed with him over five rounds of questions: `docs/BOT_SIMULATION_PLAN.md`.

- **When:** a round as each Proving Grounds match of his ends (after that match's own build, so the credits screen is not delayed). Also on demand: a SIMULATE MATCHES menu row (Left/Right 1-20 rounds, A/Enter plays) and a "Play rounds" form in the site's edit mode (`/api/simulate`). `sim.after_match=0` in proving_grounds.ini turns the after-match round off.
- **Who:** every pool bot (people never), each at its own pace averaging a third of his games, with grinders three times as likely among Legendary, Blind, Mythic and Demon. Lobbies are built like his: Arena 4v4 or BTB 8v8 from proving_grounds.ini, clans together, teams balanced by skill, the same vote (`liking` / `bot_vote` ported) for map and gametype. Bots left unseated wait for the next round.
- **How a match plays (`tools/sim_engine.py`):** fight by fight.
  - Skill is a Bradley-Terry fit of who killed whom in his real matches, around each tier's start. It learns from real matches only, never from a simulated one.
  - Rates (fights a minute, assists, suicides, headshots, weapon mix) are each bot's own, shrunk toward its tier's.
  - Weapons and vehicles, with their respawn times, come from each map's own game files (objects.json; a Forge or Anniversary layout's .mvar). Power weapons are picked up and run out; bots board vehicles, gunners shoot, drivers splatter, and an empty vehicle can be hijacked.
  - All 10 playlist gametypes, with their objectives; score and time limits from his real matches by team size (Team Slayer 50 in 4v4, 100 in 8v8).
  - Medals follow Reach's rules on the kill-by-kill record (multi-kills in 4 s, sprees, Killjoy, Revenge, Avenger, First Strike, Wheelman, Splatter...), the rest at the rates real matches show.
- **Shown exactly like real matches:** each match is stored as a report and kill rows, and the Service Record reads them as it builds, so K/D, credits and rank, commendations, challenges, weapons, heatmaps and carnage reports all come out of the same code. Storage is `native/bin/service_record/sim.db` (SQLite: seed, engine, inputs, compressed report and kill rows, about 7 KB a match), and their ids are added to matchmaking.txt. bot_career's totals (the in-game career pages) include them, and `--reset-bots` / `--reset-all` cover them.
- **Site:** Today's Top 5 (best games by credits earned, his included) and Playlist Activity on the Bot Tracker. The credits screen still reports the newest match a person played.
- **Changed files:** new `tools/bot_sim.py`, `tools/sim_engine.py` and `tools/test_bot_sim.py`. Hunks in `tools/service_record.py` (build, collect, `write_last_match`, `today_block`), `tools/bot_career.py`, `tools/service_record_edit.py`, `service_record_site/app.js` and `style.css`, and `native/proving_grounds.cpp` (`stats_build`, `run_tools`, `sim_start` / `sim_poll`, the menu row). Built as `botcore_pg14.dll`.
- **Validation:**
  - `bot_sim.py --check` replays each of his 41 real two-team Reach matches 60 times: kills a player a minute 1.44 simulated vs 1.49 real; real K/D inside the simulated 90% band for 90% of 433 players; win-call Brier 0.21.
  - Medals per 100 kills are close to real ones (Revenge 7.6 vs 7.7, Avenger 5.9 vs 5.5, Wheelman 2.9 vs 2.1).
  - A round is about 25 lobbies in under a second.
  - `tools/test_bot_sim.py` (12 tests): a seed replays; kill rows equal the scoreboard; every gametype keeps its limits; Boneyard has vehicle and power weapon kills; people never play; clans line up; the pace average holds; storage and the site and career totals read it; a reset covers it; a stored match plays again from its inputs; the credits screen keeps the person's match; Top 5 and activity.
  - All 823 `tools/test_*.py` and the 32 `test_service_record.py` checks pass. The menu row was checked in the Proving Grounds preview.
- **Not yet tried:** a real match's round, the menu row in game, and the site button. Not yet run against the real store.
- **Utopie (Nov 18):** the owner swapped Paradiso for his own Forge map Utopie in 8v8 ("Remove Paradiso from the map rotation in 8v8 and replace it with Utopie"; `btb.removemap` / `btb.addmap` in his proving_grounds.ini). `bot_sim.py` MAP_FILES now names `Utopie.mvar`, so simulated 8v8 matches play it from his file (35 weapons, 11 vehicles, flag and bomb points read). The 12 `test_bot_sim.py` tests pass. Not yet seen in a lobby.

### Reach carriers drop the flag to fight when they would die with it, 2026-11-17

The owner: "Sometimes it feels like they just let me kill them for free because they ignore anything but running the flag, but at the same time I feel like they could get less flag caps if they drop to fight", then "Let's try to add that in. Not the strafe and movement on the way home ... everything else we can try".

- Found in four Reach CTF recordings (Launch Station and Aft Ship Nov 17, Forge World and Countdown Nov 13): 15 bot carriers were killed, every one walking on while an enemy came from 6-9 u to 2 u, most of them 6-22 u from home. In 12 of them 2-4 enemies were within 15 u, so a "one man only" rule would have caught 3. From first damage to death took 0.1-3 s. Three died from full health (a melee or an assassination), with no warning at all.
- The flag melee was already there (`plan`: a man within `MELEE_R` 1.25 u, one swing every 0.6-0.9 s). It does not drop a CTF flag. In these recordings carriers swung 21 times and killed nobody; why (the reach, the aim or the flag's damage) is not known yet.
- `brain/bot.py` `flag_fight_check` / `flag_fight_phase` / `flag_fight_scores` / `flag_fight_press` (new; `FLAG_FIGHT_*`, `FLAG_BACK_*`), Reach CTF and Stockpile, on foot:
  - **When:** hurt in the last 1.5 s, at a rate that empties its shield and health within `FLAG_FIGHT_DIE_S` 1.5 s and before it could walk home (`FLAG_FIGHT_SPEED` 2.5 u/s); more than `FLAG_FIGHT_HOME` 4 u from where it scores (CTF its order's point, Stockpile its goal); an enemy known in the last 1.5 s within `FLAG_FIGHT_R` 10 u. It is dying with the flag anyway, so the flag lies where it would have fallen.
  - **The drop:** the weapon switch (the key the Stockpile drop already uses) tapped 0.3 s, again at 0.8 s only while the weapon read still shows the flag. Still carrying after 1.5 s: the drop failed, and it carries on.
  - **The fight:** that man at `FLAG_FIGHT_SCORE` 3.3 (over carrying 3.0, regroup 3.0 and a committed fight 2.6-2.9). The flag at its feet is not taken again meanwhile.
  - **After:** the man dead, unknown for 1.5 s, or 8 s of fighting: back to the flag at `FLAG_BACK_SCORE` 3.1 while it lies within 20 u (12 s at most), taken as before. No new drop for 6 s after.
  - Not in a vehicle, and not in other games (Halo 4's carriers keep shooting their magnum) or modes.
- Tuned on the same recordings, replaying the rule at every moment of every carry: it fires before 9 of the 15 deaths at the first moment it could. With the 1.5 s horizon, 7 of its 11 drops came before a death and 4 on carriers that went on to live. A 3 s horizon gave 9 and 12, none gave 10 and 21. So it costs some carries that would have made it home; it should cut the free kills, not every carrier death.
- Validation: `tools/test_flag_fight.py` (new, 13 tests): dying far from home it taps and fights; it runs on when it would live, 3 u from home, with the man 25 u off, in a vehicle, in Halo 4, Halo 3 or Oddball; the fight, then back for the flag, then the 6 s wait; the man lost or 8 s of fighting; the flag gone home; a failed drop; the second tap only with the flag in hand; Stockpile; and through `Bot.plan` the tap is sent and the flag at its feet is not taken mid-fight, only after. All 811 `tools/test_*.py` pass. Not yet seen in a match: whether the switch drops a CTF flag (it is what drops a Stockpile flag, by the owner's Nov 13 note), how fast the gun comes up, and whether the drops win more than they lose.

### bot.py as it runs, 2026-11-17

`bf01fba` (Demon stays in cover) committed `brain/bot.py` with `def hidden_spot(s, me, threats):` left above `def demon_recharge` and its body after it, so the committed file does not compile. The working copy, saved before that commit and run in every match since, was right. `0515807` commits it as it runs; no behaviour change.

### Reach Stockpile: the flags found on Forge layouts (Pinnacle), 2026-11-17

The owner's bug reports from Pinnacle Stockpile on Forge World (TU STOCKPILE: 4 flags, random placement, collected every minute; recording 20261117-205817): "Bots all stuck here" (102 s) and "Bots cant play stockpile on pinnacle" (122 s).

- Found in the match's recording: the brain never saw a flag. Its objective list stayed empty for 49 s while the four flags lay on their stands. Bot 1 (blue) picked one up at 3.7 s, 4.5 u from its own goal; not counted as the carrier, it switched to its rifle at 11 s, which dropped the flag, and was killed at 13.2 s. That was the match's only carry.
- From 49.6 s the gun a bot dropped dying on a stand was taken for the flag's kind, and up to 17 dropped guns were "loose flags". Runners and escorts were sent to them and stood on them: three blue bots on one at (122, 186.5) from 60 to 90 s, below where the owner stood for the first report; a red bot on another at (139, 177) from 66 to 84 s. Around the first report the blue bots waited at the teleporter whose exit red stood on. 0-0 at both collections.
- Cause: Reach's reader learns the flag's kind from the first object seen lying on a flag stand (LiveH3 `flags_by_stand`), and never from a kind with an object on one of the map's weapon spawns, so that no gun on a stand is taken for a flag. Pinnacle's stands sit on weapon spawns: the rocket launcher's 0.15 u from one, the plasma pistol's 0.12 and 0.15 u from two, the magnum's 0.36 u from another. The flag counted as a gun; and once a wrong kind is learned, no other is.
- `brain/live.py` `LiveReach.OBJECTIVE_NAMES` (new): Stockpile's flags are named by the map's tag names (`objects\weapons\multiplayer\flag\flag`, `_own_name`), as Halo 4's and H2A's objectives already are (`_name_objectives`). With the flag named, no gun is learned in its place. Only Stockpile's set is named; CTF and Assault on Reach still learn by stand.
- Validation: `tools/test_reach_stockpile_flags.py` (new, 6 tests). They put Pinnacle's own stands and weapon spawns in a stand-in object table read by the real `LiveReach.objective_items`:
  - a flag beside the rocket spawn is found, and four flags are all found;
  - a gun dropped on a stand is no flag, over three reads;
  - a carried flag (third slot) names its carrier;
  - CTF's set is untouched;
  - with the names off, the old way misses the flag and learns the dropped gun (the bug).
- Against Forge World's own tag list, every index in the flag's block resolves to `flag`, and the DMR, rocket launcher and plasma pistol to their own names. All 798 `tools/test_*.py` pass. Not yet seen in a match: bots carrying flags home and dropping them in the goal on Pinnacle.

### Demon stays in cover until its shield is full, 2026-11-17

The owner: "They need to stay in cover and fully recharge their sheilds. currently they do break line of sight, but they seem to re challenge when the shields start to recharge, Not at full. Or even 75%".

- Found (13 Reach traces, Nov 12-17): of 125 times a Demon was out of every enemy's sight under 0.75 shield and unhurt for 0.5 s, 79 waited for a full shield. The other 46 went back in about 0.5 s later at a median shield of 0.56 (41 under 0.75): a hunt toward a tracker dot or the man it had fought (3.16-3.42), or a corner push (2.9-3.07), over the recharge holds (2.3-3.1). The full-shield re-peek rule (`repeek_rule`, Nov 8) runs only in `demon_odds_rules`, which is Halo 4's; Reach Demons had none.
- `brain/bot.py` `demon_recharge` (new, called late in `decide`), every game: a Demon hurt within `SHIELD_BACK` s, its shield under `DEMON_FULL` 0.95, out of every enemy's sight `DEMON_RECHARGE_ARM` 0.5 s, holds cover until the shield is full. No fight or hunt meanwhile, a man who comes into view included. It stays where it stands if no man known in the last 10 s has a line to it, else goes to cover from them (`cover_from`, `hidden_spot`), at `DEMON_RECHARGE_SCORE` 3.5 (over hunts, a trade 3.4, guns 3.15, pushes; under a losing fight's break 3.6). Still fought: a man within `DEMON_STAND_R` 6 u (in sight, or a dot under 0.6 s old). A shot in the last `DEMON_RECHARGE_HIT` 1 s leaves it to the usual rules. Not in a vehicle, carrying, on a loose objective, in Race or Infection, or without shields. Legendary, Mythic, Blind and the rest unchanged.
- Validation: `tools/test_demon_recharge.py` (new, 7: no hunt back out at 0.55 or 0.85, back to him at 0.95; a 0.3 s blink out of sight does not start it; a man who comes into view at 12 u is not fought, cover behind the wall from him; a man at 4 u still fought; shot 0.2 s ago, the usual rules; untouched past `SHIELD_BACK` counts as full; Legendary and Race as before). All 792 regression tests pass. Untested in a match.

### Proving Grounds: the challenges in game, connected to the Service Record, 2026-11-17

The owner, with the Service Record session's note on the challenges in game and a picture of Bungie.net's Halo: Reach Challenges page: "Make it correlate to our website as well. They have to be connected."

- **`tools/service_record.py write_game_challenges`:** each build writes `logs/service_record/challenges.txt` beside `data.js` from the same `challenge_table` and `challenge_progress`. It holds this week's weekly and today's dailies in the site's order (name, what to do, target, cR, icon, when the period ends) and each listed person's completed counts, challenge cR and progress on the live challenges. The game reads this file and works nothing out itself, so the site and the game show the same numbers.
- **`native/proving_grounds.cpp`:** a CHALLENGES row on the menu ("done / live", with the GAMES INCLUDED block moved down 60) opens the page, laid out as Bungie.net's:
  - a header band per section, "Weekly Challenge:" or "Daily Challenges:", with "... Challenges Completed: N";
  - a dark row per challenge with the white icon, the name, what to do, the time left with its seconds in orange, the cR, and the bar with its tick and `n/need`, or Completed;
  - "Ended" once the time runs out before the next build, as on the site.
  - The icons are the site's own pictures (`logs/service_record/icons`, chosen as `app.js` NEON chooses them; assists is drawn from the site's own path), and cR is written with commas, as on the site.
  - The file is re-read when the site is rebuilt.
  - Y (or Tab) opens the same player's page on the site, `http://localhost:8766/#/p/<name>/challenges`, after starting the editor if needed (`tools/service_record_editor.cmd /startup`). Esc or B goes back to the menu.
- Validation: `tools/test_service_record.py` 32 passed (new `test_game_reads_the_sites_challenges`: `challenges.txt` equals the build's data, row by row, after a counted match). Compared in the preview against the site in the browser: the same weekly and dailies, times, cR, progress and counts. Built `native/bin/botcore_pg13.dll`. Not tested in game: the menu row, the page, and Y opening the browser over MCC.

### Proving Grounds: Reach's party list with player cards; the credits each match earned, 2026-11-17

The owner, with three Halo: Reach pictures (the full party list, its header picked with MY PARTY DETAILS, a player picked with their Spartan): "Only if its super similar if not spot on", then "Also possible add this level up bar after each game showing what earned you your xp. Before the carnage report? Or after whichever is cleaner".

- **The roster (`native/proving_grounds.cpp`, `roster`, `ros_details`, `ros_card`):** the menu's session list and the search and vote lobby lists are now one roster. Pressing Right (arrow or d-pad) or clicking the list gives it the focus. It then slides 0.22 s from MCC's place to Reach's (measured from the owner's pictures: rows ending at x 990, a tab over the header). The screen's own content steps aside, and Up and Down move through it. Left, Esc, B or a click away bring the screen back, with its focus as it was; the menu's GAME SIZE still takes Right (`g_lr_taken`).
  - **Header:** picked, it lights grey with Reach's pointer, and MY PARTY DETAILS (the menu) or LOBBY DETAILS stands beside it: Party Leader, Playlist, Player Count, Max Player Count, Game Mode.
  - **Rows:** a picked row is drawn a little larger and lit, its pointer reaching the panel. Its card shows the emblem, the name over the Service Record rank, the emblem again large and faint, and the Spartan in 3D: a bot's own Reach look (`bots_panel.cpp bot_figure`, as the bot card draws it; a bot with no profile gets one, as on that card), or for a person Reach's default Spartan in Steel (`person_figure`; MCC does not give the mod a player's armor).
  - **Card numbers:** Reach's own four lines with the Service Record's numbers: Daily and Weekly Challenges Completed, Kill/Death Ratio (in place of Armory Completion), Overall Commendation Progress. "..." where there is none.
  - `pg_env.figure` is filled by `overlay.cpp pg_figure` and the preview's `pv_figure`.
- **The Service Record side (`tools/service_record.py`):** `ranks.txt` gains games, K/D, win %, commendation progress, credits and the daily and weekly challenges completed. `commendation_progress` now computes the percentage once; the site's `app.js commProgress` reads the build's `comm_pct` instead of its own sum.
- **The credits screen (`S_CREDITS`, `credits_screen`):** after the carnage report, since MCC owns its post-game screens. When `mark_check` tags a match, `stats_build` runs `bot_career.py` and `service_record.py` in the background, so the match counts straight away instead of at the next game's start. `write_last_match` writes `logs/service_record/last_match.txt` with the player's credits before (what the last build had, `credits_seen.json`) and after, and lines by `ranks.json`'s worth: Game Completed, Victory, Kills, Assists, Medals, then Challenges and Commendations. When the lobby comes back from a marked match, the lines come in one by one, then the total, then the bar fills toward the next rank, with PROMOTED on a promotion. A, Enter, a click, Esc or B go on to the lobby, and it moves on by itself 6 s after the bar. No report in 20 s, or nobody listed played: straight on.
- `native/pg_preview.cpp`: three roster shots and the credits screen, the Spartans drawn with `model_view.cpp`. A bot without a profile is skipped there, so the preview never writes the owner's `bot_profiles.ini`.
- Validation: `tools/test_service_record.py` 31 passed (new `test_credits_of_the_last_match`; `test_game_reads_the_sites_ranks` checks the new columns). `test_bot_matchmaking`, `test_service_record_art` and `test_figure_snap` passed. Built `native/bin/botcore_pg12.dll`, and the preview's shots were checked against the owner's pictures. Not tested in game: the keys, mouse and pad in the list, the slide, the figure's turn, the credits screen after a real match, and the background build's timing.

### Banshee bombs as the owner's bomb kills had them; a run stays on its man, 2026-11-17

The owner: "I did the banshee bomb and boost like at the same time. Only record the ones where i got kills with the bomb", "C2IR when flying it didnt get a kill and died", then "Yes, fixes 1-3" (the boost into the bomb left for later: "Before boost bombing I want them to just play correctly inside the banshee first").

- `tools/owner_bomb_kills.py` (new): a match's trace and collect file to the person's Banshee bomb kills only (damage type 30) and his flight over the 3 s before each hit: speed, height over the man, range, nose pitch, heading off him (logs/owner_bomb_kills_<map>_<stamp>.json, a summary). No buttons are recorded in a match, so his boost shows as speed.
- Found (Boneyard 20261117-185650, his 21 bomb kills, about 0.5 s before each hit): range 3.8-17.3 u (median 11.5; 6 under 10 u, none past 20), 6.5 u over him, nose 0.71 rad down, within 0.07 rad of him, 4.6 -> 7.3 -> 8.7 u/s through the release. C2IR's one Banshee ride (77-99 s): never over about 12 u from the floor, median 3.7 u/s, its nose up most of its runs, its run's man changed 10 times among six, the cannons on 8 of 536 ticks; three DMRs killed it.
- `brain/bot.py` `air_pass`: Reach's bomb from `REACH_BOMB_R` 6-18 u (was `FUELROD_R` 10-31, which Halo 4 keeps). With the bomb ready, in gun range and under `REACH_BOMB_OVER` 6.5 u over him, the nose climbs toward that height over him (no bomb while it does); once there in a run (`bomb_dive`, the run's start) it dives onto him with no climbing back.
- `brain/bot.py` `drive`, `run_hold`: a pilot's run stays on its man out of sight for `AIR_RUN_HOLD_S` 2.5 s while another man is in sight (`air_keep` held him only with nobody else in sight).
- `tools/test_reach_boost.py`: the bomb-first test's run now from 15 u (its 29.4 u is past Reach's bomb reach now).
- Validation: `tools/test_banshee_owner_bombs.py` (new, 7: Reach bombs from 8.8 and 15.7 u, not 21.2; Halo 4 not from 8.8; low with the bomb ready it climbs and holds the bomb, not without one ready or in Halo 4; over him it dives and keeps diving lower down; the run's man held 1 s out of sight, let go after 3). All 785 regression tests pass. Untested in a match.

### A Banshee's bomb goes at his feet, 2026-11-17

The owner: "Before boost bombing I want them to just play correctly inside the banshee first. Does a driver of a banshee try to flick the banshee bomb at them? It should try to shoot it similarly like a rocket or fuel rod. At their legs or ground below them?"

- Found: with the bomb selected (`Bot.rod`), the pilot's aim stayed the cannons' (`plasma_rifle`, not an explosive): Reach at his chest (his place + 0.35), Halo 4 at its chest point. Only the lead was the bomb's (Reach's `REACH_BOMB_SPEED`). A bomb that went over his shoulder flew on past him.
- `brain/bot.py` `drive`: while the bomb is selected, from the cycle press through the shot, the aim is an explosive's (`Aim.step` gun `fuelrod`, `SPLASH`): Reach his feet (his place + 0.05); Halo 4 the floor under him (its place less `H2A_FEET`, + 0.05), a rider his vehicle's body. The lead stays the bomb's own (Reach 20 u/s; Halo 4 the cannons', as before). The cannons keep his chest. The nose swings down onto his feet in the 0.25 s between the cycle press and the shot (Reach).
- Validation: `tools/test_banshee_bomb_aim.py` (new, 2: a Demon pilot 15 u off and 9 u up, the bomb selected or not, Reach and Halo 4: lower with the bomb, on his feet within 0.05 rad, the same heading). All 778 regression tests pass. Untested in a match.

### Service Record: every pool bot listed, long lists in pages of 100, 2026-11-17

The owner: "why is it when reset all the bots list reset to 47? why isnt every bot on here", then (of listing every pool bot, 753) "we seperate it to top 100 and then it goes to pages. And we do top 100 for anything that has categories. With player search still in".

- Found: the site listed the bots of `bot_profiles.ini` (46) always, any other bot only once it had a counted match, so the reset dropped every matchmaking pool bot.
- `service_record.py read_pool_names`, `Paths.bot_pool`: every bot of Bot Matchmaking's pool (`native/bin/bot_pool.txt`, BOTS panel > Settings) is listed, at 0 until it plays: one entry a name (cut to 15, a repeat or `Name*N` once, `#`/`;` notes skipped), never a person's name. 753 bots on this PC, 754 names with the owner.
- `app.js` / `style.css` (`pager`, `pagedTable`, `holders`): the leaderboard, the state boards, each Ranks card's holders, the clans list and a clan's members show a page of 100 at a time: Top 100, 101-200 ... with Prev and Next; a page's numbers count from the top of the whole list. The leaderboard's and the state boards' Find a name searches every name, not the page, and a found name keeps its place.
- Validation: `tools/test_service_record.py` 29 passed in the working tree and 26 in this commit's own tree (the other sessions' new tests are not in it), `tools/test_bot_career.py` passed (`test_everyone_restarts_at_zero` adds the pool: a repeat, `Name*3`, a note and a long name read right, pool bots listed at 0 and not as people). The first build with the pool drew each new bot's figure once (541 s), later builds 2 s; `data.js` 0.4 MB. Browser: 754 names in 8 pages (701-754 last), "TheNoble" found from any page; a state board with numbers put in the page only (reload clears them) paged the same and searched with places kept (181st); an empty board shows its message (a stray "null" there found and fixed); a clan's members; phone width without sideways scroll. Not seen: a state board with real numbers past 100 (nobody has a counted match since the reset).

### Service Record: Proving Grounds matches only, 2026-11-17

The owner: "Why are stats recording to the website when bot matchmaking is turned off and still play with bots?", then, given a choice between splitting custom games out like Reach and dropping them, "Matchmaking only".

- The cause: the site counted every match MCC wrote a post-game report for (60 s or more played). Nothing checked how the match was started, and a Proving Grounds game's report is the same as any custom game's.
- **`native/proving_grounds.cpp`:** when a match Proving Grounds launched starts (`S_LAUNCH` to `S_PLAYING`, `mark_start`), it waits for MCC's report (`mpcarnagereport1_3528_0_0.xml`) to be written after that start. It then appends the report's `GameUniqueId`, the time and the playlist to `native/bin/service_record/matchmaking.txt` (`mark_check`, once a second from `pg_frame`). It gives up 30 s after the lobby is back with no new report (a quit game) and logs either outcome.
- **`tools/service_record.py`:** `load_matchmaking` reads that list (`Paths.matchmaking`). `collect` keeps only the matches it names, so a custom game adds no match, stats, rank credits or newly listed bot. People and pool bots are still listed at 0. No list yet means no matches. `bot_career.py` and `totals.txt` (the bots' in-game MCC Career pages) still count every match. The test World passes `matchmaking=None`, so the older tests still count every match.
- Built `native/bin/botcore_pg11.dll`. The running MCC has `botcore_standin1.dll`, which does not mark matches, so Proving Grounds matches count only after MCC restarts on pg11. Every match so far was already reset (Reset all), so none had to be sorted.
- Validation: `tools/test_service_record.py` 29 passed (new `test_matchmaking_only`: an unlisted custom game is in `totals.txt` but not on the site; a listed match counts alone; the game writes the file the site reads). `test_service_record_art.py` 11 and `test_figure_snap.py` 3 passed, and the Proving Grounds preview compiles. Not tested live: no match has been marked in game yet.

### Service Record: the owner listed, everyone's stats reset, a Reset all button, an edit mode that stays, 2026-11-17

The owner: "Are humans allocated to the website? I see myself in carnage reports but not on the board", then "Yes just me for now and also my ability to edit is gone?"; "purge the stats. Including mine from the website I want everyone to start at zero"; "add the Website owner (me) to have a permanent edit button"; "a reset all button so I don't ask you everytime? And store it the same as the edit".

- Listed people (`service_record.py load_people`, `person_names`): a person is listed only when named in `native/bin/service_record/people.json` (a list of gamertags, this PC only, never in git; today the owner alone), at 0 too when none of their matches counts. Their row is `person: true`: the Profile says "Listed as Player" with no Difficulty, the card has no Clan tag box (their tag is their own, from their reports), and the editor's `listed_bots` leaves them out, so `/api/bot-clan` never writes a person into `bot_profiles.ini`. A person gets a made-up home state like a bot (the state boards need one). Strangers stay off.
- `tools/bot_career.py --reset-all`: marks every match so far `all_reset`; no row of it counts (people's too) in `totals.txt` (the bots' MCC Career pages) or on the site (`collect` skips it). The matches stay in the ledger, as with `--reset-bots`, so nothing is counted twice and taking the mark off brings them back. Run once on the real ledger: 116 matches; copy kept as `ledger.before_reset_all_2026-11-17.json` and `totals.before_reset_all_2026-11-17.txt`.
- Reset all in the edit mode: `service_record.py reset_everyone` (a copy of the ledger first, `ledger.before_reset_all_<date>_<time>.json`; refused while MCC runs, since `tools/play.py` runs bot_career as a match starts), `service_record_edit.py POST /api/reset-all` (only with `{"confirm": "reset all"}`, the same this-PC / Origin / header checks); `app.js` / `style.css`: a red Reset all stats strip on the Bot Tracker page in edit mode, asking a second yes before it sends.
- Edit mode that stays: `app.js` keeps the switch in `localStorage` (it was per tab). The editor had gone because the desktop app stopped the preview server it ran in; `tools/service_record_editor.cmd` (new) starts `service_record_edit.py` in the background with `pythonw` unless port 8766 already answers, then opens the site (`/startup`: start only). The local `.claude/launch.json` (ignored) now attaches to it instead of starting its own copy.
- Validation: `tools/test_service_record.py` 28 passed (new `test_a_person_the_owner_lists`, `test_everyone_restarts_at_zero` with Reset all refused while MCC "runs", the copy kept and everyone at 0), `tools/test_bot_career.py` passed. Live: the owner listed (68 Reach games before the reset), then everyone at 0 with 47 players and no matches; Reset all clicked through the browser (second yes, done, copy kept); the edit switch kept over a reload; the launcher started the editor once and left it running on a second start. Not tested: a reset while MCC runs (refusal tested only in the test), the launcher at Windows sign-in (no Startup shortcut made).

### Proving Grounds: friends who join take a bot's seat, teams balanced around them, 2026-11-17

The owner, on a friend joining the lobby: "Just balance him to a team like normal matchmaking would".

- **`native/session_watch.cpp`:** reads the people in MCC's session from the session list. The rule comes from the
  owner's logs of real lobbies, with two friends who joined and two only on the friends list:
  - A person in the session has flags +0x12 and +0x13 set. A friends-list entry has only +0x14.
  - +0x6C is the team: the player 0, a joined friend 1, and in a match's list each bot its dealt team. +0x64 is the
    machine.
  - Bot ids are never people.
  - It keeps them only from a list that holds the player, and provides `mcc_session_people`, `mcc_player_team` and
    `mcc_session_has`. Changes are logged ("session list: people: ...").
- **`native/report.cpp`:** the look cache now covers a joined friend's emblem and nameplate as well as the player's
  (`mcc_person_look`).
- **`native/bots_panel.cpp` `bot_pool_matchmake`:** takes the other people and their teams. Each takes a bot's seat on
  his team and is counted (20 points) in the deal. One not on a team yet counts on the team with fewer people, and that
  team is written back. 8v8 with a friend is 14 bots, keeping the game's 16.
- **`native/proving_grounds.cpp`:**
  - **Your team:** `person_team` uses the team MCC's lobby has you on, and the last match's file only when that is not
    known.
  - **The deal:** `deal()` makes the lobby with the people in it, for searches and between matches.
  - **Live changes:** once a second before the launch, a friend joining, leaving or switching team deals the lobby
    again. Every bot that still has a seat keeps it, with its arrival and its vote; a new bot arrives and votes then.
  - **On screen:** friends are shown with their own emblem and nameplate, in IN LOBBY, on their team in the vote's
    roster and in MY GAME SESSION, and they count in the lobby totals.
  - **Votes:** a friend cannot vote in Proving Grounds, so for None of the Above's majority he counts as a player not
    voting.
- **Limits:**
  - Proving Grounds cannot move a real player between MCC's teams. It builds the teams around where MCC put him (MCC
    put the one joined friend in the logs on Blue).
  - The bots on a friend's own machine are the separate, still open sync problem.
- **Validation:**
  - `native/pool_test.cpp` test 26: a friend on Blue gives 3 + 3 bots, on Red 2 + 4, and one not on a team counts on
    Blue. 8v8 with a friend is 14 bots. With keep 100, a friend in costs one bot and out gives it back. All pool checks
    pass.
  - Preview with `PG_FRIEND=1` (a stand-in friend): the friend sits on Blue with his look, IN LOBBY reads 4/8 at once,
    and the teams are 4 and 4.
  - `build.bat pg10` builds `botcore_pg10.dll`, and all 81 `tools/test_*.py` pass.
  - Not tried with a real friend, so MCC's team for a friend while still in the lobby is read but untested live.

### Proving Grounds: each player's Service Record Reach rank beside their name, 2026-11-17

The owner asked for each player's rank from the Service Record site beside their name, as in the original Halo: Reach.

- `tools/service_record.py` `write_game_ranks` writes `logs/service_record/ranks.txt` with every site build: each listed
  player's name, rank step and rank. The one table stays `ranks.json` and the one credits sum stays this file's; the
  game reads the result and never adds up credits itself (the Reach-ranks-one-copy rule).
- `native/proving_grounds.cpp`:
  - `sr_rank_of` reads that file and reads it again when the site is rebuilt.
  - A bot the site has no record for has no credits, so it shows Recruit, as the site would.
  - The site's own insignia (`ranks/<step>.png`) sits in its own cell past each nameplate, as in the owner's picture of
    Halo: Reach's roster ("in its own little sub space"). The cell is a 44 square, 3 units apart from the nameplate, in
    the row's shade (team colour in team games), and is drawn even when there is no rank. Rows now end at the cell. The
    lobby headers, MY GAME SESSION and the invite list widened by 47 to fit it, and the nameplate keeps MCC's 332.
    Built as `botcore_pg9.dll`.
- Not shown: the player's own Reach rank. The site lists bots only ("People are never listed"), so there is no rank of
  theirs to show.
- **Validation:**
  - New test `test_game_reads_the_sites_ranks` (`tools/test_service_record.py`).
  - `test_reach_ranks_one_copy` still passes, and all 81 `tools/test_*.py` pass.
  - The preview shows the insignia.
  - `build.bat pg8` builds `botcore_pg8.dll`.
  - Not yet seen in game.

### Proving Grounds: rows at MCC's own size; the player's own nameplate and emblem, 2026-11-17

The owner asked for the rows to match MCC's nameplate and emblem sizes, and for his own nameplate and emblem to show.

- `native/proving_grounds.cpp`, `player_row`:
  - **Size:** the numbers come from MCC's MY GAME SESSION, as `overlay.cpp`'s bot rows use them (`ui_layout.h`). The
    nameplate is 332 x 44 and the team bar 12 wide, 14 to its left. The emblem is a 32 square at (9, 6). The tag is 15
    over a name of 21 at x 55. Rows are 50 apart, and the rank badge (46) sits left of the bar.
  - **Where:** the lobby columns, MY GAME SESSION (y 82 and 137 + 50 k, as MCC places them) and the invite list (720
    wide) all use it.
  - **Names:** a dark edge under each name, so it reads on light nameplates.
- **The player's look:**
  - `native/session_watch.cpp` keeps the player's id from MCC's list as `mcc_player_id`.
  - `native/report.cpp` `h_profile` keeps the five emblem numbers and the nameplate (+0x18) when MCC's own lookup answers
    for that id (`mcc_player_look`). It calls nothing MCC does not call itself.
  - `native/bots_panel.cpp` `player_emblem` draws the emblem once in the background to
    `native/bin/emblems/_player_<numbers>.rgba`. A changed emblem gets a new file.
  - `brain/emblems.py --draw <out> fg bg primary secondary background` composes any emblem from MCC's numbers.
- Not shown: the player's clan tag. MCC's string in the lookup is not read, so the name is drawn alone.
- `native/pg_preview.cpp`: a stand-in look for the person.
- **Validation:**
  - The preview renders rows at the new size with the stand-in emblem and nameplate.
  - `--draw` with real numbers draws, and with unknown ones refuses. The `emblems.py` selftest passes.
  - `build.bat pg7` builds `botcore_pg7.dll`, and all 81 `tools/test_*.py` pass.
  - Not yet run in game, so it is unconfirmed whether MCC's lookup is called for the player while in the lobby. The log
    line "report: the player's look" will show it.

### Proving Grounds: closer to MCC's own matchmaking screens; MCC's lobby hidden behind them, 2026-11-17

The owner asked for Proving Grounds to look more like MCC's matchmaking and for the custom game lobby not to show through.
The layouts follow screenshots of MCC's own Find Game and Match Found (vote) screens.

- `native/proving_grounds.cpp`:
  - **Background:** opaque, so MCC's lobby is no longer seen behind the screens. It is a deep blue wash over a faint
    picture of one of the playlist's maps, changing every 12 s with a fade. The vote shows your option's map and the
    result shows the winner's.
  - **Footer:** MCC's button prompts. The key glyph (Esc, Enter) or the pad's lettered circle (B, A) is chosen from the
    last input. A line of help for the focused control sits above them, replacing the boxed description. Back stays
    clickable.
  - **Find Game:** the status and a search clock (playlist and m:ss) are centred at the top. The playlist's card has its
    name low on the picture with the blurb under it. The middle column holds GAMES IN THIS PLAYLIST, a maps and
    game-types line, and PLAYLIST STATS, all one width.
  - **Match Found:** plain option rows (a thin map picture, the game over the map, the votes, the box). A chevron marks
    the focused row. The gametype icon is gone from the rows. The round's clock sits right-aligned under a divider line.
    The big picture's game name is in capitals.
  - **Player rows:** bots wear their MCC nameplate as the overlay's MY GAME SESSION rows do. Plain nameplates are
    tinted in the team's colour, and a shade sits under the name. A bot with no clan shows its name alone, not "[ ]".
  - **Menu:** PLAYLIST STATS moved level with the card, clear of the category tiles.
  - **Error wording:** the launch errors now say to leave Proving Grounds to see MCC's lobby message, since the lobby is
    hidden. Same change in `native/pg_lobby.cpp`.
- `native/pg_preview.cpp`: loads MCC's nameplates (MCC_ROOT, else the owner's Steam library), as `pool_test` does.
- **Validation:**
  - `build_pg_preview.bat` renders all six screens. The preview's stand-in backdrop no longer shows, and the nameplates,
    prompts and layouts were checked by eye.
  - `build.bat pg6` builds `botcore_pg6.dll`.
  - All 81 `tools/test_*.py` pass.
  - Not yet seen in game.

### The owner's LiDAR driving routes: the bots keep to them, 2026-11-17

The owner: "sometimes my routes wouldn't be ideal for bots that's why I created the lidar driving routes. So bots would try to always stick to those", then "Do all 4 options if possible".

- Found: a drive in LiDAR mode and one in a match went into `rides.json` alike, and a person's drive cost a bot 0.4 of its length (`ROAD_COST`): on open ground a cut under about 2.5 times shorter won. The paint tool's drive layers only make ground drivable, and no map has any.
- `tools/lidar.py` `RideWatch(owner=True)` (LiDAR mode, `main`): a person's drive there is an owner route, the drive row's sixth number (`[x, y, z, person, bot, owner]`; an older row reads as none). A bot's drive in LiDAR mode stays a bot's. `rides_view` and `tools/lidar_view.html` draw the routes orange; the Vehicle drives count reads "your routes / people / bots".
- `brain/maps.py` `rides_layers`: the owner's routes are `T.owner_drive`. On a map that has any, people's match drives stay drivable ground but are no roads (`T.people_drive` empty); a map without them keeps people's drives as its roads, as before (the drives saved so far cannot be told apart).
- `brain/terrain.py` `_build_vnav`, `owner_route_nodes`: an edge in a 1.25 u band round the route costs `OWNER_ROAD_COST` 0.12 of its length (people's roads 0.4), so a bot drives to the nearest route and along it unless the open ground is about 8 times shorter, and off it near its goal. The band is never left off the vehicles' ground for a wedge mark (the owner's vehicle blockers still win). `tools/wedges.py` counts the routes as driven.
- Fights unchanged: the run-over, a tank's or Ghost's gun run, the artillery's range and aircraft steer at the man, not along the vehicles' ground; a Warthog in a fight drives its way on, now along the routes.
- Validation: `tools/test_owner_routes.py` (new, 6: LiDAR-mode drives saved as routes and a LiDAR bot's as a bot's, a match's drive and an older row kept; the layers with and without routes; on Blood Gulch a route bent 0.45 of the way off the line between two open spots is driven round its bend and on to the goal, the plain drive about straight). All 776 regression tests pass. Untested in a match; the live view's orange layer not opened. No map has a route yet: each needs its routes driven once in LiDAR mode.

### Service Record: every weapon and vehicle listed, used or not, 2026-11-17

The owner: "I would like all weapons and vehicles to be on the site pages correlating to them even if the player has no kills with it."

- `weapons.json`: Reach's `arsenal`, the multiplayer weapons by damage type (Magnum to Fuel Rod Gun, both grenades, Melee, the Target Locator and both turrets); its `vehicles` as before. Damage types that are not Reach weapons (SMG, Battle Rifle, Brute Shot, the Sentinels' guns) and the other ways to die (a fall, the Guardians...) are left out of it.
- `service_record.py arsenal_keys`: the site's `arsenal` {weapons, vehicles}; every one named and given MCC's picture whether or not a bot has used it.
- `app.js` / `style.css`: a player's Weapons page has a Weapons and a Vehicles panel listing the whole arsenal, most kills first, the ones never used at Kills 0 | Deaths 0, faded and grey; "N of M used" in each panel's corner; another way the bot killed or died (a fall...) still listed with the weapons. A bot with no kill record yet sees the whole list at 0 with the note why. The "not matched live" mark only on a card with numbers. The state boards' Weapon and Vehicle menus list every one (opened on the first with a kill); one nobody has a kill with says so.
- Validation: `tools/test_service_record.py` passed (new `test_whole_arsenal_listed`); 26 weapons and 18 vehicles in the built site, all with MCC's pictures. Browser: 12ab34cd's Weapons page shows its 10 used first, the rest at 0 (a stray "0" after an unused card's name found and fixed); the boards list 28 weapons and 19 vehicle choices; Scorpion board: "No kill with the Scorpion is recorded yet."
### Service Record: four new commendations, MVP, Game Changer, Positive Thinking, Loyal Soldier, 2026-11-17

The owner picked these four on Nov 16 ("Mvp, Game Changer, Positive thinking, Loyal soldier") and sent their tier sheets on Nov 17: a title over six emblems, Iron to Max.

- `service_record.py match_deeds`, counted per match in `collect` (new `deeds` per player), as follows:
  - **MVP:** the most points (MCC's Score, ties too) in a Slayer game.
  - **Game Changer:** the same in an objective game (CTF, Assault, King, Oddball, Headhunter, Stockpile, Territories), where the Score is the objective's points.
  - **Positive Thinking:** more kills than deaths in a game played to the end.
  - **Loyal Soldier:** a game played to the end.
  - The points ones need MCC's report. "To the end" is the report's `mCompletedGame`, now read (`_int` takes a default; reports kept before count as finished).
- `commendations.json`: the four in the "pg" set with Iron-to-Max needs and cR. MVP and Game Changer are 5/25/100/400/1000/2000, Positive Thinking is like Victor, and Loyal Soldier is the long one at 25 to 8000. Their cR counts in the rank as the others' does.
- `service_record_art.py emblems <sheet> <key>` (new): cuts a tier sheet into `art/commendations/tiers/<tier>/<key>_<tier>.png` (448 squares).
  - The six are the sheet's biggest lit shapes that are not wide (not the title, its rules or the names), left to right. Each is lifted off the sheet's own black or night blue, its glow kept; any other count writes nothing.
  - It also makes the "not started" banner (Victor's Reach banner with the Silver emblem in grey) and keeps a copy of the sheet. The four of the owner's were cut (local art, not in git).
- Tests:
  - `test_service_record.py`: new `test_mvp_game_changer_positive_loyal`; the commendation tests now expect 23.
  - `test_service_record_art.py`: new `test_tier_emblems_from_a_sheet` (a made-up night-blue sheet).
  - `test_bot_matchmaking.py`: its overlay line updated for Proving Grounds' `pg_up`, missed when that was built.
- Validation:
  - All 80 `tools/test_*.py` pass.
  - The 24 emblems were looked at on a checkerboard (clean edges, glow kept).
  - Site rebuilt (7 matches since the bots' reset: Cosmic 1 MVP, three bots 1 Game Changer, the most Loyal Soldier games 2). The four cards were looked at in the browser pane, and the Gold MVP and Max Loyal Soldier banners framed in their colours.

### Service Record: clan tags set from the edit mode, saved in game; the clan on its own line of the player card, 2026-11-16

The owner: "add to the edit mode my ability to effectively change their clan tags on a player page basis ... add them to clans through the edit mode on the website so I dont have to ingame but it saves in game"; then, of "Gamertag -Clan" on the player page, "Make it more professional. Find a better spot for clan that keeps it relevant but not dirty".

- `service_record.py set_bot_clan`: a bot's clan tag written to `native/bin/bot_profiles.ini` the way `native/bots_panel.cpp profiles_save` writes it: only the clan field of the bot's own line changes (seed and looks set by hand kept, every other line and the line ends as they were); a bot with no line gets `bot=<name>,<seed>,<clan>` with the seed it already wears (`brain/looks.py seed_of`, botcore `name_look_seed`), as the panel's `profile_ensure` does. Tags as the panel's Clan tag box takes them (4 at most, no blanks or `, ; = [ ] |`); "" leaves the clan. Refused while MCC runs (`mcc_running`, tasklist): botcore reads the file at MCC's start and its panel writes its whole copy back, so the change is worn from MCC's next start (the 4v4/8v8 pool files remake themselves then, their source line holding the clans). The file as it was before each edit is kept beside it (`bot_profiles.ini.before_site_edit`). The site's `clan` now follows the profile even when it is blank (it fell back to the bot's last report's tag).
- `service_record_edit.py`: `POST /api/bot-clan` ({name, clan}), with the same this-PC / Origin / header checks as the clan name edits, only for a bot the built site lists; 409 while MCC runs. Site rebuilt after a save.
- `app.js` / `style.css`: in edit mode the player card has a Clan tag box (the site's clans to pick from, Save, Leave clan, a note that MCC must be closed). The card's "Name - TAG" is replaced by a quiet line under the name: CLAN label, the tag in an outlined chip, the clan's full name, linking to the clan's page; none for a bot in no clan.
- Validation: `tools/test_service_record.py` 23 passed (new `test_bot_clan_saved_in_game`: own line changed with its overrides kept, new line with the CRC seed, CRLF kept, bad tags refused, nothing written while MCC "runs"). Live through the editor with MCC closed: Lord117 saved as AYS left `bot_profiles.ini` byte-identical; a tag with a space and a name not on the site refused (400). `mcc_running` sees a running process (checked with explorer.exe). Card checked at desktop and 375 px (no sideways scroll). Not yet seen in game: a changed tag shows from MCC's next start.
### Service Record: see-through neon panels, every bot's own figure, Clans with your names, an edit mode, 2026-11-16

The owner: the player pages' panels "more transparent" with "the neon glow ... similar to the one from the header player card", then "make all of the backgrounds to the panel be see through", the same for the front pages; "take whatever the bots have set as their ingame model and add it to their player page by default"; a clan tab ("apply to clans and see their members", a clan rank "accumulative of all of their scores ... multiple it by maybe like 10x"), Apply a placeholder for now; "Allow me to be the only one to edit the site from my end. Like an edit mode", clan names first and the tag second, "a little clan description"; his "Spartan Over the Burning Wreckage" as the player pages' background.

- `style.css`: player pages' and front pages' panels, sidebar and tiles see-through with the player card's cyan neon outline and glow; the small boxes inside lightly tinted, the text shaded. Player pages draw the owner's `player.jpg` (`native/bin/service_record/art/backdrops`, not in git) fixed behind the whole page; the front pages keep the Noble movie.
- Figures (`service_record.py all_looks`, `bot_figures`): a bot with no Reach look in `bot_looks.ini` (a matchmaking pool bot with no profile) gets the look it wears in game, worked out from its name by `brain/looks.py armory_view` (the seed `native/pool_test.cpp` holds botcore to), into this tool's own `bot_looks_site.ini` (`bot_looks.ini` only read). Only new or changed looks are drawn (`drawn.json`): a build with nothing new is under 1 s, one new bot about 2 s (all 70 at once: 54 s).
- Clans (`app.js`): a Clans tab (search by tag, name, description or member), clan cR = all members' cR, the clan rank the players' ladder with every step x10 (from `D.ranks`: the one table), a clan page with its members linked to their records, the clan tag on cards and in the standings a link to the clan. Apply: a disabled "Coming soon" placeholder.
- Edit mode (`tools/service_record_edit.py`, new): serves the site at localhost:8766 and takes the owner's edits only (this PC alone, the site's own Origin, an edit header); a footer switch shows it, a clan's page then has its name and description boxes (`clan_names.json`, `clan_about.json` in `native/bin/service_record`, `save_clan_name`, `save_clan_about`), the site rebuilt after each. The site from its folder or any copy has no edit mode. Clans show the full name first and the tag second.
- Validation: `tools/test_service_record.py` 22 (+1: clan names, descriptions and the editor's origin check), `tools/test_figure_snap.py` 3 (+1: a pool bot's look is the mod's own). Checked live: a name and a description saved and shown, then my test text cleared; a save from another origin and one without the edit header refused (403); the folder copy has no edit switch; phone width without sideways scroll. `tools/test_bot_matchmaking.py` fails on uncommitted `native/overlay.cpp` work in progress (the custom-lobby files), not this change.
### Proving Grounds: offline Social Games for Halo: Reach (4v4 / 8v8, search, the vote, invites), 2026-11-16

The owner: "recreate the Social games menu for my own offline experience. We will name the new selection Proving Grounds", "select either 4v4 or 8v8", "a random 4-10 seconds of fake searching and then we connect to our lobby", the voting "where I can openly vote and the bots in my lobby will (vote)", "an 'invite player' function", then "Build the entire thing start to finish Map voting and all". His friend: random lobbies "broken up to balance teams every match (unless they're a stack/clan)", "Three maps/gametypes to vote for", bots voting on their traits and skill, "Roll a weighted dice". The engine under it is the lobby test below.

- **Where it is:** a PROVING GROUNDS tile (or **P**) beside BOTS in MCC's Halo: Reach custom game lobby (`native/overlay.cpp`, `ui_layout.h pg_tile_rect`). Its screens cover the lobby and take the mouse, keys and pad while they are up.
- **Screens** (`native/proving_grounds.cpp`, our own drawing over MCC's backdrop, no game art shipped):
  - **Proving Grounds:** GAME SIZE 4v4 (Arena) / 8v8 (Big Team Battle), INVITE PLAYER, games and categories included, playlist stats, MY GAME SESSION.
  - **Find Game:** "Checking for rejoins", then 4-10 s of searching while the lobby fills. A clan arrives together.
  - **Match Found:** three gametype-on-map options and None of the Above. Live vote counts, a 15 s clock (`vote_seconds=`), your vote with a click, Enter or A, and red and blue teams.
  - **Next game,** then MCC's own countdown.
  - Map previews and gametype icons come from `native/bin/service_record/art` when this PC has them (MCC's own pictures, the owner's icon sheet; not in git).
- **The lobby** (`bots_panel.cpp bot_pool_matchmake`, Bot Matchmaking's pool and format files):
  - your invited party is pinned to your team (`roster_point_balance` now takes pinned seats);
  - a clan stays whole on one team, not yours when it fits;
  - teams are dealt by points every match.
  - Between matches about 7 in 10 stay (a clan stays or goes together), new bots join, and the vote comes round again (the overlay's after-match step hands over to Proving Grounds).
- **The vote:**
  - **Options:** drawn from the playlist's gametypes by weight and its maps, only team games (MCC's own flag, checked against its SLAYER and CAPTURE THE FLAG, else a list of known team games), never the last game, and only pairs MCC's own pairing check accepts.
  - **Bot votes:** each bot rolls on its own odds. These come from its name (its favourite and least favourite maps, its liking of each kind of game, vehicles, map size), its play style (Wheelman: vehicles, Sniper: big maps, Rusher: small) and its difficulty (Demon, Mythic and Legendary sweatier: Slayer and the competitive maps).
  - **None of the Above:** a majority on it brings three new options with no veto, as in Reach.
- **The launch** (`native/pg_lobby.cpp`, replacing the test file): hooks the lobby screen's per-frame Update (vtable +0x58, `FUN_1404DECDC`, MCC's UI thread). There it:
  - keeps a copy of MCC's maps and gametypes (team flag included; `lobby_library.txt` once a session);
  - answers the pairing checks;
  - puts the winner in as MCC's own picks do, runs its apply step and presses its Start, unless a countdown already runs (`FUN_14034CEF8(1)`, `FUN_14034D1E4`).
- **Playlists** (`native/bin/proving_grounds.ini`, not in git, made on first change): `size=`, `vote_seconds=`, `party=` lines. `arena.gametype=NAME*weight` / `arena.map=` (and `btb.`) lines replace a playlist's own lists.
  - Arena: Team Slayer (TU Team Slayer DMR) most, SWAT, CTF, King, Oddball, Assault, Stockpile, 3 Plot Territories on Sword Base, Countdown, Zealot, Powerhouse, Reflection, Boardwalk, Anchor 9, Condemned, Asylum, The Cage, Pinnacle, Beaver Creek, Damnation, Hang 'Em High and Prisoner.
  - Big Team Battle: Team Slayer, CTF, Assault, Stockpile, Territories and Headhunter on Boneyard, Spire, Breakpoint, Tempest, Highlands, Hemorrhage, Paradiso, Ridgeline, Breakneck, Headlong and Timberland.
  - FFA gametypes in a list are left out by MCC's own team flag.
- **Also:**
  - `session_watch.cpp mcc_player_name` (your name in MCC's list, for your row);
  - `bots_panel.cpp bot_pool_names` and `hb_image_rgba`;
  - `native/pg_preview.cpp` with `build_pg_preview.bat` (the screens drawn offscreen to PNGs with the real code; MCC's side stood in for by the lists of the owner's lobby test).
- **Validation:**
  - `build.bat` builds `botcore_pg2.dll`.
  - `build_pool_test.bat`: all pool checks pass. Test 25 is new: 300 lobbies sized right with the party always on your team, the clan whole and off your team, no name twice, keep 100 / keep 0, pinned seats through the point deal.
  - `pg_preview`: all six screens drawn and looked at (menu, invite, search, vote, next game, error). The odds of one vote's 7 bots ranged from 91% on one option to near-even splits, None of the Above 3-12%.
  - **Not yet run in MCC:** pressing Start from the Update hook, the team flag read, the screens' input over the live lobby, the between-match turnover after a real match, and which team MCC puts you on. Until a match has written `bot_pool_humans.txt`, you are taken to be on Red, and your party goes there.
- **First live run** (the owner: "The firsdt game worked perfectly"): the search and the vote, then Team Slayer on Anchor 9 launched by MCC's own Start, pressed from the Update hook. The second vote failed with "MCC's lobby did not answer which games go on which maps", and Try Again fixed it.
  - Cause, from the log: the next vote was drawn when the match ended, before MCC came back to its lobby and reloaded its Reach lists. MCC accepted none of the options, so the vote had nothing to show. Try Again started a fresh search once the lobby was back, but it also replaced the lobby between matches with all new bots.
  - Fix (`botcore_pg3.dll`):
    - the vote is drawn once MCC's lobby is back;
    - `pg_lobby.cpp` copies MCC's lists the moment the lobby returns;
    - when MCC accepts no option, the options are drawn again from the lists as they are now (up to 8 times, 16 s), not given up after 6 s;
    - TRY AGAIN keeps the lobby and only sets its vote up again (after a launch failure, it presses Start again for the same winner);
    - your team (and your party's) comes from `bot_pool_humans.txt`, which `tools/play.py` writes at each match start.
  - Validation: builds; `pg_preview` draws all six screens. Not yet seen live: the second game's vote.
- The owner: "that was great. Can I add my own maps and modes to the list of voting? and also is the starting votes always the same three at the restart of the mod?" (`botcore_pg4.dll`):
  - **The same three:** they were. The vote's dice started from a fixed seed, so every MCC start drew the same first options, search length and bot rolls. They are now seeded from the clock on first use. Two preview runs drew different first votes.
  - **Your own maps and modes:** `proving_grounds.ini` takes `<arena|btb>.addmap=` and `.addgametype=NAME*weight` (added to the built-in lists, or a gametype's weight changed), and `.removemap=` / `.removegametype=`. `.map=` / `.gametype=` still replace a whole list.
  - The file is read each time Proving Grounds is opened. The owner's file now lists his own Forge maps and MLG gametypes from MCC's list, commented out.
  - Checked with `pg_preview lists` on a scratch file: adds, a changed weight, removes and a replaced list all came out as written.
- The owner's own TU gametypes (`botcore_pg5.dll`). He sent ten files: "add these all to the game. And replace our matchmaking gametypes with these corresponding to the ones we have".
  - **The files:** Halo: Reach `_blf`/`chdr`/`mpvr` gametype files, read for their names only. The two TU Neutral Bomb Assault (4-10) files are byte-identical.
  - **Copied:** the nine distinct ones went into his `LocalLow\MCC\LocalFiles\<id>\HaloReach\GameType` under new GUID names, as MCC names its own (local only, not in git; nothing overwritten, the downloads untouched).
  - **Same names as MCC's:** TU TEAM SLAYER DMR and TU MULTI FLAG CTF have MCC's built-in names, but their data differs from MCC's built-in copies. `playlist_pool` now picks the player's own (kind 3) when MCC has a name twice. The vote shows clean names: "TU ONE FLAG CTF (4-10)" as One Flag CTF, and so on.
  - **`proving_grounds.ini`, Arena:** his (4-10) One Flag, Multi Flag and Neutral Bomb, his CTU 5-Plot Territories (for 3-Plot), and his Team Crazy King (4-10) and Team Oddball. The last two are new to the vote; MCC's own are free for all.
  - **`proving_grounds.ini`, Big Team Battle:** his TU Multi Flag CTF and CTU 5-Plot Territories. Neutral Bomb stays MCC's, since his is the 4-10 player one. The weights are kept (Stockpile 2%).
  - **Both playlists:** Team Slayer is his TU TEAM SLAYER DMR. TU FFA CRAZY KING is in the game but not in the vote (free for all).
  - Checked with `pg_preview lists` (stand-in list with his names as kind 3 and MCC's team flags as read live): the vote uses his files for every replaced mode and MCC's for CTF, One Bomb, Stockpile and BTB's Neutral Bomb.
  - Not yet seen: MCC listing the nine files. They are uncompressed `mpvr`, as MCC's shipped files are, while MCC's own saves are compressed. A file MCC does not load is simply missing from the vote.
- Not done: Reach's own matchmaking variant files (`haloreach\hopper_game_variants`) are not used, because custom games list only the shipped and the player's own. A real entry in MCC's Multiplayer menu is not done either: that menu is MCC's newer UI, so the tile sits in the Reach lobby instead.

#### The lobby test that proved it (same day)

The owner's plan: Proving Grounds, an offline copy of Social Games (4v4 / 8v8, a short fake search, Reach's vote with the bots voting). Its open question is whether the mod can make MCC's own Custom Multiplayer lobby launch the vote's winner, so that the lobby, the match and any friends agree. The owner: "Yes, study it", then "Yes, build the test".

- Static study of `MCC-Win64-Shipping.exe` (Oct 31 2026 file, read only). The lobby's screen keeps its picks: the game variant id, map variant id, base map and map entry. Its Start checks the pair against MCC's variant library, then hands it to the lobby's settings. The map id is the one MCC's own map pick sets.
- `native/lobby_test.cpp` (new): hooks that Start, so it runs on MCC's own thread at the moment MCC chooses.
  - With `native/bin/lobby_test.ini` `on=1` (not in git) in a Halo: Reach lobby, it swaps in `game=` and `map=` (a name or `#id`) just before MCC checks and commits them. It acts once, then sets the file back to `on=0`.
  - Every Start logs what the lobby had and writes the whole library to `native/bin/lobby_library.txt`: each title's game variants, map variants and base maps.
  - With `on=0`, no file, or another MCC build (byte check), nothing changes.
- `native/overlay.cpp`: `mcc_lobby_title()` (the open lobby's title, from the files it loads). `native/session_watch.cpp` installs the hook, and `native/build.bat` builds the new file.
- First live run (the owner's Reach lobby, CTF on Boardwalk): the hook caught Start, and Reach is library index 6, the only title loaded. Names read as empty, so nothing was swapped and CTF on Boardwalk launched as picked. An entry's text is a run of 0x30-byte records from +0x28 (length +0x14, text pointer +0x18); the name is the record at +0x58, the one MCC's own name reader gets. A map variant's +0x450 is its base map id. Fixed the name reader.
- Second live run (CTF on Boardwalk): the names read correctly, but they showed the static read had two lists swapped. The library's +0x28 list is the gametypes (their category at +0x450) and +0x108 is the maps. The screen's +0x16D0 is the map and +0x16D8 the gametype. The test's fallback set TU Team Slayer DMR on Boardwalk, MCC's check accepted it, and CTF still launched. MCC's own Start tile runs its apply step (`FUN_1404D4C8C`) before Start, and the test's swap came after that.
- Rewritten for that (run 3): gametype and map are swapped as MCC's own picks set them. That covers the map, its content id, the category, the gametype and its entry, plus the host's category. MCC's own pairing check runs first, then MCC's own apply step. Names match the entry name or any of its text (`SwordBase`), or `#id`. A watcher logs the launch host's map and gametype whenever they change. The fallback is removed.
- Third live run (the owner: "It loaded Sword base slayer"): the lobby had CTF on Boardwalk and the test swapped in SLAYER on Sword Base. MCC's check passed, its Start committed the new picks (the host read map #5088, gametype #5182, category 1), and the match loaded Slayer on Sword Base. **The mod can choose what MCC's own lobby launches.**
- Validation: builds (`botcore_lobbytest4.dll`, no warnings from the new file). The function bytes and the screen's Start slot were checked against the exe on disk. Never seen: a friend in the lobby (the owner has none to test with).

### Service Record: commendation banners outlined in their tier's colour, 2026-11-16

The owner: "You didnt update the website to inclue the commendation banner outlines. The colored outlines for each rank?", then sent his six tier frames (Iron to Max, Max with flames).

- `service_record.py framed`: a tier banner gets its progress strip in the tier colour and an outline: the owner's frame of that tier when this PC has it (`native/bin/service_record/art/commendations/frames/<tier>.png` and `frames.json`, the opening the banner sits in), else a glowing outline of the tier colour drawn round it. Tier banners are redrawn when the emblem, the banner, a frame or this tool changes.
- `service_record_art.py frames <sheet>`: cuts the owner's frame sheet (six frames on black, three a row) into the six frames on transparency and finds the opening on the Iron frame.
- `style.css`: a card of a tier reached is outlined all round in the tier colour; framed banners keep their own shape.
- Not done yet: the owner's frame sheet arrived only as a picture in chat, not saved to disk, so the drawn outlines are what shows until it is saved and `frames` is run.
- Validation: `tools/test_service_record.py` 21 (the tier banner test now checks the outline), `tools/test_service_record_art.py` 10 (+1: frames from a made-up sheet), all 80 `tools/test_*.py` pass. Looked at a real Iron card (AimAssistPriest's Medal Collector) and, with made-up counts in the page, Iron, Bronze and Gold cards.

### Service Record: player pages like the old service record; turning figures; carnage reports; commendations and badges, 2026-11-16

The owner's mockup of the old service record ("I want our site to look like this once you click on any players page", "almost perfectly identical"), then: Game History and carnage reports, a Ranks page, a front-page podium, medals by group ("Do 1, 3, 4, and 5"); the commendations from his list with his tier art; his own commendations and badges; Forge objects on the heatmaps; and "reset everyones stats. Not models".

- Player pages (`tools/service_record_site/app.js`, `style.css`, `index.html`): a record card across the top (emblem, name, clan, rank bar, the three most played modes, unlocked badges linking to them), an icon sidebar, the Overview of the mockup (figure, stat list, Games Played ring, Top Commendations, Victory Streaks, Recent Games), night-blue panels. Our own `backdrop.svg` as the fallback; the owner's header, sidebar, icon, game type and commendation pictures are read from `native/bin/service_record/art` (not in git), the site's drawn ones without them.
- Figures (`native/figure_snap.cpp`, `native/build_figure_snap.bat`, `service_record.py bot_figures`): each bot's Reach figure in its own armor pieces and colours, drawn by the bots panel's own `model_view.cpp` on a device of its own (MCC need not run), 24 angles one strip, WebP; the page turns it (drag, arrows, keys) and stands it inside a lit ring. Spartans and Elites the same height. Redrawn only when `bot_looks.ini` changes.
- MCC's own pictures (`tools/service_record_art.py pictures`, `video`): the body drawings, the map previews, and the Noble main-menu movie as MP4 for the landing pages (`native/bink_to_mp4.cpp`: MCC's `bink2w64.dll` decodes, Media Foundation encodes; a pause button, remembered).
- Game History as cards with mode, map and result filters; a carnage report per game (map banner, team panels, each player's medals that game, a kill feed from the kill record, `service_record.py kill_feed`); a Ranks page; the front page's top three by cR on a podium; Medals grouped as the old site did (`medal_group`, MCC's own medal types).
- Commendations (`tools/service_record_site/commendations.json`, `service_record.py commendation_counts`, `tier_banners`): Reach's 14 multiplayer ones (the owner's list) and our Victor, First Blood, Closer, Grudge Match, Medal Collector, each tier Iron to Max with its cR (counted in the rank: `ranks.json commendation_credits`); the card shows the owner's emblem of the tier reached on Reach's banner. Badges: Map Master (a win on all 20 Reach maps) and Hometown Hero (#1 in the home state on any board with another bot of the state on it), one-time, no cR.
- Heatmaps (`map_pieces`, `draw_pieces`, `match_variant`): a game on a Forge layout gets that layout's own heatmap with its pieces drawn from their collision shapes (the layouts the mod already files under `maps/<map>/variants`); a standard map gets its placed objects drawn on.
- Also: game-type icons (`modes.json`), Enemies and the rank table fit the screen, Play style off the Profile, ties read "Tied".
- The bots' numbers were reset again with the mod's own `tools/bot_career.py --reset-bots` (ledger and totals backed up in `native/bin/career/*_before_bot_reset_20261116.*`); figures, art and the person's own totals kept. Pool bots appear again once they play.
- Validation: `tools/test_service_record.py` 21 tests (+6: kill feed, match medals and groups, commendations, our commendations and badges, mode icons, Forge layouts and tier banners), `tools/test_service_record_art.py` 9 (+1), `tools/test_figure_snap.py` 2 (new: the colour tables equal the bots panel's), all 80 `tools/test_*.py` pass. Looked at at 1280 px and 375 px (no sideways scroll, no console errors) in the browser pane and headless Edge. Not checked: dragging the figure with a real mouse or finger, and the Noble movie playing on screen (headless capture shows its still).

### Service Record: a Bot Tracker front page; home states and state leaderboards per weapon, vehicle and mode, 2026-11-16

The owner: "Region leaderboards per weapon, vehicle, mode, procedural state placement for every bot."; while it was built: "You don't have to include that they're bots everywhere. Just put it on the front page something like "Bot Tracker"".

- Home states (`tools/service_record_site/states.json`, `service_record.py` `load_states`, `home_state`): every listed name gets one of the 50 states, picked from the name alone (sha256), weighted by 2020 census population, so it never moves and a new bot gets one the first time it is listed. Regions are the Census Bureau's four. Today's 55: 26 states (California 7, Texas 5); South 19, West 16, Midwest 13, Northeast 7.
- `weapons.json` `reach.vehicles`: the damage types that are a vehicle (24-40, 59). `data.js` gets `vehicles`, `regions`, `states` and each player's `state`.
- Front page (`app.js`): the heading is "Bot Tracker", with tabs Leaderboard | By state. By state has four boards: Overall and Mode (cR by the rank's formula, Mode within that mode's matches), Weapon and Vehicle (kills with it from the kill record, plus All vehicles). Each board is shown for Nationwide, a region or a state; a name with none of the number is left off; equal numbers share a place; a Leaders by state table follows. Follows the Game picker.
- Each record: a State Placements page (its place in its state, its region and nationwide on every board it is on); its home state on the banner and Profile.
- The pages say "bot" only on the front page now: "Roster" / "Matchmaking pool", Name, Standings, "Find a name", the kill notes name the player, the footer drops "for our own bots".
- Validation: `tools/test_service_record.py` +1 (16): six names pinned to their states (a table change that would move them fails), the picks follow the weights over 20,000 names, every state has a region, the site names every player's state and the vehicle types. All 79 `tools/test_*.py` passed before the rewording; the site, art and one-copy tests again after it. In the browser pane at 1280 px and 375 px (no sideways scroll), no console errors: Overall cR equals the rank's cR for all 55; ties share places on the DMR board. No vehicle kill is recorded yet, so the Vehicle board shows only its empty note.

### Bot Matchmaking: 4v4 / 8v8 pool files, clans always whole, 2026-11-16

The owner: "Make clans trump team balance, then balance lobby the best possible. Make balance button follow this rule. Distance clans in the text file, but add variety so teams can play"; the teams "have to always remained balanced, but I don't want a clan member of theirs on my team"; then "a UI element next to the bot matchmaking button ... choose between a bot text file formatted for 4v4 or 8v8", "allow clan parties to be up to 4 or up to 8", "for the clans with more members, usually include the max party size".

- Pool files (`native/bots_panel.cpp` `pool_write_format`, `pool_ensure_format`, `bot_pool_set_format`, `bot_pool_reshuffle`): `bot_pool.txt` stays the file to edit. `bot_pool_4v4.txt` and `bot_pool_8v8.txt` are made from it whenever it, a bot's clan tag or the reshuffle changes (their `# source=` line). In them, the lines of bots in no clan (or a clan of one bot) keep their order; each clan's lines go in rounds cut into parties of up to 4 or 8; the parties are spread evenly through the file, one clan's apart, and about 1 in 4 is placed beside another clan's so the clans meet. Each format keeps its own queue position (`bot_pool_saved.ini` `next4=`, `next8=`, `salt=`; the old `next=` reads as the 4v4 one). `botcore.ini` `pool_format=4|8`.
- Parties (`bot_pool_rotate`, `pool_fits`, `party_cap`): a clan's first bot in a lobby pulls its clanmates in 85% of the time (was 70%, re-rolled by each clanmate), up to the format's party size and the seats of the team without people. A lobby never takes more of a clan than fit whole on one team (that bot is passed over); "Swap for next bot" too.
- Teams (`roster_point_balance`, `roster_balance`): a clan stays whole on one team (it was cut to the biggest team's size), the team without people when it fits, then the points. Balance teams now evens the sizes counting the people of the last match (it counted bots only, so a 4v4 with you could deal 4 bots to your team). A clan too big for any team (a lobby made by hand): with Bot Matchmaking on, its extra bots are swapped for the next pool bots that fit; off, it is split, and the panel's banner names the clan (`roster_balance_note`).
- Menus: a 4v4 / 8v8 picker beside the Bot Matchmaking switch; "Group parties" became "Reshuffle clans" (both files made again with a new spread; `bot_pool.txt` unchanged); the help text, the banner and the Balance teams tooltip say the new rules.
- The owner's question: the earlier counts (COD 12, WE 11) were pool lines, repeats included. COD has 3 bots and WE 4.
- Validation: `native/pool_test.cpp` test 22 updated (party on the team without people; the 4v4 file keeps a clan together and the rest in order), new 22b (a clan of 6: parties of 4 and 2; the full party 258 of 300 times, about 85%; never more than fit; 4v4 and 8v8), 22c (5 clanmates in a 4v4 with you: even sizes; split with a note when off, swapped when on), test 24 replaced (three clans in 200 lines: clans meet in 113 of 487 places, places at least 3 lines apart, the other lines in order, a clan of one bot no party, each format's own queue position). All pool checks and all 79 `tools/test_*.py` pass; `native\build.bat clanformat` built `botcore_clanformat.dll`. The owner's real pool, copied to a scratch folder, came out with every clan's parties spread out (COD at lines 73, 522, 691, 857) and AYS beside WAVE. Not yet seen in MCC.

### Service Record: every weapon has its picture; a blueprint theme, 2026-11-15

The owner: "Make all the weapons have their png picture like the original website nice and neat. I think the website also needs a little more flare and theme".

- **The pictures are MCC's own**: `careerdb.xml`'s Weapons list gives every damage type the picture MCC draws on its post-game Tools of Destruction, 352 x 100 light blue line drawings kept in `globaluitexturepack` and `mainmenuandcampaigntexturepack`. Nothing was downloaded.
- `tools/service_record_art.py` `weapons` (new): reads them into `native/bin/service_record/art/weapons/` (not in git), each cut to what is drawn so it sits centred in its card, with `art/weapons.json` (damage type number to file). `tools/service_record_site/weapon_art.json` (new) says which of MCC's damage types each recorded number is (its names only, no picture). All 72 of Reach's numbers get one, 55 different pictures.
- `tools/service_record.py` `weapon_pictures`: the pictures of the weapons a page names are copied into the site (`weapons/`), as `weapon_art` in the page data. One without a picture keeps the site's own plain mark.
- Pages (`app.js`): the Weapons page is cards (the picture, the name, "Kills: N | Deaths: N", its share of the recorded kills and deaths) in place of the table; Top weapons on Summary shows the three deadliest the same way, and Overview has them too. Overview opens with four large numbers (kills, kill/death, wins, medals). The leaderboard's first three places are in gold.
- Theme (`style.css`, our own drawing, no game art): a blueprint. A drafting grid behind the pages, panels with two bracketed corners and a heading bar that fades out, a hatched nameplate banner with a larger emblem and insignia, the rank bar in gold, weapon and medal cards on squared paper. A page's blocks rise into place, and bars draw from the left, unless the PC asks for reduced motion.
- Validation: `tools/test_service_record_art.py` +2 (8: pictures read from a made-up MCC, a BC3 texture built by hand, cut to what is drawn, a number MCC has no picture for left out, the site copying safe names only; every number of `weapons.json` has an entry in `weapon_art.json`). All 79 `tools/test_*.py` files pass. On the real data: 11 recorded weapons, 11 pictures, each loads; every one of the 72 looked at on a labelled sheet beside its name. Leaderboard, Overview, Summary, Weapons and Medals looked at at 1280 px (headless Edge, from the folder); 12 pages at 375 px with no sideways scroll, no control under 24 px and no console errors. **Untested**: a real Chrome or Edge window, a screen reader; the pictures of the 61 damage types no bot has killed or died by yet are matched by name, as `weapons.json`'s unchecked names are.

### A recorded match is on the Service Record as it ends; heatmaps open on where the fights were, 2026-11-15

The owner, asked whether the site should rebuild when a match ends: "Whatever you think is most efficient".

- **Before**: a match's report was kept beside its recording, added to the career ledger and put on the site only when the next match started (`tools/play.py`), so the last match of an evening waited for the next evening's first. play.py cannot do it at the end: botcore stops it the moment a match ends. The brain ends on its own a few seconds later.
- `tools/after_match.py` (new): the same three steps, in play.py's order, as a recorded match ends. `play.keep_carnage` is asked about that match's recording only, then `bot_career.py` runs, then `service_record.py`. It waits up to 20 s for MCC's report. Nothing is done for a match with no report, one kept already, or a recording that is gone.
- `tools/live_bots.py`: starts it in the background as the brain stops, after the recording is closed, and only for the mod's own logs folder. The next match's start finds the report kept and the match counted, and repeats nothing.
- Heatmaps (`tools/service_record_site/app.js`, `style.css`): when every spot lies in a small part of the map's picture, the page opens on that part, with "Show the whole map" under it. A Forge variant in a corner of Forge World had its 32 spots in one blob. The picture is now drawn into the canvas, cut to the view and dimmed there. The page's foot says "Rebuilds when a recorded match ends and when one starts".
- Validation:
  - `tools/test_after_match.py` (new, 3): the report kept by play.py's own rule, then the totals, then the site; nothing for a report from minutes before, a kept one, a recording that is gone; a late report waited for; the brain starts it after closing the recording. All 79 `tools/test_*.py` files pass.
  - Run by hand on the real Forge World match that had just ended (20261115-204102, its report 14 s older than its recording's last line): the report was kept, the ledger and the site rebuilt, in under a second. `service_record.py --check-kills` then said both recorded matches' rows equal MCC's report for every player.
  - The real site in a browser: that match's Weapons page, its heatmap zoomed and whole, Powerhouse's heatmap whole with no zoom offered, no console errors.
- **Untested**: the brain starting it by itself as a match ends (the next recorded match). The zoom on a phone. A report MCC writes more than 30 s before the brain stops is not kept, by play.py's rule; it was 14 to 17 s in three matches.

### Kill record: the kill that wins the match counts; the first whole match equals MCC's report, 2026-11-15

The owner played the first match recorded with the kill record (Powerhouse 20261115-203100, TU Team Slayer DMR, the owner and 7 bots, 478 s) and asked for it to be checked.

- **Seen**: 94 rows, no read failed, every body read. Kills and deaths equalled MCC's report for 6 of the 8 players. The other two were one kill apart: the kill that won the match. The engine's state turns to "over" in that kill's own tick, so its row said "over" and was left out. MCC's report counts it. It does not count a melee kill 6 s later, whose credit the game never wrote.
- `tools/kill_record.py` `Watch`: a row's state is the one its victim was last seen alive in, a pass before. The recording's first line now says version 2.
- `tools/service_record.py`: the store keeps each recording's rows as written, with the recorder's version (`read_kills`). `kill_rows` (new) reads them each time they are used: a version 1 recording's first "over" row is "played" when the game wrote its credit at that death. Only that match is version 1. The real store had kept its rows before this fix, as a bare list; a bare list is read as version 1, so nothing had to be read again.
- `tools/service_record_site/weapons.json`: six more damage types matched to what the killer held in that match, so they lose their star on the site: assault rifle (4 of 4), shotgun (2 of 2), needle rifle (3 of 3), focus rifle (5 of 5), gravity hammer (1 of 1), and melee (8 of 8 bot kills with the melee button pressed in the 1.3 s before).
- Validation:
  - With the fix that match's rows equal MCC's report for all 8 players: kills and deaths (93 each in all), each player's "killed most" and "most killed by" by name and count, and each player's melee and grenade kills.
  - `tools/test_service_record.py` +1 (15): a version 1 recording's winning kill counts, a death after it and a left-over credit do not, a version 2 recording is read as written, the kept rows are never changed by reading. `tools/kill_record.py` self-check: the winning kill and a death after it. All 78 `tools/test_*.py` files pass.
  - The real site rebuilt with that match in it: `--check-kills` says every player's kills and deaths equal MCC's report. Its Weapons, Enemies and Heatmaps pages were looked at in a browser on a copy built from the same rows and report (a bot's 25 kills and 12 deaths per weapon, its 4 opponents, 37 spots on Powerhouse).
  - The next match was the first version 2 recording (Forge World 20261115-204102, the owner and 7 bots, 287 s, 91 rows): kills and deaths equal MCC's report for all 8 players, and so do each player's two rivals. A teammate's plasma grenade read as a betrayal, as the report has it (1 betrayal, not a kill). Three deaths after the end were left out, as in the report.
- **Untested**: a match that ends on time. Suicides and falls (neither match had one). Firefight, free for all, round-based modes, a second person.
- **Not changed**: the site still rebuilds only when a match starts, and a match's report is copied beside its recording at that same moment. So a match's kills, like its map, reach the site when the next match starts.

### Service Record: every kill recorded in Reach, so Weapons, Enemies and Heatmaps fill in, 2026-11-15

The site shipped with those three pages saying "not recorded yet"; the owner asked for the per-kill record as the follow-up. Python only: no botcore change, no DLL build, no MCC restart.

- **Found** (a read-only probe of a live match, Boneyard 20261115-195851, the owner and 8 bots: every player's row, each body and the engine block read 30 times a second from 81 s in until the end): the game keeps each kill itself, and the brain can read it.
  - The dead player's row names the player the game credits (`+0x3AC`), written the tick he dies. His body holds the damage type that killed (`+0x290`) and who damaged it lately (4 entries at `+0x4DC`: tick, body and shield damage, player, type).
  - Deaths: all 21 in the probe's window are deaths in MCC's report. With the 12 before it (counted from the recording's world rows) they equal the report for all 9 players, 33 of 33.
  - Kills per killer equal the report for the three players whose kills all fell in the window. For the rest the rows are short by the first 81 s, so a whole match is still to be checked. The report itself has 28 kills by one team against 27 deaths of the other; not explained.
  - The credit is not always the last hit. A teammate's frag finished a bot 1.07 s after an enemy's chaingun; the game credited the enemy, and MCC's report gave the teammate no betrayal.
  - Damage types 6, 8, 9, 11, 29 and 34 were a DMR, a sniper rifle, a rocket launcher, a frag grenade, a Banshee and a Warthog's chaingun in the killer's hands or seat every time (20 typed deaths and one own-rocket death). 43 came with no damage entry, the owner on foot beside the victim: Melee by Reach's list of damage types, not confirmed by anything else.
  - After the owner ended the match the engine block's `+0xD8` read 2 (1 before); the 4 deaths after that are not in MCC's report. A bot removed from the game leaves no body.
- `brain/live.py` `LiveReach.kill_watch`, `death_bytes` (new): the reads, with the fields and how each was found. One read of the players a pass; a body only when someone dies.
- `tools/kill_record.py` (new): `Watch` writes one row a death: who died, who the game credits, whether that credit was written at this death, what killed, the body's damage entries, teams, bots, where both stood, the game's tick, the engine's state. Players are ids; no gamertag goes into the recording. `read` says what a row counts as: a kill (the credited player is on the other team), a betrayal, or a death nobody is credited with. The weapon is the credited player's own last damage on him, else what killed. A credit left over from an earlier death counts only with that player's damage on the body. A row from after the match was over does not count.
- `tools/live_bots.py`: a recorded Reach match's trace starts with `{"kill_record": 1}` and gets a `{"t", "kill": {...}}` row a death. A read that fails is tried again the next pass; 30 in a row turn the record off for the match. It never stops the bots.
- `tools/recording.py`: the trim of a long match keeps the kill rows, as it keeps the bots' meta lines.
- `tools/service_record.py`:
  - `native/bin/service_record/kills.json` (new, game data, not in Git): each finished recording's kill rows by map and start time, read once and kept after the rotation. A recording without the first line is not read past its first 256 KB.
  - Per bot and game: kills and deaths per weapon, every opponent both ways, the spots of its kills and deaths per map, and how many of its matches have kill rows.
  - A bot is named by the index in its report id. A person is named from the report row of their team that their kills and deaths fit, and is "Unknown player" when two fit as well.
  - A map's picture: `maps/<id>/topdown.png` copied into the built site with the part of the level it shows, read from `heightmap.npz` without numpy.
  - `--check-kills` (new) prints each recorded match's rows against MCC's report, player by player.
- `tools/service_record_site/app.js`, `style.css`, `weapons.json` (new):
  - Weapons: kills, deaths and their shares per weapon. Enemies: kills on, deaths to, difference and K/D per opponent. Heatmaps: a tab per map, kills / deaths / both, a dot where the bot stood for a kill and a cross where it died, over the dimmed picture (on a plain panel when this PC has no picture of the map).
  - Each says how many of the bot's matches it comes from. A bot with no recorded match still says "not recorded yet"; no page shows a zero for a match without kill rows. MCC's kills by type and two rivals stay below, named as the report's.
  - `weapons.json` names the damage types by Reach's list. A name not yet matched to a kill seen live is marked with a star on the page.
- Validation:
  - `tools/test_service_record.py` +3 (14): made-up kill rows summed per weapon, opponent and map; a betrayal, a death with a left-over credit, a row after the match, three bad rows; a match recorded without kill rows; the rows kept after the rotation; two people named or left unnamed; a long recording's trim; a map picture's frame.
  - `tools/kill_record.py` self-check: a made-up game through `Watch` and `read`. All 78 `tools/test_*.py` files pass.
  - The probe's frames replayed through `Watch` give the 21 rows above and leave out the bots removed at the end.
  - `map_frame` equals numpy's reading on all 144 maps with a heightmap, and each picture's shape fits its grid.
  - A preview site built from those real rows and that match's report (scratch folders, not the real store): the three pages opened in a browser at desktop and phone width, no console errors, no sideways scroll. The real site rebuilt in 0.1 s: 50 recordings looked at, none with kill rows yet, the three pages unchanged.
- **Untested**: the recorder inside a live match (it runs from the next recorded Reach match: the brain starts fresh each match). Kills per killer against MCC's report over a whole match (`--check-kills` after it). Suicides, falls, splatters and assassinations; Firefight (an AI's kill has no credited player); free for all; a round-based mode (whether the engine's state reads 2 between rounds); a second person in the match. The modifier byte is stored and not read. Other games write no kill rows.

### Reach ranks: one copy, so the site and the game cannot drift, 2026-11-15

The owner, asked whether Major Grade 2 is 375,000 cR (his brief) or 370,000 (the page the insignia came from): "Either just make sure it stays flush if we end up adding ranks into the game for bots."

- Major Grade 2 stays 375,000 (`tools/service_record_site/ranks.json` unchanged).
- `CUSTOMIZATIONS.md`: the rule. The rank table and the credit formula are `ranks.json`; a bot's credits are the site build's. If the game ever shows a bot's Reach rank it takes both from there (a file the site build writes for it), never its own list or its own sum. Today's in-game badges are MCC's account ranks by difficulty, a different thing.
- `tools/test_reach_ranks_one_copy.py` (new, 2): fails when a source file under `brain/`, `tools/`, `tools/service_record_site/` or `native/` other than `ranks.json` holds three or more of the table's telling credit figures (those with three or more digits before their zeros: 26,250, 1,180,000, 5,650,000 ...), however written (`1180000`, `1,180,000`, `1_180_000`); a file whose first lines name `ranks.json` (a generated header) may hold them.
- Validation: passes on today's tree; with a made-up header holding four of the figures planted in `native/` it failed and named the file, and passed again once it was removed. `tools/test_service_record.py` and `tools/test_service_record_art.py` pass. Nothing in the game shows a Reach rank yet, so there is no second side to compare.

### Service Record: sharper rank insignia, one 91 x 91 picture a rank, 2026-11-15

The cuts from the owner's chart were 24 px across and soft at 56 px. Asked for a larger copy, he gave the Halopedia page of Reach's ranks, which shows each rank's own picture, and said to download them.

- Downloaded once, with his OK (by hand, not by a tool: no address is in the repo): the page's 50 rank pictures, 310,677 bytes in all, into `native/bin/service_record/art/rank_icons` as `<step>_<the page's file name>`, the step being the page's table row. Game art: not in git.
- `tools/service_record_art.py` `ranks <folder>` (new form): one picture a step, each file's name starting with its step's number, 0 to 49, each once (else nothing is written). A picture keeps its own see-through parts and is centred on a square (three of the 50 are 91 x 88). `ranks <chart picture>` still works; the owner's chart is kept as `art/rank_chart.jpg`.
- **For the owner to settle**: the page's table agrees with `ranks.json` on all 50 names and their order and on 49 of the credits. It gives Major Grade 2 as 370,000 cR; the brief, and so `ranks.json`, has 375,000. Left as the brief has it.
- Validation: `tools/test_service_record_art.py` +1 (6: a folder's pictures written by step with their see-through parts, one not square centred, a missing and a doubled number refused with nothing written, a big picture made smaller). All 77 `tools/test_*.py` files pass. Every one of the 50 looked at on one labelled sheet beside the cuts from his chart: the same insignia at every step. The site rebuilt: its 50 `ranks/<step>.png` are the store's, 91 x 91; a bot's page opened from the folder in headless Edge draws the Recruit picture. **Untested**: a rank above Recruit on a live page.

### Reach Banshee: the air guards let go of the boost and turn the way out, 2026-11-15

The owner's F9 on Boneyard (`logs/bug_reports/reach_70_boneyard_20261115-195851`, 20:02:28): "Oreo driving banshee weird stuck on back wall. Jumping out, not shooting bomb correctly".

- **Found** (its trace, bot 3 Oreo, Demon): on the way out of a run (`att` "pass") from 92 s to 105.5 s it pressed into the back building at 0.4-3 u/s with the boost held the whole time (the way-out boost from earlier today). The guards turned it to open air ("wall ahead, turning to open air", "stuck, out to open air"), but the next tick's way out pointed it back along the run's saved heading, and "the ground on the run, pulling out" fired every tick. After 13 s the stuck rule got it out (Use held 0.8 s). The same at 131.9 s and 204.1 s. Its bomb cycles came in pairs 0.47 s apart, every 3.2-3.3 s, as planned; whether the game switched is not in the trace.
- `brain/bot.py` `air_unboost` (new), called from `air_guard` wherever it steps in (stuck, wall ahead climbing / turning / backing off, the ground on a run, and "too near something" within half its room): Reach's boost let go, and on a run's way out its saved heading becomes the open one the guard found. Every game's guard as before otherwise; a Falcon keeps its climb input.
- Validation: `tools/test_reach_boost.py` +2. All 75 `tools/test_*.py` files pass. **Untested in a match**; the bombs still need a live look.

### Service Record: the rebuild at match start waits up to 90 s for the career totals, 2026-11-15

- **Seen live** (the owner's Boneyard match start at 19:58:31): the report was kept at 19:58:31, `bot_career.py` wrote the ledger at 19:58:51 and the site was rebuilt at 19:58:52 with that match in it (a bot's games went from 1 to 2). So the rebuild at match start works, but the ledger took 20 s, the whole of the wait the build allowed (`--wait-ledger 20`); a slower start would have built without the newest match.
- `tools/play.py`: `--wait-ledger 90`. The build still starts the moment the ledger has every report on disk; the longer limit only matters when the PC is slow at a match start.
- Validation: `tools/test_service_record.py` (11) and `tools/test_bot_career.py` pass. **Untested**: a match start since this change.

### Service Record: the rank insignia, cut from the owner's rank chart, 2026-11-15

The owner sent his picture of the Reach rank chart (374 x 746, one row of framed tiles per rank, a tile per Grade), after: "Try to extract every insignia rank from the photo for each rank ... and if that shows to be a trouble revert to hand made for the ones you have trouble on". None gave trouble.

- `tools/service_record_art.py` `ranks <picture>` (new):
  - Finds the chart's square tiles by their lit frames (every pixel of all four edges at least 38 of 255, brighter than the pixels just outside), keeps the tiles of the usual side (the chart's key has one bigger sample tile), and reads them as rows.
  - The rows must hold exactly the tiles the rank table holds (`ranks.json`: 1, 1, 2, 3, seven rows of 4, 5, then ten of 1); else nothing is written and the site keeps its numbered placeholders.
  - Writes `native/bin/service_record/art/ranks/<step>.png` (96 x 96, the frame left off, the tile's black see-through) and keeps a copy of the picture as `art/rank_chart.jpg`. Game art: not in git.
- The site needed no change: the build already copies `art/ranks` and the pages show `ranks/<step>.png` where there is one.
- Validation:
  - `tools/test_service_record_art.py` (new, 5): a made-up chart's tiles found in the table's order with its key tile left out; each cut named by its step, its own shade in the middle and its black see-through; a chart a rank short and a black picture refused with nothing written; MCC's medal numbers decoded from a made-up exe (all four codings, and refused when medal 8 is not the assist); medal names and kinds. All 77 `tools/test_*.py` files pass (76 before).
  - On the owner's picture: 50 tiles of 28 px found, rows as the table; every cut looked at on one sheet beside the chart, all 22 ranks and their Grades in order. The site rebuilt with them: all 50 load at 96 x 96, and the banner and leaderboard draw the picture, not the placeholder.
  - **Soft, not sharp**: each insignia is 24 px across in the picture and is shown at 56 px. A bigger picture of the same chart, cut with the same command, would be sharper.
  - **Untested**: a rank above Recruit on a live page (every bot is a Recruit today).

### Reach bot pilots' bomb switch: the controller's switch bit, 2026-11-15

The owner, in the first Boneyard match after the bomb-first change: "the bot hasnt used the bomb once".

- **Found** (`logs/trace_reach_70_boneyard_20261115-194821.jsonl`): the bot pilot pressed the cycle 27 times in about 2 minutes of flying, so the brain did ask for the bomb; the game never switched. In the owner's controller capture (`logs/boost_capture_reach_20261115-191207`) every one of his 10 switch taps set `+0x40 0x100` and, 0.1-0.2 s in, `+0x08` bit 44 (`0x100000000000`) for a tick or two. botcore writes `+0x08` itself, so a bot's cycle had only the `+0x40` key bits.
- `maps/_inputs/reach.json` `cycle`: `+0x08` bit 44 on the press tick (press-only), with the `+0x40 0x300` key as before. The cycle is used only by the Banshee's bomb (`Bot.fuel_rod`).
- The same match showed the boost reaching the game: bot Ghosts with it held ran p90 8.4-8.7 u/s (5.2 without; never over about 5.5 before), the bot Banshee p90 7.6 (6.1 without; its guards eased it often).
- Validation: `tools/test_reach_boost.py` +1. All 75 `tools/test_*.py` files pass. **Untested in a match**: that the switch now takes.

### Proving Grounds Service Record: a stats site for the bots, 2026-11-15

The owner's brief (`docs/SERVICE_RECORD_SITE_BRIEF.md`): a stats tracker laid out like a 2010 service record, from what the mod already records. His answers to its questions: a local website named "Proving Grounds Service Record", on this PC only; "Just the bots for now" (a match's scoreboard still shows every gamertag); Reach first with a game filter; "for now I want the stats to be reset to 0 and then have them be live updated after every match or two"; game types grouped into families; the brief's credit formula, the same for every bot; Weapons, Enemies and Heatmaps say "not recorded yet"; "all the medals from mcc".

- `tools/service_record.py` (new): one build writes `logs/service_record/index.html` (opens from the folder, no server) from the career ledger, MCC's post-game reports and the bots' own files, all read and never written.
  - It keeps each report's detail once, by `GameUniqueId`, in its own store `native/bin/service_record/matches.json`, because the recording rotation deletes the reports. Store and site are game data: not in git.
  - Counting is `bot_career.py`'s own (imported, one copy): a match counts when its person played 60 s, a bot's row from before the bots' restart does not. So with "All games" chosen the leaderboard equals `native/bin/career/totals.txt`, and every bot starts at 0.
  - Listed: every bot of `bot_profiles.ini` (at 0 from the start) and any other bot once it has a counted match. People are never listed.
  - Credits: `tools/service_record_site/ranks.json` (the 22 Reach ranks and their Grades, 50 steps; 1,000 a counted game, +1,000 a win, 100 a kill, 50 an assist, 25 a medal), from a bot's counted Reach matches only.
  - Pages: leaderboard (sortable, a name filter); per bot Overview, Game History with each match's scoreboard, Profile (Reach armor by the Armory's piece names from `native/look_names.h`, difficulty, play style, how the rank was earned), Summary with game type tabs, By Game Type, By Map, Medals, Weapons, Enemies; Commendations, Heatmaps and Achievements say what is not recorded and why.
- `tools/service_record_art.py` (new): `medals` reads MCC's medal numbers from this PC's `MCC-Win64-Shipping.exe` (the report's `Medal mId` has no names), their names and icons from `careerdb.xml` and `medalstexturepack`, into `native/bin/service_record/art/` (not in git). Run once per MCC update; without it medals show by number with our own placeholder.
- `tools/play.py`: as a match starts, the site is rebuilt in the background after `bot_career.py` has added the last match (`--wait-ledger 20`). An open page checks for a new build every 30 s and reloads.
- **Not recorded yet** (shown as such, no numbers made up): kills and deaths per weapon, a full versus table, heatmaps (all three need a per-kill record in the trace), commendations, achievements, an armor picture, the Reach rank insignia (our own numbered placeholder until the owner's rank chart picture is cut up).
- Validation:
  - `tools/test_service_record.py` (new, 11): the leaderboard equals `totals.txt` on a made-up ledger (a quick quit, a draw, two games); the bots' restart and the roster at 0; people on the scoreboard and off the lists; K/D with no deaths, 2-place rates, `13d 3h 36m`; the rank table (Colonel Grade 3 to Brigadier 220,000, Noble to Eclipse 1,500,000, 0 Recruit, 20,000,000 Inheritor); credits from Reach only; game type families and map names; a report kept after the rotation; a bad report and a missing ledger; looks by piece name. All 76 `tools/test_*.py` files pass (75 before).
  - On the real data: the site builds in under 1 s (41 bots at 0; a preview from the ledger kept before the restart: 308 bots, 78 matches, 0.6 s). 311 medals read from MCC, all with an icon; on the 567 player rows of the 50 reports on disk, the Killing Spree medal (136) is there exactly when the row's most kills in a row is 5 or more, and each row's medals sum to its `mTotalMedalCount`.
  - Opened from `file://` in headless Edge and Chrome (41 rows drawn); every page looked at through a local server at 912 px and 375 px wide with no sideways scroll and no console errors; text contrast 4.69:1 or better, the ring's colours pass the chart palette checker on this surface.
  - **Untested**: the rebuild at a real match start (the hook is `bot_career.py`'s pattern), a real Chrome or Edge window, a screen reader.

### Reach Banshee pilots bomb first, every 3.2 s, at the controller's switch speed, 2026-11-15

The owner, recording on Boneyard: "show in reach how fast you can shoot a banshee bomb while spamming it, and then implement the bots prioritizing the banshee bomb first"; then "I showed two ways to shoot with the plasma casters first then bomb, and the bomb first method which is usually better."

- **Found** (`logs/boost_capture_reach_20261115-191207`, `logs/reach_shot_capture_20261115-191208`):
  - Spammed, the bomb fired once every 3.06-3.08 s (7 bombs); in his runs after that, every 4.3-7.4 s with the cannons between.
  - On a controller the cycle (+0x40 0x100) to the bomb's shot took 0.20-0.25 s; bomb first, the cycle back came 0.12 s after the bomb and the cannons 0.15 s after that. The bots used his keyboard pairs: 0.67 s to the shot, 0.59 s back, and one bomb every 6 s.
  - Bombs flew 19-22 u/s and landed within 0.7 u of his aim line at 10-20 u (nose 27-43 deg down): no arc to aim over. Cannon bolts flew about 78 u/s.
- `brain/bot.py`, Reach only (Halo 4 unchanged), every tier the bomb was on before:
  - `REACH_FUELROD` (3.2, 0.25, 0.12, 0.05) through `fuelrod_times`: a bomb at most every 3.2 s (0.1 s over the recharge), the shot 0.25 s after the cycle press, a 0.12 s tap, the cycle back 0.05 s later. The bomb still goes first whenever it is ready and in reach (10-31 u, the nose within 3 u of him): it outranks the cannons in the same tick, as before.
  - The run's boost is off while the bomb is under way (`air_pass`, way in and way out).
  - `reach_shot_speed`: while the bomb is selected the lead uses `REACH_BOMB_SPEED` 20 u/s (the Ghost's bolt speed moved here too).
- Validation: `tools/test_reach_boost.py` +4 (the Reach bomb timeline, Halo 4's kept, the 3.2 s and no boost on the bomb's tick, the bomb's lead). All 75 `tools/test_*.py` files pass. **Untested in a match**: whether a bot's cycle press (the keyboard decode, +0x40 0x300) switches as fast as his controller's 0x100, and the hits.

### Reach Ghost and Banshee bots boost for real; Banshee runs boost in and out and pull back to turn; Ghost lead from its bolt speed, 2026-11-15

The owner recorded himself on Boneyard (controller): a Ghost with boost holds and hard turns, Ghost shots at about 3, 8 and 17 u (middle, high, low), then a Banshee with boost holds and turns with the throttle back and forward. "For the ghost I would like for the bots to boost when deciding to splatter an enemy, or to get to a spot when not fighting in it. And the banshee as well."

- **Found** (`tools/boost_capture.py` joined with the new `tools/reach_shot_capture.py` for the vehicle's place; `logs/boost_capture_reach_20261115-184247`, `logs/reach_shot_capture_20261115-184247`):
  - Every boost hold set the action's `+0x08` u64 to `0x880048000` (bits 15, 18, 31, 35), `+0x24` to 1.0 and `+0x3C` to 1.0, together on 4808 of 4817 Ghost ticks. Bots sent only `+0x3C`; botcore writes `+0x08` and `+0x0C` itself, so the bits never reached the game.
  - The boost: Ghost at full throttle 4.96 u/s unboosted, 8.17 boosted (top 9.6); a 10.7 s hold kept about 8 u/s. Banshee 4.89 to 10.17 (top 12.1), holds of 4 s.
  - Turn rates: Ghost 40 deg/s at full throttle, 35 boosted, 72 with the throttle off. Banshee 66 deg/s at full throttle, 32 boosted, 105 with the throttle pulled back.
  - Ghost bolts: 29.3 u/s (152 bolts, p10-p90 29.2-29.5). They land on the aim line from the Ghost's place + (-0.44 forward, 0, +0.58 up) within 0.05 u at every range, and within 0.08 u of the bots' current aim line (`eye`, its place + 0.62), so the aim height was already right. Its lead used the plasma rifle's 37 u/s.
  - The capture recorder's own speed read 0 in a vehicle: a seated unit's place is relative to the vehicle (the join above fixes that for the analysis).
- `maps/_inputs/reach.json` `fire2` (new): while a bot's `fire2` is held, `+0x08` mask `0x880048000` and `+0x24` 1.0 (the u64 at `+0x20`, high half); cleared otherwise, so the person's trigger in the template action never leaks to bots. No botcore build: the brain writes the table at start. Bot.boost still sends `+0x3C` 1.0, as the person's action has it.
- `brain/bot.py`, Reach only, every tier but Easy as before:
  - `travel_boost`: a Ghost or Banshee (`TRAVEL_BOOST_HELD`) holds the boost the whole open leg (nose within 20 deg of its way, the way clear), not the keyboard player's 1.7 s / 2.4 s taps. Other kinds and games unchanged.
  - `air_pass`: the old on-target boost from 12-36 u is gone (it now would have run the dive at 10 u/s past `AIR_RUN_SPEED`). The way in boosts past `CANNON_R` (28 u) with the nose within 20 deg of him; the way out boosts. With him more than `AIR_TIGHT_TURN` (60 deg) off the nose, the throttle goes to `AIR_TIGHT_THROTTLE` (-1), no boost, no fire. The jink boost when shot at is kept.
  - The Ghost's splatter boost (held from 15 u, Nov 14) is unchanged; it now reaches the game.
  - `Aim.step` `shot_speed`: the Reach Ghost driver's lead uses `REACH_GHOST_BOLT` 29.3 u/s. (Demon's lead factor is 0, so Demon is unaffected.)
- `tools/reach_shot_capture.py` (new, read-only): Reach's version of `h4_shot_capture.py` (its summary), with the vehicle's place, forward and up.
- Validation: `tools/test_reach_boost.py` (new, 10: the table's bits held and cleared, the person's trigger cleared, the Ghost's held travel boost and Halo 3's taps, the Banshee's boost in from past gun range, none in the dive, the pull-back turn, the boost out, Halo 4 unchanged, the bolt speed's lead). All 75 `tools/test_*.py` files pass. **Untested in a match**: that the bots' boost now reaches the game (the bits match the person's exactly, but only his were seen), whether a boosted Banshee can still fire, the Banshee's boost limit past 4 s, and how the faster runs and pull-back turns change hits and deaths.

### Bots' career stats can start over, 2026-11-15

The owner: "reset all the bots stats. For a fresh restart of stats", the bots only (their own totals kept). Deleting the ledger would not have done it: `bot_career.py` reads every match report still in `logs/` again.

- Tools (`tools/bot_career.py --reset-bots`): every match known so far (after reading every report still on disk) is marked `bots_reset`; the bots' rows of those matches no longer count, the person's still do, and the matches stay in the ledger so they are not counted again. The next match counts for everyone.
- Run once on 2026-11-15 (87 matches): no bot left on the leaderboard, the owner's totals unchanged. Backups: `native/bin/career/ledger_before_bot_reset_20261115.json` and `totals_before_bot_reset_20261115.txt` (game data, not in git).
- Validation: `tools/test_bot_career.py` +1 (bots start at 0, the person kept; a report still in `logs/` is not counted again; the next match counts for both). All 74 `tools/test_*.py` files pass. Not yet seen on a bot's MCC Career page after a new match.

### Warthog guns shoot vehicles first; no in-and-out gunner loop; bots fight on the way to a vehicle, 2026-11-15

The owner's F9 reports from Forge World and Boneyard (20261115-044159, -045642, -051122): "Bots in warthog gunners dont shoot other vehicles", "BOT AIMING STRAIGHT DOWN IN WARTHOG GUNNER SEAT", "lilwraith not doing much out in the open when being shot". Then: "fix the gunner getting out issue, also make warthogs prioritize shooting other vehicles before infantry. Unless infantry is close similar to the tank mechanic ... Make the rocket hog shoot at infantry if and only when no enemy vehicles are within a range", and "make bots fight on the way to a vehicle and during patrol routes".

- **Found:**
  - With an occupied enemy vehicle within 45 u, Warthog chaingun gunners aimed at it 27% of the time, rocket Warthog gunners 11%. The rocket gun held fire on every man on foot, so it fired 8% of its seat time.
  - A rider in a parked vehicle nobody drives got out after 5 s (the nobody-drives rule), and its ride order put it back in about a second later. Over 100 such loops in the three matches, 10 by one Demon on the rocket Warthog at its spawn. The game read its view about 3 degrees down, so the droop the owner saw is most likely the turret at each get-in (unconfirmed).
  - On foot on the way to a vehicle no tier ever fired: a Legendary took four hits in 0.8 s from two men it saw (26 u, 42 u) and died. A fight won the vote, but the drive order outranked any fight past 8 u.
- `brain/bot.py` `vehicle_pick`, a Warthog's gun (`HOG_GUNS`: chaingun, gauss, rocket), banded like the tank drivers':
  - a man on foot within `HOG_FOOT_R` 10 u first (not for the rocket gun);
  - then a vehicle, or a man with a vehicle killer (not for the rocket gun), within `HOG_VEHICLE_R` 60 u, by the guide's score within the band (a Banshee or a tank over a Mongoose);
  - then the rest by the score.
- The rocket gun fights men on foot only while no occupied enemy vehicle within `RHOG_VEHICLE_R` 60 u is known to it (its crew in sight, or a sight line to it: `vehicle_in_sight`), and never one within `RHOG_FOOT_MIN` 6 u (its own splash). `vehicles.target_score` has a `ground_ok` argument for it; without it the anti-air hold is as before.
- `drive` (non-driver seats): the nobody-drives get-out marks that vehicle `parked_ban` for `PARKED_BAN` 20 s. `veh_banned` honours it until a rider joins the vehicle or it is driven off, so the ride order, the vehicle run and every vehicle pick skip it.
- `plan` (vehicle run on foot), every tier: with a man in view (`vehicle_way_target`), the fight's aim and trigger stay on him while the walk goes on to the seat, as on a patrol (no sprint while it does), except in the last `VEHICLE_FIGHT_LAST` 3 u, where it gets in; not while carrying or dry. A man within 8 u still turns the run into a fight, as before. Patrols already fight on the way at every tier; unchanged.
- Validation: `tools/test_warthog_guns.py` is new (17 tests: the Warthog bands, the rocket gun's rule with a vehicle in or out of sight and range, the parked ban and its lifting, fighting on the way for every tier and its exceptions). All 753 regression tests pass. **Untested in a match**: the turret droop, how often gunners now see vehicle crews (13-55% before, by kind), and the slower vehicle runs under fire.

### Reach netrelay: the bots' input reaches joined machines (no more skating); netbots=4 makes every bot a member, 2026-11-15

The owner, after netmembers2 with SnypeShee (Xbox) joined: the 3 member bots showed on his scoreboard on the right team (no red reticle on teammates) but still skated, and the other bots were missing. Then: "deep dive and figure out how we could get this to work on all our consoles with me as a host."

- **Found** (static; `docs/REACH_NETWORK_PLAYERS_2026-11-12.md`, "Why the member bots skated"):
  - A joined machine moves and animates a remote player from that player's input: a 0x4C-byte action per tick, which the host sends to every joined machine (`FUN_1803c16ec`: every simulation player's action to every type-4 view but his own machine's, queued on the view's channel by `FUN_1804212c0`). The joined machine reads it per simulation player (`FUN_180418a7c`, states 4/5).
  - The game's tick (`FUN_1800575ac`) builds the tick's input, **sends it**, and only then runs the players update (`FUN_180047050`) that botcore hooks to write the bots' input. So the bots' input never left the host. On the host the bots played normally; joined machines got positions only.
  - The membership message packs a member's user slot in 2 bits and carries no per-peer player count; a joined machine copies members with no check that a (peer, user slot) pair is unique. So more than 3 bots can share the host peer's user slots 1-3, with no made-up peers.
- **`native/reach.cpp` `hr_net_relay`** (netbots=3 and 4, host only, simulation state 7/8): right after botcore writes the bots' input, it runs the game's own relay `FUN_1803c16ec` once more for the member bots only. A bot with no simulation player gets one by the game's own `FUN_1803aa1b0`, as `player_new_at` makes it. Checks the two functions' first bytes. Logs the simulation state and, once a match per bot, how many joined machines it relays to.
- **`netbots=4`** (new; `hr_mb_add`): every bot becomes a member, on user slot 1 + (slot mod 3), skipping a slot a person (a split-screen guest) holds.
  - `hr_mb_remove_bot`: the game's remove clears the peer's slot-to-player entry even when another bot still has that slot; it is pointed back at one that does, so the game's own drop after the match still finds the bots.
  - `hr_mb_sweep`: bot members that are no live bot of this match go when a bot is added. At match end (the member guard's "match is over") netbots=4 removes every bot member, since the game drops only one a slot.
  - netbots=3 behaves as before, plus the relay. `botcore.cpp` takes 0-4.
- **First netbots=4 run** (`botcore_pg10.log`, Sakallis joined, 6 bots): all 6 became members and the host relayed all 6 bots' input to 1 joined machine, but the friend saw only 3 bots on the scoreboard, red reticles on his bot teammates, and skating. Every machine makes a game player for a member only if no player of that machine has the member's record "user" (entry +0x1C) yet (`FUN_18041f510`, the members-to-players diff), and every bot had its user slot (1-3) there: the host's own diff likewise added only bots 2-4. `netrelay2`: under netbots=4 each bot gets the lowest record user 1-7 no member of this machine has (3 bits in the message; the host is 0), so 7 bots at most; more are not added (logged).
- **netrelay2 run** (Sakallis, launcher with bots off, 6 bots): **the 3 bots he could see did not skate from their first life, and his bot teammate showed friendly (green), no red reticle.** The netbots=3 part works. He still saw only those 3: the host's own netcheck shows the type-9 adds for bots 5-7 with users 0, 1, 2, though the members had 4, 5, 6. The player record keeps the user in 2 bits, so they matched the host (0) and bots 2 and 3, and the joined machine refused them. **A machine holds 4 players at most (users 0-3); more than 3 bots need more machines (peers) in the membership.** netbots=4 is no use as built.
- **Two more netbots=4 games** (10 bots, 4 teams; 7 bot members, record users 1-7): Sakallis was kicked at the start of both. The relay already counted 0 joined machines when the bots spawned. `netrelay3`: `botcore.cpp` reads netbots=4 as 3, so a saved 4 can't do it again.
- **`netbots=5`, an experiment** (owner: "I want him to be able to see all the bots"; `standin1`): bots 1-3 stay on the host's machine. Bots 4+ go on stand-in machines, made-up peers of the membership (`hr_peer_make`: the host's peer entry as template, address and +0x138 `0xB07B07B0000000xx`, no observer, peers 16, 15, 14 down), 4 each as users 0-3. Stand-ins without bots are removed when a bot is added. At the match's end the member guard removes every bot member and stand-in. The relay logs when the stand-in set changes. Static finding: a joined machine adds each peer with a connection to its address (`FUN_18039cf80` -> `FUN_1803f6fc0`). That connection can't succeed, and when it dies `FUN_18042b164` -> `FUN_1803958cc` removes the peer there. Whether that drops the bots, kicks the friend, or neither is what the test shows.
- **It works** (`botcore_standin1.log`, a 4v4 with Sakallis joined, 6 bots: 3 on the host's machine, 3 on stand-in peer 16). He saw **every bot on the scoreboard, none skating, not even in its first life, and no red reticle on teammates**, and he was not kicked. The stand-in stayed for the whole match (the relay logged no change), and at the end the guard removed all 6 bot members and the stand-in. Still open: the bots' names show as "[UNSC]" on his scoreboard. Not yet tried: more than one stand-in (bots 8+), an Xbox friend, several friends at once.
- Validation: `native\build.bat netrelay1` built `native/bin/botcore_netrelay1.dll` (not in Git) with no new warnings; `netrelay2` likewise. **Untested in game**: whether the relayed input makes the bots animate on a joined Xbox; whether joined machines also predict the bots' shots and vehicle use correctly; and netbots=4 (lobby, MCC screens, match end, a second match, friends joining with up to 16 members).

### Reach netbots=3: the first three bots join the session's membership, the list the host sends to every machine, 2026-11-15

The owner, after the netcheck run: "Yes, dig in", then "Yes, build it".

- **Found** (static; `docs/REACH_NETWORK_PLAYERS_2026-11-12.md`, "The session membership"):
  - The host sends the session's membership as the `membership-update` network message.
  - Every machine builds its game players from its own copy. The type-9 adds of netbots=1/2 never left the host, which the netcheck log showed: each one was applied on the host at once.
  - A member belongs to a peer and takes one of its 4 user slots. The host takes slot 0, so its peer has room for 3 bots.
- **`native/reach.cpp` `hr_mb_add`** (host only; session state 4-9):
  - For bot slots 0-2 it writes a member entry at the bot's own player index, on this machine's peer, user slot 1-3. It uses the game's own entry fill `FUN_18039d8a8`, then the bot's identifier and 0x80-byte configuration (name, look, team).
  - It bumps the join and update numbers and marks the membership changed (`FUN_1803fa3d8`), as the game's add `FUN_18039d620` does. That add's `FUN_18000d6b8` (MCC's online session) is left out of this test.
  - An old bot member in the way is removed first with the game's own remove. If a person holds the slot, the bot is not added.
  - On the host, its own diff finds the slot already that bot's, with the same identifier, so its add is refused: no split screen, and the bot plays as before.
- **The member guard** `h_hr_localdrop` on `FUN_180394d48`:
  - The host drops its own peer's members whose user slot has no signed-in person (`FUN_18038f49c`), so without the guard the bot members would go at once.
  - While a match ticks (a players update within 3 s), the guard keeps bot members. After the match the game drops them itself, so none reaches the next lobby or match.
- `botcore.ini` `netbots=3` turns it on (0-3 now; netbots=1/2 unchanged). The netcheck log stays on with it.
- **First solo run** (`botcore_netmembers1.log`):
  - The three bots became members (peer 0, user slots 1-3), the guard kept them, and the host's own adds for them were refused as planned. MCC's session list at match end showed three extra entries with their identifiers and no names.
  - The next lobby's list had none of them. No second match was played.
  - The members' team came out 0 for all three, though two were on team 1. The copied configuration carried the host's wanted team (entry +0x72), which the host's team assignment `FUN_1803915a8` uses.
  - `netmembers2`: `hr_mb_add` sets +0x72, +0x98 and +0x99 to the bot's team, and netcheck's player lines show all three. Untested.
- Log lines: `netmembers: bot index N is a member (...)`, `kept bot member`, `the match is over: ... dropped by the game`, or why a bot was not added.
- Validation: `native\build.bat netmembers1` built `native/bin/botcore_netmembers1.dll` (not in Git) with no new warnings. All 73 `tools/test_*.py` files and the pool checks pass. **Untested in game**: whether the host stays stable with bot members (lobby, MCC's screens, the next match); whether a joined Xbox or PC friend sees the 3 bots with their teams and animations; and whether it disconnects them.
- **Friend run** (netmembers2, SnypeShee on Xbox, two matches): the 3 member bots showed on his scoreboard on the right team, with no red reticle on teammates, and he stayed connected. They still skated (fixed by netrelay, above), and the other bots were missing. One start hung at 0 s with friends, with no member writes that session; the cause is unknown, and later starts worked.

### Reach netbots: a log-only check of the player adds the host applies, 2026-11-15

The owner: Xbox friends joined his Reach matches with `netbots=2`, and "the same bugs from before were still there": "Skating, and same team red reticles".

- His log (`botcore_nodemonwheel.log`) had SnypeShee, on their own machine, in 5 Reach matches. Every bot's add was queued (14-15 a match), none refused or dropped, and the host played as before. The friend's game still had no players for the bots, even the three on the host's machine.
- Every machine applies the simulation queue, the host too. So the host can show whether the adds go through at all, without the friend's log (an Xbox has none).
- `native/reach.cpp` `hr_chk_hook`, hooked only with `netbots` on:
  - `FUN_1803c4004` (one queue entry applied): logs `netcheck: queue entry type 9 applied, sequence N, B bytes`.
  - `FUN_180418ff8` (one decoded player record applied): logs its index, type, identifier, machine, controller, user, team, and `applied` or `refused`.
  - Both call the game's own code first and change nothing. 300 lines per load at most. Not hooked if their first bytes differ from this `haloreach.dll` build.
- Reading it: on the host each bot's add should show as type 3, `refused` (the slot is already that bot's). If our entries never show up, they never leave the host. If they show up as other values than we sent, the encoding is wrong.
- Validation: `native\build.bat netcheck1` built `native/bin/botcore_netcheck1.dll` (not in Git). All 73 `tools/test_*.py` files pass. Untested in game.

### Warthogs drive on in a fight; Ghosts hold the boost on a run-over; a boost recorder, 2026-11-14

The owner: "I dont want any warthog driver to circle in a fight, just stick to their normal pathing. Also I want the ghost to boost when they go to run over a person. It makes it better. boosting on controller is my left trigger if that helps and you have to hold it down".

- `brain/bot.py` `drive`: a Warthog driver (any kind, `vehicles.is_warthog`) with a gunner and a man in sight no longer circles him: it drives its way on (its trip, its patrol), its gunner on the man. A light vehicle head on is still run down, and a Warthog with nobody on its gun still runs down a man on foot. Other gun carriers (Spectre, Falcon, Elephant, Prowler) circle as before.
- `brain/bot.py` `ram_boost(splat=True)` from the run-over: a Ghost holds the boost from `GHOST_SPLAT_BOOST_R` 15 u, the whole run, his man within `BOOST_CONE` of its nose to start and twice that to keep it. It was a 0.85 s tap from 8 u. Not Easy. The Chopper's charge and the other boosters as before.
- Found: in 49 recent Reach and Halo 4 matches, bot Ghosts and Banshees holding the boost went no faster than without it (about 5.5 u/s top) while people's reached 9-15 u/s. The boost the bots send (Reach: the action's +0x3C, Halo 4: the second trigger) does not seem to reach the game in those vehicles; the bits of the old decode (Reach: also +0x08, +0x48, +0xA0) were never kept.
- `tools/boost_capture.py` (new, read-only): the person's raw action (botcore's `dbg_action`) and speed every tick while he drives, and a summary of the bits on while he went fast. For the owner's test: a Ghost, then a Banshee, full throttle, the boost (left trigger) held 3 s and let go 3 s, five or six times, in Reach and in Halo 4.
- Validation: `tools/test_vehicle_fight_ways.py` (new, 7: a gunned Warthog of each kind keeps its way, a Spectre still circles; the Ghost's held boost, its reach, cone and hold, not Easy or a Warthog, Halo 4's second trigger; the recorder's summary on made-up holds). All 736 regression tests pass. Untested in a match; the boost will not take until the recorder finds its bits.

### Carriers stay in the Warthog they board, 2026-11-14

The owner: "I have a tempest game where flag carriers or bomb carriers keep hopping out of warthogs passenger seat I suspect when they start getting shot at? Investigate". Three Tempest matches (20261113-210610, -233345, -234604): 28 times a carrier left a vehicle, 27 from a passenger seat, 17 noted "vehicle: home with the flag, out". The director's board order (`ferry_orders`, `person_pickup`) points at where the vehicle stood, and the passenger rule that drops a ferried carrier on its stand fired on being 5 u from the order's point, so a carrier just in was "home" a second later: out, told to board, in again (a Demon bomb carrier 11 times in 90 s at one spot, its driver waiting for crew). Shots taken were from standing at the Warthog, not the cause.

- Brain (`brain/bot.py` `drive`, passenger seat): the "home with the flag, out" exit no longer applies on a board order. On the run home (a runner order) the carrier still gets out by its stand.
- Validation: `tools/test_carrier_board_loop.py` is new (3 tests: a boarded carrier stays in, Reach and Halo 4, every tier; the runner still gets out by its stand; not far from it). It fails with the fix removed. All 72 `tools/test_*.py` files pass. Not yet played in MCC; the other 11 exits (mostly the parked/nobody-drives rule while the Warthog waited) should go with the loop, unchecked.

### Demon precision guns fire on sight in Halo 2, H2A and Halo 3, 2026-11-14

The owner, after the Halo 2 Battle Rifle change below: "Do H2a, Halo 3, And Halo 2, and all precision weapons to the list for each ... for demon only".

- Brain (`brain/bot.py` `demon_precision_snap`, was `h2_demon_br`; `DEMON_SNAP_GAMES`): Demon only, on foot, in Halo 2, H2A and Halo 3, with any gun in `PRECISION` (Battle Rifle, Covenant Carbine, Magnum, Sniper Rifle, Beam Rifle, and the other games' names, which never match there). The same three places as below: the trigger goes with the sight of him, the press snaps to his head, `fire_gate` lets it through. Reach and Halo 4 Demons keep their own paths; Legendary, Mythic, Blind and the lower tiers are unchanged.
- Validation: `tools/test_h2_demon_br.py` rewritten for the three games and five guns (automatics, shotgun, rockets and sword excluded; CE, Reach, Halo 4 excluded; Legendary, Blind, Heroic, Mythic excluded). All 726 `tools/test_*.py` pass. Not yet played in MCC, and there are no H2A or Halo 3 recordings: the generic head point (feet + 0.62) is untested against H2A's raised body report (`H2A_FEET`) and a crouched target, and the Carbine's and Beam Rifle's hits are unmeasured.

### Halo 2 Demon's Battle Rifle fires on sight, 2026-11-14

The owner: "Check the bot Parkerr and see why he doesnt hit as much as Halo 4 or Halo reach". Midship (20261114-152922), Parkerr (Demon, Battle Rifle): 2-9. His presses landed like the other games' Demons (damage within 0.35 s on 55% of presses; Reach Demon 55%, Halo 4 65%), but the trigger was allowed only 52% of his fight time (Halo 4 Demon 78%) and fights ran 5.1 s (2.3 s). Reach's DMR and Halo 4's guns fire on the sight of him and snap the press to the part; Halo 2's BR waited on the bot's own turn-capped aim.

- Brain (`brain/bot.py` `h2_demon_br`): Halo 2 (not H2A) Demon, Battle Rifle, on foot. In `fight` the trigger goes with the sight of him and a clear line (as Reach's DMR); in `think` the press snaps to his head (`head_solution`) past the turn cap; `fire_gate` lets that press through for the selected man. Legendary, Blind, Mythic, other guns and other games are unchanged.
- Validation: `tools/test_h2_demon_br.py` is new (4 tests: only H2 Demon's BR on foot; the press snaps to the head; Legendary and Halo 3 keep their aim; the Demon fires before Legendary's aim settles). All 726 `tools/test_*.py` pass. Not yet played in MCC: whether the snapped bursts land and the fights end sooner is untested.

### No Demon Wheelman, 2026-11-14

The owner: "make it to where bots that dont drive passenger vehicles cannot get wheelman". Demon is the one difficulty that never takes a Warthog's, Mongoose's or Ghost's wheel (`vehicles.DEMON_NO_DRIVE`), so a Demon Wheelman only ever went for a tank or aircraft.

- Brain (`brain/profiles.py` `make_profile`): a Demon given the Wheelman style plays as a Flanker (the Wheelman's own on-foot traits). Every other difficulty, Mythic included, keeps Wheelman.
- Menus (`native/bots_panel.h` `HB_STYLE_WHEELMAN`, `hb_style_fits`; `native/bots_panel.cpp`): the bot editor greys out Wheelman for a Demon (tooltip: Demon never drives a Warthog, Mongoose or Ghost); Quick setup's style list does the same when the difficulty is Demon. A Demon set to Wheelman any other way (its difficulty changed, the "for everyone" bar, a Mixed deal, a saved lineup or a Bot Matchmaking saved bot) becomes Any style.
- Validation: `tools/test_wheelman.py` +1 (a Demon Wheelman is a Flanker; every other difficulty keeps it; the header's rule). All 70 `tools/test_*.py` files and the pool checks pass; `native\build.bat nodemonwheel` built `botcore_nodemonwheel.dll`. Not yet seen in MCC.

### Balance teams deals by points, 2026-11-14

The owner: the lobby's Balance teams button "just makes it to where the two teams have equal players. Can we make it to where its balancing in the sense of how our matchmaking works? ... it would put ms3s and j1br on the same team and try to balance the pts system."

- native/bots_panel.cpp `roster_balance`: after evening out the team sizes (as before), it calls Bot Matchmaking's `roster_point_balance`: clanmates (one clan tag, e.g. COD's MS3S and J1BR) move as one block, the people of the last match count 20 each, the smallest points gap wins and ties pick Demons stacked 60% / spread 40%. Team sizes and every bot's difficulty stay as they are. Not in Firefight. Each press can pick another of the equally even splits. The tooltip says so.
- native/pool_test.cpp: a 6-bot lineup all on one team comes out 3v3 with its party together.

Checks: build_pool_test.bat, all pool checks pass. Builds (botcore_balance.dll). Not yet pressed in MCC.

### Stockpile: carriers drop the flag in their goal, 2026-11-13

The owner, testing every Reach mode 4v4 with Demons: "theyll go pick up a flag one of many, and then just hold it inside their capture point. We need the bots to drop the flag once they get to the capture point and go capture others ... they wont drop it until they die". Launch Station Stockpile (20261113-220813): bot carriers walked to 0.1 u from their goal's centre and stood there holding the flag up to 32 s until killed; every bot carry but six ended in a death.

- Brain (brain/bot.py `stockpile_drop`, `STP_DROP_R` 0.8 u, `STP_DROP_DZ` 1.5 u, `STP_DROP_TAP` 0.3 s, `STP_DROP_CYCLE` 1.6 s, `STP_DROP_TAPS`): in Stockpile, a carrier on foot within 0.8 u of its own goal's centre taps a player's drop keys in turn until the flag is gone: the weapon switch (`Action.cycle`, Reach's decoded switch key) at once, then Use 0.8 s later, again every 1.6 s. It is the last step of `plan`. The trace note names the key tapped ("stockpile: dropping the flag in our goal (cycle)" / "(action)"), so the next match shows which one drops it. The flag then lies in our goal, which the director already treats as banked (within 2 u), so it is not taken again and the bot gets its next role.
- It stops first (`STP_STILL_V` 0.3 u/s, `STP_SETTLE` 0.2 s): in the goal it lets go of walk, strafe, sprint and jump, and taps only once it has been under 0.3 u/s for 0.2 s; pushed back into motion, it settles again. The owner, after the switch worked: "Theyre running and then switching weapons so the flag is thrown a little too far ... stop in the capture zone then switch weapons so momentum doesnt carry the flag".
- First try, replaced the same evening: a weapon slot choice (`act.weapon`) every tick. Live Launch Station 20261113-223850 (the owner: "they still hold the flag"): carriers sent it for seconds at the goal's centre and kept the flag.

Checks: tools/test_stockpile_drop.py is new (5 tests). All 717 tools/test_*.py pass. Which key drops the flag is not yet seen in a match.

### Territories: Land Grab told from attack / defend, 2026-11-13

The owner's bug report from Powerhouse Land Grab (20261113-222752, 466 s): "Bots are trying to capture points in territories that are already capped. Or theyre trying to defend them". He: "Land Grab is where all points are nuetral and each team fights to take them ... Once capture by either team it locks as theirs ... Each round ends when all points are capture ... Normal territories is where team defends their land and the other attacks. Can you make the distinction". The trace: the brain guesses a zone's owner (30 s held alone) and had found 2 of round 1's captures when the game scored 4-1 (all five taken) at 224 s; round 2 kept round 1's owners, so one team guarded neutral zones and the other attacked them; and the team plan sent bots at enemy zones and posted defenders on ours, which Capture Lock makes pointless.

- Variant rules (brain/mvar.py `territory_rules`; tools/live_bots.py passes them to `Watch.set_territory_rules`): Style, Capture Lock and Capture Time. MCC's own: TERRITORIES Asymmetric, lock off, 30 s; LAND GRAB Symmetric, lock on, 30 s; 3-PLOT Symmetric, lock off, 5 s. The capture time now comes from the variant (it was 30 s for all).
- Ownership (brain/modes.py `Watch.territory_round`, `score_read`, `lock_from_score`; `Snapshot.terr_lock`, `terr_style`): a new round clears every owner, told by every player dead at once (the round's end takes everyone off the map: 229.7 s, 8 of 8) or by the read score falling. With Capture Lock a zone taken stays its taker's for the round, and while the score is read (a score limit read) it decides who took what: the team that scored gets the zone it holds alone (longest first), else the one its men stand nearest (within 2 u of the edge). Replayed over the Powerhouse trace: all five of round 1's captures land as the score changes, and round 2 starts neutral.
- Team plan (brain/director.py `mode_slots`, `straight_objective`): with Capture Lock, two take the neutral zone with the fewest enemies by (and with four or more, two more the next neutral one), an escort and the overlooks cover it; no guards on ours, nobody at theirs; none left, Slayer. Easy runs at a neutral zone, mid when none is left. Without the lock (Territories, 3-Plot) the plan is as before.
- The score read from round 2 on (tools/live_bots.py `match_sane`, `match_note`; `Snapshot.score_live`): the Powerhouse trace read 0-0, limit 0 and no clock from round 2 on, the snapshot's defaults, so the match read was being dropped whole. Any part out of range dropped it all; now a limit out of 0..10000 reads 0 and a clock out of 0..24 h reads none, and the scores are kept; only scores out of range drop the read. Each kind of partial or failed read is written to the brain's log (the first 3 of each, with the raw values), so the next multi-round game shows what round 2 reads. The Land Grab tracking trusts the score while the read is kept (`score_live`), not only while a limit is read.
- Not done: the attack / defend style (Asymmetric) still plays like a symmetric game; which team defends a round is not read. Why the round 2 read was dropped is not yet seen: if it is the scores themselves that read wrong, the read is still dropped (and logged), and round 2 on falls back to the 30 s guess, locked once taken.

Checks: tools/test_land_grab.py is new (16 tests, the variant files read from this machine's MCC). All 720 tools/test_*.py pass. Not yet seen in a match.

### Demon plays the objective when near it, 2026-11-13

The owner, after a Crazy King game on Condemned (20261113-204320) that blue lost with its two Demons set to Objective: "make demon bots play the objective when theyre near it". Within 8 u of the hill those Demons chose it 3% and 13% of the time; every other bot, Easy through Mythic, 30-85%. They stood on it 2 s and 4 s of 5 minutes, red's two Easy bots 130 s and 105 s. What beat it were Demon-only scores: the gun grab a few steps off (2.95 + 0.2 kept), the stand-ground hunt on a man on its tracker (3.2), and committed fights.

- Brain (brain/bot.py `demon_objective`, `DEMON_OBJ_NEAR` 15 u, `DEMON_OBJ_MARGIN` 0.4, `DEMON_OBJ_ARM` 3 u, `DEMON_OBJ_ROLES`): a Demon on foot within 15 u of its objective point, as defender, runner or mid (the hill, a post, a flag, a watch spot; not a hunter or escort chasing a carrier), outside Slayer and Race, not carrying and not dry: guns, hunts, holds and patrols stay 0.4 under the objective. Until it is on the point (3 u) fights do too: it walks on and shoots the man in view on its way (`on_way_target`), and a man within 3 u is still fought. On the point it fights from there. Retreats are left as they were. Called in `decide` after the shot-back and close-fight lifts.
- A teammate already on it (`mate_holds`; the owner: "it can change if it registers a teammate is on the objective"): a living teammate inside the hill in King of the Hill, else within 3 u of the point and 2.5 u of its floor. Then the rule lets go and the Demon guards, hunts and fights as before; it comes back once nobody of ours is on it.
- Not changed: how the team plan hands out King of the Hill roles (blue's bots changed role 104 times that game, red's Mythic held one all game), and the other tiers' gun trips.

Checks: tools/test_demon_objective.py is new (8 tests). All 699 tools/test_*.py pass. There is no King of the Hill simulator, so this has not been seen in a match.

### Mythic difficulty: between Legendary and Demon, 2026-11-13

The owner, after going 43-0 on Warhouse against two Legendary, a Blind and a Heroic: "I am thinking we make a hybrid difficulty between Legendary and Demon". His choices: aim halfway and fixed, Demon's awareness only, the name Mythic, 10 matchmaking points. In that game the Legendary and Blind bots lost the first look (49-62% to his 69%); Blind, with hands up to 85% of the way to Demon's, did worst (3 kills, 14 deaths), so Mythic takes Demon's eyes as well as better hands.

- Brain (brain/profiles.py `MYTHIC`, `mythic_hands`, `mythic_profile`, `fixed_mythic`, `demon_eyes`): fixed Legendary (tier `top`, label `mythic`, extra None), so every Legendary rule applies, including high ground, pre-nades and the protected head / turret precision (`protected_aim`). Reaction, aim error, lag, tracking, flick, overshoot and decision time sit halfway from Legendary's base to Demon's (reaction 0.077 s, decisions 0.055 s, aim error 0.003 rad), jittered 0.9-1.1 per bot as every tier is; turn speed 675 deg/s.
- Demon's eyes (brain/bot.py `Perception.update`, now `profiles.demon_eyes`: Demon and Mythic): the 180-degree view with no edge delay, every eligible radar dot noticed, a firing man's dot standing or crouched, and the dot's drift. Demon's regen reads, fight commitment, pickups, Halo 4 / Reach direct fire and vehicle bans stay Demon-only.
- Native (bots_panel.h `HB_TIER_MYTHIC 8`, `HB_TIERS 9`; bots_panel.cpp, botcore.cpp, overlay.cpp, shared.h): tier key `mythic` (botcore.ini `bot=` lines), "for everyone" difficulty 9 (`difficulty % 10`, play.py `--tier mythic`), 10 matchmaking points, rank tours 8-10, rose colour, Demon's five chevrons. The pickers show Easy, Normal, Heroic, Tactician, Legendary, Blind, Mythic, Demon, Mixed, Scaling. The footer picker is 660 units wide (was 600) and Quick setup 680 (was 620), so each button keeps its old width. In the bot inspector the second row is Tactician, Blind, Mythic and Demon, and Scaling moves to a row of its own. Mixed still deals Normal, Easy, Heroic, Legendary, Demon and Blind, without Mythic.
- Tools: botctl `TIER_KEYS` / `DIFFICULTY_TIERS`, the Observer's, player_stats' and match_export's names.

Checks: `native\build.bat mythic` built native/bin/botcore_mythic.dll (only the existing `_wfopen` warnings; panel_art.py's PIL step fails as before); `native\build_pool_test.bat` passes with Mythic's 10 points. tools/test_mythic_difficulty.py is new (7 tests; the two eyes tests fail with Demon's eyes off). test_demon_difficulty, test_tactician_difficulty, test_bot_matchmaking and test_mcc_ranks read the native source and are updated for the new tables. All 691 tools/test_*.py pass. The panel's new layout has not been seen on screen, and Mythic has not been played.

### The lobby bots' own emblems in MCC, 2026-11-13

The avatars worked live. The owner, showing their own emblem beside their name: "Make them do the same". A bot in a match already showed its own emblem (brain/looks.py `emblem_of`, sent with the add), but in the lobby nothing had sent it yet, so MCC's rows drew its default.

- brain/emblems.py: `export` also writes each bot's five emblem numbers to native/bin/emblems/<name>.ids, even without the art (no PIL: the numbers still go out). They are the same numbers a match sends (checked: Wheezy 233 568 30 2 5, Oreo 94 585 30 31 20 from both).
- native/report.cpp: `report_lobby_emblem` reads <name>.ids for a lobby bot's row; MCC's default until it is there.
- native/session_watch.cpp: a lobby bot without its numbers is asked of tools/looks_export.py --emblems in the background (20 s apart, three tries a name). Whether each bot's emblem is there is part of the lineup's hash, so MCC gets a new list once it arrives. The panel's own request only runs for the mod's drawn rows, which step aside while sessionbots is on.
- Seeded by hand: the numbers for the 444 bots that already had an emblem picture (game data, not in git).

Checks: `native\build.bat emblems` built native/bin/botcore_emblems.dll (only the existing `_wfopen` warnings; the PIL step fails as before). That build also holds the working tree's uncommitted Mythic work. brain/emblems.py selftest passes. Not yet run in MCC.

### The bots' own avatars in MCC, 2026-11-13

The Career numbers worked live (Wheezy: 0 won, 16 kills, 8 deaths, 1 assist, its leaderboard line). The owner: "Can you have the bots player details page have them pick a unique or random avatar?"

- native/report.cpp: MCC's player lookup's +0x14 is the avatar. MCC's unknown-player fill sets 6 (PlayerIDAvatar_001, the grey helmet every bot showed). MCC's avatars are <MCC>\Data\UI\playercustomization.xml's `<Avatar id>` 1-116, read once at start (found from MCC's own exe path). A bot's avatar is drawn from its name (its own hash, not the nameplate's or the rank's), so it is the same in the session list, Player Details, Career and the post-game report, every match. Ids that are not 1..n without a gap, or a catalog that cannot be read, leave MCC's default. The start line logs how many were read.

Checks: `native\build.bat avatars` built native/bin/botcore_avatars.dll (only the existing `_wfopen` warnings; the PIL step fails as before). That build also holds the working tree's uncommitted Mythic work. Not yet run in MCC.

### MCC's Career page: the bots' own numbers, and a leaderboard, 2026-11-13

The watch above never ran: the Career page the owner opens (Player Details > Career > Multiplayer: Total Games Won, Kills, Deaths, Assists, with "Compared to you") is filled by another function. Read statically instead, it showed exactly where a bot's zeros come from, so this goes straight to the numbers. The owner asked for a leaderboard ("me and the bots. Kills, Deaths, Assists, K/d") and for the bots' stats on their Career page.

- tools/bot_career.py (new): everyone's totals (games, won, kills, deaths, assists) from MCC's post-game reports: every logs/trace_*.carnage.xml and MCC's current report, each match once by its GameUniqueId in a ledger (native/bin/career/ledger.json), so they outlive the recording rotation. A match counts when its person played 60 s or more; a win is first place (mStanding 0) unless everyone is first (a draw). It writes native/bin/career/totals.txt and, run by hand, prints the leaderboard by K/D (--by kills|deaths|assists|games). The first run: 45 reports, 42 matches counted (three quick quits).
- tools/play.py: runs it in the background (--quiet) as each match starts, right after the last match's report is kept.
- native/career.cpp (was career_watch.cpp): FUN_1404A0EA4(page) fills the Multiplayer tab; the shown player's id is page +0x16F0, and its stats come from MCC's player records (FUN_14024B924, none for a bot's id). Each row has its stat code at +0x200 (0x0EC28B21 won, 0x6AD86331 kills, 0x75D204D0 deaths, 0x539C9E21 assists), and FUN_140318E94(row, text) copies the row's number text in (its length +0x14, its bytes +0x18, nothing else read). While a bot's page fills, those four texts become the bot's totals (with commas, as MCC writes them). "Compared to you" stays MCC's (your own numbers). Matchmaking and Custom Games show the same numbers. totals.txt is read again when it changes. Guarded by both prologues and the two instructions read.
- native/report.cpp: `report_bot_name`, a bot's name by its made-up id (a match's or a lobby's).
- tools/test_bot_career.py (new): one match kept once, quick quits left out, wins and draws, totals outliving a deleted report.

Checks: `native\build.bat career` built native/bin/botcore_career.dll (only the existing `_wfopen` warnings; the PIL step fails as before). That build also holds the working tree's uncommitted Mythic work. tools/test_bot_career.py passes. Not yet run in MCC: a bot's Career page with the numbers.

### MCC's Career page: a watch-only log of its stats, 2026-11-13

The rank badges worked live (MCC's rank table: 330 ranks, every bot its own badge). sessionbots=2 put the session leader's crown on every bot and still no team colour, so the owner's botcore.ini is back to 1 (local). The owner wants the bots' Career page to show stats ("can we just fake their stats? What can that hurt?"), from the 45 matches' carnage reports the mod keeps in logs/. A bot's Career page shows zeros today. The owner: "Yes, build it" (the watch first).

- native/career_watch.cpp (new): hooks FUN_140527A50(page, column), the Career page's multiplayer fill ("populateContentMultiplayer"). It logs, when they change: the column (0/1, each stat holds two 0x38 columns), the game (page +0x1008), games played, won, first places, kills, headshots, assists, betrayals, best spree and deaths (0x70-byte entries from +0x1988, a byte at +0 and the value at +0x20; the offsets paired with their $SR_ / $CAREER_ labels from the disassembly), and the offsets in the page holding an Xbox id or a bot's made-up id. Nothing is changed. Prologue checked first.
- Ruled out: FUN_14049DA34 parses the player's own progression JSON (XP), and FUN_140338E48 / FUN_140344990 (MCC's one call into XblUserStatisticsGetMultipleUserStatistics...) carry campaign scoring stats. Neither is the multiplayer Career page.
- native/session_watch.cpp starts it (so botcore.cpp, which holds the teammate's uncommitted work, is not touched); native/build.bat compiles it.

Checks: `native\build.bat careerwatch` built native/bin/botcore_careerwatch.dll (only the existing `_wfopen` warnings; the PIL step fails as before). That build also holds the working tree's uncommitted Mythic work. Not yet run in MCC.

### MCC's session list: the lobby bots' rank badges, 2026-11-13

All 9 bots showed under MY GAME SESSION (PLAYER COUNT 10), the post-game report kept the match's bots, and the list refilled with the next lineup. Every bot had the same bronze badge. The owner, on team colours or badges: "Which ever you can make way on first".

- native/report.cpp: MCC's player lookup's +0x80 is HaloStatsPlayerXP (the key names, FUN_1400C6CB0). MCC's unknown-player fill leaves it 0, the lowest badge. MCC turns XP into its account rank with a table it loads at start: manager [0x144001500], ready at +0x138, entries +0xD8..+0xE0 of 0x88 bytes (+0x20 the XP a rank starts at, +0x24 level, +0x28 prestige; FUN_140347264 / FUN_1403472E4). A lobby bot's lookup now gives the XP its rank starts at. That rank is the one the mod already draws for it, from its name and difficulty (bots_panel.cpp `bot_rank`, tour = prestige + 1). The table's level numbering (0- or 1-based) is read from the table, and the first read is logged. Guarded by the table global's load in FUN_140499908 and the level lookup's head. A match's bots are unchanged.
- native/session_watch.cpp: each bot's difficulty goes to its row, and is part of the lineup's hash (a changed difficulty asks for a new list).
- Team colours: the owner's botcore.ini is set to sessionbots=2 (the player's session flags, the team at +0x64; already built, untested). Local setting only.

Checks: `native\build.bat sessionranks` built native/bin/botcore_sessionranks.dll (only the existing `_wfopen` warnings; the PIL step fails as before). That build also holds the working tree's uncommitted Mythic work. Not yet run in MCC: whether the roster's badge reads the profile's XP, the table's log line, and mode 2's team colours.

### MCC's session list: every lobby bot, 2026-11-13

The refresh worked (the bot was on MCC's first list in the lobby, and after a match another lineup's first bot took its place). The owner: "Yes add all the bots", up to 15 (the most the roster holds).

- native/session_watch.cpp: every bot in the lobby's roster (up to 15; 16 places) is appended to MCC's list, in roster order, each in its own node from MCC's builder, id 0xB07B07B1000000<place>. The refresh compares the whole lineup (a hash of names and teams), so a changed lineup, bots turned off or a return from a match asks MCC for a new list. Modes 1 and 2 are as before, per bot.
- native/report.cpp: the lobby's bots get their own table (`g_lobby`, ids 0xB07B07B1...) instead of the match rows' table. Before, the one lobby bot at index 15 could replace a finished match's 15th bot in the post-game report, which is opened from the menus too. `row_number` / `row_at` serve both tables for MCC's name and profile lookups; the `lobby` flag is gone.

Checks: `native\build.bat sessionall` built native/bin/botcore_sessionall.dll (only the existing `_wfopen` warnings; the PIL step fails as before; a first try failed because `SW_MAX` is a windows.h ShowWindow constant, now `SW_LOBBY_ROWS`). That build also holds the working tree's uncommitted Mythic work. Not yet run in MCC: whether MCC draws all of them, the player count, Start, the bots' Player Details, and the post-game report after a match.

### MCC's session list: the lobby bot without waiting (MCC asked for the list), 2026-11-13

The one-bot test worked: Wheezy came up under MY GAME SESSION, with the player and above the friends, in MCC's own row (the clan tag, nameplate and rank from the mod's lookups), but only about 90 s in. MCC sends that list only when something changes (that time, a friend's status). The owner: "Instant refresh first".

- native/session_watch.cpp: in the menus, when the bot on MCC's last list is not the one wanted (another first bot, bots off, back from a match), MCC's own list request FUN_14024E458(session [0x144000D08], 0) is called. It stamps the session's +0x1D8, and MCC's own session update (FUN_140246070) sends the list on its own thread a moment later. The UI roster system asks the same way. A small thread checks once a second; requests are at least 3 s apart, at most 5 for each change. The request's bytes are checked first (the head and its `cmp [rcx+1D8h],0`); any mismatch leaves it off.

Checks: `native\build.bat sessionrefresh` built native/bin/botcore_sessionrefresh.dll (only the existing `_wfopen` warnings; the PIL step fails as before). That build also holds the working tree's uncommitted Mythic work. Not yet run in MCC: how soon Wheezy now shows, and the player count, Start and the bot's Player Details, are untested.

### MCC's session list: one lobby bot as a test (sessionbots=), 2026-11-13

The watch's first live log (a Reach custom game lobby) showed the list holding the owner and a second person, and only the owner while the match loaded. It never held the bots. The owner explained that the second person "was just on my friendslist in the lobby never in my game", so the list carries friends too, with their own flags. The owner: "Yes, try one bot".

- **`native/session_watch.cpp`**: with `botcore.ini` `sessionbots=1` or `2` (default 0, off), the lobby's first bot is appended to MCC's session list in the menus only. It is added before the roster system and the menus receive the list, and only while MCC is in its menus with a person on the list and bots on.
  - **The entry:** it is built by MCC's own entry builder (FUN_14024F054) in memory from MCC's own allocator (FUN_1409300F4), so MCC frees it with the message. Its id is `0xB07B07B00000000F`.
  - **Mode 1:** the entry as built, with the friend's numbers (-1, -1, -1).
  - **Mode 2:** also takes the player's two "in this session" flags and +0x15, the bot's team at +0x64 (a guess), and the player's +0x6C.
  - Both builder prologues are checked; another MCC build leaves it off. The log says when a bot is added.
- **`native/report.cpp` `report_note_lobby_bot`**: that id's row (name, service tag, clan tag, MCC's default emblem) is marked as a lobby row. It is never a Halo CE post-game row, and a match's add at index 15 replaces it.
- **`native/overlay.cpp`**: while `sessionbots=` is set, the mod's own drawn session rows step aside, so only MCC's list shows.
- **`native/botcore.cpp`**: reads and saves `sessionbots=`.
- Validation: the DLL builds (`botcore_sessionbot1.dll`). **Untested in game.**

### MCC's session list: a watch-only log, 2026-11-13

The owner wants the bots as rows in MCC's own MY GAME SESSION list. MCC's post-game report and Player Details already take the bots' made-up ids, with Career all 0 and no crash. A static read of MCC (Oct 31 2026 exe) found one function, `NotifyUIOfSessionMemberUpdate`, that builds the session's players as a one-way message for the roster panel and the menus. The owner: "Yes, build it" (the watch first).

- **`native/session_watch.cpp`** (new; `session_watch_hooks` from `botcore.cpp`, added to `build.bat`): it hooks that function (only to note which caller sent it) and the roster system's receiver. Each time the list changes, it logs one `session list:` line: each player's id, name, second string, flags and numbers, plus the caller. Nothing is changed or added. The prologues and the call site are checked first, and any other MCC build leaves the watch off. The log is capped at 400 lines.
- Validation: the DLL builds (`botcore_sessionwatch.dll`). **Untested in game**, and no bots appear in MCC's list yet.

### Bot Matchmaking: parties, Name*N turns and teams dealt by points, 2026-11-13

The owner: a "party system" so bots "that have the same clan tag are always on the same team" and come up together; "the reason I have duplicate names is to represent the same player"; "a point system to each difficulty so when a lobby is made that bots are balanced to each team based on the overall points per team", only from the seats' own bots ("I don't want the script to search out perfect teams ... take the next 7 players and balance them"); "make human players 20 points"; of the even splits "40% B style and 60% A style"; then "Implement it", with the `*5` lines. His picks: the Group parties button (not the party helper), rebalance only when a lobby fills, Scaling 8 points, 3-4 team games balanced as close as it can.

- **`Name*5`** (`native/bots_panel.cpp` `pool_line`, `bot_pool_load`): one bot_pool.txt line, one bot (the same profile, player card, saved difficulty and style), its turns (1-99) spread evenly through the queue: turn j of line i at i + j × lines / N, the lines' own order kept. A file with no `*N` reads exactly as before; repeated lines still work; `*abc` is part of a name; a long name keeps its `*N` past the 15-character cut. The editor's rename keeps the `*N`.
- **Points** (`tier_points`, `HB_HUMAN_POINTS`): Easy 1, Normal 2, Heroic 3, Tactician 5, Legendary 8, Blind 8, Scaling 8, Demon 12, a person 20.
- **Teams dealt by points** (`roster_point_balance`, from `bot_pool_rotate`: after each match and when Matchmaking is switched on; not after a swap or a hand move, not in Firefight): the seats' own bots only, the team sizes as seated kept, the people counted on their team. Two teams: every split tried, the smallest gap kept; of the splits tied for it, A style (the Demons 2 or more apart) 60% of the time and B style (spread) 40%, one at random; a style with none: the other. Three or more teams: the strongest first to the lowest total with room, then equal-size swaps while the totals come closer.
- **The people** (`tools/play.py` `save_humans`): each team match's people, a `human=<team>` line each, in `native\bin\bot_pool_humans.txt` (not Firefight, not free for all; "Bot ..." leftovers are not people). Read with the pool; none yet: you alone on Red. A team changed in MCC's lobby after the deal is not seen until the next match.
- **Parties**: bots whose profiles share a clan tag. The deal moves a party as one block (cut to the biggest team's size), so it always plays on one team. When a seat takes a bot in a clan, its free clanmates (from anywhere in the queue, the queue position kept) take the next seats 70% of the time, as many as the biggest team holds.
- **Group parties** (Settings, beside Reload pool; `bot_pool_group_parties`): bot_pool.txt rewritten with each clan's bots together where the first of them stood, a round per repeat, every line, repeat, `*N` and note kept; the old file kept as `bot_pool.txt.bak`.
- **The lobby**: each team card shows its points (and "+ you" where the person is counted); Settings explains `Name*5`, parties and the points.
- Validation: `native/pool_test.cpp` checks 19-24 (the turns' order, the rename, the points, the owner's 8v8 even in 2,000 deals with the Demons stacked in 59.4%, the 4v4 within 1, three teams within 2, a party never split, clanmates pulled in 68.7% of 300 fills with the queue kept, the people read and counted, the grouped file and its backup); check 3 now expects the team sizes kept, not each bot's team. All pool checks pass. `tools/test_bot_matchmaking.py` +1 (the people saved). All 65 `tools/test_*.py` files pass. DLL `botcore_matchmaking.dll`. **Untested in game.**

### Wheelman: first claim on a Warthog's wheel, 2026-11-13

The owner: "Make wheelman get priority for driving warthogs". The director already sent a Wheelman first when it handed out wheels (`profiles.driver_priority`), but any other bot with a long trip still took a free Warthog on its own, or kept a driving job given before, while a Wheelman walked to it.

- `brain/director.py` `wheel_dibs_of` / `wheel_dibs_of_bots`, each update: the Warthogs (any kind: `vehicles.WARTHOGS`, `is_warthog`) a Wheelman of ours, alive and on foot, is on his way to. Every bot of the team gets them (`wheel_dibs`).
- `brain/bot.py` `wheel_yield`: any other bot of ours, Easy too, leaves those Warthogs' wheels to him, in its own vehicle pick, a committed run to one, a spawn errand, an order to drive one, and at the door: it thinks again. Its gun or passenger seat, or a call aboard, is still its to take. A bot already at a wheel stays there. A Wheelman never yields.
- `brain/director.py` `crew_orders`: no driving job on those Warthogs for anyone else, and one already given is dropped. `wheel_calls`: a person on such a Warthog's gun waits for the Wheelman on his way rather than another driver.
- Validation: `tools/test_wheelman.py` +4 (whose dibs, every Warthog kind, none for a Ghost or from a seat; who yields; a crew job dropped and none given, as before with nobody on his way; a person on the gun). All 683 regression tests pass. Untested in a match.

### Pre-nades for Legendary, Blind and Demon: a grenade at the doorway before the fight, then the angle held, 2026-11-13

The owner: "How could we make a demon and legendary bot use pre-nades? ... when I 1v1 them I can throw a grenade at their doorway before seeing them due to knowing the radar ... I turned off their opening grenade because that lost them gunfights but a pre nade would work if done right?", then "Build the first one, the grenade arc isn't super important right now but note that for later ... make only legendary blind and demons use the pre nade mechanic".

- `brain/bot.py` `Bot.prenade` (called from `plan` on foot, not fighting, not retreating), `prenade_ok`:
  1. **The read**: an enemy it cannot see, known within `PRENADE_FRESH` (2 s) by its eyes, radar, a hit or a callout, 4-26 u off, moving its way (heading within 70 degrees of the line to it).
  2. **His doorway**: the walkable way (`Terrain.path_ahead`) from where he is now (Demon: `anticipate.predict`; the others: his last place, on along his heading) to the bot; the first point of it the bot has a line to.
  3. **The timing**: his time there at a run (`anticipate.RUN_SPEED`, 2.25 u/s) within `PRENADE_ETA` (1.0-2.5 s: the grenade's flight and fuse); earlier he waits it out, later he is through. Looked for every `PRENADE_EVERY` (0.25 s).
  4. **The throw**: the view turned onto the doorway's floor (up to `PRENADE_TURN` 0.8 s, to within `PRENADE_ALIGN` 0.12 rad), the button held `PRENADE_PRESS` (0.3 s), then the angle held standing `PRENADE_HOLD` (2.5 s), the gun up; the next grenade `PRENADE_COOLDOWN` (6 s) on. A man in view ends the hold (the fight takes over).
  5. **Never**: with a man in view (that was the opener's cost), a teammate by the doorway (`nade_clear`), the doorway within 4 u of itself or past 20 u, carrying the flag, in a vehicle; once per man per `PRENADE_PER_MAN` (10 s). The objective grenade waits while a pre-nade is on.
- **Who**: fixed Legendary, Blind and Demon (`fixed_high`, not Tactician, not Scaling); `LEGENDARY_GRENADES` must allow them. Other tiers, the opener (still off for them) and the fight's grenades unchanged. `PRENADE = False` turns it off.
- **For later (the owner: "note that for later")**: the throw has no arc yet, `PRENADE_LOFT` 0: the grenade goes along the view onto the doorway's floor, fine near, short or long farther off. Two ways to add it: a range-to-loft table per game from a throw test (a bot throwing at set pitches, the landings noted), or native reads of grenades in flight and of grenade counts (live reads neither now, so a bot with none presses for nothing and still holds the angle).
- Validation: new `tools/test_prenade.py` (6, a corridor whose doorway is 6 u off: Legendary, Blind and Demon throw at once for a man due in 1.1-2.3 s, the button held, then standing with the eyes on the doorway; Easy, Normal, Heroic, Tactician and Scaling never; due in 6 s or 0.4 s, in view, walking away, a teammate by the doorway: none; once per man per 10 s; the switch). All 65 `tools/test_*.py` files pass. Python only. **Untested in game**: where the grenades land with no arc.

### Demon commits to a kill: waits for a hurt man out of sight, switches only for a reason, 2026-11-13

The owner: "Why do demons during a gunfight look away if LOS is broken for just a second if they have a memory of where I am?", then "I want it to have the best chance at killing anyone, always having an advantage but I also want it to commit to a kill", and on the middle ground proposed: "Yea we can test that makes those changes".

- **What the traces showed** (six Reach matches, Nov 12, ~700 breaks of sight on the man a Demon fought): in 84% its view stayed on where it believed he was. The 16% that swung 60+ degrees away: another man close and aiming at it took over 0.03-0.2 s after the break (`demon_commit`'s "the one we fight looking away" is always true of a man out of sight); the man was let go after 0.8 s (1.6 s shield down) and a hunt, an item or an objective took over at 1.3-1.8 s; a radar dot's hunt (3.2) beat the kept fight (2.9) once he was out of sight (`turn_ok` lets any dot win then); at a vehicle's wheel, the drive.
- **How long it waits** (`brain/bot.py` `Bot.demon_wait`, `demon_waiting`): for the man it fights out of sight, `DEMON_WAIT_HURT` (3 s) while his shield is low by its reckoning (`est_shield` 0.5 or less; it reckons the recharge from 2 s after the hit, so about 2.8 s in practice), else `DEMON_WAIT_FULL` (1.2 s).
- **While it waits** (`demon_commit`, `demon_easier`): another man takes over only hitting it (`shot_by_other`), at arm's length (1.5 u), or as an easier kill in view: his shield 0.25 or less (no shields: his body half), or `DEMON_EASIER` (0.5) less shield and body than the Demon and not looking its way. A close man merely aiming at it no longer does. Halo 4's `chase_ok` still lets the man go.
- **Radar dots** (`decide`): while it waits, a dot's hunt only by the usual rule: the dot under half his distance, or the man there shooting it. A shot from behind still turns it.
- **A hunt for the man it fought** (`plan`, `commit_carry`): its eyes on where it believes he is, chest high (attention "commit"), not along its path.
- Unchanged: in view (`COMMIT_HOLD`, `COMMIT_MARGIN`), retreats to recharge, re-arming, the team spread, the drive. Demon only; Legendary and the rest as before.
- Validation: `tools/test_demon_anticipate.py` (56): the waits for a healthy man (kept at 1.1 s, let go at 1.3 s) and a hurt one (kept at 2.5 s, let go past 3 s) replace the old 0.8 / 1.6 s test; a close man aiming kept off, a cracked, a weaker-and-looking-away and an arm's-length one taking over; a dot at 6 u waiting, one at 3 u checked, the man 10 u off; the hunt watching him, Legendary not. All 64 `tools/test_*.py` files pass. Python only. **Untested in game.**

### Easy keeps moving, part 2: hunts, posts, giving up sooner, neighbouring zones, 2026-11-13

The owner, choosing from the proposals for Easy's idle time: "1-5 not 6".

- **1. No standing at an empty hunt spot** (`brain/bot.py` `Bot.plan`, `EASY_HUNT_DONE` 3 u): within 3 u of where it last knew of a man, Easy walks on to its roam point instead of standing there looking about (it stood 13-67% of its hunt time, Nov 12).
- **2. Circling at posts** (`Bot.loiter` `brisk`, `EASY_LOITER_R` 6 u): at a post (an objective point, a hold) Easy circles up to 6 u round it (others 2.5-4) and goes on to the next spot as soon as it reaches one, or after 3 s, with no stops. A zone it must stand in or the hill keeps its own radius, brisk too; a zone too small to walk in keeps its shuffle.
- **3. Jumping and dropping when stuck: no change.** It is there already: the unstuck wiggle jumps for every tier, Easy included ("getting unstuck is navigation: every tier jumps"), and the edge guard stops only at a fall (it turns another way after a while). The "step down" notes in Easy's traces are the guard letting a planned step down through, not a stop.
- **4. Giving a goal up sooner** (`Bot.headway`, `EASY_HEADWAY_S`): the existing clock, which bans a goal (a gun, a hunt spot, an objective point) with no headway, runs 3.5 s for Easy instead of 6. Zones, the hill and a carrier's run stay exempt, as for everyone.
- **5. Neighbouring zones** (`Bot.roam`, `EASY_ROAM_NEAR` 30 u): Easy's next roam point is a zone 8-30 u off and not the one before the one it just reached, so it walks round the map instead of back and forth or across it; none that near: any, as before.
- `Bot.easy_mover`: fixed Easy (not Scaling), for all of these and the fight on the move.
- Validation: `tools/test_easy_moving.py` +5 (11: the empty hunt spot through `think`, Normal still walking to it; brisk loiter's next spot at once, not otherwise; Easy's ban at 3.5 s, Normal's at 6; neighbouring zones only for Easy, Normal anywhere; no back and forth over 12 roam picks). All 64 `tools/test_*.py` files pass. No match simulator here: the gain is not measured. Python only. **Untested in game.**

### Easy keeps moving: no stalled roam points, fights on the move, 2026-11-13

The owner: "I would like to make easy actually move a lot and not stall so much. They don't have to be able to shoot or retrieve obj, or drive. Just to where they roam a lot more actively without stopping".

- **What the traces showed** (seven live matches, Nov 12, `logs/tmp`-style scan of each Easy bot's speed over 2 s): Easy stood (under 0.5 u/s) 18-60% of its time on foot. In fights it stood 37-65% of the time; roaming 3-58%, worst on Spire (32%) and Boneyard (58%), among wall, step-down and "floor not in the nav" notes. One Easy Camper (WonderBird, Spire) stood 203 s, goal roam, its next waypoint the spot it stood on: `Bot.roam` only picked a new zone centre within 3 u of the old one, so one it could not get to was kept for good.
- **Roam** (`brain/bot.py` `Bot.roam`, on foot): a roam point with no `ROAM_STALL_D` (2 u) of headway in `ROAM_STALL_S` (4 s) is given up for `ROAM_BAD_S` (60 s), and a new one is drawn at least `ROAM_MIN_D` (8 u) off (8 draws; else any). Every tier's roaming; a vehicle's roam (no clock) as before.
- **Easy's fights** (`Bot.plan`, `EASY_FIGHT_MOVING`): an Easy bot (not Scaling) fights walking on to its roam point, its fight's aim, trigger, melee, grenade and reload as before, no sprint. Normal and up fight as before. `EASY_FIGHT_MOVING = False` puts Easy's back.
- Objectives and driving unchanged (the owner: not needed).
- Validation: new `tools/test_easy_moving.py` (6: a stalled roam point given up after 4 s and marked, a new one 8 u or more off; one walked toward kept 8 s; without a clock as before; Easy fighting a man 10 u off walks at full speed toward its roam point, not sprinting, its fight running; Normal and the switch off fight as before). All 64 `tools/test_*.py` files pass. This install has no match simulator, so the gain is not measured. Python only. **Untested in game.**

### Man cannons the owner draws: bots ride them, 2026-11-13

The owner: "Do bots use man cannons much? I've seen on adrift halo 4 they've never used them I don't think". Seven Adrift (`h4_ca_warhouse`) match traces: bots rode its two gravity lifts 3-20 times a match, and the man cannon the owner drew in the LiDAR view on Nov 9 (`owner_rides.json` "Man cannon 1", (13.5, -12.5, 2.7) to (16.5, 5.0, 2.4)) never, though the owner rode it 3 times and bots stood by its pad often. The map's data has no man cannon of its own.

- Why: the nav scored the drawn cannon as a 17.8 u jump (27.6), dearer than the 23.9 walk round, so it never took it. Taken, a flat ride ran as a jump: judged short 1.5 s on, and the jump window steered for the landing from off the pad.
- `brain/maps.py` `owner_ride_links`: a drawn man cannon's link is marked `launch` with its airtime, `air_s`, at `OWNER_CANNON_SPEED` 7.5 u/s along the flat (the owner's rides of Adrift's: 17.8 u in 2.14-2.42 s). Adrift's: 2.37 s.
- `brain/terrain.py` `add_links`: a `launch` link takes the launch cost by its airtime (as rides 10+ u up already did), however flat: Adrift's cannon 6.3 now.
- `brain/bot.py`: `cannon_of` (the airtime of a drawn cannon's ride a nav jump is), `ride_cannon` and `on_cannon`. A bot onto the pad, on across it toward the landing (no jump), then steering for the landing all the flight. Done when down within 1.5 u of the landing. Never thrown (4 s on the pad, 6 s not reaching it) or short (the airtime + 2 s): that take-off is left 60 s (`jump_blocked`). The edge guard and the unstuck wiggle stand aside during a ride. A ride left over 8 s past its airtime (a death, a fight) is dropped with no verdict. Lifts, and cannons in the map's own data, ride as before.
- Validation: `tools/test_owner_rides.py` +5 (the launch flag and airtime; onto the pad, thrown, landed; never thrown leaves the take-off; a stale ride dropped; on Adrift the cannon costs under 10, the nav from its pad offers it, the bot knows its airtime). Adrift's nav: from three spots by the pad, toward the landing and past it, the next step is the pad, then the cannon; toward the east lift it is not. All 656 regression tests pass. Untested in a match: whether bots reach the cannon's trigger and land where expected.

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

### Reach Headhunter: bankers bank, drop points move on, four team scores, 2026-11-12

The owner: "check the last match in observer and see how the bots played headhunter", then "Yes, fix all three". On live Launch Station Headhunter 20261112-223426 (4 teams of 3, drop points moving every 30 s), the owner's team's bots banked 3 of its 49 points and the bots died carrying about 450 skulls between them.

- A banker carrying skulls to a drop point (director.hh_bankers) scores 3.2 + 0.1 a skull (up to 8) for it (bot.HH_BANK_SCORE). Before it scored 0.7-1.7 and lost to a hunt's 3.16; one bot with 13-16 skulls hunted round the live drop point for 20 s and died with them. Now it beats a hunt with 1 skull and a seen enemy's fight (3.41) with 3. A skull runner sent to a loose skull is unchanged.
- The live drop point is kept for the variant's "Drop point movement time": mvar.drop_point_move reads it from the game variant file, live_bots passes it to the mode watch, and headhunter.Skulls takes it ("never": for good; not read: 30 s, was 90 s). A drop point found dead is skipped for at most that long too. Before, the bankers ran to a drop point 75 s after it had moved.
- Reach reads the scores of teams 2 and on (live.LiveReach.more_team_scores): only in a team game, only for teams a player is on, and only a plausible value, so a bad read cannot fail the whole score read. The offsets past blue (8 bytes apart) are assumed, not checked against the HUD.

Tests: 15 new in tools/test_headhunter.py (move time, the variant option, the scores of teams 2 and 3, and banking over a hunt on Headlong; the two bank tests fail with the boost off). All 612 tools/test_*.py pass. Untested in game.

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

### Reach: a test that sends the game's own player add for each bot, for a friend in the match, 2026-11-12

The owner, after the first two-PC test: "Yes, start that" (reverse-engineer how Reach tells joined machines which players exist), then "Yes, build it".

- **What the logs showed** (a 4v4 with 6 bots, the friend joined with bots off): the host's game had 8 players, the friend's only the 2 people. Every bot body on his side had no player: unit +0x1CC, a unit's player link, was empty.
- **Why** (read from `haloreach.dll`; `docs/REACH_NETWORK_PLAYERS_2026-11-12.md` has the addresses):
  - Every machine makes its players from "player update" entries (type 9) in the simulation queue.
  - The host sends those only for the session's members (its sender `FUN_1803aafa4`).
  - `hr_add_bot` makes each bot with `player_new_at` on the host only, so no add ever went out for a bot.
- **The test, off unless `botcore.ini` says `netbots=1` or `netbots=2`:**
  - `native/reach.cpp` `hr_net_add` builds the 0xB8-byte record for each new bot: its index, player identifier, add, machine, and the configuration it was made with.
  - `hr_net_pump` sends it the way the host's sender does: the game's encoder (`FUN_1803c7ce0`), then a type-9 queue entry (`FUN_1803c414c`, `FUN_1803c4290`). It sends only while the host's own sender would (the same session checks) and never in a film. It retries each tick for up to 600 ticks.
  - The code checks the first bytes of each function it calls and refuses if they differ from this `haloreach.dll` build.
  - A machine can hold only 4 players. With `netbots=1` every bot has no machine. With `netbots=2` bot slots 0-2 go on the host's machine as controller/user 1-3, and the rest have no machine.
  - On the host the add does nothing: the slot is already that bot's, with the same identifier.
  - The log says `netbots: player add queued for index N`, or why it was not sent.
- `native/botcore.cpp`: `g_netbots`, read and written as `netbots=` (0, 1 or 2; anything else reads as 0).
- `hr_net_dump`'s player lines add the player's identifier, machine slot, controller and user, so the host's and the friend's logs can be matched.
- Validation: `native\build.bat netbots1` built `native/bin/botcore_netbots1.dll` (not in Git) with no new warnings. All 55 `tools/test_*.py` files and the pool checks pass; none of them can run the game's network code. **Untested in game**: whether the friend's game takes the adds, links the bodies to the players and animates them; and whether the host stays as it was.

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

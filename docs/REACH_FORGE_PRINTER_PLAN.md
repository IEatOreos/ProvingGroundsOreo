# Reach Forge Printer — Project Plan

Status: Phase 1 done (2026-11-21): built, committed locally, and the edited
variant loaded in Reach Forge with its wall moved. Phase 2 done (Halo 3
reference, scale 0.975). Phase 3 core done (2026-11-21): Guardian's floors,
straight ramps and walls are fitted with Forge pieces and three prints have
loaded in the game; see "Phase 3, part 7" for what is left. Phase 4 not
started. Separate tool from the Project Reach bot code.

## Goal

Build Halo: Reach Forge maps in Blender and export them straight to a Reach
map variant file (`.mvar`) that MCC loads — no keystroke bot. Later, use other
Halo maps (Halo 3 first) as tracing references and auto-build a first pass out
of Reach Forge pieces.

Inspiration: TubbyMcFatDuck/Halo-Infinite-Blender-2-Forge-Printer (Infinite,
keystroke-driven). We do NOT copy its code or assets; our route writes the
file directly.

## Rules

- Game-derived files (extracted meshes, map files, saved variants from the
  game, offsets dumps) stay local in `E:\Proving Grounds\re_tools` or a
  scratch folder. Never commit or ship them.
- Our map tooling uses Gravemind's GPL library, not Project Reclaimer.
- Follow AGENTS.md: small commits, CUSTOM_CHANGELOG.md entries, no push or
  release without the owner's explicit approval.
- Tool lives in its own folder (proposed: `tools/forge_printer/`), not inside
  `brain/`, so it never affects a live match.

## Phases

### Phase 1 — `.mvar` round trip  (MODEL: Fable 5.2)
1. Owner supplies a saved Reach Forge World map variant (plus 1–2 others).
2. Locate MCC's Reach user-content folder and the file container/header
   (BLF chunks, hashes/signature if any).
3. Write a reader: header, budget, every placed object (type/palette index,
   position, rotation, spawn/team/label/respawn fields).
4. Write a writer. Round-trip test: read → write → byte-compare; then a
   one-object edit (move a block) that loads in Reach Forge.
5. Document the format in `docs/reach_mvar_format.md` (our own notes, no game
   data dumps). Unit tests with a synthetic, hand-built sample — not the
   owner's game file.

### Phase 2 — Halo 3 reference import  (MODEL: Opus 5.5)
- Use Gravemind to export a Halo 3 map's collision/render geometry plus
  spawns/weapons/objectives to a local `.obj`/`.glb` + JSON for Blender.
- Scale conversion H3 units → Reach units.

### Phase 3 — Auto-builder core  (MODEL: Fable 5.2)
- Surface classification (floor / wall / slope / ceiling) of the reference mesh.
- Piece fitting: largest blocks first, greedy fill, ramps for matching slopes,
  no scaling (Reach can't scale).
- Budget/limit solver: per-type caps, total budget, map bounds; report where
  it runs out.
- Test map: Guardian. Target ~70–80% coverage, rest by hand.

### Phase 4 — Blender addon + polish  (MODEL: Opus 5.5)
- Reach object palette (blockout shapes sized to match; optional local real
  meshes never shipped), place/snap tools, live budget counter, export button.
- Gameplay pieces: spawns, weapon holders, objectives from the reference.
- Cleanup helpers: overlap/z-fight finder, gap finder.
- Optional later: load a variant into a live lobby through our MCC hook.

## Model switch points

| When | Switch to | Why |
|---|---|---|
| Start | **Fable 5.2** | Phase 1 is exact binary RE; one wrong byte breaks the file |
| Phase 1 done (see stopping point) | **Opus 5.5** | Phase 2 is routine glue code |
| Phase 2 done | **Fable 5.2** | Phase 3 fitting/budget solver is the hard algorithm |
| Phase 3 core done | **Opus 5.5** | Phase 4 is UI/addon work |

## STOPPING POINT for Fable (Phase 1)

Fable: stop and tell the owner to switch to Opus 5.5 when ALL of these are true:

1. Reader + writer exist in `tools/forge_printer/` and pass unit tests.
2. Round trip of the owner's variant is byte-identical (or every difference is
   explained and harmless, e.g. a recomputed hash).
3. A one-object edit was written and the owner confirmed it loads in Reach
   Forge (or this is listed as the only untested item).
4. `docs/reach_mvar_format.md` documents every field we use and which ones are
   still unknown.
5. Work is committed locally (not pushed) with a CUSTOM_CHANGELOG.md entry.
6. This file's checklist below is updated.

Then write a short handoff note at the bottom of this file: what's done, what's
unknown, where the files are, and the first task for Phase 2.

Do not start Phase 2 on Fable.

## Checklist

- [x] Owner's sample variant(s) collected (local only) — the 34 already in the
      MCC Reach `Map` folder, one of them saved by the owner in MCC's Forge
- [x] File container/header understood
- [x] Object list parsed
- [x] Writer + byte-identical round trip (all 34 files)
- [x] One-object edit loads in game — the owner, 2026-11-21: "FP Move Test A
      loaded, and did move"
- [x] Format doc written (`docs/reach_mvar_format.md`)
- [x] Phase 1 committed locally
- [x] Phase 2 — H3 reference import (scale 0.975, the owner's choice)
- [ ] Phase 3 — auto-builder core (Guardian test)
  - [x] reference mesh turned Z up (a phase 2 mistake), play space cut out,
        surfaces sorted (`forge_printer surfaces`)
  - [x] palette row/item → piece (from ten variants already on the PC; the
        calibration map was not needed for it)
  - [x] a file with objects added loads in the game ("It loaded fine")
  - [x] turn direction and the up vector's faces (the owner's screenshot)
  - [x] on face 2, u is +x and v is +y (the owner's screenshot from above)
  - [ ] the size of an up-vector step (measured about half of expected) and
        what a turn means under a tilted up: a second test, when tilted
        pieces are needed
  - [x] piece sizes (`forge_printer pieces`, 108 pieces, table in the repository)
  - [ ] piece prices — sixteen known from four HUD totals (`pieces.PRICES`:
        the Flat blocks used, Block 1x1 Tall, four ramps, Wall, Wall Double,
        Wall Coliseum at 10, small antenna 50); the other 93 unknown
  - [x] piece fitting, floors, first version (`forge_printer fit`, `print`):
        Guardian 71% of walked floor with 185 flat blocks — printed, waiting
        for the owner to load it
  - [x] piece fitting, ramps and walls, first version: Guardian 37 ramps on
        27% of its walked slope, 37 wall pieces — printed (`FP_Guardian_2.mvar`),
        waiting for the owner to load it
  - [ ] piece fitting: curved and odd-angle slopes, floor pieces not square to
        the axes, railings, ceilings
  - [x] ramps join end to end on any slope (seen in the third print)
  - [x] budget and limit solver: slots, budget, map bounds
        (`fit.within_limits`); no piece caps are known, 185 Building Blocks load
- [ ] Phase 4 — Blender addon

## Handoff notes

### Phase 1 → Phase 2 (2026-11-21, written by Fable 5.2)

**Done**

- `tools/forge_printer/`: `bitstream.py` (bit reader/writer), `mvar.py`
  (`MvarFile`, `MapVariant`, `ForgeObject`, value conversions, the chdr chunk,
  the hash), `__main__.py` (`info`, `check`, `move`).
- `tools/test_forge_printer.py`: 27 tests on hand-built variants, plus one that
  round-trips this PC's own MCC variants and skips where there are none.
  Whole suite: 1071 OK.
- `python\python.exe tools\forge_printer check <MCC Reach Map folder>`: all 34
  files byte-identical after read → write, no problems reported.
- `docs/reach_mvar_format.md`: every field, how sure each is, what is unknown.

**In-game result (the owner, 2026-11-21): "FP Move Test A loaded, and did
move."** MCC lists and loads a variant this tool changed, with the Xbox 360
hash written, so the writer's default stays as it is. Test B (old hash kept)
was not needed and was not tried. The notes below are how the test was set up.

**The test: does MCC load a file we changed?**

Two copies of the owner's own Forge World variant, one wall (slot 12) lifted 6
units, are in `E:\Proving Grounds\re_tools\forge_printer\` (local only):

- `FP_Move_Test_A.mvar` — title "FP Move Test A", Xbox 360 hash written.
- `FP_Move_Test_B.mvar` — title "FP Move Test B", the source file's hash kept.

Owner's test: copy both into the MCC Reach `Map` folder with MCC closed, open
Reach Forge, load "FP Move Test A". Pass = it lists, loads, and one wall stands
6 units above the rest. If A does not list or load, try B. A loads: the hash is
not checked the way MCC writes it, nothing to change. Only B loads: MCC wants
its own hash bytes left alone, so make `rehash=False` the default. Neither:
the next step is reading the game's loader (the hash MCC writes is the first
suspect; see the format doc, section 5).

**Unknown, and when it matters**

- Up-vector axes and turn direction (format doc 4.2, 4.3): needed in Phase 3
  for any piece that is not upright. A calibration variant settles it: the
  owner places one piece at a few known rotations, saves, we read it back.
- Which palette row/item is which Forge piece, and each piece's price: needed
  in Phase 3/4. Same method (place one of each, save, read), or the map's
  Forge palette through the Gravemind library.
- The 128-bit version 32 block and the map checksum: copy them from a variant
  the owner's MCC saved on the same map (use that file as the template for
  anything we write).
- What MCC puts in the hash field.

**First task for Phase 2 (Opus 5.5)**

The full brief is `docs/REACH_FORGE_PRINTER_PHASE2_BRIEF.md`. In short: with
Gravemind's library (the git-ignored `tools/map_tools` already holds
`Reclaimer.Blam` and the `bsp2obj`/`model2obj` exporters built on it), export
one Halo 3 map — Guardian — to a local `.obj` plus a JSON of spawns, weapons
and objectives, under `E:\Proving Grounds\re_tools`, and work out the Halo 3 →
Reach unit scale by measuring a known feature in both rather than assuming it.

### Phase 2 → Phase 3 (2026-11-21, written by Opus 5.5)

**Done**

- `tools/forge_printer/h3_reference.py`, run as
  `python\python.exe tools\forge_printer reference <map> [--out FOLDER]`:
  runs `bsp2obj`, writes `<map>.obj` (vertices in Reach units, LF line ends)
  and `reference.json` (spawns, weapons, objectives, other; facings converted
  from degrees to radians). Default output
  `E:\Proving Grounds\re_tools\forge_printer\reference\<map>\` (local only).
  Halo 3 maps only (`maps/h3_*`).
- `tools/forge_printer/blender_import_reference.py`:
  `blender --background --python <script> -- <folder>` loads the mesh into
  collection `level` and one empty per placement into `spawns`, `weapons`,
  `objectives`, `other` (each empty keeps its source fields as `ref_*`
  custom properties).
- `tools/test_forge_printer_reference.py`: 13 tests (a hand-built OBJ, a
  fake `bsp2obj`, one real-Guardian test that skips without MCC or the map
  tools). Full suite 1084 OK.

**Guardian results**

- `reference h3_guardian`: exit 0; 115,250 triangles, the same as `bsp2obj`
  reports; 58 spawns, 21 weapons, 23 objectives, 14 other (8 grenades, 3
  powerups, 2 launchers, 1 lift); none outside the mesh box + 2 u. A second
  run gives byte-identical files. (The OBJ differs from bsp2obj's raw file
  only in formatting: CRLF → LF and every coordinate written with 4 decimals.)
- Bounds (Reach units, scale 0.975): x -18.95..20.08, y -38.23..91.45,
  z -6.07..35.27, size 39.0 × 129.7 × 41.3 (at 1.0 it was 40.0 × 133.0 × 42.4). Forge World's box is
  x -203.60..277.66, y -360.83..324.92, z -25.01..117.79, so Guardian fits
  easily. The long y side is far-off backdrop geometry; the play space is
  much smaller. Phase 3 should crop it.
- Blender 5.1 headless: 117 objects (1 mesh, 116 empties: spawns 58,
  weapons 21, objectives 23, other 14), 115,250 triangles, mesh box equal to
  `bounds` (max difference 0.0000).
- Errors are one line each: missing map folder, `.map` not in MCC (e.g.
  `h3_s3d_avalanche`: the DLC map isn't installed here), MCC not found,
  `bsp2obj.exe` not found, non-Halo 3 map.

**The scale: 0.975, the owner's choice (2026-11-21)**

`H3_TO_REACH_SCALE = 0.975`, the percentile ratio below. Shipped at 1.0 first
and changed the same day. Guardian re-exported at 0.975: same counts, none
outside the box, repeat run identical, Blender box matches. One measurement: the player models,
exported with `model2obj` into `E:\Proving Grounds\re_tools\forge_printer\scale\`:

| Model | Max vertex height | 99.9th percentile |
|---|---|---|
| Halo 3 `objects\characters\masterchief\mp_masterchief\mp_masterchief` (guardian.map) | 0.803 u | 0.761 u |
| Reach `objects\characters\spartans\spartans` (forge_halo.map) | 0.764 u | 0.742 u |

That's a ratio of 0.975 by the percentile and 0.952 by the max: 2.5–5% apart,
not a clean number. The models are different armour designs, so this alone
can't separate "same unit, different suits" from a real unit change. No
second per-game measurement was found on this PC (the bot records Reach's
gravity, 4.1 u/s², but no Halo 3 figure), so the owner made the call.
Changing it is one constant; re-run `reference` afterwards. Phase 3 should
check that the scale doesn't break a known jump on Guardian.

**For Phase 3 (Fable 5.2)**

- Read `reference.json` plus the OBJ. Crop the backdrop first.
- The three in-game items from the Phase 1 note are still needed: palette
  row/item → Forge piece, prices, up-vector axes and turn direction.
- Not tested: any map but Guardian; a Blender run with the UI open (only
  headless was run).

### Phase 3, part 1 (2026-11-21, written by Fable 5.2)

**Correction to the Phase 2 note above.** The reference OBJ was Y up (that is
how `bsp2obj` writes it) while the placements are Z up, so the mesh stood at
right angles to its own spawns; the "long y side … far-off backdrop" was the
trees' height. Fixed in `h3_reference.scale_obj` (`x, -z, y`). Guardian's box
is x -18.95..20.08, y -35.27..6.07, z -38.23..91.45; the play space is
z 11..24 of that. Re-run `reference` on any folder made before this fix.

**Done**

- `tools/forge_printer/surfaces.py`, run as
  `python\python.exe tools\forge_printer surfaces <reference folder>`: finds
  the play space by walking the ground from the spawns, cuts the mesh to a box
  around it, sorts triangles into floor / slope / wall / ceiling, groups them
  into flat patches, marks walked ground. Writes `<map>_play.obj` and
  `surfaces.json` beside the reference (local only). The rules and their
  numbers are the constants at the top of the file.
- `blender_import_reference.py` loads the play mesh too (collection `play`).
- Guardian: play box 39.5 × 36.0 × 23.3 u; floor 566 u² (509 walked), slope
  377 (224 walked), wall 6,532, ceiling 852; 208 floor patches of 0.25 u² or
  more hold 518 of the 566. Pictures:
  `re_tools\forge_printer\reference\h3_guardian\views\`.
- Tests: `tools/test_forge_printer_surfaces.py` (23). Full suite 1108 OK.

**Known limits**

- The big tree trunks inside the box remain, as walls: 6,532 u² of wall is
  mostly trunk. The mesh names no materials. The fitter should take walls from
  beside walked ground, not from the whole list.
- A patch's `area` can exceed its outline (the render mesh stacks layers in
  places); fit to the outline, not the area.
- Patches split at T-junctions, so one real floor can be several patches.

**The calibration map (the owner, 2026-11-21): built, not saved yet** ("MCC
says private storage is full"). It will be in the MCC Reach `Map` folder; the
owner gives its name. Forge World, 97 pieces in 7 rows in placement order,
nothing deleted; the piece names row by row are the owner's notes,
`C:\Users\marsh\Downloads\Forge Items.txt` (typos his: Blcok = Block, Medieum =
Medium). Categories in order: Building Blocks (25), Bridges and Platforms (21),
Buildings (11), Decorative (6), Doors Windows and Walls (11), Inclines (15),
Nature (8).

Rotation test, not in that file: at the end of row seven, after Rock Arch,
five Ramp 1x2 copies placed right to left, copy 1 nearest the arch:
1 not turned · 2 turned 90 left · 3 turned 45 left · 4 tipped forward 90 ·
5 rolled 90 onto its right side. Rotation snap was on.

What the map can and cannot settle:

- **Row/item → piece: yes.** One earlier data point already fits: the owner's
  own variant holds type 74 item 8, and "Wall Coliseum" is the ninth name
  (index 8) in the Doors, Windows and Walls list, so an item number is the
  piece's place in its Forge menu.
- **Rotation axes and turn direction: yes**, from the five ramps.
- **Prices: only the total.** The file holds the budget spent, not a price per
  piece. If every piece costs the same the total shows it (the owner's own
  variant: 13 Coliseum walls, budget 130); otherwise the prices have to come
  from the Forge menu or the map's tags.
- **Piece sizes: no.** The file has positions only. Sizes need the pieces'
  models (`model2obj` on `forge_halo.map`, kept local) or measuring in game.

**Next**

1. When the map is saved: `forge_printer info --objects` on it, then a
   `calibrate` step that pairs slots with the notes and writes the palette
   table (names, row, item) into the repository and the rotation result into
   `docs/reach_mvar_format.md` (sections 4.2 and 4.3).
2. Piece sizes for the 97 pieces.
3. Fitting, floors first: cover each walked floor patch's outline with the
   largest blocks that fit, then ramps on walked slopes, then walls beside
   walked ground.
4. Check one known Guardian jump against the 0.975 scale.

### Phase 3, part 2: piece sizes (2026-11-21, written by Fable 5.2)

**Done**

- `tools/forge_printer/pieces.py`, run as
  `python\python.exe tools\forge_printer pieces [--measure]`. `--measure`
  exports each piece's model from MCC's `forge_halo.map` with `model2obj`
  (about a second each; the models go to
  `E:\Proving Grounds\re_tools\forge_printer\pieces\`, local only), measures
  its box and rewrites `tools/forge_printer/forge_world_pieces.json`. Without
  it the command prints the table.
- The table is in the repository: names and sizes only, 108 pieces — the
  owner's 97, two more whose menu names are known (Block 4x4 Short, Window
  Coliseum) and nine decorative ones known only by model name. Each row has
  the box the piece fills, measured from the point Forge places it by, in
  world units and the piece's own axes.
- Tests: `tools/test_forge_printer_pieces.py` (15). Full suite 1123 OK.

**What the sizes say**

- A block's name is its footprint in world units: Block 2x2 is 2.00 × 2.00 ×
  1.00. Flat blocks are 0.20–0.30 tall, Short 0.50, plain 1.00, Tall 2.5–3.0.
  The smallest blocks carry 0.02 of trim (Block 1x1 is 1.018 wide).
- Not every piece is centred on its placing point: a Block 1x1 Short sits on
  it (z 0..0.5), a Bank hangs to one side of it (x -1..0, y 0..1). The fitter
  must use `min` and `max`, not `size`.
- Wall Coliseum is 10 × 0.5 × 12, standing. The owner's own variant uses
  thirteen of them lying flat as a floor, 10 by 12 apart, which agrees.

**How names were paired with models, and where that is unsure**

Within a category the map file lists the models in the Forge menu's order
(the one pairing a saved variant confirms, Wall Coliseum = item 8, fits it),
so names were paired by order and by the obvious likeness of name and model.
Differences from the owner's notes:

- `ff_plat_4x4_short` (Block 4x4 Short) sits between 4x4 Flat and 4x4 Tall and
  is not in the notes. If it was not placed, the calibration map's Building
  Blocks will simply skip item 22.
- The notes say "Block 5x1 Short"; the model is `ff_plat_5x1_flat`, 0.22 tall
  like the other Flat blocks. The table calls it Block 5x1 Flat.
- Door / Door Double: paired by order (`ff_door_2`, then `ff_wall_2x1_door`),
  but `ff_door_2` is the taller one (2 × 2 against 2 × 1), and the "Double"
  window is the taller window. They may be the other way round. One look in
  the game settles it.
  **Settled (2026-11-21).** Shown the six door, window and wall models side by
  side (`re_tools\forge_printer\pieces\views\doors_windows_walls.png`), the
  owner named them left to right: "Door, Double door, window, window double,
  wall, wall double … the door is taller than the double door". That is the
  map file's order, so the table was right: Door = `ff_door_2` (2 × 2 arch),
  Door Double = `ff_wall_2x1_door` (2 × 1), Window = `ff_wall_2x1_window`,
  Window Double = `ff_wall_2x2_window`, Wall = `ff_wall_2x2`, Wall Double =
  `ff_wall_2x4`. Six more pairings confirmed by eye, and more support for
  "the map file's order is the menu's order".
- Window Coliseum (`ff_arena_window`) is between Wall Coliseum and Tunnel
  Short and is not in the notes: the tunnels should be items 10 and 11.
- Nine decorative models (antenna, braces, crenellations, sloped cover,
  teleporter frame, walkway cover) are not in the notes; their menu names and
  places are not claimed.

The calibration map gives item number → the owner's name. It does not show
which model an item uses, so the pairings above stay as argued here unless a
piece's resting height or the game itself says otherwise.

**A first look at rotation, from the Coliseum floor**

In the owner's own variant the flat-lying Coliseum walls have their up vector
on faces 1 and 4 (and 3 for the two turned a quarter), with the turn at -90°.
The wall's height is its model z, so "up" in the file is where the model's z
points, and faces 1/4 lie along the world's y, face 3 along x: the order
+X, +Y, +Z, -X, -Y, -Z still fits. Signs and the turn's direction wait for the
five ramps.

**Still needed**

- Prices (not in any file read so far).
- The calibration map, for row numbers, items, and rotation.

### Phase 3, part 3: rows and items without the calibration map (2026-11-21, written by Fable 5.2)

The owner, 2026-11-21, on the calibration map: "It probably wont let me save
it." So what it was for was looked for elsewhere.

**Rows and items: settled from files already on the PC.** Ten Forge World
variants on today's palette (145 quota rows, checksum 0x8B33E8AC: MCC's five
built-in Forge World maps as its session copies in
`LocalLow\MCC\Temporary\UserContent\HaloReach\Map`, and five in the private
folder) were read. Only rows 70 to 76 hold objects with many different items,
and the highest item each row uses is exactly one less than the number of
models the map file has for the matching category:

| Row | Category | Highest item used | Models |
|---|---|---|---|
| 70 | Building Blocks | 25 | 26 |
| 71 | Bridges and Platforms | 20 | 21 |
| 72 | Buildings | 10 | 11 |
| 73 | Decorative | 15 | 16 |
| 74 | Doors, Windows and Walls | 11 | 12 |
| 75 | Inclines | 14 | 15 |
| 76 | Nature | 7 | 8 |

With Wall Coliseum = row 74 item 8 (the owner's own variant) and the owner's
naming of the first six wall models in the map file's order, a piece is
(its category's row, its place in the category). `pieces.py` holds the rows
(`ROWS`), the table has `row` and `item` for all 109 pieces (the sixteenth
decorative model, `ff_dish_antenna`, was added), `pieces.at(row, item)` looks
one up, and `info --objects` now names each building piece.

Unsure: where the unplaced decorative pieces sit (items 1 and 6 to 9 of row
73); the other rows' orders are the map file's, confirmed at seven points.
Other rows seen: 54 and 55 are spawn points (most objects of all), 56/57/60/61
spawn and objective zones, 0 to 22 weapons and grenades, 32 to 39 vehicles;
none of that is in the table.

**Why MCC said storage was full (not proven).** The private folder
(`LocalLow\MCC\LocalFiles\<account>\`, Reach and Halo 4 maps and game types
together) held 105 files, 2,008,660 bytes, when the save was refused; after
the owner removed three Reach maps it holds 102 files, 1,958,680 bytes. That
fits a limit of 2,000,000 bytes (a save should now work, once) or of 100
files (three more must go first). Not tried since.

**Rotation still needs the game.** Two ways: the calibration map if it saves,
or the reverse — this tool writes five Ramp 1x2 (row 75 item 4) at chosen
turns next to marker blocks into a copy of the owner's variant, and the owner
loads it and says which way each ramp points. The second needs no saving but
is the first time objects are added to a file, which is itself untested.

**Prices** still have no source.

### Phase 3, part 4: the turn test (2026-11-21, written by Fable 5.2)

The owner chose the reverse test ("Write it."). `tools/forge_printer/turn_test.py`,
run as `python\python.exe tools\forge_printer turntest FILE OUT --origin X Y Z`,
adds eleven pieces to a copy of a Forge World variant. Built from the owner's
own variant with origin (-31, -131.5, 5.21), on its Coliseum floor in front of
its spawn points: `E:\Proving Grounds\re_tools\forge_printer\FP_Turn_Test.mvar`
(local only), title "FP Turn Test", 30 objects, budget 240 (10 a piece, a
guess). **Not loaded in the game yet; it is also the first file with objects
added, which is itself untested.**

What is in it (positions are certain, so directions are given by things in
the map: the spawn points are on the +x side, the pillars on the +y side):

| Piece | Where | Stored | If the guesses hold, the owner sees |
|---|---|---|---|
| A1 Ramp 1x2 | nearest the spawn, beside the pillars | turn 0, world up | it climbs towards the spawn (+x) |
| A2 Ramp 1x2 | 5 further from the spawn | turn +90° | it climbs towards the pillars (+y) |
| A3 Ramp 1x2 | 5 further again | turn +45° | halfway between those two |
| B1 antenna | other row, floating, nearest the spawn | up = face 0 | its tip points at the spawn (+x) |
| B2 antenna | next | up = face 1 | its tip points towards the pillars (+y) |
| B3 antenna | next, higher | up = face 5 | its tip points straight down |
| B4 antenna | next | face 2, 90 steps along u | upright, leaning about 23° one way |
| B5 antenna | last | face 2, 90 steps along v | upright, leaning about 23° another way |
| 3 pillars (Block 1x1 Tall) | 3.5 to the +y side of the ramps | | markers only |

**The owner, 2026-11-21: "It loaded fine."** So a file with objects added
(new rows used, quotas recounted, a guessed budget) loads in Reach Forge.
Which way each ramp and antenna points has not been reported yet.

**The owner's screenshot (2026-11-21), Forge monitor view from the south,
compass reading N straight ahead, spawn markers at the right edge.** So the
pillars (+y) are to the north and the spawn (+x) to the east. Read off it:

| Piece | Seen | Settles |
|---|---|---|
| A1, turn 0 | wedge, high end to the right (east) | a turn of 0 points the model's +x along world +x |
| A2, turn +90° | seen from its low end, treads rising away from the camera | +90° is towards +y: turns run counter-clockwise seen from above |
| A3, turn +45° | sloped face towards the camera's left, high edge back right | between the two, as it should be |
| B1, face 0 | lying flat, tip to the right, towards the spawn markers | face 0 is +X |
| B2, face 1 | lying flat, mast running up-left towards the vanishing point | face 1 is +Y (less plain than the others in this view) |
| B3, face 5 | base on top, mast straight down | face 5 is -Z |
| B4, face 2 + u | upright, leaning to the right (east) | face 2 is +Z; u leans it towards +x |
| B5, face 2 + v | upright, no lean left or right | v leans it along y; towards or away not visible from here |

So the guesses held: turn = angle counter-clockwise from world +x, faces in
the order +X, +Y, +Z, -X, -Y, -Z (3 and 4 by the pattern, not seen). Open
after this one view: the sign of v on face 2, how far 90 steps really lean
(B4 looks nearer 10° than the 23° a plain cube-face reading gives, but a view
from the side cannot measure it), and A2/A3/B2 would be plainer from above.
A screenshot from straight above settles all of these.

**The owner's second screenshot (2026-11-21), from above**, read together with
an enlargement of the first:

- Confirmed plainly: A2 climbs towards the pillars and A3 between A1 and A2
  (turns are counter-clockwise); B2's thin mast runs from its base towards the
  pillars (face 1 is +Y); B3 hangs tip-down.
- B4 (face 2, u + 90 steps) leans towards +x and not along y. B5 (face 2,
  v + 90 steps) leans towards +y, the pillars, and not along x. So on face 2,
  u is x and v is y, both positive the plain way.
- **How far they lean is not what was expected.** Measured off the two views,
  B4 leans about 9° and B5 about 14° (each good to perhaps ±4°), where reading
  the grid as x/z running -1..1 across a face gives 23°. So a step is worth
  roughly half of that near the face's middle, or the grid is not even. Not
  settled; a second test with larger steps (a piece at a face's edge, where
  every reading says 45°, and one halfway) and a level, side-on screenshot
  would settle it. Until then only up vectors at face middles are safe to
  write: upright, lying on a side, upside down.

**The game works out the budget itself.** The file said 240 spent; the HUD
shows $29,560 left of 30,000, so 440 spent. The stored figure is therefore
not what the game shows, and prices can be read off the HUD by loading files:
the original thirteen walls were 130, so the eleven added pieces cost 310:
3 × Ramp 1x2 + 5 × small antenna + 3 × Block 1x1 Tall = 310. If prices are
multiples of 5 that leaves (ramp + block, antenna) = (20, 50), (45, 35),
(70, 20) or (95, 5); 10, 10 and 50 is the plain reading, not yet proven.

A ramp climbs towards its model's +x; an antenna's thin tip is its model's +z,
which is what the file calls "up". Reading the answers: A1 and A2 give where a
turn of 0 points and which way a positive turn goes; B1 to B3 give the sign of
each face's axis; B4 and B5 give which of u and v is which world axis on face
2 (and so, by the pattern, the others). The antenna is row 73 item 0 by the
map file's order; if something else shows there, that is an answer too.
Still open after this test: what the turn means once "up" is tilted.

### Phase 3, part 5: the first floor fit and the first print (2026-11-21, written by Fable 5.2)

The owner, 2026-11-21: "Yes, start fitting", and of the tests, "you pick which
test to do". He also said the floor grid of his own variant "was place by
hand" and its pieces "set as the spawned": its tile spacing is approximate and
is not evidence for any exact size.

**Done**

- `tools/forge_printer/fit.py`: `python\python.exe tools\forge_printer fit
  <reference folder>` covers the walked floors with flat blocks and writes
  `fit.json` (each piece's name, middle, top height, turn) and
  `<map>_fit.obj` (the pieces as boxes) beside the reference, local only.
  `forge_printer print <folder> <template> <out> --offset DX DY DZ` writes the
  pieces into a copy of a Forge World variant.
- How it fits: the walked floor on a quarter-unit grid, each cell keeping its
  floor heights; heights busiest first, floor within 0.2 of a height being one
  level; on a level, largest block first, each at the first place (row by
  row) wholly on uncovered floor; then a pass allowing a tenth of a block past
  an edge; then a pass that fills strips between blocks with a block tucked
  0.01 under its neighbours when at least 35% of it is new floor.
- `surfaces.analyse()` is the surface work without the files, for the fitter.
  `blender_import_reference.py` also loads the fitted boxes (collection `fit`).
- Tests: `tools/test_forge_printer_fit.py` (17) and one more in the turn-test
  file. Full suite 1153 OK.

**Guardian**

- 484 u² of walked floor on 71 height steps; 341 u² covered, **71%**, with 185
  blocks (2 × 5x5, 2 × 3x3, 15 × 5x1, 10 × 2x2, 21 × 3x1, 44 × 2x1, 91 × 1x1,
  all Flat), 92 of them tucked. A 1x1 lying wholly on floor can reach 76% at
  best, so what is left is mostly rims and curves narrower than a block.
  Picture: `re_tools\forge_printer\reference\h3_guardian\views\guardian_fit_top.png`.
- Loosening the tuck rule to 25% new floor gives 75% with about 270 blocks.

**Known limits of this first version**

- Blocks are square to the map's axes only; round rooms and anything diagonal
  are part covered. Slopes, walls and ceilings are not fitted at all.
- Only the eight Flat blocks are used. No piece limits are applied: the fit
  uses 185 Building Blocks, and no variant on this PC holds more than 92 in
  that row (50 walls, 47 bridges and platforms, 89 decorative), which smells
  like a limit of about 100. Whether the game keeps the extra ones is one of
  the things the first print shows.
- A gently sloping floor is fitted flat at its middle height.

**The first print: `E:\Proving Grounds\re_tools\forge_printer\FP_Guardian_Floors.mvar`**
(local only), title "FP Guardian Floors", 214 objects: the owner's variant
(19), Guardian's 185 floor blocks moved by (-39, -135, +8) so they hang about
18 above his floor, and the second rotation test (10 pieces) on the floor
below, where the first test stood.

**The owner, 2026-11-21, after loading it:** "Im not sure if any ar missing
but the floor is somewhat printed." So a variant with 214 objects, 185 of
them added Building Blocks, loads and shows floors. Not known yet: whether
all 185 are there, the HUD's budget, whether tucked blocks flicker, and the
tilt test's reading. Screenshots asked for.

**The owner's screenshot of the print from above (2026-11-21), south at the
top, HUD budget $27,760.**

- The arrangement matches a render of the same file from the same viewpoint
  (both 5x5 blocks, the walkway between, the lone pair off to one side, the
  clusters over the west building, the tilt test's pieces at the floor's
  edge). Block by block it cannot be checked from this height: several kinds
  of Flat block are as dark as the Coliseum floor behind them, and blocks
  tucked under a neighbour show only as thin strips.
- **Budget: 2,240 spent.** That is exactly 130 (the thirteen walls) + 185 × 10
  (every floor block, at 10 each) + 260 (the tilt test with small antenna 50,
  Ramp 1x2 10, Block 1x1 Tall 10, which is also the plain reading of the
  first test's 310). So the game counted all 185 floor blocks, and more
  Building Blocks than any variant on disk (92) do load. Prices this fits:
  every Flat block 10, Ramp 1x2 10, Block 1x1 Tall 10, Wall Coliseum 10, small
  antenna 50. One total cannot prove each of those apart, but two files now
  agree with them.
- MCC does not keep a copy of a Forge session's variant under
  `Temporary\UserContent` (only of custom games'), so there is no file to read
  the game's own view of the print from.
- Not read yet: the tilt test (too small in this picture), flicker.

What to look for in the floors: are they all there (count the gaps against
the picture), are the heights right relative to each other, do tucked blocks
flicker.

The tilt test (`turntest --test tilt`), nearest the spawn first:

| Piece | Stored | Shows |
|---|---|---|
| C1 antenna, floating row | face 2, u at its edge | 45° towards +x if a face spans 45°; less says the grid is not what was assumed |
| C2 antenna | face 2, u half way | 26.6° if the grid is x/z evenly; the first test measured about half the expected lean |
| C3 antenna | face 0, u half way | which world axis u is on a side face, and its sign |
| C4 antenna | face 0, v half way | the same for v |
| D1 ramp, floating over the old ramp spots | up = face 0, turn 0 | what a turn of 0 means when up is +X |
| D2 ramp | up = face 0, turn +90° | which way a turn goes about a tilted up |
| D3 ramp | up = face 1, turn 0 | the same reference for up = +Y |

A level, side-on screenshot from the south and one from above read all seven.

### Phase 3, part 6: ramps and walls (2026-11-21, written by Fable 5.2)

The owner, 2026-11-21, asked whether to fit ramps and walls next: "Yes, ramps
and walls".

**Done**

- `pieces.py` measures each incline's sloping face (`slope` in the table:
  lean, the way it climbs in the piece's own axes, run, width, low and high,
  middle). Ramp 1x2 and Ramp 2x2 climb at 26.6°, Ramp 1x2 Shallow at 13.9°,
  Ramp 2x2 Steep at 45°, each towards its own +x. The Ramp Bridges, Ramp XL,
  Ramp Stunt, the Banks and the Circular ramps are measured but not used: their
  sloping face is not a plain rectangle from foot to top.
- `fit.fit_slopes`: each walked sloping patch of 1.5 u² or more takes the ramp
  whose lean is within 7° of its tilt (the nearer, then the larger), turned to
  climb the same way and repeated along and across; each ramp's sloping face is
  set in the patch's plane. Any turn is used, not only quarter turns.
- `fit.fit_walls`: a wall patch that is upright within 2°, at least 1.5 long
  and 1.5 high, roughly a filled rectangle, and has walked ground within a
  unit of its foot, takes Wall Double (4 × 2) and Wall (2 × 2) pieces along
  it, their face on its face, up to two rows (4 units) high. The two faces of
  one thin wall make one wall.
- `fit.json` placements now carry `part` (floor, slope, wall) and `origin`
  (where Forge's placing point goes); the report is split the same way.
- Tests: 9 more in `tools/test_forge_printer_fit.py` (26). Full suite 1162 OK.

**Guardian**

- Slopes: 224 u² walked, 60 u² fitted (27%) by 37 ramps (24 Ramp 1x2 Shallow,
  5 Ramp 2x2, 8 Ramp 2x2 Steep). The straight walkway ramps are taken; what is
  left is curved ramps (many small facets, each under 1.5 u²), slopes between
  the ramps' leans (about 33° to 38°), and steep trim counted as walked.
- Walls: 37 pieces (Wall and Wall Double) along 64 units of wall.
- With the floors: 259 pieces.
  Pictures: `guardian_fit_top.png`, `guardian_fit_angle.png` in the views folder.

**Known limits**

- A ramp piece is a solid wedge down to its foot; where Guardian's slope is a
  thin bridge the wedge fills the space under it.
- Some ramps land on tree roots and other natural slopes that count as walked.
- Tree trunk facets that happen to be upright beside a floor become walls.
- Railings and low kerbs (under 1.5 high) get nothing; ceilings get nothing.

**The second print: `E:\Proving Grounds\re_tools\forge_printer\FP_Guardian_2.mvar`**
(local only), title "FP Guardian 2", 288 objects: the owner's variant (19),
259 fitted pieces moved by (-39, -135, +8), and the same tilt test as the
first print. **Not loaded in the game yet.** Expected HUD budget if every
piece is 10 and the small antenna 50: 130 + 2,590 + 260 = 2,980 spent,
$27,020 left; a different figure gives the price of Wall, Wall Double or the
ramps.

**The owner, 2026-11-21, after loading it: "$27,020".** Exactly as expected,
so the game counted all 259 pieces, and Wall, Wall Double, Ramp 1x2 Shallow,
Ramp 2x2 and Ramp 2x2 Steep fit 10 each. `pieces.PRICES` now holds the sixteen
prices the four HUD totals agree on (fifteen pieces at 10, the small antenna
at 50), `pieces.cost()` adds a list of pieces up, and `fit` reports the
budget of what it placed (Guardian: 2,590). Not reported yet: whether the
ramps meet the floors, and the tilt test.

**The owner's three screenshots of the second print's ramps (2026-11-21).**

- The ramps climb the right way and reach the floors: a long shallow walkway
  ramp runs unbroken from an upper floor down to a lower one, and a ramp's low
  tip sits about 0.1 below the floor block it meets.
- **Fault found:** two Ramp 2x2 one after the other on one slope did not
  join; the second started about half a unit below where the first ended.
  The slope there is about 20°, between the Shallow ramp's 13.9° and the
  Ramp 2x2's 26.6°; the fitter set each ramp in the slope's plane on its own,
  so a ramp steeper than its slope overshot at the top and undershot at the
  bottom. (Its choice was also wrong: it took the larger ramp, not the nearer
  angle.)
- **Fixed in `fit.fit_slopes`:** a slope is now climbed in steps of one ramp's
  run, each step starting where the last one stopped and taking whichever
  piece of its family brings the run of ramps nearest the slope's own height
  at the step's end. Gentle slopes (to 27.5°) use a 1-wide family of rise 0
  (Block 2x1 Flat), 0.5 (Ramp 1x2 Shallow) and 1 (Ramp 1x2; two lanes side by
  side become one Ramp 2x2); steeper ones (to 48°) a 2-wide family of rise 1
  (Ramp 2x2) and 2 (Ramp 2x2 Steep). So any angle is followed by a mix, the
  ramps join end to end, and the run stays within a quarter unit of a gentle
  slope and half a unit of a steep one. This also takes in the 33° to 38°
  slopes no single ramp matched.
- Guardian after the fix: 37 ramps (26 Ramp 1x2 Shallow, 5 Ramp 2x2, 6 Ramp
  2x2 Steep) on 61 of 224 u² of walked slope; 259 pieces, budget 2,590.
  Five new tests on slopes between and beyond the ramps' own angles; full
  suite 1167 OK.

**The third print: `E:\Proving Grounds\re_tools\forge_printer\FP_Guardian_3.mvar`**
(local only), title "FP Guardian 3", 288 objects, same place and same tilt
test as the second. Expected HUD: $27,020 again (the same number of pieces,
all at 10).

**The owner's four screenshots of the third print (2026-11-21), HUD $27,020.**
The pair that stepped now joins: a Ramp 1x2 Shallow runs straight into a Ramp
2x2 with only a change of angle between them. A ramp's low tip meets the edge
of the floor block below it, a few hundredths above its top. The long walkway
ramp still runs unbroken between its two floors. ~~Nothing in the four pictures
is out of place.~~ **That was wrong** (see part 8): the owner pointed out
floors not flush with what they meet and a ramp that stops short of its
floor, and the pictures do show both. Not shown: the walls, the tilt test.

### Phase 3, part 7: limits, and where Phase 3 stands (2026-11-21, written by Fable 5.2)

**Limits.** `fit.within_limits(placements, free slots, budget left)` keeps what
a variant has room and money for: floors before ramps before walls, larger
floor blocks first; a piece with no known price counts as free and is named.
`print` uses it, raises the stored budget by the cost of what it placed, and
says what it left out and whether slots or budget ran out. Guardian needs 259
of 632 free slots and 2,590 of 29,870, so nothing is left out. No per-piece or
per-category limit is applied because none has been seen: 185 Building Blocks
loaded where no variant on disk holds more than 92. Seven new tests; full
suite 1174 OK.

**Phase 3 against the plan**

| Plan item | State |
|---|---|
| Surface classification | done (`surfaces`) |
| Piece fitting, largest first, ramps for slopes, no scaling | done for floors, straight slopes and upright walls (`fit`) |
| Budget and limit solver | done for slots, budget and map bounds; no piece caps known |
| Guardian, about 70-80% | floors 71%; slopes 27%; 259 pieces; three prints loaded in game |

**What a first pass still leaves for hand work** (each could be automated
later): curved ramps; floors and blocks not square to the map's axes (round
rooms, diagonals); railings, kerbs and ceilings; thin sloping bridges (a ramp
piece is a solid wedge); trees and rocks that pass for structure; gameplay
objects (spawns, weapons, objectives are in `reference.json` but not placed).

**Still open from the tests:** the tilt test has been in all three prints and
never read (it needs a close side-on and a top-down screenshot), so slanted
pieces are still not safe to write; 93 of 109 pieces have no price; the owner
has not said whether tucked floor blocks flicker.

**For Phase 4 (Opus 5.5), when the owner switches**

- The pipeline, all under `tools/forge_printer`, run with
  `python\python.exe tools\forge_printer <command>`:
  `reference <map>` → `surfaces <folder>` → `fit <folder>` →
  `print <folder> <template> <out> --offset DX DY DZ`. `pieces` prints the
  piece table; `info --objects` reads any variant back with piece names.
- What an addon needs from here: `pieces.load()` (names, row, item, box,
  ramp faces), `pieces.PRICES`, `fit.origin_of` and the placement format in
  `fit.json`, `fit.add_to` and `fit.within_limits` for writing, and
  `mvar.MvarFile` for the file. `blender_import_reference.py` already loads
  the level, the classified play space, the placements and the fitted boxes.
- Rules that have been proven in the game and must be kept: a turn is degrees
  counter-clockwise from world +x; only upright, on-its-side and upside-down
  up vectors; the template must be a Forge World variant the owner's MCC
  saved (145 quota rows); files copied in with MCC closed.
- Everything made from the game stays in `E:\Proving Grounds\re_tools`.

### Phase 3, part 8: ramps tied to their floors, floors flush (2026-11-21, written by Fable 5.2)

**The owner, 2026-11-21, on the third print's screenshots:** "Two of those
screenshots showed the floor not sitting flush on another object? and one of
the ra[m]ps didnt connect to the the other floor?" He was right, and the
reading in part 6/7 ("nothing … out of place") was wrong. Enlarged, the
pictures show a floor block standing proud of the ramp top beside it, a
neighbouring block at another height, and a ramp top with no floor at its
height.

**Measured, not guessed.** For every fitted slope the mesh's own ends were
compared with the floor blocks beside them: the slope's low and high ends are
at the floors' heights to within 0.01. So the mesh was right and the fitter
put the ramps wrong, two ways:

- A ramp piece is 2 long, Guardian's ramps are 1.3 to 5.5 long (2.9, 3.5,
  4.15 …). The run was centred on the slope, so it stopped short at both
  ends or overshot: on the 2.9-long ramp, one piece, its foot 0.24 above the
  lower floor and 0.45 away from it, its top 0.32 under the upper floor.
- The run's rise was whatever its pieces added up to from the slope's plane
  at an arbitrary start, not what the two floors differ by.

And floors: each block took the middle height of the cells under it, so
blocks side by side on one floor could differ by a tenth or two.

**Fixed (`fit.py`)**

- Floors: every block of a level sits at the one height most of that level's
  floor is at. A level takes floor within 0.1 of its busiest height (it was
  0.2): a kerb is levelled, a ledge of a quarter unit or more stays a ledge.
  Guardian's floors come to 18 heights (15.04 … 21.63) instead of a different
  one per block.
- Ramps (`fit_slopes(analysis, table, floors)`): a run is tied to the floor
  blocks it joins. Its ends take the height of the fitted floor block just
  past each end (within 0.35 of the slope's own height there). It starts at
  the slope's top edge and is laid downhill, enough pieces to cover the whole
  length; what is left of the last piece runs on under the lower floor. The
  mix of pieces (rise 0, 0.5, 1, and 2 for a pair of lanes) is the one whose
  total is nearest what the slope drops over the run's length, every mix
  tried for runs of up to six pieces; what the run is still out by, a quarter
  unit at most, is shared between its two ends. A slope whose foot is a unit
  or more under the floor over it (two steep "ramps" that were roots or
  braces going down through the map) gets nothing.
- Guardian after the fix: every ramp top within 0.11 of the floor block it
  meets, most within 0.05; feet at or under the lower floor. 190 floor
  blocks (70%), 36 ramps, 37 walls: 263 pieces, budget 2,630.
- Tests: six new (a 2.9-long ramp tied to both floors; ends taking a floor
  block's height; a slope diving under a floor left alone; the best mix; one
  height per level; a kerb levelled and a ledge kept) and five updated. Full
  suite 1179 OK.

**The fourth print: `E:\Proving Grounds\re_tools\forge_printer\FP_Guardian_4.mvar`**
(local only), title "FP Guardian 4", 292 objects, same place and tilt test.
**Not loaded in the game yet.** Expected HUD: $26,980 (263 pieces at 10 on
top of 130 and the tilt test's 260).

**Lesson for whoever reads the next screenshots:** enlarge every junction and
compare heights before saying a print is right; a budget that matches only
says the pieces exist.

### Phase 3, part 9: no floor standing proud of a ramp; landings (2026-11-21, written by Fable 5.2)

**The fourth print in the game (owner's two screenshots, HUD $26,980 as
predicted).** Enlarged: the ramps now reach their floors, but on the 4.15-long
ramp the lower floor block still stands about 0.15 proud of the ramp where
they meet. The numbers agree (run at 16.09 at the floor's edge, floor at
16.24).

**Cause 1: the mix of pieces was chosen for the wrong place.** Part 8 picked
the mix whose total drop was nearest the slope's drop over the run's whole
length, but the run is longer than the slope (its last piece goes on under the
lower floor), so that total is reached somewhere under the floor. What a
player sees is where the run stands at the lower floor's edge.

**Fixed: `_best_run(rises, length, rise)` returns (run, lift)** and judges a
run at the lower floor's edge, `length` down from the top:

- above the floor there: fine. The ramp comes up out of the floor a little
  further on (its foot must still get down under the floor);
- under the floor there: the floor would stand proud. Up to 0.06 in all is
  let pass, half of it moved to the top by lifting the run (0.03 at each
  end); more than that is all but ruled out;
- among runs that pass, the one nearest the slope's own line, and whose
  piece that goes into the floor keeps the slope's angle, wins.

So a slope the pieces do not fit becomes a slightly longer, slightly
shallower ramp instead of a ramp with a lip. Guardian's 4.15-long, 1.42-high
ramp is now three shallow rows: level with its upper floor, 0.38 above the
lower floor at the reference's foot, down to the floor 1.5 further on. This
is a change of shape and it is deliberate; the alternative with these pieces
is a 0.04 lip at each end.

**Cause 2, found by a second check that reads `fit.json` alone** (every floor
block edge against every ramp face, not the fitter's own arithmetic): floor
blocks are laid on a quarter-unit grid and cover 70% of the floor, so they
can stop short of where a ramp's face meets the floor. Then the ramp's sunk
foot shows in a gap in front of the floor block (a lip as high as the foot is
deep there), or a ramp's top has no block past it.

**Fixed: landings.** With fitted floors, `fit_slopes` also puts a flat block
(part `"landing"`, Block 2x1 Flat across a pair of lanes, Block 1x1 Flat for
a single lane) at each end of a run, turned with the ramp, 1 long, 0.005 under
the floor's height (never level with a block or a tucked block, so no
flicker): at the foot from where the ramp's face comes down to the floor's
height, at the top from the run's top edge. Only where the reference has
walked floor at that height under at least half of it, and no fitted block
at that height already covers all of it. Guardian gets 19.

**Guardian now:** 190 floor blocks, 45 ramp pieces (40 shallow, 5 Ramp 2x2),
19 landings, 37 walls: 291 pieces, budget 2,910. By the fitter's arithmetic
no run is more than 0.02 under its lower floor at the edge and no top more
than 0.02 over its upper floor.

**Still wrong, measured and not fixed (the `fit.json` check, before
landings; landings are not in that check, it only knows square-on blocks):**

- Two ramps meet their upper floor at an angle (the 5-wide one turned 113
  degrees, the 2-wide one turned 44). Floor blocks are square to the map, so
  their corners overlap the ramp's top and stand 0.05 to 0.12 proud there.
  Needs turned floor blocks at such edges (the "non-axis floors" item).
- A Ramp 2x2's top has floor blocks hanging 0.1 over it: 0.05 proud.
- The Ramp 2x2 at reference (-7.97, -5.68): the floor in front of its foot
  covers half its width and stops 0.5 short, 0.22 proud. The reference there
  is a tangle of small floors at 17.46, 17.66 and 17.84, so no landing was
  given. Hand work, or a better reading of that corner.
- Three ramp tops (one a fifth lane) have no floor block past them and the
  reference has no walked floor at their height there either.
- Floors beside a ramp at another height overlap its sides by 0.2 to 0.3 in
  four places (the ramp is rounded up to whole lanes). Not a lip in the
  walking direction.

Tests: `_best_run` at the floor's edge over a sweep of lengths and rises; the
gentle, steep and odd-length slope tests updated for the new rule; landings
(a slit past a ramp's top, a missing floor at a foot, none where the floor
blocks reach, none in mid air). Full suite 1186 OK.

**The fifth print: `E:\Proving Grounds\re_tools\forge_printer\FP_Guardian_5.mvar`**
(local only), title "FP Guardian 5", 320 objects, same place and tilt test.
Expected HUD: $26,700 (291 pieces at 10 on top of 130 and the tilt test's 260).

**The fifth print in the game (2026-11-21).** The owner loaded it and sent
three screenshots: HUD $26,700 as predicted, and "All seem pretty good".
Each join in them was cut out and enlarged:

- Three ramp feet (one per picture): the shallow ramp comes up out of the
  floor block with no step; the floor's top runs straight into the ramp's
  face. One is seen side-on with the ramp's sunk foot showing under the floor
  block, as intended.
- Two ramp tops: level with the floor block past them as far as the pictures
  can show (a hair of ramp above the floor in one, about what the 0.02 lift
  would be; the camera angle allows no better reading).
- A far run of three pieces joins end to end and reaches its platform.

Not shown or not identifiable in these three pictures, so still only
measured: the faults listed above (the two angled ramp tops, the ramp foot
in the tangle of small floors, the three tops with no floor past them).
Flicker at a landing cannot be judged from a still; none of the landings in
view shows a torn surface. The tilt test stands in this print too and is
still unread.

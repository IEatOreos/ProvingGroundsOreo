# Reach Forge Printer — Project Plan

Status: Phase 1 done (2026-11-21): built, committed locally, and the edited
variant loaded in Reach Forge with its wall moved. Phase 2 done (Halo 3
reference, scale 0.975). Phase 3 started: the play space is cut out and sorted
into surfaces; the calibration map is built but not saved yet; no piece
fitting yet. Separate tool from the Project Reach bot code.

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
  - [ ] calibration map read: palette row/item → piece, rotation axes
  - [x] piece sizes (`forge_printer pieces`, 108 pieces, table in the repository)
  - [ ] piece prices
  - [ ] piece fitting
  - [ ] budget and limit solver
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
  **Open (2026-11-21).** Asked which is taller, the owner said: "Same height
  just double is wider". Neither pairing gives that: both models are 2 wide,
  `ff_door_2` is a 2-tall arch with one opening and `ff_wall_2x1_door` a
  1-tall piece whose opening is about a Spartan high (the 2x1 window is the
  same piece with a sill). The only same-height, twice-as-wide pair in the
  category is Wall (2 × 2) and Wall Double (4 × 2). So either the menu's Door
  or Door Double is a model not in this list, or the two were judged by eye.
  A picture of the six door, window and wall models side by side is in
  `re_tools\forge_printer\pieces\views\doors_windows_walls.png` for the owner
  to name; until then treat both door pairings as unconfirmed.
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

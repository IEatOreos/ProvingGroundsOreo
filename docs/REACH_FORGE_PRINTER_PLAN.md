# Reach Forge Printer — Project Plan

Status: Phase 1 done (2026-11-21): built, committed locally, and the edited
variant loaded in Reach Forge with its wall moved. Phase 2 not started; its
brief is `docs/REACH_FORGE_PRINTER_PHASE2_BRIEF.md`. Separate tool from the
Project Reach bot code.

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

# Reach Forge Printer — Project Plan

Status: Phase 1 built and committed locally (2026-11-21); its one open item is
the in-game load test of an edited variant. Phase 2 not started. Separate tool
from the Project Reach bot code.

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
- [ ] One-object edit loads in game — **written, not yet tried in game**
- [x] Format doc written (`docs/reach_mvar_format.md`)
- [x] Phase 1 committed locally
- [ ] Phase 2 — H3 reference import
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

**The one untested item: does MCC load a file we changed?**

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

Do not start it before the owner reports the in-game result above. Then: with
Gravemind's library (the git-ignored `tools/map_tools` already holds
`Reclaimer.Blam` and the `bsp2obj`/`model2obj` exporters built on it), export
one Halo 3 map — Guardian — to a local `.obj`/`.glb` plus a JSON of spawns,
weapons and objectives, under `E:\Proving Grounds\re_tools`, and work out the
Halo 3 → Reach unit scale by measuring a known feature in both rather than
assuming it.

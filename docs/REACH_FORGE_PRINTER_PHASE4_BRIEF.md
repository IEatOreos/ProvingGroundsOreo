# Reach Forge Printer — Phase 4 brief (for Opus 5.5)

Written 2026-11-21 by Fable 5.2 at the end of Phase 3. Give this file to the
Phase 4 session as its task.

## Your task

Build the Blender side of the Reach Forge Printer: an addon in which the owner
can open an auto-built map (or start an empty one), move, turn, tilt, add and
delete Forge pieces, watch the limits as he works, and export a `.mvar` that
MCC's Halo: Reach Forge loads. Then place the gameplay objects (spawns,
weapons, objectives) and add helpers that find gaps and overlaps.

The owner builds maps for a group that plays on controller; he is not a
programmer. He will judge the addon by whether a map he edits in Blender shows
up in the game the way it looked in Blender.

This is Phase 4 of `docs/REACH_FORGE_PRINTER_PLAN.md`. Read, in this order:
that file's Rules and its "Phase 3 → Phase 4" note at the very end;
`docs/reach_mvar_format.md` sections 4.2 and 4.3 (turns and up vectors);
`AGENTS.md`. Phases 1 to 3 are finished and proven in the game. You should not
need to change the file format code or the fitter.

## What already exists

Check each before writing anything.

- **The pipeline**, `python\python.exe tools\forge_printer <command>`:
  `reference <map>` → `surfaces <folder>` → `fit <folder>` →
  `print <folder> <template> <out> --offset DX DY DZ`; also `info --objects`,
  `check`, `pieces`, `turntest`. Guardian has been through all of it; its
  folder is `E:\Proving Grounds\re_tools\forge_printer\reference\h3_guardian\`.
- **`fit.json`**, the list an addon would open. Each placement has `part`
  (`floor`, `slope`, `landing`, `wall`), `piece` (a name in the piece table),
  `origin` (where Forge's placing point goes, reference coordinates), `turn`
  (degrees) and, for a tilted piece only, `up` (a unit vector). Floor
  placements also carry `centre`, `top`, `size`, `tucked`, sometimes `fill`.
  The print adds an offset to every origin (Guardian: -39 -135 8).
- **The piece table**, `pieces.load()` / `pieces.by_name()` from
  `tools/forge_printer/forge_world_pieces.json`: 109 building pieces with
  palette `row` and `item`, and each piece's box (`min`, `max`) measured from
  its placing point in its own axes. Ramp pieces also have their sloping face.
  `pieces.PRICES` knows 16 prices; `pieces.price(name)` is None for the rest.
- **Orientation**, in `mvar.py`: `axes(up, turn)` gives a piece's own x, y, z
  in the world; `turn_for(up, forward)` and `up_raw(vector)` go the other way;
  `up_vector(raw)` decodes. A piece's +z is its up vector, the turn is
  counter-clockwise about up from `reference_axes(up)`. These were checked in
  the game with eight tilted ramps; trust them, and use them rather than
  writing your own matrix maths.
- **Writing a variant**: `fit.add_to(variant, placements, offset)`,
  `fit.within_limits(placements, free_slots, budget_left, row_room)`,
  `mvar.MvarFile.read / write`, `variant.problems()`. `fit.print_main` shows
  them used together.
- **A Blender script**, `tools/forge_printer/blender_import_reference.py`
  (no addon, no UI): loads the reference level, the sorted play space, the
  placements as empties and the fit as boxes. Blender 5.1 is at
  `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`.
- **Gameplay objects in the reference**: `reference.json` has 58 spawns, 21
  weapons, 23 objectives and 14 others, in Reach units, reference coordinates.
- **Check scripts** in `E:\Proving Grounds\re_tools\forge_printer\checks\`
  (scratch, local): `gaps.py` measures covered and bare walked ground,
  `tilted_check.py` and `lips2.py` compare ramps with floors.
- **Python**: `python\python.exe` in the repository root. Tests:
  `python\python.exe -I -m unittest discover -s tools -p "test_*.py"`
  (1206 OK at the start of this phase, 150 of them the Forge Printer's).

## What to build, in three milestones

Stop and report to the owner at the end of each milestone. Do not start the
next one until he says so.

### Milestone 1: open, edit, count, export

1. **An addon** under `tools/forge_printer/blender_addon/`, enabled by one
   documented step. Keep everything that does not need `bpy` in plain modules
   the test suite can import (the conversion between a Blender object and a
   placement, the counting, the checks).
2. **Open**: load a `fit.json` (and its reference level as a backdrop) so each
   placement is one Blender object: a box the size of the piece's `min`/`max`,
   built in the piece's own axes so that the object's origin is Forge's
   placing point, named after the piece, in a collection per part.
3. **Add**: a palette panel listing the pieces by Forge category; picking one
   adds it at the 3D cursor.
4. **Edit freely** with Blender's own move and rotate tools. Reach cannot
   scale a piece: treat any scale other than 1 as an error to show, not
   something to export.
5. **Count, live**: object slots used of 651; pieces per palette row of 255;
   budget from `pieces.PRICES`, with the number of pieces whose price is not
   known shown beside it rather than counted as zero silently.
6. **Export**: one button that writes a `.mvar` from a template variant, to a
   new file under `E:\Proving Grounds\re_tools\forge_printer\` by default,
   never overwriting. Position, turn and up vector come from each object's
   world matrix through `mvar.turn_for` and `mvar.up_raw`. Before writing,
   list what cannot be written and why (a piece leaning more than 45 degrees
   from +Z or +X, a scaled piece, a row over 255, no free slot, outside Forge
   World's bounds), and export nothing until the owner has seen the list.

### Milestone 2: gameplay objects

Spawns, weapons and objectives from `reference.json`, placed as real Reach
objects. This milestone has unknowns; do the finding-out first and report it
before building:

- Which palette row and item is each spawn, weapon and objective. The piece
  table covers rows 70 to 76 only. Phase 3 settled those rows from variants
  already on this PC and the Forge menu's order (plan, "Phase 3, part 3");
  the same method should work for the other rows.
- Which object fields a spawn, a weapon and an objective need (team, spawn
  sequence, respawn time, the multiplayer type, labels). `mvar.ForgeObject`
  reads and writes all of them; `info --objects` on MCC's own variants shows
  real values.
- Halo 3 weapons that Reach does not have: propose a substitute table and ask
  the owner; do not choose for him.

### Milestone 3: cleanup helpers

Buttons that select or mark the offenders in the viewport:

- **Gaps**: walked ground of the reference with no piece's top at it
  (`checks\gaps.py` is the measurement to turn into a tool).
- **Overlaps that will flicker**: two pieces whose top faces overlap in one
  plane, closer than 0.004 apart in height.
- **Lips**: a floor block's edge standing above a ramp's face
  (`checks\tilted_check.py`).

## Rules

- **Game-derived files stay local.** Everything made from the game (meshes,
  variants, `reference.json`, `fit.json`, the real piece models in
  `re_tools\forge_printer\pieces\`) stays under `E:\Proving Grounds\re_tools\`.
  Commit code, tests and docs only. The addon's own shapes are boxes from the
  committed piece table; it may load the real piece models from the local
  folder when they are there, and must work without them.
- **Leave the proven code's behaviour alone.** Do not change what `mvar.py`
  writes or how `fit.py` fits. If you believe one of them is wrong, show the
  owner the evidence and stop; a wrong byte breaks every map. Adding a small
  function beside the existing ones is fine.
- **Leave `brain/`, `native/` and `maps/` alone.** Nothing in the bot imports
  `tools/forge_printer`; keep it that way.
- **Shared working tree.** Other people commit here and have uncommitted work
  in `native/*` and `CUSTOM_CHANGELOG.md` right now. Stage only your own files
  and only your own changelog entry; your memory notes say how, and give git's
  path and the commit identity.
- **Commit locally, never push.** Small commits, each with a
  `CUSTOM_CHANGELOG.md` entry that says what was validated and what was not.
- **Ask before using subagents or workflows.**
- **Screenshots from the owner**: before saying one shows nothing wrong, cut
  out and enlarge every place two pieces meet, and measure from the placements
  where you can. This phase lost several prints to reading pictures whole.

## Done when (milestone 1)

1. Blender, run headless, enables the addon without error and prints the
   classes it registered.
2. Opening Guardian's `fit.json` makes one object per placement (336 today),
   and exporting at once, unedited, gives a variant whose added objects equal
   those `forge_printer print` writes for the same fit, template and offset:
   same palette row and item, position within 0.002, raw turn within one step
   and raw up vector within one grid step of u and v. Count and list any that
   differ. (`print` leaves out 44 for the row limit; your export must name the
   same shortfall, not hide it.)
3. For each of the eight slope-test cases (`turn_test.SLOPE_CHECKS`), an
   object given that orientation in Blender exports the raw turn and up vector
   the slope test wrote, to the same one step.
4. The counter's three figures equal `fit.within_limits`' for the same scene.
5. Each refusal in step 6 above is shown by a test: 256 pieces in one row, a
   piece leaning 50 degrees, a piece scaled 1.2, a piece outside the bounds.
6. The plain modules have tests in the suite; the Blender-only checks are a
   headless script that skips cleanly where Blender is absent. The full suite
   still passes.
7. Committed locally; the plan's checklist and a "Phase 4, milestone 1" note
   are updated.
8. The owner has loaded one variant exported from the addon, after moving a
   few pieces by hand, and compared it with Blender. If he has not yet, say so
   plainly as the one untested item; do not call the milestone done.

## If something does not go to plan

- A step fails twice for the same reason: stop retrying, write down what you
  ran and what came back, and ask the owner.
- An exported piece sits or faces differently in the game than in Blender:
  that is the most valuable thing you can find. Do not adjust numbers until it
  looks right; reduce it to the smallest case (one piece, one orientation),
  compare with `turn_test.py`'s cases, and report.
- Blender 5.1's API differs from what you expect: read the installed
  version's own documentation rather than guessing from an older one.
- Anything in this brief contradicts the repository as you find it: the
  repository wins; say what differed.

## Report back with (each milestone)

- What you built and the one step that enables it.
- The commands you ran for the "done when" list and what they printed.
- Every placement that did not survive the open-and-export round trip.
- What you did not test, and what only the owner can test in the game.
- For milestone 2, before building: the palette rows you found for gameplay
  objects and how sure each is.

## Carried over from Phase 3 (not yours to solve; do not lose them)

- The eighth Guardian print (`FP_Guardian_8.mvar`) has not been seen in the
  game: fill blocks, joined curved ramps, floors at their own heights, and
  255 pieces in one palette row (233 is the most seen loading).
- 44 small floor blocks do not fit in the Building Blocks row. The owner has
  agreed to trying walls laid on their side as floor; it is not built and
  their look is not known.
- 93 of the 109 pieces have no known price. Each print's HUD total has matched
  the prediction, so a print that uses one new piece settles its price.
- Nobody has checked whether tucked floor blocks (0.01 apart in height) or
  landings (0.005 under the floor) flicker in the game.
- Still bare on Guardian: strips under half a block wide, about 36 u2 of
  curved ramp, railings, kerbs and ceilings. These are the fitter's (Fable
  5.2's) to improve, or the owner's to finish by hand in your addon.

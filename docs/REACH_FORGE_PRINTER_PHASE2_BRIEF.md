# Reach Forge Printer — Phase 2 brief (for Opus 5.5)

Written 2026-11-21 by Fable 5.2 at the end of Phase 1. Give this file to the
Phase 2 session as its task.

## Your task

Build the command that turns one Halo 3 map into a tracing reference for
Blender: a mesh file plus one JSON of its spawns, weapons and objectives, all
in Halo: Reach world units. First map: Guardian. The reference is what Phase 3
(a different session) will fit Reach Forge pieces to, and what the owner will
trace over by hand in Blender.

This is Phase 2 of `docs/REACH_FORGE_PRINTER_PLAN.md`. Read that file's Rules
and its Phase 1 handoff note first, then `AGENTS.md`. Phase 1 (the `.mvar`
reader and writer) is finished and proven in the game; you do not need to
change it.

## What already exists

Check each of these before writing anything; most of Phase 2's raw material is
already on this PC.

- **The mesh exporter.** `tools/map_tools/bsp2obj.exe` (git-ignored, GPL, a
  separate project built on Gravemind's Reclaimer library) writes a map's level
  geometry as one OBJ. `brain/paths.py` finds it (`map_tool("bsp2obj")`) and
  finds MCC (`mcc()`); `need()` gives a clear stop when either is missing.
  Usage is in `docs/CODE_GUIDE.md`, "The map tools". It already opens Guardian:
  `bsp2obj <MCC>\halo3\maps\guardian.map <out.obj> --list` reports
  `levels\multi\guardian\guardian: 115250 triangles`.
  Note: even with `--list` it writes `<out.obj>`, so always point it at the
  local output folder below.
- **Guardian's placements, already extracted and tracked in git:**
  `maps/h3_guardian/objects.json` (58 `spawns`, 32 `equipment`, 23
  `netgame_flags`: flag spawns and returns, hills, territories, oddball spawns)
  and `maps/h3_guardian/features.json` (21 weapons, 8 grenades, 3 powerups, 23
  objectives, 2 launchers, 1 lift, each with a name, position and respawn
  time). Positions are Halo 3 world units, Z up. `tools/map_features.py`
  documents both files. Every `maps/h3_*` folder has the same pair, so the
  command should take a map name, not hard-code Guardian.
- **The Reach side.** `tools/forge_printer/mvar.py`: `MapVariant.bounds` and
  `axis_bits()`. Forge World's bounds are x -203.60..277.66, y -360.83..324.92,
  z -25.01..117.79. `docs/reach_mvar_format.md` is the format reference.
- **Blender 5.1** is installed under `C:\Program Files\Blender Foundation`.
- **Python:** `python\python.exe` in the repository root (the PATH one lacks
  numpy). Tests: `python\python.exe -I -m unittest discover -s tools -p "test_*.py"`
  (1071 OK at the start of this phase).

## What to build

1. **`tools/forge_printer/h3_reference.py`**, also reachable as
   `python\python.exe tools\forge_printer reference <map> [--out <folder>]`
   (add the subcommand to `tools/forge_printer/__main__.py`). For
   `reference h3_guardian` it:
   - runs `bsp2obj` on the map's `.map` file and writes `<out>/<map>.obj`;
   - reads `maps/<map>/objects.json` and `features.json`;
   - converts every position (mesh and placements) from Halo 3 units to Reach
     units with one named constant;
   - writes `<out>/reference.json` in the shape below.
   Default `<out>`: `E:\Proving Grounds\re_tools\forge_printer\reference\<map>\`.
2. **A Blender import script**, `tools/forge_printer/blender_import_reference.py`,
   run as `blender --python <script> -- <folder>`: loads the OBJ with Z up and
   one Blender unit per world unit, and adds one named empty per placement,
   grouped in collections `spawns`, `weapons`, `objectives`, `other`. No addon,
   no UI: that is Phase 4.
3. **The scale.** One constant, `H3_TO_REACH_SCALE`, with a comment saying how
   it was measured. Measure it; do not assume it. Both games are expected to
   use the same world unit (so 1.0), but the plan lists the conversion as an
   open task, so show evidence: compare one thing whose size is known in both
   games from data already on this PC (for example the standing player's
   height from each game's model through `model2obj`, or a physics constant the
   bot already records per game). Write the measurement and both numbers into
   your handoff note (criterion 8).

`reference.json`, with every position already in Reach units:

```json
{
  "source": {"game": "halo3", "map": "h3_guardian", "scale_from_source": 1.0},
  "mesh": "h3_guardian.obj",
  "bounds": {"min": [-20.1, -30.2, 10.0], "max": [22.3, 5.4, 31.9]},
  "spawns":     [{"pos": [1.0, -9.9, 18.2], "facing": 0.0, "team": 8, "games": ["slayer"]}],
  "weapons":    [{"name": "shotgun", "pos": [-11.3, -19.5, 16.8], "respawn": 180, "team": 8}],
  "objectives": [{"type": "ctf - flag", "pos": [0.0, 0.0, 0.0], "facing": 0.0, "team": 0, "id": 0}],
  "other":      [{"kind": "lift", "name": "…", "pos": [0.0, 0.0, 0.0]}]
}
```

The numbers above are made up to show the shape. Keep these key names; add
keys if the source data has more worth carrying (say so in your report).
`facing` must be in radians: check how `brain/` reads `facing` from
`objects.json` before deciding whether it needs converting. `bounds` is the
mesh's bounding box after scaling.

## Rules

- **Game-derived files stay local.** The OBJ, `reference.json` and anything
  else made from the game go under `E:\Proving Grounds\re_tools\forge_printer\`
  only. Commit code, tests and docs; never those files. Tests build their own
  tiny OBJ and placement dicts in the test file.
- **No Reclaimer code in this repository.** Run `bsp2obj.exe` as a separate
  process, as the bot's tools do. If you find you need something `bsp2obj`
  cannot give (collision geometry instead of render geometry, a `.glb`), stop
  and ask the owner: that is a change to the separate map tools project, not
  to this one. The render mesh as OBJ is enough for this phase.
- **Leave `brain/` and the bot alone.** Import `brain/paths.py`'s helpers; do
  not edit anything under `brain/`, `native/` or `maps/`. Saved Python in this
  tree runs in the owner's next match, so import-check every file you save.
- **Shared working tree.** Other people have uncommitted work here right now
  (`native/*.cpp|h` and an entry in `CUSTOM_CHANGELOG.md`). Stage only your own
  files and only your own changelog entry; your memory notes say how. Git is
  not on PATH; the notes give its path and the commit identity.
- **Commit locally, never push.** One or two small commits, each with a
  `CUSTOM_CHANGELOG.md` entry that says what was validated and what was not.
- **Ask before using subagents or workflows.**
- **Do not start Phase 3** (surface classification, piece fitting, budget).

## Done when

1. `python\python.exe tools\forge_printer reference h3_guardian` exits 0 and
   writes the OBJ and `reference.json`; a second run gives byte-identical
   files, or you can say exactly what differs and why.
2. `reference.json` holds every spawn, weapon and objective the two source
   files hold (counts match: 58 spawns, 21 weapons, 23 objectives, the rest
   under `other`), and every placement lies inside the mesh's bounding box
   grown by 2 units; list any that do not.
3. The OBJ's triangle count equals what `bsp2obj --list` reports for the map
   (115,250 for Guardian), or the difference is explained (the list also
   counts see-through triangles).
4. Blender, run headless (`blender --background --python … -- <folder>`),
   imports the folder without error and prints the object count, the empties
   per collection, and a mesh bounding box that equals `bounds` to 0.01.
5. `H3_TO_REACH_SCALE` has a measured value with its evidence written down.
6. A missing map, a missing `bsp2obj.exe` and a missing MCC each end with one
   clear line, not a traceback.
7. New tests pass with hand-built inputs, skip cleanly where MCC or the map
   tools are absent, and the full suite still passes.
8. The work is committed locally, the plan's checklist line "Phase 2 — H3
   reference import" is ticked, and a "Phase 2 → Phase 3" handoff note is
   added under the Phase 1 one.

## If something does not go to plan

- A step fails twice for the same reason: stop retrying, write down what you
  ran and what came back, and ask the owner.
- The scale will not come out as a clean number, or two measurements disagree
  by more than 2%: report both and ask; do not pick one.
- Guardian's size in Reach units does not fit inside Forge World's bounds:
  finish the export anyway and report the sizes; where to put it is Phase 3's.
- Anything in this brief contradicts the repository as you find it: the
  repository wins; say what differed.

## Report back with

- The commands you ran for criteria 1-4 and their output (counts, bounding
  box, Blender's printed lines).
- The scale, the two measurements behind it, and where they came from.
- Guardian's bounding box in Reach units next to Forge World's.
- Any placement you dropped, renamed or could not classify.
- What you did not test.

Then tell the owner to switch to **Fable 5.2** for Phase 3.

## Carried over from Phase 1 (not yours to solve; do not lose them)

Phase 3 needs three things only the owner can supply from inside the game,
described in the plan's Phase 1 handoff note: which palette row and item is
which Forge piece, each piece's price, and the up-vector axes and turn
direction. If the owner asks what they can do in the meantime: a Forge World
variant with one of each building block placed in a row, and one block saved
at a few known rotations, is what Phase 3 will read to settle all three.

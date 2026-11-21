# Reach Forge Printer — Blender add-on

Open an auto-built map (a `fit.json`) in Blender as Forge pieces, move, turn,
tilt, add and delete them, watch Reach's limits as you go, and export a Halo:
Reach map variant (`.mvar`) that MCC's Forge loads. Phase 4 of
`docs/REACH_FORGE_PRINTER_PLAN.md`, milestone 1.

## Install (once)

Close Blender, then from the repository folder:

```
python\python.exe tools\forge_printer\blender_addon\install.py
```

It links this folder into Blender's add-ons folder (no copy, so Blender always
runs the repository's version) and enables the add-on. In Blender it is in the
3D view's sidebar: press **N**, tab **Forge**. To take it out again:
`install.py --remove` (removes the link only).

## Use

1. **Open fit.json** (Forge tab). For Guardian it is
   `E:\Proving Grounds\re_tools\forge_printer\reference\h3_guardian\fit.json`
   with offset **-39 -135 8**. Every placement becomes one object named after
   its piece, in a collection per part (`Forge floor`, `Forge slope`,
   `Forge landing`, `Forge wall`; pieces you add go in `Forge added`). The
   reference level comes in behind them as the `Reference backdrop`, which
   cannot be clicked on. Wire / Solid floors / Hidden switches how it is drawn:
   the pieces' tops lie in the reference's floors, so solid floors hide them.
2. **Template**: a Forge World variant your MCC saved (the one the prints use is
   "Bot Testing Grounds", in MCC's `LocalLow\MCC\LocalFiles\<id>\HaloReach\Map`
   folder). It is copied, never changed. The counts use it.
3. **Edit** with Blender's own tools: **G** moves, **R** turns (R then X, Y or Z
   tilts), **X** deletes, **Shift+D** copies. Reach cannot scale a piece: a
   scaled piece is not written (Alt+S sets the scale back to 1).
4. **Add**: put the 3D cursor where the piece goes (Shift + right-click), pick
   the category in **Forge palette** and click the piece. It lands at the
   cursor, selected, ready for G and R.
5. **Counts** update as you work: objects of 651, pieces in each Forge
   category of 255, the budget. Pieces whose price nobody has seen yet are
   shown as "+ N with no price known" and are not in the budget figure.
6. **Export .mvar** writes a new file into the folder shown (default
   `E:\Proving Grounds\re_tools\forge_printer\`), named after the title, never
   over an existing file. If anything cannot be written, a list comes up first
   and those pieces are selected; nothing is written unless you press
   **Export the rest**. The full list is in Blender's text "Forge export report".
   Copy the file into MCC's Reach `Map` folder with MCC closed.

Hidden pieces are still exported; delete a piece to leave it out.

## What cannot be written, and why

- a scaled or mirrored piece, or one whose mesh was edited (Reach places a
  piece at its own size);
- a piece leaning more than 45 degrees from straight up, unless it is within
  45 degrees of +X (east) — what a variant's up value can hold. A piece lying
  exactly on its side facing -X, +Y or -Y, or upside down, is written; for -X,
  -Y and -Z the export warns that the turn under that up has not been seen in
  the game;
- a piece outside Forge World's bounds after the offset;
- more than 255 pieces in one Forge category, more than 651 objects, or more
  than the budget: `fit.within_limits` keeps what `print` would keep (floors
  first, fill blocks last) and the rest are listed.

Pieces known only by their model's name (most of Decorative) are not in the
palette yet.

## Checks

- `python\python.exe -I -m unittest discover -s tools -p "test_forge_printer_addon*.py"`:
  the plain modules (`convert.py`, `export.py`) and, when Blender is installed,
  `headless_check.py` inside Blender (it skips without Blender).
- The Guardian round trip (needs the local reference and the template):

  ```
  "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python-exit-code 1 --python tools\forge_printer\blender_addon\headless_check.py -- --guardian "E:\Proving Grounds\re_tools\forge_printer\reference\h3_guardian" --template <template.mvar> --offset -39 -135 8 --out <empty folder>
  ```

  It opens the fit through the add-on, exports it unedited, writes `print`'s
  file for the same fit beside it and compares them object by object.

## Files

- `__init__.py` — what Blender loads; imports nothing from Blender itself.
- `ui.py` — operators, panels, scene settings (needs Blender).
- `convert.py` — a Blender object's world matrix to a placement and back,
  with the reasons a piece cannot be written. No Blender.
- `export.py` — the counter, what an export would write, writing it. No Blender.
- `install.py`, `headless_check.py` — the install step and the Blender-side checks.

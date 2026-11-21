# Reach Banshee pilot: where it stands (2026-11-20)

The owner's goal: one Banshee bot gets **18–20 Banshee kills a game, three games in a row**. He wants kills first and
survival second. Ten kills in one life is worth dying for. A Banshee that stays alive without doing anything is not
wanted.

None of this is committed yet. The changes are uncommitted in `brain/bot.py`, which means they run live in the next
match. Nothing has been tested in game since the two newest changes.

## Test setup (`tools/banshee_sim.py`)

- Boneyard, variant `reach_70_boneyard/variants/v8d2f4510`, 8v8 Slayer to 100.
- Blue is all Demon, and one Blue bot is always seated in the Banshee (`--seat-team 1`). Red is all Normal.
- The sim runs the real `Bot.think` and Director code.

Command (one game; run seeds 1–10 for a batch):

```powershell
python\python.exe -I tools\banshee_sim.py --seed 1 --map reach_70_boneyard/variants/v8d2f4510 --tiers demon,demon,demon,demon,demon,demon,demon,demon --red-tiers average,average,average,average,average,average,average,average --seat-team 1 --quiet --trace out.jsonl --json out.json
```

The kill count to compare is `best.banshee_kills` in the json. Each `events` entry is `[t, killer, victim, how]`.

Sim assumptions to know about:

- The Banshee takes 82 DMR rounds to destroy. The owner estimates 38 hits plus damage thresholds he couldn't find, so
  this splits the difference.
- The bomb's kill radius is 1.8 u (an assumption).
- The sim Banshee flies 8.3 u/s at full throttle without boosting. In live Reach it flies about 4.3 u/s unboosted.

## Results (best pilot's Banshee kills, 10 games each)

| Batch | Mean | Median | Min–max | Note |
|---|---|---|---|---|
| s4 | 6.2 | | | best before the live fixes |
| p1 | 6.3 | | 2–12 | the pull-out stops short of the target |
| p2 | 6.6 | 6 | 3–12 | plus: holds the bomb when the aim slides off the man |
| f1 | **7.3** | 7 | 4–12 | plus: waits near the fight (below) |
| k1 | — | | | sticky target (below); stopped before any game finished |

There are about 3 flights a game and about 2.4 kills per flight. The first flight usually dies within 30–90 s.

## The two newest changes (both in `brain/bot.py`)

### 1. `air_fight_mid` + `air_seek`: wait near the fight, not at Red's base

With nobody in sight, the pilot used to fly to the open spot nearest Red's flag and hover there. In one game it hovered
290 s of a 445 s flight for one kill, while Red fought 35–50 u away round the scaffolding. Its runs at them from there
timed out (`AIR_CHASE_S`) before it arrived.

Now it waits at the open spot (`air_open_spots`) nearest the median position of enemies on foot it has known about in
the last `AIR_SEEK_KNOWN` = 15 s. It keeps its current spot while that spot is within `AIR_SEEK_KEEP` = 8 u of the best
one, so it doesn't swing between spots. If it knows of nobody, it falls back to Red's flag. Result: 6.6 → 7.3.

### 2. `run_hold`: the bomber keeps its man (`AIR_BOMBER_SWITCH_R` = 9)

Measured over the f1 games:

- 1203 attack runs, median length **0.7 s**.
- 799 runs ended with a switch to another man while the first one was still alive. The new man was farther away in 469
  of them, and the two men were a median 13 u apart.
- In half of those switches the old man was in sight the row before. He had dropped out of the filtered sight list
  (no-fly and open-sky filters, LOS flicker) for a single tick.

This matches what the owner saw live: it "gets a glimpse of one, shoots at it, then flicks away". Other pilots still
switch to any man in sight within `AIR_RUN_SWITCH_R` = 22 u. A Reach bomber now only switches for a man within 9 u.
**Untested:** rerun the 10 games and compare against f1's 7.3.

## Known open problems

- **The Terrain feet-floor rule.** In `Terrain._ray`, `FEET_SLAB` reads lines steeper than about 51° between an aircraft
  and a man as blocked, in both directions. That affects `sees` / `shot_los` / `fire_gate`; `aim_hit` is not affected.
  A fix was tried and reverted because kills went down: Red could then see the Banshee overhead. Whether to fix it is the
  owner's call.
- **Learned fly cells.** The high fly cells on Boneyard are fragmented into 580 pieces, and `fly_way` returns None
  between pieces. There is no learned air over the middle (x 244–280, y 76–116), which is where Red spends a lot of
  time.
- **Where Red stands.** About 21% of Red's alive time is in or under the scaffolding no-fly box
  (x 257–273.5, y 74–110), where the bomber can't attack. Large open areas in the west (x 232–240, y 48–88) and north
  (y 112–128) have Red in them but few Banshee kills.
- **Live flying vs the owner's** (one owner flight compared with two live Partyland matches):

  | | Owner | Bot |
  |---|---|---|
  | Turnarounds per minute | 8.4 | 17.9 |
  | Dives per minute | 1.4 | 0 |

  Height and distance to enemies already match. The owner said he doesn't care about boosting; he wants kills.

## Rules from AGENTS.md that apply

- Record changes and validation in `CUSTOM_CHANGELOG.md`. The Banshee entry under Unreleased already covers everything up
  to p2.
- Stage only your own hunks.
- Get the owner's approval before any push or release.
- Run the tests before committing:

  ```powershell
  python\python.exe -I -m unittest discover -s tools -p "test_*.py"
  ```

  The suite last passed with 1000 tests OK, before the two newest changes.

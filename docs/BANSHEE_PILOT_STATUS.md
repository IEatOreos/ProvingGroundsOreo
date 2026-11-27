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

## Nov 23: the pilot's line down fixed, bomb only

Live Spire (bug report 20261123-173345): the pilot dived on men and did not fire. `Terrain._ray`'s shooter's-floor rule
read every line steeper than about 45° down from the Banshee as blocked: 8 of 1318 enemy positions under it were in
sight, about 5 bombs in a 310 s ride.

- `brain/terrain.py`: the rule is skipped for a shooter more than `NO_FLOOR_H` = 1.5 u over the floor (a pilot). On the
  same recording 1020 of the 1318 now read in sight.
- `brain/bot.py`: a Reach Banshee pilot never fires its cannons; its trigger is the bomb's shot only (the owner's order).
- The other direction is unchanged: a man on the ground still has no line to a Banshee steeply over him.
- Tests 1395 OK. Untested in game. The k1 batch (sticky target) was never finished and is now mixed with this change.
- Sim batch b1 (seeds 1–5, same setup, with this change and the sticky target): 6, 13, 4, 6, 7, mean 7.2. No gain over
  f1's 7.3 on Boneyard. "No clear line: hold fire" is nearly gone (0–6 rows a game), but the pilots still let go only
  about 10–25 bombs a game and spend 24–39% of their rows on a man out of sight. Bombs per minute is the next thing to
  raise.

## Nov 25: dives reach bomb range, bombs on men in vehicles

Live Spire 20261125-175509: two pilots, 91 s of flying, 18 runs, no bomb. Nov 23's two fixes were committed (b897f54)
and are unchanged.

- The dive's ground guard (`air_guard`) used Spire's `run_floor` of 4 u on a look that stops 5 u short of the man, so
  every run pulled out 19–32 u off; the bomb reaches 18. A bomber diving on its man now uses `AIR_RUN_FLOOR` (1.5 u).
- `bomb_lined` and `air_snap_bomb` skipped men in vehicles (12 of the 18 runs' targets). They count now, and a selected
  bomb still goes from 3 u (`AIR_BOMB_NEAR`).
- Uncommitted. New test file `tools/test_banshee_bomb_riders.py`. Untested in game; the pull-out change has no test.
- Live Spire 20261125-183258 (after the two changes above): one 34 s flight, 1 bomb, 2 kills, then dead to the
  return-to-battlefield countdown. Past the east edge the level data has no ground and `ground()` gave 0.0, 43 u over
  the pilot, so it climbed at full pitch for 11 s. `Terrain.height_over` now uses the map's lowest known ground there.
  It flew out because `kill_hit` counted Spire's 150 u soft safe sphere, which covers the air past the soft safe box's
  east side; the sphere is now left out where the kind has a box (`air_safes`), so the pilot's probe and `oob_escape`
  treat the box's sides as the edge. Open: the pilot read back inside the box for its last 1.7 s and still died, so
  the game's real edge may sit further in than `killzones.json`. `tools/test_spire_safe_edge.py`. Untested in game.
- Live Spire 20261125-183823 (the owner's three Theater frames): the bomb was selected 14–18 u out, then the run ended
  or a guard swung the nose in the 0.25 s before its shot, and it was put away unfired. Now the bomb is selected once
  after boarding and kept selected (`fuel_rod`, `bomb_kept`), so the shot goes the tick a man is under the nose with
  the 3.2 s recharge done. The aim is at his feet for the whole run. Risk: the selection is not read back from the
  game; if they disagree the trigger fires cannons until the next boarding. `tools/banshee_sim.py` not rerun.
- **Measured, live Spire 20261125-193322** (all the changes above, one pilot, 260 s flying): 15 bombs (3.5 a minute),
  3 kills, 1 death. Chances without a shot (a man 3–18 u, a line, under the view, bomb recharged): 0.1 s in all, so it
  now fires when it can. But 62 dives, 17 reached 18 u, 15 bombed; 45 dives ended before bomb range. Time: 20% diving
  at a man with a line, 31% climb-out and turn, 30% with a guard steering ("wall ahead" 15% of dives' time). Every bomb
  went at 17–19 u, the tick the man came into reach: 3 of 4 let go under 9 u/s killed, 0 of 9 at 12–27 u/s.
- **Measured, sim batch c1** (Boneyard seeds 1–5, the changes up to the kept bomb) against b1: bombs a minute 3.0 → 3.7,
  bombs that hit 44 of 68 → 27 of 95, Banshee kills 36 → 18, kills a minute 1.6 → 0.7, Banshees lost 10 → 11. More
  bombs, fewer kills: the instant shot at the edge of reach misses.
- Tried and taken out the same evening: the kept bomb's shot held to `AIR_BOMBER_DROP_R` (11 u) with the craft's nose
  on him. Replayed over 20261125-193322, the view was on a man with a line inside 11 u on 2 of 62 dives, inside 18 u
  on 15 (the 15 bombs it fired), inside 26 u on 26. Its sim batch (d1) was stopped unfinished.
- **Why "it targets, then can't shoot"** (same match, every dive listed): the runs came in 12–24 u over their man and
  `air_pass` ended them 6 u *flat* from him (`PASS_OVER`), still 19–24 u off by height, past the bomb's 18 u. Now a
  Reach bomber more than `AIR_BOMB_STEEP_UP` (8 u) over its man with the bomb ready keeps diving at him until 6 u off
  in all three axes or 4 u over the floor. Sim batch e1 (Boneyard seeds 1–5, Spire seeds 1–3) is its test.
- **Measured, sim batch e1** (Boneyard seeds 1–5, with the dive-on-down change, before the no-boost one):

  | Batch | Bombs | Hit | Banshee kills | Kills a minute | Banshees lost |
  |---|---|---|---|---|---|
  | b1, before Nov 25 | 68 | 44 | 36 | 1.6 | 10 |
  | c1, kept bomb | 95 | 27 | 18 | 0.7 | 11 |
  | e1, plus dive on down | 67 | 34 | 21 | 0.9 | 12 |

  On Boneyard the sim still rates Nov 25's set below b1. The sim Banshee does not fly on Spire (no rides in three
  games), so it says nothing of the Spire-only fixes. Variant runs (current, the snap shot only with the craft's nose
  on him, the bomb not kept; seeds 1–4, `scratchpad/variant.py` patches in memory) are the test of which change costs
  the hits.
- **Boost into the bomb** (the owner's question, same match): the dive was boosted 36% of its time and the boost let
  off one tick (0.03 s) before the bomb's press on 9 of 15 bombs. Kills: 3, all with 0.8 s or less of boost in the 2 s
  before the press (7–9 u/s); 0 of the 9 with 1.0–1.9 s of it (11–17 u/s). Now a Reach bomber boosts in only past
  `AIR_BOMB_NO_BOOST_R` (30 u) of its man. Not known: whether the game refuses a bomb that soon after a boost, or the
  bomb just misses at that speed. The sim does not model either, so only a live match can show this one.
- Still open from that match: flights lasted 32 s and 59 s, and runs also ended on "wall ahead" and "shot at, jinking".

## Nov 26: target + release, 12.25 sim kills a game

Goal (Nov 25): 15-20 Banshee kills a game, any map. Method: a read-only diagnosis (five analysts + skeptics,
`scratchpad/wf1_result.json`), six candidate fixes as in-memory patches (`scratchpad/cands/`, applied with
`scratchpad/variant.py` + `patchlib.py`, no project edits), reviewed, raced in full sim games (`scratchpad/simqueue.py`),
the winners ported with the same text edits (`scratchpad/port.py`).

Sim Boneyard, kills a game (seeds in brackets):

| Variant | Games | Kills a game | Kills a bomb |
|---|---|---|---|
| The pilot as it was | 14 | 3.8 (0-11) | 0.13-0.33 |
| Target (c1) alone | 6 | 6.8 | 0.24-0.30 |
| Release (c4) alone | 2 | 4.5 | 0.75 |
| **Target + release** | 8 | **12.25** (13, 20, 14, 6, 8, 15, 8, 14) | 0.85-0.88 |
| All five candidates | 7 | 8.9 | 0.61-0.83 |
| **Shipped brain, unpatched** (Nov 26, `brain/bot.py` md5 ebd41ff6) | 8 | **11.75** (13, 20, 8, 6, 8, 15, 10, 14) | 0.85 |
| Shipped + looser nose gate 0.45 rad (c9) | 3 | 9.0 (seeds 5-7: 4, 14, 9) | 0.68 |
| Shipped + climb-out (c2) | 4 | 11.5 (seeds 4-7: 10, 22, 5, 9) | 0.81 |
| Shipped + stay off a bunch until clear (c8) | 4 | 11.0 (seeds 4-7: 6, 22, 10, 6) | 0.96 |
| Shipped + survival (c6) | 8 | 12.1 (21, 10, 12, 7, 12, 5, 13, 17) | 0.78 |
| Five without dive-end | 4 | 6.25 | 0.64 |

None of the four add-ons beat the shipped pair on the same seeds by more than noise. c6 (survival) also got wedged
61-151 s in Boneyard's scaffolding in 3 of its games (the shipped brain: never over 8.6 s in 8), so its review said
not to ship it (`scratchpad/wf4/review_c6`). Full suite 1819 tests, the 2 old test_layout_lifts failures.

Ported to `brain/bot.py`: `air_bomb_man`, `air_feet_open`, the Reach Banshee pilot's 3D view cone in
`Perception.update`, `bomb_release`, `bomb_leaving` (their constants after `AIR_BOMB_NO_BOOST_R`). Left out: the
climb-out (c2), seek orbit (c5), dive-end (c3) and survival (c6) candidates.

Also Nov 26: the boarding fix (no dud ban on an aircraft a teammate just flew; a bot sent to an empty Banshee while our
Falcon flies), and live pilot rows now log the craft's nose `vfwd` and speed `vspd`.

Still open:
- **The opening**: in the sim every first ride with the combo died 13-23 s in, inside Red's whole spawn group; the bunch
  break-off lasts only until the bomb is ready (a median 3.3 s, 13.5 u out). Candidate c8 (stay off until clear) is in
  round 4.
- **The sim is not the game.** On Spire (`tools/banshee_sim.py`'s opt-in Spire pad, unreviewed) the old pilot scored 20
  a game, live 2-3: the sim's bomb is far deadlier there. Kills a bomb live 0.21, sim 0.3-0.8. The live `vfwd` logging
  will show whether a Reach bomb leaves along the nose (as the release fix assumes) or the reticle.
- Untested in game.

## Known open problems

- **The Terrain feet-floor rule, upward.** `FEET_SLAB` still reads lines steeper than about 45° from a man up to an
  aircraft as blocked. Fixing both directions was tried and reverted because kills went down: Red could then see the
  Banshee overhead. Whether to fix that half is the owner's call.
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

# Aircraft Hold Fire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bots on foot below Demon/Mythic/Noble hold fire on an enemy Banshee's or Falcon's crew until that aircraft has killed enough of their team (live matches only).

**Architecture:** A small counter (`tools/air_kills.py`) fed by the game's kill record (Reach) or the bots' own death guesses (fallback) keeps `{aircraft handle: {victim team: kills}}`; `tools/live_bots.py` hands it to the bots as `snap.air_kills`. `brain/bot.py` leaves held crew out of its fight targets; `brain/profiles.py` gives each difficulty its number. No `snap.air_kills` (every sim, every existing test) means today's play.

**Tech Stack:** Python (bundled `python\python.exe`), unittest.

**Spec:** `docs/AIRCRAFT_HOLD_FIRE_DESIGN.md`

## Global Constraints

- Kinds: `{"banshee", "falcon"}` by `vehicles.kind_of`.
- Kills to unlock: Demon, Mythic, Noble 0; Legendary 1; Heroic, Tactician, Blind 2; Normal 3; Easy 5; Scaling 0 (today's play).
- Self-defence: `AIR_SELF_DEFENCE_S = 3.0` after the last hit from anyone aboard that aircraft.
- Bots in any vehicle seat: never held. Sims (`tools/real_sim.py`, `tools/banshee_sim.py`) untouched.
- Count resets only when the aircraft reads `dead` or leaves `snap.vehicles`.
- No switch. Comments in the project's "(custom, Nov 24, the owner: ...)" style. Upstream code and notes kept.
- Tests: `python\python.exe -I -m unittest discover -s tools -p "test_*.py"`.

## Review Focus

- Killer and victim die in the same pass (a trade): his seat comes from the previous pass's players → test in Task 2.
- Free for all (no teams): no hold at all (`snap.air_kills` stays None) → test in Task 4.
- Kill record stops after read failures mid-match: the guess fallback takes over, no double count while it runs → test in Task 4.
- A bot riding as a passenger or gunner is never held → test in Task 3.
- A destroyed Banshee's replacement starts at 0 → test in Task 2.

---

### Task 1: Each difficulty's number

**Files:**
- Modify: `brain/profiles.py` (after `fixed_demon`)
- Test: `tools/test_air_hold.py` (new)

**Interfaces:**
- Produces: `profiles.air_hold_kills(prof) -> int`

- [ ] **Step 1: Write the failing tests** `AirHoldKills.test_each_difficulty`: profiles built the way existing tests build them (`profiles.make` / the tier helpers) for Demon, Noble, Mythic → 0; Legendary → 1; Heroic, Tactician, Blind → 2; Normal → 3; Easy → 5; a Scaling profile (tier "top", `extra` populated) → 0.
- [ ] **Step 2: Run** `python\python.exe -I -m unittest tools.test_air_hold -v` → FAIL (no `air_hold_kills`).
- [ ] **Step 3: Implement** `air_hold_kills(prof)`: `extra is not None` → 0; `fixed_demon or fixed_mythic` → 0; `fixed_blind or fixed_tactician` → 2; tier `"top"` → 1; `"strong"` 2, `"average"` 3, `"novice"` 5; else 0. Table as a module constant `AIR_HOLD_KILLS`.
- [ ] **Step 4: Run** the same command → PASS.

### Task 2: The counter

**Files:**
- Create: `tools/air_kills.py`
- Test: `tools/test_air_hold.py`

**Interfaces:**
- Consumes: `kill_record.read(row, teams)`; `vehicles.kind_of`.
- Produces: `class AirKills` with `add(killer_id, victim_team, snap, before=None) -> bool`, `row(row, snap, teams, before=None) -> bool`, `prune(snap) -> None`, `table() -> dict` (`{handle: {team: n}}`, a copy). `AIR_KINDS = {"banshee", "falcon"}`.

- [ ] **Step 1: Write the failing tests** (fake snap: `players` with `id, team, vehicle, alive`, `player(i)`, `vehicles` dicts with `handle, kind, dead`):
  - `test_pilot_kill_counts`: killer in a `"banshee"` handle 7, victim team 1 → `table() == {7: {1: 1}}`.
  - `test_falcon_gunner_counts_to_falcon`: gunner whose `vehicle` is the Falcon's handle (`gunner_seat=True`) → counts to that handle.
  - `test_ground_vehicle_and_foot_not_counted`: Warthog driver, man on foot → `{}`.
  - `test_row_kill_counts_person_victim`: a kill-record row (`v`, `k`, `new=True`, `vt=1`, `kt=0`, `vb=0`, `vp`, `kp`, `hits=[]`, `c=None`) → counted; same row as a betrayal (`kt=vt`) and as a death (`k=None`) → not.
  - `test_trade_uses_before`: killer dead in `snap` (vehicle -1), aboard in `before` → counted.
  - `test_prune_on_dead_or_gone`: `dead=True` → dropped; handle missing from `vehicles` → dropped; a new handle starts at 0.
- [ ] **Step 2: Run** → FAIL (no module).
- [ ] **Step 3: Implement** `AirKills` (killer's handle from `snap.player(k)` aboard, else `before[k]`; kind from `snap.vehicles` by handle; `row` uses `kill_record.read` and counts only kind `"kill"` with `vt` not None).
- [ ] **Step 4: Run** → PASS.

### Task 3: The hold in the bot

**Files:**
- Modify: `brain/core.py` `Snapshot` (add `air_kills: object = None  # (custom, Nov 24) live only: tools/air_kills.py`)
- Modify: `brain/bot.py` — constants near `AIR_GUN_R`; `pick_target`; `decide` (first `pick_target` block, and before `s.last_scores = scores`); patrol targets (`patrol_seen`, ~line 4099); `enemy_vehicle`
- Test: `tools/test_air_hold.py`

**Interfaces:**
- Consumes: `profiles.air_hold_kills`, `air_kills.AIR_KINDS` (copy the set into bot.py as `AIR_HOLD_KINDS`: brain/ never imports tools/).
- Produces: `Bot.air_held(now, me, snap, k) -> bool`; `Bot.air_hold_scores(now, me, snap, scores) -> None`.

- [ ] **Step 1: Write the failing tests** (a real `Bot` built as `tools/test_demon_anticipate.py` builds one):
  - `test_no_table_no_hold`: `snap.air_kills = None` → `air_held` False for a Banshee pilot.
  - `test_legendary_waits_for_one_kill`: Legendary on foot, pilot aboard Banshee h: table `{}` → held; `{h: {my_team: 1}}` → not held; kills against the other team only → held.
  - `test_demon_never_held`, `test_scaling_never_held`.
  - `test_in_vehicle_never_held`: `me.vehicle` set → False.
  - `test_self_defence`: `per.attacker_id` = a Falcon gunner of h, `attacker_t = now - 1.0` → pilot of h not held; `now - 3.5` → held.
  - `test_pick_target_skips_held`: seen `[pilot, man on foot]` → the man; seen `[pilot]` → None.
  - `test_scores_drop_held_fight`: `scores = {("fight", pilot): 2.0, ("fight", man): 1.0}` → only the man's key left.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**:
  - `air_held`: False unless `snap.air_kills` is a dict, `me.vehicle in (None, -1)`, need > 0, `k` aboard a vehicle whose `kind_of` is in `AIR_HOLD_KINDS`, and no self-defence (`per.attacker_id` aboard the same handle within `AIR_SELF_DEFENCE_S`); then `table.get(h, {}).get(me.team, 0) < need`.
  - `pick_target`: filter `seen` by `not air_held` first; empty → return None.
  - `decide`: the first block uses `t` only when not None; `air_hold_scores` called right after `s.plant_hold(...)`.
  - patrol: `patrol_seen` filtered the same way.
  - `enemy_vehicle`: skip a held pilot (the Grenadier's hunt).
- [ ] **Step 4: Run** `tools.test_air_hold` → PASS, then the whole suite → same pass count as before plus the new tests.

### Task 4: Live wiring

**Files:**
- Modify: `tools/live_bots.py` (the `kills` setup ~line 1316, the kill rows ~line 1790, `events()` ~line 763, right after `snap = snapshot(...)` ~line 1560)
- Test: `tools/test_air_hold.py`

**Interfaces:**
- Consumes: `AirKills`.

- [ ] **Step 1: Write the failing tests**:
  - `test_events_fallback_counts_when_no_record`: `events(..., air=AirKills(), record=False)` with a bot that died fighting a Banshee pilot → counted; with `record=True` → not counted (the record counts it).
  - `test_air_table_off_without_teams`: `live_bots.air_table(air, snap, teams=False)` → None; `teams=True` → the table after `prune`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**:
  - `Watch` created for every `LiveReach` match; `trace.write(...)` lines and the `kill_record` header only `if trace`; map memory (`book`) as today.
  - each row: `air.row(row, snap, TEAMS, before)` alongside the existing uses.
  - `events(bots, directors, before, snap, now, air=None, record=False)`: on a bot's death with `air` and not `record`, `air.add(killer, me.team, snap, before)`. The loop passes `record=kills is not None`.
  - `air_table(air, snap, teams) -> dict | None`: `air.prune(snap)`, then `air.table()` when `teams` else None; set `snap.air_kills = air_table(air, snap, TEAMS)` right after each snapshot.
- [ ] **Step 4: Run** `tools.test_air_hold` → PASS; import check `python\python.exe -I -c "import sys; sys.path[:0]=['.','tools']; import brain.bot, live_bots, air_kills"` → no error; whole suite → all pass.

### Task 5: Changelog and local commit

**Files:**
- Modify: `CUSTOM_CHANGELOG.md` (new entry at the top of today's section; this file has someone else's uncommitted edits: stage only this entry's hunk)

- [ ] **Step 1:** Write the entry: what changed, the numbers, the owner's calls, the tests run, "untested in game".
- [ ] **Step 2:** Whole suite once more → all pass.
- [ ] **Step 3:** Commit locally only (no push): `brain/profiles.py`, `brain/core.py`, `brain/bot.py`, `tools/live_bots.py`, `tools/air_kills.py`, `tools/test_air_hold.py`, both docs, and only my hunk of `CUSTOM_CHANGELOG.md` (temp-index commit if the real index holds others' staged work); check every committed `.py` blob compiles; message by `-F` file, ending with the Co-Authored-By line.
- [ ] **Step 4:** Tell the owner the brain restarts with the launcher at his next match (no match running → restart is his call).

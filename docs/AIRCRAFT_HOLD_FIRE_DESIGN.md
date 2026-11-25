# Aircraft hold fire (design, 2026-11-24)

Status: design for the owner's approval. Nothing built yet.

## Why

The owner: Banshees should not "get mutilated at once, but also they're not flying freely". Today a bot shoots an
enemy aircraft's pilot by the same rules as anyone else (brain/bot.py `threat` / `pick_target`), so a whole team opens
up on a Banshee the moment it is seen. The better bots should answer it at once and the rest should join in only once
it has hurt the team.

## The rule (the owner's)

An enemy **Banshee or Falcon**. Every kill made by anyone aboard it (pilot, Falcon gunners) counts toward that one
aircraft, against the team of the player who died. People count, not only bots. The count goes back to 0 only when the
aircraft is destroyed.

A bot **on foot** holds fire on everyone aboard that aircraft until the aircraft has killed this many of its team:

| Difficulty | Kills before it shoots |
|---|---|
| Demon, Mythic, Noble | 0 (at once) |
| Legendary | 1 |
| Heroic, Tactician, Blind | 2 |
| Normal | 3 |
| Easy | 5 |

**Self-defence:** a bot that is being hit by someone aboard may shoot back at him.

A held bot keeps fighting everyone else. Bots in vehicles keep today's rules (vehicle_pick / vehicles.target_score).

## Approaches

- **A. The team's director keeps the count** (brain/director.py), fed by the game's kill record live and by death
  reports in the sims. The rule would play in tools/real_sim.py and tools/banshee_sim.py too.
- **B. tools/live_bots.py keeps the count and hands it to the bots in the snapshot.** Live matches only; the sims
  never set it, so they play exactly as today.

**The owner picked B**: live only, the sims left alone (no sim file changed, no sim behaviour changed).

## How (B)

1. **The count** (tools/live_bots.py), every brain pass:
   - Reach: `kill_record.Watch` runs in every Reach match (today only in recorded ones); it still writes to the
     recording only when there is one. Each row read as a kill (`kill_record.read`, kind "kill": not a betrayal or a
     suicide) whose credited killer rides a Banshee or Falcon adds 1 to `{aircraft handle: {victim's team: n}}`. The
     killer's vehicle comes from the snapshot (a Falcon gunner already reads as riding the Falcon itself: live_bots
     folds gun seats onto their carrier, `gunner_seat`).
   - Fallback, when there is no kill record (other games, or the record switched itself off after read failures): a
     bot's death as `events()` already credits it (the man it fought, else the nearest it knew). Bots only, a guess.
   - An aircraft whose vehicle reads destroyed (`dead`) or that is gone from the vehicle list is dropped: its count is 0.
   - Handed to the bots as `snap.air_kills`.
2. **The hold** (brain/bot.py): an enemy aboard a Banshee or Falcon is left out of the bot's fight targets while the
   bot is on foot, `snap.air_kills` is set, and that aircraft's kills against the bot's team are under the bot's
   number. Not left out while he (or anyone aboard the same aircraft) hit this bot in the last ~3 s (the bot's own
   attacker read, `per.attacker_id` / `attacker_t`). The Grenadier's vehicle hunt skips a held aircraft too.
   No `snap.air_kills` (every sim, every test before this): no hold, as today.

## Calls I made (the owner can overrule)

- **Scaling** bots are left as today (shoot at once): AGENTS.md keeps Scaling out of fixed-tier rules.
- **Self-defence window ~3 s** after the last hit from that aircraft, then it holds again.
- A held bot **does not run** from the aircraft or hide any more than today; only its trigger and target change.
- Betrayals, suicides and kills after the match ends do not count.
- A count is per victim team, so in a game with more than two teams each team keeps its own.

## Not in scope

- Bots in vehicles, the sims (tools/real_sim.py, tools/banshee_sim.py) and their goals, other aircraft (Hornet, Sabre,
  Seraph), how pilots fly.

## Checks

- Unit tests: each difficulty's number, Scaling and in-vehicle bots unaffected, no `snap.air_kills` = today's play,
  self-defence opens and closes, a person's death counts, a Falcon gunner's kill counts to his Falcon, betrayals do
  not count, the count drops when the aircraft is destroyed.
- Import check of brain/ and tools/live_bots.py; the full unit test run.
- Untested in game until the owner's next match.

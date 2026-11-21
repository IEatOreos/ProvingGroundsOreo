# Bot simulation: the agreed plan (Nov 17, 2026)

## Where it stands (Nov 18: built; waiting for the owner's test run)

**Built and checked.** `botcore_pg14.dll` runs a round when each Project Reach match ends; the menu row and the
site's edit-mode button play rounds on demand. It goes live at MCC's next start. Until then no simulated match has
been written to the real Service Record (there is no `native/bin/service_record/sim.db`). All of it is in
CUSTOM_CHANGELOG.md; the notes below are the build's history.

Done:
- `tools/sim_engine.py`: the model (`fit`, real matches only) and the fight-by-fight match (`play`), with all
  10 playlist gametypes. Weapons and vehicles come from each map's own game files; medals follow Reach's rules or real
  rates.
- `tools/bot_sim.py`: population (pace, grinders, BTB lean), lobbies (clans, balanced teams), the PG vote port, and
  SQLite storage (seed + inputs + compressed report and kill rows, about 7 KB a match). Also `--after`, `--rounds`,
  `--stats`, `--check` and `--verify`.
- The merge: `service_record.build` adds simulated matches in memory, `collect` counts them and uses their Forge
  layout, `write_last_match` takes the newest match a person played, and `bot_career` totals include them, with
  resets covering them.
- Checked against the real matches (`bot_sim.py --check`, scratch copy of the store):
  - kills a player a minute: 1.46 simulated, 1.49 real;
  - real K/D inside the simulated 90% band for 90% of players;
  - win-call Brier score 0.21 (a coin flip is 0.25);
  - medals per 100 kills close to real ones (Revenge 7.6 vs 7.7, Avenger 5.9 vs 5.5).
  - 811 tests pass.
- Measured: a round is about 25 lobbies (20 Arena, 5 BTB), under a second.

Done in the second sitting:
- Site extras: `service_record.today_block`, in data as `today`; `app.js todayPanels()` on the leaderboard; CSS at
  the end of style.css. A scratch build (94 simulated matches) filled them and the page loaded.
- The site's button: `service_record_edit.py /api/simulate {"rounds": 1..20}` and `app.js simulateForm()` in edit
  mode, beside Reset all. Not pressed yet: it writes real simulated matches.
- `bot_sim.run` writes sim_status.txt once, for all the rounds.
- The full test suite was not re-run after these (the run was stopped as the owner shut down); run it first.

Left, in order:
1. Run the whole suite: `python\python.exe -I -m unittest discover -s tools -p "test_*.py"`.
2. (was 1-2, done above)
3. Project Reach (`native/proving_grounds.cpp`):
   - `stats_build` runs `bot_sim.py --after <id>` after the first build, then bot_career and service_record again,
     at BELOW_NORMAL priority;
   - a SIMULATE MATCHES menu row (Left/Right rounds, Enter runs; shows sim_status.txt).
   - Then build a new DLL tag.
4. `tools/test_bot_sim.py`:
   - determinism;
   - kill rows equal the report (kill_check);
   - people never in a match;
   - clans on one team;
   - pace average;
   - storage round trip;
   - collect / bot_career count sims;
   - resets mark them;
   - write_last_match picks the person's match.
5. CUSTOM_CHANGELOG entry, then the owner's test run.

Correction to an earlier answer: Asylum (6) and Pinnacle (4) do have real kill records; they were filed under
their Forge layouts.

The owner's goal: bots only ever play when he plays, always against him, so a bot gets about one game in
a session while he logs 8-10. Simulated bot-only matches give every bot a chance to keep up on the
Service Record and give good bots games against weaker players, as he gets. Not built yet; this is what
was agreed in five rounds of questions.

## What was decided

| Question | Answer |
|---|---|
| When matches are simulated | **Alongside each of your Project Reach matches**, plus a **manual button** |
| How many bots play | **Each bot at its own rate**, averaging **a third of your games** |
| Grinders | Any tier can grind, but **Legendary, Blind, Mythic and Demon bots are about 3x as likely** |
| How they show on the site | **Exactly like real matches**: no badge, no separate list |
| What they count toward | **Career totals and K/D, credits and rank, commendations, challenges** |
| Your record | **Never simulated.** People (you, friends who join) are never in a simulated match |
| A bot's skill | **How the brain plays it in real matches** (tier, Blind's per-bot hands, personality), then pulled toward its own measured numbers by each real match |
| Do simulations teach the skill model | **Never.** Only real matches change a bot's skill |
| Detail | **Full match, play-by-play**: medals, sprees, multi-kills and assists come from Reach's rules |
| Playlists | **Same as yours**: Arena and Big Team Battle, `proving_grounds.ini` gametypes, maps and odds, picked by the same bot vote |
| Lobbies | **Random, like yours**: drawn from the bots that are playing, teams balanced the same way |
| Clans | **Same team**, as in your lobbies |
| Bot life (form, fatigue, tilt, hours) | **None for now** |
| In game after your match | **Nothing** |
| Site extras | **Daily Top 5** and **Playlist activity** |
| Button | **Both**: a Project Reach menu row and a Service Record site button. **Asks how many rounds** each time |
| Start | **From now on**; current records stay as they are |

## Defaults chosen in the write-up (not asked; change any)

- **A hidden mark in the ledger.** The site shows simulated matches as real, but the ledger keeps
  `"sim": true` and the match's random seed. The skill model must skip them (the "never" answer), and
  `bot_career.py --reset-bots` / `--reset-all` must cover them too.
- **Which playlist a bot queues for**: each bot has a fixed lean toward Big Team Battle, seeded from its
  name, averaging 35%.
- **Bots left over** after the lobbies are filled wait for the next round.
- **Times**: a round alongside your match is dated inside your match's start and end. A button round
  of k rounds is dated as if played over the last k x 10 minutes (never in the future).
- **Grinder pace**: a grinder's median is 1.5 simulated games per match of yours.

## What a simulated match writes (and so what it counts toward)

No stat is decided one by one. A real match leaves two raw files, and `tools/service_record.py` works
out every number on the site from them. A simulated match writes the same two files in the same format,
and the same code does the rest:

| Raw file | What it holds | What the site works out from it |
|---|---|---|
| MCC's carnage report | Each player's team, place, score, kills, deaths, assists, betrayals, suicides, best spree, time alive and played, finished or not, kills by weapon, grenade, melee and other, medals by MCC id, who they killed most and were killed by most. The gametype, map and teams | K/D and totals, credits and rank, medal commendations, MVP, Game Changer, Positive Thinking, Loyal Soldier, most challenges, the match's scoreboard |
| The kill record (`tools/kill_record.py`) | Every kill and death: victim, killer, damage type and modifier, the last 4 hits, where each stood, the time | Weapons, Enemies and Heatmaps pages, the kill feed, weapon and vehicle commendations, First Strike, Closer and Grudge, weapon challenges |

Each raw fact comes from the first of these that has something:

1. Reach's rules (medal timing, score limits, respawn).
2. The bot's own real matches.
3. Bots of its tier in real matches.
4. That map and gametype in real matches.
5. Otherwise it stays 0. Nothing is made up.

Weapons, for example: `p(w | bot, gametype, map) = (alpha * p_tier,map(w) + n_bot(w)) / (alpha + n_bot)`. Only
weapons seen on that map are used, or the gametype's starting weapons where the map has no record.

## The math

### Each bot's pace (one "round" = one match of yours)

```
grinder?        G_b ~ Bernoulli(p_t),  p_t = 0.30 for Legendary/Blind/Mythic/Demon, 0.10 for the rest
pace            r_b ~ LogNormal: median 1.5 if a grinder, else median m_c
games a round   n_b ~ Poisson(r_b)
the average     (1/899) * sum over bots of r_b = 1/3        -> solve for m_c
```

All of a bot's draws are seeded from its name, so its pace never changes between runs. At 1/3, about 300
bot seats a round. With the 35% lean that is about 24 Arena and 6 Big Team Battle lobbies alongside each
match of yours.

### Skill (real matches only)

```
start      mu_b = mu0(tier, the brain's hand settings for this bot),  sigma_b = sigma0
team       S_A = sum of mu_i over team A
P(A wins)  = Phi( (S_A - S_B) / sqrt(2*n*beta^2 + sum of sigma_i^2) )
update     after each REAL match: mu_i += (sigma_i^2 / c) * (W - P) * v,  sigma_i shrinks
```

### Each bot's own rates, shrunk toward its tier

```
kills per minute   k_b = (alpha_t + K_b) / (beta_t + M_b)
```

K_b is its real kills, M_b its real minutes, beta_t = 30 pretend minutes and alpha_t = the tier's rate
x 30. Deaths, assists and headshots per kill work the same way. Because real matches are all against
you, they get an opponent adjustment:

```
ln k_b(sim) = ln k_b + c * (mu_opponents,real - mu_opponents,sim) / beta
```

### The match engine (play-by-play)

```
meeting rate   lambda_ij = lambda0 * a_i * a_j          (a = aggression from real rates and personality)
next fight     dt ~ Exponential(sum of lambda_ij over live pairs)
duel           P(i kills j) = 1 / (1 + exp(-(mu_i - mu_j) / beta))
respawn        about 5 s out
assist         a teammate m assists with P = q * a_m / sum of a over the team
objectives     captures at rate_A = r0 * exp((S_A - S_B) / gamma), flag-first bots credited 2x
calibration    lambda0 *= real kills per minute / simulated kills per minute
```

Medals follow Reach's rules on the event stream:

- multi-kills: a Double Kill when the next kill lands within 4 s, then Triple and up;
- sprees: Killing Spree at 5 kills without dying, Frenzy at 10, Riot at 15;
- the rest: Killjoy, Revenge, First Strike, and Headshot with the bot's measured share.

The match ends at the gametype's score or time limit.

### Credits (the same values as real matches)

```
cR = 1000 + 1000 * won + 100 * kills + 50 * assists + 25 * medals
```

Plus commendation tier credits and challenge credits, as for real matches.

### Checks before it goes live

- **Spread test:** replay real lineups 1,000 times each. Real K/D should fall inside the simulated 90%
  band about 90% of the time.
- **Win predictions:** Brier score `(1/N) * sum of (P - W)^2`.
- **Kill counts:** per-match kills should vary as much as in real games (variance > mean).
- **Kill totals:** simulated kills per minute should match real lobbies'.

## Speed and size (measured Nov 17, read-only)

| What | Measured |
|---|---|
| A prototype engine, one round (24 Arena + 6 Big Team Battle lobbies, about 300 bots) | **0.03 s**, 2,864 kills |
| The Service Record's computation, 121 matches (today) | 1.8 s |
| ... with 643 / 2,383 matches | 2.9 s / 6.8 s: about **2.2 s more per 1,000 matches** |
| Stored per match | about 4 KB of detail plus about 16 KB of kill rows |
| MCC's own carnage report file | about 155 KB, so a simulated match writes the stored form, not a full report file |

At your pace (about 30 simulated matches per match of yours), a month of 10-match sessions is about
9,000 matches: about 180 MB stored and about 22 s of background build after each match. It all runs
after your match ends, at below-normal priority on one core. The build is already running at that
moment today, so it never competes with a fight.

Rotation maps with no kill record (no weapons or heatmap spots to copy):

- **Arena:** Sword Base, Damnation, Prisoner, Asylum, The Cage and Pinnacle. The 10 Forge World kill
  records are on two other Forge layouts.
- **Big Team Battle:** everything except Boneyard (1 kill record). Breakpoint, Tempest, Highlands,
  Breakneck and Headlong have reports, so K/D can be learned there, but no kill rows.

## Build order

1. **Ratings and rates.** Read the real matches (ledger and reports) and the brain's tier settings,
   then compute mu, sigma and the shrunk rates. Pass the spread test and the Brier check.
2. **Match engine.** Team Slayer first, then CTF, Assault, Oddball, King, Territories and Stockpile.
3. **Population.** Paces, grinders, playlist lean, and the lobby builder: random, clans together,
   teams balanced, the bot vote for map and gametype.
4. **Writing results.** Save each match in the form the Service Record reads from a real report:
   scoreboard, medals, map, gametype. Add it to the ledger and `matchmaking.txt` with the hidden mark.
5. **Triggers.** Project Reach's end-of-match build runs `tools/bot_sim.py` before `bot_career.py`
   and `service_record.py`. Add the menu row and the site button, which ask how many rounds.
6. **Site extras.** Daily Top 5 and Playlist activity.

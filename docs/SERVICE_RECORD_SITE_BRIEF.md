# Brief: a Reach-style Service Record for our bots and us

For: the owner's coding friend (web and game developer), or the AI they hand this to.
From: the owner, written up with Claude on 2026-11-15.

## Goal

Build a stats tracker for the owner, the friends who play with us, and our 15+ bots. It should look and feel like the
old Halo: Reach Service Record pages (the 2010-2012 Bungie.net stats site). It shows everything the mod already
records: career numbers, medals, armor, emblems, ranks and match history. It is for our own use, not a public site.

**Ask the owner every question in "Questions to settle first" below before writing code.** Then build it to
completion, phase by phase, checking each phase against its acceptance criteria.

## Platform: recommended choice

A **local website**: one Python script reads the mod's files and writes a folder of static HTML, CSS and JS, and the
owner opens it in a browser. Why this over a desktop app:

- The repo already ships a Python runtime (`python\python.exe`, 3.14), so there is nothing new to install. Use the
  standard library only, plus Pillow (already in `python\Lib\site-packages`) if images need converting.
- HTML and CSS can match the old page layout far more closely than a desktop UI toolkit can.
- Friends can later get a copy (a zipped folder) or a private host, if the owner chooses. Nothing gets uploaded
  without the owner's explicit OK.

Suggested layout: `tools/service_record.py` builds into `logs/service_record/` (already git-ignored output), with an
`index.html` that works from `file://` (no server needed), or with `python -m http.server` if you need `fetch`.
Optionally, `tools/play.py` can rebuild it in the background after `bot_career.py` runs at match start.

## Reference pictures (the owner has them)

1. **Service Record > Overview**: player banner (emblem, gamertag, service tag, rank insignia and name, a progress
   bar "Next: <rank> (<cR> of <cR needed>)"), a large armor render on the left, a stat list (Last Played, Armory
   Completion, Daily and Weekly Challenges, Matchmaking MP Kills with K/D, MP Medals, Covenant Killed, Player Since),
   a Games Played donut by category, Top Commendations, and a Matchmade Victory Streaks bar chart.
2. **Career Stats > Summary**: category tabs (Invasion, Arena, Competitive, Campaign, Firefight, Custom), a Games
   Played donut, and a stat table (Playtime as `13d 3h 36m`, Kills, Deaths, Assists, Kill/Death, Kills/Game,
   Deaths/Game, Kills/Hour, Deaths/Hour, Medals, Medals/Game, Medals/Hour). Next to it: **Top Medals** (a row of
   medal icons with counts, plus a "view all medals" link) and **Top Weapons** (weapon art with "Kills: N | Deaths:
   N", plus a "view all weapons" link).
3. **The Reach rank chart** (below).

## Pages

Left navigation as on the old site:

- **Service Record**: Overview, Game History, Commendations, Heatmaps, Achievements, Profile.
- **Career Stats**: Summary, By Playlist, By Map, Medals, Weapons, Enemies.
- **Leave out**: File Share, Rendered Videos, File Sets, Recent Screenshots, Top Files.

There is also a **player picker/leaderboard** (the owner, each friend, each bot), sortable by K/D, kills, deaths,
assists and games, like `python\python.exe -I tools\bot_career.py`. Each player opens their own Service Record.

Where we have no data for a stat (Daily Challenges, Covenant Killed, Campaign games), drop it or replace it with
one we do have (Betrayals, Best Killing Spree, Most Kills in a Row). Never show a made-up number.

## Ranks: all the original Reach ranks

The rank is earned by credits (cR) in total. A Grade is a higher step within a rank.

| Rank | cR to reach it (Grade 1, 2, 3, 4 after the base) |
| --- | --- |
| Recruit | 0 |
| Private | 7,500 |
| Corporal | 10,000; Gr1 15,000 |
| Sergeant | 20,000; 26,250; 32,500 |
| Warrant Officer | 45,000; 78,000; 111,000; 144,000 |
| Captain | 210,000; 233,000; 256,000; 279,000 |
| Major | 325,000; 350,000; 375,000; 400,000 |
| Lt. Colonel | 450,000; 480,000; 510,000; 540,000 |
| Commander | 600,000; 650,000; 700,000; 750,000 |
| Colonel | 850,000; 960,000; 1,070,000; 1,180,000 |
| Brigadier | 1,400,000; 1,520,000; 1,640,000; 1,760,000 |
| General | 2,000,000; 2,200,000; 2,350,000; 2,500,000; Gr4 2,650,000 |
| Field Marshal | 3,000,000 |
| Hero | 3,700,000 |
| Legend | 4,600,000 |
| Mythic | 5,650,000 |
| Noble | 7,000,000 |
| Eclipse | 8,500,000 |
| Nova | 11,000,000 |
| Forerunner | 13,000,000 |
| Reclaimer | 16,500,000 |
| Inheritor | 20,000,000 |

Checks against the reference pictures: Colonel Grade 3 to Brigadier is 220,000 cR, and Noble to Eclipse is
1,500,000 cR. Put the table in one data file and test both gaps.

**MCC's reports have no credits.** The cR formula is a design question for the owner (see questions). Whatever is
chosen, it must be a pure function of the recorded stats, so a player's rank can always be rebuilt from the ledger.

## Data we have (read it, don't change it)

All of these live on the owner's PC. Paths are relative to the repo root.

| What | Where | Notes |
| --- | --- | --- |
| Career ledger | `native/bin/career/ledger.json` | `{GameUniqueId: {file, time, players: [{name, bot, team, standing, kills, deaths, assists, seconds}], bots_reset?}}`. Built by `tools/bot_career.py` (read its docstring for the rules). A match counts when the person played 60 s or more. If `bots_reset` is set, that match's bot rows don't count (the owner reset the bots' stats on 2026-11-15). |
| Totals | `native/bin/career/totals.txt` | `name\tgames\twon\tkills\tdeaths\tassists\tbot`, derived from the ledger. |
| Full post-game reports | `logs/trace_<map>_<YYYYMMDD-HHMMSS>.carnage.xml` (MCC's report, one per match) | Per match: game type (`GameTypeName`), `GameEnum` (which Halo), `IsMatchmaking`, `GameUniqueId`. Per player: score, standing, team, kills, deaths, assists, betrayals, suicides, kills by grenade, melee, weapon and other, most kills in a row, most used weapon (a numeric id), seconds played and alive, killed-most and most-killed-by (player index and count), total medal count, `Medal mId mCount` rows, emblem (`EmblemTexture0/1`, `EmblemColor0-2`), clan tag, nameplate. **The recording rotation deletes old traces and their reports**, so copy what you need into your own store. The ledger only keeps the 8 fields above. |
| Map | the trace file name (`trace_reach_forge_halo_...` is Forge World) | Not in the report. Map ids are named in `maps/<id>/`. |
| Bot list, clan tags, hand-set armor | `native/bin/bot_profiles.ini` | `bot=<name>,<look seed>,<clan tag>,<key=value;...>` |
| Every bot's armor as rolled, per game | `native/bin/bot_looks.ini` | `<name>\|<game>\|own/other\|key=value;...`. For Reach: helmet, chest, shoulders, wrist, knees, visor, armor_effect, primary and secondary colors, gender, species. Index-to-name tables: `native/look_names.h` (its header names a generator, `tools/look_names.py`, that is not in the repo, so parse the `.h` itself). |
| Emblems | `native/bin/emblems/<name>.rgba` (+ `.ids`) | Format: uint32 width, uint32 height, then RGBA bytes. See `brain/emblems.py`. |
| MCC rank badges (tours and levels) | `native/bin/ranks/` | MCC's own badges, not Reach's. Reach's insignia aren't extracted yet. |
| 3D armor models | `native/bin/models/*.mdl` | Used by the in-game profile view (`native/model_view.cpp`). A static render is fine for the Overview page. |
| Difficulty, play style, Bot Matchmaking saves | `native/bin/bot_pool_saved.ini`, `brain/profiles.py` | Show a bot's difficulty and play style on its record. |

### Data gaps: decide with the owner, don't fake them

1. **Kills and deaths per weapon (Top Weapons).** MCC's report only has kills by type (weapon, grenade, melee) and a
   numeric "most used weapon". A real per-weapon table needs new recording in the mod. Claude can add a per-kill
   record of killer, victim and weapon to the match trace on request. Until then, the Weapons page shows "not
   recorded yet".
2. **Medal names and icons.** Reports give MCC's medal ids (about 384 across all games) and counts, but no names.
   This needs an id-to-name table for Reach's medals, plus icons extracted from the owner's own MCC install (as
   `tools/mcc_ranks.py` does for the rank badges).
3. **Reach rank insignia and medal and weapon art.** These belong to Microsoft/343. Extract them from the owner's
   MCC install at build time into an ignored folder, or use placeholders. Never commit them (see constraints).
4. **Enemies page.** Reports only name each player's killed-most and most-killed-by opponent (by index). A full
   versus table needs the same per-kill record as item 1.
5. **Heatmaps.** The traces have every bot's position several times a second, and the "world" rows have every
   player's, so kill and death heatmaps are possible from traces only while they exist. They need the per-kill
   record for exact spots, and a top-down map image per map.
6. **Older matches.** For matches whose trace and report were already rotated away, only the ledger's 8 fields
   remain. Show them, with blanks for the rest.

## Constraints

- **No Bungie or Halo branding.** Don't use the Bungie logo, the "bungie.net" header, the Halo logo, or text that
  says it's Bungie's site. Name it something of our own (ask the owner). Match the layout, dark blue palette,
  spacing and the feel of the fonts, using free fonts (Google Fonts) and our own CSS. Don't copy the old site's
  HTML, images or scripts.
- **Game art stays off GitHub.** The repo is public. Rank insignia, medal and weapon icons, emblems, armor renders
  and anything else taken from MCC are generated on the owner's PC into ignored folders (`native/bin/` or
  `logs/`). The same goes for the stats data and other players' gamertags. Only code, CSS and hand-made
  placeholders get committed.
- **Read-only on the mod's data.** Never write to the ledger, the `.ini` files, traces or reports. Keep your own
  derived store (for example `native/bin/service_record/` or `logs/service_record/`).
- **Strangers stay out by default.** The ledger has people from online and friend-join matches. Show the owner,
  the bots, and only the friends the owner lists (see questions).
- **Repo rules (`AGENTS.md`, `docs/CUSTOM_RELEASE_WORKFLOW.md`):**
  - Keep changes small.
  - Describe each change and its validation in `CUSTOM_CHANGELOG.md`.
  - Don't stage the owner's or Claude's unrelated uncommitted work, and diff each file before `git add`.
  - Never force-push.
  - Every push, tag, release or upload needs the owner's explicit approval.
  - Tests are plain scripts, `tools/test_*.py`, run with `python\python.exe` (no pytest).
- **Works offline,** from the folder, and builds in under about 10 seconds for a few hundred matches.

## Questions to settle first (ask the owner)

Each has a suggested default. The owner decides.

1. **Name of the site** (not Bungie's). Suggested: "Proving Grounds Service Record".
2. **Website or desktop app?** Suggested: the local website above.
3. **Who can see it?** Only the owner's PC, a zipped copy for friends, or a private host? Suggested: the owner's PC
   first; sharing later, only on the owner's OK.
4. **Who is listed?** The owner, the bots, and which friends (gamertags)? Suggested: strangers from online matches
   hidden.
5. **Which games count?** The ledger has Reach, Halo 4, Halo 2 and others. Suggested: Reach only on the Reach
   pages, with a game filter for the rest.
6. **Categories for the tabs and the donut.** The old tabs were Invasion, Arena, Competitive, Campaign, Firefight
   and Custom. We play custom games by game type. Suggested tabs: All, Slayer, CTF, Assault, Territories, Stockpile,
   Oddball, King of the Hill, Invasion, Headhunter, Firefight, built from `GameTypeName`.
7. **cR formula for the Reach rank.** Suggested: 1,000 per game completed, +1,000 for a win, 100 per kill, 50 per
   assist, 25 per medal. Tune it so a regular player reaches Colonel or Brigadier after a few hundred games. Should
   bots rank by the same formula, or start from their difficulty (Demon near the top), as the in-game badges do?
8. **Weapons and Enemies pages:** show "not recorded yet" for now, and ask Claude to add the per-kill record? (See
   gap 1.)
9. **Should the bots' stats reset on 2026-11-15 also apply here?** (It already applies to the ledger.)

## Phases and acceptance criteria

**Phase 1: data and Summary.**

1. `python\python.exe -I tools\service_record.py` builds the site with no errors from the real data.
2. The leaderboard's games, wins, kills, deaths and assists for every player equal `totals.txt` exactly. A test
   checks this on a small made-up ledger.
3. Career Summary shows every stat in picture 2 that we have (Playtime as `Nd Nh Nm`, and the per-game and
   per-hour rates rounded to 2 places), with the tabs from question 6.
4. A player with 0 deaths shows K/D equal to their kills, not an error, as `bot_career.py` does.

**Phase 2: Overview, ranks, looks.**

5. The banner shows the emblem, clan tag, name, Reach rank insignia and name, and the "Next: <rank> (<cR> of <cR>)"
   bar.
6. A test checks the rank table's two known gaps (Colonel Gr3 to Brigadier is 220,000; Noble to Eclipse is
   1,500,000), and that 0 cR is Recruit and 20,000,000 is Inheritor.
7. Each bot's Reach armor is listed by piece name (from `look_names.h`), with a picture if one can be made, and its
   difficulty and play style.
8. Game History lists matches newest first: date, map, game type, place, K/D/A. A match opens to its full scoreboard
   from the report.

**Phase 3: Medals, Weapons, Enemies, Heatmaps.**

9. Top Medals shows the 7 most-earned medals with counts, and "view all medals" opens the full grid. If the medal
   table isn't ready, show ids with a placeholder icon.
10. Weapons, Enemies and Heatmaps work from real records, or say clearly that the data isn't recorded yet.

**Always:**

11. Opening `index.html` from the folder works in Chrome and Edge, and works at phone width.
12. `git status` after your commits shows no game art, stats data, gamertag lists or build output staged. All
    `tools/test_*.py` still pass.

## What to report back to the owner

At the end of each phase:

- what's built, with a screenshot;
- the command that builds it;
- the tests run and their output;
- anything shown as "not recorded yet";
- any decision you made that the owner didn't, as a list.

If a file or field named here isn't where this brief says, stop and ask. Don't guess.

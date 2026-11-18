# Challenges: an in-game page

The Service Record site now has daily and weekly challenges. This note is for adding them to the game on a page of their own.

## What exists

- **The list:** `tools/service_record_site/challenges.json` holds 52 dailies and 18 weeklies. Each one has a name, a description, a target (`need`), a reward (`cr`) and a rule for what it counts.
- **Live at once:** 4 dailies, which change at local midnight, and 1 weekly, which changes on Monday. Every player gets the same set.
- **Rank:** a challenge finished before its time runs out adds its cR to the player's rank.
- **The logic:** `tools/service_record.py`, in `challenge_pick`, `challenge_progress` and `challenge_table`. The draws are decided by the date, so every build gives the same result.

## The one rule

Read what the site build writes. Don't copy the list into C++, and don't work out progress or cR in the game. The site and the game have to show the same numbers. This is the same rule that already applies to ranks (`CUSTOMIZATIONS.md`).

## Where the data is

After each build (when a match starts or ends), `logs/service_record/data.js` holds `window.SR_DATA = {...};`:

- **`challenges.daily` and `challenges.weekly`:**
  - `keys`: the live challenges.
  - `ends`: when they end, in Unix seconds, local time.
- **`challenges.list[]`:** each challenge's `key`, `name`, `what`, `need`, `cr`, `icon` and `period`.
- **`players[].chal`:** each player's progress.
  - `now`: progress on the live challenges, as `{key: n}`.
  - `cr`: challenge cR earned.
  - `daily_done` and `weekly_done`: how many completed.

`logs/service_record/ranks.txt` already has the last two columns, dailies and weeklies completed, for the roster card.

If a flat file is easier to read from C++ than JSON, the build can write `challenges.txt` next to `ranks.txt`. Just ask.

## What the page should show

One row per challenge:
- an icon
- the name and what to do
- the time left (`ends` minus now)
- the cR reward
- a progress bar with `n/need`, or "Completed"

Put the weekly challenge first, then the 4 dailies. Add "Daily Challenges Completed: N" and "Weekly Challenges Completed: N".

If the time has run out before the next build, show the old challenges as "Ended".

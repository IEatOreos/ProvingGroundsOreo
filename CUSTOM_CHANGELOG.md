# Custom release history

## Unreleased

### Demon aim turn cap, 2026-11-07

- Lower Demon's general aim turn cap from 1,000 to 480 degrees per second in `brain/profiles.py` for all personalities, including Warthog gunner aim. Reach Scorpion drivers still use the dedicated 90-degree-per-second cap. Protected final DMR and sniper head-shot corrections still apply on the firing tick.
- All 140 regression tests passed. The profile test checks the new cap and compares the other numeric settings with the prior profile. A focused check confirmed the general and Scorpion turn limits for Demon and Legendary across all personalities. Gameplay testing is pending the next bot-process launch.

### Demon fight commitment, 2026-11-07

- From the owner's Settlement 3v3v3v3 (logs/trace_reach_30_settlement_20261107-041239, owner 35-15 against a three-Demon team): the owner won 58% of his fights (an enemy in his sights for 0.5 s or more) and broke off 27%. The Demons won 34–42% and broke off 40–48%, with the same 1.1–1.3 s time to kill. Of the Demons' break-offs, about a third switched to another enemy, about a third were the target leaving sight briefly or the aim moving to another man, and 13–23% went to cover with the target still in view.
- `Bot.demon_commit` (Demon only, from `pick_target`):
  - A target that left sight stays the target for 0.8 seconds, or 1.6 seconds when its estimated shield is at or below half, and Demon chases it through the existing chase and corner logic.
  - A visible target is kept for 2 seconds after it is taken on. After that, a new enemy must pose 2x its threat (rising as the kill nears) to take over, against 1.25x for the other tiers.
  - Demon still turns at once on the enemy shooting it now (`shot_by_other`), an enemy at arm's length, or an enemy within 10 units aiming at it while the current target is looking away. A kill about to land (`finishing`) still goes first.
- Mending after a won fight waits while an enemy is in view and Demon's shield is at least 0.5: it fights first, and the mend stays owed until no enemy is in view or the shield drops below half. Mending still takes priority when cracked.
- Legendary and the other tiers keep their targeting rules.
- Validation: 6 new tests in tools/test_demon_anticipate.py. The full suite (140 tests) and the compile check (94 sources) pass. This install has no match simulator, so gameplay is the test; the bot process must be restarted.

### Infantry patrol trios, 2026-11-07

- In `brain/director.py`, roll once per new infantry patrol. Half of assignments send one Spartan and half try to send up to three to the same waypoint. If fewer than three qualify, send the eligible Spartans. Applies to maps with infantry patrols, including Boneyard and Headlong, outside Invasion.
- All 134 regression tests passed. A focused director check covered both outcomes, the three-bot cap, smaller groups when eligibility is limited, and independent arrivals. Gameplay testing is pending a bot-process restart.

### Headlong Red side ramp, lifts, man cannon and the ledge power position, 2026-11-07

- Owner report 3's ledge (-10.01, -9.37, 10.36), the east end of the Red side sniper floor over Mid, was reachable only from that floor's own spawns. In the 03:23 match the owner walked a ramp from the middle level (z 7.6) up to it; the level data's 0.1 u height steps read as 0.2 u rises per 0.25 u nav cell, over MAX_RISE 0.18, so the ramp had no link. New maps/reach_cex_headlong/moves_review.json (the existing reviewed-floor mechanism) approves that walk as floor at the owner's recorded foot heights every 0.1 u. Walking alone, the ledge is now reachable from 582 of 584 spawns. Ramp cells shifted up 0.1–0.2 to the walked heights, and no power position or patrol spot lost reach.
- The owner's LiDAR session (variant reach_cex_headlong@v2e9a3603) recorded his rides on the two air lifts and the man cannon, which lands on the same sniper floor. His three bug reports from that session point at these. Normal Headlong matches load the base map, so the three rides were copied into the base map's local, gitignored maps/reach_cex_headlong/lidar.json. A backup of that file is in logs/. With the rides, the ledge is reachable from all 584 spawns, and each lift top and the cannon landing is reachable from below. Bots that jump at all (everyone but Easy) plan with people's rides. The lidar.json change is local data and is not committed.
- The ledge is added as an owner power position (score 1.0, 6.5 u above its surroundings, duck cover) with `power_positions.py --add`.
- Validation: reachability checks above; all 134 regression tests pass. Gameplay is untested; the bot process must be restarted.

### Headlong patrol areas and owner power positions from bug reports, 2026-11-07

- The owner's six F9 reports from the Headlong 8v8 (logs/bug_reports/reach_cex_headlong_20261107-032305) mark spots where the owner stood. New maps/reach_cex_headlong/infantry_patrols.json lists the four patrol requests (reports 1, 4, 5 and 6: north spawn, southwest lower level, west spawn, man cannon), shared by both teams. Patrol orders, timers and the Invasion exclusion are the existing rules.
- Power positions: reports 2 (13.55, 17.84) and 6 (man cannon, 7.92, -2.7) are added to Headlong's positions.json with `owner: true` and score 1.0, above every computed spot, so the Slayer anchor's weighted post pick favors them. Report 3, the ledge at (-10.01, -9.37, 10.36), is not added: the level's nav reaches it only from the 3 spawns on that ledge (none of the other 37 tested), even with jump links, so an anchor sent there would stall. It waits on the owner describing the way up.
- tools/power_positions.py gains `--add X,Y,Z` (one map) to write an owner-marked row, measured like the computed spots (sightlines, height, duck spot). A later full regeneration keeps owner rows and drops computed spots within half the spacing of them.
- Validation: the map loads 4 patrol points and 10 positions with the owner's first. The patrol points (reports 1, 4, 5, 6) and the two power positions are reachable from all 40 tested slayer spawns. The owner-row merge was checked. All 134 regression tests pass, and the compile check passes. Gameplay is untested; the bot process must be restarted.

### Demon 180-degree horizontal vision, 2026-11-07

- Widen Demon's visual detection from 140 to 180 degrees (90 degrees to either side) in `brain/bot.py`. The entire cone uses Demon's zero configured recognition delay. The ordinary sight range, line-of-sight checks and other difficulties retain their existing rules.
- Validation: updated `tools/test_demon_awareness.py` to check both edges of the wider cone, including zero delay inside and no visual detection just outside. All 134 regression tests passed across the suite and the localhost-only rerun. Syntax and whitespace checks passed. Live gameplay is untested; the change takes effect on the next bot-process launch.

### Demon mends in cover after winning a fight, 2026-11-07

- Owner's request: once Demon wins a fight with any shield or health lost, it goes to cover until both are back. A win means the target died within one second of Demon's last shot. Demon uses painted cover from the remaining known threats (or from the kill spot when none are known). Without painted cover, it searches up to 10 units for the nearest walkable spot, a short walk away, that no threat can see. At the spot it crouches, which keeps it off the enemy's motion tracker, and watches out of cover.
- Mending (score 2.9; 3.1 while already under way) outranks objectives, weapon pickups, hunts and a newly visible enemy at range; Demon fires back while moving. It still loses to an enemy within the close-fight range, a hit from an unseen shooter, and a tracker dot at arm's length. A teammate on a loose objective (`stay_on`) and the flag-grab reduction keep their rules. Demon stops mending when its shield is full and its health is full or has stopped refilling for 1.5 seconds (Reach health refills only partially), when the enemy carries our flag or objective, or after 15 seconds at most. A new hiding spot is chosen if a visible enemy can see the current one. Excluded: carriers, vehicles, matches without shields and Race. Other tiers are unchanged.
- Validation: 4 new tests (won-fight mend and end, stalled health, no mend at full or for Legendary, the cap). The full suite (134 tests) and the compile check pass. On Forge World, a hiding spot was found for 35 of 40 random positions, in under 1 ms (median) and at most 18 ms, once per kill. Gameplay is untested; the bot process must be restarted.

### Demon corner follow-up from the first live match, 2026-11-07

- Owner's Reach Forge World 1v1 Slayer against one Demon (logs/trace_reach_forge_halo_20261107-022003.jsonl). Of 28 breaks of line of sight during fights, Demon held 4 (2 continued to a swing and then a push) and pushed 24, mostly targets 10 or more units away or cracked targets. Its 291 hunt destinations were within 0.5 units of the owner's true position, because they came from live tracker dots.
- **Shield recharge estimate.** Demon judges a target's shield by its value when last seen plus the recharge since. Demon learns this match's recharge delay and rate from its own shield (defaults 2.0 seconds and 0.5 shield per second, measured in that match), and a hit seen on the target restarts his clock. A target pushed while cracked becomes a hold once his estimated shield is back. Fixes the push at 480 seconds, which was triggered by a half-shield sighting although the shield was full one second later.
- **Close-corner fallback.** When no reappearance spot is found (Demon is already at the corner), it holds back from its estimate of the target's position instead of pushing. This was the likely cause of the push at 484 seconds against a full-shield target 4.5 units away.
- **Ledge hold.** If the target is at least 1 unit higher with no short walkable way up, Demon holds whatever the target's shield, then resumes the chase via the nav without a swing. Fixes the 3-second strafe into a platform wall below the owner (1.9 units up) at 480–483 seconds.
- Recharge retreats were checked in the same match: Demon left cover at 0.94–0.95 shield, as designed (the 95% threshold). Shields began refilling 2.0 seconds after the last hit and filled from empty in 1.9 seconds, so a recharge retreat lasted about 3–4 seconds. Some retreat goals at full shields while the owner was dead have an unidentified cause, because the trace does not record decision scores. Unchanged.
- Validation: 5 new tests in tools/test_demon_anticipate.py (19 in total). The full suite (130 tests) and the compile check (94 sources) pass. Gameplay is untested; the bot process must be restarted.

### Demon radar reads, out-of-sight prediction and corner discipline, 2026-11-07

- **Radar reads (Demon only).** Demon now works out which way each motion-tracker dot is moving by comparing its successive positions. A dot older than 0.5 seconds starts a new heading. Unsuppressed fire puts the shooter on Demon's tracker even when crouched or standing still, within the existing tracker range, the tracker setting and jamming. A crouch-walking enemy who isn't firing stays off the tracker. Other tiers keep heading-less dots and the existing radar and heard-gunfire rules.
- **Out-of-sight prediction (Demon only).** The new `brain/anticipate.py` estimates where an unseen enemy has reached since his last trace. Candidates are: continuing along his last heading on the walkable path, nearby painted cover hidden from the bot, or staying put. A tracker dot that disappears more than 3 units inside tracker range is read as the enemy crouching or stopping, so the guess stays near the last dot. The prediction uses only the last trace, its heading and the map, never the live position. It feeds Demon's main hunt destination and its out-of-sight pre-aim (`man_appears`). Damage-direction hunts, other tiers and Demon's fight aim are unchanged, including the protected head corrections. Only h2_warlock and h2a_ca_ascension currently have painted cover; on other maps, prediction uses heading and staying put only.
- **Corner discipline (Demon only).** When a fight target breaks line of sight within 10 units with more than half his shields when last seen, Demon no longer chases him round the corner. It holds a standoff at least 5 units from where he would reappear for a random 1.2–2.8 seconds. It then swings wide, offset 3.5 units to the side of the corner, for up to 2 seconds before resuming the chase. The existing flush-grenade roll still applies. Demon pushes immediately when the target was cracked, carries the flag or objective, is fleeing on the tracker, is out of range of the rule, or when Demon holds a sword or hammer or is in a vehicle. CTF defender holds and the sniper lane-hold keep their previous rules.
- Validation: tools/test_demon_anticipate.py adds 14 tests (radar heading, crouched shooters, prediction cases, Demon-only gating, hold/swing/push choices, backing off, varied hold length). The full regression suite (125 tests) and the compile check (94 sources) pass. On real map data (Breakpoint, Warlock, Ascension), a prediction takes about 2 ms (median), at most 7 ms, and is cached for 0.4 seconds per trace. Gameplay is untested; the bot process must be restarted.

## 0.2.2-custom.6 — Reach vehicle aim and Boneyard patrols, 2026-11-07

- Correct the Reach Warthog chaingun’s horizontal firing origin. For fixed Legendary and Demon, limit Scorpion turret turns to 90 degrees per second, require aim to settle before firing, and aim the main cannon at infantry chests.
- Add two shared Boneyard infantry patrol spots and one per team outside Invasion. A new patrol has a 50% chance to request a second eligible bot. Bots can return fire at distant visible enemies while continuing toward their waypoint.
- All 111 regression tests passed. The owner confirmed the Warthog aim and Scorpion turn changes in gameplay and reported that chest aim appeared to fix shots at infantry feet. The cannon settling check and Boneyard patrols were verified offline.

### Boneyard team patrol spots, 2026-11-07

- Add the two reported infantry patrol waypoints, one for Red and one for Blue. Restrictions follow team color, including when spawn sides swap. The original two Boneyard patrol spots are available to both teams. Patrols apply outside Invasion.
- Verified routes from nearby spawns on the reported Boneyard variant. Offline checks confirmed each team selects only its own restricted spot and that the restriction follows color when sides swap. All 41 selected regression tests passed. Live testing requires a bot process restart.

### Boneyard patrol return fire, 2026-11-07

- Patrollers use normal aiming, weapon selection, and firing checks against visible enemies while walking toward their waypoint. Taking a hit from range can leave the patrol active when a target is visible. Close threats, incoming fire with no visible target, and retreats can still interrupt the trip.
- Offline checks confirmed a bot could take a hit, fire at a distant target, and keep its movement pointed toward the patrol waypoint. Also checked close threats and unseen incoming fire. All 50 selected regression tests passed. Live testing requires a bot process restart.

### Boneyard patrol pairs and combat interruptions, 2026-11-07

- Roll once per new team patrol on Boneyard. Half of assignments request a second eligible bot for the same destination. Each patroller can finish independently, so the first arrival does not cancel the second bot's trip.
- Give each assignment up to 40 seconds. Patrollers favor moving past enemies they see at 18 world units or farther, with normal combat priority when an enemy is closer, they are hit, or they need to retreat.
- Offline checks covered both group sizes, the single-bot fallback, independent arrivals, distant and nearby contacts, recent damage, and Invasion exclusion. All 41 selected regression tests passed. Live gameplay is pending a bot process restart.

### Boneyard infantry patrols, 2026-11-07

- Add the reported Banshee Building and west upper level positions as infantry patrol destinations on Boneyard outside Invasion. One available bot per team can visit a reachable spot that teammates have not visited recently. Combat, retreat, and dedicated team assignments take priority. Patrols end on arrival or after 25 seconds.
- Verified walking routes from nearby spawns on the reported Boneyard variant and checked patrol selection, rotation, reassignment to defense, and Invasion exclusion offline. All 41 selected regression tests passed. Live gameplay testing is pending a bot process restart.

### Reach Scorpion chest aim, 2026-11-07

- Fixed Legendary and Demon Scorpion drivers aim the main cannon at the chest of standing and crouched infantry instead of applying the normal splash weapon aim at the feet. Vehicle targets, other weapons, and Scaling keep their existing aim. The Scorpion's turn cap and firing alignment checks still apply.
- Offline driver checks confirmed both chest heights and the existing aim for vehicle targets, Scaling and the Wraith. All 42 selected regression tests passed. The owner tested the change in gameplay and reported that it appeared to fix the Scorpion aiming at infantry feet.

### Reach Warthog gunner alignment and Scorpion turning, 2026-11-07

- Aim the Reach Warthog chaingun from the attached turret's horizontal position, rotated into map coordinates, with the existing calibrated firing height. Keep the chassis position for navigation and perception. Fall back to the existing origin when attachment data is unavailable or invalid.
- Boneyard's second report requested the owner's Scorpion turning speed for Legendary and Demon. Cap Reach's fixed Legendary and Demon Scorpion drivers at 90 degrees per second, based on the recorded sustained yaw rate (90.3 degrees per second at the 90th percentile of moving samples). Require 0.10 seconds of continuous aim alignment before requesting cannon fire, including at close range. The game reader does not expose the live barrel direction, so this is a settling check on view readback and aim commands.
- Offline driver checks confirmed the turn cap, firing after settling, resetting when the target moves out of alignment, and Scaling exclusion. Attachment transform and fallback checks passed, and all 92 Python source files compiled. The suite passed 110 of 111 tests; the sandbox denied the LiDAR localhost connection in the remaining test.
- The owner confirmed in gameplay that the Warthog aim correction and Scorpion turning sensitivity worked. The confirmation did not separately measure cannon timing.

## 0.2.2-custom.5 — Mongoose transport source update, 2026-11-06

- Publish the owner's approved five Mongoose fixes from 1b59ccd. Ordinary Mongoose becomes transport-only, with finite destinations, cancellation of empty/invalid jobs, bounded carrier/getaway waits, automatic ride cooldown, and retained evasions/recovery/forward splatters. Chosen defaults and full validation are recorded in the implementation entry below.
- Include the main-AI review handoff from 4c0fc95 and add a post-baseline Mongoose follow-up note so its 0.2.2-custom.4 review baseline remains explicit. All prior collaborator and owner commits retain their identities.
- Validation: 111 regression tests passed and 92 Python sources compiled for the implementation, followed by passing targeted checks after final cleanup. Release preparation changes documentation/version only; whitespace checks pass. Gameplay still needs a bot-process restart and live confirmation.
- The owner requested this normal source push to IEatOreos/ProvingGroundsOreo main. Machine settings, learned maps, fixtures, logs and installed binaries remain local. No installer, tag or GitHub Release is included.

## Unreleased — Finite Mongoose transport trips, 2026-11-06

- Apply the owner's five approved Mongoose changes. Remove ordinary Mongoose from the harasser role, require a useful distant destination for director-assigned transport, preserve the destination when assigning a driver, and exclude Mongoose from persistent crew-patrol arrival behavior. Completed trips request dismount and continue on foot.
- Give ordinary Mongoose drivers explicit finite taxi, carrier-pickup and CTF-getaway jobs. Remember the carrier across role passes, stop for boarding, carry a boarded carrier home, and cancel invalid/dead/dropped/carried-away targets. Keep only one getaway vehicle per team. Reassess getaway objective changes and carrier death.
- Chosen defaults: 8 seconds waiting beside a carrier, 20 seconds parked for a getaway, 30 seconds of automatic ride cooldown after dismount, and a travel deadline of max(60 seconds, initial straight-line distance / 3 + 30 seconds). Reassigned moving destinations cannot restart that deadline. Race checkpoints remain the continuous riding case.
- Keep emergency evasions, reversing/stuck recovery and opportunistic splatters. Ordinary Mongoose taxi trips can splatter eligible infantry within 18 units and 20 degrees ahead rather than detouring into a chase. Shared vehicle logic keeps its existing behavior for other chassis, including armed Gungoose and Warthog crew patrols. Use the existing per-game exit hold/retry mechanism and add Mongoose completion reasons to bot notes.
- Files: brain/vehicles.py, brain/director.py, brain/bot.py, tools/test_mongoose_transport.py and current customization notes. No native rebuild is needed. This changes ordinary Mongoose behavior across supported games through the shared brain.
- Validation: all 111 regression tests pass, including 16 new tests through real director/driver entry points covering arrival, no-purpose dismount, cooldown, finite moving-target deadlines, pickup/home delivery, wait cancellation, getaway approach, race, splatters, evasion, reversing, and Warthog patrol preservation. All 92 Python sources compile in memory and whitespace checks pass. The existing LiDAR localhost endpoint test requires socket access and passed on the full run. Gameplay remains untested; restart the bot process/launcher to apply.

## Local documentation — main AI review handoff, 2026-11-06

- Add docs/AI_REVIEW_HANDOFF_2026-11-06.md describing the combined published code through 9a4cf17 / 0.2.2-custom.4. Organize by Reach, Halo 4, other game scope, brain/difficulty, weapons/ammo, equipment/maps, director/vehicles, LiDAR, native menu/reporting, and upstream integration.
- Include the complete 27-commit ledger, current values and superseded settings, file/function/test map, repository access and runtime setup, test command, release validation evidence, and unresolved proposals. Distinguish retained upstream behavior, custom changes, owner confirmation, offline checks, and unverified gameplay.
- Validation: all listed commits match the published history, linked local references and named source/test files exist, and the embedded Python test snippet compiles. Documentation only. This handoff is prepared locally for the owner to share.

## 0.2.2-custom.4 — source update, 2026-11-06

- Publish the approved recent bot updates: independent Demon difficulty and restored Legendary attributes with protected head/turret precision (6a31238); Legendary zero overshoot, Demon 140-degree zero-edge-delay vision and deterministic eligible radar, and resource-call priorities (f022024, bfbb62d). Power calls rank Demon → Legendary → Heroic/Scaling → Normal; gunner calls tie Legendary/Heroic/Scaling, and reserve Demon's power jobs before new gunner assignments.
- Include teammate-coordination workflow documentation (dde7dcc) and the collaborator's LiDAR vehicle-path recording/view support (a57893f), both approved for this combined push. Preserve all existing commit identities. The fetched GitHub main is an ancestor; no incoming merge is needed. Machine settings, learned-map data and fixtures remain excluded.
- Validation: all 95 tests pass with local fixtures; the isolated committed-source snapshot passes 92 with 3 fixture-dependent skips. All 91 brain/tools Python sources and the LiDAR viewer JavaScript pass syntax checks; Git whitespace checks pass. Gameplay remains untested for these changes; restart the bot process/launcher to apply. No new Warthog missed-shot fix is claimed.
- Owner explicitly approved pushing both the bot changes and the collaborator's LiDAR feature to main in IEatOreos/ProvingGroundsOreo. No binary, installer, tag, or GitHub Release is included; upstream VERSION remains unchanged.

## Unreleased — LiDAR mode records vehicle drives and shows them in the 3D view, 2026-11-06

- The owner asked to record driving paths in LiDAR mode instead of painting them; items 1 and 2 of the plan (record in LiDAR mode; show drives in the LiDAR viewer/simulator). Item 3, a Paint-page eraser and vehicle-size tags for recorded drives, is deferred.
- tools/lidar.py main (LiDAR matches) now runs the existing RideWatch each tick, as normal bot matches already did. Every vehicle a person or bot drives or flies is merged into maps/<map>/rides.json at the one-minute LiDAR save and at match end. The bots' vehicle ground, people's "road" preference and aircraft heights (brain/maps.py rides_layers, Terrain._build_vnav) use it from the next match. Recording and saving errors are logged and never stop the mapping. The in-game LiDAR notice now mentions drives.
- RideWatch keeps a live feed of its samples (person drive / bots-only drive / flown air; up to 300,000, oldest dropped). Hub.live sends new samples after the page's `rsince`; rides_view gives every view (live match, LiDAR Viewer, LiDAR Simulator, other maps) the stored drives, using the same thresholds as the nav: a person once, bots twice. Flown air is drawn at its mean flown height.
- tools/lidar_view.html: new "Vehicle drives" layer (key V) with legend rows. Person drives are mint, bot-only drives faint mint, flights light blue. A "Vehicle drives: people / bots" stat; a driven but unscanned map still frames its drives.
- Validation: tools/test_lidar_drives.py (8 tests: person/bot feed and save thresholds, flight heights, feed trimming, riderless/dead/unknown vehicles, bad files, Hub feed only with a watch, the /live rsince endpoint including a 400 on bad input, page wiring). The LiDAR self-check and all other test suites pass. Browser check: the stored Park view drew the 459 recorded person-drive cells and the V toggle hid them and their legend; a stand-in live server driving a fake Warthog streamed new samples onto the page every poll. Not yet tried in a real LiDAR match.

## Unreleased — Clarified gunner weights and Demon resource precedence, 2026-11-06

- Apply the owner's clarification: power calls rank Demon → Legendary → Heroic/Scaling → Normal; gunner calls rank Demon → Legendary/Heroic/Scaling → Normal. Equal-weight candidates use distance; Easy retains its existing eligibility rules.
- Reserve power-weapon fetches after objective roles but before vehicle orders; select vehicle crews before honked/direct/aboard gunner calls. Exclude a Demon with a weapon fetch or driver job from new gunner and gunner-pickup calls; exclude a fetching Demon from new crew assignments. Protect every tier's assigned driver from subsequent gunner calls. Keep existing range, urgency, eligibility and radar restrictions. Demon can still take a gunner seat when no eligible power job was assigned.
- Files: brain/profiles.py, brain/director.py, resource-call/fetch regression tests and customization notes. The owner confirmed the prior deterministic eligible Demon radar behavior; no further radar or aiming change.
- Validation: all 87 tests pass, including real role-pass weapon/gunner contention, vehicle/honk contention, all four gunner-call exclusions, and tied Legendary/Heroic/Scaling weights. All 90 brain/tools Python sources compile in memory and Git whitespace checks pass. Gameplay is untested; restart the bot process/launcher. Local source only; no GitHub push or native rebuild.

## Unreleased — Demon awareness and resource-call priority, 2026-11-06

- Set fixed Legendary flick overshoot to exactly zero after profile variation. Keep other restored attributes, protected head/turret precision, lower tiers and Scaling unchanged.
- Expand Demon to a 140-degree horizontal vision cone, with no peripheral recognition penalty and its existing zero configured reaction delay. Always notice eligible motion-tracker contacts, preserving tracker settings/range, movement, crouching and jamming checks. Ordinary awareness probability remains for other difficulties.
- Prioritize new calls Demon → Legendary → Heroic → Normal → Scaling, then existing Easy eligibility, with same-tier distance ties. Apply to power-weapon fetches, power-vehicle drivers (existing taxi_ok classification), direct/aboard/honked gunner calls and driver gunner pickups. Preserve existing commitments and ordinary transport/passenger/ferry selection. Filter ranges before ranking; eligible objective bots retain their 15-unit power-vehicle limit and compete with idle drivers.
- Owner was asked about gunner inclusion, eligible radar certainty, and Scaling/Easy placement. The stated defaults above were used pending clarification. No native changes, automatic restart or GitHub upload.
- Validation: 82 regression tests pass, including actual power-weapon/vehicle/gunner selection, fallbacks, existing commitments, transport preservation, Demon vision boundaries and 120 radar eligibility scenarios. Source syntax and Git whitespace checks pass. Gameplay remains untested; restart the bot process/launcher to apply.

## Unreleased — Separate Demon from Legendary attributes, 2026-11-06

- Make Demon a distinct brain tier (`tier="demon"`, extra None), retaining the prior tuned Legendary numeric profile exactly across tested personalities/seeds. Add independent Demon entries to tier/turn/craft/reaction/callout/headshot/dry-shot/ramming/escort tables and extend fixed-tier checks, vehicle/head aiming, landing grenade tactics, resource fetching and CLI difficulty mapping. Preserve the collaborator's native menu keys, local build and display/report support.
- Restore Legendary's base profile to the installed author's defaults: reaction 0.154 s, decisions 0.10 s, tracking 0.08 s, lag 0.045 s, aim error 0.006 rad, overshoot 0.30, lead 0.8, flick 0.7 and turn 1000 deg/s, with the original variation. Demon retains 0 reaction, 0.01 s decisions without jitter and the former precise aim parameters. Scaling and lower-tier profiles remain unchanged.
- Preserve Legendary live head tracking and final DMR/sniper head corrections, plus its precise vehicle/head-directed aim via an explicit protected context. Active aim parameters also govern the firing-alignment test; switching from ordinary aiming clears stale error samples. Reaction/decision attributes are restored globally; the protected exception preserves aiming accuracy, not zero-delay target recognition.
- Keep the existing 120-degree vision, 80-unit fetch allowance, tactical grenade policy, head/chest selection, sniper percentage exceptions and Armor Lock rules for fixed Legendary and Demon. Mixed keeps its existing standard difficulty composition. Campaign/Firefight escort code recognizes Demon explicitly while retaining its prior escort parameters. No native source/binary changes, automatic restart or GitHub push.
- Validation: 69 regression tests, 88 source syntax checks and whitespace checks pass. Numeric golden profiles match the author for Legendary and the pre-split custom profile for Demon. An additional 4,480 simulated aim steps matched pre-change output and RNG state for Demon, lower tiers, Scaling and protected Legendary. Existing Halo 4/Reach, sniper, fetch, Armor Lock and migration checks remain passing. Gameplay is untested; restart the bot process to apply.

## Local workflow — review teammate work before publishing, 2026-11-06

- Record the owner's requirement to inspect both local teammate changes and fetched GitHub history before every push. Review all outgoing commits and the combined scope; additional unpublished teammate features need approval when outside the requested upload.
- Recheck concurrent work and publish only the reviewed commit. Preserve in-progress files and all existing commit identities. Documentation only; no gameplay change or GitHub upload.

## Unreleased — Demon native build confirmed in game, 2026-11-06

- Documentation only; no code change. After 0.2.2-custom.3, the owner's machine received Visual Studio Build Tools 2022 (C++ workload). `native\build.bat demon` compiled the published source (through 5620698) into native/bin/botcore_demon.dll without errors. The only warnings were existing _wfopen deprecations in unchanged lines. The tools/panel_art.py step after the build failed because PATH Python lacks PIL; the DLL is unaffected.
- The owner restarted MCC through the launcher and confirmed in game that the Demon difficulty works. The rebuilt DLL stays local and is not uploaded. The 0.2.2-custom.3 and Demon entries below that say "not compiled" or "untested" describe the state when they were written.

## 0.2.2-custom.3 — source update, 2026-11-06

- Publish the six-unit sword/Gravity Hammer Armor Lock activation change (5620698), retaining the preceding Demon difficulty commit (23e1149) without rewriting either commit. Low shields/recent damage alone no longer trigger Armor Lock; other triggers and existing restrictions remain.
- This normal main-branch source push includes the pending Demon implementation. Its native BOTS menu changes are source-only: no rebuilt DLL or installer is included, and the native code has not been compiled here. See the implementation entry below for the existing saved-difficulty compatibility limitation.
- Validation: all 60 Python regression tests passed with a workspace-local temporary directory; all 87 Python sources compiled in memory; whitespace checks passed. Gameplay remains untested. The owner requested this push. No tag, GitHub Release, binary, personal setting, recording or learned-map upload is included.
- The earlier Unreleased headings describe the state when each feature was implemented; those entries are retained for detailed behavior and validation history.

## Unreleased — Armor Lock melee-weapon proximity trigger, 2026-11-06

- Replace both low-shields/recent-damage Armor Lock branches (the nearby-enemy rule and Normal's no-cover fallback) with activation when a visible enemy carrying a sword or Gravity Hammer is within 6 world units, inclusive. This new trigger does not require low shields, recent damage, enemy facing or lack of cover.
- Preserve grenade, explosive-aim, vehicle, existing lunge and objective-hold triggers; retain current energy/input/cooldown gates, Easy's ability restriction, Infection survivor exclusion and hold/release behavior. Other abilities' low-shield rules are unchanged. Demon inherits the rule through its existing Legendary alias; preserve commit 23e1149 and its behavior.
- Validation: all 60 regression tests passed and all 87 current Python sources compiled in memory. Five new Armor Lock tests cover full-shield sword/hammer activation across Normal/Heroic/Legendary/Demon, exact range and visibility, removal of low-shield-only activation, restrictions, and retained explosive/objective triggers. The first full run hit a sandbox temporary-directory permission error in the existing Demon test; rerunning with a workspace-local temporary directory passed without modifying that test.
- Restart the bot process to apply. Gameplay is untested. No GitHub upload or native rebuild is included.

## Unreleased — Demon difficulty (fixed Legendary renamed), 2026-11-06

- Add a Demon difficulty, an exact copy of fixed Legendary under its own name, as the owner asked. brain/profiles.make_profile("demon") builds the "top" profile with the same random draws and sets only Profile.label = "demon"; tier stays "top" and extra None, so every `tier == "top" and extra is None` rule (precision, zero reaction, 10 ms decisions, 120-degree vision, live DMR/sniper head corrections, grenade policy, 80-unit power fetch) applies unchanged. Any later Legendary change also changes Demon.
- Native BOTS panel: tier 5 / key "demon" (HB_TIER_DEMON), "for everyone" difficulty 6 (botcore.ini difficulty=, shared.h). Quick setup and the footer show Easy, Normal, Heroic, Legendary, Demon, Mixed, Scaling (Scaling stays last for its hover box). The selected-bot inspector shows Demon beside Scaling on the second row because five ranks don't fit its width. Demon uses a crimson colour and five chevrons; the lobby tile names it. botcore launches play.py with --tier demon. Existing saved lists and difficulties 0-5 load unchanged.
- Python: botctl accepts "demon" on the BOTS list; the trace meta line, Observer, player stats and match export show "Demon"; the escort brain plays it as Legendary; the guide lists it.
- Validation: tools/test_demon_difficulty.py (5 tests: Demon equals fixed Legendary for every play style and seed apart from label, trace label, BOTS-list parsing, native tier/difficulty tables agree with the Python keys). Existing sniper, power-fetch, migration, Halo 4 head and Breakpoint suites pass; edited Python compiles. No C++ compiler is installed on this machine, so native/botcore.dll is NOT rebuilt or compiled: the menu change needs `native\build.bat` on a machine with Visual Studio C++ build tools, then an MCC restart. Gameplay is untested. A DLL older than this change reads a "demon" bot as Legendary, but reads a saved difficulty=6 as Easy.

## 0.2.2-custom.2 — Halo 4 animated-head aiming, 2026-11-06

- Add a Halo 4-only reader for the captured 120-node Spartan target_head marker (node 54, descriptor +0x1BC) and cached unit view point (+0xD50). Validate layout, alignment, complete reads, finite/orthonormal/right-handed transforms, scale and world-space proximity; publish both endpoints or neither.
- Carry view_pos through the live snapshot without changing the shared generic eye() function. Head-directed tracking and final Legendary DMR/sniper shot corrections use the matched Halo 4 view/head pair. Percentage sniper shots use the same pair while retaining existing thresholds and retry outcomes. Movement direction is preserved during final corrections.
- Head perception and firing use the same world-space endpoints with the existing terrain/material/barrier rules. Chest aiming is unchanged. Unsupported models or partial pairs retain legacy aiming; Reach's animated-head reader and H2A behavior are preserved. No reaction, decision interval, weapon cadence, damage or accuracy-roll thresholds changed.
- Evidence: two read-only Halo 4 captures, 1,154 human calibration poses and 1,626 human/bot poses; all 2,780 raw poses passed reader replay. The source's .62/.38 offsets were not applied as a standalone height subtraction because the shooter reference also differs. The captured view point is a view-origin correction, not independent proof of every physical bullet spawn.
- Validation: all 50 regression tests passed, all 85 Python sources compiled in memory, and whitespace checks passed. Ten new checks cover stance decoding, corrupt/unsupported data, matched-origin aiming, movement preservation, sniper outcomes, Reach/partial-pair fallback, occlusion, perception and player-reader wiring. The existing placed.py ResourceWarning remains. MCC was closed before implementation, so post-fix gameplay is untested; restart Proving Grounds and test a fresh Halo 4 match.
- The owner authorized this source push, including the dependency on the previously local 0.2.2-s181 import/custom migration (6433bb3, ca7eeb0). Preserve all prior collaborator commits. No tagged GitHub Release, installer, raw game capture, user settings, learned map export or binary upload is included.

## 0.2.2-custom.1 — local upstream migration, 2026-11-06

- Migrate to the author's installed 0.2.2-s181 source and native binaries. Archive the newly installed source locally before editing, record that installed source separately in Git, and merge individual custom methods/blocks rather than restoring old full files. All prior custom and collaborator commit identities remain ancestors.
- Retain new upstream Firefight match shutdown/respawn behavior, DLC detection, separate species loadouts, Forge/dropped-weapon identification, shared team scheduling, aircraft/navigation improvements, equipment hazard routing and final melee validation. The new launcher, updater and native adapters remain as installed.
- Restore fixed Legendary precision, zero reaction delay, 10 ms decision interval, 120-degree vision, head/chest targeting and live DMR/sniper head correction; restore sniper intended accuracy (Easy 10%, Normal 25%, Heroic 50%), tactical grenade policy, firing recovery, loaded-sniper retention, 80-unit power fetching, Reach loadout ratings/ranks and the collaborator's Breakpoint correction. Legendary-first resource assignment was discussed but never implemented and is not added here.
- Integrate the new Reach ammo fields and tag/magazine naming caches with our known-empty detection, signed/short-read guards and non-Reach isolation. Unknown named guns can still use upstream's magazine-learning fallback; battery depletion remains unknown.
- Restore installer-removed custom tests/workflow documentation. Add seven behavioral migration checks for upstream hazard and melee integration, tag caches, first-seen empty snipers, unknown-weapon learning, animated-head validation and species palette separation.
- Validation: all 40 regression tests passed; all 84 current Python sources compiled in memory; live runner --help and the new updater's offline selftest passed. The pre-existing placed.py ResourceWarning remains. This validates source integration, not live gameplay. No game/bot restart, native rebuild, GitHub push, tag or installer publication is included.
- Prior installation backup: F:/Proving Grounds Backups/Project Proving Grounds_2026-11-06_163131 (12,676 SHA-256-verified files). Raw newly installed source and its manifest are under ignored logs/migration_0.2.2-s181_2026-11-06. User settings, recordings, binaries and derived map assets remain outside the source commit.

## 0.2.1-custom.3 — source update, 2026-11-05

- Batch the three local gameplay updates: fixed Legendary zero reaction delay; fixed Legendary 10 ms decision interval without timing variation; and fixed Easy/Normal/Heroic sniper intended accuracy of 10%/25%/50% with precise aim and deliberate misses. Legendary sniper behavior and Scaling remain unchanged by the accuracy feature. The shared live loop remains 30 Hz.
- Preserve the individual implementation commits f929768, 12145d5, and 0c99e08 and all previously published collaborator commits. The owner explicitly authorized this source push to IEatOreos/ProvingGroundsOreo main. No tagged GitHub Release or installer asset is included.
- Detailed entries below describe the state when each change was implemented; their earlier "Unreleased" headings and "No GitHub upload performed" notes refer to that implementation stage.
- Validation: all 33 regression tests passed, all 82 current Python sources passed syntax compilation, and the full batch passed whitespace checks. The pre-existing placed.py unclosed-file ResourceWarning remains. Gameplay is untested; restart the bot process to apply. Intended sniper percentages do not guarantee match hit or kill rates.

## Unreleased — Difficulty-based sniper accuracy, 2026-11-05

- Fixed Easy/Normal/Heroic sniper rifles use precise head tracking with 10%/25%/50% intended hit rolls against on-foot targets. Remove competing aim wobble, lead error, and loose early/follow-through firing on this path. Use the live animated head marker where available, with the existing stance-height fallback. Miss outcomes fire beside and above the target rather than suppressing shots.
- Retain each difficulty's perception/reaction, decisions, movement, weapon cadence and safety checks. Preserve world movement direction during final shot aiming. Legendary's existing sniper/DMR behavior, Scaling, other weapons and vehicle combat are unchanged.
- Retain outcomes until a known magazine changes; rejected attempts and post-grenade retries do not repeatedly reroll. When magazine counts are unknown, use a cadence-bounded fallback; actual per-bullet acknowledgement is unavailable in that case. Suppress simultaneous melee/switch fire and exclude intentional misses from blocked-sightline learning.
- Validation: 33 offline regression tests passed, including nine sniper tests for distributions over 10,000 consumed rounds per tier, retry acknowledgement, reload observation, unknown-magazine fallback, action conflicts, exemptions, perfect tracking, final live-head aiming/movement, and false-wall prevention. All current Python source syntax and whitespace checks passed. The pre-existing placed.py ResourceWarning remains.
- Restart the bot process to apply; live gameplay is untested. Percentages describe intended shots, not guaranteed engine hits or kills. No GitHub upload performed.

## Unreleased — 10 ms fixed Legendary decision interval, 2026-11-05

- Set fixed Legendary's decision interval to 0.01 seconds and remove its per-decision timing variation. Other difficulties and Scaling retain their original interval and random variation.
- The live brain loop remains 30 Hz. The shorter decision deadline is processed on an available loop update, not at a guaranteed 100 decisions per second. The prior zero reaction delay remains in place.
- Validation: profile isolation and actual scheduling-block checks passed; existing regression tests, Python syntax checks, and whitespace checks passed. Gameplay is untested; restart the bot process to apply. No GitHub upload performed.

## Unreleased — Zero fixed Legendary reaction delay, 2026-11-05

- Set make_profile's fixed Legendary reaction override from 1/30 second to 0 seconds. Other difficulties and Scaling's separate profile builder are unchanged.
- Zero removes the configured perception reaction delay, including its peripheral multiplier; it does not remove live-loop scheduling or decision intervals.
- Validation: checked all personalities for zero Legendary reaction, unchanged other-tier and Scaling profiles against the prior source, and zero central/peripheral react_time results. Python syntax and whitespace checks passed. Live gameplay is untested; restart the bot process to apply. No GitHub upload performed.

## 0.2.1-custom.2 — source update, 2026-11-05

- Set Reach's weapon ranks to Focus Rifle 3.6 and DMR 3.5, across difficulties. Other games retain their prior ranks. Retain the requested Focus range tuple (0.1, 1.0, 1.0, 1.0), Reach AR Short-band rating 0.8, shotgun rating 1.0, and Reach upgrade cutoff 0.05.
- Verified calculated scores with the new ranks: DMR+AR 0.91, DMR+Focus 0.92, Focus+AR 0.98, DMR+shotgun 0.97, Focus+shotgun 1.04. An eligible nearby Focus upgrade replaces the DMR while preserving the AR or shotgun; it is still not a dedicated power-weapon fetch item. Battery depletion remains unknown.
- This source-upload batch also includes the earlier developer handoff, the collaborator's unchanged Breakpoint sight-line fix (1aa3339), fixed Legendary 80-unit power-weapon calls with travel allowance, the AR/shotgun preference change, Focus range ratings, and the collaborator-preservation workflow. Detailed entries below record the state when each was implemented; their earlier "not uploaded" notes do not describe the final publication state of this batch.
- Preserve all existing commits, including the collaborator's commit, in the normal main-branch history. The owner explicitly approved this source push. No tagged GitHub Release or installer asset is requested or included.
- Extend loadout regression coverage to verify Focus pickup/drop decisions across difficulties, preservation of the close-range secondary, reverse-pickup rejection, and unchanged ranks outside Reach. Live gameplay still requires restarting the bot process and owner confirmation.
- Validation: all 24 regression tests passed; all 81 Python sources compiled; whitespace check clean. The existing placed.py unclosed-file ResourceWarning appeared during the passing Breakpoint checks. The collaborator's commit remains an ancestor, and its map, terrain, correction-data, and test files are byte-for-byte unchanged from that commit.

## Local workflow — preserve collaborator commits, 2026-11-05

- Recorded the owner's requirement to preserve the coding collaborator's commits and intended behavior in AGENTS.md and docs/CUSTOM_RELEASE_WORKFLOW.md.
- Future pushes require fetching/reviewing the latest remote commits, merging incoming work without rewriting published history, reconciling overlapping behavior, and using normal pushes. Force-pushing or overwriting newer files with older copies is prohibited.
- Documentation only; no bot behavior changed and no GitHub upload performed.

## Unreleased — Focus Rifle range ratings, 2026-11-05

- Set the Focus Rifle proficiency tuple to the requested (0.1, 1.0, 1.0, 1.0). This changes AI range/loadout valuation, not the weapon's actual damage, battery, or aiming mechanics.
- With Reach's current AR rating and range weights, the real loadout calculator returns DMR+AR 0.95, DMR+Focus 0.92, and AR+Focus 0.94. DMR+Focus still scores 0.03 below DMR+AR: a 0.06 weighted short-range loss exceeds the 0.03 extreme-range gain.
- A nearby Focus Rifle is still rejected as an ordinary upgrade from a loaded DMR+AR loadout. No pickup cutoff, weapon rank, or power-weapon fetch classification was changed for this request.
- Validation: all four loadout regression scenarios passed; all 81 Python sources compiled. Requires a bot-process restart for gameplay; no GitHub upload or release performed.

## Unreleased — Reach AR and shotgun loadout preference, 2026-11-05

- Set Reach's assault-rifle Short-band proficiency to 0.8; the shotgun remains 1.0. AR ratings at other distances are unchanged. Other Halo games retain their original AR ratings.
- Reduce the ordinary Reach upgrade cutoff from 0.08 to 0.05. The requested DMR+AR -> DMR+shotgun improvement is 0.06, so changing the rating alone would still have been rejected by the old cutoff. This cutoff applies to other ordinary Reach upgrade decisions too; it does not force every higher-ranked gun to replace a lower-ranked one.
- Current calculated pair scores: DMR+AR 0.95, DMR+shotgun 1.01. The real upgrade/weapon-selection methods accept the nearby shotgun and equip the AR for replacement while keeping the DMR. The reverse AR pickup is rejected.
- Applies across Reach difficulties, including Scaling. Existing pickup distances, recent-swap protections, combat priorities, and the loaded-sniper low-ammo exemption remain in place. The range rating also informs ordinary combat weapon selection; game weapon damage and accuracy are not modified.
- Added four regression scenarios in tools/test_reach_loadout.py covering the requested pickup/drop decision, reverse rejection, other-game behavior, and distance/cooldown restrictions. Requires bot-process restart and gameplay confirmation; no GitHub push is included.
- Validation: all 22 available regression tests passed, all 81 Python sources compiled, and the whitespace check passed. The pre-existing placed.py unclosed-file ResourceWarning appeared during Breakpoint checks; no test failed.

## Unreleased — Fixed Legendary power-weapon call range, 2026-11-05

- Increase the team director's power-weapon fetch radius from 40 to 80 world units for fixed Legendary only (`tier == "top" and extra is None`). Easy, Normal, Heroic, and Scaling retain their existing behavior and radius.
- For fixed Legendary loose-weapon calls, allow at least estimated straight-line walking time (distance / 2.3) plus 10 seconds, retaining the original 25-second minimum. This prevents longer trips from expiring before normal arrival; it is a travel allowance, not a delay before starting.
- Preserve nearest-eligible one-bot assignment, the existing height limit, objective/carrier/vehicle restrictions, missing-weapon cancellation, and timed-spawn deadlines. Combat priorities, weapon classifications/rankings, and respawn anticipation remain unchanged. This improves opportunities, not guaranteed pickup ownership or a measured majority of spawns.
- Added tools/test_legendary_power_fetch.py with seven focused scenarios covering expanded range, difficulty separation, travel lifetime, assignment ownership, eligibility, cancellation, and timed-spawn deadlines.
- Validation: all 18 focused checks passed (seven power-fetch, eight ammo/rearm, three existing Breakpoint sight checks); all 80 Python sources compiled; whitespace check clean. The existing Breakpoint check emitted an unclosed-file ResourceWarning from brain/placed.py but passed.
- Requires a bot-process restart and gameplay confirmation. No GitHub push or release is included in this local change.

## Unreleased — Breakpoint tower-to-bridge sight fix, 2026-11-05

- Breakpoint (reach_dlc_invasion) only. The level export has no ground in the gap between the tower ledge and the bridge, only a thin sloped surface 16-26 u overhead (x 1.9-6.6, y 11-23). Sight, shot and crosshair rays treated the air under it as inside a hill, so bots on the bridge never saw a person on the ledge.
- Evidence: BTB match 20261105-192945, seconds 171-213. Enemies aimed straight at the ledge from 15-23 u but only heard the person or tracked them on radar, while the person's DMR shots hit them. The owner's Theater clip from the same spot shows a clear view of the bridge.
- Added maps/reach_dlc_invasion/sight_open.json and Terrain.set_open_under (loaded by maps._build). In that box, cells with no floor whose only surface is above z 5 have no ground for _ray and aim_hit (375-400 cells). Walking, falls and aircraft still use the original lowest-surface data. No other map has the file, so no other map changes.
- Replaying the match positions, sight lines from enemies facing the ledge (within 30 u and 60 degrees) went from 13 of 138 open to 46 of 138. The remaining blocks are the ledge lip in front of the person and a low solid wall near the bridge, which a bot's eye line just grazes. Those were left unchanged.
- Validation: the new tools/test_breakpoint_sight.py (3 tests) fails without the correction file and passes with it; the eight ammo/rearm tests pass; 79 Python sources compile; whitespace check clean.
- Gameplay confirmation still needs a bot-process restart and a live check from the tower ledge with enemies on the bridge. No GitHub upload or release performed.

## Local documentation — developer handoff, 2026-11-05

- Added DEVELOPER_HANDOFF_2026-11-05.md with repository access/setup, exact published commits, retained customizations, implementation details, validation, evidence locations, and outstanding work.
- Publication clarification: the initial snapshot c9a9b1f and both fixes (3f96e8e and a731340) were pushed to the private GitHub repository with owner approval. Earlier "Unreleased" and pre-upload statements below describe the state when those entries were written; no tagged GitHub release or installer has been published.
- Handoff verification reran all eight ammo/rearm tests and compiled all 78 Python sources. No bot behavior changed for this documentation task.
- The handoff and this documentation update are local; another upload requires owner approval.

## Unreleased — Keep a sniper with ammunition, 2026-11-05

- Exempt the held sniper from low-ammunition rearming while it has any total ammunition remaining, including a reserve round awaiting reload. Applies across difficulties and games using this shared rule.
- A completely empty sniper retains existing rearming and weapon-switching behavior. Other weapons retain their low-ammo rules. Deliberate upgrade/power-weapon pickup decisions are unchanged.
- Motivated by LilWraith dropping a sniper with two rounds for an assault rifle while carrying a loaded DMR. Regression coverage checks one/two remaining sniper rounds across five difficulty modes, empty snipers, and an ordinary low-ammo weapon.
- Validation: all eight ammo/rearm regression tests passed; all 78 Python sources compiled; the patch passes whitespace checks.
- Gameplay confirmation requires restarting the Proving Grounds bot process. No GitHub upload or release performed.

## Unreleased — Reach live ammo and reload fix, 2026-11-05

- Supply live total-ammo and magazine counts for recognized magazine-fed Reach weapons. Battery/charge weapons and objectives remain unknown, rather than being incorrectly treated as empty. Halo 4 and H2A retain their existing reader behavior.
- Remember observed magazine counts every bot tick, including combat, so the existing 40% between-fights reload threshold has a useful reference after a kill.
- Existing empty-weapon switching and rearming rules can now use Reach ammo counts. These data changes apply across difficulties; their existing decision differences remain.
- Verified read-only in a live Reach match: DMR 15 loaded/30 reserve -> 12/30 after three shots -> 15/27 after reload; sniper 4/4 -> 3/4 -> 4/3 -> 0/0 after depletion. HUD showed the empty-sniper switch prompt at 0/0.
- Other listed magazine-fed weapons use the same reader but still need individual gameplay confirmation. Battery depletion is not implemented. Bot reload/switch behavior after restarting the process still needs gameplay confirmation.
- Validation: six offline regression tests passed, covering recorded count sequences, unknown/battery and invalid reads, isolation from H4/H2A layouts, empty-sniper switching across all five difficulty modes, and low-magazine reload decisions after combat observation. All 78 Python sources compiled. The updated live player reader reported DMR total/magazine 42/15 and sniper 0/0; the player had already switched to the DMR, so this was not an observed bot switch.
- Controlled memory samples, pre-change source copies, and the exact patch are saved locally under logs/ammo_probe (excluded from GitHub).
- No GitHub upload or published release is authorized by this local fix.

## 0.2.1-custom.1 — prepared 2026-11-05, unpublished

- Establish local version control for the installed upstream 0.2.1 derivative.
- Inventory retained Legendary precision, live-head targeting, grenade, firing retry, and vision changes in CUSTOMIZATIONS.md.
- Preserve upstream license, notices, documentation, and credits.
- Exclude local logs, recordings, settings, bundled runtimes, generated map exports, installers, and the separate vehicle recorder.
- Document explicit user approval for every GitHub push and release.

This setup makes no changes to bot behavior. Historical gameplay and validation results in the handoff are not new checks performed for this snapshot. Sniper live-head behavior still needs gameplay confirmation. No sniper miss-chance behavior has been added.

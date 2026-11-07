# Custom release history

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

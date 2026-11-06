# Custom release history

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

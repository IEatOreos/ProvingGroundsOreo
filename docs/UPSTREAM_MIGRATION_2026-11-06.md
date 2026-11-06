# Migration to installed upstream 0.2.2-s181

Local custom version: **0.2.2-custom.1**, based on the author's installer applied on November 6, 2026. Upstream VERSION remains `0.2.2-s181`. No GitHub publication is authorized by this migration.

## Provenance and recovery

- Previous published custom source: `4d4d847` (`0.2.1-custom.3`). Preserve this and all earlier commits, including collaborator commit `1aa3339`.
- Full previous installation: `F:/Proving Grounds Backups/Project Proving Grounds_2026-11-06_163131`. All 12,676 files were verified with SHA-256 before the installer ran; its checksum manifest is beside that folder.
- The new installer left the existing Git repository in place, replaced shared source files and removed our custom tests and release-workflow document. Those custom-only files were restored from Git.
- Before integration, the installed tracked source plus new source files were copied to `logs/migration_0.2.2-s181_2026-11-06/installed`, with `manifest.json` and an installed-versus-custom patch beside it. This ignored local snapshot contains 1,161 files. It records the actual installed state, not independently verified upstream repository history.
- Git records installed source import `6433bb3` and the subsequent customization merge separately. No published history is rewritten.

## Integration decisions

Keep the author's new code as the working base. Restore only reviewed custom methods, constants and insertion blocks. Native source, installed binaries, the new launcher/updater, Firefight lifecycle, map-variant identification, navigation and vehicle improvements remain from the new installation.

The key overlap is Reach ammunition: upstream now uses the same reserve/magazine offsets as our live-verified reader. Our override preserves first-seen known-zero detection and invalid-read/game guards while updating upstream's tag/magazine caches. Unnamed weapons can still use upstream's generic magazine-learning path. Battery depletion is still unimplemented.

Bot.think combines the new hazard-aware navigation and final melee-facing/teammate check with our combat magazine observation, final head corrections, grenade-recovery handling and sniper shot rolls. Terrain integration preserves the new walked-cell/navigation changes while restoring precise body-part rays and the map-scoped Breakpoint overhead correction.

Retained custom behavior:

- Fixed Legendary: precise aim, zero configured reaction delay, 10 ms decision deadline without jitter, 120-degree detection, live DMR/sniper head correction and the AR chest exception.
- Fixed Easy/Normal/Heroic: precise sniper targeting plus intended 10%/25%/50% hits. Actual engine hits are not guaranteed; Scaling is excluded.
- Tactical grenades and post-throw retries; deliberate sniper misses do not teach false walls.
- Fixed Legendary loose-power fetch radius 80 units and travel allowance. No Legendary-first allocation was added; that was only discussed.
- Loaded-sniper low-ammo retention; Reach AR close rating 0.8, shotgun 1.0, Focus tuple (0.1, 1.0, 1.0, 1.0), Focus rank 3.6, DMR 3.5 and Reach upgrade cutoff 0.05.
- Collaborator's Breakpoint sight correction and tests.

The live loop remains 30 Hz; a 10 ms decision deadline is processed on available updates. Existing match rules still govern health, shields, damage, ammo and movement.

## Validation and live checks

All 40 offline regression tests passed, including seven new integration checks. All 84 current Python sources compiled in memory. The live runner loads and displays --help, and the new updater's offline selftest passes. The prior placed.py unclosed-file ResourceWarning remains. No native rebuild is required: native source and binaries are the new installer versions.

After restarting Proving Grounds, check normal match startup and shutdown, Legendary DMR/sniper aim, lower-tier sniper shots, empty-sniper switching/reloading, power fetching, weapon replacements and the Breakpoint ledge. Firefight and newly changed vehicle behavior also need gameplay confirmation. No live game result is claimed from offline tests.

The author's updater remains unmodified. Running another upstream installer, including an enabled automatic update, can replace customized source again; preserve the custom Git history and repeat a source merge after future updates. Machine settings, recordings, bundled runtimes, binaries and derived map exports are not included in source commits.

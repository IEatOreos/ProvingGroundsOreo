# Project Proving Grounds — custom bot developer handoff

Prepared November 5, 2026, America/New_York. This is a standalone handoff for the next developer or coding agent. It describes the installed code and work completed in this session; observations, verified behavior, and proposals are distinguished below.

## 1. Start here

We are customizing **Project Proving Grounds**, an existing Halo: The Master Chief Collection bot mod. Testing has primarily been **Halo: Reach offline 1v1 custom games**, with the owner reviewing Theater clips from the bot's perspective.

The owner's objective is extremely accurate, challenging fixed Legendary bots with better combat decisions. Preserve the existing accuracy work while fixing decisions such as reloading, using an empty weapon, and discarding useful power weapons.

Current state:

- The actual installed folder is also the Git working tree: `E:\Proving Grounds\Project Proving Grounds`.
- Private GitHub repository: [IEatOreos/ProvingGroundsOreo](https://github.com/IEatOreos/ProvingGroundsOreo).
- `main` was verified on GitHub at **`a731340d21ec6bbdff65f850f0ace321bb24767d`** when this handoff was prepared.
- Both the live-ammo/reload fix and the sniper low-ammo exemption are pushed.
- GitHub has **no release entries** as of this check. No custom installer or release package has been published.
- Eight focused ammo/rearm regression tests pass. All 78 `brain/*.py` and `tools/*.py` sources compile with the installed Python runtime.
- Battery/energy depletion detection is **not implemented**. It must not be described as working.
- Restart the Proving Grounds bot process/launcher after Python changes. Coordinate around the owner's active match.
- **The owner must approve each future push, published tag, release, or artifact upload.** Today's completed pushes do not authorize later uploads.

This handoff is a new local document created after the code commits above. Unless separately approved and pushed later, obtain it directly from the owner rather than assuming it is already on GitHub.

## 2. Repository, history, and version identification

| Commit | Purpose | Publication |
|---|---|---|
| [`c9a9b1f`](https://github.com/IEatOreos/ProvingGroundsOreo/commit/c9a9b1f05c5fa55eb7f4141bb2bbe719cd199801) | Initial snapshot of the already-customized installed source, plus customization/workflow documentation | Pushed |
| [`3f96e8e`](https://github.com/IEatOreos/ProvingGroundsOreo/commit/3f96e8e9493221164ccae21821cb9cd876b8ee37) | Read live Reach ammo and retain observed magazine counts during combat | Pushed |
| [`a731340`](https://github.com/IEatOreos/ProvingGroundsOreo/commit/a731340d21ec6bbdff65f850f0ace321bb24767d) | Exempt a held sniper with remaining ammunition from low-ammo rearming | Pushed |

[Exact changes after the initial snapshot](https://github.com/IEatOreos/ProvingGroundsOreo/compare/c9a9b1f...a731340) · [Commit history](https://github.com/IEatOreos/ProvingGroundsOreo/commits/main)

`VERSION` is **0.2.1**, the installed upstream version. `CUSTOM_VERSION` is still **0.2.1-custom.1**; it was not bumped when the two fixes were pushed. Identify the precise current source by commit SHA. Pushing commits did not create a versioned release or installer.

There was no earlier Git history or verified pristine baseline for the original customized installation. Earlier accuracy/grenade/vision changes are present in the first snapshot, but are not individually reconstructed commits. The later 0.2.1 migration does have six-file original/staged copies and an exact migration patch in the local backup described below. Those records do not establish a pristine baseline for the entire earlier installation.

Some existing documentation still calls the now-pushed fixes "local follow-up" or "Unreleased," and contains statements written before upload. The source commits above were subsequently pushed with the owner's approval. They remain untagged, with no GitHub release. Use this distinction when updating the older documentation.

## 3. How to get access and connect

### A developer using a separate GitHub account

The repository is private. The owner must invite the developer's own GitHub account, and the developer must accept. In the repository, the owner can use **Settings → Collaborators → Add people**. This document does not grant account access. [GitHub's collaborator instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)

After access is granted, authenticate normally and clone into a new development folder:

```powershell
git clone https://github.com/IEatOreos/ProvingGroundsOreo.git
Set-Location ProvingGroundsOreo
git remote -v
git status --short --branch
git log --oneline -5
git switch -c work/describe-your-change
```

These are local setup commands, not authorization to publish. Use the developer's own commit identity. [GitHub cloning instructions](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)

### Working on the owner's existing Windows installation

Do not initialize another repository inside it or overwrite it with a fresh clone. It is already connected:

```powershell
Set-Location 'E:\Proving Grounds\Project Proving Grounds'
git status --short --branch
git remote -v
git fetch origin
git log --oneline -5
```

The `origin` fetch/push URL is `https://github.com/IEatOreos/ProvingGroundsOreo.git`. Before changing branches or updating files, inspect the working tree and coordinate with any developer or active bot process using the same installation.

Git for Windows is installed. Git Credential Manager is configured as the credential helper, and browser authentication succeeded for the uploads. If reauthentication is needed on this authorized workstation, the command used successfully was:

```powershell
git credential-manager github login --username IEatOreos --browser
```

The account holder completes the browser flow. GitHub CLI (`gh`) was not installed at the time of setup. It is optional; Git plus Credential Manager was sufficient. Do not request passwords or paste tokens into chat, source, or remote URLs. [GitHub authentication/credential guidance](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git)

### A separate coding service or GitHub integration

Authorize that service for this private repository using its normal GitHub access flow. An integration's repository access and command-line Git authentication are separate: our GitHub integration returned 404 for the new repository while authenticated Git successfully accessed and pushed it. Check repository permissions and authentication before interpreting a 404 as a missing repository.

No collaborator invitation, new integration authorization, or credential transfer was performed as part of creating this document.

## 4. What is and is not in the repository

The first source snapshot contains 1,155 files, approximately 59 MB before Git compression. It is based on an installed mod, not a separately verified complete upstream developer checkout.

Excluded installation/runtime data includes `python/`, `native/bin/`, `logs/`, local backups, installed map tools, generated models/art, optional map-pack files, learned map/variant data, installation archives/uninstallers, and the separate `Vehicle Data Recorder/` add-on. Review `.gitignore` for the actual patterns.

**`user/` currently exists locally, is untracked, and is not explicitly ignored by the current `.gitignore`.** It contains per-machine settings according to the upstream guide. It was not uploaded. Do not use a blanket `git add --all`; stage intended files explicitly and preserve this folder.

A fresh clone is not a runnable replacement for the complete installation by itself. It lacks the installed runtime, native build outputs, and generated/optional assets. Read `docs/CODE_GUIDE.md` and the upstream setup/build instructions. References in that guide can point to developer files absent from this installed-source snapshot; for example, `tools/make_release.py` and `CONTRIBUTING.md` were not present when checked.

Original upstream: [AyoItzKye/project-proving-grounds](https://github.com/AyoItzKye/project-proving-grounds). Preserve `LICENSE.md`, `NOTICE.md`, credits, and third-party notices. The included project license is PolyForm Noncommercial 1.0.0. The existing README's download and bug-report links point to upstream, not to the custom repository.

The mod's existing scope is offline custom games with anti-cheat off. Preserve its refusal to operate with anti-cheat enabled. No work here targets matchmaking or online competitive services.

## 5. Architecture and useful files

| File or area | Role / reason to inspect |
|---|---|
| `AGENTS.md` | Local coding-agent instructions, approval policy, and preservation requirements |
| `CUSTOMIZATIONS.md` | Inventory of retained custom behavior and unresolved proposals |
| `CUSTOM_CHANGELOG.md` | Implementation and validation notes; see publication-status clarification above |
| `docs/CUSTOM_RELEASE_WORKFLOW.md` | Owner-approved working/release process; its repository-setup suggestion predates the actual chosen name |
| `docs/CODE_GUIDE.md` | Upstream architecture/build reference; reconcile with installed files and custom code |
| `brain/bot.py` | Perception, aim, combat, weapon selection, pickups, rearming, reloads, final shot adjustment, grenade retries |
| `brain/profiles.py` | Fixed difficulty profiles and custom Legendary precision values |
| `brain/scaling.py` | Separate Scaling profile construction and adaptive parameters |
| `brain/core.py` | `PlayerState`, `Snapshot`, `Action`; includes optional `head_pos` and ammo/magazine fields |
| `brain/live.py` | Read-only per-game memory readers; Reach animated head marker and new ammo integration |
| `brain/terrain.py` | Navigation/visibility material rules and chest/head visibility rays |
| `brain/director.py` | Team roles, coordination, power-weapon fetch assignments |
| `brain/maps.py` | Map definitions, spawn items, pickup values/classification |
| `brain/equipment.py` | Armor abilities, shooting restrictions, vehicle/weapon counters |
| `tools/live_bots.py` | Live brain loop, about 30 Hz; constructs snapshots, forwards `head_pos`, writes traces, sends bot actions |
| `tools/memread.py`, `tools/tls.py` | Read-only game-memory/TLS access used by probes; include anti-cheat refusal |
| `tools/test_reach_ammo.py` | Eight regression tests for ammo integration, reload decisions, and sniper rearming |
| `native/`, `tools/botctl.py` | Native hooks/shared-memory action interface; no native changes made in this session |

The native mod executes bot inputs inside MCC. Python reads state, computes decisions, and submits inputs through the established shared-memory interface. Debug probes described here only read game memory; they do not control the human player or alter ammo.

## 6. Retained customizations already in the initial snapshot

### Fixed Legendary must remain separate from Scaling

The behavior guard is:

```python
fixed_legendary = profile.tier == "top" and profile.extra is None
```

Scaling also uses `tier == "top"` but carries `extra` data. Its profiles are built separately by `brain/scaling.py:profile()`, not through the fixed Legendary override in `make_profile()`. Do not broadly apply our fixed Legendary changes to all `top` profiles.

Fixed Legendary precision settings:

| Parameter | Value |
|---|---:|
| `aim_err` | `0.0` |
| `lag` | `0.001` seconds |
| `track` | `0.001` seconds |
| `overshoot` | `0.0` |
| `lead` | `0.0` |
| `flick` | `0.05` |
| `reaction` | `1.0 / 30.0` seconds |
| `turn` | `math.radians(1000)` |

The live brain targets about 30 Hz; 1 ms profile values do not mean it runs at 1,000 updates/second. Reaction is also processed by the perception logic rather than being a guaranteed measured response time.

Fixed Legendary has no random under/over-leading, hand tremor, or prediction of its own movement. Ordinary eligible on-foot weapons target the head regardless of shields; the assault rifle targets the chest. Splash, charge, melee, and vehicle cases use their separate rules.

### Reach live animated head targeting

The key confirmed accuracy improvement was reading the live animated Reach Spartan head marker, rather than only aiming at a fixed height above the feet.

- `LiveReach.spartan_head_position()` produces an optional position.
- `PlayerState.head_pos` carries it through `tools/live_bots.py`.
- On an eligible fixed Legendary DMR or sniper firing command, `Bot.think()` corrects final yaw/pitch toward that position **after the turn cap**. It rotates movement inputs to preserve the intended travel direction.
- If the live head position is unavailable, it falls back to an estimated stance-dependent head position.
- The validated layout check expects an 82-node Spartan transform block, offset `0xF1C`, and head node 38; the reader also validates scale, matrix properties, finite values, and displacement from the feet. Other models/layouts are not proven equivalent.
- DMR firing has a custom alignment relaxation when head-only targeting applies; visibility and other firing restrictions still matter. The sniper retains its normal alignment and cadence checks.

DMR accuracy was confirmed by the owner in gameplay. The owner later reported very strong sniper accuracy as well. There is no recorded controlled sniper hit-rate benchmark, and neither correction guarantees a hit through movement, latency, occlusion, or game weapon mechanics.

### Grenades and post-throw firing

Fixed Legendary grenades remain enabled (`LEGENDARY_GRENADES = True`), but these two ordinary fight behaviors are suppressed for fixed Legendary:

- Opening a newly started fight with a grenade.
- Random visible-enemy "keep the pressure" throws.

Tactical throws remain: flushing cover, occupied objectives, anticipated lift landings, vehicle attacks/boarding, and armor-ability counters.

Shared post-grenade recovery retries apply to eligible ordinary weapons across difficulties. The **2-second setting is a retry window, not a forced delay**. Semiautomatic retries alternate releases and presses. Known magazine decreases acknowledge resumed gunfire; unknown magazines use bounded attempts. Retry requests alone must not count as confirmed shots for blocked-line learning.

The owner observed long post-throw pauses. Earlier traces showed retries beginning about 33 ms afterward, but actual game weapon recovery timing was not conclusively established. Keep this unresolved rather than claiming it was fully fixed. Reach's new magazine data can support better confirmation now.

### Vision and material rules

Fixed Legendary's horizontal detection cone is 120 degrees: normal reaction within 50 degrees of center, and a 1.5 peripheral reaction multiplier between 50 and 60 degrees. Normal and Scaling retain the original FOV settings. Sight range remains 80 world units.

Radar was investigated, not customized. Its eligible-contact probability uses `profile.radar * 0.15` per update; actual profile jitter and eligibility rules matter. Contacts require movement, an uncrouched target, range, and the match's radar settings.

Visibility integration was adapted to the author's separate sight and bullet-material rules. Preserve seeing through appropriate glass/fences without assuming every visible line is shootable. The selected head/chest ray must respect the bullet material mode and source height.

## 7. New live ammo and reload fix — commit 3f96e8e

### Cause and data contract

The brain already had ammo-aware rules, but Reach player snapshots did not supply ammo or magazine arrays. The owner saw bots retain nearly empty magazines after a kill and keep an empty sniper equipped.

`PlayerState.ammo[i]` means **magazine + reserve total**, not reserve alone. `PlayerState.mag[i]` is the loaded magazine. Both arrays align with `weapons`. **`-1` means unknown; `0` means known empty.** Never turn unknown battery weapons into empty guns.

### Live verification

Read-only samples from the same weapon objects were compared with controlled owner actions and the HUD:

| Weapon / action | Loaded | Reserve | Total supplied to the brain |
|---|---:|---:|---:|
| DMR initially | 15 | 30 | 45 |
| Fire exactly 3 DMR shots | 12 | 30 | 42 |
| Reload DMR | 15 | 27 | 42 |
| Sniper initially | 4 | 4 | 8 |
| Fire exactly 1 sniper shot | 3 | 4 | 7 |
| Reload sniper | 4 | 3 | 7 |
| Exhaust all remaining sniper rounds | 0 | 0 | 0 |

The sniper HUD showed the out-of-ammo/switch prompt at 0/0. The updated live player reader subsequently reported DMR total/magazine 42/15 and sniper 0/0. The human had already switched to the DMR then; that check was not an observed bot switch.

### Implementation and limits

`LiveReach.rounds()` reads signed 16-bit reserve at **weapon object + `0x2C6`** and magazine at **+ `0x2CA`**. It validates read length and rejects negative values. A newly encountered, fully empty recognized gun returns 0/0 rather than unknown. `LiveReach.players()` now populates both aligned arrays.

The reader uses a magazine-fed weapon allowlist:

`dmr`, `sniper`, `assault_rifle`, `magnum`, `shotgun`, `needle_rifle`, `needler`, `rockets`, `fuelrod`, `concussion_rifle`, `grenade_launcher`.

Only DMR and sniper count transitions were verified live. Other listed weapons share the implemented layout but need individual gameplay confirmation. Layout comments refer to MCC 1.3528; game updates require revalidation.

The implementation explicitly checks `haloreach.dll`. Halo 4 and H2A inherit parts of the class hierarchy but retain their previous ammo behavior; do not accidentally apply Reach offsets to them.

`Bot.think()` also remembers observed magazine maxima **during combat**, before planning. Previously the reload helper only learned them between fights, which could make a low post-kill magazine become the reference maximum. This still uses observed maxima, not a tag-derived magazine capacity; spawning with an already-low magazine remains a case worth testing.

### Existing behavior that now has usable Reach data

- Proactive reloads occur between fights, with no visible enemy, at **40% or less of the highest observed magazine**, with reserve rounds available and a 3-second reload-request cooldown. The caller excludes fighting/retreating, objective carrying, and an active weapon switch. This is not a guarantee to reload after every kill.
- Normal and above can switch away from an empty magazine in combat to another loaded, non-explosive weapon at close enough range. A completely dry gun has a separate switching path; Easy retains its deliberate hesitation.
- If no manual reload/switch is selected, the existing code relies on the game's empty-magazine trigger/reload behavior.
- Rearming can seek replacement ground weapons when ammo is exhausted or low.

Decision tests passed; reload animations and all weapon/game-mode combinations have not been comprehensively validated in live bot matches.

## 8. Loaded sniper replacement fix — commit a731340

The owner provided [this Theater clip](https://streamable.com/vfa6m3) of a bot dropping a sniper with ammunition for an assault rifle. LilWraith's local trace records DMR total/magazine 30/15 plus sniper 2/2 immediately before a sniper-to-AR swap. It also records subsequent pickups/drops of that sniper.

The cause was `Bot.rearm_point()`:

1. The held gun qualified as low with fewer than 6 total rounds and less than half its highest observed total.
2. Low-ammo rearming selected a nearby ground weapon without requiring a loadout improvement.
3. `drop_slot()` favored retaining the DMR, so the nonempty sniper was discarded for the AR.

The decision was reproduced using the logged ammo and pickup position. The owner explicitly requested removing the sniper from this low-ammo logic because even one sniper shot is valuable.

The targeted exemption is:

```python
if me.weapon == "sniper" and held > 0:
    return None
```

Here `held` is the current weapon's total ammo. One reserve round awaiting reload also qualifies. The shared change applies across difficulties and games using this method.

**Scope matters:** this prevents the **held sniper** from initiating a low-ammo rearming trip while it still has ammo. It is not a universal "never drop any loaded sniper" policy. Other upgrade/power pickup decisions, or a rearming trip initiated while holding a different weapon, are not globally blocked from replacing an inventory sniper. Completely empty sniper behavior is unchanged. No post-fix gameplay confirmation was recorded before this handoff.

## 9. Weapon and pickup findings that may guide future work

These are inspected behavior, not additional changes made here.

### Three different weapon valuations

- `brain/maps.py:POWER` supplies map-item values. `Director.power_runs()` gives dedicated fetch orders for weapon items valued at least 0.8: rockets 1.0, sword/laser 0.9, sniper/hammer 0.8. Fuel rod and plasma launcher are 0.6, so they can be picked individually but do not qualify for that dedicated assignment route.
- `WEAPON_RANK` plus `RANK_GAME` supplies base preferences. It is not a complete decision by itself.
- `loadout_value()` scores two-weapon distance coverage plus power-weapon value. Combat weapon selection then adds target/range/safety considerations.

Reach base ranks:

| Score | Weapons |
|---:|---|
| 5.0 | Rockets |
| 4.6 | Spartan Laser |
| 4.5 | Sword |
| 4.0 | Sniper, fuel rod, gravity hammer |
| 3.8 | Plasma launcher |
| 3.6 | DMR |
| 3.2 | Focus rifle |
| 3.0 | Shotgun, needle rifle, grenade launcher |
| 2.8 | Concussion rifle |
| 2.6 | Magnum |
| 2.3 | Plasma repeater, when represented under that internal name |
| 2.2 | Assault rifle, plasma rifle |
| 2.0 | Needler |
| 1.0 | Plasma pistol |

Aliases can affect which internal name reaches a rank lookup; inspect live names before assuming the HUD name selects a particular entry.

Dedicated fetches select an eligible nearby teammate within 40 world units and under 6 units of height difference, excluding occupied/urgent/carrier cases and bots already carrying a power weapon. Easy does not receive coordinated fetches; timed-spawn assignments require higher map knowledge. **The existing "already has a power weapon" test uses names, not remaining ammo.** An empty sniper can therefore block assignment until replaced.

Ordinary loose-weapon upgrades normally search within 14 units and under 1 unit of height difference; Easy searches within 2. They require a loadout gain greater than 0.08, favor proximity, skip duplicates, and generally yield to nearby threats/recent damage. The score values close/medium/long/extreme coverage with weights 0.30/0.35/0.25/0.10. Rank-4+ guns contribute half coverage to encourage a usable secondary.

A useful counterexample: AR + DMR → DMR + sniper gains only **0.04**, so the ordinary upgrade route rejects it. Separate spawn/fetch decisions can still pursue the sniper. DMR + sniper → DMR + rockets gains 0.40. These were evaluated using the current code.

`drop_slot()` prioritizes known-empty guns, then preserves the highest-value remaining combination. Rearming searches up to 60 units when all carried guns are known empty, otherwise up to 12 for low ammo. Failed pickups and recent swaps have cooldowns, but not every acquisition route shares all protections.

### Projectile, beam, and charge behavior

| Weapon | Current main firing behavior |
|---|---|
| Rockets | Feet/splash aim; 1.1-second base shot interval; ordinary alignment, visibility, range, and blast checks |
| Fuel rod | Feet/splash aim; 0.6-second base interval; modeled projectile speed 9.5 world units/second |
| Concussion rifle | Feet/splash aim; 0.6-second base interval; no dedicated ledge/knockback strategy found |
| Grenade launcher | Feet/splash aim; 1.0-second base interval; no dedicated ballistic arc, planned bounce, or timed hold/release EMP detonation strategy found |
| Spartan Laser | Holds through a nominal 3-second charge, tracks the target, and cancels on specified lost-sight/line/time conditions |
| Focus rifle | Holds a continuous beam rather than bursts; fixed Legendary ordinarily head-targets on-foot enemies, without the DMR/sniper live-head correction |
| Plasma launcher | Charges/releases; nominal 1.6 seconds against ordinary targets; special 2.2-second vehicle alignment requirement with a 0.3-second tracking-slip reset |

Intervals are AI request timing, not promises about the game's actual firing cadence. Cooldowns, alignment, reloads, and engine state still apply. Higher difficulties mostly change reactions, aim, and tactics; they do not shorten every weapon's charge time. Explosive safety checks and a desperate trade exception also exist.

**Important interaction:** fixed Legendary's global `lead = 0` also disables target movement prediction for slow projectile weapons. Very accurate tracking of current feet position can still miss a moving target by arrival time. Fuel rods and rockets have explicit modeled speeds, while several other listed weapons fall back to a generic 360 units/second. That fallback is not validated weapon-specific flight modeling. No projectile-leading correction was implemented in this session.

## 10. Battery depletion: still an open task

The owner correctly identified the distinction:

- **0 remaining energy:** the weapon is depleted and should permit switching/replacement.
- **Overheated with energy remaining:** it is temporarily unable to fire, but should not be treated as permanently empty.

The owner supplied a plasma-pistol screenshot showing 0 and the game's out-of-ammo/switch prompt. That confirms the HUD behavior. Our bots do not read the HUD, and we have not located or validated the underlying per-weapon depleted condition or energy field.

We attempted a read-only depleted-pistol sample, but by capture time the inventory contained a needler and sniper. **`logs/ammo_probe/plasma_empty.json` and `plasma_empty_check.json` do not contain a valid empty plasma-pistol baseline despite their filenames.** They must not be used as evidence for a plasma-pistol energy offset.

Remaining energy is unknown for plasma pistol, plasma rifle/repeater, focus rifle, laser, plasma launcher, and other non-allowlisted weapons. Do not assume every item in that group uses an identical battery or reload model; classify each from verified engine/tag behavior.

A suitable next experiment is to keep the same identified battery weapon equipped through full, partially depleted/cooled, overheated-with-energy, cooled-again, and genuinely empty states. Record the HUD values and same-object memory reads at each step. Distinguish remaining energy from heat and charge progress before connecting a field to `ammo == 0`. Validate per-bot object state rather than relying only on a human-only HUD flag.

## 11. Validation, commands, and remaining gameplay tests

The installed runtime is **Python 3.14.2** under `python/python.exe`. Its embedded configuration does not automatically make every `python -c` invocation import the project root; scripts that import `brain` add the root explicitly. The regression script handles that itself.

From the installed project folder on Windows:

```powershell
& '.\python\python.exe' '.\tools\test_reach_ammo.py'
```

For a conventional Windows development environment with appropriate dependencies, use its Python executable instead. The tests import the Windows game reader (`ctypes.WinDLL`); they were verified on Windows, not as portable Linux tests. A clone does not include the bundled Python.

Syntax-check the same source set without producing bytecode:

```powershell
& '.\python\python.exe' -c "from pathlib import Path; paths=list(Path('brain').glob('*.py'))+list(Path('tools').glob('*.py')); [compile(p.read_bytes(),str(p),'exec') for p in paths]; print('Compiled',len(paths),'Python sources')"
git diff --check
```

Latest handoff verification: **8 tests passed; 78 sources compiled; no working diff whitespace errors.** Coverage includes controlled ammo sequences, unknown/battery preservation, invalid/short reads, isolation from H4/H2A offsets, empty-sniper switching across five difficulty modes, observed-magazine reloads, loaded-sniper rearming exemptions, and retained empty/other-weapon rearming.

The earlier 0.2.1 migration separately recorded 77 compiled sources and seven focused checks. Do not present those as a freshly rerun full upstream test suite. The increase from 77 to 78 sources comes from the added ammo regression script.

Priority gameplay checks after restarting the bot process:

1. A bot with a DMR at 3/15 loaded and reserves, after the fight ends, requests and completes a reload. Also test visibility/retreat situations where it intentionally holds off.
2. A bot exhausts all sniper ammunition while carrying a loaded secondary and switches away. Account for Easy's deliberate hesitation.
3. A bot with one or two sniper rounds does not initiate the former low-ammo trip to replace it with an AR. Also test other pickup routes to characterize the targeted fix's limits.
4. A sniper with an empty magazine but a reserve round reloads or otherwise handles that state without discarding it merely for being low.
5. Repeat count/reload/depletion checks for other allowlisted Reach guns before calling all of them verified.
6. Confirm H4/H2A and Normal/Scaling behavior after any future shared-reader/profile edits.

Compilation and computed decisions are not proof of actual input delivery, reload animation completion, hit rate, or every game-mode outcome.

## 12. Local evidence and backups

These paths are on the owner's PC and are not included in a normal GitHub clone:

| Path | Contents |
|---|---|
| `C:\Users\marsh\Documents\Codex\Proving Grounds Legendary backup 2026-11-05` | Original customization backup/context |
| `C:\Users\marsh\Documents\Codex\Proving Grounds migration 2026-11-05` | Six-file `original/` and `staged/` trees, `customizations.patch`, manifests, migration/validation scripts, `validation.txt`, `MIGRATION_REPORT.md` |
| `C:\Users\marsh\Documents\Codex\Proving Grounds Legendary sniper live head 2026-11-05` | Later sniper extension: `bot.before.py`, `bot.updated.py`, `change.patch`, `NOTE.md` |
| `E:\Proving Grounds\Project Proving Grounds\logs\ammo_probe` | Controlled DMR/sniper snapshots, pre-change copies, ammo patch, read-only probes, integration result, and the mislabeled/non-plasma battery samples described above |
| `E:\Proving Grounds\Project Proving Grounds\logs\trace_reach_forge_halo_20261105-174151.jsonl` | LilWraith inventory/ammo and pickup decisions used for the sniper replacement investigation |
| `E:\Proving Grounds\Project Proving Grounds\Vehicle Data Recorder` | Separate installed recorder add-on, excluded from the source repository |

The trace records a DMR+sniper → DMR+AR swap at brain time 239.441 seconds, followed by sniper reacquisition at 241.767 and another AR swap at 243.180. The sniper carried 2 total/2 loaded before the first swap. Preserve the distinction between brain timestamps, game clock, and Theater playback speed.

The `read_ammo.py`, `read_battery.py`, and `verify_integration.py` scripts in the probe folder were local investigation helpers. They do not change gameplay. They may need the same Windows process permissions as the live reader. Captures are point-in-time; coordinate exact shoot/reload steps with the owner and verify object handles before comparing samples. Do not reuse a sample label if the original evidence must be preserved.

Raw recordings/settings can contain personal or machine-specific details. Keep them local unless the owner explicitly asks to share relevant evidence; a request to share this handoff is not a request to upload all logs.

## 13. Upstream migration and owner workflow

The author released an update reporting 0.2.1. Our earlier customizations were ported individually into the new source, preserving the author's glass/fence, movement, game-mode, and sword/grenade improvements. The owner reported the migrated behavior worked well.

For another update:

1. Preserve the current custom tree and identify the new upstream version/source.
2. Read the new files, then merge the intended behavior at the reviewed integration points.
3. Preserve the separate sight/bullet material rules and both DMR and later sniper live-head correction.
4. Port the live-ammo integration and loaded-sniper rearming exemption too; they were added after the earlier migration records.
5. Revalidate memory layout assumptions, fixed Legendary/Scaling separation, and live gameplay. Existing exact-anchor migration scripts are specific to that saved version and must not be blindly rerun against another release.

Working preferences:

- Make small, targeted edits and explain their gameplay effect plainly.
- Preserve unrelated local changes; do not force-reset/clean this installed working tree.
- Keep precise commits and validation notes; stage named files, not the whole installation.
- Suggest a release checkpoint after roughly three meaningful updates, or whenever the owner asks. This is a reminder, not automatic permission.
- Prepare the actual candidate diff, destination, version/changelog, checks, and limitations before asking for upload approval.
- Push/tag/publish only the approved candidate. A branch push, source tag, GitHub Release, and installer asset are distinct operations.
- Use the next developer's own identity. Earlier commits used the owner's GitHub no-reply identity for the owner's local work; that is not permission for someone else to impersonate the owner.

This handoff does not authorize any new push or release.

## 14. Other open investigations and proposals

- **Visible enemy but withheld fire near a balcony:** a head line-of-sight rejection is suspected, not confirmed. Inspect actual gate/visibility diagnostics before treating this as a settled cause.
- **Post-grenade pauses:** trigger retries were observed, but game recovery timing remains unresolved.
- **Sniper miss percentage:** discussed an initial 80% precise-head-aim / 20% near-miss approach. **Not implemented or approved for implementation.** If pursued, a selected aim outcome should persist across retries, and the final live-head correction must not erase the intended offset. Aiming weights are not guaranteed measured hit percentages.
- **Projectile leading:** global fixed Legendary zero lead can hurt slow weapons. No weapon-specific leading fix was made.
- **Broader sniper retention:** the owner values even one sniper round. The implemented exemption is deliberately narrow; broader pickup-policy protection would be a separate change.
- **Flight learning:** gameplay demonstrations may help derive maneuvers. No imitation-learning or flight-controller changes were made. The separate vehicle recorder says it records vehicle state from memory, not raw keyboard/mouse/controller inputs; recorded inputs or intent would require additional instrumentation and agreement on the experiment.

## 15. Suggested first actions for the next developer

1. Obtain authorized repository access; inspect `main` and the working tree before editing.
2. Read this handoff, `AGENTS.md`, the current implementation, and the three historical commits.
3. Run the eight focused tests in a suitable Windows environment.
4. Confirm with the owner which task to pursue next: live gameplay validation, battery depletion, projectile leading, or broader weapon decisions. Discussion alone is not a request to implement every proposal.
5. Keep source changes local and reviewable until the owner approves the next upload.

The current code and commit SHAs are authoritative. This document records what was established and where evidence is still missing; revise conclusions when new controlled tests provide better evidence.

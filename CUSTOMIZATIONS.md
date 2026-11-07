# Custom Legendary bots

This is a custom derivative of [Project Proving Grounds](https://github.com/AyoItzKye/project-proving-grounds), now based on installed upstream version 0.2.2-s181. Original credits and licensing remain in LICENSE.md and NOTICE.md. This repository is not the upstream author's official release.

The 2026-11-06 migration merges our custom behavior into the new installed source and keeps its new native binaries, Firefight lifecycle changes, pickup fixes, vehicle improvements, hazard avoidance and melee validation. See docs/UPSTREAM_MIGRATION_2026-11-06.md for provenance, validation and remaining live checks. The following initial-snapshot section is historical; later notes describe current overrides.

The original README.md documents the upstream mod, and its download and issue links point to upstream. Custom release details belong in CUSTOM_CHANGELOG.md and docs/CUSTOM_RELEASE_WORKFLOW.md. VERSION retains the upstream version; CUSTOM_VERSION identifies our derivative.

## Retained behavior at the initial snapshot

The following inventory comes from the customization handoff. It is not a verified historical diff. Most changes target fixed Legendary (`tier == "top" and extra is None`), distinct from Scaling difficulty.

- Precision profile: aim_err=0, lag=0.001, track=0.001, overshoot=0, lead=0, flick=0.05, reaction=1/30 second, turn=1000 degrees/second.
- Fixed Legendary has no randomized under/over-leading, hand wobble, or own-movement prediction. It normally aims for the head; the assault rifle targets the chest.
- Final fixed Legendary DMR and sniper shot direction uses the Reach Spartan's live animated head marker, with a fallback when unavailable. The sniper keeps its normal alignment and cadence checks. DMR behavior was confirmed in gameplay; the sniper extension still needs gameplay confirmation according to the handoff.
- Fixed Legendary grenades remain enabled, excluding fight-opening and random visible-enemy pressure throws. Tactical grenade uses remain.
- Shared post-grenade firing retries include semiautomatic trigger releases. The two-second retry window is not a mandatory delay. Actual weapon recovery timing remains unresolved.
- Fixed Legendary detection uses a 120-degree horizontal cone. Reaction takes 50% longer between 50 and 60 degrees from center. Normal and Scaling retain their original FOV settings. Sight range remains 80 world units.
- Radar was investigated but not customized at this initial snapshot; see the current Demon override below.

Primary integration files: brain/bot.py, brain/profiles.py, brain/core.py, brain/live.py, brain/terrain.py, tools/live_bots.py.

## Open investigations and proposals

- Armor Lock's former low-shield/recent-hit activation is now a visible sword/Gravity Hammer proximity trigger within 6 world units, independent of the bot's health/shields, damage and enemy facing. Both low-shield Armor Lock branches were removed. Other triggers and hold/release rules remain; Easy and Infection-survivor exclusions remain. The rule covers the distinct Demon tier too. Initial validation: 60 tests and 87 source syntax checks passed; restart the bot process and confirm gameplay.

- Halo 4 now supplies a paired animated head marker and cached unit view point for the captured 120-node Spartan rig. Head-directed tracking, final DMR/sniper corrections, sniper hit/miss rolls and head visibility use the matched endpoints; invalid or unsupported layouts retain the legacy pair. Reach and H2A readers are unchanged. All 2,780 saved poses passed offline replay and 50 regression tests pass; post-fix gameplay is still unconfirmed. See docs/HALO4_HEAD_AIM_2026-11-06.md.

- Fixed Easy/Normal/Heroic sniper-rifle shots against on-foot targets now use precise head aim with intended hit chances of 10%/25%/50%. Random aim error and loose early/follow-through fire are bypassed for this path; misses fire beside/above the target. Known magazine consumption acknowledges shots so rejected attempts retain their roll. Undecoded magazines use a cadence-bounded fallback. Legendary, Scaling, other weapons, and vehicle combat retain their prior behavior. Deliberate misses do not teach false blocked sightlines. Gameplay requires a bot-process restart and live confirmation; intended percentages are not guaranteed match hit rates.

- Demon retains the 0.01-second decision interval without timing variation. Legendary now uses the upstream 0.10-second base interval, profile variation and per-decision jitter. The shared live loop remains 30 Hz, so deadlines are processed on available updates; restart the bot process to apply.

- Demon retains zero configured reaction delay. Legendary's base attributes now match the upstream profile, including 0.154-second base reaction, 0.08-second tracking, 0.045-second aim lag, 0.006 aim error, zero overshoot, 0.8 lead and 0.7 flick factor, with normal profile variation. Protected Legendary head-directed and vehicle aim still uses the prior precision parameters; live head markers and final DMR/sniper corrections are preserved. Scaling and lower tiers retain their settings.

- Current Reach loadout follow-up: Focus Rifle range ratings are (0.1, 1.0, 1.0, 1.0), with Focus ranked 3.6 and DMR 3.5. DMR+AR scores 0.91, DMR+Focus 0.92, and Focus+AR 0.98; an eligible ordinary Focus pickup replaces the DMR while retaining the AR (or shotgun). Power-fetch classification and unknown battery counts are unchanged. Other games retain their prior weapon ranks.

- Local follow-up: Reach AR Short-band proficiency is 0.8 (shotgun remains 1.0), and Reach's ordinary upgrade cutoff is 0.05 so DMR+shotgun is accepted over DMR+AR (gain 0.06). Applies across Reach difficulties; other games retain their existing values. Gameplay confirmation requires restarting the bot process.

- Local follow-up: Fixed Legendary and Demon power-weapon fetch calls cover 80 world units instead of 40, with a distance-based travel allowance for loose weapons. Lower difficulties and Scaling retain their existing range. Weapon classifications, urgency checks, and timed-spawn deadlines remain unchanged. Their tactical grenade policy remains. Gameplay confirmation is pending a bot-process restart.

- Local follow-up: Reach now supplies live magazine and total-ammo counts for recognized magazine-fed weapons; the bot remembers magazine maxima during combat too. DMR and sniper counts were verified against controlled shots, reloads, and sniper depletion. See CUSTOM_CHANGELOG.md for validation and remaining gameplay checks. Battery counts remain unknown.
- Local follow-up: A held sniper with any remaining total ammunition is exempt from low-ammo rearming. Empty-sniper behavior and deliberate upgrade decisions remain unchanged. Eight ammo/rearm regression tests passed; gameplay confirmation is pending a bot-process restart.
- Local follow-up: Breakpoint only. maps/reach_dlc_invasion/sight_open.json opens sight and shot rays under a thin overhead surface where the level export has no ground (the tower ledge to bridge gap), via Terrain.set_open_under. tools/test_breakpoint_sight.py covers it; live confirmation is pending.
- Local follow-up: LiDAR mode records vehicle drives and flights into maps/<map>/rides.json (tools/lidar.py RideWatch, as normal matches do), and the LiDAR 3D view shows stored and live drives in a "Vehicle drives" layer (key V). Deferred: Paint-page editing of recorded drives (eraser, vehicle-size tags). tools/test_lidar_drives.py covers it; a real LiDAR match is untested.
- Demon is now a real independent brain tier ("demon", extra None), retaining the numeric profile previously used by tuned Legendary. Difficulty tables/checks explicitly include Demon, including callouts, firing safeguards, landing tactics, fetch assignments, campaigns/Firefight and reporting. Native panel tier 5 / "for everyone" difficulty 6 remain unchanged; the collaborator's locally built Demon menu was already confirmed in game on 2026-11-06. This Python-side separation needs a bot-process restart and no native rebuild. tools/test_demon_difficulty.py and tools/test_difficulty_separation.py cover it.

- Demon radar and out-of-sight reasoning (2026-11-07): Demon reads each tracker dot's heading from its successive positions and sees unsuppressed shooters on the tracker even when crouched. brain/anticipate.py predicts where an unseen enemy went (heading, hidden cover, a quiet dot inside range means he crouched or stopped) for Demon's hunts and pre-aim. Bot.corner_plan holds the angle (random 1.2–2.8 s) and then swings wide instead of chasing a healthy enemy round a corner within 10 units; cracked, objective-carrying or fleeing targets are pushed. Demon-only; fight aim and protected head corrections are unchanged. tools/test_demon_anticipate.py covers it; gameplay is pending a bot-process restart.

- Visible-target firing hesitation near a balcony: head line of sight is suspected, not confirmed.
- The initial sniper miss-percentage proposal was implemented later: fixed Easy/Normal/Heroic use 10%/25%/50% intended sniper hits, as described above.
- Flight learning from demonstrations has NOT been implemented. The local companion vehicle recorder is excluded from this repository pending separate review.

## Baseline and backups

No earlier Git history or verified pristine source baseline exists for the customized installation. The first commit captures the installed state on 2026-11-05; do not claim it proves every historical edit. Local backups described by the handoff remain separate from the repository and are not uploaded.

Upstream migrations must also preserve the later sniper live-head change, which was backed up separately after the 0.2.1 migration.

## Current resource calls and Demon awareness

- Legendary flick overshoot is exactly zero across personalities; its other restored attributes and protected head/turret precision remain. Scaling keeps its own overshoot calculation.
- Demon sees within a 180-degree horizontal cone (90 degrees each side), with zero configured recognition delay throughout. Legendary retains its 120-degree cone. Sight range and line-of-sight restrictions remain; the 30 Hz loop still bounds processing.
- Demon always notices eligible motion-tracker contacts, bypassing the ordinary awareness probability. Tracker range, motion/crouching, jamming and match tracker settings remain enforced; this creates a radar belief, not visual confirmation. Other difficulties retain their radar probabilities.
- New power-weapon and power-vehicle calls use Demon → Legendary → Heroic/Scaling → Normal priority. Gunner calls use Demon → Legendary/Heroic/Scaling → Normal. Equal weights use distance. Easy retains existing eligibility rules; objective/urgency, range, timing, rider and availability checks remain.
- Power vehicles use the existing `not vehicles.taxi_ok(kind)` classification. Nearest vehicle/role choice is retained; the eligible driver for that power vehicle is then selected by difficulty, including eligible nearby objective bots within their original 15-unit limit. Ordinary transport/passenger/ferry choices remain unchanged.
- The owner confirmed deterministic eligible radar and clarified call priorities. Weapon fetches are reserved before vehicle orders; vehicle crews are assigned before honked/direct/aboard gunner calls. A Demon with an active weapon fetch or driver order is excluded from new gunner/pickup calls, and a Demon fetching a weapon is excluded from new driver calls. Without an eligible power assignment, Demon remains first for a gun seat. Changes need a bot-process restart and live testing; no automatic restart or GitHub push.

## Ordinary Mongoose transport follow-up

- Ordinary Mongoose is transport-only in the director's role table. A new director-assigned ride needs an eligible destination over 35 units away (or a race checkpoint), with the existing height/vehicle checks. Finishing a transport trip dismounts instead of creating another crew patrol.
- Explicit Mongoose jobs cover useful taxi travel, friendly carrier pickup/home delivery, and one CTF getaway ride per team. Carrier identity survives role reassignment. Idle/no-purpose trips and invalid carrier/getaway tasks end; races retain continuous checkpoint driving.
- Pickup waiting is 8 seconds within boarding range, getaway parking is 20 seconds, and automatic reboarding is cooled down for 30 seconds after an exit request. Each trip has a distance-based travel allowance, at least 60 seconds, which moving goals cannot repeatedly reset. These timer defaults were chosen for the owner's approved behavior.
- Emergency dodges and stuck reversing remain. An eligible infantry target within 18 units and 20 degrees ahead can be splattered on a taxi trip. Exit input uses the existing game's hold/retry mechanism. These changes cover the ordinary Mongoose in supported games, with regression coverage in tools/test_mongoose_transport.py. Restart the bot process and check gameplay.

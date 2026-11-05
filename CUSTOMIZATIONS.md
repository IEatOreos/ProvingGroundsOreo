# Custom Legendary bots

This is a custom derivative of [Project Proving Grounds](https://github.com/AyoItzKye/project-proving-grounds), based on the installed upstream version 0.2.1. Original credits and licensing remain in LICENSE.md and NOTICE.md. This repository is not the upstream author's official release.

The original README.md documents the upstream mod, and its download and issue links point to upstream. Custom release details belong in CUSTOM_CHANGELOG.md and docs/CUSTOM_RELEASE_WORKFLOW.md. VERSION retains the upstream version; CUSTOM_VERSION identifies our derivative.

## Retained behavior at the initial snapshot

The following inventory comes from the customization handoff. It is not a verified historical diff. Most changes target fixed Legendary (`tier == "top" and extra is None`), distinct from Scaling difficulty.

- Precision profile: aim_err=0, lag=0.001, track=0.001, overshoot=0, lead=0, flick=0.05, reaction=1/30 second, turn=1000 degrees/second.
- Fixed Legendary has no randomized under/over-leading, hand wobble, or own-movement prediction. It normally aims for the head; the assault rifle targets the chest.
- Final fixed Legendary DMR and sniper shot direction uses the Reach Spartan's live animated head marker, with a fallback when unavailable. The sniper keeps its normal alignment and cadence checks. DMR behavior was confirmed in gameplay; the sniper extension still needs gameplay confirmation according to the handoff.
- Fixed Legendary grenades remain enabled, excluding fight-opening and random visible-enemy pressure throws. Tactical grenade uses remain.
- Shared post-grenade firing retries include semiautomatic trigger releases. The two-second retry window is not a mandatory delay. Actual weapon recovery timing remains unresolved.
- Fixed Legendary detection uses a 120-degree horizontal cone. Reaction takes 50% longer between 50 and 60 degrees from center. Normal and Scaling retain their original FOV settings. Sight range remains 80 world units.
- Radar was investigated but not customized.

Primary integration files: brain/bot.py, brain/profiles.py, brain/core.py, brain/live.py, brain/terrain.py, tools/live_bots.py.

## Open investigations and proposals

- Visible-target firing hesitation near a balcony: head line of sight is suspected, not confirmed.
- Sniper miss percentages were discussed but have NOT been implemented.
- Flight learning from demonstrations has NOT been implemented. The local companion vehicle recorder is excluded from this repository pending separate review.

## Baseline and backups

No earlier Git history or verified pristine source baseline exists for the customized installation. The first commit captures the installed state on 2026-11-05; do not claim it proves every historical edit. Local backups described by the handoff remain separate from the repository and are not uploaded.

Upstream migrations must also preserve the later sniper live-head change, which was backed up separately after the 0.2.1 migration.

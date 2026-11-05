# Custom Project Proving Grounds workflow

This is a customized installation based on upstream Project Proving Grounds 0.2.1.
Read CUSTOMIZATIONS.md and docs/CUSTOM_RELEASE_WORKFLOW.md before making changes.

- Make small targeted changes. Preserve upstream logic and license notices.
- Fixed Legendary means `tier == "top" and extra is None`; Scaling also uses top.
- Preserve the DMR and sniper live animated head corrections unless explicitly asked to change them.
- Preserve exact changes in Git and describe changes and validation in CUSTOM_CHANGELOG.md.
- Do not stage unrelated user changes or recordings, machine settings, game-derived exports, credentials, installers, or bundled runtimes.
- Restart the bot process/launcher after Python changes when appropriate; coordinate around an active match.
- Local preparation and validation are allowed. The user must explicitly approve each GitHub push, published tag, release, or uploaded artifact. Approval of one upload does not authorize later uploads.
- Batch several meaningful updates into a release; suggest a release checkpoint after approximately three updates, without publishing automatically.
- Before requesting publication approval, prepare the actual diff, version, changelog, checks, and intended destination. Report untested gameplay behavior accurately.
- Migrate upstream updates by reading the new source and merging individual customizations. Never overwrite an upstream update with old full files.

The first local commit is an installed-state snapshot, not verified pristine upstream source or a reconstruction of past edits.

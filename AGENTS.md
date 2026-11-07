# Custom Project Proving Grounds workflow

This is a customized installation based on upstream Project Proving Grounds 0.2.2-s181.
Read CUSTOMIZATIONS.md and docs/CUSTOM_RELEASE_WORKFLOW.md before making changes.

- Make small targeted changes. Preserve upstream logic and license notices.
- Fixed Legendary means `tier == "top" and extra is None`; Demon now has its own `tier == "demon"` with extra None. Use profiles.fixed_high for their shared rules and profiles.fixed_demon for Demon's precision/timing overrides. Scaling still uses top with extra populated and must remain excluded from fixed-tier overrides.
- Preserve Legendary/Demon DMR and sniper live animated head corrections and the protected head/turret precision contexts unless explicitly asked to change them. Legendary base attributes are restored to upstream defaults; Demon retains the prior tuned numeric profile.
- Preserve exact changes in Git and describe changes and validation in CUSTOM_CHANGELOG.md.
- Do not stage unrelated user changes or recordings, machine settings, game-derived exports, credentials, installers, or bundled runtimes.
- Restart the bot process/launcher after Python changes when appropriate; coordinate around an active match.
- Local preparation and validation are allowed. The user must explicitly approve each GitHub push, published tag, release, or uploaded artifact. Approval of one upload does not authorize later uploads.
- Batch several meaningful updates into a release; suggest a release checkpoint after approximately three updates, without publishing automatically.
- Before requesting publication approval, prepare the actual diff, version, changelog, checks, and intended destination. Report untested gameplay behavior accurately.
- Preserve the owner's coding collaborator's commits and intended behavior. Before preparing any push, fetch the latest remote history, review incoming and overlapping changes, and integrate them with a normal merge that preserves the existing commit identities. Do not force-push, rewrite published history, discard collaborator work, or replace newer files with older copies. Resolve conflicts by preserving both intended changes; ask the owner when the intentions cannot be reconciled safely. A normal push must descend from the current remote head; if the remote advances, fetch and integrate again before retrying.
- Treat the owner's collaborator as a teammate working both locally and remotely. Before every push, inspect the local HEAD, outgoing commits, staged/unstaged changes and new files as well as fetched GitHub changes. Do not assume an additional unpublished teammate feature is approved merely because it precedes our commit. Review it, report the combined upload scope, and obtain the owner's approval if it exceeds the requested update. Recheck for concurrent local/remote changes immediately before publication and push only the reviewed commit; never silently include new teammate work or overwrite their in-progress files.
- Migrate upstream updates by reading the new source and merging individual customizations. Never overwrite an upstream update with old full files.

The first local commit is an installed-state snapshot, not verified pristine upstream source or a reconstruction of past edits.

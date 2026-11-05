# Custom release workflow

## Repository setup

Use a private GitHub repository, as requested by the user. The account/organization and final repository name must be confirmed before creating the remote. Suggested name: project-proving-grounds-custom. Keep upstream attribution and the existing license and notices.

## Each update

1. Inspect the working tree and preserve unrelated changes. Make a targeted change.
2. Validate the affected code and record any required in-game testing. Do not claim gameplay checks from compilation alone.
3. Update CUSTOM_CHANGELOG.md with behavior, affected files, validation, and known limitations.
4. Make a local commit for the completed change. Git history records exact edits from this baseline onward. Keep independent backups where appropriate.
5. Remind the user to restart the bot process/launcher for changed Python code, coordinating around active matches.

## Release checkpoint

After approximately three meaningful updates, or when the user asks, prepare a candidate release. This count is a reminder, not permission to publish.

1. Review the full diff since the last approved version and inspect files for private data and oversized artifacts.
2. Set CUSTOM_VERSION and finalize the matching changelog entry. Preserve VERSION for the upstream version unless the upstream integration explicitly requires otherwise.
3. Run relevant checks and prepare a concrete summary with the target repository, version, changes, files/artifacts to upload, and remaining gameplay checks.
4. Ask for explicit approval to push that exact candidate and, separately if applicable, publish its GitHub release. Do not push, upload, publish tags, or create public releases before approval.
5. After approval, push only the approved commits to the confirmed private repository. Publish a release/tag only when included in that approval. Verify the remote commit and links, then record the result.

Initial publication follows the same approval gate. No automation should push on a timer or after a commit count.

## Upstream updates

Keep upstream updates identifiable separately from our customization commits. Read the new upstream files, merge retained behavior individually, validate it, and record upstream version and unresolved tests. Never reconstruct a supposed pristine upstream baseline from this installed-state snapshot.

## Distribution scope

This is initially a source repository, not a complete installer or self-contained game mod distribution. The installed runtime, native build outputs, optional map pack, machine settings, and recorder are excluded. Review build reproducibility and packaging before offering installable custom releases; the upstream installation documentation may require tools absent from this installation's source snapshot.

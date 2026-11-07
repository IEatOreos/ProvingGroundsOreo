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

1. Fetch the latest remote history and review the owner's collaborator's incoming commits before preparing the candidate. Integrate those commits while preserving their identities and intended behavior, then review the full diff since the last approved version and inspect files for private data and oversized artifacts.
2. Set CUSTOM_VERSION and finalize the matching changelog entry. Preserve VERSION for the upstream version unless the upstream integration explicitly requires otherwise.
3. Run relevant checks and prepare a concrete summary with the target repository, version, changes, files/artifacts to upload, and remaining gameplay checks.
4. Ask for explicit approval to push that exact candidate and, separately if applicable, publish its GitHub release. Do not push, upload, publish tags, or create public releases before approval.
5. After approval, push only the approved candidate to the confirmed private repository using a normal push. The candidate must descend from the current remote head. If the remote has advanced, fetch, integrate, and revalidate before retrying; obtain approval again if the candidate changes materially. Publish a release/tag only when included in that approval. Verify the remote commit and links, then record the result.

Initial publication follows the same approval gate. No automation should push on a timer or after a commit count.

## Preserve collaborator work

The owner reiterated on 2026-11-06 that this is a team workflow: check the collaborator's local work as well as GitHub before publishing. Inspect local HEAD and all outgoing commits, staged/unstaged changes and new files, then fetch and review remote changes. A pending teammate commit is not automatically approved for upload just because it is an ancestor of our change. Explain the combined candidate and confirm any additional feature outside the requested upload before pushing. Preserve in-progress files and commit identities. Immediately before publication, recheck local/remote state; publish only the reviewed commit so a concurrently advanced local branch cannot silently add unreviewed changes.

The owner explicitly requires preserving the coding collaborator's commits and changes. Review both histories and overlapping file edits before integration. Use normal merges that retain existing commit identities; do not rebase published collaborator commits, force-push, reset away their work, or copy older whole files over newer versions. A preserved commit in history is not sufficient if conflict resolution silently removes its behavior: reconcile the actual code and run relevant checks. Ask the owner when conflicting intentions cannot be reconciled. Do not stage or alter unrelated work in the shared installation.

## Upstream updates

Keep upstream updates identifiable separately from our customization commits. Read the new upstream files, merge retained behavior individually, validate it, and record upstream version and unresolved tests. Never reconstruct a supposed pristine upstream baseline from this installed-state snapshot.

## Distribution scope

This is initially a source repository, not a complete installer or self-contained game mod distribution. The installed runtime, native build outputs, optional map pack, machine settings, and recorder are excluded. Review build reproducibility and packaging before offering installable custom releases; the upstream installation documentation may require tools absent from this installation's source snapshot.

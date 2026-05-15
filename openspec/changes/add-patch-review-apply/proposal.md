## Why

Milestone 3 can generate and validate unified diffs, but the agent still cannot perform the next controlled editing step in the MVP loop. Milestone 4 adds the safety gate between generated patches and repository modification: deterministic review, dry-run application, actual application, and git diff reporting.

## What Changes

- Add Patch Review behavior that approves or rejects generated unified diffs before application.
- Add controlled Patch Apply behavior that requires review approval and runs a dry-run check before modifying files.
- Add Git Diff reporting that summarizes changed files and the resulting working tree diff after application.
- Add an apply-mode LangGraph workflow and `codeflow apply` CLI command that reuses Plan Mode and Patch Mode stages before review and application.
- Keep patch application limited to existing repository-relative files and structured failure results.
- Do not add pytest execution, retry loops, commits, resets, arbitrary shell execution, or direct file overwrite fallback in this milestone.

## Capabilities

### New Capabilities
- `patch-review-apply`: Reviews generated unified diffs, applies approved patches through a dry-run guarded path, and reports the resulting git diff.

### Modified Capabilities

## Impact

- Affected runtime modules: `state`, patch validation/review/apply helpers, git diff tooling, apply-mode workflow, and CLI dispatch.
- Affected tests: add review, dry-run, apply, git diff, workflow, and CLI coverage for the calculator demo fixture.
- External local systems: use controlled `git apply` and `git diff` subprocess calls with `shell=False`.
- Dependencies: no new third-party runtime framework is proposed.

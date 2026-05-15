## 1. State and Contracts

- [x] 1.1 Extend workflow state with `patch_review`, `apply_result`, and `git_diff` fields.
- [x] 1.2 Document Apply Mode node read/write fields in a `NODE_IO` map.
- [x] 1.3 Keep existing Plan Mode and Patch Mode behavior unchanged.

## 2. Patch Review Tooling

- [x] 2.1 Add a `review_patch` helper that reuses generated patch validation and returns a structured `ToolResult`.
- [x] 2.2 Enforce conservative review limits for patch bytes, changed file count, and changed line count.
- [x] 2.3 Reject Markdown fences, absolute paths, path traversal, forbidden paths, and out-of-plan paths through review tests.
- [x] 2.4 Record approved review data with `approved`, `changed_files`, and a compact summary.

## 3. Patch Application and Git Diff Tools

- [x] 3.1 Add an `apply_patch` tool that refuses to run without review approval.
- [x] 3.2 Run `git apply --check --whitespace=nowarn` before any repository modification.
- [x] 3.3 Run `git apply --whitespace=nowarn` only after the dry-run succeeds.
- [x] 3.4 Use `subprocess.run` with `shell=False`, `cwd=repo_root`, patch content on stdin, and a timeout.
- [x] 3.5 Return structured failures for missing repo roots, non-Git repos, dry-run failures, apply failures, and timeouts.
- [x] 3.6 Add a `git_diff` tool that reports changed files and compact diff statistics with length-limited output.

## 4. Apply Mode Workflow

- [x] 4.1 Add an Apply Mode LangGraph workflow that reuses analysis, context, planning, patch generation, and validation nodes.
- [x] 4.2 Add `review_patch`, `apply_patch`, `git_diff`, and final summary nodes with explicit conditional edges.
- [x] 4.3 Stop before application when patch review fails.
- [x] 4.4 Stop before git diff reporting when patch application fails.
- [x] 4.5 Return `ToolResult` data containing status, plan, patch, patch review, apply result, git diff, error summary, and final output.

## 5. CLI and Documentation

- [x] 5.1 Add `codeflow apply --repo <repo> <task>` CLI dispatch.
- [x] 5.2 Update README current status and CLI shape for Milestone 4.
- [x] 5.3 Update `docs/architecture.md` to include Patch Review and Apply modules and workflow status.
- [x] 5.4 Update `docs/roadmap.md` to mark Milestone 4 acceptance criteria when implementation is complete.

## 6. Tests and Verification

- [x] 6.1 Add unit tests for patch review acceptance and rejection cases.
- [x] 6.2 Add unit tests for dry-run required behavior and refusal without review approval.
- [x] 6.3 Add integration tests for successful apply against an isolated copy of the calculator demo fixture.
- [x] 6.4 Add tests for git diff changed files and compact summary output.
- [x] 6.5 Add CLI test coverage for `codeflow apply` JSON `ToolResult` output.
- [x] 6.6 Verify the main test suite with `python -m pytest -q`.

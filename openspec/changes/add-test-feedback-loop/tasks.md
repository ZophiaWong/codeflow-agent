## 1. State and Test Tooling

- [x] 1.1 Extend workflow state with `test_result`, `iteration_count`, and `max_iterations`.
- [x] 1.2 Add a controlled `run_tests` tool for the default pytest command shape.
- [x] 1.3 Enforce `shell=False`, repository working directory, timeout, and command allowlist.
- [x] 1.4 Return compact structured test output and summaries.

## 2. Fix Mode Workflow

- [x] 2.1 Add a LangGraph-backed Fix Mode workflow that reuses Plan, Patch, and Apply behavior.
- [x] 2.2 Add `run_tests`, `analyze_result`, `prepare_retry`, and final summary nodes.
- [x] 2.3 Route passing tests to `status = success`.
- [x] 2.4 Route failing tests into bounded retry while attempts remain.
- [x] 2.5 Return `status = failed` when retry limit is reached.

## 3. CLI and Documentation

- [x] 3.1 Add `codeflow fix --repo <repo> <task>` CLI dispatch.
- [x] 3.2 Update README for Milestone 5 status and CLI shape.
- [x] 3.3 Update `docs/architecture.md` with test runner and Fix Mode.
- [x] 3.4 Update `docs/roadmap.md` to mark Milestone 5 complete.

## 4. Tests and Verification

- [x] 4.1 Add unit tests for controlled pytest execution.
- [x] 4.2 Add workflow tests for success, no-change, retry, and retry exhaustion.
- [x] 4.3 Add CLI coverage for `codeflow fix`.
- [x] 4.4 Verify the main test suite with `python -m pytest -q`.

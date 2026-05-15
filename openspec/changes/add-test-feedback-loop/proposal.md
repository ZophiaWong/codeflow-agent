## Why

Milestone 4 can review and apply patches, but the agent still cannot verify changes or use test feedback. Milestone 5 completes the verification loop by running controlled pytest, summarizing failures, and retrying within a strict bound.

## What Changes

- Add a controlled `run_tests` tool for the default pytest command.
- Add Fix Mode through `codeflow fix`, reusing planning, patch generation, review, apply, and git diff behavior.
- Add test result analysis, compact failure summaries, and bounded retry state.
- Feed failed test results back into patch generation for one retry by default.
- Do not add arbitrary commands, dependency installation, reset/checkout rollback, commits, Multi-Agent roles, or benchmark features.

## Capabilities

### New Capabilities
- `test-feedback-loop`: Runs allowlisted pytest verification after patch application and performs bounded retry from compact test feedback.

### Modified Capabilities

## Impact

- Affected runtime modules: workflow state, patch generation seam, test runner, Fix Mode workflow, and CLI dispatch.
- Affected tests: controlled pytest execution, retry routing, retry exhaustion, and `codeflow fix` JSON output.
- External local systems: pytest subprocess execution with `shell=False` and a timeout.
- Dependencies: no new third-party runtime framework is proposed.

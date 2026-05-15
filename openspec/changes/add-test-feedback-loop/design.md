## Context

Codeflow-agent currently supports read-only repository inspection, planning, patch generation, patch review, controlled patch application, and git diff reporting. The next MVP step is verification: run tests after patch application and use compact feedback for a bounded retry.

The project rules require a single-agent LangGraph workflow, structured tool results, allowlisted subprocess commands, `shell=False`, timeouts, compact state, and no automatic reset, checkout, commit, dependency installation, or direct file overwrite fallback.

## Goals / Non-Goals

**Goals:**

- Add controlled pytest execution after successful patch application.
- Add structured test result analysis and compact failure summaries.
- Add bounded retry using `iteration_count` and `max_iterations`.
- Add `codeflow fix` as the first test-verified workflow command.
- Preserve Plan Mode, Patch Mode, and Apply Mode behavior.

**Non-Goals:**

- Do not add arbitrary shell execution or custom command execution.
- Do not install dependencies automatically.
- Do not reset, checkout, commit, or roll back Git state automatically.
- Do not delete or weaken tests.
- Do not add Multi-Agent testing roles or benchmark harnesses.

## Decisions

### Decision 1: Add Fix Mode Instead of Extending Apply Mode

Fix Mode reuses the Plan, Patch, and Apply nodes, then adds `run_tests`, `analyze_result`, `prepare_retry`, and final summary behavior.

Rationale: Apply Mode remains a useful write-only milestone command, while Fix Mode owns verification and retry.

### Decision 2: Use a Strict Pytest Allowlist

The test tool supports only the default pytest command shape, `python -m pytest -q`, and executes it with `shell=False`, `cwd=repo_root`, and a timeout.

Rationale: this satisfies the MVP verification need without introducing arbitrary shell execution.

### Decision 3: Retry Is Incremental and Bounded

Fix Mode defaults to `max_iterations = 2`: initial patch plus one retry. It does not reset or checkout after failed tests; retry patches are generated against the current working tree.

Rationale: automatic reset/checkout is a hard non-goal, so retry must work as an incremental patch loop.

## Risks / Trade-offs

- Failed retry may leave partial changes in the working tree -> Mitigation: report final failure and git diff; do not reset automatically.
- Local environments may not expose `python` on PATH -> Mitigation: keep the public command shape as `python -m pytest -q` while executing with the current interpreter when resolving the default command internally.
- Test logs may be large -> Mitigation: store length-limited stdout/stderr and a compact summary.

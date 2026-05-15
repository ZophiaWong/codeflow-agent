# Codeflow-agent Roadmap

This roadmap defines the implementation sequence for the Codeflow-agent MVP.

The roadmap is intentionally milestone-based. Each milestone should produce a small, runnable, testable increment. Do not skip ahead to patching, testing, or Multi-Agent features before the earlier milestones are stable.

## 1. Roadmap Principles

Development must follow these principles:

- Build small increments.
- Keep each milestone runnable.
- Keep each milestone testable.
- Implement read-only repository capabilities before write capabilities.
- Implement planning before patch generation.
- Implement patch review before patch application.
- Implement verification only after patch application is controlled.
- Keep retries bounded.
- Do not implement post-MVP features during MVP milestones.
- Do not introduce new frameworks without explicit approval.

## 2. Status Values

Use the following status values:

| Status        | Meaning                                                   |
| ------------- | --------------------------------------------------------- |
| `not_started` | No implementation work has started                        |
| `in_progress` | Work has started but acceptance criteria are not complete |
| `done`        | Acceptance criteria are complete and tested               |
| `deferred`    | Intentionally postponed                                   |

## 3. Milestone Overview

| Milestone | Name                        | Status        |
| --------- | --------------------------- | ------------- |
| 1         | Read-only Repo Agent        | `done`        |
| 2         | Plan Mode                   | `done`        |
| 3         | Patch Generation            | `done`        |
| 4         | Patch Review and Apply      | `done`        |
| 5         | Run Tests and Feedback Loop | `done`        |
| 6         | Minimal Demo                | `not_started` |

## 4. Milestone 1: Read-only Repo Agent

Status: `done`

### Goal

Create the read-only foundation for Codeflow-agent.

The agent should be able to inspect a repository, list files, read files, search code, and answer basic repository-structure questions without modifying anything.

### Scope

Implement:

- minimal project scaffold;
- shared `ToolResult` contract;
- safe path utilities;
- `list_files`;
- `read_file`;
- `search_code`;
- minimal CLI commands for read-only inspection;
- pytest coverage for all read-only tools.

Suggested early CLI commands:

```text
codeflow inspect --repo ./examples/calculator_bug
codeflow search --repo ./examples/calculator_bug add
codeflow read --repo ./examples/calculator_bug src/calculator.py
```

### Acceptance Criteria

- [x] The package can be installed or run locally.
- [x] `ToolResult` exists and is used by tools.
- [x] Safe path utilities reject paths outside `repo_root`.
- [x] `list_files` lists allowed repository files.
- [x] `list_files` ignores forbidden directories such as `.git`, `.venv`, `__pycache__`, and `.pytest_cache`.
- [x] `read_file` reads text files inside `repo_root`.
- [x] `read_file` rejects missing files, binary files, and path traversal.
- [x] `search_code` returns matching file paths, line numbers, and snippets.
- [x] Tool output is length-limited or summarized.
- [x] All tools have explicit failure returns.
- [x] No command modifies repository files.
- [x] Tool-level tests pass.

### Delivered Behavior

Milestone 1 added the `codeflow_agent` package, `ToolResult`, safe path utilities,
read-only repository tools, the minimal `codeflow` CLI, and the
`examples/calculator_bug` fixture. The `search_code` implementation is pure
Python for now; `ripgrep` is not required for Milestone 1 and can be introduced
later as an optional adapter behind the same tool contract.

Project pytest configuration collects only the main `tests/` directory so the
demo fixture tests are not collected accidentally.

### Non-goals

Do not implement:

- LLM calls;
- LangGraph workflow;
- planning;
- patch generation;
- patch review;
- patch application;
- test execution;
- retry loop;
- Multi-Agent features.

## 5. Milestone 2: Plan Mode

Status: `done`

### Goal

Add a planning-only workflow.

Given a development task, Codeflow-agent should analyze the task, build repository context, and produce a change plan without generating or applying a patch.

### Scope

Implement:

- `Analyze Task` node;
- `Build Repo Context` node using read-only tools;
- `Plan Changes` node;
- minimal AgentState shape for planning;
- plan-mode CLI command;
- tests using fake or stubbed LLM outputs.

A planned CLI shape:

```text
codeflow plan --repo ./examples/calculator_bug "Fix add() for negative numbers"
```

### Acceptance Criteria

- [x] The agent can classify whether a task likely needs code changes.
- [x] The agent can build relevant repository context from read-only tools.
- [x] The plan includes target files, intended change, and validation strategy.
- [x] Plan Mode does not generate patches.
- [x] Plan Mode does not modify files.
- [x] Running Plan Mode leaves `git diff` empty.
- [x] Node-level tests pass.

### Delivered Behavior

Milestone 2 added a LangGraph-backed planning workflow with `Analyze Task`,
`Build Repo Context`, `Plan Changes`, and final summary nodes. The planner is an
injectable deterministic seam for now, so tests do not depend on real LLM calls
or provider configuration.

The `codeflow plan` command returns JSON `ToolResult` output and performs only
read-only repository inspection.

### Non-goals

Do not implement:

- patch generation;
- patch review;
- patch application;
- pytest execution;
- retry loop;
- Multi-Agent roles.

## 6. Milestone 3: Patch Generation

Status: `done`

### Goal

Generate unified diff patches from a plan and repository context without applying them.

### Scope

Implement:

- `Generate Patch` node;
- patch format validation helper;
- patch-mode CLI command;
- tests with fake or stubbed LLM patch output.

A planned CLI shape:

```text
codeflow patch --repo ./examples/calculator_bug "Fix add() for negative numbers"
```

### Acceptance Criteria

- [x] The agent can generate a unified diff patch.
- [x] The patch uses repository-relative paths.
- [x] The patch does not contain Markdown code fences.
- [x] The patch is scoped to the plan.
- [x] Invalid patch format is detected.
- [x] Empty patch output is detected.
- [x] Patch Mode does not modify files.
- [x] Running Patch Mode leaves `git diff` empty.
- [x] Patch generation tests pass.

### Delivered Behavior

Milestone 3 added a LangGraph-backed Patch Mode that reuses Plan Mode, generates
a unified diff through an injectable deterministic patch generator, and validates
the generated patch for format, path safety, and plan scope.

The `codeflow patch` command returns JSON `ToolResult` output and does not apply
patches, run pytest, or modify repository files.

### Non-goals

Do not implement:

- patch application;
- pytest execution;
- retry loop based on test results;
- direct file overwrite;
- new file or delete-file support unless explicitly approved.

## 7. Milestone 4: Patch Review and Apply

Status: `done`

### Goal

Review generated patches, apply approved patches, and report the resulting git diff.

### Scope

Implement:

- `Review Patch` node;
- deterministic patch review checks;
- `Apply Patch` node;
- `Git Diff` node;
- `review_patch` tool;
- `apply_patch` tool;
- `git_diff` tool;
- apply-mode CLI command.

A planned CLI shape:

```text
codeflow apply --repo ./examples/calculator_bug "Fix add() for negative numbers"
```

### Acceptance Criteria

- [x] `review_patch` accepts valid unified diffs.
- [x] `review_patch` rejects Markdown-wrapped patches.
- [x] `review_patch` rejects absolute paths.
- [x] `review_patch` rejects `../` path traversal.
- [x] `review_patch` rejects forbidden paths.
- [x] `review_patch` rejects overly large patches.
- [x] `apply_patch` requires review approval.
- [x] `apply_patch` runs a dry-run check before application.
- [x] Approved patches can be applied successfully.
- [x] `git_diff` reports changed files and diff summary.
- [x] Patch application failure is reported through structured state.
- [x] Tests for review and apply pass.

### Delivered Behavior

Milestone 4 added a LangGraph-backed Apply Mode that reuses Plan Mode and Patch
Mode, reviews generated patches with deterministic limits, runs a dry-run Git
apply check, applies approved patches, and reports a compact git diff summary.

The `codeflow apply` command returns JSON `ToolResult` output and is the first
write-capable CLI command. It does not run pytest, retry, commit, reset, or
fall back to direct file overwrites.

### Non-goals

Do not implement:

- pytest execution;
- test feedback retry;
- automatic git commit;
- automatic git reset;
- arbitrary shell execution;
- direct file overwrite fallback.

## 8. Milestone 5: Run Tests and Feedback Loop

Status: `done`

### Goal

Run controlled tests after patch application and use test feedback for bounded retry.

### Scope

Implement:

- `Run Tests` node;
- `Analyze Result` node;
- `run_tests` tool;
- pytest output summarization;
- retry control through `iteration_count` and `max_iterations`;
- failure and success final summary paths.

A planned CLI shape:

```text
codeflow fix --repo ./examples/calculator_bug "Fix add() for negative numbers"
```

### Acceptance Criteria

- [x] `run_tests` supports the default command `python -m pytest -q`.
- [x] Test command execution uses `shell=False`.
- [x] Test command execution has a timeout.
- [x] Disallowed commands are rejected.
- [x] Passing tests produce `status = success`.
- [x] Failing tests produce a compact `error_summary`.
- [x] Test failure can feed back into patch generation.
- [x] Retry count is bounded.
- [x] Reaching the retry limit produces `status = failed`.
- [x] The agent never reports success when tests fail.
- [x] Tests for run, failure summary, and retry routing pass.

### Delivered Behavior

Milestone 5 added a LangGraph-backed Fix Mode that reuses Plan, Patch, and
Apply Mode behavior, runs controlled pytest after patch application, analyzes
the result, and retries once by default when tests fail.

The `run_tests` tool allows only the default pytest command shape, executes with
`shell=False`, enforces a timeout, and stores compact test output in state.

The `codeflow fix` command returns JSON `ToolResult` output with final status,
git diff summary, test result, retry count, and final output. Failed-test retry
is bounded and does not use automatic `git reset` or `git checkout`.

### Non-goals

Do not implement:

- arbitrary shell execution;
- dependency installation;
- test deletion or weakening;
- hardcoded outputs to satisfy tests;
- Multi-Agent testing roles;
- benchmark platform.

## 9. Milestone 6: Minimal Demo

Status: `not_started`

### Goal

Create and demonstrate the full MVP loop on a small Python repository.

### Scope

Implement or prepare:

- use the existing `examples/calculator_bug` fixture from Milestone 1;
- a failing test for the initial bug;
- full `codeflow fix` demo;
- success-path demonstration;
- failure-path demonstration;
- concise project documentation updates if needed.

### Demo Scenario

Repository:

```text
examples/calculator_bug
```

Files:

```text
src/calculator.py
tests/test_calculator.py
```

Initial bug:

```text
add(-1, -2) returns 3 instead of -3
```

User task:

```text
Fix add() so it handles negative numbers correctly.
```

### Acceptance Criteria

- [ ] The demo starts with at least one failing pytest test.
- [ ] Codeflow-agent locates relevant code.
- [ ] Codeflow-agent produces a plan.
- [ ] Codeflow-agent generates a patch.
- [ ] Codeflow-agent reviews and applies the patch.
- [ ] Codeflow-agent runs pytest.
- [ ] pytest passes after the fix.
- [ ] Final summary reports changed files and test results.
- [ ] A failure-path demo fails safely without random code changes.

### Non-goals

Do not implement:

- additional complex demos;
- large repository support;
- full evaluation harness;
- Multi-Agent orchestration;
- MCP integration;
- IDE integration.

## 10. Post-MVP Roadmap

Post-MVP features may be considered only after the single-agent MVP is stable.

Possible sequence:

| Version | Direction                              |
| ------- | -------------------------------------- |
| V2      | Add Reviewer Agent                     |
| V3      | Add Tester Agent                       |
| V4      | Split Planner and Coder                |
| V5      | Add Coordinator for role orchestration |

Post-MVP work must remain artifact-driven.

Agents should exchange structured artifacts such as:

```text
plan
patch
patch_review
test_result
final_summary
```

Avoid free-form multi-agent conversation without clear artifacts.

## 11. Deferred Ideas

The following ideas are deferred:

- MCP integration;
- IDE plugin;
- cloud execution;
- vector database retrieval;
- full benchmark platform;
- advanced checkpoint and rollback;
- multi-language repository support;
- long-term memory;
- automatic dependency management;
- automatic git commit workflow.

Deferred ideas are not part of MVP implementation.

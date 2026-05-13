# Codeflow-agent

Codeflow-agent is a minimal coding agent for local code repositories.

It is designed to demonstrate the core engineering patterns behind agentic coding tools: repository inspection, context building, planning, patch-based editing, controlled tool use, test-based verification, bounded retry, and explainable final reporting.

The MVP is intentionally small. It starts as a single-agent LangGraph workflow and focuses on making the main coding-agent loop reliable before adding any Multi-Agent extensions.

## MVP Scope

The MVP will support the following workflow:

```text
User Task
→ Analyze Task
→ Build Repo Context
→ Plan Changes
→ Generate Patch
→ Review Patch
→ Apply Patch
→ Run Tests
→ Analyze Result
→ Retry or Final Summary
```

The MVP must be able to:

- inspect a local repository;
- list files, read files, and search code;
- build a compact repository context;
- generate a change plan;
- generate a unified diff patch;
- review the patch before applying it;
- apply approved patches only;
- run a controlled pytest command;
- retry within a bounded limit when verification fails;
- produce a final `success`, `failed`, or `no_change` summary.

## What This Project Is Not

Codeflow-agent is not:

- a general chatbot;
- a plain RAG application;
- a full IDE assistant;
- a cloud execution system;
- a benchmark platform;
- a full Multi-Agent system in the MVP;
- an arbitrary shell automation agent.

The MVP must not allow the LLM to directly overwrite files. All code changes must go through unified diff patches, patch review, dry-run validation, and controlled application.

## Current Status

Status: Milestone 1 complete.

The project now has a runnable read-only repository inspection foundation:

- installable package scaffold under `src/codeflow_agent/`;
- structured `ToolResult` responses for read-only tools;
- safe repository-local path handling;
- pure-Python `list_files`, `read_file`, and `search_code` tools;
- minimal read-only CLI commands: `inspect`, `read`, and `search`;
- `examples/calculator_bug` as the stable demo fixture;
- pytest configured to collect only the main `tests/` directory.

The next implementation target is:

```text
Milestone 2: Plan Mode
```

See `docs/roadmap.md` for the current roadmap.

## CLI Shape

Milestone 1 exposes read-only repository inspection commands:

```text
codeflow inspect --repo ./examples/calculator_bug
codeflow search --repo ./examples/calculator_bug add
codeflow read --repo ./examples/calculator_bug src/calculator.py
```

Later milestones will add the full fix flow. The intended final MVP interaction is:

```text
codeflow fix --repo ./examples/calculator_bug "Fix add() for negative numbers"
```

## Minimal Demo

The recommended demo repository is:

```text
examples/calculator_bug
```

The demo contains:

```text
src/calculator.py
tests/test_calculator.py
```

Initial bug:

```text
add(-1, -2)
```

Expected result:

```text
-3
```

Incorrect result:

```text
3
```

The current M1 demo supports read-only inspection only. The final MVP demo should show the full loop:

```text
analyze task
→ locate relevant code
→ plan change
→ generate patch
→ review patch
→ apply patch
→ run pytest
→ summarize result
```

The demo is successful when pytest passes and the final summary reports the changed file, the change made, and the test result.

## Documentation

Project documentation:

| File                   | Purpose                                                                         |
| ---------------------- | ------------------------------------------------------------------------------- |
| `docs/mvp-spec.md`     | MVP scope, non-goals, input/output, demo, and Definition of Done                |
| `docs/architecture.md` | Top-level architecture map, domain boundaries, runtime workflow, and invariants |
| `docs/roadmap.md`      | Milestone plan and implementation sequence                                      |
| `AGENTS.md`            | Short, strict implementation rules for AI coding tools                          |

Read order:

```text
README.md
→ docs/mvp-spec.md
→ docs/architecture.md
→ docs/roadmap.md
→ AGENTS.md
```

## Development Principles

Implementation should follow these principles:

- Build in small steps.
- Keep every step runnable.
- Keep every step testable.
- Start with read-only repository tools.
- Add planning before patch generation.
- Add patch review before patch application.
- Add verification only after patch application is controlled.
- Do not introduce new frameworks without a clear need.
- Do not expand the MVP while implementing a milestone.

## Roadmap Summary

The MVP roadmap is:

```text
Milestone 1: Read-only Repo Agent (done)
Milestone 2: Plan Mode
Milestone 3: Patch Generation
Milestone 4: Patch Review and Apply
Milestone 5: Run Tests and Feedback Loop
Milestone 6: Minimal Demo
```

Post-MVP work may introduce role separation such as Reviewer, Tester, Planner, Coder, and Coordinator, but these are not part of the MVP.

## Development Rules

Before making implementation changes, check:

```text
AGENTS.md
docs/mvp-spec.md
docs/architecture.md
docs/roadmap.md
```

When in doubt:

```text
Do less.
Keep the change smaller.
Do not expand MVP scope.
```

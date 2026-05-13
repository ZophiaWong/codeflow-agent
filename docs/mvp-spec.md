# Codeflow-agent MVP Specification

## 1. Project Positioning

Codeflow-agent is a minimal coding agent for local code repositories.

The project is designed to demonstrate the core engineering patterns behind agentic coding tools: repository understanding, context construction, planning, patch-based editing, controlled tool use, test-based verification, bounded retry, and failure reporting.

This MVP is intended for AI Agent application engineering job preparation. It is not a general chatbot, not a plain RAG application, and not a clone of any commercial coding assistant. Its purpose is to show how an agent can safely inspect and modify a local repository through a constrained workflow.

## 2. MVP Goal

The MVP implements a single-agent LangGraph workflow.

The core loop is:

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

After receiving a user development task, the agent should be able to:

- understand whether the task requires code changes;
- inspect the local repository;
- build a compact and relevant repository context;
- generate a change plan;
- generate a unified diff patch;
- review the patch before applying it;
- apply the approved patch;
- run a controlled pytest command;
- use test results to retry within a fixed limit;
- produce a final success, failure, or no-change summary.

## 3. Core User Flow

The MVP user flow is:

1. The user runs a CLI command with a repository path and a development task.
2. The agent analyzes the task.
3. The agent searches and reads relevant files from the repository.
4. The agent builds a compressed repository context.
5. The agent produces a change plan.
6. The agent generates a unified diff patch.
7. The agent reviews the patch for format, scope, and safety.
8. The agent applies the patch only if review passes.
9. The agent runs the configured pytest command.
10. The agent analyzes the result.
11. The agent either retries with test feedback or produces a final summary.

The final status must be one of:

```text
success
failed
no_change
```

## 4. Must-have Capabilities

### 4.1 Repository Context Building

The agent must inspect the repository without loading the whole repository into the model context.

Minimum requirements:

- list relevant files;
- search code by keyword or error text;
- read selected file snippets;
- preserve file paths and line ranges where possible;
- compress the context before passing it to LLM nodes.

### 4.2 Planning

The agent must generate a plan before generating a patch.

The plan should include:

- target files;
- target function, class, or code area when available;
- intended change;
- validation strategy.

Planning must not modify files.

### 4.3 Patch Generation

The agent must generate code changes as a unified diff patch.

The LLM must not directly overwrite files.

The generated patch should be:

- repository-relative;
- free of Markdown code fences;
- scoped to the plan;
- small enough for review.

### 4.4 Patch Review

The agent must review a patch before applying it.

The review should check:

- unified diff format;
- file paths;
- forbidden paths;
- patch size;
- obvious mismatch with the plan;
- whether the patch can be dry-run before application.

### 4.5 Apply Patch

The agent must apply only approved patches.

Patch application must:

- be limited to the target repository;
- run a dry-run check first;
- fail closed when the patch is invalid;
- never fall back to direct file overwrite.

### 4.6 Run Tests

The agent must run tests through a controlled command.

The default test command is:

```text
python -m pytest -q
```

The test runner must:

- use a command allowlist;
- avoid arbitrary shell execution;
- enforce a timeout;
- capture structured results.

### 4.7 Limited Retry

The agent may retry after patch generation, patch review, patch application, or test failure.

Retries must be bounded.

Default recommendation:

```text
max_retries = 2
```

The agent must never retry indefinitely.

### 4.8 Final Summary

The final summary must include:

- final status;
- changed files, if any;
- main change made;
- test command;
- test result;
- failure reason, if failed;
- whether the working tree was modified.

## 5. Simplified Capabilities

The MVP intentionally simplifies several areas.

| Area               | MVP Simplification                                                        |
| ------------------ | ------------------------------------------------------------------------- |
| Repository support | Focus on small Python repositories                                        |
| Test command       | Default to controlled pytest command                                      |
| Context retrieval  | Use file listing, code search, and file snippets instead of vector search |
| Patch review       | Start with deterministic format, path, and scope checks                   |
| Permission model   | Use basic local path and command restrictions                             |
| Rollback           | Do not implement full rollback; report current git diff instead           |
| Multi-Agent        | Do not implement in MVP; keep only extension seams                        |
| Benchmarking       | Do not build a full evaluation platform                                   |

These simplifications are intentional. The MVP should demonstrate the core agent loop before expanding into larger systems.

## 6. Explicit Non-goals

The MVP must not implement:

- full Multi-Agent orchestration;
- MCP integration;
- IDE plugins;
- cloud execution;
- arbitrary shell execution;
- automatic dependency installation;
- automatic `git commit`, `git push`, `git reset`, or `git checkout`;
- complex benchmark infrastructure;
- vector database indexing;
- long-term memory;
- automatic modification of files outside the repository;
- direct file overwrite by the LLM.

The MVP must not become a general-purpose automation agent. It is a constrained coding agent focused on patch-based editing and test feedback.

## 7. MVP Input and Output

### 7.1 Input

A typical command should contain:

```text
repo path
user task
optional test command
optional max retry count
```

Example:

```text
codeflow fix --repo ./examples/calculator_bug "Fix add() for negative numbers"
```

### 7.2 Successful Output

A successful run should include:

```text
Status: success
Changed files:
- src/calculator.py

Summary:
- Fixed add() so it returns a + b for all integer inputs.

Validation:
- Command: python -m pytest -q
- Result: passed
```

### 7.3 Failed Output

A failed run should include:

```text
Status: failed
Failure stage: run_tests
Attempts: 3
Last error:
- tests/test_calculator.py::test_add_negative still failed

Changed files:
- src/calculator.py

Suggested next step:
- Inspect src/calculator.py and tests/test_calculator.py manually.
```

### 7.4 No-change Output

A no-change run should include:

```text
Status: no_change
Reason:
- The task asks for explanation only and does not require code modification.

Relevant context:
- src/calculator.py
```

## 8. Definition of Done

The MVP is done when all of the following are true:

- [ ] The CLI accepts a repository path and a user task.
- [ ] The agent can inspect a demo Python repository.
- [ ] The agent can list files, search code, and read relevant snippets.
- [ ] The agent can produce a structured task analysis.
- [ ] The agent can produce a change plan.
- [ ] The agent can generate a unified diff patch.
- [ ] The agent can review and reject invalid patches.
- [ ] The agent can apply an approved patch.
- [ ] The agent can show the resulting git diff.
- [ ] The agent can run a controlled pytest command.
- [ ] The agent can summarize test success or failure.
- [ ] The agent can retry on test failure within a fixed limit.
- [ ] The agent can produce an explainable failure summary.
- [ ] The agent does not use arbitrary shell execution.
- [ ] The LLM never directly overwrites files.
- [ ] The MVP can complete one end-to-end demo bug fix.

## 9. Minimal Demo Scenario

The recommended MVP demo repository is:

```text
examples/calculator_bug
```

Milestone 1 includes this repository as a stable read-only fixture. It contains:

```text
src/calculator.py
tests/test_calculator.py
```

Project-level pytest collection is configured to use only the main `tests/`
directory, so demo fixture tests are not collected accidentally before the full
Milestone 6 fix loop exists.

### Initial Bug

The `add(a, b)` function handles negative numbers incorrectly.

Example:

```text
add(-1, -2)
```

Expected:

```text
-3
```

Actual:

```text
3
```

### User Task

```text
Fix add() so it handles negative numbers correctly.
```

### Expected Agent Behavior

The agent should:

1. analyze the task;
2. search for `add`;
3. read the source file and relevant test file;
4. produce a plan;
5. generate a unified diff patch;
6. review the patch;
7. apply the patch;
8. run `python -m pytest -q`;
9. produce a success summary.

### Demo Acceptance Criteria

The demo is successful when:

- pytest changes from failing to passing;
- git diff shows the expected source change;
- the final status is `success`;
- the final summary reports changed files and test results.

A failure-path demo should also be supported.

Example:

```text
Fix the missing multiply_magic function.
```

Expected behavior:

- the agent does not invent unrelated changes;
- the agent does not modify random files;
- the final status is `failed`;
- the failure reason is explainable.

## 10. Post-MVP Boundary

The following features are reserved for post-MVP versions:

- Reviewer Agent;
- Tester Agent;
- Planner / Coder separation;
- Coordinator Agent;
- stronger checkpoint and rollback support;
- more advanced repository retrieval;
- evaluation harness;
- MCP integration;
- IDE integration;
- cloud execution.

Post-MVP features should only be added after the single-agent MVP is stable.

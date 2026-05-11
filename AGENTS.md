# Codeflow-agent AI Coding Rules

## 1. Project Scope

- Codeflow-agent is a minimal coding agent for local repositories.
- The MVP is a single-agent LangGraph workflow.
- The MVP focuses on context building, planning, patch editing, test verification, and bounded retry.
- Do not expand the project beyond the MVP unless explicitly requested.

## 2. MVP Boundary

The MVP may implement:

- repository file listing;
- repository file reading;
- code search;
- task analysis;
- change planning;
- unified diff generation;
- patch review;
- patch application;
- git diff summary;
- controlled pytest execution;
- bounded retry;
- final summary.

## 3. Hard Non-goals

Do not implement:

- full Multi-Agent orchestration;
- MCP integration;
- IDE plugins;
- cloud execution;
- arbitrary shell execution;
- automatic dependency installation;
- automatic `git commit`, `git push`, `git reset`, or `git checkout`;
- vector database indexing;
- benchmark platform;
- long-term memory;
- direct file overwrite by the LLM.

## 4. LangGraph Rules

- Do not bypass LangGraph.
- Do not hide the workflow inside one large `while` loop.
- Each node must have one clear responsibility.
- Each node must declare which state fields it reads and writes.
- Conditional edges must be explicit.
- Failure paths must be represented in state.
- Retry loops must be bounded.
- Final output should be produced only by the final summary path.

## 5. State Rules

- Keep `AgentState` small and stable.
- Do not add state fields without a clear reason.
- Do not store the full repository in state.
- Do not store full test logs in state.
- Do not store very large diffs in state.
- Use `error_summary` for compressed failure information.
- Use `iteration_count` and `max_iterations` for retry control.
- Write `final_output` only at the end of the workflow.

## 6. Tool Rules

- Every tool must return a structured result.
- Every tool must have an explicit failure return.
- Tools must not crash the whole workflow on normal failure.
- File paths must stay inside `repo_root`.
- Tool output must be length-limited or summarized.
- Read-only tools must not modify files.
- Write tools must be explicitly controlled.
- Test tools must use allowlisted commands.
- Subprocess calls must use `shell=False`.

## 7. Patch Editing Rules

- All code changes must use unified diff patches.
- The LLM may generate patches but must not directly write files.
- Patches must not contain Markdown fences.
- Patches must use repository-relative paths.
- Patches must not use absolute paths.
- Patches must not use `../` path traversal.
- Patches must not modify forbidden files or directories.
- Patches must be reviewed before application.
- Patch application must run a dry-run check first.
- If patch application fails, do not overwrite files manually.

## 8. Test and Verification Rules

- The default test command is `python -m pytest -q`.
- Do not allow arbitrary shell commands.
- Test execution must have a timeout.
- Test failure must be summarized before feeding back into the agent.
- Do not pass full pytest logs into the model.
- Do not report success when tests fail.
- Do not delete or weaken tests to make them pass.
- Do not hardcode outputs only to satisfy tests.
- Stop when the retry limit is reached.

## 9. AI Coding Workflow Rules

- Change one tool, node, or edge at a time.
- Do not generate the whole project in one step.
- Do not introduce new frameworks without approval.
- Do not expand MVP scope.
- Add or update tests for every meaningful change.
- Prefer small, reviewable patches.
- Explain the changed files.
- Explain how to run verification.
- Keep implementation aligned with `docs/mvp-spec.md` and `docs/architecture.md`.

## 10. Conflict Resolution

- MVP scope is defined by `docs/mvp-spec.md`.
- Architecture boundaries are defined by `docs/architecture.md`.
- AI coding behavior is constrained by this file.
- If documents conflict, choose the more conservative interpretation.
- When unsure, do less.
- Do not expand MVP scope.

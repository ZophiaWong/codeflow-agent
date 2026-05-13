## Context

Codeflow-agent is currently documentation-first. Milestone 1 must create the first runnable foundation without introducing the later agent workflow. The immediate need is a safe, testable read-only repository inspection layer that later LangGraph nodes can call through structured tool contracts.

The design follows the project layering direction:

```text
CLI -> Tool Interfaces -> Local Implementations -> Filesystem
```

LangGraph, LLM calls, planning, patch generation, patch application, pytest execution tools, and retry loops remain outside this milestone.

## Goals / Non-Goals

**Goals:**

- Provide a minimal installable Python package scaffold.
- Define a shared `ToolResult` dataclass for structured tool responses.
- Provide path utilities that keep file access inside `repo_root`.
- Implement read-only `list_files`, `read_file`, and `search_code` tools.
- Add a minimal CLI for read-only inspection once the package scaffold exists.
- Add `examples/calculator_bug` as a stable demo fixture.
- Add focused pytest coverage under the main `tests/` directory.

**Non-Goals:**

- No LangGraph workflow or AgentState runtime implementation.
- No LLM calls, task analysis, planning, patch generation, patch review, or patch application.
- No controlled pytest execution tool or retry loop.
- No arbitrary shell execution.
- No `ripgrep` dependency in Milestone 1.
- No repository-modifying commands.

## Decisions

### Decision: Use a Pydantic-free `ToolResult` dataclass

`ToolResult` will be a standard-library dataclass with fields:

```text
ok
data
summary
error_type
error_message
```

It will provide `success(...)`, `failure(...)`, and `to_dict()` helpers.

Rationale: The project does not need validation-heavy models in Milestone 1, and avoiding Pydantic keeps the scaffold small. `to_dict()` preserves a simple serialization path for future AgentState usage.

Alternative considered: Use plain dictionaries. This is simpler initially, but it makes field consistency weaker and increases the chance of unstructured failure returns.

Alternative considered: Use Pydantic models. This is unnecessary for the MVP foundation and would add a dependency before the project needs one.

### Decision: Centralize repo path validation

All tools will resolve paths through shared safe path utilities. The utilities will reject path traversal, missing roots, and paths that resolve outside `repo_root`, including symlink escapes.

Rationale: Path safety is a core invariant for later write-capable milestones. Implementing it once keeps read tools consistent and avoids each tool inventing its own checks.

Alternative considered: Validate paths inside each tool. This duplicates logic and makes safety behavior easier to drift.

### Decision: Start with pure-Python search

`search_code` will walk allowed files and search decoded text using standard-library Python.

Rationale: Milestone 1 should be runnable without external search dependencies. A future `ripgrep` adapter can be added behind the same tool contract if performance becomes important.

Alternative considered: Require `ripgrep` immediately. This would improve performance on large repositories, but it adds dependency and subprocess concerns before the read-only contract is stable.

### Decision: Use simple byte-prefix text detection

Text reads will inspect a small byte prefix, reject null bytes, and reject unsupported decoding.

Rationale: This is enough to prevent obvious binary-file reads in the MVP. It is also easy to test and keeps behavior explicit.

Alternative considered: Use MIME detection or a third-party library. That adds complexity and dependencies without improving the small-repository MVP enough to justify it.

### Decision: Keep demo tests outside pytest collection

`pyproject.toml` will configure pytest to collect only the main `tests/` directory. The demo repository can contain files named like tests without being collected accidentally.

Rationale: `examples/calculator_bug` is a fixture for inspection and later demo work, not part of the project's test suite in Milestone 1.

Alternative considered: Avoid demo tests until Milestone 6. The README already names the demo repo, and including it now gives read-only tools a stable target.

## Risks / Trade-offs

- Pure-Python search may be slower on large repositories -> Limit Milestone 1 expectations to small repositories and keep `ripgrep` as a future adapter option.
- Simple binary detection may classify some edge-case text files as unreadable -> Prefer fail-closed behavior for the MVP safety boundary.
- CLI behavior could grow beyond read-only inspection -> Keep commands limited to inspect, read, and search.
- Demo fixture tests could be collected accidentally -> Configure pytest test paths to `tests/` only.
- Path handling around symlinks can be subtle -> Resolve paths before containment checks and add tests for traversal and symlink escape cases where the platform supports them.

## Migration Plan

This is a new foundation with no existing runtime API to migrate. Implementation can proceed in small steps:

1. Add package scaffold and pytest configuration.
2. Add `ToolResult` and path utilities.
3. Add read-only tools and tests.
4. Add minimal CLI commands and tests.
5. Add the demo fixture.

Rollback is deleting the newly added scaffold and artifacts; no existing code behavior is changed.

## Open Questions

- Should the initial package name be `codeflow_agent` while the console script is `codeflow`?
- What default output limits should `list_files`, `read_file`, and `search_code` use?
- Should symlink escape tests be skipped on platforms that restrict symlink creation?

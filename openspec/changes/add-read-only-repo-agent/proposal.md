## Why

Codeflow-agent needs a safe read-only foundation before any planning, patch generation, or verification workflow can be built. Milestone 1 establishes the repository inspection tools and minimal local package structure required for later MVP milestones without allowing repository modification.

## What Changes

- Introduce a minimal Python package scaffold with `pyproject.toml`.
- Configure pytest so only the main `tests/` directory is collected, preventing demo repository tests from running accidentally.
- Add a Pydantic-free `ToolResult` dataclass with `ok`, `data`, `summary`, `error_type`, and `error_message` fields, plus success/failure constructors and `to_dict()` serialization.
- Add safe path utilities that constrain all file access to `repo_root`.
- Add read-only repository tools for listing files, reading text files, and searching code.
- Implement `search_code` in pure Python; `ripgrep` is not required for Milestone 1 and may be added later as an optional adapter.
- Add simple text/binary detection using a small byte-prefix sniff that rejects null bytes and unsupported decoding.
- Add minimal read-only CLI commands once the CLI surface exists.
- Add `examples/calculator_bug` as a stable read-only demo fixture.
- Add pytest coverage for the read-only tools and path safety behavior.

## Capabilities

### New Capabilities

- `repo-inspection`: Read-only repository inspection through structured tools for file listing, file reading, code search, safe path validation, length-limited output, and explicit failure returns.

### Modified Capabilities

None.

## Impact

- Affected code areas will include the initial package scaffold, read-only tool modules, safe path utilities, minimal CLI entry points, tests under `tests/`, pytest configuration, and the `examples/calculator_bug` fixture.
- No existing public API is changed.
- No new runtime framework is introduced.
- Milestone 1 intentionally excludes LLM calls, LangGraph workflow, planning, patch generation, patch review, patch application, test execution tools, retry loops, Multi-Agent features, and any repository-modifying command.

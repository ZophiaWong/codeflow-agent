## 1. Project Scaffold

- [x] 1.1 Add `pyproject.toml` with package metadata for `codeflow-agent`, Python package discovery, and pytest configuration limited to `tests/`.
- [x] 1.2 Create the initial `src/codeflow_agent/` package structure.
- [x] 1.3 Add minimal package exports without introducing LangGraph, LLM, or patching modules.

## 2. Tool Contract and Path Safety

- [x] 2.1 Implement the `ToolResult` dataclass with `ok`, `data`, `summary`, `error_type`, and `error_message` fields.
- [x] 2.2 Add `ToolResult.success(...)`, `ToolResult.failure(...)`, and `ToolResult.to_dict()`.
- [x] 2.3 Implement safe path utilities that resolve `repo_root` and repository-relative paths.
- [x] 2.4 Reject absolute-path escapes, `../` traversal, missing repository roots, and resolved paths outside `repo_root`.
- [x] 2.5 Add tests for `ToolResult` success/failure serialization and safe path acceptance/rejection.

## 3. Read-only Repository Tools

- [x] 3.1 Implement `list_files` using the shared `ToolResult` contract.
- [x] 3.2 Ensure `list_files` ignores `.git`, `.venv`, `__pycache__`, `.pytest_cache`, and other configured forbidden directories.
- [x] 3.3 Implement byte-prefix text detection that rejects null bytes and unsupported decoding.
- [x] 3.4 Implement `read_file` for text files inside `repo_root` with structured failures for missing files, directories, binary files, decode failures, and path escapes.
- [x] 3.5 Implement pure-Python `search_code` with repository-relative paths, line numbers, snippets, and structured failure handling.
- [x] 3.6 Add output limits or summaries for large file lists, file reads, and search results.
- [x] 3.7 Add tests covering successful and failing behavior for all read-only tools.

## 4. CLI and Demo Fixture

- [x] 4.1 Add a minimal read-only CLI module with inspect, read, and search command handling.
- [x] 4.2 Add the `codeflow` console script after the minimal CLI exists.
- [x] 4.3 Ensure CLI commands call read-only tools and do not modify repository files.
- [x] 4.4 Add `examples/calculator_bug` with `src/calculator.py` and `tests/test_calculator.py` as a stable demo fixture.
- [x] 4.5 Add tests or assertions that default pytest collection excludes demo fixture tests.

## 5. Verification

- [x] 5.1 Run `python -m pytest -q` and fix any Milestone 1 failures without weakening tests.
- [x] 5.2 Manually exercise the read-only CLI against `examples/calculator_bug`.
- [x] 5.3 Confirm no Milestone 1 command modifies files in the target repository.
- [x] 5.4 Update relevant documentation only if implementation details differ from the current README, roadmap, or architecture docs.

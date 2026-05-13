## ADDED Requirements

### Requirement: Structured tool result contract

The system SHALL provide a Pydantic-free `ToolResult` dataclass with `ok`, `data`, `summary`, `error_type`, and `error_message` fields. The contract SHALL provide success and failure constructors and a `to_dict()` method suitable for future AgentState serialization.

#### Scenario: Successful tool result

- **WHEN** a read-only tool completes successfully
- **THEN** it returns a `ToolResult` with `ok` set to true, populated `data`, a concise `summary`, and no failure details

#### Scenario: Failed tool result

- **WHEN** a read-only tool cannot complete normally
- **THEN** it returns a `ToolResult` with `ok` set to false, an `error_type`, an `error_message`, and no uncaught normal failure

### Requirement: Repository path safety

The system MUST constrain all repository file access to paths inside `repo_root`. It MUST reject absolute-path escapes, `../` traversal, and resolved paths outside `repo_root`.

#### Scenario: Path inside repository

- **WHEN** a tool receives a repository-relative path that resolves inside `repo_root`
- **THEN** the path is accepted for read-only access

#### Scenario: Path traversal outside repository

- **WHEN** a tool receives a path that resolves outside `repo_root`
- **THEN** the tool returns a structured failure without reading the target

### Requirement: File listing

The system SHALL provide a read-only `list_files` tool that lists allowed repository files inside `repo_root` while ignoring forbidden directories such as `.git`, `.venv`, `__pycache__`, and `.pytest_cache`.

#### Scenario: List allowed files

- **WHEN** `list_files` runs against a repository containing regular source files
- **THEN** it returns repository-relative file paths for allowed files

#### Scenario: Ignore forbidden directories

- **WHEN** `list_files` encounters forbidden directories
- **THEN** it omits files inside those directories from the result

### Requirement: Text file reading

The system SHALL provide a read-only `read_file` tool that reads text files inside `repo_root`. It MUST reject missing files, directories, binary files, unsupported text decoding, and paths outside `repo_root`.

#### Scenario: Read text file

- **WHEN** `read_file` receives a path to a text file inside `repo_root`
- **THEN** it returns the file content or a length-limited representation with repository-relative path metadata

#### Scenario: Reject binary file

- **WHEN** `read_file` receives a file whose byte prefix contains null bytes or cannot be decoded as supported text
- **THEN** it returns a structured failure indicating the file is not readable text

### Requirement: Pure-Python code search

The system SHALL provide a read-only `search_code` tool implemented without requiring `ripgrep` in Milestone 1. Search results SHALL include matching repository-relative file paths, line numbers, and snippets.

#### Scenario: Search matching code

- **WHEN** `search_code` receives a query that appears in readable repository files
- **THEN** it returns matching file paths, line numbers, and concise snippets

#### Scenario: Search skips unreadable files

- **WHEN** `search_code` encounters forbidden, binary, or unsupported text files
- **THEN** it skips those files or reports summarized skipped-file information without crashing

### Requirement: Length-limited output

The system MUST length-limit or summarize read-only tool output so large repositories, large files, and broad searches do not produce unbounded results.

#### Scenario: File list exceeds limit

- **WHEN** `list_files` finds more files than the configured output limit
- **THEN** it returns a bounded result and summary indicating truncation or omission

#### Scenario: Search exceeds limit

- **WHEN** `search_code` finds more matches than the configured output limit
- **THEN** it returns a bounded result and summary indicating truncation or omission

### Requirement: Read-only CLI inspection

The system SHALL expose minimal CLI commands for read-only inspection after the package scaffold exists. The commands SHALL allow users to inspect files, read a file, and search code without modifying repository files.

#### Scenario: CLI reads repository structure

- **WHEN** a user runs a read-only inspection command with a repository path
- **THEN** the command reports repository information through read-only tools

#### Scenario: CLI does not modify repository

- **WHEN** a user runs any Milestone 1 CLI command
- **THEN** the command performs no repository modification

### Requirement: Demo fixture and test collection

The system SHALL include `examples/calculator_bug` as a stable read-only demo fixture. The project pytest configuration MUST collect only the main `tests/` directory so demo repository tests are not collected accidentally.

#### Scenario: Demo fixture exists

- **WHEN** read-only tools are exercised against `examples/calculator_bug`
- **THEN** the fixture provides source and test files suitable for listing, reading, and searching

#### Scenario: Pytest excludes demo tests

- **WHEN** project tests are run with the default pytest configuration
- **THEN** pytest collects tests from the main `tests/` directory and does not collect tests from `examples/calculator_bug`

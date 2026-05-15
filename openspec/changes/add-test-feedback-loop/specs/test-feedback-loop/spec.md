## ADDED Requirements

### Requirement: Controlled pytest execution
The system SHALL run tests only through the allowlisted default pytest command shape.

#### Scenario: Default pytest command passes
- **WHEN** Fix Mode runs tests for a repository whose pytest suite passes
- **THEN** the system records a structured test result with `passed` set to true

#### Scenario: Disallowed command is rejected
- **WHEN** test execution is requested with a command other than `python -m pytest -q`
- **THEN** the system rejects the command with a structured failure result

#### Scenario: Test command times out
- **WHEN** pytest execution exceeds the configured timeout
- **THEN** the system records a structured timeout failure

### Requirement: Test result analysis
The system SHALL analyze pytest results before producing a final Fix Mode status.

#### Scenario: Passing tests produce success
- **WHEN** pytest exits successfully after patch application
- **THEN** Fix Mode returns `status = success`

#### Scenario: Failing tests produce compact failure summary
- **WHEN** pytest exits with failing tests
- **THEN** Fix Mode stores compact failure details in `error_summary`

#### Scenario: Failed tests are never reported as success
- **WHEN** pytest reports failing tests and retry is exhausted
- **THEN** Fix Mode returns `status = failed`

### Requirement: Bounded retry from test feedback
The system SHALL feed failed test results back into patch generation only while retry attempts remain.

#### Scenario: Retry remains after failed tests
- **WHEN** tests fail and `iteration_count` is less than `max_iterations`
- **THEN** Fix Mode increments `iteration_count`, rebuilds repository context, and attempts another patch

#### Scenario: Retry limit reached
- **WHEN** tests fail and `iteration_count` equals `max_iterations`
- **THEN** Fix Mode stops and returns a failed result

### Requirement: Fix Mode CLI workflow
The system SHALL expose `codeflow fix` as the test-verified workflow command.

#### Scenario: Calculator fixture succeeds
- **WHEN** `codeflow fix --repo <copy-of-calculator-fixture> "Fix add() for negative numbers"` runs
- **THEN** the system applies the patch, runs pytest, and returns a successful JSON `ToolResult`

#### Scenario: No-change task skips tests
- **WHEN** Fix Mode classifies a task as not requiring code changes
- **THEN** the workflow returns `no_change` without running tests

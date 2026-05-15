## ADDED Requirements

### Requirement: Patch review gate
The system SHALL review a generated unified diff before any patch application is attempted.

#### Scenario: Valid patch is approved
- **WHEN** Patch Review receives a generated unified diff that passes validation, stays within the planned target files, and stays within configured size limits
- **THEN** the system records an approved patch review result with the reviewed changed files

#### Scenario: Markdown-wrapped patch is rejected
- **WHEN** Patch Review receives a patch containing Markdown code fences
- **THEN** the system rejects the patch review with a structured failure result

#### Scenario: Unsafe patch path is rejected
- **WHEN** Patch Review receives a patch that uses an absolute path, path traversal, or a forbidden repository path
- **THEN** the system rejects the patch review with a structured failure result

#### Scenario: Overly large patch is rejected
- **WHEN** Patch Review receives a patch that exceeds the configured patch byte, changed file, or changed line limit
- **THEN** the system rejects the patch review with a structured failure result

### Requirement: Review-approved patch application
The system SHALL apply patches only after a patch review result explicitly approves the patch.

#### Scenario: Unapproved patch is not applied
- **WHEN** patch application is requested without an approved patch review result
- **THEN** the system refuses to apply the patch and returns a structured failure result

#### Scenario: Dry-run failure prevents application
- **WHEN** patch application is requested with an approved patch review result but the dry-run check fails
- **THEN** the system does not apply the patch and returns a structured failure result

#### Scenario: Approved patch is applied after dry-run
- **WHEN** patch application is requested with an approved patch review result and the dry-run check succeeds
- **THEN** the system applies the patch using the controlled patch application path

### Requirement: Controlled subprocess execution for patch tools
The system SHALL use allowlisted Git commands with `shell=False` and a timeout for patch application and git diff reporting.

#### Scenario: Patch dry-run uses allowlisted command
- **WHEN** the system checks whether a patch can be applied
- **THEN** it runs `git apply --check --whitespace=nowarn` with `shell=False`, repository root as the working directory, patch content on stdin, and a timeout

#### Scenario: Patch application uses allowlisted command
- **WHEN** the system applies an approved patch
- **THEN** it runs `git apply --whitespace=nowarn` with `shell=False`, repository root as the working directory, patch content on stdin, and a timeout

#### Scenario: Disallowed command is not available through patch tools
- **WHEN** the Patch Review and Apply workflow runs
- **THEN** it does not expose arbitrary shell command execution

### Requirement: Git diff summary reporting
The system SHALL report a compact git diff summary after successful patch application.

#### Scenario: Applied patch reports changed files
- **WHEN** a patch is applied successfully
- **THEN** the system records the changed repository files reported by Git

#### Scenario: Applied patch reports diff statistics
- **WHEN** a patch is applied successfully
- **THEN** the system records compact git diff statistics or a length-limited diff summary

#### Scenario: Git diff failure is structured
- **WHEN** git diff reporting fails
- **THEN** the system records a structured failure result instead of crashing the workflow

### Requirement: Apply Mode workflow
The system SHALL expose a LangGraph-backed Apply Mode that extends Patch Mode with review, application, git diff, and final summary nodes.

#### Scenario: Apply Mode modifies the calculator demo fixture
- **WHEN** `codeflow apply --repo ./examples/calculator_bug "Fix add() for negative numbers"` runs against the demo fixture
- **THEN** the system generates, reviews, dry-runs, applies the patch, and reports `src/calculator.py` in the git diff summary

#### Scenario: Apply Mode stops on review failure
- **WHEN** Patch Review rejects the generated patch
- **THEN** Apply Mode stops before patch application and returns a failed `ToolResult`

#### Scenario: Apply Mode final output comes from final summary
- **WHEN** Apply Mode completes successfully or fails
- **THEN** the workflow writes `final_output` only on the final summary path

#### Scenario: Apply Mode does not run tests
- **WHEN** Apply Mode applies a patch successfully
- **THEN** the workflow does not run pytest or report test success

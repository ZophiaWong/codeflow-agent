## Context

Codeflow-agent currently supports read-only repository tools, Plan Mode, and Patch Mode. Patch Mode can generate a unified diff and validate its basic format, path safety, and plan scope, but it intentionally does not modify the repository.

Milestone 4 is the first write-capable milestone. It must preserve the MVP constraints: a single-agent LangGraph workflow, patch-based editing only, structured tool results, repository-local path boundaries, no arbitrary shell execution, and no direct file overwrite fallback.

## Goals / Non-Goals

**Goals:**

- Add a Patch Review step after generated patch validation and before application.
- Add a controlled patch application tool that requires review approval.
- Run a dry-run patch check before modifying files.
- Apply approved unified diffs to the target repository.
- Report a compact git diff summary after successful application.
- Expose the flow through a `codeflow apply` CLI command.
- Preserve explicit node responsibilities and state field read/write documentation.

**Non-Goals:**

- Do not run pytest or analyze test results.
- Do not add retry loops based on apply or test failures.
- Do not add automatic git commit, push, reset, checkout, or rollback.
- Do not allow arbitrary shell commands.
- Do not support direct file overwrite fallback if patch application fails.
- Do not add new/delete/rename patch support unless later approved.

## Decisions

### Decision 1: Build Apply Mode as an Extension of Patch Mode

Apply Mode will reuse the same early workflow stages already used by Patch Mode:

```text
analyze_task
-> build_repo_context
-> plan_changes
-> generate_patch
-> validate_patch
-> review_patch
-> apply_patch
-> git_diff
-> final_summary
```

Rationale: this keeps behavior aligned with the existing LangGraph flow and avoids duplicating task analysis, context gathering, planning, or patch generation logic.

Alternative considered: make `codeflow apply` accept a patch file only. That would be useful later, but it would not exercise the MVP agent loop described in the roadmap.

### Decision 2: Review Patch Is a Separate Gate From Format Validation

`validate_generated_patch` remains the low-level generated diff validator. `review_patch` will call or reuse that validation, then add application-oriented checks such as patch byte limits, changed file limits, changed line limits, and required target-file scope.

Rationale: M3 validation answers "is this a plausible generated unified diff?" M4 review answers "is this acceptable to apply in this controlled workflow?"

Alternative considered: fold all review logic into `validate_generated_patch`. Keeping review separate makes the application gate explicit in state and in the LangGraph node map.

### Decision 3: Patch Application Uses Controlled Git Subprocesses

The patch application tool will run a dry-run first:

```text
git apply --check --whitespace=nowarn
```

Only after the dry-run succeeds will it run:

```text
git apply --whitespace=nowarn
```

Both commands must use `subprocess.run(..., shell=False, cwd=repo_root, input=patch, text=True, timeout=...)`.

Rationale: `git apply --check` provides a native patch compatibility check without modifying files, while `git apply` applies unified diffs without requiring direct file overwrite logic.

Alternative considered: implement a Python patch applier. That would increase risk and complexity for the MVP and duplicate behavior that Git already provides.

### Decision 4: Git Diff Reporting Is a Read-Only Reporting Tool

After successful application, a `git_diff` tool will summarize:

- changed files from `git diff --name-only`;
- compact diff statistics from `git diff --stat`;
- optionally a length-limited diff preview from `git diff`.

Rationale: M4 needs to report the result of application, but should not store or print unlimited diffs.

Alternative considered: return the full raw diff. That conflicts with the state rule to avoid very large diffs.

### Decision 5: `codeflow apply` Means User Approval To Modify Files

The CLI command `codeflow apply --repo <repo> <task>` will be the explicit user-facing write command. Internally, `apply_patch` must still require `patch_review.approved == true`.

Rationale: the CLI command separates non-writing `plan` and `patch` modes from a writing apply mode, while the internal review result preserves a second safety gate.

Alternative considered: add an `--apply` flag to `codeflow patch`. A separate command keeps the write boundary clearer.

## Risks / Trade-offs

- Patch applies to a dirty working tree unexpectedly -> Mitigation: M4 reports the resulting git diff and does not commit or reset. It may optionally surface pre-existing changed files as part of structured context, but must not modify them outside the patch.
- Git is unavailable or the repository is not a Git worktree -> Mitigation: return a structured tool failure such as `git_unavailable` or `git_repo_required`.
- Generated patch is valid but too broad -> Mitigation: review enforces conservative size and changed-file limits before dry-run.
- Dry-run succeeds but apply fails due to a race or file change -> Mitigation: return structured `patch_apply_failed`; do not overwrite files manually.
- Diff output is large -> Mitigation: summarize changed files and stat output, and length-limit any diff preview.

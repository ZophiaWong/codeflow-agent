"""Controlled patch application tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from codeflow_agent.paths import PathSafetyError, resolve_repo_root
from codeflow_agent.results import ToolResult

GIT_APPLY_CHECK_COMMAND = ["git", "apply", "--check", "--whitespace=nowarn"]
GIT_APPLY_COMMAND = ["git", "apply", "--whitespace=nowarn"]
GIT_WORKTREE_COMMAND = ["git", "rev-parse", "--is-inside-work-tree"]
DEFAULT_TIMEOUT_SECONDS = 10


def apply_patch(
    repo_root: str,
    patch: str,
    patch_review: dict[str, Any] | None,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> ToolResult:
    if not patch_review or patch_review.get("approved") is not True:
        return ToolResult.failure("patch_not_approved", "Patch application requires an approved patch review.")
    if not patch.strip():
        return ToolResult.failure("empty_patch", "Patch application requires a non-empty patch.")

    root_result = _resolve_git_repo(repo_root, timeout_seconds=timeout_seconds)
    if not root_result.ok:
        return root_result
    root = root_result.data["repo_root"]

    dry_run = _run_git(
        GIT_APPLY_CHECK_COMMAND,
        root,
        patch,
        timeout_seconds=timeout_seconds,
        failure_type="patch_dry_run_failed",
    )
    if not dry_run.ok:
        return dry_run

    applied = _run_git(
        GIT_APPLY_COMMAND,
        root,
        patch,
        timeout_seconds=timeout_seconds,
        failure_type="patch_apply_failed",
    )
    if not applied.ok:
        return applied

    return ToolResult.success(
        data={
            "applied": True,
            "dry_run": {"ok": True, "command": GIT_APPLY_CHECK_COMMAND},
            "command": GIT_APPLY_COMMAND,
            "changed_files": patch_review.get("changed_files", []),
        },
        summary="Patch applied after successful dry-run.",
    )


def _resolve_git_repo(repo_root: str, *, timeout_seconds: int) -> ToolResult:
    try:
        root = resolve_repo_root(repo_root)
    except PathSafetyError as exc:
        return ToolResult.failure(exc.error_type, exc.error_message)

    worktree = _run_git(
        GIT_WORKTREE_COMMAND,
        root,
        None,
        timeout_seconds=timeout_seconds,
        failure_type="git_repo_required",
    )
    if not worktree.ok:
        return worktree
    if (worktree.data.get("stdout") or "").strip() != "true":
        return ToolResult.failure("git_repo_required", f"Repository root is not inside a Git worktree: {repo_root}")
    return ToolResult.success(data={"repo_root": root})


def _run_git(
    command: list[str],
    cwd: Path,
    stdin: str | None,
    *,
    timeout_seconds: int,
    failure_type: str,
) -> ToolResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        return ToolResult.failure("git_unavailable", "Git executable was not found.")
    except subprocess.TimeoutExpired:
        return ToolResult.failure(failure_type, f"Git command timed out after {timeout_seconds} second(s).")

    data = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _limit_output(completed.stdout),
        "stderr": _limit_output(completed.stderr),
    }
    if completed.returncode != 0:
        message = data["stderr"] or data["stdout"] or f"Git command failed: {' '.join(command)}"
        return ToolResult.failure(failure_type, message, data=data)
    return ToolResult.success(data=data)


def _limit_output(output: str, max_chars: int = 2_000) -> str:
    if len(output) <= max_chars:
        return output
    return output[:max_chars] + "\n...<truncated>"

"""Read-only Git reporting tools."""

from __future__ import annotations

import subprocess
from pathlib import Path

from codeflow_agent.paths import PathSafetyError, resolve_repo_root
from codeflow_agent.results import ToolResult

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MAX_DIFF_CHARS = 4_000


def git_diff(repo_root: str, *, max_diff_chars: int = DEFAULT_MAX_DIFF_CHARS, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> ToolResult:
    try:
        root = resolve_repo_root(repo_root)
    except PathSafetyError as exc:
        return ToolResult.failure(exc.error_type, exc.error_message)

    worktree = _run_git(["git", "rev-parse", "--is-inside-work-tree"], root, timeout_seconds=timeout_seconds)
    if not worktree.ok:
        return ToolResult.failure(worktree.error_type or "git_repo_required", worktree.error_message or "Git worktree check failed.")
    if (worktree.data.get("stdout") or "").strip() != "true":
        return ToolResult.failure("git_repo_required", f"Repository root is not inside a Git worktree: {repo_root}")

    names = _run_git(["git", "diff", "--name-only"], root, timeout_seconds=timeout_seconds)
    if not names.ok:
        return names
    stat = _run_git(["git", "diff", "--stat"], root, timeout_seconds=timeout_seconds)
    if not stat.ok:
        return stat
    diff = _run_git(["git", "diff"], root, timeout_seconds=timeout_seconds)
    if not diff.ok:
        return diff

    changed_files = [line for line in names.data["stdout"].splitlines() if line.strip()]
    diff_text = diff.data["stdout"]
    preview = _limit_output(diff_text, max_diff_chars)
    return ToolResult.success(
        data={
            "changed_files": changed_files,
            "stat": stat.data["stdout"],
            "diff_preview": preview,
            "diff_truncated": len(diff_text) > max_diff_chars,
        },
        summary=f"Git diff reports {len(changed_files)} changed file(s).",
    )


def _run_git(command: list[str], cwd: Path, *, timeout_seconds: int) -> ToolResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        return ToolResult.failure("git_unavailable", "Git executable was not found.")
    except subprocess.TimeoutExpired:
        return ToolResult.failure("git_timeout", f"Git command timed out after {timeout_seconds} second(s).")

    data = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _limit_output(completed.stdout),
        "stderr": _limit_output(completed.stderr),
    }
    if completed.returncode != 0:
        message = data["stderr"] or data["stdout"] or f"Git command failed: {' '.join(command)}"
        return ToolResult.failure("git_command_failed", message, data=data)
    return ToolResult.success(data=data)


def _limit_output(output: str, max_chars: int = 2_000) -> str:
    if len(output) <= max_chars:
        return output
    return output[:max_chars] + "\n...<truncated>"

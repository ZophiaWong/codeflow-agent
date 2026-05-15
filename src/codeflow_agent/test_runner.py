"""Controlled pytest execution tool."""

from __future__ import annotations

import subprocess
import sys

from codeflow_agent.paths import PathSafetyError, resolve_repo_root
from codeflow_agent.results import ToolResult

DEFAULT_TEST_COMMAND = ["python", "-m", "pytest", "-q"]
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TEST_OUTPUT_CHARS = 4_000


def run_tests(
    repo_root: str,
    command: list[str] | None = None,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_chars: int = MAX_TEST_OUTPUT_CHARS,
) -> ToolResult:
    requested_command = command or DEFAULT_TEST_COMMAND
    command_result = _resolve_allowed_command(requested_command)
    if not command_result.ok:
        return command_result
    execution_command = command_result.data["execution_command"]

    try:
        root = resolve_repo_root(repo_root)
    except PathSafetyError as exc:
        return ToolResult.failure(exc.error_type, exc.error_message)

    try:
        completed = subprocess.run(
            execution_command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        return ToolResult.failure("test_command_unavailable", "Python executable for pytest was not found.")
    except subprocess.TimeoutExpired as exc:
        output = _limit_output((exc.stdout or "") + (exc.stderr or ""), max_output_chars)
        return ToolResult.failure(
            "test_timeout",
            f"Test command timed out after {timeout_seconds} second(s).",
            data={
                "command": requested_command,
                "execution_command": execution_command,
                "timeout_seconds": timeout_seconds,
                "output": output,
            },
        )

    stdout = _limit_output(completed.stdout, max_output_chars)
    stderr = _limit_output(completed.stderr, max_output_chars)
    passed = completed.returncode == 0
    summary = "Tests passed." if passed else _summarize_failure(stdout, stderr)
    return ToolResult.success(
        data={
            "passed": passed,
            "returncode": completed.returncode,
            "command": requested_command,
            "execution_command": execution_command,
            "stdout": stdout,
            "stderr": stderr,
            "summary": summary,
            "truncated": len(completed.stdout) > max_output_chars or len(completed.stderr) > max_output_chars,
        },
        summary=summary,
    )


def _resolve_allowed_command(command: list[str]) -> ToolResult:
    allowed_first = {"python", "python3", sys.executable}
    if len(command) != 4 or command[0] not in allowed_first or command[1:] != ["-m", "pytest", "-q"]:
        return ToolResult.failure(
            "disallowed_test_command",
            "Only the default pytest command is allowed: python -m pytest -q",
        )

    execution_command = [sys.executable, "-m", "pytest", "-q"] if command[0] in {"python", "python3"} else command
    return ToolResult.success(data={"execution_command": execution_command})


def _summarize_failure(stdout: str, stderr: str) -> str:
    combined = "\n".join(part for part in (stdout, stderr) if part.strip())
    failing_lines = [
        line.strip()
        for line in combined.splitlines()
        if line.startswith("FAILED ") or line.strip().startswith("E   ")
    ]
    if failing_lines:
        return "Tests failed: " + " | ".join(failing_lines[:5])
    if combined.strip():
        return "Tests failed: " + combined.strip().splitlines()[-1]
    return "Tests failed."


def _limit_output(output: str, max_chars: int) -> str:
    if len(output) <= max_chars:
        return output
    return output[:max_chars] + "\n...<truncated>"

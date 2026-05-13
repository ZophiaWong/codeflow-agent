"""Injectable patch generation seam for Patch Mode."""

from __future__ import annotations

from typing import Any, Protocol


class PatchGenerator(Protocol):
    def generate_patch(
        self,
        *,
        user_task: str,
        task_analysis: dict[str, Any],
        repo_context: dict[str, Any],
        plan: dict[str, Any],
    ) -> str:
        """Return a unified diff patch."""


class DeterministicPatchGenerator:
    """Small deterministic generator used until a real LLM adapter exists."""

    def generate_patch(
        self,
        *,
        user_task: str,
        task_analysis: dict[str, Any],
        repo_context: dict[str, Any],
        plan: dict[str, Any],
    ) -> str:
        if not plan.get("needs_patch"):
            return ""

        target_files = set(plan.get("target_files", []))
        task = user_task.lower()
        if "src/calculator.py" not in target_files or "add" not in task:
            return ""

        for item in repo_context.get("relevant_files", []):
            if item.get("path") != "src/calculator.py":
                continue
            if "return abs(a) + abs(b)" not in item.get("content", ""):
                return ""
            return (
                "diff --git a/src/calculator.py b/src/calculator.py\n"
                "--- a/src/calculator.py\n"
                "+++ b/src/calculator.py\n"
                "@@ -1,2 +1,2 @@\n"
                " def add(a, b):\n"
                "-    return abs(a) + abs(b)\n"
                "+    return a + b\n"
            )

        return ""

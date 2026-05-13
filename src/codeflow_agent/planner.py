"""Injectable planning seam for Plan Mode."""

from __future__ import annotations

import re
from typing import Any, Protocol


class Planner(Protocol):
    def analyze_task(self, user_task: str) -> dict[str, Any]:
        """Return structured task analysis."""

    def plan_changes(
        self,
        *,
        user_task: str,
        task_analysis: dict[str, Any],
        repo_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a structured change plan."""


class DeterministicPlanner:
    """Small deterministic planner used until a real LLM adapter exists."""

    _no_change_markers = (
        "explain",
        "describe",
        "summarize",
        "what is",
        "what does",
        "how does",
        "why does",
        "show me",
    )

    def analyze_task(self, user_task: str) -> dict[str, Any]:
        task = user_task.strip()
        lowered = task.lower()
        needs_code_change = not any(marker in lowered for marker in self._no_change_markers)
        return {
            "summary": task,
            "needs_code_change": needs_code_change,
            "task_type": "code_change" if needs_code_change else "question",
            "reason": (
                "Task appears to request a repository change."
                if needs_code_change
                else "Task appears to request explanation only."
            ),
        }

    def plan_changes(
        self,
        *,
        user_task: str,
        task_analysis: dict[str, Any],
        repo_context: dict[str, Any],
    ) -> dict[str, Any]:
        target_files = [item["path"] for item in repo_context.get("relevant_files", [])]
        return {
            "needs_patch": bool(task_analysis.get("needs_code_change")),
            "target_files": target_files,
            "intended_change": f"Update the repository to satisfy: {user_task.strip()}",
            "steps": [
                "Review the relevant files identified from repository context.",
                "Make the smallest source change that satisfies the task.",
                "Keep any future patch repository-relative and scoped to the plan.",
            ],
            "validation_strategy": "After patch application is available, run python -m pytest -q.",
        }


_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "the",
    "this",
    "that",
    "with",
    "should",
    "please",
    "handles",
    "correctly",
}


def derive_search_terms(user_task: str, *, limit: int = 5) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", user_task):
        lowered = token.lower()
        if len(lowered) < 3 or lowered in _STOPWORDS:
            continue
        if lowered not in terms:
            terms.append(lowered)
        if len(terms) >= limit:
            break
    return terms

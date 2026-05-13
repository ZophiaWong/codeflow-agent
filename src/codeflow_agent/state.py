"""State shapes for Codeflow-agent workflows."""

from __future__ import annotations

from typing import Any, TypedDict


class PlanState(TypedDict, total=False):
    repo_root: str
    user_task: str
    task_analysis: dict[str, Any] | None
    repo_context: dict[str, Any] | None
    plan: dict[str, Any] | None
    error_summary: dict[str, Any] | None
    status: str
    final_output: str | None


class PatchState(PlanState, total=False):
    patch: str | None
    patch_validation: dict[str, Any] | None


def initial_plan_state(repo_root: str, user_task: str) -> PlanState:
    return {
        "repo_root": repo_root,
        "user_task": user_task,
        "task_analysis": None,
        "repo_context": None,
        "plan": None,
        "error_summary": None,
        "status": "pending",
        "final_output": None,
    }


def initial_patch_state(repo_root: str, user_task: str) -> PatchState:
    state: PatchState = initial_plan_state(repo_root, user_task)
    state["patch"] = None
    state["patch_validation"] = None
    return state

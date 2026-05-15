"""LangGraph-backed patch review and apply workflow."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from codeflow_agent.git_tools import git_diff
from codeflow_agent.patch_apply import apply_patch
from codeflow_agent.patch_generator import DeterministicPatchGenerator, PatchGenerator
from codeflow_agent.patch_mode import generate_patch_node, validate_patch_node
from codeflow_agent.patch_review import review_patch
from codeflow_agent.plan_mode import (
    analyze_task_node,
    build_repo_context_node,
    plan_changes_node,
)
from codeflow_agent.planner import DeterministicPlanner, Planner
from codeflow_agent.results import ToolResult
from codeflow_agent.state import ApplyState, initial_apply_state

NODE_IO = {
    "analyze_task": {
        "reads": ["user_task"],
        "writes": ["task_analysis", "status", "error_summary"],
    },
    "build_repo_context": {
        "reads": ["repo_root", "user_task", "task_analysis"],
        "writes": ["repo_context", "status", "error_summary"],
    },
    "plan_changes": {
        "reads": ["user_task", "task_analysis", "repo_context"],
        "writes": ["plan", "status", "error_summary"],
    },
    "generate_patch": {
        "reads": ["user_task", "task_analysis", "repo_context", "plan"],
        "writes": ["patch", "status", "error_summary"],
    },
    "validate_patch": {
        "reads": ["patch", "plan"],
        "writes": ["patch_validation", "status", "error_summary"],
    },
    "review_patch": {
        "reads": ["patch", "plan"],
        "writes": ["patch_review", "status", "error_summary"],
    },
    "apply_patch": {
        "reads": ["repo_root", "patch", "patch_review"],
        "writes": ["apply_result", "status", "error_summary"],
    },
    "git_diff": {
        "reads": ["repo_root"],
        "writes": ["git_diff", "status", "error_summary"],
    },
    "final_summary": {
        "reads": ["status", "plan", "patch_review", "apply_result", "git_diff", "error_summary"],
        "writes": ["status", "final_output"],
    },
}


def review_patch_node(state: ApplyState) -> dict[str, Any]:
    review = review_patch(
        state.get("patch") or "",
        target_files=(state.get("plan") or {}).get("target_files", []),
    )
    if not review.ok:
        return {
            "patch_review": {
                "approved": False,
                "error_type": review.error_type,
                "error_message": review.error_message,
            },
            **_failed(review.error_type or "patch_review_failed", review.error_message or ""),
        }

    return {
        "patch_review": {
            "approved": True,
            "changed_files": review.data["changed_files"],
            "patch_bytes": review.data["patch_bytes"],
            "changed_lines": review.data["changed_lines"],
            "limits": review.data["limits"],
            "summary": review.summary,
        },
        "status": "patch_reviewed",
        "error_summary": None,
    }


def apply_patch_node(state: ApplyState) -> dict[str, Any]:
    result = apply_patch(
        state["repo_root"],
        state.get("patch") or "",
        state.get("patch_review"),
    )
    if not result.ok:
        return {
            "apply_result": {
                "applied": False,
                "error_type": result.error_type,
                "error_message": result.error_message,
            },
            **_failed(result.error_type or "patch_apply_failed", result.error_message or ""),
        }

    return {
        "apply_result": {
            "applied": True,
            "changed_files": result.data.get("changed_files", []),
            "summary": result.summary,
        },
        "status": "patch_applied",
        "error_summary": None,
    }


def git_diff_node(state: ApplyState) -> dict[str, Any]:
    result = git_diff(state["repo_root"])
    if not result.ok:
        return {
            "git_diff": {
                "ok": False,
                "error_type": result.error_type,
                "error_message": result.error_message,
            },
            **_failed(result.error_type or "git_diff_failed", result.error_message or ""),
        }

    return {
        "git_diff": {
            "ok": True,
            "changed_files": result.data["changed_files"],
            "stat": result.data["stat"],
            "diff_preview": result.data["diff_preview"],
            "diff_truncated": result.data["diff_truncated"],
            "summary": result.summary,
        },
        "status": "applied",
        "error_summary": None,
    }


def final_summary_node(state: ApplyState) -> dict[str, Any]:
    status = state.get("status", "failed")
    if state.get("error_summary"):
        status = "failed"
        final_output = f"Apply Mode failed: {state['error_summary']['error_message']}"
    elif status == "no_change":
        final_output = "No code change is needed for this task."
    elif status == "planned" and not (state.get("plan") or {}).get("needs_patch"):
        status = "no_change"
        final_output = "Plan does not require a patch."
    elif status == "applied":
        changed_files = ", ".join((state.get("git_diff") or {}).get("changed_files", [])) or "none"
        final_output = f"Patch applied. Changed files: {changed_files}. Tests not run."
    else:
        status = "failed"
        final_output = "Apply Mode failed before applying a patch."

    return {"status": status, "final_output": final_output}


def build_apply_graph(
    planner: Planner | None = None,
    patch_generator: PatchGenerator | None = None,
):
    planner = planner or DeterministicPlanner()
    patch_generator = patch_generator or DeterministicPatchGenerator()

    graph = StateGraph(ApplyState)
    graph.add_node("analyze_task", lambda state: analyze_task_node(state, planner))
    graph.add_node("build_repo_context", build_repo_context_node)
    graph.add_node("plan_changes", lambda state: plan_changes_node(state, planner))
    graph.add_node("generate_patch", lambda state: generate_patch_node(state, patch_generator))
    graph.add_node("validate_patch", validate_patch_node)
    graph.add_node("review_patch", review_patch_node)
    graph.add_node("apply_patch", apply_patch_node)
    graph.add_node("git_diff", git_diff_node)
    graph.add_node("final_summary", final_summary_node)

    graph.set_entry_point("analyze_task")
    graph.add_conditional_edges(
        "analyze_task",
        _route_after_analysis,
        {"context": "build_repo_context", "final": "final_summary"},
    )
    graph.add_conditional_edges(
        "build_repo_context",
        _route_after_context,
        {"plan": "plan_changes", "final": "final_summary"},
    )
    graph.add_conditional_edges(
        "plan_changes",
        _route_after_plan,
        {"generate": "generate_patch", "final": "final_summary"},
    )
    graph.add_edge("generate_patch", "validate_patch")
    graph.add_conditional_edges(
        "validate_patch",
        _route_after_validation,
        {"review": "review_patch", "final": "final_summary"},
    )
    graph.add_conditional_edges(
        "review_patch",
        _route_after_review,
        {"apply": "apply_patch", "final": "final_summary"},
    )
    graph.add_conditional_edges(
        "apply_patch",
        _route_after_apply,
        {"diff": "git_diff", "final": "final_summary"},
    )
    graph.add_edge("git_diff", "final_summary")
    graph.add_edge("final_summary", END)
    return graph.compile()


def run_apply_mode(
    repo_root: str,
    user_task: str,
    planner: Planner | None = None,
    patch_generator: PatchGenerator | None = None,
) -> ToolResult:
    final_state = build_apply_graph(planner, patch_generator).invoke(initial_apply_state(repo_root, user_task))
    data = {
        "status": final_state.get("status"),
        "task_analysis": final_state.get("task_analysis"),
        "repo_context": final_state.get("repo_context"),
        "plan": final_state.get("plan"),
        "patch": final_state.get("patch"),
        "patch_validation": final_state.get("patch_validation"),
        "patch_review": final_state.get("patch_review"),
        "apply_result": final_state.get("apply_result"),
        "git_diff": final_state.get("git_diff"),
        "error_summary": final_state.get("error_summary"),
        "final_output": final_state.get("final_output"),
    }
    summary = final_state.get("final_output") or ""
    if final_state.get("status") == "failed":
        error_summary = final_state.get("error_summary") or {}
        return ToolResult.failure(
            error_summary.get("error_type", "apply_mode_failed"),
            error_summary.get("error_message", summary or "Apply Mode failed."),
            summary=summary,
            data=data,
        )
    return ToolResult.success(data=data, summary=summary)


def _route_after_analysis(state: ApplyState) -> str:
    if state.get("error_summary") or not (state.get("task_analysis") or {}).get("needs_code_change"):
        return "final"
    return "context"


def _route_after_context(state: ApplyState) -> str:
    if state.get("error_summary"):
        return "final"
    return "plan"


def _route_after_plan(state: ApplyState) -> str:
    if state.get("error_summary") or not (state.get("plan") or {}).get("needs_patch"):
        return "final"
    return "generate"


def _route_after_validation(state: ApplyState) -> str:
    if state.get("error_summary"):
        return "final"
    return "review"


def _route_after_review(state: ApplyState) -> str:
    if state.get("error_summary") or not (state.get("patch_review") or {}).get("approved"):
        return "final"
    return "apply"


def _route_after_apply(state: ApplyState) -> str:
    if state.get("error_summary") or not (state.get("apply_result") or {}).get("applied"):
        return "final"
    return "diff"


def _failed(error_type: str, error_message: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_summary": {"error_type": error_type, "error_message": error_message},
    }

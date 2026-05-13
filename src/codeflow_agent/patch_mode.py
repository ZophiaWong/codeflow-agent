"""LangGraph-backed patch-generation workflow."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from codeflow_agent.patch_generator import DeterministicPatchGenerator, PatchGenerator
from codeflow_agent.patch_validation import validate_generated_patch
from codeflow_agent.plan_mode import (
    analyze_task_node,
    build_repo_context_node,
    plan_changes_node,
)
from codeflow_agent.planner import DeterministicPlanner, Planner
from codeflow_agent.results import ToolResult
from codeflow_agent.state import PatchState, initial_patch_state

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
    "final_summary": {
        "reads": ["status", "plan", "patch", "patch_validation", "error_summary"],
        "writes": ["status", "final_output"],
    },
}


def generate_patch_node(state: PatchState, generator: PatchGenerator) -> dict[str, Any]:
    try:
        patch = generator.generate_patch(
            user_task=state["user_task"],
            task_analysis=state.get("task_analysis") or {},
            repo_context=state.get("repo_context") or {},
            plan=state.get("plan") or {},
        )
    except Exception as exc:  # pragma: no cover - defensive seam for future adapters
        return _failed("patch_generation_error", str(exc))

    return {"patch": patch, "status": "patch_generated", "error_summary": None}


def validate_patch_node(state: PatchState) -> dict[str, Any]:
    validation_result = validate_generated_patch(
        state.get("patch") or "",
        target_files=(state.get("plan") or {}).get("target_files", []),
    )
    if not validation_result.ok:
        return {
            "patch_validation": {
                "ok": False,
                "error_type": validation_result.error_type,
                "error_message": validation_result.error_message,
            },
            **_failed(validation_result.error_type or "patch_validation_error", validation_result.error_message or ""),
        }

    return {
        "patch_validation": {
            "ok": True,
            "changed_files": validation_result.data["changed_files"],
            "summary": validation_result.summary,
        },
        "status": "patch_generated",
        "error_summary": None,
    }


def final_summary_node(state: PatchState) -> dict[str, Any]:
    status = state.get("status", "failed")
    if state.get("error_summary"):
        status = "failed"
        final_output = f"Patch Mode failed: {state['error_summary']['error_message']}"
    elif status == "no_change":
        final_output = "No code change is needed for this task."
    elif status == "planned" and not (state.get("plan") or {}).get("needs_patch"):
        status = "no_change"
        final_output = "Plan does not require a patch."
    elif status == "patch_generated":
        changed_files = ", ".join((state.get("patch_validation") or {}).get("changed_files", [])) or "none"
        final_output = f"Patch generated. Changed files: {changed_files}."
    else:
        status = "failed"
        final_output = "Patch Mode failed before producing a valid patch."

    return {"status": status, "final_output": final_output}


def build_patch_graph(
    planner: Planner | None = None,
    patch_generator: PatchGenerator | None = None,
):
    planner = planner or DeterministicPlanner()
    patch_generator = patch_generator or DeterministicPatchGenerator()

    graph = StateGraph(PatchState)
    graph.add_node("analyze_task", lambda state: analyze_task_node(state, planner))
    graph.add_node("build_repo_context", build_repo_context_node)
    graph.add_node("plan_changes", lambda state: plan_changes_node(state, planner))
    graph.add_node("generate_patch", lambda state: generate_patch_node(state, patch_generator))
    graph.add_node("validate_patch", validate_patch_node)
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
    graph.add_edge("validate_patch", "final_summary")
    graph.add_edge("final_summary", END)
    return graph.compile()


def run_patch_mode(
    repo_root: str,
    user_task: str,
    planner: Planner | None = None,
    patch_generator: PatchGenerator | None = None,
) -> ToolResult:
    final_state = build_patch_graph(planner, patch_generator).invoke(initial_patch_state(repo_root, user_task))
    data = {
        "status": final_state.get("status"),
        "task_analysis": final_state.get("task_analysis"),
        "repo_context": final_state.get("repo_context"),
        "plan": final_state.get("plan"),
        "patch": final_state.get("patch"),
        "patch_validation": final_state.get("patch_validation"),
        "error_summary": final_state.get("error_summary"),
        "final_output": final_state.get("final_output"),
    }
    summary = final_state.get("final_output") or ""
    if final_state.get("status") == "failed":
        error_summary = final_state.get("error_summary") or {}
        return ToolResult.failure(
            error_summary.get("error_type", "patch_mode_failed"),
            error_summary.get("error_message", summary or "Patch Mode failed."),
            summary=summary,
            data=data,
        )
    return ToolResult.success(data=data, summary=summary)


def _route_after_analysis(state: PatchState) -> str:
    if state.get("error_summary") or not (state.get("task_analysis") or {}).get("needs_code_change"):
        return "final"
    return "context"


def _route_after_context(state: PatchState) -> str:
    if state.get("error_summary"):
        return "final"
    return "plan"


def _route_after_plan(state: PatchState) -> str:
    if state.get("error_summary") or not (state.get("plan") or {}).get("needs_patch"):
        return "final"
    return "generate"


def _failed(error_type: str, error_message: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_summary": {"error_type": error_type, "error_message": error_message},
    }

"""LangGraph-backed fix workflow with controlled pytest feedback."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from codeflow_agent.apply_mode import apply_patch_node, git_diff_node, review_patch_node
from codeflow_agent.patch_generator import DeterministicPatchGenerator, PatchGenerator
from codeflow_agent.patch_mode import validate_patch_node
from codeflow_agent.plan_mode import (
    analyze_task_node,
    build_repo_context_node,
    plan_changes_node,
)
from codeflow_agent.planner import DeterministicPlanner, Planner
from codeflow_agent.results import ToolResult
from codeflow_agent.state import FixState, initial_fix_state
from codeflow_agent.test_runner import run_tests

DEFAULT_MAX_ITERATIONS = 2

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
        "reads": ["user_task", "task_analysis", "repo_context", "plan", "test_result", "iteration_count"],
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
    "run_tests": {
        "reads": ["repo_root"],
        "writes": ["test_result", "status", "error_summary"],
    },
    "analyze_result": {
        "reads": ["test_result", "iteration_count", "max_iterations"],
        "writes": ["status", "error_summary"],
    },
    "prepare_retry": {
        "reads": ["iteration_count", "test_result"],
        "writes": [
            "iteration_count",
            "patch",
            "patch_validation",
            "patch_review",
            "apply_result",
            "git_diff",
            "status",
            "error_summary",
        ],
    },
    "final_summary": {
        "reads": ["status", "git_diff", "test_result", "iteration_count", "error_summary"],
        "writes": ["status", "final_output"],
    },
}


def generate_patch_node(state: FixState, generator: PatchGenerator) -> dict[str, Any]:
    try:
        patch = generator.generate_patch(
            user_task=state["user_task"],
            task_analysis=state.get("task_analysis") or {},
            repo_context=state.get("repo_context") or {},
            plan=state.get("plan") or {},
            test_result=state.get("test_result"),
            iteration_count=state.get("iteration_count", 1),
            error_summary=state.get("error_summary"),
        )
    except Exception as exc:  # pragma: no cover - defensive seam for future adapters
        return _failed("patch_generation_error", str(exc))

    return {"patch": patch, "status": "patch_generated", "error_summary": None}


def run_tests_node(state: FixState) -> dict[str, Any]:
    result = run_tests(state["repo_root"])
    if not result.ok:
        return {
            "test_result": {
                "ok": False,
                "error_type": result.error_type,
                "error_message": result.error_message,
                "summary": result.summary,
            },
            **_failed(result.error_type or "test_execution_failed", result.error_message or ""),
        }

    return {
        "test_result": {
            "ok": True,
            "passed": result.data["passed"],
            "returncode": result.data["returncode"],
            "command": result.data["command"],
            "execution_command": result.data["execution_command"],
            "stdout": result.data["stdout"],
            "stderr": result.data["stderr"],
            "summary": result.data["summary"],
            "truncated": result.data["truncated"],
        },
        "status": "tests_ran",
        "error_summary": None,
    }


def analyze_result_node(state: FixState) -> dict[str, Any]:
    test_result = state.get("test_result") or {}
    if test_result.get("passed") is True:
        return {"status": "success", "error_summary": None}

    summary = test_result.get("summary") or test_result.get("error_message") or "Tests failed."
    return {
        "status": "tests_failed",
        "error_summary": {
            "error_type": "tests_failed",
            "error_message": summary,
            "iteration_count": state.get("iteration_count", 1),
            "max_iterations": state.get("max_iterations", DEFAULT_MAX_ITERATIONS),
        },
    }


def prepare_retry_node(state: FixState) -> dict[str, Any]:
    return {
        "iteration_count": state.get("iteration_count", 1) + 1,
        "patch": None,
        "patch_validation": None,
        "patch_review": None,
        "apply_result": None,
        "git_diff": None,
        "status": "retrying",
        "error_summary": None,
    }


def final_summary_node(state: FixState) -> dict[str, Any]:
    status = state.get("status", "failed")
    if status == "success":
        changed_files = ", ".join((state.get("git_diff") or {}).get("changed_files", [])) or "none"
        output = (
            f"Fix succeeded. Changed files: {changed_files}. "
            f"Tests passed. Attempts: {state.get('iteration_count', 1)}."
        )
        return {"status": "success", "final_output": output}

    if status == "no_change":
        return {"status": "no_change", "final_output": "No code change is needed for this task."}

    if status == "planned" and not (state.get("plan") or {}).get("needs_patch"):
        return {"status": "no_change", "final_output": "Plan does not require a patch."}

    error_summary = state.get("error_summary") or {}
    message = error_summary.get("error_message") or "Fix Mode failed before tests passed."
    return {"status": "failed", "final_output": f"Fix Mode failed: {message}"}


def build_fix_graph(
    planner: Planner | None = None,
    patch_generator: PatchGenerator | None = None,
):
    planner = planner or DeterministicPlanner()
    patch_generator = patch_generator or DeterministicPatchGenerator()

    graph = StateGraph(FixState)
    graph.add_node("analyze_task", lambda state: analyze_task_node(state, planner))
    graph.add_node("build_repo_context", build_repo_context_node)
    graph.add_node("plan_changes", lambda state: plan_changes_node(state, planner))
    graph.add_node("generate_patch", lambda state: generate_patch_node(state, patch_generator))
    graph.add_node("validate_patch", validate_patch_node)
    graph.add_node("review_patch", review_patch_node)
    graph.add_node("apply_patch", apply_patch_node)
    graph.add_node("git_diff", git_diff_node)
    graph.add_node("run_tests", run_tests_node)
    graph.add_node("analyze_result", analyze_result_node)
    graph.add_node("prepare_retry", prepare_retry_node)
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
    graph.add_edge("git_diff", "run_tests")
    graph.add_conditional_edges(
        "run_tests",
        _route_after_tests,
        {"analyze": "analyze_result", "final": "final_summary"},
    )
    graph.add_conditional_edges(
        "analyze_result",
        _route_after_result,
        {"retry": "prepare_retry", "final": "final_summary"},
    )
    graph.add_edge("prepare_retry", "build_repo_context")
    graph.add_edge("final_summary", END)
    return graph.compile()


def run_fix_mode(
    repo_root: str,
    user_task: str,
    planner: Planner | None = None,
    patch_generator: PatchGenerator | None = None,
    *,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> ToolResult:
    final_state = build_fix_graph(planner, patch_generator).invoke(
        initial_fix_state(repo_root, user_task, max_iterations=max_iterations)
    )
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
        "test_result": final_state.get("test_result"),
        "iteration_count": final_state.get("iteration_count"),
        "max_iterations": final_state.get("max_iterations"),
        "error_summary": final_state.get("error_summary"),
        "final_output": final_state.get("final_output"),
    }
    summary = final_state.get("final_output") or ""
    if final_state.get("status") == "failed":
        error_summary = final_state.get("error_summary") or {}
        return ToolResult.failure(
            error_summary.get("error_type", "fix_mode_failed"),
            error_summary.get("error_message", summary or "Fix Mode failed."),
            summary=summary,
            data=data,
        )
    return ToolResult.success(data=data, summary=summary)


def _route_after_analysis(state: FixState) -> str:
    if state.get("error_summary") or not (state.get("task_analysis") or {}).get("needs_code_change"):
        return "final"
    return "context"


def _route_after_context(state: FixState) -> str:
    if state.get("error_summary"):
        return "final"
    return "plan"


def _route_after_plan(state: FixState) -> str:
    if state.get("error_summary") or not (state.get("plan") or {}).get("needs_patch"):
        return "final"
    return "generate"


def _route_after_validation(state: FixState) -> str:
    if state.get("error_summary"):
        return "final"
    return "review"


def _route_after_review(state: FixState) -> str:
    if state.get("error_summary") or not (state.get("patch_review") or {}).get("approved"):
        return "final"
    return "apply"


def _route_after_apply(state: FixState) -> str:
    if state.get("error_summary") or not (state.get("apply_result") or {}).get("applied"):
        return "final"
    return "diff"


def _route_after_tests(state: FixState) -> str:
    if state.get("error_summary"):
        return "final"
    return "analyze"


def _route_after_result(state: FixState) -> str:
    if state.get("status") == "success":
        return "final"
    if state.get("status") == "tests_failed" and state.get("iteration_count", 1) < state.get("max_iterations", 1):
        return "retry"
    return "final"


def _failed(error_type: str, error_message: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_summary": {"error_type": error_type, "error_message": error_message},
    }

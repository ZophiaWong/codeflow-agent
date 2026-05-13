"""LangGraph-backed planning-only workflow."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from codeflow_agent.planner import DeterministicPlanner, Planner, derive_search_terms
from codeflow_agent.results import ToolResult
from codeflow_agent.state import PlanState, initial_plan_state
from codeflow_agent.tools import list_files, read_file, search_code

MAX_CONTEXT_FILES = 5
MAX_SEARCH_MATCHES_PER_TERM = 10
MAX_CONTEXT_CHARS = 4_000

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
    "final_summary": {
        "reads": ["status", "task_analysis", "repo_context", "plan", "error_summary"],
        "writes": ["status", "final_output"],
    },
}


def analyze_task_node(state: PlanState, planner: Planner) -> dict[str, Any]:
    try:
        analysis = planner.analyze_task(state["user_task"])
    except Exception as exc:  # pragma: no cover - defensive seam for future adapters
        return _failed("task_analysis_error", str(exc))

    status = "analyzed" if analysis.get("needs_code_change") else "no_change"
    return {"task_analysis": analysis, "status": status, "error_summary": None}


def build_repo_context_node(state: PlanState) -> dict[str, Any]:
    files_result = list_files(state["repo_root"])
    if not files_result.ok:
        return _failed_from_result(files_result)

    search_terms = derive_search_terms(state["user_task"])
    searches: list[dict[str, Any]] = []
    candidate_paths: list[str] = []

    for term in search_terms:
        search_result = search_code(state["repo_root"], term, max_matches=MAX_SEARCH_MATCHES_PER_TERM)
        if not search_result.ok:
            continue

        matches = search_result.data["matches"]
        searches.append(
            {
                "query": term,
                "matches": matches,
                "total_matches": search_result.data["total_matches"],
                "truncated": search_result.data["truncated"],
            }
        )
        for match in matches:
            path = match["path"]
            if path not in candidate_paths:
                candidate_paths.append(path)

    if not candidate_paths:
        candidate_paths = files_result.data["files"][:MAX_CONTEXT_FILES]

    relevant_files: list[dict[str, Any]] = []
    for path in candidate_paths[:MAX_CONTEXT_FILES]:
        read_result = read_file(state["repo_root"], path, max_chars=MAX_CONTEXT_CHARS)
        if not read_result.ok:
            continue
        relevant_files.append(
            {
                "path": read_result.data["path"],
                "content": read_result.data["content"],
                "truncated": read_result.data["truncated"],
            }
        )

    repo_context = {
        "files": files_result.data["files"],
        "file_count": files_result.data["total_count"],
        "files_truncated": files_result.data["truncated"],
        "search_terms": search_terms,
        "searches": searches,
        "relevant_files": relevant_files,
    }
    return {"repo_context": repo_context, "status": "context_built", "error_summary": None}


def plan_changes_node(state: PlanState, planner: Planner) -> dict[str, Any]:
    try:
        plan = planner.plan_changes(
            user_task=state["user_task"],
            task_analysis=state["task_analysis"] or {},
            repo_context=state["repo_context"] or {},
        )
    except Exception as exc:  # pragma: no cover - defensive seam for future adapters
        return _failed("planning_error", str(exc))

    return {"plan": plan, "status": "planned", "error_summary": None}


def final_summary_node(state: PlanState) -> dict[str, Any]:
    status = state.get("status", "failed")
    if state.get("error_summary"):
        status = "failed"
        final_output = f"Plan Mode failed: {state['error_summary']['error_message']}"
    elif status == "no_change":
        final_output = "No code change is needed for this task."
    elif status == "planned":
        target_files = ", ".join((state.get("plan") or {}).get("target_files", [])) or "none"
        final_output = f"Plan created. Target files: {target_files}."
    else:
        status = "failed"
        final_output = "Plan Mode failed before producing a plan."

    return {"status": status, "final_output": final_output}


def build_plan_graph(planner: Planner | None = None):
    planner = planner or DeterministicPlanner()
    graph = StateGraph(PlanState)
    graph.add_node("analyze_task", lambda state: analyze_task_node(state, planner))
    graph.add_node("build_repo_context", build_repo_context_node)
    graph.add_node("plan_changes", lambda state: plan_changes_node(state, planner))
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
    graph.add_edge("plan_changes", "final_summary")
    graph.add_edge("final_summary", END)
    return graph.compile()


def run_plan_mode(repo_root: str, user_task: str, planner: Planner | None = None) -> ToolResult:
    final_state = build_plan_graph(planner).invoke(initial_plan_state(repo_root, user_task))
    data = {
        "status": final_state.get("status"),
        "task_analysis": final_state.get("task_analysis"),
        "repo_context": final_state.get("repo_context"),
        "plan": final_state.get("plan"),
        "error_summary": final_state.get("error_summary"),
        "final_output": final_state.get("final_output"),
    }
    summary = final_state.get("final_output") or ""
    if final_state.get("status") == "failed":
        error_summary = final_state.get("error_summary") or {}
        return ToolResult.failure(
            error_summary.get("error_type", "plan_mode_failed"),
            error_summary.get("error_message", summary or "Plan Mode failed."),
            summary=summary,
            data=data,
        )
    return ToolResult.success(data=data, summary=summary)


def _route_after_analysis(state: PlanState) -> str:
    if state.get("error_summary") or not (state.get("task_analysis") or {}).get("needs_code_change"):
        return "final"
    return "context"


def _route_after_context(state: PlanState) -> str:
    if state.get("error_summary"):
        return "final"
    return "plan"


def _failed(error_type: str, error_message: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_summary": {"error_type": error_type, "error_message": error_message},
    }


def _failed_from_result(result: ToolResult) -> dict[str, Any]:
    return _failed(result.error_type or "tool_error", result.error_message or result.summary)

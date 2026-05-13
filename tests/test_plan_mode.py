import hashlib
from pathlib import Path

from codeflow_agent.plan_mode import NODE_IO, build_repo_context_node, run_plan_mode
from codeflow_agent.planner import DeterministicPlanner, derive_search_terms
from codeflow_agent.state import initial_plan_state


def test_deterministic_planner_classifies_code_change():
    analysis = DeterministicPlanner().analyze_task("Fix add() for negative numbers")

    assert analysis["needs_code_change"] is True
    assert analysis["task_type"] == "code_change"


def test_deterministic_planner_classifies_no_change():
    analysis = DeterministicPlanner().analyze_task("Explain how add works")

    assert analysis["needs_code_change"] is False
    assert analysis["task_type"] == "question"


def test_derive_search_terms_prefers_task_identifiers():
    assert derive_search_terms("Fix add() for negative numbers")[:3] == ["fix", "add", "negative"]


def test_node_io_documents_reads_and_writes():
    assert NODE_IO["analyze_task"]["reads"] == ["user_task"]
    assert "final_output" in NODE_IO["final_summary"]["writes"]


def test_context_builder_finds_calculator_fixture_files():
    state = initial_plan_state("examples/calculator_bug", "Fix add() for negative numbers")
    state["task_analysis"] = {"needs_code_change": True}

    update = build_repo_context_node(state)

    paths = [item["path"] for item in update["repo_context"]["relevant_files"]]
    assert "src/calculator.py" in paths
    assert "tests/test_calculator.py" in paths


def test_plan_workflow_returns_structured_plan_for_code_change():
    result = run_plan_mode("examples/calculator_bug", "Fix add() for negative numbers")

    assert result.ok is True
    assert result.data["status"] == "planned"
    assert result.data["plan"]["needs_patch"] is True
    assert "src/calculator.py" in result.data["plan"]["target_files"]
    assert "python -m pytest -q" in result.data["plan"]["validation_strategy"]


def test_plan_workflow_skips_context_for_no_change_even_with_missing_repo():
    result = run_plan_mode("missing-repo", "Explain how add works")

    assert result.ok is True
    assert result.data["status"] == "no_change"
    assert result.data["repo_context"] is None
    assert result.data["plan"] is None


def test_plan_workflow_reports_context_failure():
    result = run_plan_mode("missing-repo", "Fix add")

    assert result.ok is False
    assert result.error_type == "repo_root_missing"
    assert result.data["status"] == "failed"


def test_plan_mode_does_not_modify_demo_fixture():
    files = [
        Path("examples/calculator_bug/src/calculator.py"),
        Path("examples/calculator_bug/tests/test_calculator.py"),
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}

    result = run_plan_mode("examples/calculator_bug", "Fix add() for negative numbers")

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert result.ok is True
    assert after == before

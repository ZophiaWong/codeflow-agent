import hashlib
from pathlib import Path

from codeflow_agent.patch_generator import DeterministicPatchGenerator
from codeflow_agent.patch_mode import NODE_IO, run_patch_mode
from codeflow_agent.patch_validation import validate_generated_patch
from codeflow_agent.plan_mode import run_plan_mode


VALID_PATCH = (
    "diff --git a/src/calculator.py b/src/calculator.py\n"
    "--- a/src/calculator.py\n"
    "+++ b/src/calculator.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a, b):\n"
    "-    return abs(a) + abs(b)\n"
    "+    return a + b\n"
)


def test_deterministic_patch_generator_returns_calculator_patch():
    plan_result = run_plan_mode("examples/calculator_bug", "Fix add() for negative numbers")

    patch = DeterministicPatchGenerator().generate_patch(
        user_task="Fix add() for negative numbers",
        task_analysis=plan_result.data["task_analysis"],
        repo_context=plan_result.data["repo_context"],
        plan=plan_result.data["plan"],
    )

    assert "diff --git a/src/calculator.py b/src/calculator.py" in patch
    assert "-    return abs(a) + abs(b)" in patch
    assert "+    return a + b" in patch


def test_validate_generated_patch_accepts_scoped_unified_diff():
    result = validate_generated_patch(VALID_PATCH, target_files=["src/calculator.py"])

    assert result.ok is True
    assert result.data["changed_files"] == ["src/calculator.py"]


def test_validate_generated_patch_rejects_empty_patch():
    result = validate_generated_patch("", target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "empty_patch"


def test_validate_generated_patch_rejects_markdown_fence():
    result = validate_generated_patch(f"```diff\n{VALID_PATCH}```", target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "markdown_fence"


def test_validate_generated_patch_rejects_absolute_path():
    patch = VALID_PATCH.replace("a/src/calculator.py b/src/calculator.py", "a/src/calculator.py /tmp/calculator.py")

    result = validate_generated_patch(patch, target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "absolute_path"


def test_validate_generated_patch_rejects_traversal():
    patch = VALID_PATCH.replace("src/calculator.py", "../calculator.py")

    result = validate_generated_patch(patch, target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "path_traversal"


def test_validate_generated_patch_rejects_forbidden_path():
    patch = VALID_PATCH.replace("src/calculator.py", ".git/config")

    result = validate_generated_patch(patch, target_files=[".git/config"])

    assert result.ok is False
    assert result.error_type == "forbidden_path"


def test_validate_generated_patch_rejects_out_of_scope_path():
    result = validate_generated_patch(VALID_PATCH, target_files=["tests/test_calculator.py"])

    assert result.ok is False
    assert result.error_type == "patch_scope"


def test_validate_generated_patch_rejects_non_unified_text():
    result = validate_generated_patch("change src/calculator.py", target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "invalid_patch_format"


def test_node_io_documents_patch_node_reads_and_writes():
    assert "patch" in NODE_IO["generate_patch"]["writes"]
    assert "patch_validation" in NODE_IO["validate_patch"]["writes"]


def test_patch_workflow_returns_valid_patch_for_calculator_fixture():
    result = run_patch_mode("examples/calculator_bug", "Fix add() for negative numbers")

    assert result.ok is True
    assert result.data["status"] == "patch_generated"
    assert result.data["patch_validation"]["ok"] is True
    assert result.data["patch_validation"]["changed_files"] == ["src/calculator.py"]
    assert "+    return a + b" in result.data["patch"]


def test_patch_workflow_skips_patch_for_no_change():
    result = run_patch_mode("missing-repo", "Explain how add works")

    assert result.ok is True
    assert result.data["status"] == "no_change"
    assert result.data["patch"] is None


def test_patch_workflow_reports_empty_generation_failure():
    result = run_patch_mode("examples/calculator_bug", "Fix multiply")

    assert result.ok is False
    assert result.error_type == "empty_patch"
    assert result.data["status"] == "failed"


def test_patch_mode_does_not_modify_demo_fixture():
    files = [
        Path("examples/calculator_bug/src/calculator.py"),
        Path("examples/calculator_bug/tests/test_calculator.py"),
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}

    result = run_patch_mode("examples/calculator_bug", "Fix add() for negative numbers")

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert result.ok is True
    assert after == before

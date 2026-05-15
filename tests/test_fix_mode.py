import shutil
import subprocess
from pathlib import Path

from codeflow_agent.fix_mode import NODE_IO, run_fix_mode
from codeflow_agent.patch_generator import PatchGenerator


def test_fix_mode_node_io_documents_test_and_retry_nodes():
    assert "test_result" in NODE_IO["run_tests"]["writes"]
    assert "error_summary" in NODE_IO["analyze_result"]["writes"]
    assert "iteration_count" in NODE_IO["prepare_retry"]["writes"]


def test_fix_mode_succeeds_on_calculator_fixture_copy(tmp_path):
    repo = _make_git_demo_repo(tmp_path)

    result = run_fix_mode(str(repo), "Fix add() for negative numbers")

    assert result.ok is True
    assert result.data["status"] == "success"
    assert result.data["test_result"]["passed"] is True
    assert result.data["iteration_count"] == 1
    assert result.data["git_diff"]["changed_files"] == ["src/calculator.py"]
    assert "return a + b" in (repo / "src/calculator.py").read_text(encoding="utf-8")


def test_fix_mode_retries_once_after_test_failure(tmp_path):
    repo = _make_git_demo_repo(tmp_path)
    generator = RetryPatchGenerator()

    result = run_fix_mode(str(repo), "Fix add() for negative numbers", patch_generator=generator)

    assert result.ok is True
    assert result.data["status"] == "success"
    assert result.data["iteration_count"] == 2
    assert result.data["test_result"]["passed"] is True
    assert generator.calls == 2
    assert "return a + b" in (repo / "src/calculator.py").read_text(encoding="utf-8")


def test_fix_mode_fails_when_retry_limit_is_reached(tmp_path):
    repo = _make_git_demo_repo(tmp_path)

    result = run_fix_mode(str(repo), "Fix add() for negative numbers", patch_generator=AlwaysFailingPatchGenerator())

    assert result.ok is False
    assert result.data["status"] == "failed"
    assert result.error_type == "tests_failed"
    assert result.data["iteration_count"] == 2
    assert result.data["test_result"]["passed"] is False


def test_fix_mode_skips_tests_for_no_change_task():
    result = run_fix_mode("missing-repo", "Explain how add works")

    assert result.ok is True
    assert result.data["status"] == "no_change"
    assert result.data["test_result"] is None


class RetryPatchGenerator(PatchGenerator):
    def __init__(self):
        self.calls = 0

    def generate_patch(
        self,
        *,
        user_task,
        task_analysis,
        repo_context,
        plan,
        test_result=None,
        iteration_count=1,
        error_summary=None,
    ):
        self.calls += 1
        if iteration_count == 1:
            return _patch("return abs(a) + abs(b)", "return a - b")
        return _patch("return a - b", "return a + b")


class AlwaysFailingPatchGenerator(PatchGenerator):
    def generate_patch(
        self,
        *,
        user_task,
        task_analysis,
        repo_context,
        plan,
        test_result=None,
        iteration_count=1,
        error_summary=None,
    ):
        if iteration_count == 1:
            return _patch("return abs(a) + abs(b)", "return a - b")
        return _patch("return a - b", "return b - a")


def _patch(old: str, new: str) -> str:
    return (
        "diff --git a/src/calculator.py b/src/calculator.py\n"
        "--- a/src/calculator.py\n"
        "+++ b/src/calculator.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def add(a, b):\n"
        f"-    {old}\n"
        f"+    {new}\n"
    )


def _make_git_demo_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "calculator_bug"
    shutil.copytree(Path("examples/calculator_bug"), repo)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    return repo

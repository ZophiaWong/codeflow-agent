import shutil
import subprocess
from pathlib import Path

from codeflow_agent.apply_mode import NODE_IO, run_apply_mode
from codeflow_agent.git_tools import git_diff
from codeflow_agent.patch_apply import apply_patch
from codeflow_agent.patch_generator import PatchGenerator
from codeflow_agent.patch_review import review_patch

VALID_PATCH = (
    "diff --git a/src/calculator.py b/src/calculator.py\n"
    "--- a/src/calculator.py\n"
    "+++ b/src/calculator.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a, b):\n"
    "-    return abs(a) + abs(b)\n"
    "+    return a + b\n"
)


def test_review_patch_approves_valid_scoped_patch():
    result = review_patch(VALID_PATCH, target_files=["src/calculator.py"])

    assert result.ok is True
    assert result.data["approved"] is True
    assert result.data["changed_files"] == ["src/calculator.py"]


def test_review_patch_rejects_markdown_fence():
    result = review_patch(f"```diff\n{VALID_PATCH}```", target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "markdown_fence"


def test_review_patch_rejects_absolute_path():
    patch = VALID_PATCH.replace("a/src/calculator.py b/src/calculator.py", "a/src/calculator.py /tmp/calculator.py")

    result = review_patch(patch, target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "absolute_path"


def test_review_patch_rejects_traversal():
    patch = VALID_PATCH.replace("src/calculator.py", "../calculator.py")

    result = review_patch(patch, target_files=["src/calculator.py"])

    assert result.ok is False
    assert result.error_type == "path_traversal"


def test_review_patch_rejects_forbidden_path():
    patch = VALID_PATCH.replace("src/calculator.py", ".git/config")

    result = review_patch(patch, target_files=[".git/config"])

    assert result.ok is False
    assert result.error_type == "forbidden_path"


def test_review_patch_rejects_out_of_plan_path():
    result = review_patch(VALID_PATCH, target_files=["tests/test_calculator.py"])

    assert result.ok is False
    assert result.error_type == "patch_scope"


def test_review_patch_rejects_oversized_patch():
    result = review_patch(VALID_PATCH, target_files=["src/calculator.py"], max_patch_bytes=10)

    assert result.ok is False
    assert result.error_type == "patch_too_large"


def test_apply_patch_refuses_without_review_approval(tmp_path):
    repo = _make_git_demo_repo(tmp_path)

    result = apply_patch(str(repo), VALID_PATCH, {"approved": False})

    assert result.ok is False
    assert result.error_type == "patch_not_approved"
    assert "abs(a) + abs(b)" in (repo / "src/calculator.py").read_text(encoding="utf-8")


def test_apply_patch_dry_run_failure_prevents_modification(tmp_path):
    repo = _make_git_demo_repo(tmp_path)
    bad_patch = VALID_PATCH.replace("return abs(a) + abs(b)", "return missing")

    result = apply_patch(str(repo), bad_patch, {"approved": True, "changed_files": ["src/calculator.py"]})

    assert result.ok is False
    assert result.error_type == "patch_dry_run_failed"
    assert "abs(a) + abs(b)" in (repo / "src/calculator.py").read_text(encoding="utf-8")


def test_apply_patch_applies_after_successful_dry_run(tmp_path):
    repo = _make_git_demo_repo(tmp_path)

    result = apply_patch(str(repo), VALID_PATCH, {"approved": True, "changed_files": ["src/calculator.py"]})

    assert result.ok is True
    assert result.data["applied"] is True
    assert "return a + b" in (repo / "src/calculator.py").read_text(encoding="utf-8")


def test_git_diff_reports_changed_files_and_summary(tmp_path):
    repo = _make_git_demo_repo(tmp_path)
    apply_patch(str(repo), VALID_PATCH, {"approved": True, "changed_files": ["src/calculator.py"]})

    result = git_diff(str(repo))

    assert result.ok is True
    assert result.data["changed_files"] == ["src/calculator.py"]
    assert "src/calculator.py" in result.data["stat"]
    assert "return a + b" in result.data["diff_preview"]


def test_apply_mode_node_io_documents_new_nodes():
    assert "patch_review" in NODE_IO["review_patch"]["writes"]
    assert "apply_result" in NODE_IO["apply_patch"]["writes"]
    assert "git_diff" in NODE_IO["git_diff"]["writes"]


def test_apply_mode_applies_patch_to_isolated_demo_repo(tmp_path):
    repo = _make_git_demo_repo(tmp_path)

    result = run_apply_mode(str(repo), "Fix add() for negative numbers")

    assert result.ok is True
    assert result.data["status"] == "applied"
    assert result.data["patch_review"]["approved"] is True
    assert result.data["apply_result"]["applied"] is True
    assert result.data["git_diff"]["changed_files"] == ["src/calculator.py"]
    assert "return a + b" in (repo / "src/calculator.py").read_text(encoding="utf-8")
    assert "test_result" not in result.data


def test_apply_mode_stops_before_apply_on_review_failure(tmp_path):
    repo = _make_git_demo_repo(tmp_path)

    result = run_apply_mode(str(repo), "Fix add() for negative numbers", patch_generator=OversizedPatchGenerator())

    assert result.ok is False
    assert result.error_type == "too_many_changed_lines"
    assert result.data["apply_result"] is None
    assert "abs(a) + abs(b)" in (repo / "src/calculator.py").read_text(encoding="utf-8")


class OversizedPatchGenerator(PatchGenerator):
    def generate_patch(self, user_task, task_analysis, repo_context, plan):  # noqa: ANN001
        additions = "\n".join(f"+line {index}" for index in range(501))
        return (
            "diff --git a/src/calculator.py b/src/calculator.py\n"
            "--- a/src/calculator.py\n"
            "+++ b/src/calculator.py\n"
            "@@ -1,2 +1,501 @@\n"
            f"{additions}\n"
        )


def _make_git_demo_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "calculator_bug"
    shutil.copytree(Path("examples/calculator_bug"), repo)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    return repo

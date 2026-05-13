from pathlib import Path

import pytest

from codeflow_agent.paths import PathSafetyError, resolve_inside_repo, resolve_repo_root
from codeflow_agent.results import ToolResult


def test_tool_result_success_to_dict():
    result = ToolResult.success(data={"files": ["a.py"]}, summary="ok")

    assert result.to_dict() == {
        "ok": True,
        "data": {"files": ["a.py"]},
        "summary": "ok",
        "error_type": None,
        "error_message": None,
    }


def test_tool_result_failure_to_dict():
    result = ToolResult.failure("path_traversal", "Path traversal is not allowed")

    assert result.to_dict()["ok"] is False
    assert result.to_dict()["error_type"] == "path_traversal"
    assert result.to_dict()["error_message"] == "Path traversal is not allowed"


def test_resolve_repo_root_requires_existing_directory(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(PathSafetyError) as exc_info:
        resolve_repo_root(missing)

    assert exc_info.value.error_type == "repo_root_missing"


def test_resolve_inside_repo_accepts_relative_path(tmp_path):
    file_path = tmp_path / "src" / "app.py"
    file_path.parent.mkdir()
    file_path.write_text("print('ok')\n", encoding="utf-8")

    assert resolve_inside_repo(tmp_path, "src/app.py") == file_path.resolve()


def test_resolve_inside_repo_rejects_absolute_path(tmp_path):
    absolute = Path("/tmp/outside.py")

    with pytest.raises(PathSafetyError) as exc_info:
        resolve_inside_repo(tmp_path, absolute)

    assert exc_info.value.error_type == "absolute_path"


def test_resolve_inside_repo_rejects_traversal(tmp_path):
    with pytest.raises(PathSafetyError) as exc_info:
        resolve_inside_repo(tmp_path, "../outside.py")

    assert exc_info.value.error_type == "path_traversal"


def test_resolve_inside_repo_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside-target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not supported")

    with pytest.raises(PathSafetyError) as exc_info:
        resolve_inside_repo(tmp_path, "escape/file.py")

    assert exc_info.value.error_type == "path_outside_repo"

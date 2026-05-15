import json
import shutil
import subprocess
from pathlib import Path

from codeflow_agent.cli import main


def test_cli_inspect_outputs_tool_result(tmp_path, capsys):
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")

    exit_code = main(["inspect", "--repo", str(tmp_path)])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["data"]["files"] == ["app.py"]


def test_cli_read_outputs_file_content(tmp_path, capsys):
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")

    exit_code = main(["read", "--repo", str(tmp_path), "app.py"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["data"]["content"] == "print('ok')\n"


def test_cli_search_outputs_matches(tmp_path, capsys):
    (tmp_path / "app.py").write_text("needle = True\n", encoding="utf-8")

    exit_code = main(["search", "--repo", str(tmp_path), "needle"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["data"]["matches"][0]["path"] == "app.py"


def test_cli_returns_nonzero_for_tool_failure(tmp_path, capsys):
    exit_code = main(["read", "--repo", str(tmp_path), "missing.py"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["ok"] is False


def test_cli_plan_outputs_json_tool_result(capsys):
    exit_code = main(["plan", "--repo", "examples/calculator_bug", "Fix add() for negative numbers"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["data"]["status"] == "planned"
    assert "src/calculator.py" in output["data"]["plan"]["target_files"]


def test_cli_patch_outputs_json_tool_result(capsys):
    exit_code = main(["patch", "--repo", "examples/calculator_bug", "Fix add() for negative numbers"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["data"]["status"] == "patch_generated"
    assert "+    return a + b" in output["data"]["patch"]


def test_cli_apply_outputs_json_tool_result(tmp_path, capsys):
    repo = tmp_path / "calculator_bug"
    shutil.copytree(Path("examples/calculator_bug"), repo)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)

    exit_code = main(["apply", "--repo", str(repo), "Fix add() for negative numbers"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["data"]["status"] == "applied"
    assert output["data"]["git_diff"]["changed_files"] == ["src/calculator.py"]


def test_cli_fix_outputs_json_tool_result(tmp_path, capsys):
    repo = tmp_path / "calculator_bug"
    shutil.copytree(Path("examples/calculator_bug"), repo)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)

    exit_code = main(["fix", "--repo", str(repo), "Fix add() for negative numbers"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["data"]["status"] == "success"
    assert output["data"]["test_result"]["passed"] is True

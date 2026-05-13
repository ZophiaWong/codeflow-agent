import json

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

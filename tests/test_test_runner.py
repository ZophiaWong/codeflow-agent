import subprocess
import sys

from codeflow_agent.test_runner import run_tests


def test_run_tests_passes_with_default_command(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    result = run_tests(str(tmp_path))

    assert result.ok is True
    assert result.data["passed"] is True
    assert result.data["command"] == ["python", "-m", "pytest", "-q"]


def test_run_tests_reports_pytest_failure_as_test_result(tmp_path):
    (tmp_path / "test_fail.py").write_text("def test_fail():\n    assert False\n", encoding="utf-8")

    result = run_tests(str(tmp_path))

    assert result.ok is True
    assert result.data["passed"] is False
    assert result.data["returncode"] != 0
    assert "Tests failed" in result.summary


def test_run_tests_rejects_disallowed_command(tmp_path):
    result = run_tests(str(tmp_path), ["echo", "hello"])

    assert result.ok is False
    assert result.error_type == "disallowed_test_command"


def test_run_tests_reports_timeout(tmp_path):
    (tmp_path / "test_slow.py").write_text("import time\n\ndef test_slow():\n    time.sleep(5)\n", encoding="utf-8")

    result = run_tests(str(tmp_path), timeout_seconds=1)

    assert result.ok is False
    assert result.error_type == "test_timeout"


def test_run_tests_uses_shell_false(tmp_path, monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="ok\n", stderr="")

    monkeypatch.setattr("codeflow_agent.test_runner.subprocess.run", fake_run)

    result = run_tests(str(tmp_path), [sys.executable, "-m", "pytest", "-q"])

    assert result.ok is True
    assert calls[0][1]["shell"] is False

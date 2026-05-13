from pathlib import Path


def test_pyproject_limits_pytest_collection_to_main_tests_directory():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'testpaths = ["tests"]' in pyproject

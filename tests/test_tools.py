from codeflow_agent.tools import list_files, read_file, search_code


def test_list_files_ignores_forbidden_directories(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("ignored\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "app.pyc").write_bytes(b"\x00")

    result = list_files(tmp_path)

    assert result.ok is True
    assert result.data["files"] == ["src/app.py"]


def test_list_files_truncates_output(tmp_path):
    for index in range(3):
        (tmp_path / f"{index}.py").write_text("x\n", encoding="utf-8")

    result = list_files(tmp_path, max_files=2)

    assert result.ok is True
    assert result.data["files"] == ["0.py", "1.py"]
    assert result.data["total_count"] == 3
    assert result.data["truncated"] is True


def test_read_file_reads_text_inside_repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = read_file(tmp_path, "src/app.py")

    assert result.ok is True
    assert result.data["path"] == "src/app.py"
    assert "return a + b" in result.data["content"]


def test_read_file_rejects_missing_file(tmp_path):
    result = read_file(tmp_path, "missing.py")

    assert result.ok is False
    assert result.error_type == "file_missing"


def test_read_file_rejects_binary_file(tmp_path):
    (tmp_path / "data.bin").write_bytes(b"abc\x00def")

    result = read_file(tmp_path, "data.bin")

    assert result.ok is False
    assert result.error_type == "binary_file"


def test_read_file_rejects_path_traversal(tmp_path):
    result = read_file(tmp_path, "../outside.py")

    assert result.ok is False
    assert result.error_type == "path_traversal"


def test_read_file_truncates_content(tmp_path):
    (tmp_path / "large.txt").write_text("abcdef", encoding="utf-8")

    result = read_file(tmp_path, "large.txt", max_chars=3)

    assert result.ok is True
    assert result.data["content"] == "abc"
    assert result.data["truncated"] is True


def test_search_code_returns_paths_line_numbers_and_snippets(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "calculator.py").write_text(
        "def add(a, b):\n    return abs(a) + abs(b)\n",
        encoding="utf-8",
    )

    result = search_code(tmp_path, "abs")

    assert result.ok is True
    assert result.data["matches"] == [
        {"path": "src/calculator.py", "line_number": 2, "snippet": "return abs(a) + abs(b)"}
    ]


def test_search_code_skips_binary_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("needle = True\n", encoding="utf-8")
    (tmp_path / "binary.bin").write_bytes(b"needle\x00")

    result = search_code(tmp_path, "needle")

    assert result.ok is True
    assert len(result.data["matches"]) == 1
    assert result.data["skipped_files"] == 1


def test_search_code_truncates_matches(tmp_path):
    (tmp_path / "app.py").write_text("needle\nneedle\nneedle\n", encoding="utf-8")

    result = search_code(tmp_path, "needle", max_matches=2)

    assert result.ok is True
    assert len(result.data["matches"]) == 2
    assert result.data["total_matches"] == 3
    assert result.data["truncated"] is True


def test_search_code_rejects_empty_query(tmp_path):
    result = search_code(tmp_path, "")

    assert result.ok is False
    assert result.error_type == "empty_query"

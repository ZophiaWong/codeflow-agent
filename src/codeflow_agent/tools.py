"""Read-only repository tools."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from codeflow_agent.paths import (
    FORBIDDEN_DIRS,
    PathSafetyError,
    has_forbidden_part,
    relative_to_repo,
    resolve_inside_repo,
    resolve_repo_root,
)
from codeflow_agent.results import ToolResult

DEFAULT_ENCODING = "utf-8"
DEFAULT_PREFIX_BYTES = 4096
DEFAULT_MAX_FILES = 200
DEFAULT_MAX_CHARS = 20_000
DEFAULT_MAX_MATCHES = 50


def list_files(
    repo_root: str | Path,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    forbidden_dirs: Iterable[str] = FORBIDDEN_DIRS,
) -> ToolResult:
    try:
        root = resolve_repo_root(repo_root)
        forbidden = set(forbidden_dirs)
        files: list[str] = []
        total_count = 0

        for current_root_str, dirs, filenames in os.walk(root):
            current_root = Path(current_root_str)
            rel_dir = current_root.relative_to(root)
            if has_forbidden_part(rel_dir, forbidden):
                dirs[:] = []
                continue

            dirs[:] = sorted(
                dirname
                for dirname in dirs
                if dirname not in forbidden and (current_root / dirname).resolve(strict=False).is_relative_to(root)
            )

            for filename in sorted(filenames):
                path = current_root / filename
                rel_path = path.relative_to(root)
                if has_forbidden_part(rel_path, forbidden):
                    continue
                if not path.resolve(strict=False).is_relative_to(root):
                    continue
                total_count += 1
                if len(files) < max_files:
                    files.append(rel_path.as_posix())

        truncated = total_count > len(files)
        summary = f"Listed {len(files)} of {total_count} files." if truncated else f"Listed {total_count} files."
        return ToolResult.success(
            data={
                "repo_root": str(root),
                "files": files,
                "total_count": total_count,
                "truncated": truncated,
            },
            summary=summary,
        )
    except PathSafetyError as exc:
        return ToolResult.failure(exc.error_type, exc.error_message)


def read_file(
    repo_root: str | Path,
    path: str | Path,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    encoding: str = DEFAULT_ENCODING,
) -> ToolResult:
    try:
        root = resolve_repo_root(repo_root)
        target = resolve_inside_repo(root, path)
        relative_path = relative_to_repo(root, target)

        if has_forbidden_part(relative_path):
            return ToolResult.failure("forbidden_path", f"Path is inside a forbidden directory: {relative_path}")
        if not target.exists():
            return ToolResult.failure("file_missing", f"File does not exist: {relative_path}")
        if not target.is_file():
            return ToolResult.failure("not_file", f"Path is not a file: {relative_path}")

        text_result = _read_text(target, max_chars=max_chars, encoding=encoding)
        if not text_result.ok:
            return text_result

        content = text_result.data["content"]
        truncated = text_result.data["truncated"]
        summary = f"Read {len(content)} characters from {relative_path}."
        if truncated:
            summary += " Output was truncated."

        return ToolResult.success(
            data={
                "path": relative_path,
                "content": content,
                "encoding": encoding,
                "size_bytes": target.stat().st_size,
                "truncated": truncated,
            },
            summary=summary,
        )
    except PathSafetyError as exc:
        return ToolResult.failure(exc.error_type, exc.error_message)


def search_code(
    repo_root: str | Path,
    query: str,
    *,
    max_matches: int = DEFAULT_MAX_MATCHES,
    encoding: str = DEFAULT_ENCODING,
) -> ToolResult:
    if not query:
        return ToolResult.failure("empty_query", "Search query must not be empty.")

    try:
        root = resolve_repo_root(repo_root)
        matches: list[dict[str, object]] = []
        total_matches = 0
        searched_files = 0
        skipped_files = 0

        for current_root_str, dirs, filenames in os.walk(root):
            current_root = Path(current_root_str)
            rel_dir = current_root.relative_to(root)
            if has_forbidden_part(rel_dir):
                dirs[:] = []
                continue

            dirs[:] = sorted(
                dirname
                for dirname in dirs
                if dirname not in FORBIDDEN_DIRS and (current_root / dirname).resolve(strict=False).is_relative_to(root)
            )

            for filename in sorted(filenames):
                target = current_root / filename
                relative_path = target.relative_to(root).as_posix()
                if has_forbidden_part(relative_path):
                    continue
                if not target.resolve(strict=False).is_relative_to(root):
                    continue
                if not _is_text_file(target, encoding=encoding):
                    skipped_files += 1
                    continue

                searched_files += 1
                try:
                    with target.open("r", encoding=encoding) as handle:
                        for line_number, line in enumerate(handle, start=1):
                            if query in line:
                                total_matches += 1
                                if len(matches) < max_matches:
                                    matches.append(
                                        {
                                            "path": relative_path,
                                            "line_number": line_number,
                                            "snippet": _make_snippet(line, query),
                                        }
                                    )
                except UnicodeDecodeError:
                    skipped_files += 1

        truncated = total_matches > len(matches)
        summary = f"Found {len(matches)} of {total_matches} matches in {searched_files} files."
        if truncated:
            summary += " Output was truncated."
        if skipped_files:
            summary += f" Skipped {skipped_files} unreadable files."

        return ToolResult.success(
            data={
                "query": query,
                "matches": matches,
                "total_matches": total_matches,
                "searched_files": searched_files,
                "skipped_files": skipped_files,
                "truncated": truncated,
            },
            summary=summary,
        )
    except PathSafetyError as exc:
        return ToolResult.failure(exc.error_type, exc.error_message)


def _is_text_file(path: Path, *, encoding: str = DEFAULT_ENCODING) -> bool:
    try:
        with path.open("rb") as handle:
            prefix = handle.read(DEFAULT_PREFIX_BYTES)
    except OSError:
        return False
    if b"\x00" in prefix:
        return False
    try:
        prefix.decode(encoding)
    except UnicodeDecodeError:
        return False
    return True


def _read_text(path: Path, *, max_chars: int, encoding: str) -> ToolResult:
    if not _is_text_file(path, encoding=encoding):
        return ToolResult.failure("binary_file", f"File is not readable text: {path.name}")
    try:
        with path.open("r", encoding=encoding) as handle:
            content = handle.read(max_chars + 1)
    except UnicodeDecodeError:
        return ToolResult.failure("unsupported_decoding", f"File cannot be decoded as {encoding}: {path.name}")
    except OSError as exc:
        return ToolResult.failure("read_error", str(exc))

    truncated = len(content) > max_chars
    return ToolResult.success(data={"content": content[:max_chars], "truncated": truncated})


def _make_snippet(line: str, query: str, *, max_chars: int = 160) -> str:
    stripped = line.strip()
    if len(stripped) <= max_chars:
        return stripped

    index = stripped.find(query)
    if index == -1:
        return stripped[: max_chars - 3] + "..."

    half_window = max((max_chars - len(query)) // 2, 0)
    start = max(index - half_window, 0)
    end = min(start + max_chars, len(stripped))
    start = max(end - max_chars, 0)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(stripped) else ""
    body_limit = max_chars - len(prefix) - len(suffix)
    return prefix + stripped[start : start + body_limit] + suffix

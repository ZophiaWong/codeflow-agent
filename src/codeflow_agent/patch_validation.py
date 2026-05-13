"""Patch validation helpers for generated unified diffs."""

from __future__ import annotations

from pathlib import PurePosixPath

from codeflow_agent.paths import FORBIDDEN_DIRS, has_forbidden_part
from codeflow_agent.results import ToolResult


def validate_generated_patch(patch: str, *, target_files: list[str]) -> ToolResult:
    if not patch.strip():
        return ToolResult.failure("empty_patch", "Generated patch must not be empty.")
    if "```" in patch:
        return ToolResult.failure("markdown_fence", "Generated patch must not contain Markdown fences.")

    lines = patch.splitlines()
    changed_files: list[str] = []
    saw_diff_header = False
    saw_file_header = False
    saw_hunk = False
    target_file_set = set(target_files)

    for line in lines:
        if line.startswith("diff --git "):
            saw_diff_header = True
            result = _parse_diff_git_line(line)
            if not result.ok:
                return result
            for path in result.data["paths"]:
                path_result = _validate_changed_path(path, target_file_set)
                if not path_result.ok:
                    return path_result
                if path not in changed_files:
                    changed_files.append(path)
        elif line.startswith("--- ") or line.startswith("+++ "):
            saw_file_header = True
            path = line[4:].strip().split("\t", 1)[0]
            if path == "/dev/null":
                return ToolResult.failure("unsupported_path", "New or deleted files are not supported in Milestone 3.")
            normalized = _strip_diff_prefix(path)
            path_result = _validate_changed_path(normalized, target_file_set)
            if not path_result.ok:
                return path_result
        elif line.startswith("@@ "):
            saw_hunk = True

    if not saw_diff_header or not saw_file_header or not saw_hunk:
        return ToolResult.failure("invalid_patch_format", "Patch must be a unified diff with file and hunk headers.")
    if not changed_files:
        return ToolResult.failure("invalid_patch_format", "Patch must include at least one changed file.")

    return ToolResult.success(
        data={
            "ok": True,
            "changed_files": changed_files,
        },
        summary=f"Validated patch for {len(changed_files)} file(s).",
    )


def _parse_diff_git_line(line: str) -> ToolResult:
    parts = line.split()
    if len(parts) != 4:
        return ToolResult.failure("invalid_patch_format", "diff --git header must include old and new paths.")

    old_path = _strip_diff_prefix(parts[2])
    new_path = _strip_diff_prefix(parts[3])
    for path in (old_path, new_path):
        pure_path = PurePosixPath(path)
        if pure_path.is_absolute():
            return ToolResult.failure("absolute_path", f"Patch path must be repository-relative: {path}")
        if ".." in pure_path.parts:
            return ToolResult.failure("path_traversal", f"Patch path traversal is not allowed: {path}")

    if old_path != new_path:
        return ToolResult.failure("unsupported_path", "Renames are not supported in Milestone 3.")
    return ToolResult.success(data={"paths": [old_path]})


def _strip_diff_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _validate_changed_path(path: str, target_files: set[str]) -> ToolResult:
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        return ToolResult.failure("absolute_path", f"Patch path must be repository-relative: {path}")
    if ".." in pure_path.parts:
        return ToolResult.failure("path_traversal", f"Patch path traversal is not allowed: {path}")
    if has_forbidden_part(path, FORBIDDEN_DIRS):
        return ToolResult.failure("forbidden_path", f"Patch path is forbidden: {path}")
    if target_files and path not in target_files:
        return ToolResult.failure("patch_scope", f"Patch path is outside the plan target files: {path}")
    return ToolResult.success()

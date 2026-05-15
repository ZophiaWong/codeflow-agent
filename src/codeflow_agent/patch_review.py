"""Patch review checks before repository modification."""

from __future__ import annotations

from codeflow_agent.patch_validation import validate_generated_patch
from codeflow_agent.results import ToolResult

MAX_PATCH_BYTES = 50_000
MAX_CHANGED_FILES = 5
MAX_CHANGED_LINES = 500


def review_patch(
    patch: str,
    *,
    target_files: list[str],
    max_patch_bytes: int = MAX_PATCH_BYTES,
    max_changed_files: int = MAX_CHANGED_FILES,
    max_changed_lines: int = MAX_CHANGED_LINES,
) -> ToolResult:
    validation = validate_generated_patch(patch, target_files=target_files)
    if not validation.ok:
        return ToolResult.failure(
            validation.error_type or "patch_review_failed",
            validation.error_message or "Patch review failed.",
        )

    patch_size = len(patch.encode("utf-8"))
    if patch_size > max_patch_bytes:
        return ToolResult.failure(
            "patch_too_large",
            f"Patch exceeds maximum size: {patch_size} bytes > {max_patch_bytes} bytes.",
        )

    changed_files = validation.data["changed_files"]
    if len(changed_files) > max_changed_files:
        return ToolResult.failure(
            "too_many_changed_files",
            f"Patch changes too many files: {len(changed_files)} > {max_changed_files}.",
        )

    changed_lines = _count_changed_lines(patch)
    if changed_lines > max_changed_lines:
        return ToolResult.failure(
            "too_many_changed_lines",
            f"Patch changes too many lines: {changed_lines} > {max_changed_lines}.",
        )

    return ToolResult.success(
        data={
            "approved": True,
            "changed_files": changed_files,
            "patch_bytes": patch_size,
            "changed_lines": changed_lines,
            "limits": {
                "max_patch_bytes": max_patch_bytes,
                "max_changed_files": max_changed_files,
                "max_changed_lines": max_changed_lines,
            },
        },
        summary=f"Patch review approved {len(changed_files)} file(s), {changed_lines} changed line(s).",
    )


def _count_changed_lines(patch: str) -> int:
    changed = 0
    for line in patch.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            changed += 1
    return changed

"""Path safety helpers for repository-local file access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_DIRS = frozenset({".git", ".venv", "__pycache__", ".pytest_cache"})


@dataclass(frozen=True)
class PathSafetyError(Exception):
    error_type: str
    error_message: str

    def __str__(self) -> str:
        return self.error_message


def resolve_repo_root(repo_root: str | Path) -> Path:
    root = Path(repo_root).expanduser()
    try:
        resolved = root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PathSafetyError("repo_root_missing", f"Repository root does not exist: {repo_root}") from exc

    if not resolved.is_dir():
        raise PathSafetyError("repo_root_not_directory", f"Repository root is not a directory: {repo_root}")
    return resolved


def resolve_inside_repo(repo_root: str | Path, relative_path: str | Path = ".") -> Path:
    root = resolve_repo_root(repo_root)
    path = Path(relative_path)

    if path.is_absolute():
        raise PathSafetyError("absolute_path", f"Path must be repository-relative: {relative_path}")
    if ".." in path.parts:
        raise PathSafetyError("path_traversal", f"Path traversal is not allowed: {relative_path}")

    resolved = (root / path).resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise PathSafetyError("path_outside_repo", f"Path resolves outside repo_root: {relative_path}")
    return resolved


def relative_to_repo(repo_root: str | Path, path: str | Path) -> str:
    root = resolve_repo_root(repo_root)
    resolved = Path(path).resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise PathSafetyError("path_outside_repo", f"Path resolves outside repo_root: {path}")
    return resolved.relative_to(root).as_posix()


def has_forbidden_part(relative_path: str | Path, forbidden_dirs: set[str] | frozenset[str] = FORBIDDEN_DIRS) -> bool:
    return any(part in forbidden_dirs for part in Path(relative_path).parts)

"""Minimal read-only CLI for repository inspection."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from codeflow_agent.apply_mode import run_apply_mode
from codeflow_agent.patch_mode import run_patch_mode
from codeflow_agent.plan_mode import run_plan_mode
from codeflow_agent.tools import list_files, read_file, search_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codeflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="List repository files")
    inspect_parser.add_argument("--repo", required=True, help="Repository root")
    inspect_parser.add_argument("--max-files", type=int, default=200)

    read_parser = subparsers.add_parser("read", help="Read a text file")
    read_parser.add_argument("--repo", required=True, help="Repository root")
    read_parser.add_argument("path", help="Repository-relative file path")
    read_parser.add_argument("--max-chars", type=int, default=20_000)

    search_parser = subparsers.add_parser("search", help="Search repository code")
    search_parser.add_argument("--repo", required=True, help="Repository root")
    search_parser.add_argument("query", help="Text to search for")
    search_parser.add_argument("--max-matches", type=int, default=50)

    plan_parser = subparsers.add_parser("plan", help="Create a read-only change plan")
    plan_parser.add_argument("--repo", required=True, help="Repository root")
    plan_parser.add_argument("task", help="Development task to plan")

    patch_parser = subparsers.add_parser("patch", help="Generate a unified diff without applying it")
    patch_parser.add_argument("--repo", required=True, help="Repository root")
    patch_parser.add_argument("task", help="Development task to patch")

    apply_parser = subparsers.add_parser("apply", help="Review and apply a generated unified diff")
    apply_parser.add_argument("--repo", required=True, help="Repository root")
    apply_parser.add_argument("task", help="Development task to apply")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        result = list_files(args.repo, max_files=args.max_files)
    elif args.command == "read":
        result = read_file(args.repo, args.path, max_chars=args.max_chars)
    elif args.command == "search":
        result = search_code(args.repo, args.query, max_matches=args.max_matches)
    elif args.command == "plan":
        result = run_plan_mode(args.repo, args.task)
    elif args.command == "patch":
        result = run_patch_mode(args.repo, args.task)
    elif args.command == "apply":
        result = run_apply_mode(args.repo, args.task)
    else:
        parser.error(f"unknown command: {args.command}")

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

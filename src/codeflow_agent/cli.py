"""Minimal read-only CLI for repository inspection."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

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
    else:
        parser.error(f"unknown command: {args.command}")

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

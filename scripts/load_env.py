#!/usr/bin/env python3
"""Utility to emit `export` statements for environment variables."""

from __future__ import annotations

import argparse
import shlex
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Iterable


def parse_line(line: str) -> tuple[str, str] | None:
    """Parse a line of KEY=VALUE syntax.

    Returns a (key, value) tuple or None if the line should be ignored.
    """

    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if stripped.startswith("export "):
        stripped = stripped[len("export "):].lstrip()

    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None

    if (value.startswith(('"', "'"))
            and value.endswith(('"', "'"))
            and len(value) >= 2):
        value = value[1:-1]

    return key, value


def load_env_files(paths: Iterable[Path]) -> OrderedDict[str, str]:
    values: OrderedDict[str, str] = OrderedDict()
    for path in paths:
        if not path.exists():
            continue
        try:
            lines = path.read_text().splitlines()
        except OSError as exc:
            print(f"Warning: unable to read {path}: {exc}", file=sys.stderr)
            continue
        for raw_line in lines:
            parsed = parse_line(raw_line)
            if not parsed:
                continue
            key, value = parsed
            values[key] = value
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit export statements for env files")
    parser.add_argument(
        "paths",
        nargs="*",
        default=[Path(".env"), Path("read.env")],
        type=Path,
        help="Env files to load (default: .env and read.env)",
    )
    args = parser.parse_args(argv)

    env_values = load_env_files(args.paths)
    if not env_values:
        print("No environment variables found.", file=sys.stderr)
        return 1

    for key, value in env_values.items():
        print(f"export {key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

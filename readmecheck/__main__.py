"""CLI: run a README's promises and report the ones it broke."""

from __future__ import annotations

import argparse
import os
import sys

from .parse import parse, parse_claims
from .run import DEFAULT_TIMEOUT, check
from .update import diff, update

RED = "\033[31m"
GREEN = "\033[32m"
DIM = "\033[2m"
RESET = "\033[0m"


def _colour(enabled: bool):
    if enabled:
        return RED, GREEN, DIM, RESET
    return "", "", "", ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="readme-check",
        description="Run the console blocks in a README and check they still "
                    "produce what the README says they do.")
    parser.add_argument("readme", nargs="?", default="README.md")
    parser.add_argument("--cwd", default=None,
                        help="run the commands here (default: the README's directory)")
    parser.add_argument("--tolerance", type=float, default=3.0,
                        help="how far a ~number may move, as a factor (default: 3)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--update", action="store_true",
                        help="write the numbers that moved back into the README. "
                             "Keeps ~ and ... exactly where the author put them.")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)

    red, green, dim, reset = _colour(
        not args.no_color and sys.stdout.isatty())

    if not os.path.exists(args.readme):
        print(f"readme-check: {args.readme}: no such file", file=sys.stderr)
        return 2

    with open(args.readme, encoding="utf-8") as handle:
        markdown = handle.read()

    root = args.cwd or os.path.dirname(os.path.abspath(args.readme)) or "."

    if args.update:
        return _update(args, markdown, root, red, green, dim, reset)

    result = check(parse(markdown), root=root, tolerance=args.tolerance,
                   timeout=args.timeout, claims=parse_claims(markdown))

    for bad in result.mismatches:
        print(f"{red}✗{reset} {args.readme}:{bad.line}  $ {bad.command}")
        print(f"  {bad.reason}")
        if bad.actual:
            print(f"{dim}  --- the README promises{reset}")
            for line in bad.expected.splitlines():
                print(f"{dim}  |{reset} {line}")
            print(f"{dim}  --- what actually happened{reset}")
            for line in bad.actual.splitlines()[:12]:
                print(f"  | {line}")
        print()

    total = result.checked
    broken = len(result.mismatches)

    if broken:
        print(f"{red}{broken} of {total} promise(s) broken{reset}"
              f"{dim}, {result.skipped} skipped{reset}")
        return 1

    print(f"{green}{total} promise(s) kept{reset}"
          f"{dim}, {result.skipped} skipped{reset}")
    return 0


def _update(args, markdown: str, root: str,
            red: str, green: str, dim: str, reset: str) -> int:
    """`--update` does not ask. The flag was the question, and you typed it.

    It shows the diff regardless, because a tool that edits your README and
    tells you nothing about it is a tool you have to check by hand afterwards,
    which is the work it was supposed to save.
    """
    done = update(markdown, root=root, tolerance=args.tolerance,
                  timeout=args.timeout)

    for line in diff(markdown, done.text, args.readme):
        line = line.rstrip("\n")
        if line.startswith("+") and not line.startswith("+++"):
            print(f"{green}{line}{reset}")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"{red}{line}{reset}")
        else:
            print(f"{dim}{line}{reset}")

    if done.changed:
        with open(args.readme, "w", encoding="utf-8") as handle:
            handle.write(done.text)

    for bad in done.unresolved:
        print(f"{red}✗{reset} {args.readme}:{bad.line}  $ {bad.command}")
        print(f"  {bad.reason}")

    if done.unresolved:
        print(f"\n{green}{done.edits} line(s) updated{reset}"
              f"{red}, {len(done.unresolved)} left for a human{reset}")
        return 1

    if not done.changed:
        print(f"{green}nothing to update{reset}"
              f"{dim} -- the README already tells the truth{reset}")
        return 0

    print(f"{green}{done.edits} line(s) updated in {args.readme}{reset}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Run the commands and collect what they actually did.

A README's console block is a promise about a *shell session*, so the commands
run in order, in one working directory, with stdout and stderr merged -- because
that is what the author saw when they pasted it.

Nothing here is sandboxed. A README that says `$ rm -rf /` will get exactly what
it asked for. That is a deliberate non-feature: this tool exists to run the
commands you tell people to run, and pretending to protect you from your own
documentation would only hide the problem.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .match import Mismatch, compare
from .parse import Block

DEFAULT_TIMEOUT = 300.0


@dataclass
class Result:
    checked: int = 0
    skipped: int = 0
    mismatches: list[Mismatch] = None       # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.mismatches is None:
            self.mismatches = []

    @property
    def ok(self) -> bool:
        return not self.mismatches


def run_block(block: Block, root: str, tolerance: float,
              timeout: float, result: Result) -> None:
    if block.skip:
        result.skipped += len(block.commands)
        return

    cwd = os.path.join(root, block.cwd) if block.cwd else root
    limit = block.timeout or timeout

    for command in block.commands:
        # Every command in the block runs, including the ones that promise no
        # output. A console block is a *session*: it has state. The README's
        #
        #     $ btreedb put library.db hitchhiker 42
        #     $ btreedb get library.db hitchhiker
        #     42
        #
        # only makes sense if the `put` happens. Skipping it because it promised
        # nothing produces a spectacular false accusation -- the `get` returns
        # "not found" and the tool reports the README as a liar. It did that to
        # me on the first run, which is the most useful thing it has done so far.
        verify = bool(command.expected)

        try:
            completed = subprocess.run(
                command.command, shell=True, cwd=cwd,
                capture_output=True, text=True, timeout=limit,
            )
            actual = (completed.stdout + completed.stderr).splitlines()
        except subprocess.TimeoutExpired:
            if verify:
                result.checked += 1
                result.mismatches.append(Mismatch(
                    line=command.line, command=command.command,
                    expected="\n".join(command.expected), actual="",
                    reason=f"timed out after {limit:.0f}s"))
            continue
        except OSError as exc:
            if verify:
                result.checked += 1
                result.mismatches.append(Mismatch(
                    line=command.line, command=command.command,
                    expected="\n".join(command.expected), actual="",
                    reason=f"could not run: {exc}"))
            continue

        if not verify:
            result.skipped += 1        # ran, to keep the session honest; nothing claimed
            continue

        result.checked += 1
        reason = compare(command.expected, actual, tolerance=tolerance)
        if reason:
            result.mismatches.append(Mismatch(
                line=command.line, command=command.command,
                expected="\n".join(command.expected),
                actual="\n".join(actual),
                reason=reason))


def check(blocks: list[Block], root: str, tolerance: float,
          timeout: float = DEFAULT_TIMEOUT) -> Result:
    result = Result()
    for block in blocks:
        run_block(block, root, tolerance, timeout, result)
    return result

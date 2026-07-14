"""`--update`: write the truth back into the README.

The tool spends the rest of its time telling you a number is wrong. This is the
part that fixes it, and the temptation here is to be clever -- to take the real
output and paste it over the promised output, the way a snapshot test does.

That would be wrong, and it is worth being precise about why.

A README is not a snapshot. `pytest -q` prints `39 passed in 4.51s`; the README
says `39 passed`, because the duration is not a claim and printing it would only
guarantee a failure on the next machine. `~19 ms` says, in public, that the
number moves. `...` says the address is random. Every one of those marks is the
author being honest about the limits of what they know -- and a snapshot updater
would erase all three, replace them with a transcript that is true for four
seconds, and call it an improvement.

So the rule here is narrower and, I think, the only defensible one:

    --update changes the numbers. It does not change the prose,
    it does not add lines the README chose not to show, and it
    never removes a `~` or a `...`.

A promised line keeps its wording, its column alignment, its tilde and its
wildcard; only the digits are replaced, by the digits that actually turned up.
If a line has changed so much that no number can rescue it -- `all 42 hashes
verified` against `command not found` -- the tool refuses to touch it and says
so. That is not a gap in the feature. Deciding what a README should say instead
is writing, and this program cannot write.

Lines that are already true are left exactly as they are, which is what keeps
`~19 ms` from quietly becoming `22 ms` the first time somebody runs the flag on
a warm laptop.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass

from .match import (NUMBER, Mismatch, _clean, _line_matches, _restyle,
                    check_claim, compare, measure, prose_disagrees,
                    rewrite_numbers)
from .parse import COMMENT, Block, Claim, parse, parse_claims
from .run import DEFAULT_TIMEOUT, execute


@dataclass
class Update:
    """What `--update` did, and what it would not do."""
    text: str                            # the new README
    edits: int = 0                       # lines it rewrote
    unresolved: list[Mismatch] = None    # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.unresolved is None:
            self.unresolved = []

    @property
    def changed(self) -> bool:
        return self.edits > 0


def _reconcile(expected: list[str], actual: list[str],
               tolerance: float) -> tuple[list[str], list[str]]:
    """Walk the promised output beside the real output, line by line.

    Returns the new promised output and the lines it could not fix. The walk is
    the same subsequence walk the checker does -- a promised line is looked for
    from wherever the last one was found -- so the order of a session is kept.
    """
    fixed: list[str] = []
    beyond_help: list[str] = []
    position = 0

    for line in expected:
        if not line.strip() or line.strip() == "...":
            fixed.append(line)           # a wildcard and a blank line are always true
            continue

        # 1. Still true. Leave it exactly as the author wrote it: this is the
        #    branch that protects `~19 ms` from being "corrected" to `22 ms`.
        hit = None
        for index in range(position, len(actual)):
            if _line_matches(line, actual[index], tolerance, substring=True):
                hit = index
                break
        if hit is not None:
            fixed.append(line)
            position = hit + 1
            continue

        # 2. Same shape, different numbers. The overwhelmingly common case: a
        #    test count, a byte count, a line count, a benchmark. Refresh the
        #    digits and nothing else.
        repaired = None
        for index in range(position, len(actual)):
            repaired = rewrite_numbers(line, actual[index])
            if repaired is not None:
                position = index + 1
                break
        if repaired is not None:
            fixed.append(repaired)
            continue

        # 3. The line is gone. Not a number that drifted -- a promise that is
        #    no longer recognisable in the output. Keep it, report it, and let
        #    a human decide what the README should say now.
        fixed.append(line)
        beyond_help.append(line)

    return fixed, beyond_help


def _update_block(block: Block, root: str, tolerance: float, timeout: float,
                  edits: dict[int, str], unresolved: list[Mismatch]) -> None:
    if block.skip:
        return                           # a skipped block was never a promise

    cwd = os.path.join(root, block.cwd) if block.cwd else root
    limit = block.timeout or timeout

    for command in block.commands:
        # Run everything, output or not. A block is a session and `put` has to
        # happen before `get` -- see the long comment in run.py, which was
        # written the day this tool accused a README of lying about a database
        # it had never been allowed to write to.
        actual, error = execute(command.command, cwd, limit)
        if not command.expected:
            continue
        if error:
            unresolved.append(Mismatch(
                line=command.line, command=command.command,
                expected="\n".join(command.expected), actual="", reason=error))
            continue
        if compare(command.expected, actual, tolerance=tolerance) is None:
            continue                     # the README is already true

        fixed, beyond_help = _reconcile(command.expected, actual, tolerance)

        # The promised output is contiguous: it starts on the line after the
        # `$ ` and runs as far as the parser trimmed it.
        for offset, (was, now) in enumerate(zip(command.expected, fixed)):
            if was != now:
                edits[command.line + 1 + offset] = now

        for line in beyond_help:
            unresolved.append(Mismatch(
                line=command.line, command=command.command,
                expected=line, actual="\n".join(actual),
                reason=(f"the README promises {line.strip()!r} and the output "
                        f"has nothing like it -- this is not a number that "
                        f"drifted, and --update will not guess")))


def _update_claim(claim: Claim, root: str, tolerance: float, timeout: float,
                  lines: list[str], edits: dict[int, str],
                  unresolved: list[Mismatch]) -> None:
    actual, error = execute(claim.command, root, timeout)
    if error:
        unresolved.append(Mismatch(
            line=claim.line, command=claim.command, expected=claim.claimed,
            actual="", reason=error))
        return

    number_wrong = check_claim(claim.claimed, actual, tolerance)
    prose_wrong = prose_disagrees(claim.claimed, claim.prose)
    if not number_wrong and not prose_wrong:
        return                           # true, and the sentence says so

    measured = measure(actual)
    if measured is None:
        unresolved.append(Mismatch(
            line=claim.line, command=claim.command, expected=claim.claimed,
            actual="\n".join(actual), reason="the command printed no number at all"))
        return

    wanted = NUMBER.search(claim.claimed)
    if not wanted:
        return
    old = _clean(wanted.group())

    # A `~` inside its tolerance is not wrong, and is not touched: the point of
    # the tilde is that the number may move without anybody rewriting anything.
    # If only the sentence is out of step, then the sentence is what moves --
    # back to the number the author was willing to stand behind.
    new = old if number_wrong is None else _restyle(old, measured)

    line = lines[claim.line - 1]
    rewritten = _rewrite_claim_line(line, claim.directive, old, new)
    if rewritten != line:
        edits[claim.line] = rewritten


def _spellings(token: str) -> list[str]:
    """`1,089,128` and `1089128` are the same number, written by two people."""
    out = [token]
    plain = token.replace(",", "").replace("_", "")
    if plain not in out:
        out.append(plain)
    try:
        grouped = f"{int(plain):,}"
    except ValueError:
        return out
    if grouped not in out:
        out.append(grouped)
    return out


def _whole_number(text: str, token: str):
    """Find `920` in a sentence, and not the `920` inside `9201`."""
    return re.search(rf"(?<![\d,._]){re.escape(token)}(?![\d])", text)


def _rewrite_claim_line(line: str, directive: str, old: str, new: str) -> str:
    """Fix the number in the comment and the number in the sentence, together.

    Together, because they are one claim wearing two hats. A repair that moved
    only the comment would leave the sentence saying something the machine had
    just certified as false -- and the sentence is the part people read.

    Which number in the sentence? Normally there is no question: the sentence
    says what the comment says, and both move. But when they have already come
    apart -- the prose says 920, the comment says 981 -- the tool has to pick,
    and it picks the number the comment is standing next to: the first one
    after it, or failing that the last one before it. That is where the author
    put the comment, and it is the only signal in the file about which number
    the claim was ever about.
    """
    segments: list[list] = []            # [text, is_comment]
    position = 0
    for found in COMMENT.finditer(line):
        segments.append([line[position:found.start()], False])
        segments.append([found.group(0), True])
        position = found.end()
    segments.append([line[position:], False])

    for index, segment in enumerate(segments):
        if segment[1] and segment[0] == directive:
            segment[0] = segment[0].replace(old, new, 1)
            here = index
            break
    else:
        return line                      # the comment moved; nothing to anchor to

    def rebuilt() -> str:
        return "".join(segment[0] for segment in segments)

    def swap(segment: list, found) -> str:
        text = segment[0]
        was = text[found.start():found.end()]
        segment[0] = text[:found.start()] + _restyle(was, new) + text[found.end():]
        return rebuilt()

    # The sentence still says what the comment used to say: the ordinary case.
    for segment in segments:
        if segment[1]:
            continue
        for spelling in _spellings(old):
            found = _whole_number(segment[0], spelling)
            if found:
                return swap(segment, found)

    # It does not. Take the number the comment is pointing at.
    for segment in segments[here + 1:]:
        if not segment[1]:
            found = NUMBER.search(segment[0])
            if found:
                return swap(segment, found)

    for segment in reversed(segments[:here]):
        if not segment[1]:
            found = None
            for candidate in NUMBER.finditer(segment[0]):
                found = candidate
            if found:
                return swap(segment, found)

    return rebuilt()                     # a sentence with no number in it at all


def update(markdown: str, root: str, tolerance: float,
           timeout: float = DEFAULT_TIMEOUT) -> Update:
    """Run the README, and write back the numbers that moved."""
    lines = markdown.splitlines()
    edits: dict[int, str] = {}
    unresolved: list[Mismatch] = []

    for block in parse(markdown):
        _update_block(block, root, tolerance, timeout, edits, unresolved)
    for claim in parse_claims(markdown):
        _update_claim(claim, root, tolerance, timeout, lines, edits, unresolved)

    for number, text in edits.items():
        lines[number - 1] = text

    text = "\n".join(lines)
    if markdown.endswith("\n"):
        text += "\n"
    return Update(text=text, edits=len(edits), unresolved=unresolved)


def diff(before: str, after: str, name: str) -> list[str]:
    """The change, shown before it is made. The flag was the consent; the diff
    is the receipt."""
    return list(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=name, tofile=f"{name} (updated)", n=2))

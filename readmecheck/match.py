"""Compare what the README promised with what the command actually did.

The hard part is not comparing strings. It is deciding *what is allowed to
differ*, and that decision is the whole design.

Compare everything exactly and the tool is useless: a timing of `19 ms` becomes
`22 ms` on a warm laptop and you get a failure that means nothing. Compare
loosely and the tool is worthless: `7 passed` versus `6 passed` slides through,
which is the exact bug that started this project.

So the rule is that the *author* declares what varies, in the README, in the
open:

    39 passed              exact. Anything else is a failure.
    ~19 ms                 a number that moves. Within tolerance (default 3x).
    resolved ... objects   `...` matches anything on the line.
    ...                    on its own line: any number of lines.

The point of putting it in the README rather than a config file is that the
reader sees it too. "~19 ms" tells them the number is not a promise. A README
that hides its own uncertainty in a dotfile is back to lying, just quietly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ~19, ~19.5, ~1,089,128 -- a number the author admits will move.
APPROX = re.compile(r"~(\d[\d,._]*)")
NUMBER = re.compile(r"\d[\d,._]*")

# The default tolerance is deliberately generous. A throttling laptop CPU swings
# 2-3x on the same benchmark -- we measured it -- so anything tighter produces
# failures that teach the author to ignore the tool.
DEFAULT_TOLERANCE = 3.0


@dataclass
class Mismatch:
    line: int                  # line in the README where the promise sits
    command: str
    expected: str
    actual: str
    reason: str


def _to_number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("_", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _line_matches(expected: str, actual: str, tolerance: float,
                  substring: bool = False) -> bool:
    """Does one promised line match one real line?

    With `substring`, the promise only has to be *contained* in the real line --
    so a README that says `39 passed` is satisfied by `39 passed in 4.51s`. The
    README abbreviated; it did not lie.
    """
    expected = expected.rstrip()
    actual = actual.rstrip()

    if expected == actual:
        return True
    if substring and not APPROX.search(expected) and "..." not in expected:
        return expected.strip() in actual

    # Build a regex out of the line: `...` is a wildcard, `~N` is a number
    # within tolerance, everything else is literal.
    approx_targets: list[float] = []
    pattern_parts: list[str] = []
    position = 0

    tokens = sorted(
        [(m.start(), m.end(), "approx", m) for m in APPROX.finditer(expected)]
        + [(m.start(), m.end(), "any", None)
           for m in re.finditer(r"\.\.\.", expected)],
        key=lambda item: item[0],
    )

    def literal(text: str) -> str:
        """Escape the fixed text, but let runs of whitespace stretch.

        A run of spaces is column alignment, not a claim. `~51 µs` is one
        character wider than ` 89 µs`, so demanding the exact gutter would fail
        every table the moment a number changed width -- and the author would
        learn to distrust the tool rather than the table.
        """
        out = []
        for part in re.split(r"(\s+)", text):
            if not part:
                continue
            out.append(r"\s+" if part.isspace() else re.escape(part))
        return "".join(out)

    for start, end, kind, match in tokens:
        pattern_parts.append(literal(expected[position:start]))
        if kind == "approx":
            value = _to_number(match.group(1))
            if value is None:
                pattern_parts.append(re.escape(expected[start:end]))
            else:
                approx_targets.append(value)
                pattern_parts.append(r"(\d[\d,._]*)")
        else:
            pattern_parts.append(r".*")
        position = end

    pattern_parts.append(literal(expected[position:]))
    if not tokens:
        return False

    pattern = "".join(pattern_parts)
    # In substring mode the promise need only occur inside the real line.
    found = (re.search(pattern, actual) if substring
             else re.fullmatch(pattern, actual))
    if not found:
        return False

    # Every ~N has to land within tolerance of the number that turned up.
    for target, captured in zip(approx_targets, found.groups()):
        got = _to_number(captured)
        if got is None:
            return False
        if target == 0:
            if got != 0:
                return False
            continue
        ratio = got / target
        if not (1 / tolerance) <= ratio <= tolerance:
            return False

    return True


ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    """Colour codes are for humans. `pytest -q` emits them even into a pipe."""
    return ANSI.sub("", text)


def compare(expected: list[str], actual: list[str],
            tolerance: float = DEFAULT_TOLERANCE,
            exact: bool = False) -> str | None:
    """Match the promised output against the real output.

    The default is deliberately *not* a diff, and the reason matters.

    A README abbreviates, and it is right to. `pytest -q` prints a line of dots,
    a percentage, and a duration; the README shows `39 passed`, because that is
    the part that is a claim. Demanding a byte-exact transcript would flag every
    honest README in existence, and a tool that cries wolf gets switched off --
    at which point it protects nothing.

    So the question asked here is the one that actually matters:

        **Does every line the README promises still appear, in order?**

    Extra output is fine. Missing or changed output is not. `39 passed` when the
    truth is `38 passed` fails, because the promised line is nowhere to be found.
    That is the bug this tool exists for, and it is caught.

    Pass `exact=True` when a README means to show a complete transcript and you
    want it held to that.
    """
    if not expected:
        return None                     # the block promised nothing; nothing to break

    expected = [line.rstrip() for line in expected if line.strip()]
    actual = [strip_ansi(line).rstrip() for line in actual]

    if exact:
        return _compare_exact(expected, actual, tolerance)

    # Subsequence: every promised line must turn up, in the promised order.
    position = 0
    for line in expected:
        if line.strip() == "...":
            continue                    # explicit "something happens here"

        found = None
        for index in range(position, len(actual)):
            if _line_matches(line, actual[index], tolerance, substring=True):
                found = index
                break

        if found is None:
            if any(_line_matches(line, other, tolerance, substring=True)
                   for other in actual[:position]):
                return (f"the README promises {line!r}, and it does appear -- "
                        f"but out of order")
            return f"the README promises {line!r}; nothing in the output says that"

        position = found + 1

    return None


def _compare_exact(expected: list[str], actual: list[str],
                   tolerance: float) -> str | None:
    if len(expected) != len(actual):
        return (f"expected {len(expected)} line(s) of output, got {len(actual)}")
    for index, (want, got) in enumerate(zip(expected, actual)):
        if not _line_matches(want, got, tolerance):
            return f"line {index + 1}: expected {want!r}, got {got!r}"
    return None

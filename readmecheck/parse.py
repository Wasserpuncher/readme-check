"""Find the checkable claims in a README.

A README makes two kinds of claim. Prose claims ("this is fast", "it handles
Unicode") are opinions or need a human to judge. But a console block is a
*promise*: run this, see that. It is the only part of documentation that can be
falsified by a machine, and therefore the only part worth checking here.

So this module extracts exactly that: fenced blocks whose commands begin with
`$ `, together with the output the author promised they would produce.

    ```console
    $ python -m pytest -q
    39 passed
    ```

Directives are HTML comments placed immediately before a block. They are
invisible in the rendered README, which matters -- the README is the product,
and a tool that forces you to litter it with markup is a tool nobody uses.

    <!-- readme-check: skip -->        this block is documentation, not a promise
    <!-- readme-check: timeout=120 -->
    <!-- readme-check: cwd=examples -->
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FENCE = re.compile(r"^```([\w-]*)\s*$")
PROMPT = re.compile(r"^\$\s+(.*)$")
DIRECTIVE = re.compile(r"<!--\s*readme-check:\s*(.*?)\s*-->")

# Blocks in these languages are transcripts of commands; anything else is code.
SHELL_LANGUAGES = {"console", "shell", "sh", "bash", "shell-session"}


@dataclass
class Command:
    """One `$ ...` line and the output the README promises it produces."""
    line: int                  # 1-based line of the `$ ` in the README
    command: str
    expected: list[str] = field(default_factory=list)


@dataclass
class Block:
    """One fenced console block."""
    start_line: int
    language: str
    commands: list[Command] = field(default_factory=list)

    skip: bool = False
    skip_reason: str = ""
    timeout: float | None = None
    cwd: str | None = None


def _trim_annotations(expected: list[str]) -> list[str]:
    """Drop the author talking to the reader mid-session.

    READMEs use shell comments as headings inside a long console block:

        $ git clone ... && cd project

        # Run it natively
        $ project run demo
        21

    The `# Run it natively` line is not output of `git clone`. Treating it as
    such accuses the README of a broken promise it never made -- which is how
    a checking tool loses the author's trust, and after that it is furniture.

    The rule is narrow on purpose: a *blank line* followed by a `#` line ends
    the output. Real output that merely happens to contain `#` (a diff, a
    Makefile, a comment in generated code) is untouched, because it is not
    preceded by a blank line inside the block.
    """
    for index in range(len(expected) - 1):
        if not expected[index].strip() and expected[index + 1].lstrip().startswith("#"):
            return expected[:index]
    return expected


def _parse_directives(text: str, block: Block) -> None:
    for raw in DIRECTIVE.findall(text):
        for part in raw.split():
            if part == "skip":
                block.skip = True
            elif part.startswith("skip="):
                block.skip = True
                block.skip_reason = part[5:]
            elif part.startswith("timeout="):
                block.timeout = float(part[8:])
            elif part.startswith("cwd="):
                block.cwd = part[4:]


def parse(markdown: str) -> list[Block]:
    """Extract every console block that makes a checkable promise."""
    lines = markdown.splitlines()
    blocks: list[Block] = []

    index = 0
    while index < len(lines):
        fence = FENCE.match(lines[index])
        if not fence:
            index += 1
            continue

        language = fence.group(1).lower()
        block = Block(start_line=index + 1, language=language)

        # Directives sit in the lines just above the fence, past any blank line.
        look = index - 1
        while look >= 0 and (lines[look].strip() == "" or "readme-check:" in lines[look]):
            if "readme-check:" in lines[look]:
                _parse_directives(lines[look], block)
            look -= 1

        # Collect the body up to the closing fence.
        body: list[tuple[int, str]] = []
        index += 1
        while index < len(lines) and not lines[index].startswith("```"):
            body.append((index + 1, lines[index]))
            index += 1
        index += 1                       # step over the closing fence

        if language not in SHELL_LANGUAGES:
            continue                     # a code sample, not a promise

        current: Command | None = None
        for line_number, line in body:
            prompt = PROMPT.match(line)
            if prompt:
                current = Command(line=line_number, command=prompt.group(1).strip())
                block.commands.append(current)
            elif current is not None:
                current.expected.append(line)
            # Output before the first `$` has nothing to belong to; drop it.

        for command in block.commands:
            command.expected = _trim_annotations(command.expected)
            # Trailing blank lines are formatting, not a promise about output.
            while command.expected and not command.expected[-1].strip():
                command.expected.pop()

        if block.commands:
            blocks.append(block)

    return blocks

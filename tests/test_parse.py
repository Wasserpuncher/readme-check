"""Parsing: which parts of a README are promises, and which are prose."""

from __future__ import annotations

import textwrap

from readmecheck import parse


def blocks(markdown: str):
    return parse(textwrap.dedent(markdown))


class TestWhatCounts:
    def test_a_console_block_is_a_promise(self):
        [block] = blocks("""
            ```console
            $ echo hello
            hello
            ```
        """)
        [command] = block.commands
        assert command.command == "echo hello"
        assert command.expected == ["hello"]

    def test_a_python_block_is_not(self):
        """A code sample shows you how to write something. It does not promise
        what happens when you run it, and running it would be presumptuous."""
        assert blocks("""
            ```python
            import readmecheck
            ```
        """) == []

    def test_several_commands_in_one_session(self):
        [block] = blocks("""
            ```console
            $ cd project
            $ make
            built
            $ ./run
            ok
            ```
        """)
        assert [c.command for c in block.commands] == ["cd project", "make", "./run"]
        assert block.commands[0].expected == []      # no output promised
        assert block.commands[1].expected == ["built"]

    def test_bash_and_sh_count_too(self):
        for language in ("bash", "sh", "shell", "shell-session"):
            assert blocks(f"```{language}\n$ true\nok\n```")

    def test_output_before_the_first_prompt_belongs_to_nobody(self):
        [block] = blocks("""
            ```console
            stray line
            $ echo hi
            hi
            ```
        """)
        assert block.commands[0].expected == ["hi"]


class TestDirectives:
    def test_skip(self):
        """Some blocks are instructions to the reader, not promises -- a command
        that needs a tool they must install first, say."""
        [block] = blocks("""
            <!-- readme-check: skip -->
            ```console
            $ drat-trim proof.cnf proof.drat
            ```
        """)
        assert block.skip

    def test_skip_with_a_reason(self):
        [block] = blocks("""
            <!-- readme-check: skip=needs-root -->
            ```console
            $ sudo ip tuntap add dev tun0 mode tun
            ```
        """)
        assert block.skip and block.skip_reason == "needs-root"

    def test_timeout_and_cwd(self):
        [block] = blocks("""
            <!-- readme-check: timeout=600 cwd=examples -->
            ```console
            $ make
            done
            ```
        """)
        assert block.timeout == 600
        assert block.cwd == "examples"

    def test_a_directive_survives_a_blank_line(self):
        [block] = blocks("""
            <!-- readme-check: skip -->

            ```console
            $ whatever
            ```
        """)
        assert block.skip

    def test_a_directive_does_not_leak_into_the_next_block(self):
        first, second = blocks("""
            <!-- readme-check: skip -->
            ```console
            $ dangerous
            out
            ```

            ```console
            $ safe
            out
            ```
        """)
        assert first.skip
        assert not second.skip


class TestTrailing:
    def test_trailing_blank_lines_are_not_a_promise(self):
        [block] = blocks("```console\n$ echo hi\nhi\n\n\n```")
        assert block.commands[0].expected == ["hi"]

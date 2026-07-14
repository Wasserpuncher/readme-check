"""`--update`, and the four ways it could have been a disaster.

Writing the truth back into a README is easy. Writing it back without deleting
the author's honesty is the whole job, and every test in the second class below
is a mistake a snapshot updater makes by default:

  * it turns `39 passed` into `39 passed in 4.51s`, pasting a duration into a
    promise, so the README fails on the next machine -- a README broken by the
    tool that was fixing it;
  * it turns `~19 ms` into `22 ms`, deleting in one keystroke the author's
    public admission that the number moves;
  * it fills in the `...` that stood for a random root nameserver;
  * it pastes the whole transcript, because it cannot tell an abbreviation from
    an omission.

So this one only ever changes digits. If a line has changed beyond the reach of
a number, it says so and leaves it alone, because deciding what the README
should say instead is writing, and this program cannot write.
"""

from __future__ import annotations

import textwrap

from readmecheck import update


def run(markdown: str, tolerance: float = 3.0):
    return update(textwrap.dedent(markdown).lstrip("\n"), root=".",
                  tolerance=tolerance)


def promised(done) -> str:
    """The part of the block the README promises as *output*.

    The `$ printf ...` lines have to be excluded, or every assertion below
    passes for the wrong reason: the string we are checking the tool did not
    write is sitting right there in the command that produced it.
    """
    return "\n".join(line for line in done.text.splitlines()
                     if not line.startswith(("$", "```")))


class TestItFixesTheNumbersThatMoved:
    def test_the_test_count_that_drifted(self):
        """pdb-from-scratch said 7 and there were 6. This is the fix, and it is
        the reason the flag exists: the author should not have to retype a
        number a machine just measured."""
        done = run("""
            ```console
            $ printf '......\\n7 passed in 0.26s\\n'
            6 passed
            ```
        """)
        assert promised(done).strip() == "7 passed"
        assert done.edits == 1
        assert not done.unresolved

    def test_it_does_not_paste_the_duration_it_could_never_promise(self):
        """The obvious implementation copies the real line over the promised
        one and writes `7 passed in 0.26s` into the README. That duration is
        not a promise anybody can keep, and the very next run fails -- on a
        README the tool wrote itself."""
        done = run("""
            ```console
            $ printf '7 passed in 0.26s\\n'
            6 passed
            ```
        """)
        assert promised(done).strip() == "7 passed"
        assert "0.26s" not in promised(done)

    def test_the_byte_count_that_was_stale_within_the_hour(self):
        """minilink said 8204. Section headers were added; it became 9049."""
        done = run("""
            ```console
            $ printf "hello: 9049 bytes, entry '_start'\\n"
            hello: 8204 bytes, entry '_start'
            ```
        """)
        assert promised(done).strip() == "hello: 9049 bytes, entry '_start'"

    def test_it_keeps_the_column_the_author_lined_up(self):
        done = run("""
            ```console
            $ printf '  28   13807 ms   0.23 ms\\n'
              28   34060 ms   0.18 ms
            ```
        """)
        assert promised(done).strip("\n") == "  28   13807 ms   0.23 ms"


class TestItMustNotDestroyTheHonestyMarks:
    def test_a_tilde_inside_its_tolerance_is_not_touched(self):
        """The one that would have made this feature a net loss. `~19 ms` is
        the author saying, in public, that the number moves; a warm laptop says
        22 ms; an updater that "corrects" the README to `22 ms` has deleted an
        admission of uncertainty and replaced it with a false precision that
        will be wrong again in four seconds.

        Nothing here is broken, so nothing here is written."""
        done = run("""
            ```console
            $ printf 'Native fib(30): 22 ms\\n'
            Native fib(30): ~19 ms
            ```
        """)
        assert promised(done).strip() == "Native fib(30): ~19 ms"
        assert "22 ms" not in promised(done)
        assert done.edits == 0
        assert not done.changed

    def test_a_tilde_outside_its_tolerance_keeps_its_tilde(self):
        """`~19` will not excuse 300 -- that is a real failure, and the number
        does get rewritten. But it is rewritten as `~300`: the author said this
        number moves, and the tool does not get to retract that on their
        behalf."""
        done = run("""
            ```console
            $ printf 'Native fib(30): 300 ms\\n'
            Native fib(30): ~19 ms
            ```
        """)
        assert promised(done).strip() == "Native fib(30): ~300 ms"
        assert done.edits == 1

    def test_a_wildcard_stays_a_wildcard(self):
        """recursive-dns picks a root server at random. `...` is the honest way
        to say so, and filling it in with whichever server answered today would
        turn an honest README into a flaky one."""
        done = run("""
            ```console
            $ printf '  192.33.4.12   [.]  example.com  ->  delegation\\n'
              ...  [.]  example.com  ->  delegation
            ```
        """)
        assert "..." in promised(done)
        assert "192.33.4.12" not in promised(done)
        assert done.edits == 0

    def test_it_does_not_paste_output_the_readme_chose_not_to_show(self):
        """A README abbreviates, and it is right to. The tool's own rule is
        that extra output is fine -- so an updater that appended every line the
        command printed would be contradicting the checker it ships with."""
        done = run("""
            ```console
            $ printf 'warming up\\ndone\\ncleanup\\n'
            done
            ```
        """)
        assert promised(done).strip() == "done"
        assert done.edits == 0

    def test_a_skipped_block_is_never_rewritten(self):
        """`skip` means this block is documentation, not a promise. It is also
        the block that needs root, or the network, or a tool the reader has to
        install -- and it is emphatically not to be run just because somebody
        asked for an update."""
        source = textwrap.dedent("""
            <!-- readme-check: skip=needs-root -->
            ```console
            $ printf 'wrong\\n'
            right
            ```
        """).lstrip("\n")
        done = update(source, root=".", tolerance=3.0)
        assert done.text == source
        assert done.edits == 0


class TestItFixesTheSentencesToo:
    def test_the_cdcl_sat_sentence(self):
        """"920 lines you can read", and there were 981. The comment and the
        sentence are one claim wearing two hats, and both hats move."""
        done = run("""
            It is <!-- readme-check: 920 = printf '981' --> 920 lines you can read.
        """)
        assert done.text == (
            "It is <!-- readme-check: 981 = printf '981' --> 981 lines you can read.\n")
        assert done.edits == 1

    def test_prose_that_drifted_is_pulled_back_to_the_truth(self):
        """The sentence says 920, the comment says 981, the command measures
        981. The number is right and the README still lies -- so the sentence
        is what moves."""
        done = run("""
            It is <!-- readme-check: 981 = printf '981' --> 920 lines you can read.
        """)
        assert "981 lines you can read" in done.text

    def test_a_true_sentence_is_left_alone(self):
        done = run("""
            It is <!-- readme-check: 981 = printf '981' --> 981 lines you can read.
        """)
        assert done.edits == 0

    def test_a_tolerated_tilde_in_prose_survives_as_well(self):
        done = run("""
            It runs in <!-- readme-check: ~19 ms = printf '22' --> roughly 19 ms.
        """)
        assert done.edits == 0
        assert done.text.endswith("--> roughly 19 ms.\n")


class TestItRefusesToGuess:
    def test_a_promise_that_is_simply_gone(self):
        """`all 42 hashes verified` against `command not found` is not a number
        that drifted. What the README should say instead is a question about
        the project, not about arithmetic, and the tool has no business
        answering it."""
        done = run("""
            ```console
            $ printf 'command not found\\n'
            all 42 hashes verified
            ```
        """)
        assert promised(done).strip() == "all 42 hashes verified"
        assert done.edits == 0
        assert len(done.unresolved) == 1
        assert "will not guess" in done.unresolved[0].reason


class TestNothingToDo:
    def test_a_readme_that_already_tells_the_truth_is_byte_identical(self):
        source = textwrap.dedent("""
            ```console
            $ printf '6 passed in 0.26s\\n'
            6 passed
            ```
        """).lstrip("\n")
        done = update(source, root=".", tolerance=3.0)
        assert done.text == source
        assert not done.changed

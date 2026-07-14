"""The bugs this tool was built for -- pinned as tests.

Every case below is a lie that was actually live in a public README, found by
hand, on one long night of auditing eight repositories. Half of them were wrong.

The point of a tool like this is that the same lie cannot happen twice. So the
lies become the test suite: if a future refactor stops catching one of these,
the tool has quietly lost the only reason it exists.

Just as important are the *honest* cases. A README abbreviates `pytest`'s output
and rounds a benchmark, and that is not lying -- it is writing. A tool that
flags those is a tool that gets switched off, and a tool that is switched off
catches nothing at all. So each lie is paired with the honest thing it must not
be confused with.
"""

from __future__ import annotations

import pytest

from readmecheck import compare


class TestLiesItMustCatch:
    def test_a_test_count_that_drifted(self):
        """pdb-from-scratch said 7. There were 6. The number a reader checks
        in thirty seconds."""
        assert compare(["7 passed"], ["......", "6 passed in 0.26s"])

    def test_a_transcript_pasted_from_a_test_fixture(self):
        """recursive-dns printed 1.2.3.4 as a real nameserver -- the placeholder
        constant from its own test file. Nobody had ever run the tool."""
        assert compare(
            ["  1.2.3.4          [example.com]  example.com  ->  answer"],
            ["  172.64.35.228    [example.com]  example.com  ->  answer"])

    def test_a_size_that_was_true_when_it_was_written(self):
        """minilink said 8204 bytes. Then section headers were added and the
        binary grew. The README was stale within the hour."""
        assert compare(["hello: 8204 bytes, entry '_start'"],
                       ["hello: 9049 bytes, entry '_start'"])

    def test_a_benchmark_that_was_three_times_too_flattering(self):
        """rejit claimed Python's re took 34,060 ms. It took 13,807. Even with a
        generous tolerance, a 2.5x overstatement is not a rounding error."""
        assert compare(["  28   ~34060 ms   0.18 ms"], ["  28   13807 ms   0.23 ms"])

    def test_output_that_vanished_entirely(self):
        assert compare(["all 42 hashes verified"], ["command not found"])

    def test_a_promise_that_appears_but_in_the_wrong_place(self):
        reason = compare(["step one", "step two"], ["step two", "step one"])
        assert reason and "out of order" in reason


class TestHonestyItMustNotFlag:
    def test_an_abbreviated_pytest_line(self):
        """A README says `39 passed`. pytest says `39 passed in 4.51s` after a
        line of dots. The README abbreviated; it did not lie."""
        assert compare(["39 passed"],
                       ["........  [100%]", "39 passed in 4.51s"]) is None

    def test_colour_codes(self):
        """pytest emits ANSI even into a pipe. That is not a broken promise."""
        assert compare(["20 passed"],
                       ["\x1b[32m20 passed\x1b[0m in 4.51s"]) is None

    def test_a_timing_the_author_marked_as_approximate(self):
        """`~19 ms` is an honest way to write a number that moves. A laptop CPU
        swings 2-3x on the same benchmark -- we measured it."""
        assert compare(["Native fib(30): ~19 ms"],
                       ["Native fib(30): 22 ms"]) is None
        assert compare(["Native fib(30): ~19 ms"],
                       ["Native fib(30): 11 ms"]) is None

    def test_but_approximate_is_not_a_blank_cheque(self):
        """`~19 ms` must not excuse 300 ms. Tolerance is generous, not infinite."""
        assert compare(["Native fib(30): ~19 ms"], ["Native fib(30): 300 ms"])

    def test_a_wildcard_for_something_genuinely_random(self):
        """recursive-dns picks a root server at random every run. The README is
        allowed to say so."""
        assert compare(
            ["  ...  [.]  example.com  ->  delegation"],
            ["  192.33.4.12      [.]  example.com  ->  delegation"]) is None

    def test_extra_output_the_readme_did_not_show(self):
        assert compare(["done"], ["warming up", "done", "cleanup"]) is None


class TestNumbers:
    @pytest.mark.parametrize("promised,actual,ok", [
        ("~100", "100", True),
        ("~100", "250", True),        # inside the default 3x tolerance
        ("~100", "40", True),
        ("~100", "301", False),       # outside it
        ("~100", "33", False),
        ("~1,089,128", "1089128", True),
        ("~1,089,128", "12", False),
    ])
    def test_tolerance(self, promised, actual, ok):
        result = compare([f"conflicts: {promised}"], [f"conflicts: {actual}"])
        assert (result is None) == ok


class TestExactMode:
    def test_exact_mode_rejects_extra_output(self):
        assert compare(["done"], ["done", "and then some"], exact=True)

    def test_exact_mode_accepts_a_full_transcript(self):
        assert compare(["a", "b"], ["a", "b"], exact=True) is None

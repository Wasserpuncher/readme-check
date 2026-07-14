"""The lie that no console block could ever have caught.

cdcl-sat's README said, in a sentence, in English: "920 lines you can read".
There were 981. It had been 920 once. Nobody had lied; somebody had written
more code, which is what code does.

That one is worse than the others, because there was no `$`, no fenced block,
nothing for a machine to run -- and yet it is exactly the kind of number a
reader checks in thirty seconds and then quietly stops trusting the rest of the
page. So a sentence may now name the command that settles it, in a comment that
renders as nothing:

    It is <!-- readme-check: 981 = cat cdcl/*.py | wc -l --> 981 lines.

Two things are then checked, and the second one matters more than it looks:
the command's number must equal the claim, *and* the sentence must still say
what the comment says it says. A checker that can be satisfied while the README
lies is not a checker. It is an alibi.
"""

from __future__ import annotations

import textwrap

import pytest

from readmecheck import check, check_claim, parse, parse_claims, prose_disagrees


def claims(markdown: str):
    return parse_claims(textwrap.dedent(markdown))


class TestTheSentenceThatLied:
    def test_the_line_count_that_grew_while_nobody_looked(self):
        """cdcl-sat: "920 lines you can read". It was 981."""
        reason = check_claim("920", ["981"])
        assert reason == "the README claims 920, measured 981"

    def test_the_message_names_both_numbers(self):
        """A failure that says only "wrong" makes the author go and measure it
        themselves, which is the work the tool was supposed to do."""
        reason = check_claim("920", ["981"])
        assert "920" in reason and "981" in reason

    def test_a_sentence_that_is_simply_true(self):
        assert check_claim("981", ["981"]) is None

    def test_a_number_buried_in_a_sentence_of_output(self):
        """`wc -l` on many files ends with `981 total`, and `du -h` says other
        things first. The first number the command prints is the measurement --
        one sentence, so the author can predict the verdict."""
        assert check_claim("981", ["  981 total"]) is None

    def test_a_substring_is_not_a_measurement(self):
        """The naive implementation asks whether "920" appears in the output.
        It does appear in `9201`, and in `1920`, and the tool that shipped that
        would bless a README off by an order of magnitude."""
        assert check_claim("920", ["9201"])
        assert check_claim("920", ["1920"])

    def test_a_command_that_measured_nothing(self):
        """A typo in the command is not a passing claim."""
        reason = check_claim("981", ["sh: wc: command not found"])
        assert reason and "no number" in reason


class TestNumbersInProseAlsoMove:
    def test_a_prose_number_may_wear_a_tilde(self):
        """The tilde means the same thing in a sentence as in a console block:
        this number moves, and I am telling you so where you can see it."""
        assert check_claim("~19 ms", ["22"]) is None

    def test_but_the_tilde_is_not_a_blank_cheque_here_either(self):
        reason = check_claim("~19 ms", ["300"])
        assert reason and "300" in reason

    @pytest.mark.parametrize("claimed,measured,ok", [
        ("~100", "250", True),
        ("~100", "301", False),
        ("1,089,128", "1089128", True),      # a comma is a spelling, not a value
        ("1,089,128", "1089129", False),
    ])
    def test_tolerance_and_spelling(self, claimed, measured, ok):
        assert (check_claim(claimed, [measured]) is None) == ok


class TestBindingASentenceToACommand:
    def test_a_sentence_names_the_command_that_proves_it(self):
        [claim] = claims("""
            It is <!-- readme-check: 981 = cat cdcl/*.py | wc -l --> 981 lines.
        """)
        assert claim.claimed == "981"
        assert claim.command == "cat cdcl/*.py | wc -l"

    def test_the_reader_sees_none_of_it(self):
        """The comment renders as nothing. The README is the product; a tool
        that makes you scar it to be checked is a tool nobody uses."""
        [claim] = claims("""
            It is <!-- readme-check: 981 = wc -l --> 981 lines you can read.
        """)
        assert "readme-check" not in claim.prose
        assert claim.prose.strip() == "It is  981 lines you can read."

    def test_a_command_is_allowed_an_equals_sign(self):
        [claim] = claims("""
            Roughly <!-- readme-check: 42 = awk -F= '{n=$2} END {print n}' f --> 42.
        """)
        assert claim.command == "awk -F= '{n=$2} END {print n}' f"

    def test_a_block_directive_is_not_a_claim(self):
        """`skip`, `timeout=120`, `cwd=examples`. No keyword has a digit in its
        name, which is the entire rule that tells the two apart."""
        assert claims("<!-- readme-check: skip=needs-root -->\n") == []
        assert claims("<!-- readme-check: timeout=120 cwd=examples -->\n") == []

    def test_a_claim_does_not_leak_into_the_block_below_it(self):
        [block] = parse(textwrap.dedent("""
            It is <!-- readme-check: 981 = wc -l --> 981 lines.
            ```console
            $ echo hi
            hi
            ```
        """))
        assert not block.skip
        assert block.timeout is None

    def test_a_claim_in_a_code_fence_is_documentation(self):
        """This README documents the syntax by showing it. If the parser could
        not tell an example from a claim, the tool would spend its life running
        its own manual."""
        assert claims("""
            ```markdown
            It is <!-- readme-check: 981 = wc -l --> 981 lines.
            ```
        """) == []

    def test_a_claim_in_backticks_is_documentation_too(self):
        """Found by the tool, on this project's own README, which had a prose
        sentence explaining the syntax and got the syntax run at it. The command
        in that illustration was `...`, and `...` is not a command."""
        assert claims("""
            The tilde works here as well: `<!-- readme-check: ~19 ms = ... -->`.
        """) == []


class TestTheCommentMustAgreeWithTheSentence:
    def test_prose_that_drifted_away_from_its_own_directive(self):
        """The trap this feature could have walked into: the author fixes the
        code, the tool updates nothing, the comment still says 981, the command
        still measures 981, the build is green -- and the sentence the reader
        actually reads says 920. Green, and a lie."""
        reason = prose_disagrees("981", "It is 920 lines you can read.")
        assert reason and "981" in reason

    def test_a_sentence_that_says_what_it_claims(self):
        assert prose_disagrees("981", "It is 981 lines you can read.") is None

    def test_the_tilde_is_not_required_in_english(self):
        """`~19 ms` is a notation. "roughly 19 ms" is a sentence. The number is
        what has to match."""
        assert prose_disagrees("~19 ms", "It runs in roughly 19 ms.") is None

    def test_a_comma_is_a_spelling(self):
        assert prose_disagrees("1089128", "It resolved 1,089,128 conflicts.") is None
        assert prose_disagrees("1,089,128", "It resolved 1089128 conflicts.") is None

    def test_a_longer_number_is_not_the_number(self):
        assert prose_disagrees("920", "It is 9201 lines you can read.")


class TestEndToEnd:
    def test_a_lying_sentence_fails_the_build(self, tmp_path):
        readme = "It is <!-- readme-check: 920 = printf '981' --> 920 lines.\n"
        result = check([], root=str(tmp_path), tolerance=3.0,
                       claims=parse_claims(readme))
        assert result.checked == 1
        assert not result.ok
        assert result.mismatches[0].reason == "the README claims 920, measured 981"

    def test_an_honest_sentence_passes(self, tmp_path):
        readme = "It is <!-- readme-check: 981 = printf '981' --> 981 lines.\n"
        result = check([], root=str(tmp_path), tolerance=3.0,
                       claims=parse_claims(readme))
        assert result.ok and result.checked == 1

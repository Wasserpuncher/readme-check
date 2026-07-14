"""Run the console blocks in a README and check they still tell the truth.

A README's console block is a promise: run this, see that. It is the only part
of documentation a machine can falsify -- so this falsifies it.

    >>> from readmecheck import parse, check
    >>> blocks = parse(open("README.md").read())
    >>> check(blocks, root=".", tolerance=3.0).ok
    True
"""

from .match import (Mismatch, check_claim, compare, measure, prose_disagrees,
                    rewrite_numbers)
from .parse import Block, Claim, Command, parse, parse_claims
from .run import Result, check
from .update import Update, diff, update

__all__ = ["parse", "parse_claims", "check", "compare", "check_claim",
           "prose_disagrees", "measure", "rewrite_numbers", "update", "diff",
           "Block", "Claim", "Command", "Result", "Update", "Mismatch"]
__version__ = "1.0.0"

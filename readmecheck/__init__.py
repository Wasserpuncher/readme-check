"""Run the console blocks in a README and check they still tell the truth.

A README's console block is a promise: run this, see that. It is the only part
of documentation a machine can falsify -- so this falsifies it.

    >>> from readmecheck import parse, check
    >>> blocks = parse(open("README.md").read())
    >>> check(blocks, root=".", tolerance=3.0).ok
    True
"""

from .match import Mismatch, compare
from .parse import Block, Command, parse
from .run import Result, check

__all__ = ["parse", "check", "compare", "Block", "Command", "Result", "Mismatch"]
__version__ = "1.0.0"

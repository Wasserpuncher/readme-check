# readme-check

**Your README makes promises. This runs them.**

I audited the READMEs of eight of my own repositories, by hand, in one night.
**Four of them lied.**

Not maliciously. One said `7 passed` when there were six. One pasted a console
transcript straight out of a test fixture — it advertised `1.2.3.4` as a real
nameserver, which is a placeholder constant, which means nobody had ever run the
tool they were documenting. One quoted a benchmark 2.5× more flattering than the
machine actually produces. One reported a binary size that was true when it was
written and stale within the hour, because the code got better and the README
didn't notice.

Every one of those was a number a reader could have checked in thirty seconds. So
now a machine checks them.

<!-- readme-check: skip=illustration -->
```console
$ readme-check
✗ README.md:73  $ python -m pytest tests/test_elf.py -q
  the README promises '7 passed'; nothing in the output says that
  --- the README promises
  | 7 passed
  --- what actually happened
  | 6 passed in 0.26s

1 of 4 promise(s) broken, 6 skipped
```

## What it does

It finds the console blocks in your README, **runs the commands**, and checks
that what they print still contains what you said they would.

A console block is the only part of documentation that is falsifiable. Prose
("it's fast", "it handles Unicode") needs a human. But

    ```console
    $ python -m pytest -q
    39 passed
    ```

is a promise, and a promise can be broken.

## What it does not do

**It does not demand a byte-exact transcript.** A README abbreviates, and it is
right to. `pytest -q` prints a line of dots, a percentage and a duration; your
README shows `39 passed`, because that is the part that is a claim. A tool that
flagged that would flag every honest README in existence — and a tool that cries
wolf gets switched off, at which point it protects nothing at all.

So the question it asks is the narrow, useful one: **does every line you promised
still appear, in order?** Extra output is fine. Missing output is not.

## Numbers that move

Timings are not promises. A laptop CPU throttles; the same benchmark swings 2–3×
between runs. Say so, with a `~`:

<!-- readme-check: skip=another-repo -->
```console
$ python -m tinyjit bench
Native fib(30):     ~19 ms
Interpreter:     ~25000 ms
```

A `~19` accepts anything within 3× (`--tolerance` changes it). It will not accept
300. And the reader sees the tilde too, which is the whole point: **a number the
author will not stand behind should not look like one they will.** A README that
hides its uncertainty in a config file is still lying, just quietly.

For output that is genuinely unpredictable — a random root nameserver, a
timestamp — use `...`:

<!-- readme-check: skip=another-repo -->
```console
$ python -m recursivedns example.com
resolving example.com from the root
  ...  [.]  example.com  ->  delegation
```

`...` on its own line skips any number of lines.

## Blocks that should not run

Some blocks are instructions, not promises: they need root, or a tool the reader
has to install, or they talk to the network. Mark them, in an HTML comment that
renders as nothing:

```markdown
<!-- readme-check: skip=needs-root -->
```console
$ sudo ip tuntap add dev tun0 mode tun
```
```

Other directives: `timeout=120`, `cwd=examples`.

## Verified

```console
$ python -m pytest -q
32 passed
```

The test suite is the audit. Every lie found that night is pinned as a test —
the drifting test count, the transcript from the fixture, the flattering
benchmark, the stale byte count — and so is the *honest* thing each one must not
be confused with: the abbreviated pytest line, the rounded timing, the colour
codes, the genuinely random address.

That pairing is the hard part. Catching lies is easy if you are willing to
scream at the truth as well.

**And it checks itself.** The block above is run by the tool, on this file, in
CI. If this README ever claims something it cannot do, the build fails — which
would be a particularly embarrassing way to find out.

## What it found on my own repositories

Every one of these is now fixed, and every fix is a commit that says what was
wrong:

| repository | what the README claimed | what was true |
| --- | --- | --- |
| `pdb-from-scratch` | `7 passed` | 6 |
| `recursive-dns` | `1.2.3.4` as the authoritative nameserver | a fixture constant; the transcript was never run |
| `rejit` | Python's `re` takes 34,060 ms | 13,807 ms — a 2.5× overstatement |
| `minilink` | `hello: 8204 bytes` | 9,049 — true when written, stale within the hour |
| `tcp-userspace` | 300 connections at 35% loss | the test ran twelve, at 30% |

The tool did not find these — I did, painfully, by hand. It exists so that the
next one is found in four seconds by a machine that does not get tired and does
not want the number to be true.

## Install

<!-- readme-check: skip=would-install -->
```console
$ pip install readme-check
$ readme-check                    # checks ./README.md
$ readme-check docs/GUIDE.md --tolerance 5
```

Python 3.10+, no dependencies.

**It runs the commands in your README.** That is the entire idea, and it means it
will do whatever your README tells people to do — including writing files, and
including anything destructive you have documented. It is not a sandbox. If you
would not want a stranger to paste your README into a shell, this tool is the
least of your problems.

## License

MIT

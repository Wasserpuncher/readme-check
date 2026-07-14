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
that what they print still contains what you said they would. A number in your
prose can be checked too, if you point at the command that measures it.

A console block is the part of documentation that is falsifiable without asking
anybody's permission. Prose ("it's fast", "it handles Unicode") needs a human. But

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

## Numbers in the prose

The most expensive lie was not in a console block at all. `cdcl-sat`'s README
said it, in a sentence, in English:

> It is **920 lines** you can read.

There were 981. Nobody had lied; somebody had written more code, which is what
code does. There was no `$` on that line and nothing to run, so a tool that only
reads fenced blocks would never have found it — and it is precisely the number a
reader checks in thirty seconds before quietly deciding not to trust the rest of
the page.

So a sentence can name the command that settles it, in a comment that renders as
nothing:

```markdown
It is <!-- readme-check: 981 = cat cdcl/*.py | wc -l --> 981 lines you can read.
```

The command runs, the first number it prints is the measurement, and the sentence
is held to it:

<!-- readme-check: skip=illustration -->
```console
$ readme-check
✗ README.md:14  $ cat cdcl/*.py | wc -l
  the README claims 920, measured 981
```

The comparison is arithmetic, not text: a claim of `920` is *not* satisfied by an
output of `9201`. A claim may wear a tilde — `` `<!-- readme-check: ~19 ms = … -->` ``
— and it means there what it means everywhere else, to the machine and to the
reader, who can see the number even though they cannot see the comment.

Two things are checked, not one. The command must agree with the comment, **and
the sentence must still agree with the comment.** An author who edits the prose
and forgets the comment would otherwise end up with a README that lies and a
build that passes — which is not a checker. It is an alibi.

This tool is <!-- readme-check: 1244 = cat readmecheck/*.py | wc -l --> 1244
lines of Python, most of them comments, and that sentence is checked by the code
it is counting.

## When the number moved, it can move it back

`--update` runs the README and writes the measured numbers into it:

<!-- readme-check: skip=illustration -->
```console
$ readme-check --update
--- README.md
+++ README.md (updated)
-6 passed
+7 passed
-It is <!-- readme-check: 920 = cat cdcl/*.py | wc -l --> 920 lines.
+It is <!-- readme-check: 981 = cat cdcl/*.py | wc -l --> 981 lines.
2 line(s) updated in README.md
```

It prints the diff and it does not ask. You typed the flag; that was the
question.

And it changes **only the digits**. That restraint is the entire feature, because
a snapshot updater of the obvious kind would quietly undo everything this project
is for:

- `39 passed` does not become `39 passed in 4.51s`. A duration is not a promise
  anybody can keep, and pasting it in would break the README on the next machine
  — the tool breaking the file it was fixing.
- `~19 ms` does not become `22 ms`. **The tilde is the author saying in public
  that the number moves, and no flag gets to delete an admission.** A `~` inside
  its tolerance is not wrong in the first place, so it is not touched at all.
- `...` stays `...`. The random root nameserver stays random.
- `skip` blocks are not run, let alone rewritten.
- Output the README chose not to show is not pasted in. The README abbreviates,
  the checker allows it, and the updater does not get to overrule the checker it
  ships with.

If a promised line has drifted beyond the reach of a number — `all 42 hashes
verified` against `command not found` — the tool leaves it alone and says so.
Deciding what the README should say instead is *writing*, and this program cannot
write.

## Verified

```console
$ python -m pytest -q
73 passed
```

The test suite is the audit. Every lie found that night is pinned as a test —
the drifting test count, the transcript from the fixture, the flattering
benchmark, the stale byte count, the sentence that said 920 — and so is the
*honest* thing each one must not be confused with: the abbreviated pytest line,
the rounded timing, the colour codes, the genuinely random address, and the
`~19 ms` that `--update` must never "correct" into `22 ms`.

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
$ readme-check --update           # writes the numbers that moved back in
```

Python 3.10+, no dependencies.

**It runs the commands in your README.** That is the entire idea, and it means it
will do whatever your README tells people to do — including writing files, and
including anything destructive you have documented. It is not a sandbox. If you
would not want a stranger to paste your README into a shell, this tool is the
least of your problems.

## License

MIT

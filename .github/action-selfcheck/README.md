# action self-check fixture

This fixture exists so the `selfcheck` workflow can prove the readme-check
**Action** installs from `@v1` and runs. Its single console block is
deterministic and needs nothing but a shell — unlike this repository's own
README, which documents commands (a test run) that need the dev environment.

```console
$ echo readme-check-action-ok
readme-check-action-ok
```

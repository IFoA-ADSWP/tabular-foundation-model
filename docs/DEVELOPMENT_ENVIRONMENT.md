# Development environment

> **Status:** current as of 2026-11-10. Written after the #516/#526 session, where the gate was
> real in CI and undefined locally.

This page carries the facts a handoff used to carry in a temp file: how to build an environment the
lock describes, which checkout you are in, how to make a worktree that works, and how long the
suite takes. Handoffs point here instead of restating it.

## 1. Which checkout am I in?

More than one clone of this repository has existed on this machine. They disagree about `HEAD`, and
a worktree can be created from a different clone than the one the session started in. Observed on
2026-11-10:

| Path | State |
| --- | --- |
| `~/projects/tabular-foundation-model` | the session's clone; both `github` and `origin` remotes; at `origin/main` |
| `~/tabular-foundation-model` | the checkout the global `workload.sh` helper selects for this repository name; was weeks behind |
| `~/Documents/Data Science/ADSWP/TabPFN-work-scott` | stale and dirty; the harness built a worktree from it |

`workload.sh` takes the name you give it and reports the checkout it finds; it does not follow your
working directory, so its first line can name a different clone from the one you are in.

Before writing, ask the tree rather than the habit:

```bash
git rev-parse --show-toplevel
git log --oneline -1
git remote -v
```

If `tests/conftest.py` is missing, you are in an incomplete worktree, not a repository with a
missing module. Fix it with:

```bash
git fetch origin
git reset --hard origin/main
```

Which clone is canonical is a human decision and is not recorded here: only the owner knows which
of the older checkouts are disposable.

## 2. Build the environment

```bash
./scripts/bootstrap_dev.sh          # .venv from requirements.lock, Python 3.12
.venv/bin/pytest tests/ -q
```

`requirements.lock` is the authority; `requirements.txt` states ranges (`pandas>=2,<3`) that admit
drift *within* them — scipy 1.10 and 1.17 both satisfy the file, and so do two lightgbm majors — so
two machines can both honour it and disagree on the result. The lock fixes one set of bytes.

The eight failures in the #516/#526 session came from a temp venv that was built by hand, not from
`requirements.txt`; they were pandas 3.1 / numpy 2.5 / no matplotlib, i.e. an environment nobody
declared. `bootstrap_dev.sh` asserts the pins after installing, so a venv that merely imports the
right names fails the check.

Python 3.12 is what this repository is tested on. `tabpfn==8.5.0` itself needs only ≥ 3.10; the
binding constraint is the lock's `numpy<2`, which has no 3.13 wheel, so 3.12 is the version that
installs without compiling.

## 3. Run the gate

```bash
.venv/bin/pytest tests/ -q                     # the full gate
.venv/bin/pytest tests/test_positive_control.py -q   # targeted: seconds
.venv/bin/ruff check scripts/ src/ tests/
./scripts/check.sh                             # the same commands CI calls
```

One check at a time is `./scripts/check.sh <name>`, where the name is one of `ruff`, `pytest`,
`shellcheck`, `evidence`, `doclinks`, `docstatus`, `citation`, `verdict`.

**How long the suite takes is not settled.** Two runs of the same suite here, a lock-built venv in a
worktree on the SSD: **724 passed in 551 s** (2026-11-10, quiet machine) and **724 passed in
1,167 s** (same day, with CI and another test run competing for the CPU). A 2× spread from load
alone. `CONTRIBUTING.md` records **667 tests in 1,720 s** on 2026-11-06, and `CHANGELOG.md` carries
that figure as its own correction of an earlier one. The three numbers are stated rather than
averaged; budget from a run on the machine you are on.

CI is eight checks, not one; a change that passes pytest can still fail the rest. A missing tool
exits non-zero rather than skipping.

## 4. Create a worktree

```bash
./scripts/new_worktree.sh feat/531-some-work          # from origin/main
./scripts/new_worktree.sh fix/532-thing develop       # from another base
```

It lands beside the repository as `<repo>-worktrees/<branch-with-slashes-as-dashes>`, checks that
the new tree is at `origin/<base>` **and** that `tests/conftest.py` exists, and removes the worktree
and branch if either check fails, so a retry is not blocked by the leftovers.

Each worktree needs its own `.venv` (about 1.9 GB) unless you point `VENV` at an existing one:
`VENV=../tabular-foundation-model/.venv ./scripts/bootstrap_dev.sh` refreshes that environment
rather than creating a second copy.

If you create one with the harness `worktree_create` tool instead, treat its output as untrusted:
reset to `origin/main` and check for `tests/conftest.py` before the first edit.

## 5. Pins

| What | Pinned by | Value at 2026-11-10 |
| --- | --- | --- |
| Library | `requirements.lock` | `tabpfn==8.5.0`, `tabpfn-client==0.3.3` |
| Scientific stack | `requirements.lock` | numpy 1.26.4, pandas 2.3.3, scipy 1.17.1, scikit-learn 1.6.1 |
| Lint | `requirements.lock` and `.github/workflows/ci.yml` | ruff 0.16.4 in both (CI was 0.15.8 until #530 aligned it) |
| Python | CI workflow and this page | 3.12 |

**The lock fixes one machine, not the whole gate.** CI still installs the ranges in
`requirements.txt` — a deliberate scope, not an oversight: moving CI onto the lock is its own change
with its own evidence. The lint pin is now equal on both sides, so a local lint pass and CI's agree;
the test run is equal wherever the ranges resolve to the lock's versions.

`docs/MODEL_VERSIONS.md` records the model timeline; never mix version eras in a claim.

## 6. Things that look like bugs but are not

- **`ModuleNotFoundError` in a fresh worktree** — the worktree is incomplete. `git reset --hard
  origin/main`.
- **Eight failures in `test_d1_profiling`, `test_d5_eudirectlapse`, `test_registry_producers`** —
  pandas 3 / numpy 2 / missing matplotlib. Rebuild from the lock.
- **`git status` reports "unable to map index file"** — the `Documents` volume's index hit a
  transient mmap timeout. Delete `.git/worktrees/<name>/index` and run `git reset`; the working
  tree is preserved.
- **Git operations on the `Documents` clone take minutes** — that volume is slow. Prefer the clone
  you are in; do not assume a 120 s `git ls-remote` timeout means the branch is gone.
- **`git push` from a worktree whose git dir is on the `Documents` volume fails** with
  `error: RPC failed; HTTP 400` and `send-pack: unexpected disconnect`, followed by the misleading
  `Everything up-to-date`, even for a commit that is already on the server (measured 2026-11-10).
  The checkout is the problem, not the branch: fetch the commit into a healthy clone and push from
  there — `git fetch <worktree-path> <branch>:<branch> && git push origin <branch>`.

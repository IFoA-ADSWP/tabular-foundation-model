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
| `~/projects/tabular-foundation-model` | the session's clone; remote named `github`; at `origin/main` |
| `~/tabular-foundation-model` | the clone the global `workload.sh` helper resolves; was weeks behind |
| `~/Documents/Data Science/ADSWP/TabPFN-work-scott` | stale and dirty; the harness built a worktree from it |

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

`requirements.lock` is the authority; `requirements.txt` states ranges (`pandas>=2,<3`) and a fresh
resolve can drift outside them. A session that ran on pandas 3.1 / numpy 2.5 produced eight test
failures that were the environment, not the change (`ValueError: underlying array is read-only`,
`ModuleNotFoundError: matplotlib`).

Python 3.12 is required in practice: `tabpfn==8.5.0` needs ≥ 3.10, and v3 is tested on 3.12.

## 3. Run the gate

```bash
.venv/bin/pytest tests/ -q                     # the full gate, ~9 minutes on this machine
.venv/bin/pytest tests/test_positive_control.py -q   # targeted: seconds
.venv/bin/ruff check scripts/ src/ tests/
./scripts/check.sh                             # all eight checks, the same commands CI calls
./scripts/check.sh ruff|pytest|shellcheck|evidence|doclinks|docstatus|citation|verdict
```

Measured 2026-11-10 in a lock-built venv: 724 passed in 551 s. A handoff had claimed ~28 minutes;
the real figure on this machine is about a third of that. Budget by measurement, not by rumour.

CI is eight checks, not one; a change that passes pytest can still fail the rest. A missing tool
exits non-zero rather than skipping.

## 4. Create a worktree

```bash
./scripts/new_worktree.sh feat/531-some-work
```

It branches from `origin/main`, lands beside the repository as
`<repo>-worktrees/<branch-with-slashes-as-dashes>`, and refuses to print a path whose
`tests/conftest.py` is absent.

If you create one with the harness `worktree_create` tool instead, treat its output as untrusted:
reset to `origin/main` and check for `tests/conftest.py` before the first edit.

## 5. Pins

| What | Pinned by | Value at 2026-11-10 |
| --- | --- | --- |
| Library | `requirements.lock` | `tabpfn==8.5.0`, `tabpfn-client==0.3.3` |
| Scientific stack | `requirements.lock` | numpy 1.26.4, pandas 2.3.3, scipy 1.17.1, scikit-learn 1.6.1 |
| Lint | `requirements.lock` | ruff 0.16.4 |
| Python | CI workflow | 3.12 |

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

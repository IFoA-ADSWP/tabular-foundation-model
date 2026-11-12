# Plan — the runner's on-ramp is one page, and the indexes tell the truth

**Status:** Proposed — awaiting sign-off.
**Origin:** #575. Follows the #484 map, whose #488 front door and #492 cold read fixed the
*actuary's* path and left the *runner's* path untouched.
**Design:** a colleague who will run the code asks a task question, not an era question and not a role
question. Three pages answer it in order — environment, verification, task route — and the indexes that
currently mislead are corrected rather than reorganised.

## What is wrong, measured

- `README.md` Quick Start gives **two environment commands back to back**: `pip install -r
  requirements.txt` and then "reproducible exact-match env (recommended): `uv pip sync
  requirements.lock`". A runner cannot tell which one is the instruction and which is the aside, and a
  third file, `requirements-legacy.txt`, is never introduced anywhere in the README.
- `scripts/README.md` is **47 lines and covers 3 of the 10 subdirectories**. It does not mention
  `run_pilot.py` or `run_fair_test.py` — the two current entry points — nor `eval/` (106 tracked files),
  `gpu_helpers/` (the paid path), `colab_helpers/`, `analyses/`, `diagnostics/`, `bootstrap_dev.sh` or
  `check.sh`.
- `docs/REPRODUCIBILITY_RUNBOOK.md` is **946 lines whose top-level axis is chronology** (A frontier, B
  legacy, C GPU). Its map is registry-topic-key → section, so it helps only a reader who already knows the
  key. A colleague who knows the task and not the key has to scan the file.
- `results/` holds **32 run directories and 2,436 tracked files (79% of the repository)**; `outputs/gpu-pilot/`
  holds the paid record. Nothing at either tree's root says which run ids are current, which are cited and
  which are superseded, so "where is the result I just reproduced?" has no cheap answer.
- No page states the clone cost a runner pays first: **521 MB**, of which `data/` is 92 MB and `results/`
  is 96 MB.

## The five changes

1. **`docs/RUNNING.md`** — new, ≤90 lines, the runner's only page. A three-row route — verify the published
   numbers, run a benchmark, run a paid pilot — and for each: the environment, the command, the output tree
   and the runbook section. Then a short table of which `results/` ids are current and cited, and a pointer
   to `EVIDENCE_MAP.md` for what a run directory contains. The environment column is **per route,
   not one command** — see *The environment, resolved* below.
2. **`scripts/README.md`** — rewritten to cover all ten subdirectories and both current root entry points,
   with one "start here" line per directory and the gate named. The existing benchmark and legacy tables
   survive; they are correct.
3. **`docs/REPRODUCIBILITY_RUNBOOK.md`** — a **task index at the top**, above the existing registry map:
   "I want to X → §". The era sections are untouched.
4. **`README.md`** — Quick Start names **one** environment command and says what the other two files are
   for. One line points at `docs/RUNNING.md`.
5. **`docs/README.md`** — the runner's door added to the route table, so the front door does not send a
   code-runner into the actuary's route.

## Decisions worth arguing with

**Task index, not era reordering.** The era sections are correct and are cross-referenced from the registry
map, from `EVIDENCE_MAP.md` and from the plans that cite sections by number. Reordering them would renumber
§A.1–§C.7 and break every section citation to gain nothing an index does not give. The index is additive.

**No file moves.** `doclinks`, `docstatus`, `citation` and `evidence` all police this tree, and the
repository's own rule is "nothing is moved, so no link breaks". A move buys comprehension an index already
buys, and costs link edits plus a tier argument for each document.

**The run-tree guide goes in `docs/RUNNING.md`, not `results/README.md`.** `results/` is an evidence tree
(`check.sh evidence`, `EVIDENCE_TREES=(outputs results)`). A new page there is an evidence change needing
the `evidence-change` label, to say nothing a docs page cannot say. "Which run ids are current" belongs
beside the command that reproduces them.

**Clone weight is named, not solved.** Detaching ~188 MB of binaries is an evidence-policy decision —
`capture.json` must stay resolvable, and `.gitignore` re-includes `results/**/*.npy` deliberately for #436's
reason. It gets its own ticket rather than riding this one.

## Cold read, before the page exists

Run 2026-11-12 in a fresh context given **the plan text only**, with no repository access, and asked the
question the page has to answer. Verdict: it could not reproduce a published number from the plan — which is
correct, because a plan specifies a page rather than containing it, and #492's test was run against a
finished page. The exercise still earned its keep: it found one contradiction and three empty cells, each of
which would otherwise have been discovered while writing the page.

1. **The plan contradicted itself about the environment.** It claimed one environment command, then sent the
   runner to "verify the published numbers" — which needs `tabpfn-client 0.3.3`, not the `tabpfn 8.5.0` the
   lock installs. Resolved below.
2. **Two entry points were named and neither was assigned to a route.** `run_pilot.py` is the fine-tuning
   pilot, `run_fair_test.py` the regressor fair test; the page says which row each serves.
3. **"Verify the published numbers" carried no command.** It is `notebooks/reproducibility/01`–`03`, whose
   evidence cells read committed files and reproduce their display without credits.
4. **The eight checks were never listed**, though the plan cites them as the gate. The page names them.

The lesson is the one #492 already recorded: a page is only good if a reader can use it, and the time to
find out is before it is written.

## The environment, resolved

Three routes, three environments, and only one of them is built on the laptop:

| Route | Environment | Built by |
| --- | --- | --- |
| Current code — tests, diagnostics, `run_pilot.py`, `run_fair_test.py` | `.venv`, Python 3.12, `tabpfn 8.5.0` from `requirements.lock` | `./scripts/bootstrap_dev.sh`, which asserts the pins (#530) |
| Frontier line — `scripts/eval/`, `scripts/benchmarks/`, repro notebooks 01–03 | the TabArena venv, `tabpfn-client 0.3.3` | [`notebooks/reproducibility/README.md`](../notebooks/reproducibility/README.md) §Setup — **not** `bootstrap_dev.sh` |
| Paid launch — the GPU pilot | the box's own pins | `scripts/gpu_helpers/bootstrap_pilot.sh`, on the rented machine |

`requirements.txt` is the loose floor that `requirements.lock` is compiled from; `requirements-legacy.txt` is
the v2-era path for `scripts/legacy_finetuning/` only and is never used for new work. The README fix names
`bootstrap_dev.sh` as the one command, explains the other two files in one sentence each, and does not
pretend the frontier venv is the same environment.

## Shape

```
docs/RUNNING.md                    # new page
scripts/README.md                  # rewritten to cover the tree
docs/REPRODUCIBILITY_RUNBOOK.md    # task index added at the top only
README.md                          # one environment command, one line to RUNNING.md
docs/README.md                     # the runner's door in the route table
CHANGELOG.md                       # one entry
docs/plans/runner-onramp.md        # this plan
```

**Three `README.md` defects are fixed in the same change, because they sit in the lines being rewritten** —
the practice #488 used. Its directory tree listed `docs/reports/`, dissolved in #200–#202, and `docs/status/`,
which is now `docs/archive/status/`; it called `tests/` "Smoke tests" when it is the suite the gate runs; and
its Dependencies said "Python 3.10+" when `bootstrap_dev.sh` refuses an interpreter that is not 3.12. Its
duplicate "Documentation Index" — a third map beside `docs/README.md` and the report registry — becomes a
pointer, and its stale paragraph about `docs/current/PILOT_2_*` files (there are none) goes with it.

## Verification

```sh
./scripts/check.sh                 # all eight
```

Then the comprehension test the #484 map used, because a page is only good if a reader can use it: a fresh
context given **only** `docs/RUNNING.md` must state (a) the one environment command, (b) the command that
verifies the published numbers, (c) where a run's output lands, and (d) which `results/` ids are current.
Recorded on the ticket, not assumed.

`doclinks` resolves the new page's references or the change does not land; `docstatus` sees no movement
because no tiered document moves; `evidence` and `citation` are untouched by construction.

## What this does not do

- Does not move, delete or retier a document, and changes no tier metadata.
- Does not change any run record, capture, manifest or evidence file — #208 owns the record shape and #353
  owns the per-run table.
- Does not renumber or rewrite the runbook's §A/§B/§C sections.
- Does not reduce the clone size; that is a separate ticket.
- Does not touch the actuary's or the external reviewer's path, which #488 and #492 already settled.

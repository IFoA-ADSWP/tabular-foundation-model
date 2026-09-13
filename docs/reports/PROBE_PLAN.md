# The budget probe — a standalone pilot

> **Status: proposal for review. No spend is authorised by this document.** It runs only after the
> plan and the code it needs are merged, and only on an explicit go-ahead.
>
> **Deliberately separate from the wider Pilot 2 design** (held in the wider proposal, which is **not merged and not required for this pilot**). The probe's outcome
> will change that design, so the two are decoupled: approving, running and reading this commits
> nobody to the wider testing.

## What it tests

**One question:** does fine-tuning TabPFN for longer than the first pilot did make it better — on the
dataset it was trained on?

One dataset, one split, four models that differ **only** in how long they trained, all scored on the
**same** test rows. Nothing crosses datasets; nothing is pooled.

| Arm | What it is |
| --- | --- |
| `A_raw` | raw TabPFN, no training — the baseline |
| `B_ft3` | fine-tuned, 3 epochs — what the first pilot did |
| `B_ft10` | fine-tuned, 10 epochs — midpoint |
| `B_ft30` | fine-tuned, 30 epochs — the library's default, the "fair budget" nobody has tested |

## Why it is worth nine pence

1. **The training budget is ~65% of the wider programme's modelled cost.** It is the single most
   expensive assumption in the plan, and it is the cheapest one to test.
2. **The first pilot only ever tried 3 epochs.** The library's default is 30. So the existing
   "fine-tuning does not help" verdict stands *at 3 epochs* — that is a statement about a budget
   nobody chose deliberately.
3. **A flat ladder is worth as much as a rising one.** It closes the expensive rungs before they are
   bought, and it is a reportable finding rather than a failed run.
4. **It exercises the paid pipeline end to end for the first time** — see *What it discharges*.

## The design, and the reason for each parameter

| Parameter | Value | Why this value |
| --- | --- | --- |
| **Dataset** | **uslapseagent** | Selected on **resolution, not cost**: 369 positives, resolves **≥ 0.009 ROC**. `coil2000` — the repository's habitual first choice — resolves only ≥ 0.061, because 6% of its rows are positive. A null on the wrong dataset is not evidence |
| Training rows | 2,000 | R1 parity — the same scale as every comparison already held, so the `B_ft3` rung is directly comparable to R1 rather than merely similar |
| Test rows | 1,000 | This is what sets the resolution. The floor is driven by the test set's positives, not the training rows |
| Reserved rows | 500 | Loaded then excluded, so the train-size cap can never reach a test row; fingerprinted so the drop is visible rather than silent |
| Split | stratified, one split | Keeps the positive rate at the dataset's rate, because the resolution depends on it. One split because this is screening, not estimation |
| Epochs | 3 / 10 / 30 | Parity · midpoint · library default |
| Context | matched across arms, asserted | The confound the historic comparison died of |
| Seeds | 1 (42) | Screening. Three seeds is a later, separate decision |

**Recording:** every arm states the commit it ran from, its declared epochs, its **row-epochs**
(training rows × epochs) and the epochs **actually executed**. Row-epochs matter because an epoch is a
pass over the split: 30 epochs is 60,000 row-passes at 2,000 rows and 150,000 at 5,000, so the same
label means different amounts of training at different scales.

## Three outcomes, not two

1. **The ladder rises** → the budget matters; carry the winning rung forward.
2. **The ladder is flat, but the arms beat `A_raw`** → fine-tuning works and the budget does not
   matter; carry **3 epochs** forward, which is the cheaper configuration. This is not a dead result.
3. **The ladder is flat and the arms do not beat `A_raw`** → the fine-tuning hypothesis is dead **at
   this scale**; reported with its minimum detectable effect beside it.

## Two preconditions before the result may be read

- **Early stopping pinned, or the executed epoch count recorded.** Otherwise "30 epochs" means
  "whatever early stopping allowed", and the probe measures a different quantity from the one it names.
  **This is not yet built — it is the one outstanding code change.**
- **`B_ft3` must replicate the first pilot** — R1 measured +0.0014 on coil2000 and −0.0008 to +0.0095
  across the four datasets. If `B_ft3` misses that band, the pipeline has changed and nothing else in
  the run is interpretable. A free validity gate.

## What it is not

- **Not transfer.** Nothing here tests a dataset the model has never seen; that is the wider design.
- **Not pooling.** No dataset is combined with another.
- **Not a scale study.** The result is conditional on the 2,000-row sample, and says so.
- **Not a verdict on the other three datasets.** One dataset is chosen; the result speaks for it and
  is reported as such.

## What it discharges

The first real run against the paid path, which confirms three things that have only ever been tested
in theory: the run **manifest** (audit record), the **weights save/reload**, and the **licence check**
on a cold container.

## How to run it

The launcher is `scripts/gpu_helpers/vast_run.sh`: it selects a box, creates the instance, runs the
bootstrap, pulls the artifacts, and destroys the box on every exit it can catch — with the watchdog as
the backstop for the exits it cannot.

```bash
# the licence token lives in its mode-600 file; load it into THIS shell only
eval "$(bash scripts/gpu_helpers/keys.sh env)"     # confirm with: keys.sh check

bash scripts/gpu_helpers/vast_run.sh \
  --dataset uslapseagent \
  --arms A_raw,B_ft3,B_ft10,B_ft30 \
  --max-dph 0.65
```

Then read it, off the artifacts the run pulled down:

```bash
python3 scripts/analyse_pilot.py --outdir outputs/finetune/pilot --baseline A_raw
```

`--baseline A_raw` is where the estimand comes from: `Delta = arm - A_raw`, and a **negative** Delta means
fine-tuning won.

**Why each value:**

| Flag | Value | Reason |
| --- | --- | --- |
| `--dataset` | `uslapseagent` | chosen on **resolution**, not cost or familiarity: 369 test positives resolve an effect of about 0.009, where coil2000's 57 resolve only about 0.061 |
| `--arms` | `A_raw,B_ft3,B_ft10,B_ft30` | the ladder and its baseline. Each rung carries its **own** epoch budget, so a stray `--epochs` cannot flatten the ladder |
| `--max-dph` | `0.65` | the default ceiling of 0.60/hr excludes the cheapest acceptable boxes observed (about 0.628/hr) |
| `--yes` | **not passed** | the confirmation prompt *is* the gate: nothing is provisioned without an explicit, current go-ahead |

**Attempts and ceiling:** one attempt, **0.25 all-in** — about 9p of compute inside roughly 2.7 minutes of
boot, pull, licence and teardown around 7.4 minutes of work. A second attempt is a new decision, not a retry.

**On the dataset pass-through.** `--dataset` was not exposed by the launcher when this plan was written, so
the flow ran *every* registered dataset — the first pilot's behaviour, four times the price here, and not
this experiment. The pass-through ships in this same PR, which is what lets the probe be initiated from a
merged `main` exactly as specified above.

## Approval and sequencing

| # | Step |
| --- | --- |
| 0 | *(in this PR)* The early-stopping pin, row-epochs recording and the dataset pass-through |
| 1 | **Merge the code and this document.** The probe runs from a commit on `main`, not an unmerged branch |
| 2 | **Run it** — ~9p, ceiling $0.25, one attempt, **watched** (every control is unit-tested and none has yet run on real hardware) |
| 3 | **Read it** — with the replication gate and the row-epochs in hand |
| 4 | **Then** decide the wider testing. Nothing beyond this probe is released before it |

**Nothing is provisioned without an explicit, current go-ahead**, and the wider experiments are not
approved — they require team review before anything is committed.

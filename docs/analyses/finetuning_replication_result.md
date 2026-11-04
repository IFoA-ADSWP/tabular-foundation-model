# Fine-tuning replication — the effect is real, and it is +0.0035 AUC

> **Status:** active — result, 2026-11-04. **Question:** does in-domain fine-tuning of TabPFN beat raw
> TabPFN on `uslapseagent` at 10,000 rows, by at least δ = 0.002 ROC AUC? **Run:**
> `results/20261104T123839Z/` (56 records, committed). **Decision it settles:** D14 — the pilot
> publishes and stops. **No further runs are authorised by this result.**

## Answer

**Yes.** Fine-tuning at 30 epochs beats the in-run raw baseline by **+0.0035 ROC AUC**, 95% interval
**[+0.00272, +0.00428]**, with Brier no worse (+0.0003 against a +0.001 allowance).

| | Value |
|---|---|
| Mean ΔAUC over 28 seeds | **+0.0035** |
| 95% interval (between-seed SD 0.0021, n = 28) | **[+0.00272, +0.00428]** |
| Brier, worst seed | +0.0003 (guard ≤ +0.001) |
| Null false-positive rate (2,000 permutations/seed) | 0.0000 |
| Model | `v3_default` (`tabpfn-v3-classifier-v3_default.ckpt`), tabpfn 8.5.0 |
| Comparator | the `A_raw` arm of the same seed, same launch |

The whole interval sits above δ, so this is not a marginal clearing and does not need to be defended
from "close enough" arguments later.

## The design that produced it

Pre-registered in `docs/current/FINETUNING_PREREGISTRATION_2026-11.md` before any spend:

1. **Probe** — 4 arms × 10 seeds (45–54) measured the between-seed SD and picked the rung: `B_ft30`,
   the highest probe mean that fitted the cost ceiling.
2. **Resolution gate** — the implied seed count (28) was computed from the probe's SD before the
   replication was authorised.
3. **Replication** — `A_raw` + `B_ft30` over 28 fresh seeds (55–82), disjoint from the probe's.

The seed count was fixed by formula, not chosen after seeing data. That is the difference between this
result and the October one: the anchor ran 2 seeds, one passed and one failed, and the disagreement was
unresolvable because two seeds cannot estimate between-seed variance.

## Why the earlier stop was wrong

The null control (`docs/analyses/null_control_scoring_path.md`) permuted the anchor's labels 5,000 times
per seed: the design resolved **±0.010** against an effect of **0.002–0.003**. Every observed delta sat
inside the null band (p 0.29–0.84). The October stop was therefore a **power stop**, not a null — the
correct reading is the one D11's own pre-registered mapping gave for "test-set power unreachable":
report the power limit, revisit scale, or accept the limit.

## What this does not establish

- **Other datasets.** One dataset, `uslapseagent`. Phase 2 breadth was declined by D14 and is not
  implied by this result.
- **Other epoch budgets.** 30 epochs is the top of the ladder tested; the probe's dose-response
  (+0.0015 at 3, +0.0021 at 10, +0.0030 at 30) is monotone but every gap is inside seed noise.
- **Transfer.** Phase 3, untouched.
- **Magnitude in context.** +0.0035 AUC is real and small. Raw TabPFN's margin over the best actuarial
  baseline is **+0.068** on COIL 2000 — roughly twenty times larger. Choosing TabPFN matters far more
  than tuning it, and any report that quotes this number without that comparison overstates it.

## Cost, measured

| Launch | Purpose | Cost |
|---|---|---|
| attempt 1 (RTX 3090) | failed before writing any artifact | $0.042 |
| `20261104T122235Z` | probe (RTX 4090) | $0.078 |
| `20261104T123839Z` | replication (RTX PRO 4000) | $0.188 |
| **Total** | | **$0.308** |

**The replication breached its $0.15 per-launch ceiling by 25%** ($0.188 against a $0.122 projection).
The projection used the probe's `B_ft30` timing of 38.9 s/seed on an RTX 4090; the replication ran at
~62 s/seed on an RTX PRO 4000. A projection built on one host's timings does not transfer, and the next
pre-registration should carry a host margin or use the slowest observed arm time.

## Reproduction

```
python scripts/analyses/verdict.py --run results/20261104T123839Z --delta 0.002 --reps 2000
```

Same inputs, same output: the tool is deterministic, reads only the committed capture, and refuses a
run whose arrays do not hash to its record. The gate runs the same tool against the anchor to keep the
prose and the arithmetic together.

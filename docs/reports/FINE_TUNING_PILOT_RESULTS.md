# Fine-Tuning Pilot — Pre-Fine-Tuning Baseline Results

> **Status:** partial. Arms A/E/F complete on all four datasets. **Arm B (fine-tuning) is not yet measured** — it cannot fit the CPU runtime (see §5). The research question in `PRE_FINETUNING_INVESTIGATIONS.md` is therefore not yet answered; this report establishes the baseline that arm B must beat.

## Version stamp

| Field | Value |
| --- | --- |
| Run date | 2026-09-12, 09:18:03 → 09:20:56 UTC (12 runs; ~3 min compute after ~90 s setup) |
| TabPFN weights | **`tabpfn-v3-classifier-v3_default.ckpt`** (212.8 MB) |
| TabPFN package | `tabpfn 8.5.0` |
| Device | CPU (Colab free tier, 12 GB, no swap) — `Device: cpu`, no GPU |
| Seed | 42 (single) |
| Branch / commit | `finetune-v2`, launcher `eb45e0e` |

Weights ID evidenced from the resolved cache file on the VM (`/root/.cache/tabpfn/tabpfn-v3-classifier-v3_default.ckpt`), **not** from the run manifests — `checkpoints` recording was added after this run and applies to future runs only. See §6.

`v3_default` is the repo's current citable line per `docs/MODEL_VERSIONS.md`, so these numbers sit on the same model line as the frontier benchmark work rather than the frozen v2-era tables.

## 1. Purpose

`PRE_FINETUNING_INVESTIGATIONS.md` frames the goal as: does fine-tuning TabPFN on insurance data improve performance on held-out insurance tasks, versus raw TabPFN and actuarial baselines?

Arm A (raw TabPFN) is the "no fine-tuning" reference. Without it the B-vs-A delta — the actual quantity of interest — has no denominator. This report supplies A, E and F.

## 2. Configuration

```python
PILOT_CONFIG = {
    "context_samples": 64,
    "max_finetune_steps": 3,
    "n_estimators": 2,
    "learning_rate": 1e-5,
    "fit_mode": "batched",
}
```

| Setting | Value |
| --- | --- |
| Train / test rows | 2,000 / 1,000 (stratified, `random_state=42`) |
| Preprocessing | `pd.get_dummies(drop_first=False)`, `fillna(0)`, `StandardScaler` |
| Datasets | `coil2000`, `uslapseagent`, `eudirectlapse`, `spanish_motor_lapse` |
| Max rows read | 3,500 per dataset |

Arms (from `ARMS` in `scripts/run_pilot.py`):

| Arm | Definition |
| --- | --- |
| `A_raw` | Raw TabPFN classifier, no fine-tuning |
| `B_in_domain` | TabPFN fine-tuned on the same dataset's training split |
| `E_glm` | Logistic regression on scaled features (GLM baseline) |
| `F_catboost` | CatBoost, 200 iterations (GBDT baseline) |

## 3. Results

ROC AUC is the primary metric; Brier and PR AUC reported alongside because a ROC-only win can hide calibration or ranking regressions.

| dataset | arm | ROC AUC | Brier | PR AUC | secs |
| --- | --- | --- | --- | --- | --- |
| coil2000 | **A_raw** | **0.7679** | **0.0507** | **0.1882** | 83.5 |
| coil2000 | E_glm | 0.6830 | 0.0559 | 0.1307 | 0.03 |
| coil2000 | F_catboost | 0.6993 | 0.0516 | 0.1753 | 3.2 |
| eudirectlapse | **A_raw** | **0.5879** | **0.1137** | **0.1939** | 68.9 |
| eudirectlapse | E_glm | 0.5744 | 0.1163 | 0.1601 | 0.02 |
| eudirectlapse | F_catboost | 0.5738 | 0.1151 | 0.1830 | 0.6 |
| spanish_motor_lapse | **A_raw** | **0.7230** | **0.1980** | **0.5699** | 54.2 |
| spanish_motor_lapse | E_glm | 0.6166 | 0.2222 | 0.4469 | 0.01 |
| spanish_motor_lapse | F_catboost | 0.7114 | 0.2015 | 0.5412 | 0.7 |
| uslapseagent | **A_raw** | **0.9360** | **0.0869** | **0.8359** | 33.8 |
| uslapseagent | E_glm | 0.9271 | 0.0910 | 0.8172 | 0.01 |
| uslapseagent | F_catboost | 0.9297 | 0.0934 | 0.8293 | 0.5 |

Deltas (A minus baseline; positive ROC/Brier-improvement means TabPFN better):

| dataset | ROC A−E | ROC A−F | Brier A−E | Brier A−F |
| --- | --- | --- | --- | --- |
| coil2000 | +0.0849 | +0.0686 | −0.0052 | −0.0009 |
| eudirectlapse | +0.0136 | +0.0141 | −0.0026 | −0.0014 |
| spanish_motor_lapse | +0.1065 | +0.0116 | −0.0242 | −0.0035 |
| uslapseagent | +0.0090 | +0.0064 | −0.0041 | −0.0065 |

## 4. Findings

1. **Raw TabPFN is first on all four datasets, on all three metrics.** The win is not a ROC artefact — Brier and PR AUC agree in every cell, so it is neither a ranking-only nor a calibration-only effect.

2. **The margins track the complexity diagnostic.** `spanish_motor_lapse` (+0.106 vs GLM) and `coil2000` (+0.085) show wide gaps; `eudirectlapse` is the narrowest at **+0.014**. The earlier complexity diagnostic classed `eudirectlapse` as `LINEAR — no non-linear structure for TabPFN to exploit`, and `docs/MODEL_VERSIONS.md` already records `eudirectlapse` as a *"genuine classification loss"* with additive structure. Independent methods converging on the same dataset being the weakest case for TabPFN is a consistency check, not a surprise — but it also means `eudirectlapse` is where fine-tuning has the least headroom to demonstrate value.

3. **`uslapseagent` is a near-tie** (+0.009 vs GLM) despite the highest absolute AUC (0.936). High absolute performance leaves little room for a delta, so this dataset cannot discriminate between methods well.

4. **Arm A is the entire compute cost.** 34–83 s per dataset versus sub-second for E and 0.5–3.2 s for F. Any future grid should be sized on arm A, and note A does not necessarily speed up proportionally on GPU (it is not FLOP-bound in the same way as training).

## 4b. GPU re-run of arm A — device variance, and what the artifact now holds

Arm A was re-run on a rented GPU on **2026-09-12 17:06 UTC**. The pipeline is now
proven end to end (provisioning, transport, licence, arm loop, artifact return), and
the GPU numbers differ slightly from the CPU table in §3:

| dataset | A_raw CPU (§3) | A_raw GPU | delta |
| --- | --- | --- | --- |
| coil2000 | 0.7679 | **0.7673** | −0.0006 |
| eudirectlapse | 0.5879 | **0.5872** | −0.0007 |
| spanish_motor_lapse | 0.7230 | **0.7239** | +0.0009 |
| uslapseagent | 0.9360 | **0.9355** | −0.0005 |

Same seed, same config, same checkpoint — so this is **device-dependent
floating-point**, not a behavioural change. It matters only for citation: quote
one device's numbers, and say which. The direction of every §4 conclusion is
unaffected (all four deltas are ~1e-3 against margins of 6e-3 to 1e-1).

Provenance recorded by the GPU run itself: `tabpfn 8.5.0`, `torch 2.7.0+cu128`,
`python 3.11.12`, device `cuda` on an **NVIDIA RTX PRO 5000 Blackwell**,
checkpoint `tabpfn-v3-classifier-v3_default.ckpt`.

**Caution — `outputs/gpu-pilot/` now mixes provenance.** The box clones the repo,
so the committed CPU outputs are already on disk, and the aggregate re-reads them.
The file therefore holds four GPU `A_raw` rows (17:06) alongside four CPU `E_glm`
and four CPU `F_catboost` rows (09:20). That is benign here — GLM and CatBoost are
CPU models and device cannot affect them — but it is the same failure mode that
once printed a complete results table made entirely of stale numbers. Read the
`device`, `timestamp` and `versions` columns before trusting any row.

## 5. Arm B: not measured, and why

Arm B has never completed a run. On the 12 GB CPU runtime it was killed by the kernel OOM killer:

```
Memory cgroup out of memory: Killed process 27691 (python3)
  total-vm:13561664kB  anon-rss:11824532kB
Swap: 0
```

~11.8 GB of a 12 GB cgroup with no swap. This is a **hardware ceiling, not a bug**.

The failure mode was worse than a normal error: the kernel SIGKILLs the interpreter, so the per-arm `except Exception` in `run_single_dataset` could never fire. No traceback was printed and the three remaining arms never ran — only `coil2000/A_raw` survived. That is the systemic issue addressed by the fix below.

**Fix applied** (commit `eb45e0e`, *not* in effect for this run's numbers):

- each arm now runs in its own subprocess, so a SIGKILL costs one arm rather than the batch;
- the launcher reports `rc` per arm, so a signal death is visible instead of silent;
- `--arms` on the runner and an `ARMS` env var on the launcher allow skipping arms a VM cannot hold.

**Consequence:** the B-vs-A delta — the primary quantity of interest — remains unmeasured. It requires the GPU runtime, and it is not guaranteed to fit there either: 11.8 GB was *system RAM* usage, and the T4 offers 16 GB *VRAM*, which is a different budget. `TabPFNClassifier` accepts a `memory_saving_mode` argument (confirmed present in 8.5.0) if trimming is needed, but enabling it changes the recorded config and must be treated as a deliberate, documented deviation rather than a silent one.

## 6. Provenance gaps and deviations

State these when citing these numbers.

1. **No `checkpoints` field in these manifests.** The run manifests record `versions.tabpfn = 8.5.0` — the *package*, which `docs/MODEL_VERSIONS.md` explicitly warns is not the model: *"`tabpfn==2.6.0` is the pip package, not the model."* The weights ID above was established after the fact from the VM cache. `_checkpoints()` now records resolved `.ckpt` basenames per run, so future runs carry this automatically.

2. **Package version deviates from the repo pin.** `requirements.txt` pins `tabpfn>=6,<7`; this run used **8.5.0**. Weights (`v3_default`) and fine-tuning API were verified compatible, but the package major differs from the repo's declared pin, so arm B's behaviour under 8.5.0 is unverified for the same reason it is unmeasured.

3. **`requirements.txt` is deliberately not used by the launcher.** It pins `numpy>=1.24,<2`, and numpy 1.x has no cp313 wheels, so pip compiles numpy from source (~20 min). The launcher installs named packages and lets pip resolve wheels (`numpy 2.1.3` in this run).

4. **Single seed, single split.** Seed 42, one 2,000/1,000 stratified split, no folds and no confidence intervals. Differences of ~0.01 ( `uslapseagent`, `eudirectlapse` ) are within the range a different split could plausibly move; treat those two rows as directional only. No paired significance testing has been done.

5. **Reported to 4 dp with no uncertainty.** Read as point estimates, not as separated effects.

## 7. What would change the conclusion

- Arm B on GPU — the outstanding blocker.
- Multi-seed replication and paired tests, particularly before claiming anything about the two near-ties.
- Confirming that the dataset pipeline's row cap (3,500) interacts with `eudirectlapse`'s 23k+ rows, which was flagged in the design review as a sizing risk.

## Source Workbooks

- `scripts/run_pilot.py` — pilot runner (arms, config, per-run persistence)
- `scripts/colab_helpers/launch_pilot.sh` — detached Colab launch (commit `eb45e0e`)
- `scripts/colab_helpers/poll_pilot.py` — remote log poll
- `scripts/colab_helpers/export_predictions.py` — packs the per-run `.npy` outputs into the committed predictions parquet (needed because `.gitignore` excludes `*.npy`)

## Evidence Files

- `outputs/finetune/pilot/pilot_metrics.parquet` — aggregated metrics (12 rows)
- `outputs/finetune/pilot/pilot_predictions.parquet` — per-row `y_true` / `y_prob` for all 12 runs (12,000 rows), so metrics can be recomputed or added to without re-running arm A. Verified to reproduce every ROC AUC and Brier in §3 to 1e-9
- `outputs/finetune/pilot/<dataset>/<arm>/meta.json` — per-run config, versions, device, timings

> **Not committed:** the runner's per-run `predictions.npy` / `ground_truth.npy`. `.gitignore:139` excludes `*.npy` repo-wide; `pilot_predictions.parquet` above is the committed equivalent, and the `.npy` originals remain on the run VM only.

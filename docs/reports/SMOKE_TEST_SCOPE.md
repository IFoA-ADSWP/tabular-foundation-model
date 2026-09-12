# Smoke Test Scope — What R1 Has and Has Not Established

> Date: 2026-09-12 | Status: current | Related: #22
> Design: `FINE_TUNING_EXPERIMENT_DESIGN.md` (this is rung **R1** of that design)
> Results: `FINE_TUNING_PILOT_RESULTS.md` (the numbers; §5d covers statistical validity)
> Runbook: `../REPRODUCIBILITY_RUNBOOK.md` §C (how to operate the harness)

---

## 0. Why this document exists

R1 was a **smoke test**. Its job was to prove the pipeline works, sense-check the
fine-tuning code, and produce reusable scripts — not to answer the research question.

That distinction is easy to lose once numbers exist. This document fixes the boundary
explicitly: **what has been exercised and verified**, **what has never been exercised**,
and **the technical facts a follow-up run must inherit**. A future test should be designed
against §4 (the gaps) and §5 (the inherited constraints), not against the pilot's headline
numbers.

---

## 1. What the smoke test was

R1 of `FINE_TUNING_EXPERIMENT_DESIGN.md`:

| Element | Specification | Executed |
| --- | --- | --- |
| Datasets | 4 of 15: coil2000, uslapseagent, eudirectlapse, spanish_motor_lapse | yes |
| Arms | A_raw, B_in_domain, E_glm, F_catboost | yes |
| Config | one config only: context_samples 64, max_finetune_steps 3, n_estimators 2, lr 1e-5, fit_mode batched | partially (§6.5) |
| Split | design: 70/30 stratified seed 42. Actual: fixed 2,000 train / 1,000 test cap | deviated |
| Scale | R1 = 2,000 train / 1,000 test / 2,000 pool | yes |
| Device | design: Colab T4 (free). Actual: Vast.ai, 4 different GPUs | deviated (Colab T4 was 503) |

Nominal size: 4 datasets x 4 arms = 16 arm-runs. **All 16 were produced**, on 10 provisioned
instances, for **$0.3382**.

---

## 2. Execution record — what actually ran

Ten instances were provisioned. Only some carried a successful run:

| run_id | instance | GPU | transport | min | cost | what happened |
| --- | --- | --- | --- | --- | --- | --- |
| 20260912T144012Z | 50756703 | RTX 6000 Ada | execute | 0.03 | $0.0003 | aborted immediately |
| 20260912T144946Z | 50757464 | RTX 6000 Ada | execute | 3.08 | $0.0337 | **transport bug** — `execute` is not a shell; no arm ran |
| 20260912T150830Z | 50758729 | RTX 6000 Ada | onstart | 5.08 | $0.0459 | ran; **licence gate** rejected all 4 datasets; **leaked ~64 min** |
| 20260912T161508Z | 50765553 | RTX 4090 | onstart | 4.97 | $0.0365 | never started (`intended_status: stopped`) |
| 20260912T163050Z | 50766615 | RTX 4090 | onstart | 11.35 | $0.0759 | never started (image pull stalled) |
| 20260912T164324Z | 50769223 | RTX PRO 5000 | onstart | 2.00 | $0.0219 | preflight ran |
| 20260912T170033Z | 50771451 | RTX PRO 5000 | onstart | 1.88 | $0.0206 | preflight ran |
| 20260912T170703Z | 50772306 | RTX PRO 5000 | onstart | 2.43 | $0.0266 | preflight ran |
| 20260912T171210Z | 50773139 | RTX PRO 5000 | onstart | 2.62 | $0.0286 | produced **A_raw GPU numbers** |
| 20260912T201944Z | 50795221 | L40S | onstart | 5.32 | $0.0482 | produced the **complete A/B result** (decisive run) |

**Cost to date: $0.3382.** Of that, $0.1796 is attributable to runs with `bootstrap_rc` recorded
as 0; the remainder includes the transport failures, the provisioning failures, and the ~64-minute
licence-gate leak. **Roughly half the spend bought nothing.**

This is the honest shape of a first smoke test: **6 of 10 instances failed before or at the
gate**, and the pipeline only became reliable after four separate defects were found and fixed
(transport, empty-log polling, `intended_status`, licence name).

---

## 3. What the smoke test HAS done — verified capabilities

Each item below is evidenced, not assumed. Evidence: the container log, returned artifacts,
the per-run JSONs, or the ledger.

### 3.1 Provisioning

- Query-based offer selection works (no hardcoded instance IDs): offers filtered by
  `gpu_ram`, `disk_space`, reliability, bandwidth, price; picked by value (dlperf/$).
- Instances were created on **four GPU models across four hosts** — RTX 6000 Ada, RTX 4090,
  RTX PRO 5000 Blackwell, L40S. Host/machine IDs are recorded per run.
- Bounded retry across hosts works: `--max-attempts` with a failed `machine_id` skipped on retry.
- Image selection is driven by the host's CUDA capability (`pick_image.py`), verified against
  the image <-> torch <-> CUDA matrix in the runbook.
- **Teardown works on every exit path**: `trap ... EXIT` + `destroy ... -y` + a launchd watchdog
  on a 60-minute age ceiling. A leaked instance was caught and destroyed.

### 3.2 Transport

- **`--onstart <file>` + `vastai logs` is the working transport.** `vastai execute` accepts
  only `ls`/`rm`/`du` and cannot run a shell — that was the first defect found.
- The container log **caps every line at exactly 500 characters**, so artifact payloads are
  folded into tagged 440-character chunks and reassembled client-side. **Round-trip verified
  sha256-identical** (13,638-byte parquet).
- The bootstrap emits `BOOTSTRAP FINISHED` via an EXIT trap on every path, so a run that dies
  early is still distinguishable from an empty log.
- No `--ssh --direct` on create — it sets `image_runtype: ssh_direct ssh_proxy`, and Vast then
  parks the instance at `intended_status: stopped`. We never use SSH (the team context has no keys).

### 3.3 Licensing and gated weights

- The TabPFN licence gate was passed **end to end on a remote box with no interactive terminal**:
  `TABPFN_TOKEN` injected from a mode-600 file, weights downloaded, a fit completed.
- The licence name is derived correctly: **`tabpfn-3-license-v1.0`** (an identifier from the HF
  repo, *not* a package version). The endpoint returns `{"accepted": true}`.
- A **preflight gate** runs before any arm and refuses to proceed if auth fails — it aborted
  runs rather than burning 16 identical failures. This gate paid for itself the first time it fired.

### 3.4 Model execution

- Raw TabPFN inference produced genuine numbers on all four datasets (GPU).
- **The fine-tuning path (arm B) completed on GPU for the first time on record** — four datasets,
  18-36 s each, fitting comfortably (50.8 GB VRAM free). It uses the library's shipped
  `FinetunedTabPFNClassifier`, not a hand-rolled loop.
- CPU baselines (E_glm, F_catboost) produced numbers for all four datasets.
- Metrics (ROC AUC, PR AUC, Brier, run time) computed and aggregated for all 16 arm-runs.

### 3.5 Artifacts

- Metrics metadata returned from the box and landed locally.
- Per-arm predictions returned for A_raw, E_glm, F_catboost (see §6.4 for the arm B gap).
- The `PILOT RESULTS SUMMARY` table printed by a run was identified as possibly **stale
  committed data** rather than that run's output — a trap a future run must avoid.

### 3.6 Reusable code (a first-class requirement, not a nice-to-have)

Every step is a checked-in script, not a manual command:

```
scripts/run_pilot.py                       # experiment definition + arm registry
scripts/gpu_helpers/vast_run.sh             # provision -> onstart -> poll -> artifacts -> destroy
scripts/gpu_helpers/bootstrap_pilot.sh      # box-side: clone, deps, preflight, arms, artifact channel
scripts/gpu_helpers/select_offer.py         # query-based offer selection
scripts/gpu_helpers/pick_image.py           # CUDA -> image mapping
scripts/gpu_helpers/keys.sh                 # one-rule secret store (mode-600 files under ~/.config)
scripts/gpu_helpers/vast_watchdog.sh        # leak detection
scripts/gpu_helpers/mock_vastai.sh          # PATH-shadowable mock for testing without spend
scripts/colab_helpers/                    # the free-tier path
```

The mock (`mock_vastai.sh`) allows the whole runner to be exercised with **zero spend** — the
single most important reusability asset here.

---

## 4. What the smoke test has NOT done — never exercised

### 4.1 The research question itself

The design's question is whether fine-tuning improves performance on **unseen insurance
tasks**. R1 ran **Q0 only** (in-domain: fine-tune and evaluate on the same dataset).

**Arms C and D — the pool-composition / transfer arms — have never been run.** These are
defined in the design (`C — all-other pooled`, `D — homogeneous pooled`, both evaluated on the
target dataset). Until one of them runs, **the actual deployment question is untested**, and
nothing in R1 speaks to it. R1 can say "in-domain fine-tuning on this dataset changed nothing";
it cannot say anything about adapting to a new dataset.

### 4.2 Scale

Only **R1** was run. R2 (5,000 train / 2,000 test / 10,000 pool) and R3 (full datasets, ~120K
pool, rented GPU) have never been exercised. R1's 2,000-row train cap is the *smallest* rung.

### 4.3 Configuration space

One config was run. The design's expanded grid — `context_samples` 64/128,
`max_finetune_steps` 1/3/5, `n_estimators` 2/8 — is entirely unexercised. With 3 passes at
lr 1e-5, the lever tested was deliberately small, which biases toward finding no effect.

### 4.4 Statistical design

- **One seed (42), one split.** No variance estimate exists for any delta.
- **No cross-validation or repeated folds.**
- **The paired test on the B-vs-A comparison has never been run** — blocked, not rejected
  (§6.4). It was demonstrated on A_raw vs E_glm instead, where it excludes zero on 3 of 4 datasets.
- **No confidence intervals were reported** in the results; they were computed afterwards.
- The design's **R3 gate** (`proceed if B > A or B > E in R2`) has never been formally evaluated
  against a result, because R2 has never run.

### 4.5 Data coverage

- **4 of 15 datasets** in the design. Nine classification datasets (freMTPL2 Binary, Aus.
  Vehicle, Spanish Motor Freq, bemtl16, bemtl97, norauto, fretelematic, ...) untouched.
- **All four regression targets untouched.** The design lists four.
- **64-93% of each dataset used was discarded** by the 3,500-row loader cap, taken via an
  unstratified `df.sample` before the stratified split.
- 500 rows per dataset are loaded and never used.

### 4.6 Metrics and validation

- No calibration metric on the fine-tuned arm (fine-tuning can distort probabilities invisibly here).
- No out-of-time or external holdout.
- No per-segment / thin-segment analysis, which is the design's Q5 motivation.
- The Q5 factorial (N x train-ratio surface on coil2000) has never been run.

### 4.7 Failure paths never exercised

- No test of what happens when the box runs out of VRAM mid-arm.
- No test of a partial artifact transfer (a truncated payload).
- No test of resume-after-failure; every run starts from scratch.
- The watchdog has fired only against a manually-created leak, not a naturally occurring one.

---

## 5. Technical facts a follow-up run must inherit

Hard constraints — violating any of these caused a real failure:

1. **`vastai execute` is not a shell** (only `ls`/`rm`/`du`). Use `--onstart <file>`.
2. **Container log lines cap at exactly 500 characters.** Chunk payloads at 440 and reassemble.
3. **Never pass `--ssh --direct`** — it strands the instance at `intended_status: stopped`.
4. **`--tail` with a huge value silently returns nothing**, which is indistinguishable from
   "not finished" and caused a 64-minute billing leak. Fetch small, fetch early, warn on empties.
5. **The licence name is `tabpfn-3-license-v1.0`** — an HF-repo-derived identifier, not a version.
6. **Never `export VAST_API_KEY` or set a stale `TABPFN_TOKEN`** — the 2FA session binds to the
   key file, and an exported value overrides it and 401s.
7. **Secrets are mode-600 files under `~/.config`** (`~/.config/tfm/keys.env`,
   `~/.config/vastai/vast_api_key`). One rule, no keychain, no Passwords.app.
8. **Destroy with `-y` on every exit path**, and never leave an instance in any state but
   `offline` — storage bills per second for the instance's entire existence, including `stopped`.
9. **Image must match host CUDA** (see the matrix in the runbook §C). The image was *not* the
   variable in the provisioning failures — the host was.
10. **Provisioning failures are host-specific.** Record `machine_id`/`host_id` and skip failed hosts.

---

## 6. Metadata defects — do not trust these fields

These were found while writing this document. They do not change the results, but they constrain
what the metadata can be used for.

1. **`arms` is not a per-run record.** All ten run JSONs record `arms: A_raw,B_in_domain`,
   including runs where only a subset executed and runs predating the flag. It equals neither the
   script default (4 arms) nor the artefact evidence (A/B/E/F). **Determine what ran from the
   artifacts, never from this field.**
2. **`bootstrap_rc` is 0 on every run where it was recorded — including runs that failed at the
   preflight gate** (`PREFLIGHT FAILED (rc=1)` in the log). The EXIT-trap completion marker exits 0
   on all paths, so **`rc=0` does not mean success**. Judge success from the artifact markers and
   `ROC=` lines.
3. **The run ledger could misalign.** Adding fields to the run record silently shifted every column
   against the older header; it once reported `$1789231403` for a five-minute run. Now header-checked
   and quarantined on mismatch. The per-run JSONs are the source of truth; the ledger is derived.
4. **Arm B returns no per-row predictions.** The box's payload carries `pilot_metrics.parquet` and
   `meta.json`; per-arm predictions are `.npy` (gitignored) and are not in the payload. So B's
   numbers can be read but not recomputed, and the paired test cannot be run on them.
5. **`context_samples: 64` is recorded but used by neither arm.** `A_raw` fits on all 2,000 rows.
   The recorded config overstates what arm B used; the effective settings are in the results
   report §5d.4.

---

## 7. Test-design template for the next run

Before spending, fix these explicitly — each corresponds to a gap in §4:

| Decision | Why it must be stated up front |
| --- | --- |
| Question (Q0 in-domain, or Q4 transfer?) | Determines the arm set; the current result only answers Q0 |
| Arm set | C/D are required for any transfer claim |
| Rung (R1/R2/R3) and train/test sizes | Sets the noise floor and the cost |
| Config(s) | One config cannot distinguish "no effect" from "lever too small" |
| Seed policy (multi-seed? folds?) | Without it the delta has no distribution |
| Decision rule | The design's R3 gate is the existing rule — state it, then apply it |
| Metric set, including calibration | Probabilities matter downstream |
| Artifact list (must include per-arm predictions) | Otherwise the result is unverifiable |
| Budget ceiling and abort conditions | Hard stop, with the watchdog as backstop |

**Pre-flight checklist** (all of these have failed at least once):

1. Offer query returns at least one acceptable host at the budget.
2. `keys.sh licence` reports the licence accepted with the current token.
3. The mock run passes end to end with zero spend.
4. The image matches the candidate host's CUDA.
5. The ledger and per-run JSON are writable and the header matches.
6. A teardown path exists for every exit (trap + watchdog + explicit destroy).

---

## 8. Cost summary

| Item | Amount |
| --- | --- |
| Total GPU spend to date (10 instances) | **$0.3382** |
| Spend on runs that produced usable output | ~$0.18 |
| Spend on failures, leaks and provisioning stalls | ~$0.16 |
| Credit remaining | ~$9.66 of $10 |

Reference: the design's budget assumed **$0** for R1 (Colab T4). Colab's T4 was returning 503, so
R1 ran on the paid path instead. Any future plan that budgets R1/R2 at $0 should not assume Colab.

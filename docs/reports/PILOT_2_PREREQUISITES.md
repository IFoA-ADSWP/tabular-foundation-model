# Pilot 2 — Prerequisites Checklist

> Date: 2026-09-12 | Status: **IN PROGRESS (4 of 8 done)**
> Design: `PILOT_2_DESIGN.md` §7 (this is that section, expanded and tracked)
> Related: #22 | No paid run may proceed until the Gate in this file is green.

---

## How to use this

Each prerequisite has an **acceptance test** — a command that must pass, with its output recorded
in the Evidence column. A prerequisite is DONE only when its acceptance test passes on the branch
that will run Pilot 2. Status values: `TODO`, `IN PROGRESS`, `DONE`, `N/A`.

The runner-side acceptance tests live in `tests/test_pilot2_prerequisites.py`:

```bash
python -m pytest tests/test_pilot2_prerequisites.py -v
```

---

## Status summary

| ID | Prerequisite | Status | Blocks |
| --- | --- | --- | --- |
| PR-1 | Run manifest (audit record) | IN PROGRESS — runner side done, end-to-end unverified | all |
| PR-2 | Per-arm predictions returned from the box | **DONE** — verified end-to-end locally at $0 with both real scripts; box execution is PR-8 | Stage 1 |
| PR-3 | Fine-tuned weights saved + hashed | IN PROGRESS — code path done, live save/reload outstanding | Stage 1 |
| PR-4 | Matched-inference-context assertion | **DONE** | Stage 1 |
| PR-5 | LODO exclusion assertion | **DONE** | Stage 2 |
| PR-6 | Dataset + split fingerprints | **DONE** | all |
| PR-7 | Epoch ladder as a first-class factor | **DONE** | Stage 1 |
| PR-8 | Mock-verified end-to-end at $0 | **DONE** — full mock run passes in ~3.5s, teardown asserted | any spend |
| PR-9 | Pre-fetch the gated weights (move the licence gate off the run path) | IN PROGRESS — logic + wiring verified, live cold→warm download outstanding | any spend |

Suite status at this revision: `94 passed, 1 failed` across `tests/` — the failure is the
pre-existing `tests/test_frontier_cli.py::test_reconstruct_pp` float32/float64 assertion,
unrelated to these changes. Pilot 2 additions: 25 tests in `test_pilot2_prerequisites.py`,
17 in `test_pilot2_artifact_roundtrip.py`, 4 in `test_pilot2_mock_run.py`.

---

## PR-1 — Run manifest

**Why.** R1's records could not answer basic questions about its own runs: which arms executed, what
config each arm actually used, which data version was loaded, what the split was, what anything cost
per arm, or whether the decision rule was evaluated. Twelve capture gaps are catalogued in
`NEXT_STAGE_PROPOSAL.md` §4.1.

**Required.** One immutable JSON per invocation, plus a per-arm record, containing: run id and
status; git SHA/branch/dirty; host and environment (GPU model, VRAM, driver, CUDA); dataset
fingerprints; split policy, seed, fold, sizes, class counts and index hashes; pool contents for
transfer runs; **per-arm effective configuration** with passed-vs-defaulted provenance; per-arm
metrics; prediction hashes; model references; gate rule and outcome.

**Acceptance test.** A third party can recompute every reported metric from the returned
predictions to within 1e-9, and identify the exact data version and split from the manifest alone.

**Status.** Runner side implemented: `write_run_manifest()` writes `manifest_<run_id>.json`
per invocation (git/host/env/config/seeds/folds/rung/dataset fingerprints/pool), and every arm
writes `meta.json` with dataset fingerprint, split fingerprint, `predictions_sha256`,
`effective_config` and `inference_context`. **Not yet verified end-to-end**, because it depends on
PR-2 returning the predictions to recompute from. Cost per arm is still not captured — it belongs
with the runner-level cost accounting in `vast_run.sh`.

**Reproducibility inputs added later** (an audit of "could someone re-run this and get the same
answer" found four that were implicit or absent):

| Input | Was | Now |
| --- | --- | --- |
| Data source | `/main/` hardcoded — a **moving branch**; a hash tells you a file changed, not how to get the original back | recorded per dataset (`source_url`, `source_ref`, `source_ref_is_pinned`), and pinnable with `TFM_DATA_REF=<sha>` |
| Box dependencies | `pip install --upgrade` with **sklearn and pandas unpinned** — both change *results*, not just logs | `tabpfn` and `scikit-learn` pinned to what the pilot ran; `pandas`/`pyarrow`/`catboost` bounded; `--upgrade` removed; all four recorded per run |
| Weights | `checkpoints` recorded the **filename** — an assertion, not proof of which bytes ran | `fetch_weights.py` computes the sha256 and it reaches the manifest via `TFM_WEIGHTS_MANIFEST` |
| Container image | chosen at run time from host CUDA, recorded only in the runner's own JSON | interpolated into the onstart environment and recorded in the manifest, with a shared `run_stamp` joining the box record to the runner's cost record |

Also recorded now: the **actual estimator class per arm**. Arm F silently falls back to
`RandomForestClassifier` when catboost is missing, and the row still said `F_catboost`;
the substitution is now recorded *and* printed loudly. (Checked: catboost 1.2.10 was present
on both the box and locally, so the pilot's F arm was genuine — but the hazard is closed.)

**Two bugs this work surfaced**, both caught by the mock run: `RUN_STAMP` was defined inside a
function, so the onstart builder hit it unset and `set -u` aborted the run; and the ledger heredoc
hardcoded `outputs/gpu-pilot` **inside** the Python, so `VAST_OUTDIR` never reached the run record
or the ledger — meaning every earlier mock run had been writing into the working tree. Now verified
isolated: 13 run records before a mock run, 13 after.

**Evidence.** `tests/test_pilot2_prerequisites.py::test_pr1_git_and_host_info_present` passes, plus
eight provenance tests (`test_pf_data_source_url_honours_a_pinned_ref`,
`test_pf_fingerprint_records_where_the_bytes_came_from`,
`test_pf_versions_record_the_packages_that_change_results`,
`test_weights_provenance_*`, `test_container_provenance_*`,
`test_per_arm_record_carries_the_new_provenance`).

---

## PR-2 — Per-arm predictions returned from the box

**Why.** R1's arm B returned metrics but no predictions, so its headline number can be read but not
recomputed or paired-tested. The transport exists and is verified — chunked 440-character tagged
lines because the container log caps every line at exactly 500 characters — it is simply not applied
to predictions.

**Required.** Every arm's prediction vector included in the artifact payload and reassembled
client-side, verified by hash.

**Acceptance test.** A round-trip reproduces each arm's `predictions.npy` with a matching sha256, for
a payload at least as large as the real one (~120 KB uncompressed for 4 arms x 4 datasets x 1,000
rows).

**Status.** **DONE.** The transport is now three scripts, each independently testable:
`emit_artifacts.sh` (box side) declares the payload's byte size, sha256, line count and file
count; `verify_artifacts.py` (receiving side) refuses a short read, checks the archive sha256,
unpacks, and then verifies **every arm's predictions against the `predictions_sha256` its own
`meta.json` recorded**.

Two subtleties that would have made a naive check useless:

- `meta.json` records the hash of the **array's bytes** (`array.tobytes()`), not of the `.npy`
  container, so hashing the file directly always mismatches. `npy_data_sha256` parses the `.npy`
  header and hashes only the data payload — pure stdlib, so no numpy is needed on the receiving side.
- The container log caps lines at 500 characters, so the payload is folded at 440 and reassembled.
  A 3-seed x 5-fold run is ~3,800 payload lines, which is why the runner's log window was raised
  from 5,000 to 20,000 — bounded well below the 200,000 value that once returned nothing and caused
  a billing leak.

**Two real bugs this work found**, both previously invisible:

1. **`meta.json` was never returned from the box.** The payload glob was `*/meta.json`, but the
   runner writes `<dataset>/<arm>/meta.json` — one level deeper. The glob matched nothing, so
   per-run metadata (and with it the config/provenance the manifest depends on) never came back.
   Now a recursive `find`.
2. **`grep -c` on an empty file.** BSD `grep -c` exits 1 when nothing matches, so the
   `|| echo 0` fallback *also* fired and the file count came out as two lines (`0\n0`). Replaced
   with a portable count, plus an explicit "nothing to send" path so the receiver can distinguish
   "the box produced no outputs" from "the transfer was truncated".

**Evidence.** `tests/test_pilot2_artifact_roundtrip.py` — 17 tests, including an **end-to-end
round trip using the real emitter and the real verifier** (193 payload lines, 9 files, 63 KB
compressed), asserting byte-identical predictions and matching hashes; a truncation case that must
report a short read rather than unpack; an empty-tree case that must declare zero; tamper detection
on both the archive and the predictions; and a regression test for the `INFO` parsing bug found
during development. Local suite: `90 passed, 1 failed` (the pre-existing `test_reconstruct_pp`).

**Residual.** The box-side script has been exercised on macOS/bash rather than Linux, so the
environment difference (GNU vs BSD coreutils) is handled explicitly — `sha256sum` with a
`shasum -a 256` fallback — but the first real box execution happens under PR-8.

---

## PR-3 — Fine-tuned weights saved and hashed

**Why.** R1 produced four fine-tuned models that existed only in memory: no artefact, no hash, no way
to reload or audit. `tabpfn` 8.5.0 exports `save_fitted_tabpfn_model` / `load_fitted_tabpfn_model`.

**Required.** Persist the fine-tuned model where size permits, record its sha256, and verify it
reloads and reproduces the same predictions. Where saving is not viable, record the reason and the
exact reproduction command.

**Acceptance test.** Save, reload, predict, and confirm identical predictions (tolerance stated) and
a recorded hash.

**Status.** IN PROGRESS — `save_model_artifact()` is implemented behind `--save-models`, hashes the
written file, and **records any failure rather than raising or staying silent** (the failure mode
that let R1's arm B report numbers for a model that may never have taken a gradient step). A live
save/reload on a GPU box is outstanding, so the "reproduces the same predictions" half of the
acceptance test has not run.

**Evidence.** Import path verified present in `tabpfn==8.5.0` (the box version);
`save_fitted_tabpfn_model` exported from `tabpfn/__init__.py`.

---

## PR-4 — Matched-inference-context assertion

**Why.** This is the defect that made the historic transfer verdict unusable: the fine-tuned arm was
evaluated with a subsampled context (64 then 128 rows) while the raw arm used the full training
split. The modern shipped trainer refits inference on the full training split, so parity holds *by
construction* — but the lesson is that such claims must be **recorded and asserted**, not assumed.

**Required.** Record the effective inference context (row count) per arm, and make the comparison
**refuse to report a delta** if the two TabPFN arms differ.

**Acceptance test.** The assertion fires on a deliberate mismatch and passes on a real run.

**Status.** **DONE.** `inference_context_rows()` returns the row count and the mechanism for each
arm; `assert_matched_context()` raises `MATCHED-CONTEXT VIOLATION` when contexts differ, and is
called **before any arm runs** in `run_single_dataset`, so a mismatch aborts rather than producing a
comparable-looking number.

**Evidence.** Three passing tests:
`test_pr4_matched_context_passes_when_equal`, `test_pr4_matched_context_raises_on_mismatch`,
`test_pr4_context_passes_without_ft_arm`.

---

## PR-5 — LODO exclusion assertion

**Why.** A transfer result is only meaningful if the target dataset was provably absent from the pool
that trained the model. This is the central integrity property of the design, and it must be checked
in code rather than by convention.

**Required.** A pool-building function that takes the target, excludes it, and asserts the exclusion
by name and by content hash before any fine-tuning starts. Overlap is a hard error.

**Acceptance test.** The assertion raises when the target is in the pool, and passes on a clean pool.

**Status.** **DONE.** `build_pool()` asserts absence by name and checks for a content-hash collision
(the target duplicated under another filename), records `out_of_pool_asserted: True`, and is wired to
the CLI (`--pool` with `--assert-lodo-for`). It is not yet called by a transfer arm, because arms C/D
do not exist yet — this is the guard they will run under.

**Evidence.** Three passing tests: `test_pr5_pool_excludes_target`,
`test_pr5_pool_raises_if_target_in_pool`, `test_pr5_pool_raises_on_content_hash_collision`.

---

## PR-6 — Dataset and split fingerprints

**Why.** R1 recorded neither a data version nor a split, so a result cannot be tied to the data that
produced it and the split cannot be reproduced.

**Required.** Per dataset: file sha256, row/column counts, column list, target, positive rate. Per
split: policy, seed, fold, sizes, per-class counts, index hashes, and a flag confirming test rows
were never seen during fitting.

**Acceptance test.** Re-running the split from the recorded indices reproduces the identical test
set; the dataset hash matches on a second read.

**Status.** **DONE.** `dataset_fingerprint()` records sha256 + shape + column list + target +
positive rate; `load_dataset()` additionally reports whether the unstratified row cap was applied
(the R1 limitation, now visible rather than hidden); `make_split()` records policy, seed, fold, sizes,
class counts, both index hashes and `test_rows_excluded_from_fit`. The non-stratified row cap is a
recorded caveat, not a fixed behaviour.

**Evidence.** Six passing tests, including fold partitioning without overlap
(`test_pf_folds_partition_without_overlap`) and split reproducibility by seed
(`test_pf_split_index_hash_is_reproducible`, `test_pf_split_changes_with_seed`).

---

## PR-7 — Epoch ladder as a first-class factor

**Why.** The library default is `epochs=30`. R1 ran 3, sourced from `max_finetune_steps` — a field
that was never a TabPFN parameter — and the historic work ran 3-5 gradient steps. The mechanism has
never been exercised above roughly a tenth of its default budget, and the old config made the budget
hard to see.

**Required.** `epochs` explicit, first-class and recorded; support {3, 10, 30} without code change.

**Acceptance test.** Runs at 3 / 10 / 30 each record the requested value; the fine-tune demonstrably
does more work as the value rises.

**Status.** **DONE** for the config and recording half. `--epochs` is a CLI flag (default 3 =
R1 parity), `epochs` appears in `effective_config()["passed_params"]`, and the ladder needs no code
change. The **"demonstrably does more work"** half — run-time scaling with the epoch count — needs a
GPU run and is outstanding.

**Evidence.** Four passing tests: `test_pr7_epochs_is_the_reported_budget`,
`test_pr7_legacy_context_samples_is_flagged_unused`, `test_pr7_raw_arm_reports_no_epochs`,
`test_pr7_default_is_r1_parity_and_ladder_reachable`.

---

## PR-8 — Mock-verified end-to-end at $0

**Why.** R1 spent roughly half its budget on failures a zero-cost mock run would have caught: a
transport that could not work, a licence gate, and provisioning stalls.

**Required.** A full run of the runner's own path (create → onstart → poll → artifact return →
destroy) against `scripts/gpu_helpers/mock_vastai.sh`, with the new manifest and per-arm predictions,
at $0, asserting the teardown fired.

**Acceptance test.** Mock run completes with the manifest and all predictions restored client-side,
and the mock confirms the teardown was called.

**Status.** **DONE.** A full run of the runner's own path — create → onstart → poll → artifact
return → destroy — now passes against the mock in ~3.5 s at $0, and three properties are asserted
because each has failed before:

1. **The run completes AND tears down.** The mock *records* `destroy instance -y` rather than just
   printing it; a mock that only prints cannot prove the trap fired.
2. **Artifacts come back and verify** — the real `verify_artifacts.py` confirms every arm's
   predictions against the hash its `meta.json` recorded (`verified=3 mismatched=0 missing=0`).
3. **The mock cannot drift from reality.** Its `logs` branch now calls the **real**
   `emit_artifacts.sh` instead of emitting a private format. The previous mock invented
   `__ARTIFACTS_B64_BEGIN__`/`END__` markers the verifier does not look for — so it validated a
   wire format that no longer existed, which is exactly how a transport that cannot work gets
   signed off. That drift is now structurally impossible.

**A third real bug this found:** `manifest_<run_id>.json` was **not in the payload**, so the audit
record PR-1 exists to produce was written on the box and never returned. Fixed by including
top-level run-level JSON alongside the per-run `meta.json`.

Also added: `VAST_OUTDIR`, so a mock/dry run can be isolated instead of writing into the working
tree — the runner previously hardcoded `$REPO_DIR/outputs/gpu-pilot` in five places.

**Evidence.** `tests/test_pilot2_mock_run.py` — 4 tests: the full path (create recorded, teardown
recorded, artifacts verified, manifest returned); that the verification result is surfaced rather
than restored silently; the interlock that refuses to run when a *different* `vastai` resolves
(this misfire once created three real billing instances); and that the mock still models the real
`execute` constraint (only `ls`/`rm`/`du`).

---

## PR-9 — Pre-fetch the gated weights

**Why.** TabPFN's licence check sits inside the weight-download path and fires **only on a cache
miss**: when the checkpoint already exists, the library returns early and never calls
`ensure_license_accepted`. Consequences: fine-tuning needs no API key at all; a warm cache needs no
token; and an **ephemeral container takes the cache-miss path on every run**, so the gate fires every
run. Fetching the weights as one explicit early step moves the token's use to a single, loud, early
point instead of letting it surface inside the first arm's `fit()`, and it lets the run record the
resolved checkpoint's hash — the weights ID the runbook requires, recorded rather than inferred.

**Required.** A step that resolves the library's own cache directory, fetches the gated checkpoint
explicitly if absent, records path/size/sha256, and lets the bootstrap **skip the licence preflight
when the weights are already cached**.

**Acceptance test.** On a cold cache the step reports `cached: false` and exits non-zero; on a warm
cache it reports `cached: true`, `licence_gate_will_fire: false` and exit 0; and the bootstrap's
preflight is skipped in that case.

**Status.** IN PROGRESS — implemented as `scripts/gpu_helpers/fetch_weights.py` and wired into
`bootstrap_pilot.sh` as step 3a, with the preflight at 3b now conditional. Both halves are verified
locally: the script's resolution path runs on this machine (resolving the cache dir via the library's
own `get_cache_dir()`, and correctly falling back for repo/filename because the local tabpfn is 6.4.1
and lacks `get_classifier_v3`), and the shell's marker/JSON/cached parsing was exercised against all
five cases (cached, downloaded, missing, empty output, unparseable). **Design note:** the preflight
remains authoritative — a failed fetch falls through to it rather than aborting, because the library's
own path may succeed where ours did not. Only a positive `cached` result changes control flow.
Outstanding: a real cold→warm download on a box, confirming the gate genuinely does not fire.

**Evidence.** Five passing tests (`test_pr9_*`); `bash -n` and `shellcheck -S error` clean on both
scripts; a local `--check-only` run reported `cached: false` / `licence_gate_will_fire: true` on this
machine's cold cache.

---

## Gate — no spend until all of these hold

- [ ] PR-1 through PR-9 are `DONE`, each with a recorded evidence artefact.
- [ ] The fairness checklist in `PILOT_2_DESIGN.md` §8 is satisfied for the specific rung being run.
- [ ] The decision rule and outcome mapping for that rung are written down **before** the run.
- [ ] The run's cost ceiling is set, and per-run approval has been given explicitly for that run.

---

## Progress log

| Date | Change | Commit |
| --- | --- | --- |
| 2026-09-12 | Checklist created from `PILOT_2_DESIGN.md` §7 | — |
| 2026-09-12 | Runner rewritten to Pilot 2 schema v2: manifest, fingerprints, matched-context assertion, LODO assertion, epoch ladder, model hashing, log loss + ECE. PR-4/5/6/7 DONE; PR-1/3 IN PROGRESS; PR-2/8 TODO. 20 new acceptance tests, suite at 68 passed / 1 pre-existing failure. | — |
| 2026-09-12 | PR-9 added and implemented: `scripts/gpu_helpers/fetch_weights.py` + bootstrap step 3a, with the licence preflight at 3b now skipped when the weights are already cached. 5 more tests (25 total in this file; full suite 73 passed / 1 pre-existing failure). `bash -n` and `shellcheck -S error` clean. | — |
| 2026-09-12 | PR-2 done: `emit_artifacts.sh` + `verify_artifacts.py`, wired into the bootstrap, log window 5000 → 20000. Payload now carries every arm's predictions and is hash-verified on return. **Found and fixed two pre-existing bugs**: `meta.json` was never returned (glob one level too shallow), and BSD `grep -c` produced a two-line file count. 17 new tests incl. a real emit→verify round trip; full suite 90 passed / 1 pre-existing failure. | — |
| 2026-09-12 | PR-8 done: mock run of the full runner path passes in ~3.5s at $0, asserting create, teardown, artifact verification and manifest return. Mock now delegates to the real emitter so it cannot validate a wire format that no longer exists. **Found and fixed a third bug**: `manifest_<run_id>.json` was not in the payload. Added `VAST_OUTDIR` for isolation. 4 new tests; full suite 94 passed / 1 pre-existing failure. | — |

# Review: PR #187 — TabPFN 3.5 version-drift re-test, regression/count tier

**PR:** https://github.com/IFoA-ADSWP/tabular-foundation-model/pull/187
**Author:** Mako-120
**Issue:** #186
**Review date:** 2026-09-20
**Reviewer:** scotthawes (existing APPROVED review, 2026-09-17); re-review by Hermes for documentation.

## Verdict

**Approve with nits.** Substantive content is correct, well-documented, and the two harness fixes
(auth + retry coverage) are real defects that would have silently corrupted the re-test. The two
genuine evidence gaps (Δ/SE not a paired test; manifest payload not hashed) are both disclosed and
correctly scoped as follow-ups, the second already flagged in the existing review.

## Summary of the PR

First live execution of the §15 Version-Drift Re-Test Policy, triggered by the TabPFN 3.5 release.
Re-tests the four regression/count datasets where v3_default sat off the parsimony frontier:
freMTPL2freq, spanish_motor_freq, bemtl97_amount, spanish_motor_severity.

Result: all four improved; one verdict change (spanish_motor_freq onto the frontier, 5/12 → 4/12);
falsifies §14.9's "tree-extractable only" reading for that dataset. The pricing-at-scale verdict
narrows but does not reverse.

## What is strong

1. §16 addendum is the right shape for a drift re-test: provenance table (model, client version,
   server default, caps, folds/seed/split, script git SHA), per-fold values listed, paired t-tests
   vs lgbm, the one verdict change called out explicitly, scikit-learn confound disclosed before
   citing, two harness defects named and fixed, clear "what's still open" close.

2. The result is honest: all four improved, but only one verdict change; freMTPL2freq −22.3% but
   still paired-significant loss; bemtl97_amount and spanish_motor_severity remain losses. "Narrows
   but does not reverse" is the right read.

3. Two harness fixes are genuine defects:
   - Auth (TABPFN_TOKEN after 0.3.3 — baselines run, TabPFN folds silently fail).
   - Retry loop covering only fit, not predict (discarded four completed freMTPL2freq folds, ~59 min).
   Both fixed and re-run; the re-run reproduced folds 0–3 to the digit.

4. src/model_version.py resolves model_path from TABPFN_MODEL_PATH, defaulting to v3_default, so an
   unconfigured run reproduces the baseline rather than silently scoring v3.5. Verified: defaults to
   v3_default, env→.env→baseline order.

5. src/api_key.py exports both TABPFN_API_KEY and TABPFN_TOKEN from one resolved key. Correct:
   keeps 0.3.3 baseline re-runs working while fixing the 0.6.0 auth gap. Verified: both names
   exported from one resolved key.

6. Prediction filenames now carry model_path (<dataset>__seed<seed>__<model_path>.npz), so a re-test
   preserves its predecessor. The .gitignore exemption (!scripts/eval/insurance_benchmark_v1/predictions/*.npz)
   is the right mechanism.

7. Manifests record model_version, tabpfn_client_version, script_git_sha, dataset/seed/split —
   provenance is what a drift re-test needs.

## Nits (not blockers)

1. §16.2 Δ/SE is a two-sample comparison, not a paired test. The committed v3 frontier CSVs carry
   only mean±SE, so the paired version can't be done here — but PR #152 (open) backfills v3 per-fold
   predictions for all four datasets. §16.6 discloses this and names the follow-up. Not a blocker, but
   worth confirming the disclosure is sufficient for the citation chain.

2. scikit-learn drift 1.6.1 → 1.9.0. §16.4 discloses it, bounds it with a per-method reproduction table
   (lgbm/cat/xgb bit-exact; ols drifts up to +5.63%; rf/poissonglm/tweedieglm <0.2%), and argues the
   conclusions survive. The argument is sound for the TabPFN-vs-lgbm paired tests. But the ols rows in
   this re-test are explicitly not comparable to v3. A reviewer citing §16 should treat ols as unreliable
   here. Verified: requirements.lock pins scikit-learn==1.6.1 (the lock is correct; the re-test just
   didn't use the locked env).

3. Single seed (42), single split, no v3.5-fast_default arm. Stated as a limit in §16.6. Fine for a
   first re-test; don't treat as settled.

4. The DIRTY merge state (GitHub mergeStateStatus=DIRTY, mergeable=CONFLICTING). This is a GitHub UI
   artifact around the force-pushed branch history, not a content problem — but it does mean the PR
   cannot be merged via the UI until the force-push history is resolved or the branch is rebased. Worth
   confirming before merge.

5. Overlap with PR #204 (hygiene): one trivial .gitignore conflict (same exemption line, different
   surrounding comments — merge order doesn't matter). Five "both added" (AA) file conflicts
   (run_pilot.py, gpu-pilot/README.md, bootstrap_pilot.sh, vast_run.sh, finetune/pilot/pilot_metrics.parquet)
   are merge-order decisions, not content defects in either PR. If #204 lands first, PR #187 needs a
   rebase; if #187 lands first, #204's versions of those files need reconciling on top.

## Suggested next action

Resolve the force-push DIRTY state on the PR branch (rebase onto current main if needed), then merge.
If #204 lands first, rebase PR #187 on top and resolve the five AA file conflicts in the intended merge
order. The one content nit worth a second look is whether §16.2's Δ/SE disclosure is sufficient — if in
doubt, add one sentence to §16.2 naming PR #152 explicitly as the follow-up that will convert Δ/SE to
a paired test, so a reader doesn't have to hunt for it.

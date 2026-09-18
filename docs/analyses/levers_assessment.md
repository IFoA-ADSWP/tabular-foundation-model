# TabPFN levers assessment — fine-tuning, HPO, ensembling (issue #54)

Status: assessment / scoping — no new runs performed. 2026-08-04.

## Summary

The "are we limiting TabPFN?" levers were assessed against the 12-dataset frontier (master report §14). Verdict: two of three levers are already closed by existing evidence; the remaining one (fine-tuned TabPFN inside the harness) has low expected value outside small-data/lapse regimes. The issue's hypothesis — levers narrow but do not close the at-scale gap — is kept, sharpened.

## Lever assessment

| Lever | Evidence already in repo | Feasibility on this stack | Overturn at-scale verdict? | Recommendation | Effort |
|---|---|---|---|---|---|
| Fine-tuned TabPFN on the frontier | §5.1: fine-tune degraded 3/4 targets at every step/context (aggregate ROC AUC −0.0752); §5.2 coil2000 small-finetune max gain +0.0047; §5.3: "does not change the do-not-deploy-severity verdict". Never ran inside the benchmark harness; classification-only, 2,500-row subsets, single seed (§7.2) | Local only — hosted v3 API has no fine-tune endpoint (inference-only client). Local fine-tune on M1: CPU > MPS. Save/load plumbing exists (`scripts/legacy_finetuning/`) | Conditional: unlikely. Only freMTPL2freq_binary improved (+0.05); the decisive losses (severity regressions) are where the prior adds nothing (§14.10) | Run-truncated — harness-arm on the one target that improved plus one severity regression | 2–3 sessions |
| HPO'd TabPFN | §12.3: TabPFN ran at its floor (`TabPFNClassifier(random_state=0)`, no HPO) — the one untested accuracy lever (§8(a)); §13/§14.2: ensemble-size dimension already closed (n_estimators=8 = server default, 1 worse); §13.5: don't re-chase the config-lite arm | Hosted client exposes only `model_path`, `random_state`, `n_estimators` (API cap 8) — no LR/epochs/temperature. HPO surface is empty on hosted; local HPO infeasible at ≥53.5K rows on M1 | No — nothing tunable remains that the sweep didn't close | Skip (hosted); defer local HPO to small-data niche only | 0–1 (document-closed) |
| Context-window ensembling (1M rows) | §12.1 model-version correction: v3 supports 1M rows/200M cells; all 12 frontier datasets already ran full-size through hosted v3 (incl. 678K-row freMTPL2freq §14.8, 184K norauto) — the lever is already exercised; server-side mechanism (subsampling/ensembling) not exposed | Nothing to pull client-side; hosted already at full context. Local chunked-ensemble = the §13.5 config-lite arm already closed | No — the size pattern is empirical and mechanism-independent (§12.1); the frontier is the 1M-row test | Skip — closed by existing evidence | 0 |

## Plumbing and API tunability

The codebase has a complete local fine-tune pipeline under `scripts/legacy_finetuning/`: `finetune_pilot.py`, `run_domain_finetune_stage_a.py`, `run_small_finetune_classifier_trial.py`, `run_finetuned_tabpfn_regression_benchmark.py`, a save/load validator (`check_saved_finetune_classifier_model.py`), and a regressor stability gate (`evaluate_regressor_stability_gate.py`, exposes `finetune_steps_executed` / non-finite counters). It targets the local upstream TabPFN source tree, not `tabpfn_client`. The hosted v3 API is not tunable beyond `model_path`, `random_state`, `n_estimators` (cap 8, equals default), and `balance_probabilities` (actively harmful, §11.4) — no fine-tune endpoint, no HPO knobs. So HPO is empty on the hosted surface and fine-tuning requires local inference on fine-tuned checkpoints.

## Hypothesis update

Keep, sharpened. "Levers narrow but do not close the at-scale gap" is confirmed by existing evidence — ensembling is closed (§13/§14.2), 1M context is closed (§12.1), HPO is empty on the hosted API, and fine-tuning degrades under every tested protocol (§5). The GLM-captured regime result (regime_characterization: linear floor within ~2% ⇒ no edge; calibration edge; §14.11 adds an AUC ranking edge in GLM-captured regimes; TabPFN wins only where the prior extracts linear-missed signal, e.g. Spanish lapse 0.7553 vs LR 0.684, §14.10) predicts exactly this: the at-scale gap is structural — tree-extractable signal plus GLM parsimony floor at ≥53.5K rows — not a configuration artifact. Sharpened form: on hosted v3 the only remaining untested lever is a fine-tuned TabPFN arm inside the harness (the §8 precondition), and its expected value is low outside small-data/lapse regimes.

## Proposed next steps (if approved)

- Fine-tuned harness arm, classification: local fine-tune (1 epoch, context 1024, CPU) via `scripts/legacy_finetuning/run_small_finetune_classifier_trial.py` on freMTPL2freq_binary (only improving target), then score on the benchmark's folds (seed 42, StratifiedKFold 5). Verify CLI flags before running.
- Fine-tuned arm, regression (decisive test): `run_finetuned_tabpfn_regression_benchmark.py` + `evaluate_regressor_stability_gate.py` on spanish_motor_severity (53.5K) — the off-frontier severity loss; report `finetune_steps_executed` and non-finite counters.
- HPO: document-as-closed addendum to §12.3 (hosted API surface); no run.
- Context/ensembling: document-as-closed addendum to §13/§12.1 (frontier already ran full-size); no run.
- Pins per §15 policy: tabpfn-client 0.3.3 in /tmp/tabarena/.venv-ta, model_path="v3_default", record installed version and diff `frontier_results_*.csv` (method, mean, se, n_params, on_frontier) against committed baselines before claiming any change.
- If fine-tuned arms show no beyond-SE improvement on both targets, close #54 with the hypothesis confirmed and no further runs.

## References
- Master report: docs/analyses/tabpfn_vs_gbdt_baselines_finetuning.md (§5, §8, §11.4, §12.1, §12.3, §13, §13.5, §14, §14.2, §14.8, §14.10, §15)
- docs/analyses/regime_characterization.md
- docs/archive/TABPFN_BENCHMARK_SUMMARY.md (Conclusion & adoption guidance)
- scripts/legacy_finetuning/ (fine-tune pipeline)
- Issue #54

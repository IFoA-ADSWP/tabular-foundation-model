# Task List

Tracked from GitHub issues. Updated manually.

| Status | # | Title | Assignee |
|--------|---|-------|----------|
| 🔲 | #186 | Version-drift re-test: TabPFN 3.5 on the v3_default underperformance cases — regression/count tier **done** (4/4 improved; `spanish_motor_freq` onto the frontier, falsifies §14.9's tree-only reading; off-frontier count 5/12 → 4/12; master report §16). Open: classification calibration tier (`ausprivauto0405`, `bemtl97`, `norauto`), `bemtl16` lift, `eudirectlapse`, and the §15.2 sweep refresh required before any `bemtl97` frontier claim | Mako-120 |
| 🔲 | #82 | B8 Exercise version-drift re-test policy (dry run) — **superseded by #186**, which executed §15 live after a real trigger fired; close once #186 lands | — |
| 🔲 | #125 | Fine-tuning negative-result audit — null-control Stage A harness (W1 confound) + power/dose/scale remediation; gates #85/#81 | — |
| ✅ | #— | Repository migrated to IFoA-ADSWP/tabular-foundation-model — full history, 123 issues+PRs (numbering preserved), wiki, collaborator access; open PR recreated as #124; old fork retained as read-only archive | scotthawes |
| 🔲 | #123 | Add insurance-native alternative metrics (Gamma/Tweedie deviance, MAE) with fold-level SEs to regression benchmarks — consumes #122 predictions; spec at `docs/analyses/altmetrics_rescore_spec.md` | — |
| 🔲 | #122 | Persist per-fold test predictions for retrospective re-scoring (`--save-predictions`) — spec at `docs/analyses/prediction_capture_rescore_spec.md` | — |
| 🔲 | #57 | Clean up main junk commits (f0bf230, 5264ec1) — blocked (needs main force-push decision) | — |
| ✅ | #56 | Merge PR #51 + post-merge verification — merged 2026-08-04 (31d40a5); registry check clean | scotthawes |
| ✅ | #55 | Version-drift re-test policy for the benchmark verdict — PR #62 | — |
| 🔲 | #54 | TabPFN levers in the parsimony framework — fine-tuning, HPO, ensembling — assessment shipped (PR #63), run decision pending | — |
| ✅ | #53 | Regime characterization — why does TabPFN win lapse at 53.5K but lose frequency/severity? — PR #61 | — |
| ✅ | #52 | Conclusion & adoption guidance for the TabPFN benchmark — PR #61 | — |
| ✅ | #35 | Pipeline for Insurance/Actuarial Predictions — 5/5 criteria done (#47–#50 + #46 generic CLI) | — |
| ✅ | #46 | Pipeline: CLI entrypoint (dataset path + target column) — PR #65 | — |
| 🔲 | #29 | Funding Request #1 | Cillian-Williamson |
| 🔲 | #28 | Funding Request #2 | Cillian-Williamson |
| ✅ | #27 | Review TabArena (frontier benchmark D1–D5 + v1-suite + regression Phase 2) — MERGED to main via PR #51; follow-ups #52–#57. AUC/Brier rescore addendum implemented 2026-08-06 (spec 4e7912c, code + §14.11 9037b26) | scotthawes |
| ✅ | #27a | Spanish motor portfolio extension — MERGED via PR #51 (freq + severity frontiers, 5-fold lapse settlement: TabPFN AUC 0.7553 vs LGBM 0.7500) | scotthawes |
| ✅ | #26 | List Available Foundational Models — closed on GitHub | — |
| 🔲 | #25 | Draft Insurance/Actuarial Use Cases — task mapping exists in frontier spec §8 + report §14; formal use-case doc pending | — |
| ✅ | #24 | Dataset Selection CASDatasets — delivered via PR #51 (7 CASdatasets + Spanish motor, leak fixes) | Cillian-Williamson |
| 🔲 | #22 | Access to GPUs — blocked | — |
| ✅ | #20 | Add Max as collaborator — closed on GitHub | Karol-Gawlowski |

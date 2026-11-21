# Baseline conclusion — generated tables

> **Status:** current — generated 2026-11-21 (#631). Regenerate with
> `scripts/analyses/baseline_conclusion.py --out`; a test fails when this file drifts.

<!-- BEGIN GENERATED: baseline-conclusion -->

### Table 1 — frontier verdicts

| dataset | era | model | metric | value | best rival | Δ | interval (±SE) | decision | source |
|---|---|---|---|---:|---|---:|---:|---|---|
| `coil2000` | v3 | `v3_default` | log_loss | 0.20059 | `lr` 0.20552 | -0.00492 | 0.00221 | on frontier | `frontier_results_coil2000.csv` |
| `bemtl16` | v3 | `v3_default` | log_loss | 0.23803 | `lgbm` 0.23985 | -0.00182 | 0.00129 | on frontier | `frontier_results_bemtl16.csv` |
| `uslapseagent` | v3 | `v3_default` | log_loss | 0.24909 | `cat` 0.25286 | -0.00377 | 0.00518 | on frontier | `frontier_results_uslapseagent.csv` |
| `norauto` | v3 | `v3_default` | log_loss | 0.17619 | `lgbm` 0.17518 | +0.00101 | 0.00061 | on frontier | `frontier_results_norauto.csv` |
| `bemtl97` | v3 | `v3_default` | log_loss | 0.34279 | `lgbm` 0.34177 | +0.00101 | 0.00057 | on frontier | `frontier_results_bemtl97.csv` |
| `ausprivauto0405` | v3 | `v3_default` | log_loss | 0.24026 | `logisticglm` 0.23947 | +0.00080 | 0.00037 | off frontier | `frontier_results_ausprivauto0405.csv` |
| `ausautoBI8999` | v3 | `v3_default` | rmse | 0.96491 | `cat` 0.96883 | -0.00392 | 0.00868 | on frontier | `frontier_results_ausautoBI8999.csv` |
| `ausprivauto0405_vehvalue` | v3 | `v3_default` | rmse | 0.71162 | `lgbm` 0.71645 | -0.00483 | 0.01246 | on frontier | `frontier_results_ausprivauto0405_vehvalue.csv` |
| `bemtl97_amount` | v3 | `v3_default` | rmse | 0.72825 | `lgbm` 0.48499 | +0.24326 | 0.01057 | off frontier | `frontier_results_bemtl97_amount.csv` |
| `freMTPL2freq` | v3 | `v3_default` | poisson_deviance | 0.38770 | `lgbm` 0.29113 | +0.09657 | 0.00201 | off frontier | `frontier_results_freMTPL2freq.csv` |
| `spanish_motor_freq` | v3 | `v3_default` | poisson_deviance | 0.98764 | `lgbm` 0.89157 | +0.09606 | 0.01624 | off frontier | `frontier_results_spanish_motor_freq.csv` |
| `spanish_motor_severity` | v3 | `v3_default` | rmse | 1.88616 | `lgbm` 1.83719 | +0.04897 | 0.01165 | off frontier | `frontier_results_spanish_motor_severity.csv` |

### Table 2 — checks run 2026-11-21

| check | dataset | contrast | metric | Δ | interval | decision | source |
|---|---|---|---|---:|---|---|---|
| exposure-aware GLM | `ausprivauto0405` | one-hot LR + log(exposure) | log loss | -0.00037 | p=0.058 | model ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `ausprivauto0405` | one-hot LR + log(exposure) | log loss | +0.00173 | p=0.000 | GLM ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `bemtl16` | one-hot LR + log(exposure) | log loss | -0.01356 | p=0.000 | model ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `bemtl16` | one-hot LR + log(exposure) | log loss | -0.01222 | p=0.000 | model ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `bemtl97` | one-hot LR + log(exposure) | log loss | -0.00166 | p=0.000 | model ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `bemtl97` | one-hot LR + log(exposure) | log loss | +0.00069 | p=0.039 | GLM ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `norauto` | one-hot LR + log(exposure) | log loss | +0.00014 | p=0.130 | GLM ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `norauto` | one-hot LR + log(exposure) | log loss | +0.00186 | p=0.000 | GLM ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `uslapseagent` | one-hot LR + log(exposure) | log loss | -0.02596 | p=0.000 | model ahead | `exposure_aware_glm_followup.csv` |
| exposure-aware GLM | `uslapseagent` | one-hot LR + log(exposure) | log loss | -0.02071 | p=0.000 | model ahead | `exposure_aware_glm_followup.csv` |
| row curve | `freMTPL2freq` @ 1000 | `F_catboost` | poisson_deviance | 1049.32232 vs `M_intercept` | MDE 107.84528 | resolvable | `row_curve_stage1.csv` |
| row curve | `freMTPL2freq` @ 2000 | `F_catboost` | poisson_deviance | 433.11518 vs `M_intercept` | MDE 99.81345 | resolvable | `row_curve_stage1.csv` |
| row curve | `freMTPL2freq` @ 5000 | `F_catboost` | poisson_deviance | 43.49200 vs `M_intercept` | MDE 99.51764 | Inconclusive | `row_curve_stage1.csv` |
| row curve | `freMTPL2sev` @ 1000 | `E_glm` | rmse | 0.01673 vs `M_intercept` | MDE 0.01250 | resolvable | `row_curve_stage1.csv` |
| row curve | `freMTPL2sev` @ 2000 | `E_glm` | rmse | 0.00299 vs `M_intercept` | MDE 0.01243 | Inconclusive | `row_curve_stage1.csv` |
| row curve | `freMTPL2sev` @ 5000 | `F_catboost` | rmse | 0.00338 vs `E_glm` | MDE 0.01187 | Inconclusive | `row_curve_stage1.csv` |
| row curve | `spanish_motor_freq` @ 1000 | `E_glm` | poisson_deviance | 391.28308 vs `M_intercept` | MDE 275.72855 | resolvable | `row_curve_stage1.csv` |
| row curve | `spanish_motor_freq` @ 2000 | `M_intercept` | poisson_deviance | 710.22192 vs `E_glm` | MDE 335.25696 | resolvable | `row_curve_stage1.csv` |
| row curve | `spanish_motor_freq` @ 5000 | `F_catboost` | poisson_deviance | 476.75602 vs `E_glm` | MDE 179.51418 | resolvable | `row_curve_stage1.csv` |
| row curve | `spanish_motor_severity` @ 1000 | `F_catboost` | weighted_rmse | 0.03102 vs `E_glm` | MDE 0.01995 | resolvable | `row_curve_stage1.csv` |
| row curve | `spanish_motor_severity` @ 2000 | `F_catboost` | weighted_rmse | 0.01111 vs `E_glm` | MDE 0.02014 | Inconclusive | `row_curve_stage1.csv` |
| row curve | `spanish_motor_severity` @ 4760 | `E_glm` | weighted_rmse | 0.01243 vs `F_catboost` | MDE 0.01963 | Inconclusive | `row_curve_stage1.csv` |

<!-- END GENERATED: baseline-conclusion -->

# Exposure-aware GLM follow-up — the six classification datasets

> **Status:** current — analysis, 2026-11-21 (#695). Reads committed captures; no TabPFN refit.

**Question:** §14.11–§14.13's "TabPFN is AUC #1 on all six classification datasets" compares
against GLMs that take `Expo` raw. §19.4 showed that on `norauto` a one-hot LR with `log(Expo)`
added — the usual actuarial treatment — beats both model versions. Does that generalise? The report
filed it as "a separate follow-up that re-tests all six datasets against exposure-aware GLMs"; this
is that follow-up.

## Method

- **Specification, anchored first.** One-hot categoricals + numeric features + `log(exposure)` as an
  additive column, `LogisticRegression(random_state=0, max_iter=500)`. On `norauto` seed 42 this
  reproduces §19.4 to the published digits: 0.17755 without exposure and **0.17433** with it
  against their 0.17755 / 0.17432 (the difference is the fifth decimal).
- **No refit of TabPFN.** Per-fold predictions come from the committed captures
  (`predictions/<dataset>__seed<seed>__<model_version>.npz`); the GLM is fit on the complement of
  each capture's `test_idx`, so the folds are identical by construction.
- **Scope.** `coil2000` carries **no exposure column** — it is a CARAVAN purchase dataset — so it
  cannot be given the actuarial treatment and is excluded by construction. That leaves **five** of
  the six, not six.
- Metrics: log loss, Brier, AUC, PR-AUC, paired per fold; `*` marks p<0.05.

## Results

Δ = TabPFN − GLM. For log loss and Brier, negative means TabPFN better; for AUC and PR-AUC,
positive means TabPFN better. `(T)` / `(G)` marks the better mean.

| dataset | seed | version | log loss GLM / TabPFN | Brier Δ | AUC Δ | PR-AUC Δ |
|---|---:|---|---|---|---|---|
| `ausprivauto0405` | 7 | v3.5_default | 0.23851 / 0.23820 | -0.00003* (T) | +0.00088 (T) | +0.00156* (T) |
| `ausprivauto0405` | 42 | v3.5_default | 0.23853 / 0.23816 | -0.00005* (T) | +0.00126 (T) | +0.00232* (T) |
| `ausprivauto0405` | 42 | v3_default | 0.23853 / 0.24026 | +0.00020* (G) | +0.00194 (T) | +0.00108 (T) |
| `ausprivauto0405` | 123 | v3.5_default | 0.23849 / 0.23824 | -0.00003 (T) | +0.00062 (T) | +0.00176 (T) |
| `bemtl16` | 42 | v3.5_default | 0.60903 / 0.59546 | -0.00557* (T) | +0.01858* (T) | +0.02996* (T) |
| `bemtl16` | 42 | v3_default | 0.60903 / 0.59681 | -0.00511* (T) | +0.01768* (T) | +0.02944* (T) |
| `bemtl97` | 7 | v3.5_default | 0.34210 / 0.34035 | -0.00039* (T) | +0.01055* (T) | +0.00919* (T) |
| `bemtl97` | 42 | v3.5_default | 0.34210 / 0.34044 | -0.00037* (T) | +0.01002* (T) | +0.00885* (T) |
| `bemtl97` | 42 | v3_default | 0.34210 / 0.34279 | +0.00002 (G) | +0.00899* (T) | +0.00843* (T) |
| `bemtl97` | 123 | v3.5_default | 0.34208 / 0.34042 | -0.00038* (T) | +0.01033* (T) | +0.00909* (T) |
| `norauto` | 7 | v3.5_default | 0.17430 / 0.17450 | +0.00003* (G) | -0.00159 (G) | -0.00153* (G) |
| `norauto` | 42 | v3.5_default | 0.17433 / 0.17446 | +0.00002 (G) | -0.00112 (G) | -0.00098 (G) |
| `norauto` | 42 | v3_default | 0.17433 / 0.17619 | +0.00016* (G) | -0.00030 (G) | -0.00116 (G) |
| `norauto` | 123 | v3.5_default | 0.17430 / 0.17445 | +0.00002 (G) | -0.00103* (G) | -0.00109 (G) |
| `uslapseagent` | 42 | v3.5_default | 0.26977 / 0.24380 | -0.00960* (T) | +0.01779* (T) | +0.04840* (T) |
| `uslapseagent` | 42 | v3_default | 0.26977 / 0.24906 | -0.00779* (T) | +0.01498* (T) | +0.04104* (T) |

## Reading

- **`norauto` is the exception, and it is the only one.** TabPFN loses log loss on all four
  seed/version rows and loses AUC on three of four. On v3.5 the gap is small (+0.00014 to
  +0.00020 log loss, −0.0010 to −0.0016 AUC) and significant on one seed only; on v3 it is clear
  (+0.00186 log loss).
- **`bemtl97`, `bemtl16`, `uslapseagent` and `ausprivauto0405` keep TabPFN's lead.** `bemtl16`
  gains most from exposure (+0.0186 AUC over the GLM with it), `uslapseagent` next (+0.0178). On
  `ausprivauto0405` the GLM edges log loss on some seeds while TabPFN holds AUC — the same pattern
  §19.4 reported.
- **`bemtl97`'s v3 log-loss loss is +0.00002** — significant by the paired test and meaningless in
  size; the v3.5 rows win it back (−0.0017).

## What this corrects

The claim "AUC #1 on all six classification datasets" is wrong in two ways and should read:

> AUC #1 over GLMs, GBDTs and RF on **four of the five datasets that carry an exposure column**
> (`coil2000` has none); on `norauto` an exposure-aware GLM edges v3.5 and clearly beats v3.

The adoption rule does not change: §19.4 already recorded `norauto` as the "exposure-aware GLM
edges both versions" case, and this follow-up shows it is the exception rather than the rule.

## Evidence

- `scripts/eval/insurance_benchmark_v1/exposure_aware_glm_followup.csv` — 16 rows, one per
  dataset × seed × version, with the paired p and fold counts.
- Reproduce: the specification and the anchor are stated above; the GLM is fit on the complement of
  each capture's `test_idx`.

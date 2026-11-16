# Baseline claims inventory — the v3.5 stack against the published claims

> **Status:** current — desk inventory, 2026-11-16. It measures nothing, fits nothing and restates
> no number it does not point at; every row sends the reader to the document and section that keeps
> the number. **Ticket:** #626 (wayfinder research). **Inputs:** #623 (map), #635 (the landed v3.5
> stack), #640 (landing spec). **Consumers:** #627 (headline verdict) and #628 (gap register).
> **Branch:** `research/baseline-claims-inventory` — a note only; no PR.

## How to read this

- **Owner.** The document and section that keeps the number. A number resolves to its Capture, and the
  [evidence map](../EVIDENCE_MAP.md) says which tree to walk; the owner is the section where the claim is
  stated and therefore the one that must carry the correction. Where a second document carries the same
  claim, it is named in the amendment cell, because that is where an edit is owed.
- **Status.**
  - **confirmed** — still holds, and the owner is the section to cite.
  - **superseded** — a later section replaces it and is now the citation; the earlier text stays as the
    record of what was run.
  - **withdrawn** — no longer supported by any evidence; do not cite it, in any version.
  - A **Model version** is named per row. Where a status differs between versions, the claim states
    which version it belongs to. No claim here spans the v3 and v3.5 lines.
- **Discharged.** Where the amendment cell says *discharged*, the pointer or label landed with the v3.5
  stack (#645) and #628 should not re-open it. *Edit owed* means the owning text still reads as if the
  claim stood.

**The seven areas the ticket names**, used as the row prefix: **1** `eudirectlapse`, **2**
`ausprivauto0405`, **3** `norauto`, **4** `bemtl97`, **5** the two target leaks (`bemtl16`,
`bemtl97_amount`), **6** the size sweep, **7** the four frontier wins.

## The inventory

| claim | status | owning document and section | what must be amended |
| --- | --- | --- | --- |
| **1.1** `eudirectlapse` is a TabPFN classification loss: the Method finishes last of three on AUC, behind a linear Method on every fold, and the deficit is attributed to additive-lapse structure the Method does not capture. Model version: v3 (TabArena harness) | withdrawn | master report §14.10 (the number); withdrawn at §17.3 and §17.8 | §14.10 table row — dated note "did not reproduce; §17.3" (**edit owed**). [Benchmark summary](../archive/frontier-benchmark/TABPFN_BENCHMARK_SUMMARY.md) Caveats bullet — already rewritten to a narrow win with the §17 pointer (**discharged**). [benchmark_portfolio.md](../experiments/frontier-benchmark/benchmark_portfolio.md) §3 — replace "Linear still wins `eudirectlapse`" with the §17 pointer (**edit owed**). [regime_characterization.md](../experiments/frontier-benchmark/regime_characterization.md) §1 table row, §2(b) GLM-captured list, §3 paste-ready descriptor — reclassify and add a dated note; its own status line claims currency, so this LOSE row is the loudest stale artefact (**edit owed**). [MASTER-REPORT-DIGEST](../MASTER-REPORT-DIGEST.md) §14.10 paragraph ("eudirectlapse still Linear") — note (**edit owed**). [R1 pilot](../experiments/r1-pilot/FINE_TUNING_PILOT_RESULTS.md) §4 finding 2 and `archive/pilot2-phase2/PRE_FINETUNING_INVESTIGATIONS.md` — both use the loss to justify the breadth study; note (**edit owed**). [D5 explanation](../experiments/diagnostics/d5_eudirectlapse_explanation.md) §1 — note that its premise is a TabArena-harness figure and that its null agrees with §17.3 (**edit owed**) |
| **1.2** The August TabArena figure is the number to cite for the Method's lapse skill on `eudirectlapse`. Model version: v3 | superseded | §17.2, §17.3, §17.9 (three split seeds) replace §14.10 | [MODEL_VERSIONS](../MODEL_VERSIONS.md) banner carries the pointer (**discharged**); its "what flipped between the v2 era and v3" table still prints the old figure with no note (**edit owed**). Any other citation routes to §17 |
| **1.3** The gap sits on TabPFN's side of the harness, not the baseline's: a fairly encoded linear Method reproduces the published baseline result on the identical folds, while TabPFN does not reproduce its published result. Model version: v3 | confirmed | §17.3 | None. This is the asymmetry #627 should state if it mentions the loss at all |
| **1.4** v3.5 improves on v3 on `eudirectlapse` on log loss, Brier and PR-AUC, paired on identical folds, and holds on three split seeds. Model version: v3 vs v3.5 | confirmed | §17.2, §17.9 | None. Cite as the paired version test |
| **1.5** The cause of the August gap is known. Model version: n/a | withdrawn | §17.4 (alias drift and fewer training rows ruled out; the TabArena wrapper survives by elimination, untested) | None in the documents — the limitation is stated. Constraint on #627: do not attribute the gap, and do not carry "additive structure" forward |
| **2.1** On `ausprivauto0405` the entire linear family beats TabPFN on log loss and Brier, paired-significant and stable across split seeds, while TabPFN stays first on AUC. Model version: v3 | superseded on v3.5; confirmed for v3 | §14.13.3 (claim); §18.2–§18.4 replace it; §18.8 states the v3 exception remains the correct statement for v3 | §14.13.3 and §14.13.5 — dated supersession line to §18 (**edit owed**; §18.8 says "not edited here"). Benchmark summary Verdict paragraph — carries the pointer (**discharged**). Regime §1 `ausprivauto0405` row and §2(b) — the row's note cites the §14.11.3 retraction but not §18 (**edit owed**) |
| **2.2** The v3.5 log-loss rank on `ausprivauto0405` moves from mid-table to first of the nine harness Methods. Model version: v3.5 | confirmed | §18.2 | None. #627 may state the rank with §18.2 as owner |
| **2.3** AUC does not move from v3 to v3.5 on `ausprivauto0405`; TabPFN remains first of nine on all three seeds. Model version: v3 vs v3.5 | confirmed | §18.2, §18.6 | None. Note the counter-example it creates for area 3: here v3 keeps its AUC lead even over the exposure-aware GLM (§19.4) |
| **2.4** The v3.5 calibration win on `ausprivauto0405` is a dominant one. Model version: v3.5 | withdrawn | §18.3, §18.6, §18.8 (a narrow, consistent win; ~0.1% over the strongest linear specification) | None in the documents. Wording constraint for #627: "narrow and consistent", never "dominant" |
| **3.1** On `norauto` TabPFN loses log loss and Brier to LightGBM (the published v3 calibration loss). Model version: v3 | superseded | §14.11.3, §14.13.3 → §19.2, §19.3 | §14.11.3 table row and §14.13.3 bullet — dated note to §19 (**edit owed**). Regime §1 `norauto` row ("fold-noise tie") and §2(b) — a v3 reading presented without a version column (**edit owed**) |
| **3.2** TabPFN holds the best AUC of the suite on all six canonical classification datasets, over GLMs as well as GBDTs. Model version: v3, and carried forward unqualified | withdrawn for `norauto`; the scoped form ("best of the nine harness Methods") still holds | §14.11.4 and §14.13.2 (claim); decided by §19.4 | §14.11.4 bullet, §14.13.2 table, §14.12.5, §14.13.5 — dated scope note (**edit owed**). Benchmark summary Verdict paragraph ("AUC and PR AUC #1 … over GLMs") — same scope (**edit owed**). [KNOWLEDGE-PATH](../KNOWLEDGE-PATH.md) stage-4 verdict line — same (**edit owed**). Regime §2(b) and §3 — must not list `norauto` as an AUC win unqualified (**edit owed**) |
| **3.3** v3.5 is approximately the exposure-aware GLM on `norauto`, with the GLM marginally ahead; v3 is clearly behind it. Model version: v3 vs v3.5 vs a linear Method outside the nine | confirmed | §19.4, §19.8 | None in the documents. #628 should register the six-dataset exposure-aware re-test — flagged at §19.4 as outside #186 — as open work |
| **3.4** The nine-Method baseline set establishes the linear floor. Model version: all | withdrawn as a general claim | §17.5 (categoricals as integer codes), §19.4 and §19.6 (exposure taken raw) | Master §7.1 limitation list and the benchmark summary's "How we tested it" — add the encoding sentence (**edit owed**) |
| **3.5** TabPFN's calibration is never significantly worse than the alternatives at default settings. Model version: v3, carried forward unqualified | withdrawn | §14.11.4 and §14.13.3 (claim); decided by §18.3 and §19.4 | Benchmark summary Verdict paragraph and §14.11.4's closing bullet — replace with "never worse among the nine harness Methods; two documented exceptions, and overturned on `ausprivauto0405`" (**edit owed**) |
| **4.1** TabPFN ranks mid-table on log loss on `bemtl97`, behind LightGBM. Model version: v3 | superseded | §14.11.3, §14.13.3 → §20.3 | §14.11.3 row and §14.13.3 bullet — dated note (**edit owed**). Regime §1 `bemtl97` row and §2(b) — version scope (**edit owed**). Digest §14.11 and §14.13 paragraphs (**edit owed**) |
| **4.2** On v3.5 TabPFN is first of nine on log loss, Brier and AUC on every seed, and wins PR-AUC on every fold of all three seeds. Model version: v3.5 | confirmed | §20.3 | None. Constraint on #627: the owner states four metrics, not "every metric" — lift is not claimed first (§20.2) |
| **4.3** v3.5 trades a little ranking for calibration — a general trait of the version. Model version: v3 → v3.5 | withdrawn | §18.6, §19.6, §20.2, §20.6 (each scopes the dip to the dataset) | None in the documents — the owners already scope it. Constraint on #627: do not generalise the dip |
| **4.4** `bemtl97` needs no exposure caveat: the exposure-aware GLM trails LightGBM here, so v3.5 leads every linear specification tested. Model version: v3.5 | confirmed | §20.4 | None |
| **5.0** The `bemtl16` and `bemtl97_amount` numbers outside §§21–§22 remain citable. Model version: v3 | withdrawn | §6 (the leaks), §21.4, §22.4, §22.6 | Scope of the supersession, stated once here: **every `bemtl16` performance number in §3–§14.13**, and **every `bemtl97_amount` performance number in §4, §12.1, §14.8 and §16**. Dataset identity — row counts, folds, targets — is unaffected. No document may be read as exempt without a dated note |
| **5.1** `bemtl16` is a thin-signal win with a beyond-SE lead over LightGBM and a large harness-GLM gap. Model version: v3 (leaky) | superseded | §14.7, §14.13.2 → §21.3, §21.4 | §14.7 and §14.13.2 carry dated notes (**discharged**). Regime §1 `bemtl16` row and footnote † — the footnote explains the replacement, but the row's position and outcome-class cells still print the leaky reading; add "(clean: §21)" to the class cell (**edit owed**, small) |
| **5.2** TabPFN's top-decile lift deficit on `bemtl16` is a genuine weak spot: lift rank behind LightGBM and CatBoost. Model version: v3 (leaky) | withdrawn — a leak artefact | §14.12.3 and §21.4 | §14.12.3 note (**discharged**). Benchmark summary Verdict paragraph — "rank 1 on 4/6 by lift" must be re-derived from §14.12.3's remaining rows plus §21.4 and stated with both owners; editing the digit alone would invent a number no section states (**edit owed**). Digest §14.12 paragraph — same (**edit owed**) |
| **5.3** On clean `bemtl16` TabPFN is first of nine on all five metrics under both versions, and its lead over LightGBM is not beyond one SE. Model version: v3 and v3.5 (clean) | confirmed | §21.3, §21.5, §21.8 | None — cite §21, not §14.7–§14.13. #628: §21.6 leaves the tuned-baseline set unverified on clean data |
| **5.4** `bemtl97_amount`'s large RMSE loss and its rank at the bottom of the field describe the Method or the target. Model version: v3, v3.5 (leaky) | superseded | §4.1, §14.8, §16.2 → §22.3, §22.4, §22.8 | §4.1, §14.8, §16.2 carry dated notes (**discharged**); regime §1 row and footnotes ‡ (**discharged**). Digest §14.8 paragraph and §14.15 paragraph — both still present the leaky gaps and the alt-metric rows; `altmetrics_rescore_spec.md`'s background does the same, and §22.6 supersedes those rows (**edit owed**) |
| **5.5** The Poisson GLM's collapse on `bemtl97_amount` is explained by the target's zero mass. Model version: v3 (leaky) | withdrawn | §14.8 (claim); withdrawn at §22.4 and §22.6 | §14.8 paragraph already carries the note (**discharged**). Any document that reuses §14.8 as the cautionary tale for zero-inflated targets must cite §22.4 instead — in particular [`baseline_method_specification.md`](../experiments/fair-test-freq-sev/baseline_method_specification.md), which cites §14.15 of the digest as standing warning (**edit owed**) |
| **5.6** TabPFN stays off the parsimony frontier on `bemtl97_amount` and still loses RMSE to LightGBM — the direction survives, the published size does not. Model version: v3 and v3.5 (clean) | confirmed | §22.4, §22.5, §22.8 | None |
| **6.1** TabPFN wins eight of the nine size-sweep cells; the single loss is `bemtl97` at full size. Model version: v3 | superseded | §13.2 → §23.2, §23.6 | §13.2 and §13.3 carry notes (**discharged**). Benchmark summary at-a-glance row and "The evidence" bullet still print the v3 count with no v3.5 pointer (**edit owed**). Regime §1 sweep paragraph and §3 descriptor carry it (**discharged**). benchmark_portfolio §5 and digest §13 — add the pointer (**edit owed**) |
| **6.2** The size-ceiling curve is flat for TabPFN and the full-size loss is a shave. Model version: v3 | superseded | §13.3 → §23.3 | §13.3 note exists (**discharged**). Wording constraint on #627: cite §23.3, which states the ceiling is not visible in the v3.5 sweep |
| **6.3** A frontier run may reuse a sweep's TabPFN row from a different model version. Model version: all | withdrawn | §15.2 caveat (claim); withdrawn at §23.4 and §20.1 | §20.1 and §20.6 still say the size-sweep claim is "still a v3 statement" — add the dated note that §23 refreshed all nine cells and §23.4 closed the reuse path (**edit owed**, small). §15.2's sweep caveat becomes historical |
| **6.4** Off the parsimony frontier, four of twelve datasets on v3.5, against five of twelve on v3. Model version: v3 vs v3.5 | confirmed | §16.3, §16.8 | Discharged across the summary at-a-glance row, the summary banner, §8's count, the regime totals and MODEL_VERSIONS. #627 cites the v3.5 count with §16.3 as owner |
| **7.1** The four frontier datasets where v3 won hold on v3.5: no win and no frontier position lost. Model version: v3 vs v3.5 | confirmed | §24.2, §24.3, §24.7 | None — the citation for "the wins hold" |
| **7.2** TabPFN is first on every metric of `ausprivauto0405_vehvalue`. Model version: v3.5 | withdrawn | §24.3 (MAE worse on every fold; RMSE unchanged) | Any "every metric" phrasing must except MAE (**edit owed** wherever it appears). Benchmark summary "The evidence" regression bullet — silent on the MAE regression; add the exception (**edit owed**) |
| **7.3** v3.5 is better than v3 or tied on every frontier metric across the four datasets, with `ausprivauto0405_vehvalue` RMSE unchanged and still not separable from LightGBM. Model version: v3 vs v3.5 | confirmed | §24.3, §24.4, §24.7 | None |
| **7.4** The §17–§20 and §24 deltas are model-only: same-day pairs, identical folds and truth, every non-TabPFN Method's predictions bit-identical. Model version: v3 vs v3.5 | confirmed, for those four addenda only | §17.1, §18.1, §19.1, §20.1, §24.1 | None. Constraint on #627: the claim does **not** extend to §16, where `scikit-learn` moved and the `ols` rows are not comparable (§16.4; MODEL_VERSIONS carries that caveat, **discharged**) |

## What this gives #627 and #628

**#627 (headline verdict) — three sentences it cannot use.** `eudirectlapse` as a TabPFN
classification loss or as evidence about additive structure (1.1, 1.5); "best AUC over all classical
alternatives on all six datasets" without the exposure caveat (3.2); "calibration never worse" (3.5).
**Three it can.** v3.5 improves on v3, paired, across every re-tested tier (1.4, 2.2, 4.2, 5.3, 6.1,
7.1); every published calibration loss reverses on v3.5 except where an exposure-aware GLM edges it
(3.1, 3.3, 4.1); the four v3 wins hold, with one secondary MAE regression (7.1, 7.2, 7.3).

**#628 (gap register) — six open items the stack leaves behind.**

1. The tuned-baseline set is unverified on clean `bemtl16` (§21.6).
2. No dataset has been re-tested against exposure-aware GLMs beyond the two done here; the report
   flags the six-dataset re-test as outside #186 (§19.4).
3. The cause of the `eudirectlapse` gap is unresolved; the TabArena wrapper is the only surviving
   candidate and is untested (§17.4).
4. The v1 TabArena runs and the #123 alt-metric rows are superseded but not regenerated (§21.6,
   §22.6).
5. The harness's linear encoding understates the linear floor benchmark-wide (§17.5, §19.6).
6. `eudirectlapse` has no exposure analogue, but its regime-table classification and the adoption
   rule's "GLM-captured" list both need a version column before either can be cited (§14.10 row,
   regime §1–§3).

## Carriers that need no further edit

Listed so the gap register does not re-open settled work. The benchmark summary's version banner; the
MODEL_VERSIONS timeline and its v3→v3.5 table; §13.2/§13.3's v3.5 notes; §14.7's, §14.8's, §14.11.3's,
§14.12.3's and §16.2's dated notes; the regime table's footnotes † and ‡; §18.8's and §20.8's "not
edited here" statements. Each already points at the section that owns the replacement. What remains
open is the **forward** side: the headline sections those notes point away from, which still read as if
the claim stood — that is the edit list in the table above.

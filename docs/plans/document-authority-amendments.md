# Plan — the document-authority amendments

> **Status:** plan, written 2026-11-09. It specifies the edits that implement the decisions in
> [#518](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518)–[#522](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/522),
> under map [#517](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/517). The order it enforces
> is stated in [`docs/DOCUMENT_AUTHORITY.md`](../DOCUMENT_AUTHORITY.md).

## What this is for

Every losing passage in the Phase 2 owning documents, with the note it gains. **45 amendments across five
tickets, plus one passage recorded as deliberately unchanged.** One implementing run applies them. No
decision is re-opened here — the decision lives in its ticket, and the note points at it.

## The three kinds

A note cannot repair an inverted sign or a misquoted figure, and a correction cannot preserve an older
sentence that contradicts a newer one. So each row says which it is:

| Kind | What happens | When |
| --- | --- | --- |
| **note** | Text unchanged; a dated note is added | The passage is older than the winner, or was true of a narrower scope |
| **correction** | A phrase is replaced in place, and the note **quotes the wording it replaced** | The passage is factually wrong: a misquoted figure, an inverted sign, a value matching neither the plan nor the run |
| **addition** | A new row, line or paragraph is added | The page omits a fact it must show (a timeline row, a per-artifact entry) |

Nothing is lost under any kind: a correction keeps the superseded wording inside its own note.

**Note form.** Prose passages take a blockquote immediately after the paragraph, opening with the date.
Table rows take an italic note immediately after the table, keyed by row label — a blockquote cannot live
inside a Markdown table row. Both follow the decision log's own correction style (`D11→D15`, `D21→D22`).

---

## [#518 — the metric rule](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/518)

| Site | Kind | Current text | Note |
| --- | --- | --- | --- |
| `current/FINETUNING_PILOT_DESIGN.md:204-208` | note | "Primary \| Brier score, log loss, calibration error" | 2026-11-09: this table governs what Phase 2 **reports**. The claim rested on ROC AUC with a Brier veto (D12, 2026-11-03). |
| `current/FINETUNING_PILOT_DESIGN.md:210` | note | "improves ROC AUC while worsening calibration is not a general performance improvement" | 2026-11-09: D12 made this numeric. The tolerance is +0.001; the anchor rose +0.0003 and stands; above +0.001 the claim would have been refused. |
| `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md:41-43` | correction | "For discrimination and calibration metrics (ROC AUC, PR AUC, Brier), positive means improvement" | **Correction**: Brier moves to the loss-type list. ΔBrier = arm − `A_raw`, so positive means worse. Note quotes the old sentence. Every analysis already reads it that way. |
| `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md:47-48` | note | "Primary \| the paired difference in log loss" | 2026-11-09: the claim measure was ROC AUC (D12). The paired log-loss estimand was not carried into the Phase 2 report — a stated gap, not a silent demotion. |
| `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md:55-57` | note | "Primary: log loss … Also reported, no decision role: … Brier" | 2026-11-09: Brier carries a **veto** under D12, so it has a decision role. Log loss keeps its primary reporting role and is unreported. |
| `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md:58-60` | note | "This is currently **TBD**" | 2026-11-09: set at sign-off on 2026-10-30 — see §12.1. |
| `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md:228`, `:253`, `:262` | note | ">= 0.009" / "carries 369 and 0.009" / "already resolves 0.009 ROC" | 2026-10-31: superseded by the reconciliation at `:190-195`; must not be quoted. The measured figure is the anchor's 0.0036 median half-width. |
| `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md:236-239` | note | "Only more test rows (or more positives) move it" | 2026-11-09: true of the row-sampling floor. The between-split component is what the replication bought (D13, D22: "resolution-for-variance substitution"). |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:42` | note | "ROC AUC reported alongside, never folded in" | 2026-11-09: ROC AUC was the claim measure (D12), with Brier as a veto. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:853` | note | "369 positives resolved about 0.009" | 2026-10-31: superseded; see the SAP's reconciliation at `:190-195`. Must not be quoted. |
| `analyses/finetuning_replication_result.md:11` | correction | "Brier no worse (+0.0003 against a +0.001 allowance)" | **Correction**: "no more than 0.001 worse" — +0.0003 is an increase. |
| `current/FINETUNING_PHASE2_OUTCOME.md:62` | correction | "Brier's worst seed was +0.0003 against an allowance of +0.001" | **Correction**: "was 0.0003 worse, against an allowance of 0.001". |
| `current/FINETUNING_PHASE2_OUTCOME.md`, after §4 `:117` | addition | "**Untested is not failed.**" (last of the three misreadings) | A fourth paragraph: the SAP's primary estimand (paired log loss) is not reported here, and why. It belongs with the misreadings, not in §6's list of owning analyses. |

---

## [#519 — the R3 gate](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/519)

| Site | Kind | Current text | Note |
| --- | --- | --- | --- |
| `reference/FINE_TUNING_PILOT_RESULTS.md:469-473` | note | "That rule already exists — the R3 gate … The gap is application and recording, not design." | 2026-11-09: the gate cannot refuse a null — its `B > E` branch is satisfied by raw TabPFN, and `B > A` failed in R1. Rejected by `PILOT_2_DESIGN.md:345-346`; Phase 2's rule is D12. |
| `reference/FINE_TUNING_PILOT_RESULTS.md:570-571` | note | "Apply and record the existing decision rule (the design's R3 gate)" | 2026-11-09: withdrawn. Applying it would admit on a criterion the baseline arm satisfies. |
| `reference/PILOT_2_DESIGN.md:345-346` | note | "**Rejected:** the `R3 gate` … cannot discriminate the fine-tuning hypothesis." | 2026-11-09: binding. This rejection is why the gate does not appear in the Phase 2 outcome, and why D12 was written. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:409-415` | note | "Proceed to R3 if **any** of the following hold in R2" | 2026-11-09: historical. Never evaluated — R2 never ran — and rejected as a rule (`:778-797`). Do not apply to any later result. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:778-782` | note | "A criterion satisfied by the baseline arm cannot discriminate …" | 2026-11-09: this is the finding, and it governs. Retained as the record of why the gate failed. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:791-797` | note | "Recommended replacement: admit only on a **B vs A** criterion" | 2026-11-09: not adopted. Recommended for R2/R3, neither of which ran; adopting it now would be a new commitment. Phase 2 used D12. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:98-101` | note | "**R2 has not been run** … **Do not cite R1 as a gate decision.**" | 2026-11-09: this instruction stands, and is why the R1 page's recommendation is not followed. |

---

## [#520 — cost and batch size](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/520)

| Site | Kind | Current text | Note |
| --- | --- | --- | --- |
| `current/FINETUNING_DECISION_LOG.md:471-472` | note | "Batch size is now **twenty seeds** … giving twelve batches" | 2026-11-09: the plan. Twenty launches of twelve ran (D18 `:497`); the change is unrecorded. |
| `current/FINETUNING_DECISION_LOG.md:490` | correction | "… 238 fresh seeds (93–330), eight batches" | **Correction**: twelve batches were planned and twenty launches ran. "Eight" matches neither the body nor the execution. |
| `current/FINETUNING_DECISION_LOG.md:485` | note | "projects to ~512 seeds (≈ $6.3 at two arms)" | 2026-11-09: projection. The cell cost $0.065 (D20); it was wrong by two orders of magnitude for pricing resolution rather than variance. |
| `current/FINETUNING_DECISION_LOG.md:497-498` | note | "twenty paid launches — nineteen of twelve seeds, the last of ten" | 2026-11-09: **the execution record, and it governs.** Confirmed by twenty `results/` directories. |
| `current/FINETUNING_DECISION_LOG.md:523` | note | "projects to ~512 seeds (~$14)" | 2026-11-09: projection, superseded by the measured $0.065 (D20). |
| `current/FINETUNING_DECISION_LOG.md:552-553` | note | "≈$6.3 (D17) and ≈$18.8 (the breadth specification's per-dataset line)" | 2026-11-09: $18.8 is **derived** — the spec's `:140` programme line divided by three — not a per-dataset line the spec states. |
| `current/FINETUNING_DECISION_LOG.md:715` | correction | "D18 projected **~512 seeds (~$9.50)**" | **Correction**: D18 projected **~$14**. The $9.50 is a misattribution, not a fourth estimate. |
| `analyses/finetuning_breadth_spanish_result.md:46` | correction | "D18 projected **~512 seeds (~$9.50)**" | **Correction**: same — D18 says ~$14. |
| `current/FINETUNING_BREADTH_SPEC.md:107` | correction | "the per-launch ceiling that **D10** sets for the run" | **Correction**: D10 sets no ceiling. The ceilings are D12's $0.15 and D17's $0.60; a cell may set its own, as D19 did at $0.50 and $3.00. |
| `current/FINETUNING_STATUS_BRIEF.md:76` | note | "the second needs ~512 seeds (~$14), which the remaining balance does not cover" | 2026-11-09: historical projection; the cell cost $0.065 and completed inside the balance. |
| `current/FINETUNING_COST_AND_CONTROLS.md:6` | note | "This page owns measured and modelled cost figures" | 2026-11-09: the breadth cells' cost is measured in D18 and D20. The four projections are superseded and were never carried here. |

---

## [#521 — scope and counts](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/521)

| Site | Kind | Current text | Note |
| --- | --- | --- | --- |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:37` | note | "scope \| lapse only: `uslapseagent`, `spanish_motor_lapse`, `eudirectlapse`" | 2026-11-09: this is the count of datasets with a **lapse target**, not the pilot scope. The scope is the four-dataset family (design `:141`); `coil2000` was stopped on resolution (D21), not excluded. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:126-128` | note | "The scope is lapse classification only, three datasets, as stated in the front section." | 2026-11-09: the front section does not state this — the design states four. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:159-160` | note | "Four datasets was the pre-probe selection. The current design uses the three lapse datasets, staged, and `A_raw` is re-measured in every run rather than compared across runs." | 2026-11-09: the current design uses **four**; three is the lapse-target count. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:940-943` | note | "Scope decision: lapse classification (13 Sep)" | 2026-11-09: this is a finding about **targets** — three datasets carry a lapse or surrender outcome. It was taken as a scope decision; it is not one. The finding stands. |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:950` | correction | `| eudirectlapse | lapse | 23,060 | 128 | ~2,954 |` | **Correction**: 132 positives at the 1,000-row cap (SAP `:226`, R1 `:483`, computed from saved predictions). |
| `current/FINETUNING_EXPERIMENT_REFERENCE.md:124-153` | note | "Available Datasets (15 total, successor repo)" and its rows | 2026-11-09: **another repository's inventory, marked not corrected.** Counts for this repository are owned by `FINETUNING_COST_AND_CONTROLS.md:79-91` and match the CSVs. |
| `current/FINETUNING_PILOT_DESIGN.md:141` | note | "The four-dataset family is the in-domain pilot scope." | 2026-11-09: this governs. `coil2000`'s absence from Phase 2 is a resolution stop (D21), not a scope limit. |
| `current/FINETUNING_COST_AND_CONTROLS.md:79-91` | note | the registered / not-registered table | 2026-11-09: the authoritative count for this repository; agrees with the CSVs. |

---

## [#522 — model eras](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/522)

| Site | Kind | Current text | Note |
| --- | --- | --- | --- |
| `MODEL_VERSIONS.md:17` | note | "Apr 2026: paper writing — referenced only, never run … **Do not cite our numbers as v2.5.**" | 2026-11-09: true **of Apr 2026 and the benchmark era**. The imperative is scoped: do not cite the v2-era **benchmark** numbers as v2.5. A v2.5 run exists — see the 4 Nov row. |
| `MODEL_VERSIONS.md` timeline, after `:20` | addition | — | **New row**: `4 Nov 2026: D2 importance diagnostic` · `v2.5 (v2.5_default)` · local `tabpfn 6.4.1` · 2,000-row subsample · evidence `tests/fixtures/diagnostics/d2_importance/20261104T1725Z-uslapseagent/record.json` and `docs/analyses/data/README.md` · **current for that diagnostic only; not a benchmark number; do not cite as v3.** |
| `MODEL_VERSIONS.md:42` | correction | mermaid: "Apr 2026 : v2.5 released (referenced in paper caveat, never run by us)" | **Correction**: "(paper caveat; no benchmark run)" plus a line `Nov 2026 : v2.5 local checkpoint — D2 importance diagnostic`. |
| `MODEL_VERSIONS.md:89-96` | addition | per-artifact validity table — four rows, none for the diagnostics | **New row**: `docs/analyses/data/*` (D1/D2) · tested 2026-11-04 · TabPFN **v2.5**, local `tabpfn 6.4.1` · **v2.5 only — do not cite as v3.** |
| `MODEL_VERSIONS.md:79-83` | note | "`tabpfn 8.5.0`, the version the anchor ran on" | 2026-11-09: scoped to the **fine-tuning pilot**. The diagnostics ran on `tabpfn 6.4.1`, a different local-package line. |
| `MODEL_VERSIONS.md:100` | note | "Never write 'v2.6' unless you have a manifest proving the weights ID" | 2026-11-09: the same rule applies to v2.5 — cite it only with a record naming the checkpoint. |
| `analyses/data/README.md:133`, `:158-159` | **none** | "the era the library actually resolved: `v2.5`" | **No amendment.** This page records what the library resolved and is correct. Carried here so the omission is visible as a decision. |

---

## Order of work

One commit per group, so each diff is reviewable against the rows above. Per-file site counts, for proving
completeness:

| Group | File | Sites |
| --- | --- | ---: |
| 1 | `current/FINETUNING_STATISTICAL_ANALYSIS_PLAN.md` | 6 |
| 2 | `current/FINETUNING_DECISION_LOG.md` | 7 |
| 3 | `current/FINETUNING_EXPERIMENT_REFERENCE.md` | 12 |
| 4 | `current/FINETUNING_PILOT_DESIGN.md` | 3 |
| 5 | `current/FINETUNING_COST_AND_CONTROLS.md` | 2 |
| 6 | `current/FINETUNING_BREADTH_SPEC.md`, `current/FINETUNING_STATUS_BRIEF.md` | 1 + 1 |
| 7 | `reference/FINE_TUNING_PILOT_RESULTS.md`, `reference/PILOT_2_DESIGN.md` | 2 + 1 |
| 8 | `MODEL_VERSIONS.md` | 6 |
| 9 | `analyses/finetuning_replication_result.md`, `analyses/finetuning_breadth_spanish_result.md` | 1 + 1 |
| 10 | `current/FINETUNING_PHASE2_OUTCOME.md` | 2 |
| | **total** | **45** |

`docs/analyses/data/README.md` is in no group: it takes no amendment.

## Verification

Run the full gate — `./scripts/check.sh` — and in particular:

- **doclinks** — every link added by a note resolves, including the pointer left in `EVIDENCE_MAP.md`.
- **docstatus** — the new page is at `docs/` root and outside the three report tiers, so it must not be
  read as a report; 43/43 reports must still pass.
- **citation** — no note introduces a bare run id.
- **evidence** — `outputs/` and `results/` are untouched, so no `evidence-change` label is needed.

Then check by hand, because the gate cannot:

- Every site still contains its original phrase — in the text, or in the note that supersedes it.
- The page's table has fourteen rows and carries no figure.
- Each note names the winner and links the ticket.
- The per-file counts above sum to the sites actually changed.

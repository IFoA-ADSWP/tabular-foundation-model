# Plans

One file per task: `docs/plans/<task>.md`. Write it **before** non-trivial work, and commit it with the
change. A plan outranks a fresh ticket — check this directory before speccing or building, because the ticket
you are about to write may already be covered.

**This index is the only map.** Of the 102 plans, 98 are linked from no other document; a handful are
mentioned elsewhere.

Each row carries the plan's own first heading, so the index cannot drift from the file it points at. The
group is the **first word of that plan's own `Status:` line** — the plans use *current*, *agreed*,
*implemented*, *proposed*, *plan* and *historical*, and the three headings below collapse those rather than
inventing a fifth vocabulary.

A plan records what was intended when it was written. Several still read **proposed** although the work has
since merged, and the pull request that merged it is the record of what happened. Nothing is corrected after
the fact: a plan that says proposed stays that way unless its author amends it, because rewriting the status
of a plan after the data would make the trail say something it did not.

## Current, agreed or implemented — 88 plans

Newest first, by ticket number where the filename carries one.

| Plan | What it settles |
| --- | --- |
| [`739-finetuning-matrix.md`](739-finetuning-matrix.md) | the paper-facing fine-tuning results matrix (#739) |
| [`729-severity-estimand.md`](729-severity-estimand.md) | the severity estimand decision (#729) |
| [`701-paid-run-ceilings.md`](701-paid-run-ceilings.md) | the paid-run path measures its own ceilings (#701, #433) |
| [`423-yes-leak-preflight.md`](423-yes-leak-preflight.md) | `--yes` answers the leak preflight (#423) |
| [`678-launch-seed-layout.md`](678-launch-seed-layout.md) | the runs ledger reads both launch-record layouts (#678) |
| [`685-access-recheck.md`](685-access-recheck.md) | refresh the model-access scoping note (#685) |
| [`687-tabicl-probe.md`](687-tabicl-probe.md) | TabICL v2 CPU timing probe (#687) |
| [`684-cite-replication.md`](684-cite-replication.md) | cite the external replication in the regime note (#684) |
| [`695-exposure-aware.md`](695-exposure-aware.md) | exposure-aware GLM follow-up (#695) |
| [`631-conclusion-table.md`](631-conclusion-table.md) | generate the conclusion's table (#631) |
| [`632-conclusion.md`](632-conclusion.md) | the technical conclusion and its companion (#632) |
| [`633-register.md`](633-register.md) | register the conclusion, and gate it (#633) |
| [`697-row-curve.md`](697-row-curve.md) | row curve stage 1 (#697) |
| [`568-reemit-captures.md`](568-reemit-captures.md) | a kept instance re-emits its captures without re-fitting (#568) |
| [`analysis-review.md`](analysis-review.md) | Plan: `analysis-review` skill |
| [`anchor-checkpoint-assertion.md`](anchor-checkpoint-assertion.md) | refuse a launch whose weights are not the anchor's line |
| [`citation-check.md`](citation-check.md) | a cited run must have a capture (#364) |
| [`credit-preflight.md`](credit-preflight.md) | the balance is checked, not assumed (#348) |
| [`d1-profile-table.md`](d1-profile-table.md) | D1 runs, and its table lands (#302's diagnostic, #407's readout) |
| [`d1-profiling.md`](d1-profiling.md) | finish D1 as the diagnostics template (#302) |
| [`d2-feature-importance.md`](d2-feature-importance.md) | D2 feature importance across TabPFN, GLM and LGBM (#303) |
| [`d3-reframe.md`](d3-reframe.md) | D3's control, and the boundary of what is free (#304) |
| [`d5-eudirectlapse.md`](d5-eudirectlapse.md) | D5: why the linear model beats TabPFN on `eudirectlapse` (#306) |
| [`declared-version.md`](declared-version.md) | a run records its declared and resolved model version (#239) |
| [`dev-environment.md`](dev-environment.md) | a reproducible local environment and a worktree that works |
| [`evidence-guard.md`](evidence-guard.md) | guard the evidence trees (#317 retro) |
| [`experiment-registry.md`](experiment-registry.md) | experiment registry (#230) |
| [`experiment-spec.md`](experiment-spec.md) | experiment spec |
| [`frontier-registry-adoption.md`](frontier-registry-adoption.md) | frontier classification reads the registry (#231) |
| [`lease.md`](lease.md) | the lease writes its record and reports its release (#325) |
| [`metric-registry-rescore.md`](metric-registry-rescore.md) | the metric registry, and a rescore that reproduces the recorded five |
| [`model-pin-auto.md`](model-pin-auto.md) | pass a model path only when an operator set one (#285) |
| [`model-pin.md`](model-pin.md) | pin the model version the pilot records (#285) |
| [`pilot-registry-adoption.md`](pilot-registry-adoption.md) | the pilot takes its experiment from the registry (#238) |
| [`predictions-export.md`](predictions-export.md) | the anchor's predictions as a table a colleague can open |
| [`provenance-record-writer.md`](provenance-record-writer.md) | one diagnostic record writer, so D1–D5 cannot diverge |
| [`record-contract.md`](record-contract.md) | the pilot writes a provenance block, and one reader states the verdict |
| [`registry-producers.md`](registry-producers.md) | remaining producers read the registry (#235) |
| [`regression-seed.md`](regression-seed.md) | regression runs honour their seed (#232) |
| [`regressor-capture-v3.md`](regressor-capture-v3.md) | capture v3 and the regressor fair-test runner |
| [`regressor-positive-control.md`](regressor-positive-control.md) | the regressor positive control |
| [`retire-baseline-config.md`](retire-baseline-config.md) | retire `src/baseline_config.py` (#234) |
| [`retry-identity.md`](retry-identity.md) | a retry is a new attempt under one launch id (#326) |
| [`reuse-provenance.md`](reuse-provenance.md) | reuse a sweep row only when its provenance matches (#233) |
| [`row-size-axis.md`](row-size-axis.md) | the row-size axis is declared in the registry (#264) |
| [`run-capture-generator.md`](run-capture-generator.md) | one offline command writes a run's capture manifest |
| [`skill-pack.md`](skill-pack.md) | Plan: skill-pack — `dataviz`, `eda`, `literature` |
| [`spine-decisions.md`](spine-decisions.md) | record the launch id and the spend gate (#245) |
| [`suite-hygiene.md`](suite-hygiene.md) | suite hygiene and the plan/ADR pointer |
| [`supply-policy-decisions.md`](supply-policy-decisions.md) | record the supply policy (#253) |
| [`truth-hash-verification.md`](truth-hash-verification.md) | the rescore verifies both hashes it was given |
| [`vast-log-dir.md`](vast-log-dir.md) | a mock launch's log goes beside its records (#280) |
| [`verification-gate.md`](verification-gate.md) | verification gate, slice 1: the local command |
| [`651-diagnostics-chance.md`](651-diagnostics-chance.md) | the diagnostics figure shows what overlap to expect (#651) |
| [`649-adoption-version.md`](649-adoption-version.md) | the adoption figures declare their model version (#649) |
| [`653-baseline-power.md`](653-baseline-power.md) | the baseline forest exposes the power behind Inconclusive (#653) |
| [`647-baseline-forest.md`](647-baseline-forest.md) | the actuarial baseline verdict as a forest (#647) |
| [`618-621-caption-clarity.md`](618-621-caption-clarity.md) | the cold-read caption fixes, prose only (#618–#621) |
| [`611-figure-boilerplate.md`](611-figure-boilerplate.md) | one CLI and one test loader for the figure scripts (#611) |
| [`610-diagnostics-figures.md`](610-diagnostics-figures.md) | the D2 feature-ranking readings as one panel (#610) |
| [`609-adoption-figures.md`](609-adoption-figures.md) | the adoption picture in two figures, and a stale claim it corrects (#609) |
| [`607-verdict-figures.md`](607-verdict-figures.md) | the two closing verdicts get forest plots drawn from committed evidence (#607) |
| [`597-actuarial-baseline.md`](597-actuarial-baseline.md) | the actuarial baseline: TabPFN vs GLM and CatBoost (#597) |
| [`572-row-scale-frequency.md`](572-row-scale-frequency.md) | the row-scaling arm on `frequency_french` (#572) |
| [`572-row-scale-outcome.md`](572-row-scale-outcome.md) | the row-scaling arm's outcome (#572) |
| [`492-cold-read.md`](492-cold-read.md) | the cold read, and what it found |
| [`490-evidence-map.md`](490-evidence-map.md) | an evidence map for the run trees |
| [`489-claim-registry.md`](489-claim-registry.md) | the findings registry becomes a pointer, and stops being able to drift |
| [`488-front-door.md`](488-front-door.md) | the front door becomes one route |
| [`487-phase2-report.md`](487-phase2-report.md) | the Phase 2 closing report |
| [`450-seed-range-and-preregistration.md`](450-seed-range-and-preregistration.md) | a seed range, and a pre-registration the record names (#450) |
| [`444-spanish-cell.md`](444-spanish-cell.md) | the Spanish lapse cell: leak-safe data, a pre-registered probe, and a resolution gate |
| [`443-retro-process-lessons.md`](443-retro-process-lessons.md) | the 2026-11-05 paid-run retro's process lessons (#443) |
| [`436-d18-evidence.md`](436-d18-evidence.md) | commit the evidence D18 cites |
| [`434-paid-run-rules.md`](434-paid-run-rules.md) | the rules for running many paid launches (#434) |
| [`430-batch-harness.md`](430-batch-harness.md) | a self-healing batch harness: the missing set is the queue (#430) |
| [`429-verify-seeds.md`](429-verify-seeds.md) | a batch verifies the seeds it actually wrote (#429) |
| [`407-export-records.md`](407-export-records.md) | a diagnostics record becomes a table a reviewer can open (#407) |
| [`397-decision-catchup.md`](397-decision-catchup.md) | the repository states the decision it has made (#397) |
| [`396-398-prereg-and-verdict.md`](396-398-prereg-and-verdict.md) | the pre-registration and the verdict tool (#396, #398) |
| [`377-lapse-students.md`](377-lapse-students.md) | measure the lapse GBDTs instead of estimating them |
| [`341-pilot-disposition.md`](341-pilot-disposition.md) | the pilot's disposition, and the pre-run documents |
| [`296-significance-marker.md`](296-significance-marker.md) | the significance marker agrees with its own bounds (#296) |
| [`159-zero-inflation-port.md`](159-zero-inflation-port.md) | the zero-inflation study lands on the current layout (#159) |
| [`159-zero-inflation-hurdle.md`](159-zero-inflation-hurdle.md) | hurdle models in the zero-inflation study (#159) |
| [`runner-onramp.md`](runner-onramp.md) | the runner's on-ramp is one page, and the indexes tell the truth (#575) |
| [`416-ledger-migration.md`](416-ledger-migration.md) | the cost ledger migrates instead of quarantining (#416) |
| [`docs-experiment-first.md`](docs-experiment-first.md) | group the documentation by experiment (#595) |

## Proposed — 12 plans

| Plan | What it settles |
| --- | --- |
| [`679-launch-citation.md`](679-launch-citation.md) | the citation gate accepts a committed launch tree (#679) |
| [`chunk-transport-under-stalls.md`](chunk-transport-under-stalls.md) | the chunked transport under a stalling poll (#566) |
| [`fairtest-capture-transport.md`](fairtest-capture-transport.md) | the fair test ships its captures (#564) |
| [`freq-sev-implementation.md`](freq-sev-implementation.md) | implementing the frequency/severity fair test |
| [`regressor-benchmark-fit.md`](regressor-benchmark-fit.md) | the benchmark fit that sizes the fair test's spend |
| [`regressor-benchmark-probe-path.md`](regressor-benchmark-probe-path.md) | let the paid path carry the benchmark measurement |
| [`regressor-fair-test-runner.md`](regressor-fair-test-runner.md) | the regressor fair-test runner |
| [`rescore-capture-discovery.md`](rescore-capture-discovery.md) | restore capture discovery in the alt-metrics rescore |
| [`528-pinned-offer-cuda.md`](528-pinned-offer-cuda.md) | a pinned offer declares its CUDA, and the box kernel-tests torch |
| [`668-cross-task-ledger.md`](668-cross-task-ledger.md) | the runs ledger covers regression as well as classification (#668) |
| [`671-eligible-rows.md`](671-eligible-rows.md) | the runs ledger says how much data existed, not only how much was trained on (#671) |
| [`665-finetuning-runs-ledger.md`](665-finetuning-runs-ledger.md) | one generated ledger of every committed fine-tuning run, arm and seed (#665) |

## Historical or unclassified — 2 plans

| Plan | What it settles |
| --- | --- |
| [`document-authority-amendments.md`](document-authority-amendments.md) | the document-authority amendments |
| [`experiment-spec-handoff.md`](experiment-spec-handoff.md) | Handoff — experiment spec (architecture candidate 1) |


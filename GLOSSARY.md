# tabular-foundation-model

TabPFN against actuarial baselines on insurance datasets. This glossary covers the
analysis pipeline — the suite under `scripts/eval/insurance_benchmark_v1/` and the
committed evidence it produces. The fine-tuning pilot at the bottom is a separate
context that happens to share a word.

## Analysis pipeline

**Experiment**:
A declared configuration with a stable id: one dataset, its seed and fold count, the
methods compared, the metrics, and the model version. Its identity lives in the
committed spec file, once.
_Avoid_: setup, config, case

**Run**:
One execution of an experiment, producing one output directory with its manifest.
Re-running an experiment makes a second run of the same experiment.
_Avoid_: experiment, job, trial

**Sweep**:
A set of runs over one varied axis — training size, seed, or reframing.
_Avoid_: batch, grid

**Method**:
One predictor under comparison inside an experiment.
_Avoid_: arm, model

**Model version**:
The TabPFN model a number was measured against. A number is meaningless without it,
and it is recorded, never inferred.
_Avoid_: model, version, model path

**Dataset**:
A named table plus its target, its leak-drops and the metric applied to it. Declared
once and referenced by name.
_Avoid_: table, file, corpus

**Capture**:
The persisted per-fold predictions and true labels from a run, keyed by dataset, seed
and model version.
_Avoid_: prediction file, checkpoint, dump

**Rescore**:
Recomputing metrics from a capture, without refitting anything.

**Reuse**:
Taking rows from a sweep's result table instead of refitting. Legal only while the
row's recorded provenance matches the experiment being run.

**Provenance**:
The identity a number was produced under: dataset, seed, fold construction, model
version, and git sha. When an artifact's recorded provenance contradicts itself, that
is a bug in the artifact, not a stale comment.

**Record**:
The file a run writes to describe itself: one top-level `provenance` block with the same
four sections — dataset, split, model, code — whatever produced it. A per-dataset record
(an arm run, a capture) holds one dataset; a run-level record holds a list of them, and
that is the only structural difference allowed.
_Avoid_: metadata, sidecar, output

**Verdict**:
What a record can prove: `comparable`, `partial` or `unusable`, with the missing keys
named. Computed from the record, never written into it by the writer — a record cannot
claim to be comparable while missing the field that makes a comparison meaningful.
_Avoid_: status, score, pass/fail

**Frontier**:
The set of methods on a dataset that are not dominated. A is dominated iff some B with
strictly fewer parameters has `mean_B + SE_B < mean_A − SE_A` (the D3 rule). Within-SE
methods both stay on it.
_Avoid_: leaderboard, ranking, best-of

**Frontier membership**:
Whether a method is on the frontier for a dataset. Decided by the D3 rule only — a
point-estimate comparison lets fold noise decide.
_Avoid_: winner, ranking

## Fine-tuning pilot

**Arm**:
One training configuration under test in the fine-tuning pilot. Distinct from a
method: it varies how a model is trained, not which predictor is compared.
_Avoid_: method

The pilot's prose predates this glossary. New text in the analysis pipeline uses
_method_; _arm_ stays where it already means a training configuration.

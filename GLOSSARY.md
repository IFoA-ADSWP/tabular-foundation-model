# tabular-foundation-model

TabPFN against actuarial baselines on insurance datasets. This glossary covers three
contexts that share words: the analysis pipeline — the suite under
`scripts/eval/insurance_benchmark_v1/` and the committed evidence it produces; the
fine-tuning pilot; and the paid-run path that rents the machines both of them run on.

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

## Paid-run path

**Launch**:
One rent of a remote machine for one purpose, from the decision to spend until the
machine is gone. It owns one cost record and one identity, and contains zero or
more runs. Committed `run_*.json` files and the ledger predate this word: they call a
launch a run and are not renamed.
_Avoid_: job, session, attempt

**Launch id**:
The name a launch is known by everywhere it is recorded or referred to. Minted before
anything is rented, so a launch that never got a machine still has one; a run that
never had a launcher is marked as local.
_Avoid_: run id, job id

**Arrival**:
The moment the artifacts a run produced are present locally and verified. A claim of
completion is not arrival; verification is.
_Avoid_: download, transfer, pull

**Spend gate**:
The decision that a launch may rent a machine, taken before anything is created. It
either allows the launch or refuses it, listing every failed check at once, and the
decision is recorded. A refusal is not a crash and not a transport failure.
_Avoid_: gate, preflight, guard

**Dispatch**:
The paid-path seam that turns a launch's experiment — or its ad-hoc facts — into one
command document before spend. It builds and validates the command; it never decides
what an experiment is.
_Avoid_: runner, launcher, job builder

**Command document**:
The versioned JSON a launch sends to the box: launch id, experiment id or ad-hoc facts,
pinned commit, image, and the declared-arm subset. It carries no secret and no machine
identity; the box re-validates it and expands it into runs.
_Avoid_: payload, config, script

**Ad-hoc run**:
A paid run with no declared experiment: its dataset, arms, seed and row sizes are stated
explicitly. It is recorded as ad-hoc and never stamped with an experiment id.
_Avoid_: custom run, manual run

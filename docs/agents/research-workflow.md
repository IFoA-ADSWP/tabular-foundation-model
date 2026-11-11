# Research workflow

This repo produces verdicts, not only features. The engineering skills assume a
change whose behaviour is known; a research question's outcome is not. Keep the
two lanes separate, and say which lane a change is in when you name it at the
flow gate.

## Two lanes

**Engineering lane** — harness, loaders, pipeline code, tests, CI. The normal
flow applies: spec, tracer-bullet tickets, TDD, code review, land. A green gate
means the code does what it says.

**Research lane** — a question, a protocol, a run, a verdict. The gate is a
pre-registered bar, not a test suite. `wayfinder` maps the questions; one
protocol ticket carries one experiment.

## A protocol ticket

Before the run, a research ticket carries:

| Field | What it holds |
|---|---|
| Hypothesis | One falsifiable sentence. |
| Bar | The pre-registered threshold, with the noise floor it must clear. |
| Falsifier | The result that would refute the hypothesis. |
| Analysis plan | The comparison, the seeds or folds, and the decision rule. |
| Run record | Command, revision, environment, and the path to the artifact. |
| Verdict | `CONFIRMED`, `REFUTED`, `UNRESOLVED`, or `UNTESTED`. |
| Decision | The thing that changes if the verdict lands. |

A ticket is `ready-for-agent` only when the first four fields are present and
the run is mechanical. An agent executes the protocol; it does not choose the
hypothesis, set or move the bar, or interpret an ambiguous result.

## Verdicts

- **CONFIRMED** — the bar was met under the pre-registered analysis.
- **REFUTED** — the bar was missed or the falsifier was hit. Recorded and
  closed. Do not re-scope the question to make it pass.
- **UNRESOLVED** — the run completed, but the measurement cannot separate the
  hypotheses at the observed noise.
- **UNTESTED** — not run. Parked with the reason, and the bar stays on record.

A moved bar is a new ticket, not an edit to an old one. One verdict per ticket.
A REFUTED result is an outcome, not a failure, and is as worth publishing as a
positive one.

## What does not apply

- TDD for exploratory probes: there is no known behaviour to assert.
- A passing CI gate as evidence of a result: it proves the code, not the claim.
- "Done" as a merged change: for research, done is a recorded verdict,
  including a negative one.

## Records

Keep the run record with the artifact and link it from the ticket. A number
without a command, revision, and environment cannot be reproduced, so it is not
evidence. State the noise floor before comparing anything; a ratio of means
reads like a finding whether or not it is one.

## Agents

- **May:** execute a pre-registered protocol, regenerate an artifact, verify a
  run record, and update links.
- **May not:** pick the question, set or move a bar, choose the analysis after
  seeing the data, or declare CONFIRMED on a result inside the noise.
- **Must:** record UNTESTED rather than silently dropping a planned run.

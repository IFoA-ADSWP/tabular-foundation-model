# Coding standards

What **review** enforces that a machine cannot. `AGENTS.md` carries the process rules and the
commands; this file carries only the judgement calls, and says so in one place rather than two.
It is read during review, not while writing, so it stays out of an implementer's context.

A rule earns its place by having been raised in review. Each cites the finding that motivated
it, so a rule with no finding behind it can be retired rather than inherited.

## A declared field is enforced, or scoped where it is recorded

*Raised in the #230 review, twice in one pass: `n_folds` was declared and validated but never
read, so a ten-fold experiment would have run five and still stamped its id; and
`model_version` was recorded in the run manifest without saying what it attested.*

If a declaration names a field, the run honours it or the artifact states the limit. A field
that is neither is a stamp the artifact cannot back — the mechanism behind what `GLOSSARY.md`
already calls "a bug in the artifact" under *provenance*. The glossary names the symptom; this
is the rule that prevents it.

**Reviewer's test:** for every field the change adds to a declaration or an artifact, name the
code path that reads it, or the scope note that limits it. "It is only a record" is the
answer that should fail.

## A parameter that crosses a seam is *forwarded*, not re-defaulted

*Raised by three findings in one day, 2026-11-06: `bootstrap_pilot.sh` accepted `--seeds` and
dropped it before the runner (#454); a diagnostic's `main` accepted `--seed-range` and dropped it
before `measure`, so a 66-seed request ran five and wrote a plausible record; and
`TFM_EXPECT_CHECKPOINT` was never forwarded by the launcher at all, so the box asserted its own
default — which made D18's "asserted before every launch" an assertion of the default, not of the
claimed line.*

A value crossing a seam — launcher to box, CLI to library, `main` to a worker — either arrives or
stops the run. It does not quietly become the callee's default. The failure is invisible from both
ends: each side is individually correct, the run succeeds, and the record describes an experiment
nobody asked for.

The mechanical half is now a check: `tests/test_pilot2_seed_passthrough.py` asserts that every
variable the box reads is either forwarded by the launcher or on a named list of launcher-owned and
box-enforced names, and that no forwarded name is dead. The judgement half is what review adds:
**a new seam gets a wiring test at that seam**, not an end-to-end test that happens to cover it.

**Reviewer's test:** name the call site that receives the value. If the answer is "it is in the
environment" or "it is on the object", that is the belief to check, not the answer.

## Tests sit at a named seam

*Raised in the #230 review: coverage was argued per file rather than per boundary.*

A test targets an interface a caller could use — a loader, a CLI, a stamped artifact. It does
not reach into a private helper, and it does not assert a value it recomputed the same way the
code does. Where the seams are not obvious, name them before writing tests.

## How this file grows

A **mechanical** finding — a banned construct, an import shape, a file-location rule — gets a
check, not a paragraph: the gate script (#257) or the lint pass (#258), whichever is cheaper.
This file is for judgement calls that no guardrail can substitute for.

Promote a judgement call here once review has raised it repeatedly. Two instances in one pass
counts, as it did for the first rule; one passing mention does not.

## A cost or availability claim cites its measurement

*Raised in the 2026-10-30 campaign review, twice in one pass: D2's "the models are already
committed" (only prediction arrays were — nothing loadable), and D3's "analysis only, $0" (true
for the one dataset already run; the reframe fits nine methods through the hosted client for any
other). Both sat in signed documents, and both changed what got scheduled.*

A claim about cost, availability, runtime or what a repository already contains is a fact about the
world, not a preference. Cite the measurement, the file, or the command that establishes it — or
write **unmeasured**, so the next reader knows to measure before relying on it.

**Reviewer's test:** for every such claim the change adds or leans on, ask for the file, the figure
or the command. "It says so in the design document" is the answer that should fail; the design
document is where the claim was written, not where it was checked.

## A result quotes the analysing tool, not a hand-assembled summary

*Raised in the #436 review of the D18 result, and again in the 2026-11-05 retro (#443): the document
reported mean +0.0009, between-seed SD 0.0081 and a 129-seed requirement — the 228-seed pool that
existed before the final ten-seed batch landed — beside a count of 134/238 from the full pool. The
committed evidence gives +0.0007, SD 0.0082 and 132 seeds. The reading was unchanged, but a signed
document disagreed with its own evidence until the capture was committed.*

The figures in a result document come from **one run of the analysing tool over the final evidence**,
and the document carries the command that produced them. A figure copied from an earlier pool, or
assembled from several runs, is **unmeasured** in the sense above — regenerate it or say so. Where the
evidence supports it, a test parses the document and reproduces the mean, SD and interval, as
`tests/test_d18_evidence.py` does; this rule covers the figures no test can reach.

**Reviewer's test:** ask for the command behind every figure. A document that cannot name one run of
the tool over the final evidence is quoting something other than its evidence.

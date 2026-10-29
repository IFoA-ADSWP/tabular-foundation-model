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

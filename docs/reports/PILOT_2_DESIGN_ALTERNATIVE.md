# Pilot 2 — alternative design: staged isolation

**This is an alternative to the design in `PILOT_2_DESIGN.md`, not a revision of it.** It differs in
kind, not just in budget: it changes **one factor at a time** and treats every step as a screening
question with its own stop rule. The design in `PILOT_2_DESIGN.md` changes several factors together
and reads the result at the end.

## Why an alternative is worth considering

The concern is analytic, not financial. **`PILOT_2_DESIGN.md` varies three things at once** — the
number of repeats, the training length, and the data scale — across two experiments (in-domain and
transfer) with two pool policies and a control. If the result comes back negative, the negative is
**ambiguous**: it could be the epoch budget, the pool's composition, the scale, or the repeat
structure, and the design cannot tell us which.

**This project has already paid for that mistake once.** The historic fine-tuning verdict — "do not
chase fine-tuning" in the master report — came from a comparison whose inference context was not
matched between arms. The arms differed in more than one way, so the negative was uninterpretable,
and it took the first pilot to establish that the comparison had been confounded. A design that
varies several factors at once reproduces that risk at a larger price.

## The two designs

| | **A. As specified** (`PILOT_2_DESIGN.md`) | **B. Staged isolation** (`PILOT_2_DECISION_GRAPH.md`) |
| --- | --- | --- |
| Factors varied at once | repeats, epochs, rows, pool policy | **one per step** |
| Order | all arms, all stages, then read | each step gated on the last |
| A negative means | the combination failed — **cause unresolved** | *this factor* failed — a specific, reportable claim |
| Comparisons per read | ~24 across datasets, epochs, targets and policies | **one** |
| Multiplicity | large surface, and the Gate 1 criteria add more | one hypothesis per step, so no correction needed |
| Cost to a first answer | ~$31 (as written), ~$368 at full scale | **~$4.70**, or ~66c if the probe says 3 epochs is enough |
| Repeat structure | 3 seeds x 5 folds throughout | 3 seeds x 1 split first; **5 folds only after an effect exists** |
| When a result is reportable | at the end | **after every step** |

## Why the analysis is easier

1. **One hypothesis per step.** Each step compares a single pair — the fine-tuned arm against raw
   TabPFN, on one dataset, at one budget. The decision rule is a paired comparison with a known
   noise floor, not a criterion across four datasets and two stages at once.
2. **A null is interpretable.** "Fine-tuning at 30 epochs on a coherent pool does not beat raw
   TabPFN on this target" is a usable finding. "The pooled arms were negative in a run where the
   epoch budget was also set wrong" is not.
3. **Multiplicity stops being a problem.** Design A tests roughly two dozen comparisons at once
   across datasets, epochs, targets and policies, and then applies Gate 1's criteria on top. Design B
   tests one, so no correction is needed and no result has to be discounted for the number of others
   examined.
4. **Screening is separated from estimation.** Step 0-4 are *screening*: does an effect exist, and is
   it bigger than the measured noise? Step 5 is *estimation*: how large is it, with what interval?
   Mixing the two is what makes bundled designs hard to read.
5. **Every step produces a reportable outcome.** The analysis does not depend on the last run. If
   the programme stops at step 2 or 3, the work still yields a defensible statement.

## What isolation costs us

Stated plainly, because it is a real trade:

1. **Interactions are not detected.** Design A could in principle find that training longer helps
   *only* under a coherent pool. Design B will not: it tests training length in-domain, and pool
   composition later, but not their combination. If an interaction is the actual phenomenon, B
   misses it.
2. **The first passes are screening, not definitive.** One split with three seeds bounds the effect
   loosely. The precise figure still requires step 5, and step 5 is only bought if the screening
   passes.
3. **The steps are sequential, so a late answer depends on early ones.** A stopping rule at step 2
   means the transfer question is answered later than it would be in Design A — or not at all, if
   Stage 1 is negative.
4. **Isolation invites peeking.** Stopping when a result looks good is a way to manufacture a
   finding. This is why every step's decision rule and the noise floor must be **fixed in advance**,
   and the stop rules in `PILOT_2_DECISION_GRAPH.md` are written to be pre-registerable.

## Interaction policy — by decision, with a stated mechanism

**Isolation by default. An interaction is investigated only when it is entered deliberately, and only
with a technical reason for expecting it.**

The reason is attribution. The bundled design *is* an interaction measurement — but an **incidental**
one. With repeats, training length, data scale and pool policy all moving across its arms, a positive
result cannot be attributed: two factors are jointly the possible cause, and the design offers no
contrast that separates them. That is the "A and B as possible causation" problem, and it is not
fixed by running more repeats.

An interaction is a legitimate and interesting question — **two factors can each be null in isolation
and positive in combination.** The point is not to rule such questions out, but to design them.

### Entry criteria — all four must hold

1. **A stated technical mechanism.** Not "it might work", but *why the combination should differ from
   the sum of its parts*. For example: *"training longer should help more under a coherent pool,
   because the gradient signal is not diluted by schema-mismatched columns."* If the mechanism cannot
   be written in one sentence before the run, the hypothesis is unfalsifiable and must not be run.
2. **It is implied by the isolation results.** At least one factor shows an effect, or two are
   near-misses *in the direction the mechanism predicts* — for example each alone is +0.002 against a
   noise floor of 0.003, and the mechanism names the threshold the combination should cross.
3. **A design that can attribute it.** A contrast between cells that differ in **exactly** the factors
   of interest, with everything else held fixed. Never "everything at once".
4. **Pre-registered.** The interaction being tested, the expected direction, the arms, the decision
   rule and the stop rule, all fixed before the run. Without this, an interaction search is fishing.

### Cost of a designed probe

The most plausible interaction here is **training length x pool coherence**, testable as a 2x2 on a
single target:

| | in-domain | pooled (3 datasets) |
| --- | --- | --- |
| **3 epochs** | 29 s | 73 s |
| **30 epochs** | 225 s | 659 s |

Plus the shuffled-label control at both pooled cells (1,464 s).

**3 seeds, one split: $1.11.** At 5 folds: $5.55.

### Why it must be entered deliberately: it is the most expensive claim available

In a 2x2 with equal cells the interaction contrast is a *difference of differences*, whose variance is
**four times** a single cell's. It therefore needs roughly **four times the repeats for the same
precision as a main effect**. An interaction is the hardest thing in this programme to establish.

Which gives the comparison in one line:

- **Designed interaction:** $1.11 for a specific, attributable answer to a question with a stated
  mechanism.
- **Incidental interaction:** $31 for an answer with two factors jointly to blame and no contrast to
  separate them.

Whatever the outcome, an interaction result is reported as an **estimate with an interval**, never as a
headline.

## Which to choose

Design B is the better default **if the goal is to learn what is true**. Design A is defensible
**if the goal is to produce a single definitive number** and the budget is not binding. Given that
the historic confound is the reason this pilot exists, and that Design B reaches the same decisions
for roughly **$4 instead of $31**, the isolation design is the stronger recommendation — with the
caveat that it will not detect interactions, and should say so when it reports.

**They are not mutually exclusive.** Design B's step 5 is Design A's core comparison: if the
screening steps pass, the programme arrives at the full design having already established that each
factor matters — which is a better position from which to spend the larger budget, not a retreat
from it.

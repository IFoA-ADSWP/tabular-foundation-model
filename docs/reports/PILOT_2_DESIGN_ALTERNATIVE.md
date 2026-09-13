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

| | **A. As specified** (`PILOT_2_DESIGN.md`) | **B. Staged isolation** (`PILOT_2_EXECUTION_PLAN.md`) |
| --- | --- | --- |
| Factors varied at once | repeats, epochs, rows, pool policy | **one per step** |
| Order | all arms, all stages, then read | each step gated on the last |
| A negative means | the combination failed — **cause unresolved** | *this factor* failed — a specific, reportable claim |
| Comparisons per read | ~24 across datasets, epochs, targets and policies | **one** |
| Multiplicity | large surface, and the Gate 1 criteria add more | one hypothesis per step, so no correction needed |
| Cost to a first answer | ~$31 (as written), ~$367 at full scale | **~$4.15**, or ~$0.58 if the probe says 3 epochs is enough |
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
   and the stop rules in `PILOT_2_EXECUTION_PLAN.md` are written to be pre-registerable.

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

# TabPFN-3.5 Hackathon — idea log and decision record

> **Status:** living document, opened 2026-09-17. This is the working page: ideas, scores, the lead
> candidate and what still needs deciding. Event facts and the event-level assessment live in
> `HACKATHON_ENTRY_ASSESSMENT.md`; nothing here is a commitment until it appears in the decision log at
> the foot of the page. **What the entry actually shows — beat by beat, with the claims and what would
> falsify them — is in `HACKATHON_WHAT_WE_SHOW.md`.**

## 1. The brief, as constraints

Every idea below is scored against these, because most of them are eliminable on rules alone.

| | |
|---|---|
| Window | Submissions open 15 Sept 2026 00:00 CEST, **close 6 Oct 2026 23:59 CEST** — 19 days from today |
| Who | Individuals, 18+, one Prior Labs account; entries are tied to the account |
| Entry = | (i) a link to a **public** source-code repository, and (ii) a description a third-party developer can follow |
| Licence | The repository must be released under **Apache License 2.0** |
| Reproducibility | Code and instructions to run it, and the input data included **or available at a public URL** |
| Model | Built with **TabPFN-3.5**; other models and tools allowed provided 3.5 is a core part |
| Multiplicity | More than one project may be submitted; each is judged separately; the latest version of an entry counts |
| Credits | The API is free with a limited default allowance; **extra credits are granted on joining the Hackathon** and submitting a request |
| Sharing | Prior Labs may share the project publicly with attribution |
| Prizes | 1st NVIDIA DGX Spark · 2nd NVIDIA Jetson AGX Orin 64GB · 3rd RTX 4090 · honourable mentions are recognition |

**Judging: Showcase of TabPFN-3.5 50% · Creativity and originality 30% · Technical quality and
reproducibility 20%.**

### Two readings of the rubric that shape every idea

1. **The 50% is about the model, not the domain.** It reads "how prominently and effectively the project
   uses TabPFN-3.5 and how convincingly it demonstrates the model's capabilities in a working prototype".
   That rewards a **capability tour with a domain spine** — exercise several distinct 3.5 capabilities and
   say what each one buys — over one clever pipeline that happens to use the model well.
2. **Creativity is 30% and it includes practical value.** The best-scoring domain is therefore one where
   the *standard method is not machine learning at all*, so the reframing itself is the contribution,
   while the data stays public and reproducible. That is a narrow door, and it is the door we are standing
   in front of.

## 2. Candidate ideas

Scored against the weights, not against our enthusiasm. Feasibility assumes ~2–3 focused days spread over
the 19-day window.

| # | Idea | Tracks | 3.5 capabilities shown | Creat. (30) | Show. (50) | Repro (20) | Verdict |
|---|---|---|---|---|---|---|---|
| **1** | **Reserving as a prediction problem** — turn a loss triangle into a supervised task and produce a full reserve distribution | Formalize a new problem · Take on a hard problem · Showcase a harness | default predict · predictive distribution · Thinking mode · calibration · KV-cache speed · relational (RPI) upstream | High — reserving is *not* an ML task in practice; the standard is Chain Ladder / Mack | High — five or six distinct capabilities on one spine, each with a named job | High — public triangles, `chainladder` (the CAS-act package) as the baseline | **Lead** |
| 2 | Relational insurance portfolio through TabPFN-Rel / RPI / RelArena-α | Showcase a harness · Formalize a new problem | 3.5 through their own harness, anchor-dated | Med-high — uses their harness, so the idea is partly theirs | High — their flagship new capability, on a domain they sell into | Med — the "database" must be constituted from CSVs, and the harness is alpha | Strong second; **folds into 1** as the upstream layer |
| 3 | Actuarial analyst agent — profiles a portfolio, picks the framing (including the count→classification reframe), fits, calibrates, writes the memo, and says when not to use TabPFN | Build an agent | default · calibration · reframe · interpretability | Med — agents are crowded; the differentiator is the measured decision rule as policy | Med-high | High — a script and an API key | Reserve; the decision-rule-as-policy angle is genuinely ours |
| 4 | Domain MCP server / app exposing actuarial prediction tools | Build an extension or app | default · reframe · calibration | Med — MCP servers are common, a domain one is not | Med | High | Cheap to ship as a **second entry** if the lead lands early |
| 5 | Harness showcase: the 3.5 version-drift re-test, public and reproducible, with the adoption decision rule | Showcase a harness | default · Thinking · calibration, with elo/time Pareto fronts | Low — it is our existing work, repackaged | Med-high — honest, thorough, and exactly the repo's culture | Very high — everything already exists | **Fallback and evidence base**; a plausible honourable mention |
| 6 | Synthetic insurance portfolios via 3.5 data generation, with a privacy/utility case | Your idea · Take on a hard problem | data generation · predictive distribution | Med-high — data sharing under GDPR is a real actuarial blocker | Med — one capability, demonstrated | Med — utility metrics are fiddly to make convincing | Interesting, second-order; keep on the list |
| 7 | Mortality / annuity: a lifetable as a survival prediction task | Formalize a new problem | default · predictive distribution | Med — adjacent to reserving, same shape of reframing | Med | High | Same skeleton as 1 with a smaller payoff; park |
| 8 | The roadmap's untreated sets — telematics, catastrophe, large loss | Take on a hard problem | default · predictive distribution | Med | Med | Med — licence and size risk on several of these | Park; useful for the paper later |

## 3. The lead, settled: *the reserve as a distribution* — TabPFN-3.5 on loss triangles

> **Settled 2026-09-17, subject to your sign-off.** The idea survived the two checks that could have killed
> it — whether our own reserving verdict contradicts it, and whether the model and the data are actually
> available. Both are answered below with evidence rather than assurance.

**The reframing is the idea.** Loss reserving is the actuarial task that is least like machine learning: an
actuary arranges past claims into a triangle of accident periods by development periods, picks development
factors, and runs the arithmetic. Uncertainty is bolted on afterwards by an analytical formula (Mack) or a
bootstrap. Nobody treats the triangle as a table to be predicted.

Presented as a prediction problem, every cell of the lower (unobserved) triangle is a supervised target:
features are the accident period, the development period, the cumulative paid and incurred to date, and the
development factors implied so far — using **only data that would have been available at the valuation
date**, which is the same anchor-time discipline the relational harness enforces. The reserve is then the
sum of the predicted cells, and 3.5's predictive distribution turns that sum into a distribution rather
than a standard error.

### The capability tour — one spine, six capabilities, each with a named job

| # | Capability | The job it does here |
|---|---|---|
| 1 | Default prediction | Point estimate for every unobserved cell → the reserve |
| 2 | **Predictive distribution** | The reserve as a distribution: percentiles, not just a Mack standard error |
| 3 | **Thinking mode** | The late-development and thin cells, where the signal is weakest |
| 4 | Calibration | Interval coverage: do the 90% intervals contain the truth 90% of the time? This is the honest test |
| 5 | Fast / KV cache | The workbench angle: reserve many triangles in the time one takes today |
| 6 | Relational harness (stretch) | The triangle is a *summary* of a policy/claim/payment database — run the upstream claim data through TabPFN-Rel with an anchor date and let the harness build the features |

**Baselines that make it credible rather than promotional:** `chainladder` — the CAS Actuaries' own Python
package (MPL-2.0, `github.com/casact/chainladder-python`) — supplies Chain Ladder, Mack and bootstrap ODP.
If 3.5 is compared only against itself, the entry has no argument.

**The honest claim, which is also the most credible one:** *a reserve with a full predictive distribution,
computed in seconds on a triangle of any shape, with no model fitting and no distributional assumption —
and a straight answer on where the actuarial standard still wins.* The rubric asks for a convincing
demonstration of the model's capabilities, not a victory lap; on this repo's own evidence, half the value
of the story is in the comparison.

### Why this does not contradict our own reserving verdict

`RESERVING_WITH_FOUNDATIONAL_MODELS.md` concludes "do not deploy for severity" — but that verdict is about a
**different statistical object**: flat, claim-level regression on 163K–678K zero-inflated rows. A triangle is
not that. A 10×10 triangle has ~55 observed cells; even a 20×20 has ~210. That is squarely inside the regime
our own decision rule says TabPFN wins (≤ ~5K rows; 8/9 size-sweep cells), and the zero-inflation trap does
not arise on cumulative cells. So the honest framing is not a reversal, it is a **scope correction**: we are
the people who said do not use it for this — the triangle was never the object we tested. Testing it *is* the
entry.

### Feasibility, checked rather than assumed (2026-09-17)

| Question | Answer | Evidence |
|---|---|---|
| Does "built with TabPFN-3.5" mean pip or API only? | `pip install tabpfn` → **9.0.0, uploaded 2026-09-15**, the day 3.5 shipped. The 3.5 family is Base, Plus, Thinking, Fast (alpha) | PyPI release metadata; `docs.priorlabs.ai/models.md` |
| Does the model give a *distribution* cheaply? | `TabPFNRegressor.predict(X, output_type="full")` returns the full predictive distribution **in a single forward pass, at no extra inference cost** — quantiles, skew and multimodality exposed | `docs.priorlabs.ai/capabilities/predictive-distribution.md` |
| Is there a credible baseline tool? | `chainladder` — the CAS Actuaries' own Python package (MPL-2.0): ChainLadder, MackChainLadder, BootstrapODPSample | `github.com/casact/chainladder-python` |
| Is there public triangle data, in volume? | Yes: `cl.load_sample()` bundles the **CAS Loss Reserve Database** (`clrd` — Meyers/Shi, NAIC Schedule P, ~200+ insurers × 6 lines) plus the classics (`abc`, `genins`, `mcl`, `ukmotor`, `m3ir5`) | chainladder sample-data docs; CAS research resources |
| Which data licence applies? | The CAS LRD is published for reserving studies; the entry **downloads rather than vendors** it, with a URL and a hash — which also satisfies clause 3.2 | T&C 3.2 |

### The claim the entry makes

*An actuarial reserve with a full predictive distribution, computed in a single forward pass, on a triangle of
any shape — against a standard that obtains the same distribution from a thousand simulated refits.*

That is the sentence the 50% is looking for: a capability statement about 3.5, not a domain essay. The second
half of the entry is the measurement — a fleet backtest over the CAS database with interval coverage and
wall-clock timings — so the claim arrives with numbers and an honest read on where Chain Ladder still wins.

**Prior art, stated so the creativity claim is not overstated:** machine learning for *individual* claims
reserving is an active literature (Richman & Wüthrich, arXiv 2602.15385; transformer/LSTM individual reserving
at JSM 2026). What is not done — and what this entry does — is a **tabular foundation model, zero-shot, on the
development-cell formulation, with a predictive distribution, benchmarked against Chain Ladder / Mack / ODP
across a public triangle database**.

**Data:** public triangles via `chainladder`'s loader — the CAS LRD for the fleet backtest, and `abc`,
`genins`, `mcl`, `ukmotor` for the readable worked examples. Downloaded at run time with a URL and a hash.
Nothing from the working party's own portfolios is needed, which keeps the rights certification in clause 3.3
simple.

### Scope ladder — MVP first, each rung shippable

| Rung | Contents | Effort |
|---|---|---|
| **MVP** | One triangle (`abc`), the reframing written down, Chain Ladder vs 3.5 default, and the **reserve distribution** from `output_type="full"`; one notebook; a README that runs | ~1 day |
| **v1** | The **fleet backtest** over the CAS LRD: reserve error against Chain Ladder, **interval coverage**, wall-clock against the ODP bootstrap; a Thinking-mode arm on the late and thin cells; a Fast arm for the fleet | +1 day |
| **Stretch** | A CLI that reserves a folder of triangles; the relational upstream via RPI (claims database → anchor-dated features); a written "what it unlocks" page for reserving actuaries | +1 day |

Submit at MVP if the clock runs short; the deadline does not move, and updates are allowed until close.

### The repository — separate, public, Apache-2.0

**Created: `IFoA-ADSWP/tabpfn-reserving`** — public, Apache-2.0, in the same org as this repository
(2026-09-17). It carries `README.md`, `docs/method.md`, `docs/brief.md` and `requirements.txt`; the code
lands with the spike. The intended shape:

```
tabpfn-reserving/                 Apache-2.0, public
├── README.md                     what it is, quickstart, results table, acknowledgements
├── LICENSE                       Apache-2.0
├── pyproject.toml                tabpfn>=9.0.0, chainladder, pandas, matplotlib
├── src/tabpfn_reserving/         triangle → cells, anchor-time split, the TabPFN arm,
│                                 the reserve distribution, the backtest
├── notebooks/quickstart.ipynb    Colab-runnable: one triangle end to end, distribution plotted
├── scripts/fetch_data.py         downloads the public triangles, records URLs and hashes
├── results/                      the backtest outputs the README quotes
└── docs/what_it_unlocks.md       the reserving-actuary page, including where Chain Ladder still wins
```

Three things in that layout answer the rubric directly: the **capability tour is the README's spine** (the
50%), the **reframing plus the prior-art note** is the originality claim (the 30%), and **one command
reproduces the table** (the 20%). The name and the owner are the two parts I cannot choose for you.

## 4. Fallback and second entry

Multiple submissions are allowed and judged separately, so the natural pairing is **the lead (1) plus the
harness re-test (5)**: the re-test is half a day, needs no invention, and doubles as the evidence base for
every 3.5 claim in the lead. If only one entry gets finished, it should be the lead.

## 5. What we are deliberately not doing

- **A fine-tuning entry.** It needs a GPU, hours and a sponsor, and the prize is hardware we would use to
  run it — a strange loop. Out.
- **A pure Kaggle-challenge entry.** Crowded, and 3.5 would be a tool rather than the subject, which is
  backwards against a 50% weight on the model.
- **An agent as the headline.** Crowded field; we would be one more. The decision rule as agent policy is
  the only genuinely distinctive part, and it is worth more inside the lead than as its own entry.

## 6. Open questions and what needs deciding

| # | Question | Why it matters | Proposed answer |
|---|---|---|---|
| Q1 | **Who enters, and in whose name?** | The T&Cs are individual: one account, prizes shipped to one address. A working party cannot enter as such | One named individual enters; the working party is acknowledged in the README. Needs the nominee's agreement |
| Q2 | **Which repository is submitted?** | The entry must be a public repo under **Apache-2.0**. This repo is MIT, org-owned, and full of working-party material | **Done — `IFoA-ADSWP/tabpfn-reserving`**, created 2026-09-17 in the same org as this one: public, Apache-2.0 (detected by GitHub), initial commit `4dc9e72` carrying the README, the method page and the dependency list. Code is deliberately withheld until the spike has run |
| Q3 | **Which triangles, and are they publicly URL-able?** | Clause 3.2 requires the data included or public; clause 3.3 puts the rights certification on us | Start with triangles shipped by the ChainLadder R package / CASdatasets; confirm each licence before publishing, and include a download script plus a hash |
| Q4 | **The Hackathon page URL** | The T&Cs say extra API credits are granted on joining; the page as supplied had no link | **Answered: `https://platform.priorlabs.ai/hackathon-3.5`.** Retrieved 2026-09-17: the public copy confirms the six tracks and the four prize tiers, and joining is gated behind a Prior Labs sign-in — "Sign in or create a free Prior Labs account to accept the hackathon terms and submit your entries." No account exists in this environment and credentials are not entered on your behalf, so **the join, and the credits it releases, is a step for you** |
| Q5 | **Do we submit one entry or two?** | Allowed either way; two entries double the surface but halve the depth | One (the lead) until it is safe, then decide on the second |
| Q6 | **Working-party sign-off** | This uses workstream time and the working party's accumulated credibility | Put it to the group with the assessment page; the payoff is fresh reserving material for the BAJ paper's Nov–Dec stage |
| Q7 | **Whose account, whose IP?** | Clause 3.3 makes the submitter certify they hold the rights to everything published | The entry repo carries its own Apache-2.0 licence and only includes material we can publish; no client or restricted data |

## 7. Decision log

| Date | Decision | State |
|---|---|---|
| 2026-09-17 | Event facts recorded; the event-level assessment written (`HACKATHON_ENTRY_ASSESSMENT.md`) | Done |
| 2026-09-17 | Lead candidate chosen for review: reserving as a prediction problem, with the capability tour above | **For review — not yet agreed** |
| 2026-09-17 | Hackathon page located and read: `platform.priorlabs.ai/hackathon-3.5`. Public copy confirms the six tracks and the four prize tiers; joining is a signed-in action, so the extra credits are not released yet and the join is on you | Recorded |
| 2026-09-17 | Fallback / second entry: the 3.5 version-drift harness re-test, public and reproducible | For review |
| 2026-09-17 | **Lead settled: "the reserve as a distribution" — TabPFN-3.5 on loss triangles.** It survived the two checks that could have killed it: our own severity verdict concerns a different object (flat, zero-inflated, 163K–678K rows), and `tabpfn` 9.0.0 (3.5), a public triangle database and a CAS-maintained baseline are all available | **For sign-off** |
| 2026-09-17 | **Separate repository confirmed** (your call) and then created: `IFoA-ADSWP/tabpfn-reserving` — public, Apache-2.0, initial commit `4dc9e72` (README, `docs/method.md`, `requirements.txt`). The entry repo now exists and satisfies clause 3.5; the code lands with the spike | Done |
| 2026-09-17 | **Project brief initiated** in the entry repo — `docs/brief.md`, commit `7f8d41d`: objective, rubric mapping, the event as constraints, scope with an explicit out-list, deliverables with done-when, a dated plan built back from 6 Oct, pre-registered success criteria, roles and risks. The plan submits on **2 Oct**, four days early, because the latest version counts | Done |
| 2026-09-18 | **E2 first pass done** (entry repo `results/spike/FINDINGS.md`). The raw-ratio arm carries signal — it deviates 13.8% from Chain Ladder and is closer on 5 of 11 — but blows up in the tail (+594% worst case). The **Δ-to-Chain-Ladder arm reproduces Chain Ladder to 1.86%**: at 6–36 training rows per fit, no deviation is learnable, so the arm is Chain Ladder with rounding. Conclusion: **the point estimate does not beat Chain Ladder in either formulation; the distribution is the claim with evidence** — which is what `docs/method.md` pre-registered. Next: the **fleet-as-context** idea, promoted from parked to leading candidate, since it is the one way to make the deviation learnable | Recorded |
| 2026-09-18 | **Readiness assessed against the terms** (entry repo `docs/readiness.md`): **not ready, and the gap is not the science.** Three hard blockers — the entry is not joined or submitted (clauses 2.2/2.4, human-only), the clause 3.5 description does not exist, and the README's quickstart names a package that does not exist (clause 3.2). Four judge-facing gaps (no figures, no notebook, no unlocks page, no README results table). Four experiments outstanding, led by E3 over the fleet, which is what turns the n=11 coverage result into a result. **All twelve filed as issues #1–#12** in the entry repo so the ledger is a worklist | Recorded |
| 2026-09-18 | **Entry repo built out and the scientific gap closed the same day.** Package + CLI + `pyproject.toml` (clause 3.2 closed; the README's quickstart is now copied from real output), 25 tests and CI, the reserve distribution drawn from the model's own bar distribution rather than an interpolated grid — which mattered: the ratio arm's p99 was understated by 62%. Three defects found and fixed, all of one class: the delta arm's draws were never rescaled, the two reserve functions disagreed about their default target ages, and `Triangle.load` silently reduced a **collection** to its first member and `mcl` — which carries incurred *and* paid — to its first column. The scientific question ("why does the point estimate over-reserve?") is now **answered, not argued**: per-step bias is zero where the model has training rows and **+3.2% per step as it extrapolates** (287 scored steps, t≈8.7, intercept +0.0001), compounding to ×1.33 against a measured ×1.67. The trap that nearly produced a false negative is recorded too: backtests anchored near the ultimate cannot see the depths production uses, and report a flat line while doing so. Next: **#18**, delete the recursion and predict the horizon directly — capped at one implementation, one measurement, one decision | Recorded |
| 2026-09-19 | **The entry's central claim was tested over the fleet and failed — and the failure is now documented rather than hedged.** 464 paired evaluations on the CAS Loss Reserve Database (639 usable triangles from 775 containers, last three diagonals held out so every predicted future is observed): the direct arm is closer to the truth than Chain Ladder on **38.8%** of them, median error 162.6% against the incumbent's 121.3%, losing at every horizon — and it moves the reserve by a median of **142% of Chain Ladder's** to do it, so it is overriding the standard method rather than hedging toward it. The distribution — the entry's actual claim — is **not calibrated**: 39.2/59.9/78.0/84.7% empirical against nominal 50/75/90/95 (z −4.8 to −6.6), with *wide* intervals (4.55× the point estimate) and the truth above the sampled median in 67.7% of units, i.e. a centring failure rather than a width one. The **transferable result** is the mechanism: per-step bias is zero where the model has training rows and **+3.2% per step where it extrapolates** (287 scored steps, intercept +0.0001), with the anchoring trap that nearly hid it (a backtest anchored near the ultimate reads −0.0018 flat). The **comparative claim is explicitly not made** — nothing yet measures whether Mack or the ODP bootstrap are better calibrated on the same units (#20). Entry state: **complete and submittable**; only joining and submitting remains. | Recorded |
| 2026-09-19 | **The conditions check: our negative is not the vendor's documented envelope limit, and their evidence base does not reach our regime.** The failure had been measured; this asked the prior question — is it *predicted* by Prior Labs' own documentation? **Neither pre-registered trigger fired**: no source states a training-row floor above ours and none excludes extrapolation. Our profile lands 3 / 3 / 2 / 3 across the four buckets (fits / predicts-the-opposite / ruled-out / outside-the-evidence). The decisive bucket is the last: the vendor's non-i.i.d. evidence base spans **100–1M rows** and declares sub-100-row prediction *out of scope*, so our **6–33-row** fits are **unreached** by their evidence rather than excluded by it. The bucket that *does* predict our negative is the **split**: on temporal and grouped splits their report expects **parity with tuned conventional models**, not a win — which is the shape we measured (closer than Chain Ladder on 38.8%, and a deterministic actuarial method is exactly the conventional comparator there). Three conditions point the **other** way, and they are the actionable output: the vendor names *claim amounts* by name as a target it improved distributions for; it documents **extrapolation** as a capability; and it publishes guidance for precisely our regime that we did not follow — declare identifier columns categorical ("the cheapest change and often the largest gain"), use the **extrapolating** quantile transform (the default *clips* outside the training range, and our failure is extrapolation beyond it), Thinking mode for time-ordered rows. Those became a new pre-registered arm that runs on units already on disk, with its expectation written from the sources *before* the run. The check also corrected two of our own claims: **"40–60 training rows per fit" was wrong** (a single-triangle figure — the fleet recount gives **6–33, median 25**, no unit above 33), and **"no feature engineering" is not true** — the features are hand-chosen domain ratios and the identifiers are passed as numbers, against the docs' explicit warning. | Recorded |
| 2026-09-19 | **Three explanations for the fleet failure were tested and closed in one day, and the strategy that follows is now written down.** **R4 (the paid column):** the failure is **not column-specific** — paid is closer than Chain Ladder on 36.2% against incurred's 38.2% over 414 paired units, a paired difference of −1.9% (se 3.3%) inside the 2.3pp floor; the recomputation also reproduced the published 38.8%, and *that cross-check is what exposed a defect*: the stored `error_chainladder_pct` is 0.0 on all 464 incurred rows (the null defect fixed once in the summary but never in the file), which had just produced a false "FALSIFIER FIRED — the column choice is a research result". **#22 (the vendor's two documented configuration changes):** they move the **centre** and never the **tail** — 50% coverage 40.0% → 49.3%, 90% exactly 0.0pp, and 95% **−6.7pp** on the extrapolating transform; the replication cell reproduced all 75 recorded rows field-by-field before any difference was read. **A free arithmetic measurement:** the truth lies **above the range of training labels the fit was shown on 21.1% of units** (5.3% of cells), one-sided upward — matching the direction of the coverage defect, and support for the verified mechanism that the regression distribution is a **bucket grid fixed on the pretraining prior**, rescaled only to the training target's mean and sd. The consolidated strategy is now `docs/experiments.md` §6: *stop improving the model; change the problem so it is only asked to interpolate inside ranges it has been shown, and hand the extrapolation to arithmetic* — three changes (a bounded target, an exposure-anchored level, more rows in a stated order) with a **stopping rule**: if they do not move the tail and the closer-than-CL rate above the noise floor, the remaining honest move is the **diagnostic** rather than more modelling. Two arms dispatched against that strategy. | Recorded |
| 2026-09-19 | **The last two levers were run, both falsifiers fired, and the entry is frozen.** **R2 (#24), the bounded target:** the route as pre-registered is **closed**, and honestly it does **not** isolate the support explanation — it moves the tail the *wrong* way and its own instrument cannot hold the level, so the bucket-grid support story is made less likely rather than disproved. **The row expansion (#25):** the in-triangle expansion is **dead** — the fit sees **2.6× the rows** of its own triangle (median 25 → 65, 10–98) and gains nothing measurable: **+2.2pp** on the closer-than-Chain-Ladder rate (47.8% → 50.0% on a fixed 90-unit screen, 7 fixed / 5 broken, McNemar p = 0.774) against a binomial standard error of **5.3pp**, and the depth-bias slope on the arm whose rows did change moves **−0.0005** (0.06421 → 0.06371) against a standard error of 0.0063. Both legs of the pre-registered falsifier hold, so **row count is not the binding constraint** and all the weight moves to E2b — rows that carry *different* information rather than merely more of the same. With that, **five repairs have been closed by measurement** (configuration, the column, widening, the bounded target, more rows of the same kind) plus the speed bar, and **R1 (an exposure-anchored level) is the only untested lever** the stopping rule still covers — if it does not move the tail and the rate above the noise floor, the remaining honest move is the **diagnostic** (#23). Packaging shipped: the six-repair table on the README, the freeze block in the ledger, and a **conflict-marker defect caught and fixed in a source file before it was pushed** (the merge of the two arms conflicted in `direct_training_rows`; both changes were independent and resolved as a true union, 60 tests green against 49 before). | Recorded |
| 2026-09-19 | **The comparative result landed, the novelty was checked, and the entry was packaged.** **#20:** Mack's method and the ODP bootstrap were measured on the **identical 464 units** — all three under-cover, and at the levels a risk margin is read **Mack's is the worst of the three** (74.6% at nominal 90% and 79.3% at 95%, against this model's 78.0% and 84.7%; the ODP bootstrap best at 87.1% / 90.9% but still outside 2 SE at three of four levels). The failures are **shared rather than distinctive** — at 95%, of the 71 units the model misses Mack misses 37 — so the model "misses in the same weather" as the standard method rather than in its own. That turns a negative about our method into a finding about **practice**: nobody's reserving intervals cover as advertised. It also reverses the entry's largest stated caveat, which had said the comparison "has not been run". **E11:** the prior-art pass found **no reserving study that measures interval coverage** for a learning method (that literature scores distributions with pinball/log scores but never asks whether the stated 90% interval covers 90%) and **no evaluation of a foundation model on a loss triangle**, so three firsts survive — the first interval-coverage measurement on reserving triangles, the first to locate the failure in the **depth of a recursive projection**, and the first to compare against the classical intervals on identical units — while the fixed bucket grid mechanism and the general small-n calibration behaviour are **attributed** rather than claimed. **Packaged:** two new figures (the one-sided tail; three-method coverage), a "five minutes" reading path on the README, the submission description and ledger brought current, and a self-contradiction in the #20 report fixed (its verdict said the model was worst at every level; its own table shows **Mack** worst at 90/95). Still running at the freeze: R2 (bounded target) and the row expansion, both with pre-registered falsifiers. | Recorded |

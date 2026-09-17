# What we are showing — the entry, in one page

> **Status:** living document, 2026-09-17. This is the demonstration plan: what a judge actually sees, and
> what each thing proves. `HACKATHON_IDEA_LOG.md` holds why this idea and what is still undecided;
> `HACKATHON_ENTRY_ASSESSMENT.md` holds the event facts. **No results yet** — every number below is a
> placeholder until the spike runs, and nothing here is a claim we have already measured.

## 1. The demonstration, in one sentence

**Point the repository at a loss triangle and get a reserve *with its distribution*, from a single forward
pass — beside the method the industry uses, which reaches the same distribution through a thousand simulated
refits.**

The triangle is the actuarial object nobody treats as tabular: accident periods down the side, development
periods across the top, the lower half unknown. That lower half is the reserve. Nothing about it is
statistical in current practice — it is arithmetic on selected development factors, with uncertainty bolted
on afterwards by a formula (Mack) or a simulation (the ODP bootstrap).

We turn it into a prediction problem and let TabPFN-3.5 answer it. The interesting part is not that it can
produce a number. It is that the model hands back the **whole distribution** in the same forward pass, at no
extra cost — which is the thing reserving practice currently buys with a thousand refits.

## 2. The six beats a judge sees

In the order the README and the notebook present them. Each beat carries one capability and one sentence of
"so what".

| # | Beat | What the viewer sees | What it proves |
|---|---|---|---|
| 1 | **The reframing** | The same numbers twice: as a shaded triangle, then as a tidy table of cells with features. Side by side, one screen | "Formalize a new problem" is literal here — the conversion is about twenty lines and shown, not asserted |
| 2 | **The reserve, zero-shot** | TabPFN's reserve and Chain Ladder's on one triangle, by accident year and in total. No tuning, no feature engineering, raw values straight in | 3.5 can be pointed at a domain object it has never seen and return a defensible number |
| 3 | **The distribution — the headline** | The reserve as a *distribution*: percentiles (50/75/90/99.5) with Mack's and the bootstrap's overlaid. Then a timing bar: one forward pass versus a thousand refits | The capability the whole entry rests on. A risk margin, an IFRS 17 risk adjustment and a Solvency II capital figure are all *quantiles*, not standard errors |
| 4 | **Coverage — the honest test** | A coverage curve: do the 90% intervals contain the truth 90% of the time? TabPFN, Mack, ODP, over the whole fleet | Interval *honesty*, which is the actual regulatory question. Mack's standard error is known to be optimistic in practice; if 3.5's intervals are closer to nominal, that is a real result, and if they are not, that is a real finding |
| 5 | **Speed — the fleet** | Hundreds of public triangles reserved instead of one: wall-clock per triangle for TabPFN against the bootstrap, log scale, plus the Fast checkpoint arm | "Reserve the whole book, every quarter" is the workbench claim — and running the fleet is also how beats 3 and 4 get statistical weight instead of one anecdote |
| 6 | **Where it does not win** | The triangles and the cells where Chain Ladder is closer, and the regime where the advantage flips, stated in the open | Everything above becomes believable. This is the beat that stops the entry reading as a sales pitch — and it is how this working party already writes |

## 3. What we claim, and what would falsify it

| We say | Backed by | Falsified by |
|---|---|---|
| A full reserve distribution from one forward pass | The distribution figure, and the wall-clock bar beside it | A distribution whose quantiles miss badly, or a cost that is not lower |
| The point estimate is competitive with Chain Ladder | Reserve error per triangle across the fleet, and the direction of any bias | Systematic bias over the fleet, not just noise on one triangle |
| Intervals that are more honest than Mack's | The coverage curve for all three methods on the same fleet | Coverage no closer to nominal than Mack's |
| Fleet-scale in minutes, not hours | Per-triangle timing, measured on the same machine for both methods | The bootstrap finishing faster |
| Zero-shot: no tuning, no feature engineering | The code — one `fit`, raw values, no per-triangle settings | A hidden per-triangle hyperparameter |

## 4. Pre-registered before the runs: what counts as a win

Declared now so the numbers cannot be spun afterwards. If one of these fails, the entry says so and the
story moves to the beats that held — which is the same discipline this repo applies to every other finding.

| Beat | Bar |
|---|---|
| Coverage | The 90% interval covers within ±3 points of nominal over the fleet — and is at least as close as Mack's on the same triangles |
| Point estimate | No systematic bias across the fleet; per-triangle error reported in full, including the losses |
| Speed | At least an order of magnitude faster per triangle than the ODP bootstrap, measured on the same machine |
| Never | We do not claim a regulatory-grade reserving model, a tail-extrapolation method, or a replacement for an actuary's judgement |

## 5. What we are not showing

Not individual-claim reserving (a live research literature, and harder to source public data for). Not
fine-tuning — it needs a GPU, hours and a sponsor, and this entry's claim is that none of that is necessary.
Not a stress test of 3.5's scale claims: a triangle is tens to hundreds of rows, so we are using the model in
its small-data strength, and we say so rather than implying we pushed it.

## 6. What a judge opens — the deliverables

| Item | Purpose |
|---|---|
| A public repository, Apache-2.0 | The entry itself (clause 3.5) |
| `README.md` | The six beats in order, the results table inline, and one command to reproduce it |
| `notebooks/quickstart.ipynb` | Colab-runnable: one triangle end to end, the distribution plotted |
| `scripts/fetch_data.py` | Downloads the public triangles, records URLs and hashes — satisfies clause 3.2 without vendoring data |
| `results/` | The backtest outputs the README quotes; nothing quoted that is not in here |
| `docs/what_it_unlocks.md` | The reserving-actuary page: risk margin, IFRS 17 risk adjustment, capital — and where Chain Ladder still wins |
| A two-minute video *(optional field on the form)* | The panel will not run every notebook; a screen recording of beats 1–4 is the best two minutes we can spend |

## 7. Why this scores — the rubric, unmapped from the prose

| Weight | What it is asking for | Where it is answered |
|---|---|---|
| **50%** Showcase of TabPFN-3.5 | How prominently and effectively the model is used, and how convincingly its capabilities are demonstrated in a working prototype | Beats 2–5: five distinct capabilities (default prediction, predictive distribution, Thinking, Fast, calibration) on one spine, each with a named job, each with a figure |
| **30%** Creativity and originality | Novelty and practical value | Beat 1: a domain object the model has never seen, framed as a prediction problem — plus a practical value a reserving actuary can name (a distribution, not a standard error) |
| **20%** Technical quality and reproducibility | Can a third party run it | One command, public data by URL and hash, and the spike gate below |

---

## Appendix A — The demo runbook (commands → figures)

| Step | Produces |
|---|---|
| `python scripts/fetch_data.py` | The public triangles, with URLs and hashes recorded |
| `python -m tabpfn_reserving triangle abc` | Beat 1's two views; beat 2's reserve, against Chain Ladder |
| `+ --distribution` | Beat 3's percentiles, Mack and ODP overlaid; the timings |
| `python -m tabpfn_reserving backtest clrd` | Beat 4's coverage curve and beat 5's fleet timings |
| `+ --thinking` / `+ --fast` | The Thinking arm on the late cells, the Fast arm for the fleet |
| `python -m tabpfn_reserving report` | Beat 6, and the results table the README quotes |

## Appendix B — The results table we intend to fill

One row per triangle per method. Columns are fixed now; the entries are empty until the runs happen.

| dataset | lob | valuation | method | reserve | % err vs actual | 90% interval | covered? | wall-clock (s) |
|---|---|---|---|---|---|---|---|---|
| *abc* | *…* | *…* | chainladder | — | — | — | — | — |
| *abc* | *…* | *…* | mack | — | — | — | — | — |
| *abc* | *…* | *…* | odp-bootstrap | — | — | — | — | — |
| *abc* | *…* | *…* | tabpfn-3.5 | — | — | — | — | — |

Then the same three summary numbers the claim rests on: **coverage**, **reserve error**, **wall-clock**.

## Appendix C — The shape of the code (the reframing, shown not asserted)

```python
# A triangle cell becomes a row: features known at the valuation date, target the cell's own value.
cells = triangle_to_cells(tri)                  # origin, development, cumulative-to-date, factors
train, future = anchor_split(cells, at=valuation_date)   # the lower triangle is the test set

model = TabPFNRegressor()                       # tabpfn 9.0.0 -> TabPFN-3.5; no tuning
model.fit(train[FEATURES], train[TARGET])

point = model.predict(future[FEATURES])
full  = model.predict(future[FEATURES], output_type="full")   # the whole distribution, same pass
reserve = full.sample(total_reserve_samples).sum(axis=1)      # a reserve distribution, not an SE
```

Two things to notice: there is no hyperparameter to set, and the distribution arrives from the same call that
would have produced a point estimate. That is the claim, visible in the code rather than argued in prose.

## Appendix D — The spike gates, before anything is built

The spike is one triangle end to end in a throwaway environment. It is worth doing first because the whole
entry rests on the answers:

1. Does the reframed cell-level prediction produce a *sane* reserve — within a sensible distance of Chain
   Ladder on a triangle where Chain Ladder is trusted?
2. Does `output_type="full"` actually return per-cell quantiles we can sum into a reserve distribution, or
   does it need a different call shape than the docs imply?
3. Does it run on CPU in seconds for a triangle of this size, with no GPU?
4. Does the anchor-time split leak? (The one way to get a beautiful, meaningless result.)

If 1–4 hold, the MVP is mostly packaging. If 2 fails, the entry's headline capability changes and we want to
know that on day one rather than day fourteen.

# Distillation literature — what it actually promises for tabular foundation models

**Ticket.** [#369](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/369) — research ticket, `wayfinder:research`.
**Branch.** `research/distill-literature` (never merged; no PR).
**Pin.** TabPFN v3 weights / `tabpfn-client` 0.3.3, per this repo.
**Status of every number below.** Read in the primary source unless marked otherwise. Where a
number or a fact could not be verified, the cell says **unknown** — deliberately, and not as a
placeholder for "probably".

---

## Headline

The published evidence establishes **function transfer, not prior transfer**. Every distillation
paper with measured numbers trains a *dataset-specific* student on teacher outputs for *that table*
and reports that the student recovers most (≈92–98%) of the teacher's AUC advantage **on that
table**, at CPU latency, provided the teacher was already better than a tuned GBDT there. No paper
in this literature reports a student that inherits the teacher's synthetic-pretraining prior in a
form that works on an unseen dataset — the two pieces of work that do put a prior into a small
model (MotherNet, MotherTree) do it by meta-learning a weight/tree generator, not by soft-label
distillation, and they report parity with tuned baselines rather than a transferable edge.
The gains are real but conditional and small in absolute terms (≈+0.001 to +0.011 AUC over tuned
CatBoost on low-dimensional data; ≈68–71% of the teacher's error gap elsewhere), they vanish or
invert on high-dimensional data and on multiclass tree students, and the protocols disagree with
each other on the single most basic design choice (whether teacher targets should be computed
out-of-fold). Separately, and decisively for this project, the TabPFN-3 licence forbids exactly the
thing the question contemplates: using Outputs to "train, fine-tune, or distill a model that is
competitive with the TABPFN-3 Model", and it excludes distillation for commercial use from
"Non-Commercial Purpose".

---

## Method and scope

Read in full (HTML or PDF-derived text): Pocket Foundation Models (2605.18654); TabPFN-2.5 report
(2511.08667) §3, §4.4, §6; TabPFN-3 report (2605.13986) §2.4.3; TabPFN-3 model licence (Hugging
Face); `priorlabs/tabpfn` and `priorlabs/tabpfn-extensions` READMEs; Jeong et al. (2610.01435);
GEAR (2608.18849); MotherTree (2610.10832); TabDistill (2511.05704); TL-ANDI (2607.04809);
TabPFN-3 report §5 (licence), §2.5 (prior).

Read as abstract only, cited as such: Data Laundering (2412.15255), On the Efficacy of Knowledge
Distillation (1910.01348), Dataset distillation for memorized data (2506.14457), Born-Again
Networks (1805.04770), Hinton et al. (1503.02531), MotherNet (2312.08598), In-Context Data
Distillation with TabPFN (2402.06971), TabPFGen (2406.05216), Distilling TFMs for Structured Health
Data (2605.18702), TACTICL (2608.10837), TabDistill-GAM (2604.13332).

Not read: Prior Labs' General Terms and Conditions for API users (attempted
`docs.priorlabs.ai/legal/terms` and `priorlabs.ai/terms-and-conditions` — both 404 at time of
writing). This matters; see §5.

Search was by arXiv API (`export.arxiv.org/api/query`) because the web-search tool returned HTTP
402. Queries: `all:"Pocket Foundation Models"`, `abs:"tabular foundation model" AND abs:distillation`
(14 hits, all screened), plus targeted `id_list` lookups of the cited works. **No paper was found
that measures what happens to a TFM's pretraining prior after distillation** — that absence is a
finding, not a gap in the search.

---

## 1. Provenance table

`M` = measured in the paper with reported numbers. `A` = asserted, with no measurement reported
(the paper says it, the paper does not show it). `M*` = measured, but on a benchmark that cannot
support the general claim being made from it.

| # | Paper | Claim | M/A | What it was actually measured on / caveat |
|---|---|---|---|---|
| 1 | Pocket Foundation Models — arXiv 2605.18654 (Tanna et al., May 2026) | Distilling TabICLv2 into XGBoost gives 0.882 macro-mean AUC = **96.5% of teacher**, at 1.9 ms CPU | M | 153 classification datasets (TALENT, OpenML-CC18, TabZilla, TabArena), **single seed**, IID splits only. Retention = student AUC ÷ *best-teacher-per-dataset* AUC, so the denominator (~0.914) is not TabICLv2's 0.908 |
| 2 | Pocket | Wins over tuned CatBoost on **51.0%** of datasets, Wilcoxon p=0.0008; wins average +0.021, losses −0.010 | M | Same 153 datasets. The 0.006 macro-mean gap is smaller than the asymmetry claim implies; the significance comes from win/loss asymmetry |
| 3 | Pocket | 38×–860× latency reduction across teacher–student pairs | M | Teacher on A100 (151–1,275 ms), student on one CPU core (1.5–4.0 ms). Per-query lower bound, not end-to-end serving |
| 4 | Pocket | **Teacher rank transfers exactly to student rank** across 4 teachers × 4 student families | M | 48 configurations, 153 datasets; rank-identical. Authors' explanation: tree students hit a capacity ceiling at 97–98% retention, so a stronger teacher is a strictly better target |
| 5 | Pocket | Gains concentrate on low-dimensional data: ≤21 features **+0.011** (n=79) vs >21 features **+0.001** (n=74) | M | Split at the median feature count. The high-dimensional half is "effectively a coin flip against a well-tuned CatBoost, and a slower one" |
| 6 | Pocket | On high-dimensional tasks where the teacher trails CatBoost, **distillation makes it worse** | M | `internet-ads` (d=1,558): CatBoost 0.978, teacher 0.972, distilled 0.950 (−0.028 vs baseline) |
| 7 | Pocket | Multi-teacher averaging: **+0.006 for MLP students (p=0.003)**, **+0.0004–0.0006 for tree students** | M | 5 teacher combinations. Adding Orion-MSP *reduces* AUC in every ensemble it enters |
| 8 | Pocket | The Hinton soft-label machinery is **optional**: hard labels (α=0) beat the full pipeline by **+0.034 AUC (p=0.004)** for MLP students | M* | 5 low-dimensional binary datasets, 3–30 features, 74–5,000 rows, single seed. Directly contradicts the paper's own framing that OOF soft labels are the mechanism |
| 9 | Pocket | Skipping OOF makes ICL distillation worse than hard-label training (soft targets collapse to near-one-hot: entropy ~1e-3 nats vs 0.6–0.9 nats) | A | Mechanism argument, attributed to Mansurov et al. (2412.15255); the entropy figures are illustrative, not a reported experiment |
| 10 | Distilling TFMs for Structured Health Data — arXiv 2605.18702 (same group, same day) | Students retain **≥90%** of teacher AUC across 19 healthcare datasets, ≥26× faster; **multi-teacher averaging does not consistently help** | A/M* | Abstract read, body not read. Same authors as #1; 19 datasets; healthcare only |
| 11 | Distillation of TFMs into Efficient Predictors — arXiv 2610.01435 (Jeong et al., Oct 2026) | **Full-context teacher-only supervision beats the best OOF+label mixture by 22.8–43.0 Elo** | M | TabArena 51 datasets, TabPFN v3 and TabICLv2 teachers, TabM and XGBoost students. **The opposite protocol recommendation to #1/#9** — see §3.1 |
| 12 | Jeong et al. | Distilled students beat matched **tuned-and-ensembled** students by 56.7–97.9 Elo; on TALENT improve 236–258 of 300 datasets, median error −4.02% to −6.37% | M | Default student configs, no student HPO. Strongest positive result in this literature, and still a per-dataset student |
| 13 | Jeong et al. | KD recovers a median **67.9–70.9%** of the teacher–student error gap, only on datasets where the teacher is >1% better; Spearman(teacher gain, KD gain) 0.67–0.82 | M | The cleanest available statement of *what* transfers: the teacher's advantage on this table, about two-thirds of it |
| 14 | Jeong et al. | Synthetic queries help: +14 to +91 Elo over real-queries-only; 2:1 synthetic:real is the chosen operating point; 4:1 adds only 2.7–3.8 Elo for XGBoost at 79% more generation cost | M | Four task-agnostic generators (CutMix best). This is the measured core of "query-coverage expansion", not prior transfer |
| 15 | GEAR — arXiv 2608.18849 (Qin et al., Aug 2026) | Two-stage synthetic-expansion + real-anchoring MLP beats supervised by **1.81–2.00 AUC points** (binary) / 1.19–1.35 (multiclass); beats real-only distillation by 1.76–2.19 / 2.09–2.40 | M | TALENT + TabArena, TabICL/TabPFN/TabDPT teachers, 5 seeds, 4 generators. TALENT-scale AUC points, not TabArena Elo |
| 16 | GEAR | Synthetic-query gains **saturate** and are **generator-dependent** (K=1→10: +0.98; K=10→40: +0.29), with an irreducible fidelity floor | M + proof | Corollary 1 gives the floor as TV(P_X, Q_X); empirically Copula/CTGAN stay below real-only distillation on multiclass |
| 17 | GEAR | Tree students on **multiclass**: LightGBM is **worse than supervised on every path and every teacher** (−2.17 to −10.39 AUC points); XGBoost is +0.44 to +0.51 for TabICL/TabPFN and −0.11 for TabDPT | M | TabPFGen generator. Authors: "distillation is challenging" for non-differentiable students; benefit is student-family dependent |
| 18 | On the Efficacy of Knowledge Distillation — arXiv 1910.01348 (Cho & Hariharan, ICCV 2019) | Larger teachers do not make better teachers; small students cannot mimic large ones; teacher-assistant chains do not fix it; early-stopping the teacher does | A (abstract) | The canonical capacity-gap negative result. Neural teachers/students (vision) |
| 19 | Dataset distillation for memorized data — arXiv 2506.14457 (Behrens & Zdeborová, ICLR 2026) | Students trained on soft labels recover **held-out teacher knowledge**, including memorised facts they never saw; effect depends strongly on soft-label temperature and persists across capacities | A (abstract) | This is the mechanism by which "the prior leaks through soft labels" is possible *and* the mechanism by which distilled benchmark numbers can be inflated |
| 20 | Data Laundering — arXiv 2412.15255 (Mansurov et al., 2024) | KD can transfer benchmark-specific knowledge through legitimate-looking intermediate training (+75% on GPQA with a 2-layer BERT student) without any real capability | A (abstract) | LLM benchmarks, not tabular. Cited by #1 as the reason OOF matters |
| 21 | Born-Again Networks — arXiv 1805.04770 (Furlanello et al., ICML 2018) | A student *identically parameterised to its teacher* can exceed it | A (abstract) | CV/LM, same-capacity students. Does not license "small student beats big teacher" |
| 22 | Hinton et al. — arXiv 1503.02531 | Soft targets transfer "dark knowledge"; distillation compresses an ensemble into one model | A (abstract) | MNIST / a commercial acoustic model. The origin of the soft-label prior, no tabular content |
| 23 | MotherNet — arXiv 2312.08598 (Müller et al., ICLR 2025) | A hypernetwork prompted with a training set emits a child NN's weights in one forward pass; child "comparable to TabPFN and GBDTs", highly efficient at inference | A (abstract) | The only mechanism here that produces a **prior-carrying** small model. "Comparable", not better; child is still generated per dataset |
| 24 | MotherTree — arXiv 2610.10832 (Wang & Johansson, Oct 2026) | Meta-learned tree generator: 0.692 vs 0.635 AUC (GradTree) on TabArena binary at B=200; **distillation from TabPFN-2.6 into CART is worse than plain CART** (0.659 vs 0.670 TabArena; 0.748 vs 0.759 CC18-Small) | M | 64 datasets, 5 seeds, depth-5 trees, B∈{100..1000}. At B=1000 `CART←TabPFN` becomes the top-ranked method — i.e. distillation's value is a small-sample effect, and meta-learning beats it only at B=100 |
| 25 | TabDistill — arXiv 2511.05704 (Dissanayake & Dutta, Nov 2025) | Distils a transformer's *encoder* into ~1,000-parameter MLP weights via a learned linear map; beats the base TabPFN at N=4 examples (Bank 0.72 vs 0.62) | M* | 5 UCI datasets, N∈{4,8,16,32,64}, no confidence intervals that survive a dataset change; at N≥16 it usually loses to the base (Bank N=16: 0.68 vs 0.75). Authors concede gains are limited as N grows |
| 26 | TACTICL — arXiv 2608.10837 (Koshil et al., AutoML 2026) | Replacing up to 85% of TFM layers with task-trained adapters keeps downstream performance **and** in-context ability | A (abstract) | The one compression result that explicitly claims the prior survives — but it keeps a transformer and an in-context interface, so it does not answer the CPU-GBDT question |
| 27 | TL-ANDI — arXiv 2607.04809 (Lin & Li, Jul 2026) | Naive pooling of heterogeneous source data into a TFM context causes **negative transfer**: MSE 1.6995 (TL-RAND) vs 0.9780 (target-only) | M | Simulation (p=10, n_tar=150, n_src=20,000), 30 reps, TabPFN-2.5 base. "Data distillation" here means distilling the *context*, not the model — a naming trap |
| 28 | TabPFN-3 report — arXiv 2605.13986 §2.4.3 | "TabPFN-3 also supports distillation into **dataset-specific** MLPs or tree ensembles via the engine introduced with TabPFN-2.5 … retaining **most** of TabPFN-3's predictive performance **on the dataset it was distilled for**" | A | No numbers, no benchmark, no retention figure, no failure modes. Two explicit scoping words: *dataset-specific*, *on the dataset it was distilled for* |
| 29 | TabPFN-2.5 report — arXiv 2511.08667 §3, §4.4 | "proprietary distillation engine … performance is close to the one of TabPFN on this dataset"; "competitive accuracy" | A | Figure 7 only; internal benchmark, <10k rows; no table, no ECE, no win rate. §3: the artifact "is dataset-specific, does not perform in-context learning" |
| 30 | TabPFN-3 licence v1.0 (Prior Labs GmbH, rev. 2026-03-24) | §2(d): "You may not use Outputs to train, fine-tune, or distill a model that is competitive with the TABPFN-3 Model." §1(c): distillation for commercial use is **not** a Non-Commercial Purpose | A (legal text) | Applies to weights downloaded under this licence. API users are governed by Prior Labs' General T&Cs instead (§ preamble) — **content unknown** |

---

## 2. Three different claims get called "distillation"

The ticket's question only has a clean answer once these are separated. The literature supports
the first, barely touches the second, and never claims the third.

**(a) Function transfer on the same table — measured, robust, modest.**
Train a student on teacher predictions for dataset *D*; deploy on *D*. This is what #1, #10, #11,
#12, #14, #15, #17 measure. It works when the teacher is meaningfully better than the student's
own supervised fit, and it transfers most — not all — of that advantage. Jeong et al. quantify the
transferable quantity precisely: the teacher's error-gap on *that dataset*, of which ≈68–71% comes
back (#13).

**(b) Prior transfer to a model that works on unseen tables — only via meta-learning, and modest.**
No distillation paper reports a student you can point at a new dataset. The models that carry a
prior into a small artifact do it differently: MotherNet emits child-network weights (#23),
MotherTree emits a tree (#24), TACTICL keeps a transformer and prunes it (#26), TabDistill maps an
encoder to ~1k MLP weights (#25). All are dataset-specific *outputs* of a prior-carrying
*generator*. Their reported performance is "comparable" to tuned baselines at best, plus a
small-sample edge that disappears as data grows (MotherTree's own B=100 vs B=1000 comparison, #24).

**(c) "Distil the prior into a GBDT so it generalises" — not claimed anywhere.**
The GBDT students in #1 and #17 are fitted per dataset on that dataset's teacher outputs. Nothing
in them is shared across datasets; the 300-tree, depth-6 model that wins on `cmc` is unrelated to
the one that wins on `kc2`. Read #1's retention figure as "96.5% of the teacher's *performance on
the same 153 tables, one student per table*", which is what it says, not as "96.5% of TabPFN".

---

## 3. Mechanisms claimed to make the transfer work — and what each is worth

### 3.1 Teacher supervision: OOF versus full-context (the literature disagrees)

- **Pocket (#1, #9)** argues out-of-fold labelling is *mandatory* for ICL teachers: score a row
  while it sits in the context and the soft target collapses to near-one-hot recall. It attributes
  the leakage argument to Mansurov et al. (#20) and Behrens & Zdeborová (#19) supply the
  theoretical version: soft labels can transmit held-out teacher knowledge.
- **Jeong et al. (#11)** measure the opposite: full-context targets (query row *included* in the
  teacher's context, α=1, no hard labels at all) beat the best OOF-plus-label mixture by
  **22.8–43.0 Elo** across all four teacher–student pairs, and OOF targets only become competitive
  when mixed with hard labels (α≈0.6).
- Both are measured. They use different teachers (TabICLv2/TabPFNv2.6 vs TabPFN v3/TabICLv2),
  different students (300-tree depth-6 vs TabArena defaults with 8-fold bagging), different
  benchmarks and metrics (macro-mean AUC vs TabArena Elo). **We cannot assume either protocol
  generalises to our data**; the only defensible statement is that the supervision protocol is a
  first-order design choice that two competent groups resolved in opposite directions.

### 3.2 Query-coverage expansion (synthetic covariates as teacher-query locations)

This is the mechanism the ticket calls "synthetic-data generation from the teacher", and it is the
one real lever in the literature.

- Jeong et al. (#14): four *task-agnostic* generators (CutMix, Mixup, FullMix, Perturb) all help,
  +14 to +91 Elo, CutMix best, 2:1 synthetic:real the knee.
- GEAR (#15, #16): a generative model supplies only *covariates*; labels come from the teacher.
  Gains of 1.76–2.40 AUC points over real-data-only distillation, with a proven saturation: the
  finite-query error decays as M^(-1/2) down to an irreducible floor TV(P_X, Q_X) set by generator
  fidelity. Better generators (TabDiff, TabPFGen) plateau higher; Copula and CTGAN can stay *below*
  real-only distillation on multiclass.
- **Crucially: this expands coverage of the input space for one table.** It is interpolation
  between the rows of *D*. It is not sampling from the teacher's pretraining prior, and GEAR's own
  theorem says why more queries cannot fix a generator that does not match the target covariates.

### 3.3 Student capacity and family

- Tree students hit a capacity ceiling cleanly: 97–98% of teacher AUC across all four teachers
  (#1). MLP students top out at 92–94% and are *below* CatBoost on most datasets regardless of
  teacher (#1: 26.5–28.8% win rate).
- GEAR finds the opposite-signed effect for depth: **shallower MLPs show a larger two-stage
  advantage**, and tree students are unstable on multiclass (#17).
- The capacity literature (#18) says the naive "give the student more capacity" lever is not one:
  more accurate teachers are often worse teachers, small students cannot mimic large ones, and
  teacher-assistant chains do not repair it.
- **Net:** capacity is a constraint to be respected (match student family to task type; do not
  expect an MLP to absorb a tree-sized teacher's distribution), not a dial that closes the prior
  gap.

### 3.4 Multi-teacher averaging

Measured, and mostly not worth it: +0.0004–0.0006 for trees, +0.006 for MLPs (#7), and "not
consistently" better in the health replication (#10). One teacher's outputs adding noise to another
is an observed failure (#7: Orion-MSP degrades every ensemble it joins). This is a variance-
reduction story, not a prior story.

### 3.5 Meta-learning / hypernetworks — the only prior-carrying route

MotherNet (#23), MotherTree (#24), TabDistill (#25). These share one property that matters: the
*generator* is trained once on a synthetic prior and then applied to new tables, which is exactly
the capability the distillation papers do not provide. Their reported results are parity, not
dominance — MotherTree beats GradTree substantially (0.692 vs 0.635) but is only competitive with
plain CART on binary tasks and *worse* on TabArena multiclass (0.698 vs 0.723 for GradTree), and it
generates a fixed-depth complete binary tree only.

### 3.6 What does *not* close the gap

- **Larger student capacity** — §3.3; #18, and the MLP-vs-tree retention gap in #1 runs the wrong
  way for the "bigger student" hypothesis.
- **Temperature / soft-label tuning** — #19 shows the *leakage* effect is temperature-sensitive,
  but #8 measures that the entire Hinton machinery (adaptive temperature, confidence weighting, KL)
  is worth **−0.034 AUC** against plain hard labels on clean low-dimensional data.
- **More epochs / more trees** — GEAR explicitly ablates "longer training" and "alternative warm
  starts" as explanations and rejects both (#15); no paper reports a capacity-by-training-length
  interaction that recovers a prior.
- **Augmented priors** — no distillation paper augments anything's prior. The prior-side work
  (Real-TabPFN continued pretraining on 43 real datasets; TabPFN-3's richer SCM prior with an OOD
  and temporal component) improves the *teacher* (#28, #29). Whether a richer teacher prior makes a
  student inherit more is **unknown** — nobody has measured it.

---

## 4. Documented negative results

Ordered by how directly they constrain us.

1. **High-dimensional data inverts the result.** `internet-ads` (1,558 features): CatBoost 0.978,
   teacher 0.972, distilled student 0.950. When the teacher is not better, the student is worse
   than the baseline it was meant to beat (#1, #6). The high-dimensional half of the benchmark
   (n=74) shows +0.001 — indistinguishable from zero.
2. **A weak teacher produces a weak student, proportionally.** Orion-MSP barely clears CatBoost
   (0.878 vs 0.876); its distilled students win on **22.6%** of datasets vs 51.0% for TabICLv2
   (#1). This is the cleanest demonstration that what transfers is the teacher's *margin*, and if
   the margin is ~0 there is nothing to transfer.
3. **Distilling into a tree can be worse than not distilling at all.** MotherTree's
   `CART←TabPFN` baseline scores below plain CART at B=100–200 on 64 datasets (#24). The authors
   also find distillation "provides limited benefit" at small budgets while becoming the
   best-ranked method at B=1000 — the sign of the effect depends on sample size.
4. **Multiclass + tree student is the worst cell in the matrix.** GEAR: LightGBM is below supervised
   training on every distillation path and every teacher (−2.17 to −10.39 AUC points); Copula and
   CTGAN multiclass means are negative despite positive medians (#16, #17). XGBoost is +0.44 to
   +0.51 for two of three teachers and −0.11 for the third — near-parity, not a win.
5. **The soft-label story does not survive its own ablation.** With OOF teacher labels and hard
   targets (α=0), MLP students beat the full Hinton pipeline by 0.034 AUC (p=0.004) on 5
   low-dimensional datasets (#8). The authors' own conclusion: on clean low-dimensional data,
   "practitioners can safely use α=0".
6. **Only about two-thirds of the gap comes back, and only where a gap exists.** Median gap
   recovery 67.9–70.9%; KD improves the student on nearly all datasets where the teacher beats the
   raw student, and on few elsewhere (#13).
7. **Deployment economics are thinner than the headline speedups.** Jeong et al. report 3.0–21.6×
   (not 38–860×) and median *error increases* of 1.72–2.76% vs the teacher, with a one-time cost of
   48–192 s and a break-even of ~100 to ~3,260 requests depending on context size (#12). Pocket's
   larger speedups come from a GPU-batched teacher without KV caching; the two are not comparable.
8. **The capacity gap is real and not repairable by the obvious tricks.** Cho & Hariharan: larger
   teachers are often worse teachers, small students cannot mimic them, teacher-assistant sequences
   are "ineffective", only early-stopping the teacher mitigates (#18).
9. **Soft labels can carry information that is not generalisation.** Behrens & Zdeborová show
   students recovering held-out *memorised* teacher knowledge, with strong temperature dependence
   (#19); Mansurov et al. turn that into benchmark inflation (#20). Both directions cut: it is the
   one mechanism by which something prior-like *could* leak through soft labels, and it is also why
   a distillation result on a benchmark the teacher may have seen cannot be trusted at face value.
10. **Naive source-domain pooling causes measured negative transfer.** TL-ANDI: MSE 1.6995 vs
    0.9780 target-only, not fixed by enlarging the context (#27).
11. **A distillation result can fail to beat the model it distilled from in the few-shot regime it
    targets.** TabDistill beats base TabPFN at N=4 on 5 UCI datasets but loses at N≥16, with 1k-
    parameter students and no CI that survives a dataset change (#25).
12. **Single seed.** The paper this repo cites (#1) is a single-seed study; its ± figures are
    cross-dataset spread, not repeated-measurement variance, and the authors say so in §6.1.

---

## 5. Vendor position (pinned: TabPFN v3 / tabpfn-client 0.3.3)

**Does the vendor document distillation?** Yes — and consistently scopes it as dataset-specific.

- **TabPFN-3 report §2.4.3** (our pinned model): "In production environments constrained by
  latency or memory budgets … TabPFN-3 also supports distillation into **dataset-specific** MLPs or
  tree ensembles via the engine introduced with TabPFN-2.5. The distilled artifact runs on CPU at
  the sub-millisecond latency of a standard MLP or tree ensemble while retaining **most** of
  TabPFN-3's predictive performance **on the dataset it was distilled for**." No numbers, no
  benchmark, no failure mode, no calibration or fairness claim.
- **TabPFN-2.5 report §3 / §4.4**: a "proprietary distillation engine" produces
  `TabPFN-2.5-as-MLP` / `-as-TreeEns`; the artifact "is dataset-specific, does not perform
  in-context learning, takes as input a single data point". §4.4 reports "competitive accuracy"
  against tuned LightGBM/XGBoost/CatBoost on an internal benchmark of datasets under 10k rows,
  shown only as Figure 7. No table, no retention number, no confidence interval. §5 recommends it
  "for larger datasets and CPU-based inference".
- **`priorlabs/tabpfn` README**: the engine is an **Enterprise Edition** feature — "Fast Inference
  Mode: a proprietary distillation engine that converts TabPFN into a compact MLP or tree
  ensemble"; access is via `sales@priorlabs.ai`. It is not in the open-source package and has no
  public API.
- **`tabpfn` / `tabpfn-client` / `tabpfn-extensions`**: no "student mode", no distillation entry
  point, no `distill` symbol exposed. What the ecosystem *does* offer is synthetic data generation
  — the `unsupervised` extension ("data generation, augmentation, outlier detection") and `tabebm`
  / TabPFGen-style energy-based generation. That is the vendor-sanctioned route to
  query-coverage expansion (§3.2), not to a distilled model.
- **Synthetic data generation is documented; a distillation recipe is not.** No hyperparameters, no
  OOF protocol, no temperature schedule, and no statement about whether the vendor's engine uses
  out-of-fold labelling — which is precisely the design choice the two research groups disagree on
  (§3.1). **Unknown.**

**Licensing (the part that decides the project question).** TabPFN-3 weights are released under the
TABPFN-3 License v1.0, non-commercial:

- §1(c) "Non-Commercial Purpose": "(c) to train, fine-tune, or distill other models for commercial
  use, in each case is not a Non-Commercial Purpose."
- §1(d): Outputs may be used "only for Non-Commercial Purposes. Any use of Outputs in production
  systems … requires a separate commercial license."
- §2(d): "**You may not use Outputs to train, fine-tune, or distill a model that is competitive
  with the TABPFN-3 Model.**"
- §3(d): no hosted/SaaS redistribution of the model or a Derivative without a commercial licence.
- Outputs are explicitly *not* Derivatives (§1(a)) — so this is a use restriction on the outputs,
  not a copyright claim over them. That distinction is what makes it enforceable as a contract term
  while leaving the distilled artifact's own IP status murky. **Legal reading: not attempted here —
  unknown, and out of scope for a literature ticket.**

**But our pin is the client.** The TabPFN-3 licence preamble says: "For customers accessing the
TABPFN-3 Model through our API, only our General Terms and Conditions apply." This repo uses
`tabpfn-client` 0.3.3. The operative document is therefore the API T&Cs — and **I could not read
them** (both `docs.priorlabs.ai/legal/terms` and `priorlabs.ai/terms-and-conditions` return 404).
Whether the T&Cs repeat the "do not distil a competitive model" restriction is **unknown**. This is
the single most important unresolved fact in this note, and it is a blocker, not a caveat: do not
run a distillation pilot on the hosted API until someone has read the actual T&Cs.

For completeness: TabPFN v2 weights are Apache-2.0-plus-attribution; TabPFN-2.5, 2.6, 3 and 3.5
weights are all non-commercial (README, "License"). TabPFN-2.5's report §6 adds that "the model, its
derivatives, and its outputs cannot be used for any commercial or production purpose."

---

## 6. What we may **not** assume

Each line names the source that blocks it.

1. **We may not assume a distilled student carries TabPFN's prior to a new dataset.** No paper
   measures this; every measured student is dataset-specific (#1, #11, #15, #17, and the vendor's
   own §2.4.3 wording "dataset-specific … on the dataset it was distilled for").
2. **We may not assume the 96.5% retention figure applies to our data.** It is a macro-mean over 153
   IID benchmark datasets, single seed, and it is a ratio to the best per-dataset teacher — with
   +0.011 on the low-dimensional half and +0.001 on the high-dimensional half (#1, #5).
3. **We may not assume distillation helps when TabPFN does not already beat our baseline.** The
   transfer is the teacher's margin, ~68–71% of it (#13), and a near-zero-margin teacher produces a
   22.6%-win-rate student (#2). This project's own position on TabPFN-vs-GBDT must be settled
   first, per dataset.
4. **We may not assume insurance/lapse data behaves like TabArena.** Every benchmark in every paper
   here is IID per dataset; #1 §6.2 states explicitly that behaviour "under distributional shift, on
   time-series structured data, or under heavy missingness is untested". Our temporal splits are
   outside the evidence.
5. **We may not assume either supervision protocol.** OOF-mandatory (#1) and full-context-best
   (#11) are both measured and mutually contradictory. Any pilot must treat the protocol as a
   factor, not a default.
6. **We may not assume soft labels are necessary.** Hard labels beat the full Hinton pipeline by
   0.034 AUC in the only ablation that tests it (#8). If soft labels are the mechanism by which a
   prior could leak (#19), then the measured-best configuration is also the one least likely to
   transfer anything prior-like.
7. **We may not assume multi-teacher ensembling buys anything.** +0.0006 for trees (#7),
   "not consistently" in the health replication (#10), and actively harmful when a weak teacher is
   added (#7).
8. **We may not assume an MLP student works.** 92–94% retention vs 97–98% for trees, and below
   CatBoost on ~72% of datasets (#1). Trees are the defensible student; MLPs need a reason.
9. **We may not assume a GBDT student is safe on multiclass.** GEAR's LightGBM multiclass results
   are below supervised training on every path (#17).
10. **We may not assume calibration or fairness survive.** The health paper claims both are
    preserved (#10, abstract only, 19 datasets, same authors). Pocket reports tree students inherit
    calibration to ~0.01 ECE and MLP students are 0.02–0.04 worse (#1 §5.3) — but publishes no ECE
    table. The vendor publishes nothing. Our regulatory context needs its own measurement.
11. **We may not assume speedups of the size the abstract advertises.** 38–860× (#1) and 3.0–21.6×
    (#12) measure different teacher serving configurations; both are per-query lower bounds, not
    end-to-end. Break-even is ~100 requests at best and ~3,260 at worst (#12, Table 5).
12. **We may not assume the results replicate.** #1 and #10 are one group publishing on the same
    day; #15 and #11 are concurrent with each other and with #1; #11 and #1 disagree on protocol.
    No independent replication of any of them was located. **unknown.**
13. **We may not assume we are licensed to do this.** §2(d) of the TabPFN-3 licence forbids using
    Outputs to train or distil a competitive model; §1(c) excludes commercial distillation from
    Non-Commercial Purpose. Whether the client/API T&Cs impose the same restriction is **unknown**
    and must be resolved before any pilot (see §5).
14. **We may not assume "data distillation" means model distillation.** In the transfer-learning
    literature (#27) it means compressing a *context*; in the dataset-distillation literature it
    means compressing *training data*; in GEAR it means synthetic query expansion. Three different
    things wearing one word.

---

## 7. Open questions the literature does not answer

- **Does the prior survive at all?** No measurement. The closest proxies are TACTICL's claim that
  in-context ability survives layer replacement (#26, abstract) and Behrens & Zdeborová's finding
  that soft labels can transmit held-out teacher knowledge (#19). Neither quantifies prior retention
  in a CPU student.
- **What does the TabPFN-3 distillation engine actually do, and how well?** Unknown. No retention
  number, no protocol, no OOF statement, no calibration table (§5).
- **Does a distilled student stay calibrated under temporal shift on insurance cohorts?** Unknown;
  untested by every source here.
- **Does teacher size/complexity interact with retention the way #18 says it does for neural
  teachers?** Unknown for ICL teachers; #1's tree-result (rank transfers exactly) and #18's
  neural-teacher result (bigger is often worse) are in tension and have not been reconciled.
- **Does a stronger prior (TabPFN-3's OOD/temporal prior components, §2.5) produce a better
  student?** Unknown; untested.

---

## 8. What this changes for the distillation question

1. **Restate the goal.** If the goal is "a small owned model with TabPFN's prior that works on our
   future datasets", the literature says that is a meta-learning/hypernetwork problem (#23, #24),
   not a distillation problem, and the best published version is *comparable* to tuned baselines.
   If the goal is "TabPFN-quality scores on this table at CPU latency, without TabPFN at serving
   time", that is well-supported — conditionally.
2. **The pre-condition is measurable and cheap.** Teacher margin over our tuned baseline on the
   target table, per dataset. If it is ≤0, expect nothing (#2, #6, #13); if it is positive, expect
   roughly two-thirds of it back (#13) and mostly on low-dimensional tables (#5).
3. **Design the pilot around the disagreements, not around the recipes.** Supervision protocol
   (OOF vs full-context) and student family (XGB vs LGBM vs MLP) are the two axes where the
   published answers conflict; a pilot that fixes either one inherits one group's unverified choice.
4. **Licence first.** Nothing above is worth sequencing before the T&Cs question in §5 is answered.
   That is a one-hour read, not a research task, and it gates the entire direction.

---

## Sources

| Ref | URL |
|---|---|
| Pocket Foundation Models, 2605.18654 | https://arxiv.org/abs/2605.18654 · https://arxiv.org/html/2605.18654v1 |
| Distillation of TFMs into Efficient Predictors, 2610.01435 | https://arxiv.org/abs/2610.01435 |
| GEAR, 2608.18849 | https://arxiv.org/abs/2608.18849 |
| Distilling TFMs for Structured Health Data, 2605.18702 | https://arxiv.org/abs/2605.18702 |
| MotherTree, 2610.10832 | https://arxiv.org/abs/2610.10832 |
| MotherNet, 2312.08598 | https://arxiv.org/abs/2312.08598 |
| TabDistill, 2511.05704 | https://arxiv.org/abs/2511.05704 |
| TACTICL, 2608.10837 | https://arxiv.org/abs/2608.10837 |
| TabDistill-GAM, 2604.13332 | https://arxiv.org/abs/2604.13332 |
| TL-ANDI, 2607.04809 | https://arxiv.org/abs/2607.04809 |
| On the Efficacy of KD, 1910.01348 | https://arxiv.org/abs/1910.01348 |
| Dataset distillation / soft-label leakage, 2506.14457 | https://arxiv.org/abs/2506.14457 |
| Data Laundering, 2412.15255 | https://arxiv.org/abs/2412.15255 |
| Born-Again Networks, 1805.04770 | https://arxiv.org/abs/1805.04770 |
| Hinton et al., 1503.02531 | https://arxiv.org/abs/1503.02531 |
| In-Context Data Distillation with TabPFN, 2402.06971 | https://arxiv.org/abs/2402.06971 |
| TabPFGen, 2406.05216 | https://arxiv.org/abs/2406.05216 |
| TabPFN-2.5 report, 2511.08667 | https://arxiv.org/abs/2511.08667 |
| TabPFN-3 report, 2605.13986 | https://arxiv.org/abs/2605.13986 |
| TabPFN-3 licence v1.0 | https://huggingface.co/Prior-Labs/tabpfn_3/raw/main/LICENSE |
| `priorlabs/tabpfn` README (enterprise distillation, licence summary) | https://github.com/priorlabs/tabpfn |
| `priorlabs/tabpfn-extensions` README (synthetic data generation) | https://github.com/PriorLabs/tabpfn-extensions |
| Prior Labs API T&Cs | **not found** — `docs.priorlabs.ai/legal/terms` and `priorlabs.ai/terms-and-conditions` both 404 on 2026-10-31 |

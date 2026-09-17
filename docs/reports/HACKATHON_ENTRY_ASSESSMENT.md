# TabPFN-3.5 Hackathon — can this repository enter, and what should the entry be?

> **Status:** assessment, 2026-09-17, written against the TabPFN-3.5 Hackathon page as supplied that day.
> Supersedes the first version of this page, which assessed two earlier Prior Labs events. No runs have
> been made and no existing numbers change. **Correction recorded:** the first version concluded the repo
> "cannot enter a hackathon". That was true of the two clock-bound events it was written against and is
> **false for this one** — see §2.

**The short answer:** yes, and this repo is unusually well-placed. The hackathon is an open project
submission judged by a Prior Labs panel on creativity as much as performance, and two of its six tracks —
*Formalize a new problem* and *Showcase a harness* — describe what this repository has already been doing
for a year. The gap to close is the model version: every verdict here is pinned to TabPFN-3, and the
hackathon requires **TabPFN-3.5**.

## 1. The format, as published

| | |
|---|---|
| What | The **TabPFN-3.5 Hackathon** — "Submit a project built with TabPFN-3.5" |
| Shape | Open-ended. "Creativity counts as much as performance showcases" |
| Judging | A Prior Labs judging panel picks the top 3 and honourable mentions |
| Tracks | Build an agent · Build an extension or app (extension, MCP server, visual app, from your own repo, with clear setup instructions) · Take on a hard problem (health, climate, or one you care about; or a Kaggle challenge) · **Formalize a new problem** (take a domain dataset nobody treats as tabular and turn it into a proper prediction task) · **Showcase a harness** (run TabPFN-3.5 through an existing harness like TabPFN-Rel and show what it unlocks) · Your idea |
| Hard requirement | Built with **TabPFN-3.5** |
| Not stated on the page | deadline, submission mechanism, prize, whether entries are solo or team |

## 2. Verdict: yes — and the reason is the format

The two Prior Labs events on record were **clock-bound and solo**: a dataset revealed at 18:45 with
everything submitted by 20:30, and an online prediction competition. Against those, a year of
multi-dataset actuarial evidence is the wrong currency, which is what the first version of this page said.

This hackathon is the opposite shape — an **asynchronous, open-ended, judged submission**. That is the
format accumulated, reproducible work is *for*: the judging panel reads the project, and the repo's
distinguishing asset is exactly what a one-weekend entry cannot fake — evidence, with a version pin, an
evidence path and a neutral-control discipline behind every number.

The repository's own objectives line up with the track list almost item by item.

| Hackathon track | What this repo already holds |
|---|---|
| **Formalize a new problem** | The whole ADSWP programme *is* this, six times over: lapse, claim occurrence, claim frequency, severity, reserving, plus datasets the roadmap lists as untreated (telematics, catastrophe, large loss, mortality, disability, health). Loss-reserving **triangles** are the sharpest example — a domain object actuaries do not treat as tabular at all |
| **Showcase a harness** | It has one: a TabArena-based suite with ELO and time-to-train/infer Pareto fronts, and a generic CLI that takes any CSV + target column (`run_frontier_benchmark.py --data --target --drop`, issue #46 / PR #65) |
| **Take on a hard problem** | Insurance: grouped, temporal, high-cardinality, regulatory-facing, and real. Prior Labs already sells into this vertical |
| **Build an extension or app** | One packaging step from the CLI + calibration + the count→classification reframe (§14.14, AUC #1, p≈0.0010) |
| Build an agent | Not an existing strength; would be new build |
| Your idea | — |

**The one blocker is eligibility, not merit.** Every verdict here is pinned to `v3_default`
(`tabpfn-client 0.3.3`); Prior Labs shipped **TabPFN-3.5 on 15 Sept 2026**. Issue **#186** ("Version-drift
re-test: TabPFN 3.5 on the v3_default underperformance cases") is exactly that gap and has not been run.
It is now a precondition rather than a hygiene item.

## 3. The entry — one recommendation

**Insurance as a relational, anchor-dated prediction problem: run TabPFN-3.5 through the relational
harness (TabPFN-Rel / RPI / RelArena-α) on a real insurance portfolio, and show what changes when the
actuarial frame is the harness's own frame.**

Why this one, over the safer options:

1. **It is the one thing the release itself points at.** RelArena-α, TabPFN-Rel and RPI shipped alongside
   3.5, and Prior Labs is pushing relational prediction as a category. Their harness is evaluated on
   RelBench's public databases — an insurance portfolio, correctly formalised, is a demonstration they
   cannot produce themselves but plainly want.
2. **The harness's discipline *is* actuarial practice.** TabPFN-Rel aggregates only rows with a timestamp
   ≤ *t* and takes the label from the window after *t*, with splits as cuts in time, not random samples.
   That is a valuation date, experience to date, and an outcome in the following period. Naming that
   equivalence — and showing what it buys — is the intellectual content of the entry, and it is a
   defensible finding rather than a demo.
3. **It is complementary to Prior Labs' own material, not a duplicate.** Their cookbook's insurance recipe
   is *flat*: pure premiums on zero-inflated claims, TabPFN vs GLM. An insurance portfolio is not flat —
   it is a policy table, a claim table and a payment table with a valuation date — and nobody has shown
   that publicly.
4. **The repo owns the hard half already**: the actuarial formalism, the datasets, the metric set
   (insurance-native, fold-level SEs), and the baseline suite to compare against.

Tracks hit: **Showcase a harness**, **Formalize a new problem**, **Take on a hard problem**. Deliverable:
your own repo, README with setup, a runnable demo, a results table, and one page of "what it unlocks" for
actuaries.

**First thing to verify, before committing:** whether TabPFN-3.5 is wired into the harness yet. The
harness docs currently describe TabPFN-3 / 3-Plus; the hackathon track name invites 3.5 through it. That
is a five-minute check and it decides whether the entry is "run 3.5 through TabPFN-Rel" or "extend the
harness to 3.5, then run it" — the second being *more* on-theme for a harness track, not less.

## 4. Plan — staged, each step useful on its own

| Stage | Work | Effort | Why it stands alone |
|---|---|---|---|
| **0. 3.5 re-test on the canonical folds** | Closes #186; required for eligibility | ~2h, API only | It is also the harness-showcase evidence, and the paper's Nov–Dec stage needs it |
| **1. The formalisation** | Choose one portfolio with genuine policy/claim/payment tables; declare the schema; write the predictive question as SQL with an anchor date and a label window | ~half day | This *is* "formalize a new problem" — publishable on its own |
| **2. Run it** | TabPFN-Rel via the hosted API; compare against the repo's existing flat-tabular result on the same task | ~half day | The comparison is the "what it unlocks" story |
| **3. Package and submit** | README, setup instructions, runnable demo, results table, one-page actuarial note | ~half day | Submission |
| 4. Optional slice | App / MCP server, if the deadline allows | — | Different track, same runs |

Cost: API only, near zero — and 50% off standard 3.5 rates until **29 Sept 2026**. Scale reference: the
earlier GPU probe cost **$0.0122** measured, and that was a fine-tuning run, not inference.

## 5. Risks, stated rather than discovered later

- **The "database" has to be constituted.** CASdatasets ship as CSVs; RelBench ships relational databases.
  Declaring a schema over CSV tables is honest work but a judge could call the relational structure
  synthetic. *Mitigation:* pick a portfolio that genuinely is policy + claim + payment (Spanish motor, or
  `freMTPL` policies + claims) and say so in the README.
- **Fine-tuning is a separate entry.** It needs a GPU, hours and a sponsor; bundling it dilutes the story
  and risks neither being finished. Keep it out.
- **Model-version churn.** 3.5 is two days old and Fast is in alpha. Pin the version and record the weights
  ID, as this repo's own rule requires.
- **Deadline unknown.** The page as supplied carries no dates and the page is not publicly indexed, so the
  schedule cannot be set from here.

## 6. What is needed from the team

1. **The deadline and the submission link** — the page as supplied has neither, and the plan's shape
   depends on how much time there is.
2. **Who enters.** This hackathon does not state a solo rule or a team limit; one named owner is needed
   either way.
3. **Sign-off on Stage 0's API spend** (cents, discounted until 29 Sept).

---

## Appendix A — The events this page was first written against

Kept for the record: the first version of this assessment was written against these, and they remain the
reason the earlier verdict read "cannot enter".

- **The TabPFN Hackathon** — Merantix AI Campus, Berlin, 21 Oct 2025, 17:30–21:00. Solo; dataset walked
  through at 18:45; work 19:00–20:30 (90 minutes per the Merantix page, "2 hours" per the Luma listing);
  ranked on **model performance and efficiency**; €1,000 in prizes; fireside chat with Noah Hollmann.
  <https://www.merantix-aicampus.com/event/the-tabpfn-hackathon-1keu-in-prizes> · <https://luma.com/hack_tabpfn>
- **TabPFN World Cup competition** — Jun–Jul 2026, online; predict the knockout matches; prize an interview
  with Prior Labs. <https://www.linkedin.com/posts/prior-labs_join-a-tabpfn-competition-to-win-an-interview-activity-7475231226023526402-M7pP>

## Appendix B — Prior Labs state, as of 2026-09-17

- **TabPFN-3.5**, released 15 Sept 2026: first place on TabArena (1 of 89) and BeyondArena (1 of 29);
  TabPFN-3.5-Fast in alpha (up to 6× faster than base); Plus and Thinking on the API; base and Fast in the
  open-source package; SAP AI Core availability. API/MCP at **50% off standard 3.5 rates 15–29 Sept 2026**.
  <https://priorlabs.ai/technical-reports/tabpfn-3-5>
- **RelArena-α, TabPFN-Rel and RPI**, released alongside: a relational benchmarking framework over
  RelBench; a harness that flattens a database by deep feature synthesis along foreign keys and predicts
  in-context; and an interface for defining a prediction problem on your own database by YAML. Relational
  predictions are anchor-dated — features from rows at or before *t*, label from after *t*, splits as time
  cuts. `pip install relarena`; the API-backed variant needs a token from `ux.priorlabs.ai`.
  <https://docs.priorlabs.ai/capabilities/relational> · <https://priorlabs.ai/blog-posts/introducing-relarena>
- Prior Labs is an independent lab inside SAP (acquisition closed 17 Jul 2026).
  <https://priorlabs.ai/blog-posts/priorlabs-sap>

## Appendix C — Repository evidence cited above

| Claim | Evidence in-tree |
|---|---|
| Verdicts pinned to `v3_default` (client 0.3.3); re-test rule | `docs/MODEL_VERSIONS.md`; master report §12.1, §15 |
| Generic CSV+target CLI, tested | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`; `tests/test_frontier_cli.py`; `fe34c5b` (issue #46 / PR #65) |
| Harness: ELO + time-to-train/infer Pareto fronts | `scripts/eval/*/pareto_front_*.pdf`, `time_plot.pdf`, `tabarena_leaderboard.csv`, `tuning-impact-elo*.pdf` |
| Decision rule (when TabPFN wins) — the adoption result | `docs/analyses/regime_characterization.md` §3; `docs/reports/TABPFN_BENCHMARK_SUMMARY.md` |
| Count → classification reframe (AUC #1, p≈0.0010) | master report §14.14 (issue #67) |
| Reserving as a formalised task | `docs/reports/RESERVING_WITH_FOUNDATIONAL_MODELS.md`; issue #134 (`fm_reserving`) |
| Working party objectives this entry serves | `0_roadmap and project dashboard/ADSWP Foundation Model Workstream.xlsx` — RSS/AIDSET Sept 2026, BAJ paper Oct–Dec 2026, IDSC/GIRO 2027; long-term aim: ADSWP benchmark on TabArena |
| Cost discipline for API work | `docs/reports/PILOT_2_COST_AND_CONTROLS.md` (measured, not modelled) |

# Can this repository enter a Prior Labs hackathon — and what should the entry be?

> **Status:** assessment, 2026-09-17. Answers a question about events, not about the model. No Prior Labs
> hackathon is currently announced; the assessment is made against the two events on record and is
> therefore written to survive a re-dated edition. No runs were made and no numbers change here.

**The short answer:** this repository cannot enter a hackathon, and nothing in it should be the entry. Its
value to an entry is procedural — a generic CLI, an efficiency-scoring harness, and a measured rule for
where to spend a clock. What is missing before it can field a *competitive* entry is small and finite:
defaults that are not a model-generation stale, and one clock-bound kit.

## 1. What the events on record actually are

Both Prior Labs competitions to date are **solo**, **clock-bound**, and have **nothing to do with insurance**.

| | The TabPFN Hackathon (on record) | The TabPFN competition (on record) |
|---|---|---|
| When | Tue 21 Oct 2025, 17:30–21:00 | Jun–Jul 2026 |
| Where | AI Campus Berlin (Merantix) | Online |
| Who | Designed for AI/ML engineers and data scientists | Open |
| Format | Compete **solo**; dataset walked through at 18:45, work starts 19:00, closes 20:30 — 90 minutes per the Merantix page, "2 hours" per the Luma listing | Predict the World Cup knockout matches, after Prior Labs had published its own group-stage predictions |
| Scored on | **Model performance and efficiency** | Prediction quality against a fixed target |
| Prize | €1,000 cash, top performers | An interview with Prior Labs |
| Sources | Merantix event page; `luma.com/hack_tabpfn` | Prior Labs LinkedIn 2026-06-23; participant writeup 2026-07-23 |

No 2026 edition of either is announced as of 2026-09-17: nothing on `priorlabs.ai`, nothing under Prior
Labs on Luma (their last listed event is the Oct 2025 hackathon), nothing on the Merantix event pages.
What Prior Labs is running *this* week is the model, not a competition: TabPFN-3.5 shipped 15 Sept 2026.

## 2. Can this repository enter? No — and that is not a defect

Neither format can be entered by a repository. In the Berlin format the dataset is revealed **at 18:45 on
the night** and scored 90 minutes later; in the online format the artefact is a prediction submission on a
fixed public target. A repo of multi-month evidence on closed insurance datasets is not an entry in either
— it is an **armoury**. What enters is a person, carrying a toolkit.

So the useful question is not "is the repo a sufficient entry" but: **does this repo make a nominated
individual materially more likely to win than a strong practitioner holding only the TabPFN docs?**
Today: yes in three specific ways, no in one important one.

## 3. What it already has that a strong outsider does not

| Asset | Where | Why it matters on the night |
|---|---|---|
| A generic entrypoint: any CSV + target column → scored result | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py --data --target --drop` (issue #46, PR #65), covered by `tests/test_frontier_cli.py` | The one command the clock actually needs: unseen dataset in, comparable result out |
| Efficiency instrumentation — Elo vs time-to-train / time-to-infer Pareto fronts, leaderboards, timing plots | `scripts/eval/*/pareto_front_*.pdf`, `time_plot.pdf`, `tabarena_leaderboard.csv`, `tuning-impact-elo*.pdf` | Both events score **performance *and* efficiency**. Most entrants optimise accuracy and run out of clock |
| A predictive rule for *where* TabPFN wins — the time-allocation rule | `docs/analyses/regime_characterization.md` §3, quoted in `docs/reports/TABPFN_BENCHMARK_SUMMARY.md` | 90 minutes is a budget. The rule says when to stop tuning: ≤~5K rows, or classification where the linear floor is far away |
| Measured limits on the expensive levers | `docs/reports/TABPFN_FINE_TUNING_LIMIT_STUDY.md`, `docs/analyses/levers_assessment.md`, `docs/analyses/cpu_model_feasibility.md` | Knowing that fine-tuning needs hours and a GPU — and that only TabPFN has a hosted API at all — prevents the classic hackathon death: attempting a lever that cannot finish |
| A reusable competitive move nobody else has written down: count target → classification reframe (AUC #1, p≈0.0010) | master report §14.14, issue #67 | On any frequency-style target this is a ranking win, and it is a *method*, not a fitted artefact — so it transfers to an unseen dataset |

## 4. What it lacks — three named gaps, none of them large

1. **The defaults are a model-generation stale.** Every verdict here is pinned to `v3_default`
   (`tabpfn-client 0.3.3`). Prior Labs shipped **TabPFN-3.5 on 15 Sept 2026** — first on TabArena and
   BeyondArena, with a Fast variant in alpha and Plus/Thinking on the API — and the open-source package
   ships the base and Fast checkpoints. An entry quoting these numbers, or reusing a pinned default config,
   would be a generation behind the host's own model. Issue **#186** ("Version-drift re-test: TabPFN 3.5 on
   the v3_default underperformance cases", opened 2026-09-16) is exactly this gap and has not been run.
2. **There is no clock-bound kit.** The CLI benchmarks a *suite*; nothing here is packaged as "a run that
   finishes inside 90 minutes, logs its own timings, and freezes a result". That packaging is the
   difference between a good toolkit and an entry.
3. **The rule is solo.** A working party cannot enter as a team. A nomination is needed, and the working
   party's contribution is then the toolkit rather than the entry.

## 5. What the entry should be

**One artefact, serving both formats: a clock-bound TabPFN kit.** A thin wrapper over
`run_frontier_benchmark.py` — current 3.5 default, ensemble off, a row cap chosen from the size sweep,
timing logged per stage, predictions frozen on demand — plus a one-page runbook the entrant actually
reads under the clock:

| Clock | What happens |
|---|---|
| 0–10 min | Profile the CSV: rows, target type, cardinality, class balance, missingness |
| 10–20 min | Default baseline TabPFN **and** one true rival (CatBoost or LightGBM — CPU, already in the stack) |
| 20–70 min | Spend the middle on the axes the decision rule names; do **not** attempt fine-tuning (hours + GPU) |
| 70–85 min | If the metric is probabilistic: calibration. If it is a count target: try the reframe |
| 85–90 min | Freeze, write timings, submit. Efficiency is scored, so the timings are part of the entry |

**What the entry is not.** Not the paper, not the benchmark suite, not a fine-tuned model. The Berlin
format reveals the dataset at 18:45, so nothing pre-fitted can win; the online format is a prediction
submission, where the differentiators are calibration and the reframe, not the repo's insurance numbers.
Insurance evidence is the wrong currency for both.

**Strategic value beyond winning**, which is the part worth putting to the working party: it produces
exactly the fresh v3.5 evidence the BAJ paper's Nov–Dec experimentation stage needs, and it gives issue
#186 a real scope rather than a hypothetical one.

## 6. What would make it sufficient — roughly a day, no GPU

| Step | Effort | Note |
|---|---|---|
| One verification pass on TabPFN-3.5 against the canonical folds | ~2h, API-only | Closes #186; API is 50% off until 29 Sept 2026. For scale: the earlier GPU probe cost **$0.0122** measured |
| The kit + the runbook page | ~4h | Wrapper over code that already exists; no new science |
| Re-read of the decision rule against 3.5 | ~1h | The rule is the part that could have flipped; see `MODEL_VERSIONS.md` and master report §15 |

**What is needed from the team:** the event (name, date, format — the runbook's clock depends on it); one
nominated entrant (the solo rule); and a decision on the 3.5 verification pass.

---

## Appendix A — The two events, in detail

- **The TabPFN Hackathon (€1,000 in prizes)** — Merantix AI Campus, Max-Urich-Straße 3, 13355 Berlin, Tue
  21 Oct 2025, 17:30–21:00. Agenda: 17:30 doors, 18:00 fireside chat with Noah Hollmann (Prior Labs
  co-founder; doors close 18:00 sharp), 18:45 dataset walkthrough & collab setup, 19:00 hackathon begins,
  20:30 closing remarks. "Compete **solo** … 90 minutes to experiment, optimize, and push TabPFN to its
  limits"; "Submissions will be ranked on model performance and efficiency." Hosts: Merantix AI Campus,
  {Tech: Europe}, Prior Labs.
  <https://www.merantix-aicampus.com/event/the-tabpfn-hackathon-1keu-in-prizes> · <https://luma.com/hack_tabpfn>
  - Discrepancy recorded, not resolved: the Merantix page says 90 minutes, the Luma listing says 2 hours.
    The runbook above budgets to the shorter figure.
- **TabPFN World Cup competition** — announced by Prior Labs 2026-06-23 ("predicting group stage matches…
  now it's your turn to beat us", prize: an interview with Prior Labs); participants wrote up entering in
  July 2026. <https://www.linkedin.com/posts/prior-labs_join-a-tabpfn-competition-to-win-an-interview-activity-7475231226023526402-M7pP>
- **Negative result of the search, stated so it can be re-checked:** no 2026 edition of either, and no
  other Prior Labs hackathon, is announced as of 2026-09-17.

## Appendix B — Prior Labs state, as of 2026-09-17

- TabPFN-3.5 released **15 Sept 2026**: first place on TabArena (1 of 89) and BeyondArena (1 of 29);
  TabPFN-3.5-Fast in alpha (up to 6× faster than base); Plus and Thinking on the API; base and Fast in the
  open-source package; SAP AI Core availability. API/MCP at **50% off standard 3.5 token rates from 15–29
  Sept 2026**. <https://priorlabs.ai/technical-reports/tabpfn-3-5> · <https://arxiv.org/pdf/2609.17895>
- Prior Labs is an independent lab inside SAP (acquisition closed 17 Jul 2026): brand, offices and
  open-source work unchanged. <https://priorlabs.ai/blog-posts/priorlabs-sap>
- Hosted API is the only route to a tabular foundation model with no GPU (`docs/analyses/cpu_model_feasibility.md`).

## Appendix C — Repository evidence cited above

| Claim | Evidence in-tree |
|---|---|
| Verdicts pinned to `v3_default`, client 0.3.3; re-test rule | `docs/MODEL_VERSIONS.md`; master report §12.1, §15 |
| Decision rule (when TabPFN wins) | `docs/analyses/regime_characterization.md` §3; `docs/reports/TABPFN_BENCHMARK_SUMMARY.md` |
| Generic CSV+target CLI, tested | `scripts/eval/insurance_benchmark_v1/run_frontier_benchmark.py`; `tests/test_frontier_cli.py`; commit `fe34c5b` (issue #46 / PR #65) |
| Efficiency artefacts (Elo vs time) | `scripts/eval/*/pareto_front_*.pdf`, `time_plot.pdf`, `tabarena_leaderboard.csv` |
| Count → classification reframe | master report §14.14 (issue #67) |
| Fine-tuning cost/limits | `docs/reports/TABPFN_FINE_TUNING_LIMIT_STUDY.md`; `docs/reports/PILOT_2_COST_AND_CONTROLS.md` ($0.0122 measured) |
| Working party objectives the entry could serve | `0_roadmap and project dashboard/ADSWP Foundation Model Workstream.xlsx` — RSS/AIDSET Sept 2026, BAJ paper Oct–Dec 2026, IDSC/GIRO 2027; long-term aim: ADSWP benchmark on TabArena |

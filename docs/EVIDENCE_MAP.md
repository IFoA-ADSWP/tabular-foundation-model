# Evidence map — where a number comes from

> Not a tiered report; a reading aid. It describes the trees that hold evidence and changes none of them.

A claim in this repository ends in one of four places. This page says which, so a reader can choose how far
to walk without opening a directory listing first.

## The four trees

| Tree | What it holds | Who cites it |
| --- | --- | --- |
| `results/<run id>/` | One launch's committed capture: the hashes of every prediction and truth file, the launch manifests, the metrics and prediction tables. [`results/INDEX.md`](../results/INDEX.md) maps each id to the campaign it served | The analyses behind every measured result |
| `outputs/gpu-pilot/` | The paid-run record itself: launch manifests, run ledgers, per-arm and per-seed prediction files, and the logs from the rented machines | The fine-tuning and breadth analyses, sometimes by description rather than by run id |
| `docs/analyses/data/` | Exported diagnostic tables — profiling, importance, an earlier predictions table — with a README stating every column and the hash check behind each row | The diagnostics work, and the tables are meant to be opened |
| `docs/figures/` | Committed figures, each tied to the claim it carries — the verdict, adoption and diagnostics plots, and the four pre-style lapse teaching charts. [`README.md`](figures/README.md) indexes them and names the command that regenerates each | The two closing verdicts, and the junior on-ramp |

## Anatomy of a run directory

`results/<run id>/` is the unit a number is anchored to. Inside it:

- **`capture.json`** — the commit point. For every arm and seed in the run it records the row count and the
  sha256 of both the predictions and the ground truth. A capture entry is a claim that *this file* was
  measured, not merely that a run happened.
- **`manifest_<timestamp>.json`** — the launch as configured: versions, device, arms, seeds, row counts.
  Two manifests usually mean two launches contributed to the same run directory.
- **prediction and metric tables** — the data the capture hashes.

Reading a capture entry is the cheapest audit available: it names the arm, the seed, how many rows, and the
two hashes. If a document's number cannot be re-derived from those files, the number is not supported.

## What a citation is, mechanically

The repository enforces one rule, in `scripts/check_citations.py`:

- A **bare run id** — `YYYYMMDDTHHMMSSZ` — appearing anywhere under `docs/` in a Markdown, CSV or text file
  is a **citation**. It must resolve to `results/<run id>/capture.json`, whose entries cover every arm and
  seed present in the run, with non-null hashes.
- An id carrying a `-` suffix is a **record or launch name**, not a citation, and is not scanned. That is why
  a diagnostic record is described as `20261107T112100Z-<dataset>` and not by its bare prefix: the bare
  prefix would demand a capture that does not exist, and should not.
- A small number of ids predate the rule. They are listed in `docs/analyses/legacy_citations.txt`, which is
  append-only and refuses any id from after the rule's date — grandfathering a new citation is not possible.

Conversation is not citation: issue text and commit messages are deliberately not scanned.

## Why some documents cite by description

The Spanish cell's launches live under `outputs/gpu-pilot/` and no `results/` capture was taken for them. A
document that cited its run id bare would demand a capture that does not exist, so the result is cited by
description instead — the launch record, the arm count, the seed range — and the analysis says plainly that
this is the case.

That is a gap, not a virtue, and it is the reason the rule exists: a reader can still find the launch, but
cannot verify a prediction hash against it. When a future run is cited, capture it.

## If two documents disagree

The order is stated once, in [DOCUMENT_AUTHORITY.md](DOCUMENT_AUTHORITY.md) — for a number it ends at the
capture. A summary that restates a number it does not own is the known failure mode here; the findings
registry is written to forbid it, and this page exists so the walk from summary to capture is always the
same walk.

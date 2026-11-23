# Plan — record dataset licences and provenance

**Status:** Current — implemented with this change, 2026-11-22.
**Origin:** the first authorisation of map #716, which cannot meet its own rule without this.

## What

A provenance table in `data/README.md`: one row per input file, its recorded source, and its
licence status — marked verified or unverified.

## Why

The research-portfolio map (`#716`) requires every candidate to name its dataset **and licence**
at creation. Its first authorisation — `#721` and `#719` together — cannot meet that rule today:
`data/README.md` carried no licence statement for any input.

Writing the table exposed three facts that were not visible before:

1. **`bemtl97.csv` has no entry in `data/README.md` at all** — no source, no download path,
   despite being used in the frontier benchmark and in `#722`'s scoped transfer test.
2. **`spanish_motor_freq` is not CASdatasets.** It is prepared from
   `data/raw/Spanish motor portfolio/`, a raw directory whose own provenance is unrecorded. An
   earlier assumption that recording "the CASdatasets terms" would close the gap was wrong for
   this target.
3. **`freMTPL2freq` is presumed CASdatasets but the repo never says so** — `download_datasets.py`
   treats the file as already present. A presumption is not a record.

## What is verified

CASdatasets is **GPL (>= 2)**, package version 1.2-1, DOI `10.57745/P0KHAG`, read from the
package `DESCRIPTION`. That is a *package-level* fact: whether it carries dataset-level
permission from the originating insurers is not stated by the package, and the table says so
rather than blurring the two.

## What this change does not do

It does not close the gaps. It makes them visible and names the fix: record the provenance from
the source actually used, or record the unknown deliberately. Both are acceptable endings; an
unstated assumption is not.

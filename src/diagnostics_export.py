"""Export a diagnostic record as one committed table a reviewer can open (#407).

    python scripts/diagnostics/export_records.py \
        --run outputs/diagnostics/d2_importance/20261104T1725Z-coil2000 \
        --run outputs/diagnostics/d2_importance/20261104T1725Z-eudirectlapse

`--run` is repeatable, and a directory of record directories is accepted too -- while it holds
**one run per dataset**, which is what the diagnostic directory holds today. Records accumulate (a
record is never overwritten), so once a second run exists, name the record directories of the run
you mean rather than the diagnostic directory; two runs of one dataset are refused.

A diagnostic writes its record under `outputs/diagnostics/`, which is git-ignored -- deliberate,
because a record is runtime evidence. The cost is that the campaign is unreadable from the tree:
an acceptance criterion of the form "one record per dataset" cannot be checked from a diff, and
D2's result had to be shipped as prose in a pull request because there was nowhere else for it to
live. This turns each record into a table under `docs/analyses/data/`, which is committed.

**What each row rests on.** Every row carries `dataset_sha256`, the hash of the CSV the diagnostic
read, and that hash is *verified* against `data/raw/MANIFEST.sha256` before anything is written.
It is the part a reviewer can check from a clean checkout: grep the value in the manifest and it
names the committed bytes. A mismatch refuses and names both values, the way
`scripts/analyses/export_predictions.py` refuses an array that disagrees with `capture.json`.

`record_sha` names the record itself. Where the record is committed (the D2 fixtures this
exporter's test re-exports from) it is checkable; where it is not, it identifies a record that
lives only on the machine that ran the diagnostic. The table does not pretend otherwise.

**Bytes are reproducible or the table is a claim.** No wall-clock column, no absolute path, and a
total sort order `(dataset, family, rank)`, so the same records produce the same bytes in any
argument order. `tests/test_export_records.py` holds the committed table to exactly that.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from anchor_datasets import load_anchor_datasets
from provenance import csv_cell

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data" / "raw"
MANIFEST = DATA_RAW / "MANIFEST.sha256"
OUT_DIR = REPO_ROOT / "docs" / "analyses" / "data"

RECORD_JSON = "record.json"

# The columns of each table, in this order. A column is added here and in the README together;
# the README is what tells a reviewer what the number means.
BASE_COLUMNS = ("run_id", "dataset")
ANCHOR_COLUMNS = ("dataset_sha256", "record_sha")

D2_COLUMNS = (
    *BASE_COLUMNS,
    "family",
    "rank",
    "feature",
    "importance",
    "std",
    "univariate_auc",
    "test_auc",
    "no_better_than_chance",
    # A number is only meaningful against the model it was measured with, so both the label the
    # diagnostic asked for and the one the library resolved travel with the row (#285: `auto` is a
    # request, not a version -- and the name says which is which, because `model_version` alone
    # means the *resolved* label everywhere else in this repo).
    "model_version_requested",
    "model_resolved_version",
    *ANCHOR_COLUMNS,
)

D1_COLUMNS = (
    *BASE_COLUMNS,
    "n_rows",
    "n_cols",
    "n_features",
    "n_numeric_features",
    "n_categorical_features",
    "numeric_to_categorical_ratio",
    "n_features_after_one_hot",
    "feature_row_ratio",
    "missing_rate",
    "n_cols_with_missing",
    "max_col_missing_rate",
    "n_high_cardinality_features",
    "max_vif",
    "vif_reason",
    "max_abs_feature_correlation",
    "target",
    "missing_by_column",
    *ANCHOR_COLUMNS,
)

# The measurement keys each exporter reads. A record that predates one is refused by name: a table
# with a silently blank column is a claim nothing can check.
D1_REQUIRED = (
    "n_rows",
    "n_cols",
    "n_features",
    "n_numeric_features",
    "n_categorical_features",
    "numeric_to_categorical_ratio",
    "n_features_after_one_hot",
    "feature_row_ratio",
    "missing_rate",
    "n_cols_with_missing",
    "max_col_missing_rate",
    "n_high_cardinality_features",
    "max_vif",
    "vif_reason",
    "max_abs_feature_correlation",
    "target",
    "missing_by_column",
)
D2_FAMILY_REQUIRED = ("ranking", "test_auc", "no_better_than_chance")

TABLES = {
    "d2_importance": D2_COLUMNS,
    "d1_profiling": D1_COLUMNS,
}

# D3 and D5 write records too; their tables land when each is next run. Naming the supported set
# here is what makes an unsupported record a refusal rather than an empty file.
SUPPORTED = tuple(TABLES)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
def read_manifest(path=None):
    """`{relative csv path: sha256}` from the committed manifest."""
    path = Path(path or MANIFEST)
    if not path.exists():
        raise SystemExit(f"no dataset manifest at {path}: a table row has nothing to rest on")
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sha, _, name = line.partition("  ")
        entries[name.strip().lstrip("./")] = sha.strip()
    return entries


def record_directories(paths):
    """Every record directory named, directly or one level down. Sorted and de-duplicated.

    `--run` takes a record directory (`<diagnostic>/<run id>/`) or a directory of them
    (`<diagnostic>/`), because the four D2 records of one run are siblings and passing one
    directory is the command a person actually types.
    """
    found = []
    for path in paths:
        path = Path(path)
        before = len(found)
        if (path / RECORD_JSON).exists():
            found.append(path)
        elif path.is_dir():
            found.extend(sorted(child for child in path.iterdir() if (child / RECORD_JSON).exists()))
        else:
            raise SystemExit(f"{path} is neither a record directory nor a directory of them")
        if len(found) == before:
            raise SystemExit(f"no {RECORD_JSON} under {path}")
    return sorted(set(found))


def load_record(directory):
    """The record and the sha256 of its bytes, so a row can name the file it came from."""
    directory = Path(directory)
    raw = (directory / RECORD_JSON).read_bytes()
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(f"{directory / RECORD_JSON} is not valid JSON: {error}") from error
    for key in ("diagnostic", "run_id", "dataset_name", "measurements"):
        if key not in record:
            raise SystemExit(f"{directory / RECORD_JSON} has no {key!r}: not a diagnostic record")
    return record, hashlib.sha256(raw).hexdigest()


def verify_dataset(dataset, recorded_sha, manifest, registry):
    """The committed bytes this table row rests on, or a refusal naming both values."""
    if dataset not in registry:
        raise SystemExit(
            f"REFUSING: {dataset!r} is not a dataset in the anchor registry, so its table row "
            "would rest on a file outside data/raw that no reviewer can check"
        )
    relative = Path(registry[dataset]["file"]).resolve().relative_to(DATA_RAW.resolve()).as_posix()
    if relative not in manifest:
        raise SystemExit(
            f"REFUSING: {relative} is not in the dataset manifest {MANIFEST.name}, so a row for "
            f"{dataset!r} has no hash to check against"
        )
    if manifest[relative] != recorded_sha:
        raise SystemExit(
            f"REFUSING: {dataset!r} record says dataset_sha256={recorded_sha}, but "
            f"{MANIFEST.name} says {manifest[relative]} for {relative}. The row would rest on "
            "bytes that are not the ones the run read."
        )
    return recorded_sha


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------
def _require(measurements, key, record, prefix="measurements"):
    """The measurement key, or a refusal that names it and the record it is missing from."""
    if key not in measurements:
        raise SystemExit(
            f"{record.get('run_id')}: the {record.get('diagnostic')} record has no "
            f"{prefix}.{key} -- the record shape changed since this exporter was written, and "
            "the table is refused rather than filled with blanks"
        )
    return measurements[key]


def d2_rows(record, record_sha, dataset_sha):
    """One row per dataset x family x feature: enough to rebuild a top ten and the readings."""
    measurements = record["measurements"]
    families = _require(measurements, "families", record)
    univariate = _require(measurements, "univariate", record)
    # The provenance block is required, but may be `None` (families injected) or may resolve no
    # version (`resolution_reason` says why). A present-but-empty block is a fact the record states;
    # an absent one is a shape change, so `_require` refuses that and this only tolerates the null.
    tabpfn = _require(measurements, "tabpfn", record) or {}
    resolved_version = tabpfn.get("resolved_version")

    rows = []
    for family, block in families.items():
        for key in D2_FAMILY_REQUIRED:
            _require(block, key, record, prefix=f"measurements.families.{family}")
        for position, entry in enumerate(block["ranking"], start=1):
            rows.append(
                {
                    "run_id": record["run_id"],
                    "dataset": record["dataset_name"],
                    "family": family,
                    "rank": position,
                    "feature": entry["feature"],
                    "importance": entry["importance"],
                    "std": entry["std"],
                    # Absent for a feature the diagnostic did not score univariately; the empty
                    # cell says that, and the readings that need it are still computable for the
                    # features that carry it.
                    "univariate_auc": univariate.get(entry["feature"]),
                    "test_auc": block["test_auc"],
                    "no_better_than_chance": block["no_better_than_chance"],
                    "model_version_requested": record.get("model_version"),
                    "model_resolved_version": resolved_version,
                    "dataset_sha256": dataset_sha,
                    "record_sha": record_sha,
                }
            )
    return rows


def d1_rows(record, record_sha, dataset_sha):
    """One row per dataset. The two nested blocks stay JSON so the row keeps its shape.

    No model-version column: D1 fits nothing, so a version here would be a stamp the table's
    numbers do not rest on. The record carries the field because the record contract asks for it.
    """
    measurements = record["measurements"]
    row = {
        "run_id": record["run_id"],
        "dataset": record["dataset_name"],
        "dataset_sha256": dataset_sha,
        "record_sha": record_sha,
    }
    for key in D1_REQUIRED:
        row[key] = _require(measurements, key, record)
    return [row]


EXPORTERS = {
    "d2_importance": d2_rows,
    "d1_profiling": d1_rows,
}


def _sort_key(diagnostic, row):
    """A total order: `rank` is unique within a family, and the owners guard above lets only one
    run speak for a dataset, so `(dataset, family, rank)` cannot tie. No timestamp column, so two
    exports of the same records produce the same bytes.
    """
    if diagnostic == "d2_importance":
        return (row["dataset"], row["family"], row["rank"])
    return (row["dataset"],)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def export(paths, *, out_dir=None, manifest_path=None):
    """Write one table per diagnostic named by `paths`. Returns `{diagnostic: path}`.

    Everything is validated before anything is written, so a refusal leaves the previous table
    untouched rather than half-replaced with rows that failed the check.
    """
    manifest = read_manifest(manifest_path)
    registry = load_anchor_datasets()

    collected: dict[str, list[dict]] = {}
    owners: dict[tuple[str, str], str] = {}
    seen: set[tuple[str, str]] = set()
    for directory in record_directories(paths):
        record, record_sha = load_record(directory)
        diagnostic = record["diagnostic"]
        if diagnostic not in EXPORTERS:
            raise SystemExit(
                f"{record['run_id']}: no table is defined for {diagnostic!r}. Supported: "
                f"{', '.join(SUPPORTED)}. An unsupported record is refused rather than exported "
                "as an empty table."
            )
        identity = (record["run_id"], record["dataset_name"])
        if identity in seen:
            raise SystemExit(
                f"REFUSING: two records for run {record['run_id']!r} and dataset "
                f"{record['dataset_name']!r}; one row per record, and the exporter cannot choose "
                "between them"
            )
        seen.add(identity)
        # One run per dataset, because the table's key is `(dataset, family, feature)`: a second run
        # of the same dataset would put two `rank = 1` rows in one family, and "rank <= 10" would
        # stop identifying a top ten. Records **accumulate** -- `write_diagnostic_record` refuses to
        # overwrite and every run gets its own directory, which is why passing the diagnostic
        # directory works today and will not after the next D2 run. The refusal says what to do.
        measured_by = owners.setdefault((diagnostic, record["dataset_name"]), record["run_id"])
        if measured_by != record["run_id"]:
            raise SystemExit(
                f"REFUSING: {record['dataset_name']!r} is measured by two runs "
                f"({measured_by} and {record['run_id']}). This table is one row per dataset x "
                "family x feature, so a rank would no longer identify a position. Name the record "
                "directories of the run you mean (`--run` once per dataset), or give the second "
                "run its own --out-dir."
            )
        dataset_sha = verify_dataset(
            record["dataset_name"], record.get("dataset_sha256"), manifest, registry
        )
        collected.setdefault(diagnostic, []).extend(
            EXPORTERS[diagnostic](record, record_sha, dataset_sha)
        )

    if not collected:
        raise SystemExit("no records to export")

    out_dir = Path(out_dir or OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for diagnostic, rows in sorted(collected.items()):
        rows.sort(key=lambda row: _sort_key(diagnostic, row))
        target = out_dir / f"{diagnostic}.csv"
        with open(target, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(TABLES[diagnostic]), lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({column: csv_cell(row[column]) for column in TABLES[diagnostic]})
        written[diagnostic] = target
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Export diagnostic records as committed tables under docs/analyses/data/.",
    )
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        type=Path,
        metavar="PATH",
        help="a record directory, or a directory of them (repeatable)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="where the tables are written (default: docs/analyses/data/)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="the dataset manifest every row's hash is checked against (default: data/raw/MANIFEST.sha256)",
    )
    args = parser.parse_args(argv)

    written = export(args.run, out_dir=args.out_dir, manifest_path=args.manifest)
    for diagnostic, path in written.items():
        rows = sum(1 for _ in path.open()) - 1
        print(f"{diagnostic}: {rows} row(s) -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Append a run record to the cost ledger, migrating it when the schema changed (#416).

`run_<stamp>.json` is the source of truth; `run_ledger.csv` is one row per run, derived from those
records for aggregation. A record's fields grow over time, and appending a wider row to a narrower
header shifts every column — which is how the ledger once reported a unix timestamp as "minutes of
wall time" and every cost after it as nonsense.

The first fix compared the header and quarantined the file on a mismatch. That preserves the data and
loses the file: on 2026-11-12 the `credit_before_usd` field arrived, the ledger was moved aside seven
times, and 12 runs never reached it. Rebuilding from JSON cannot restore everything either — one row
in the ledger has no record at all.

So a schema change now **migrates**: old rows are read against the old header, mapped by column name
into the new field set, and rewritten. A column that did not exist before is empty; a column that has
disappeared is dropped and named, because a silent drop is the failure this module exists to prevent.
Quarantine remains, but only for a file that cannot be read as CSV at all.
"""
from __future__ import annotations

import csv
import os

NEW = "new"
APPENDED = "appended"
MIGRATED = "migrated"
QUARANTINED = "quarantined"


def _header_and_rows(path: str) -> tuple[list[str], list[list[str]]]:
    """Return the file's header and its raw rows. Raises on anything unreadable."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        return header, [row for row in reader if row]


def _migrate(path: str, fields: list[str]) -> list[str]:
    """Rewrite `path` under `fields`, preserving every row by column name.

    Returns the columns that were dropped. An empty file, or one whose header already
    matches, is left alone by the caller.
    """
    header, rows = _header_and_rows(path)
    dropped = [column for column in header if column not in fields]
    merged: list[dict[str, str]] = []
    for row in rows:
        # A short row is padded by zip; a long one is truncated to the header's length.
        merged.append(dict(zip(header, row)))
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in merged:
            writer.writerow({field: record.get(field, "") for field in fields})
    return dropped


def append(path: str, record: dict, stamp: str | None = None) -> str:
    """Append `record`, migrating or quarantining the ledger if its header disagrees.

    `record` is the same dict the caller writes as `run_<stamp>.json`, and its key order is
    the ledger's field order — the ledger is derived from the record, never the reverse.
    """
    path = str(path)
    fields = list(record)
    existed = os.path.exists(path) and os.path.getsize(path) > 0
    status = APPENDED if existed else NEW
    if existed:
        try:
            header, _ = _header_and_rows(path)
        except (OSError, UnicodeDecodeError, csv.Error):
            _quarantine(path, stamp)
            status = QUARANTINED
        else:
            if header != fields:
                try:
                    dropped = _migrate(path, fields)
                except (OSError, UnicodeDecodeError, csv.Error):
                    _quarantine(path, stamp)
                    status = QUARANTINED
                else:
                    status = MIGRATED
                    if dropped:
                        print(
                            "[cost] ledger migrated; dropped columns no longer in the record: "
                            + ",".join(dropped)
                        )
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if handle.tell() == 0:
            writer.writeheader()
        writer.writerow(record)
    return status


def _quarantine(path: str, stamp: str | None) -> None:
    os.rename(path, path + ".stale-" + (stamp or "unknown"))

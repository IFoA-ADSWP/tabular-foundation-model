# Plan — #423: `--yes` answers the leak preflight

**Status:** Current — issue #423.

## Why

The preflight that warns about billing `tabpfn-pilot*` instances has its own `read`. A launch with
`--yes` under `nohup` gets EOF, exits 2 before provisioning, and looks like a normal start until the
abort line. That makes a second concurrent launch impossible without piping `y` into the prompt —
the workaround issue #423 was filed to remove, because it teaches a blind answer to a prompt that
exists to catch money leaking. The warning is also wrong in the concurrent case: the instances it
names are the wave's own siblings.

## What changes

- `vast_run.sh`: when `--yes` is set, the preflight continues and prints that it did so. Without
  `--yes`, the prompt and the abort are unchanged.
- `mock_vastai.sh`: `MOCK_SIBLINGS=1` reports a sibling instance, so the path can be tested.
- `tests/test_yes_leak_preflight.py`: with `--yes` the launch proceeds and provisions; without it,
  a closed stdin aborts and nothing is created.

## Not in scope

The shared `run_ledger.csv` is still written by every launch in a checkout. Two concurrent launches
from one clone interleave it; run them from separate clones or with distinct `VAST_OUTDIR` until a
lock lands.

## Verification

```bash
.venv/bin/pytest tests/test_yes_leak_preflight.py -q
./scripts/check.sh
```

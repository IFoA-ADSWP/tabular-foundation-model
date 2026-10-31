# Plan — pass a model path only when an operator set one (#285)

**Status:** Current — implementing 2026-10-31.
**Origin:** #285 reopened after the smoke launch failed every arm in three seconds.

## What the smoke proved

`resolve_model_path()` returns the **label** `v3_default`. `TabPFNClassifier(model_path=...)`
accepts a **file name, a path, or `"auto"`** — never a label. So the pin added in the first #285
attempt broke every arm:

```
ValueError: Model v3_default not found in available models:
['tabpfn-v3-classifier-v3_default.ckpt', ...]
```

Before #285, nothing was passed and `auto` worked. The fix made the record more precise and the
run impossible.

## The change

- `explicit_model_path()` returns what an operator actually set — env, then `.env` — or `None`.
  `None` now means "nobody chose", which is a different fact from "the baseline label".
- `resolve_model_path()` keeps returning the **label**, for records and benchmarks that only need
  to name an era.
- The launcher passes `model_path` **only when it is not None**. Otherwise the library's own
  default applies, and the record says `version: auto`, `version_source: auto` — honest about who
  chose.

A version-drift re-test still works: `TABPFN_MODEL_PATH=<file-or-path>` reaches both arms and the
record says `pinned`.

## What this costs

The anchor can no longer claim `v3_default` unless someone sets it. That is the correct trade: a
record saying `auto` is weak but true, and the alternative was a record saying `v3_default` while
every run died.

## Verification

- Unset (and no `.env`): no `model_path` argument reaches either constructor; the record says
  `auto` / `auto`.
- Set: the value reaches both arms; the record says `pinned`.
- The record-contract test accepts both sources and says why.
- `./scripts/check.sh` green.

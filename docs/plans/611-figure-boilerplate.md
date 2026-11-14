# Plan — one CLI and one test loader for the figure scripts

**Status:** Current — implemented with this change, 2026-11-14.
**Origin:** #611, raised in the #610 review: three figure modules and three test modules each carried
the same boilerplate.
**Design:** move the shared parts to the module that already owns the shared style, and to one pytest
fixture. No behaviour change; no figure bytes change.

## Scope

1. `scripts/infra/figure_style.py` gains `figure_parser(default_out, *, description)` and
   `report_written(paths)`.
2. `verdict_figures.py`, `adoption_figures.py` and `diagnostics_figures.py` use them; their local
   `argparse` setup and path-printing loop go.
3. `tests/conftest.py` gains a `load_script` fixture that registers a module under its name before
   executing it (required for `@dataclass`); the three test modules use it instead of their own
   `_module()`.

## Decisions worth arguing with

**The parser lives with the style, not in a new module.** `figure_style.py` is already the one place a
figure script imports its look from; adding its two shared verbs there keeps the import list short and
avoids a `figure_cli.py` that exists only to be imported once per script.

**The fixture registers the module, deliberately.** The loaders were passing without registration
because the scripts had no dataclass when they were written; `adoption_figures` and
`diagnostics_figures` do, and an unregistered module raises inside `@dataclass`. Registering is the
standard pattern and removes a latent trap.

**Script-specific flags stay local.** `--only` differs between the two multi-figure scripts, so
`figure_parser()` returns a parser the caller extends rather than taking a `choices` argument.

## Verification

```sh
.venv/bin/python scripts/infra/verdict_figures.py
.venv/bin/python scripts/infra/adoption_figures.py
.venv/bin/python scripts/infra/diagnostics_figures.py
PATH="$PWD/.venv/bin:$PATH" ./scripts/check.sh
```

All ten committed PDF/PNG files hash identically before and after the change, and the suite is green.

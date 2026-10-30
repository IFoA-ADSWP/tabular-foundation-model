"""The experiment registry: what an experiment *is*, declared once and read fail-closed.

Issue #230. The registry is a committed TOML file beside the v1 suite's evidence; this
module owns reading it. Nothing here touches a dataset, a model or the disk beyond the
file it is handed — the loader is path-in/data-out so the scoring code stays testable
without a filesystem.

Vocabulary follows `GLOSSARY.md`: a dataset carries its metric, an experiment carries a
dataset, a set of methods, a seed and a fold count. The metric is resolved onto the
experiment at load and cannot be restated in the file, so there is one declaration site.

Everything is refused rather than defaulted: a registry that is missing a field, names an
unknown key, or points at a dataset that does not exist describes nothing, and a benchmark
that ran against a guess is worse than one that did not run.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1

CLASSIFICATION = "classification"
REGRESSION = "regression"
MODES = (CLASSIFICATION, REGRESSION)

# The metric a dataset carries decides its mode — the same dispatch `metric_fn` uses.
MODE_BY_METRIC = {
    "log_loss": CLASSIFICATION,
    "rmse": REGRESSION,
    "poisson_deviance": REGRESSION,
}

# How the D2 rule counts a method's parameters (spec §5 counting-rule table).
N_PARAMS_RULES = ("glm", "trees", "tabpfn")

# The input transforms `load_Xy` knows how to apply.
TRANSFORMS = ("log_exposure",)

_DATASET_KEYS = ("file", "target", "drop", "metric", "transform")
_METHOD_KEYS = ("n_params",)
_EXPERIMENT_KEYS = ("dataset", "methods", "n_folds", "seed", "model_version", "row_sizes")


class RegistryError(ValueError):
    """A registry that cannot be trusted to describe what it claims."""


@dataclass(frozen=True)
class Dataset:
    name: str
    file: str
    target: str
    drop: tuple[str, ...]
    metric: str
    transform: str | None = None

    @property
    def mode(self) -> str:
        return MODE_BY_METRIC[self.metric]


@dataclass(frozen=True)
class Method:
    name: str
    mode: str
    n_params: str


@dataclass(frozen=True)
class Experiment:
    id: str
    dataset: str
    methods: tuple[str, ...]
    metric: str
    n_folds: int
    seed: int
    model_version: str
    row_sizes: tuple[int, ...] = ()

    @property
    def mode(self) -> str:
        return MODE_BY_METRIC[self.metric]

    @property
    def row_size_points(self) -> tuple[int | None, ...]:
        """The sizes this experiment is measured at, full last (#264).

        A declared size is a cap on the training rows; full is always a point, because an
        experiment quoted at its whole table is not an exception to its own axis, and the
        committed sweep already carries those rows. Declaring none therefore means full
        only -- which is what every experiment predating the axis means.
        """
        return (*self.row_sizes, None)


def resolve_row_size(experiment: Experiment, requested: int | None) -> int | None:
    """The declared point a run asked for, or a refusal naming the declaration (#264).

    `None` asks for the full table, which every experiment has. An integer must be one of
    the declared sizes: a point the declaration does not contain describes a measurement
    the experiment never claimed, so it is refused before anything is fitted.
    """
    if requested is None or requested in experiment.row_sizes:
        return requested
    declared = ", ".join(["full", *(str(n) for n in experiment.row_sizes)])
    raise RegistryError(
        f"experiment {experiment.id!r} is not declared at {requested} rows "
        f"(declared: {declared})"
    )


@dataclass(frozen=True)
class Registry:
    schema_version: int
    datasets: Mapping[str, Dataset]
    methods: Mapping[str, Mapping[str, Method]]
    experiments: Mapping[str, Experiment]

    def experiment(self, experiment_id: str) -> Experiment:
        """Look up one experiment, naming it when it does not exist."""
        try:
            return self.experiments[experiment_id]
        except KeyError:
            known = ", ".join(sorted(self.experiments)) or "none"
            raise RegistryError(
                f"unknown experiment {experiment_id!r} (registered: {known})"
            ) from None

    def dataset_of(self, experiment: Experiment) -> Dataset:
        return self.datasets[experiment.dataset]

    def methods_of(self, experiment: Experiment) -> tuple[Method, ...]:
        """The method entries an experiment compares, in its declared order."""
        table = self.methods[experiment.mode]
        return tuple(table[name] for name in experiment.methods)


# ---------------------------------------------------------------------------
# Fail-closed parsing
# ---------------------------------------------------------------------------
def _loc(path: Path, where: str) -> str:
    """`<file>: [section.entry]` — every rejection says which entry, and where it lives."""
    return f"{path}: [{where}]"


def _fail(loc: str, message: str) -> None:
    raise RegistryError(f"{loc} {message}")


def _check_keys(loc: str, entry: Mapping[str, Any], allowed: Iterable[str],
                hints: Mapping[str, str] | None = None) -> None:
    """Refuse keys this schema does not define, optionally saying why one is refused."""
    unknown = [key for key in entry if key not in allowed]
    if unknown:
        hints = hints or {}
        detail = "; ".join(f"{key!r} ({hints[key]})" if key in hints else repr(key)
                           for key in sorted(unknown))
        _fail(loc, f"unknown key(s): {detail}")


def _table(loc: str, entry: Any) -> Mapping[str, Any]:
    """A section entry that is not a table declares nothing; say so instead of crashing."""
    if not isinstance(entry, Mapping):
        _fail(loc, f"must be a table, got {entry!r}")
    return entry


def _require(loc: str, entry: Mapping[str, Any], key: str) -> Any:
    if key not in entry:
        _fail(loc, f"missing required key {key!r}")
    return entry[key]


def _typed(loc: str, entry: Mapping[str, Any], key: str, kind: type, label: str) -> Any:
    value = _require(loc, entry, key)
    # bool is an int subclass, and `n_folds = true` must not slip through
    if not isinstance(value, kind) or isinstance(value, bool) is not (kind is bool):
        _fail(loc, f"{key} must be {label}, got {value!r}")
    return value


def _integer(loc: str, entry: Mapping[str, Any], key: str, minimum: int) -> int:
    value = _typed(loc, entry, key, int, "an integer")
    if value < minimum:
        _fail(loc, f"{key} must be at least {minimum}, got {value}")
    return value


def _text(loc: str, entry: Mapping[str, Any], key: str) -> str:
    value = _typed(loc, entry, key, str, "a non-empty string")
    if not value.strip():
        _fail(loc, f"{key} must be a non-empty string")
    return value


def _choice(loc: str, value: Any, key: str, allowed: Iterable[str]) -> str:
    allowed = tuple(allowed)
    if value not in allowed:
        _fail(loc, f"{key} {value!r} is not one of: {', '.join(allowed)}")
    return value


def _decode(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        raise RegistryError(f"{path}: no such registry") from None
    except tomllib.TOMLDecodeError as exc:
        # Includes a duplicate id: the message names the key declared twice.
        raise RegistryError(f"{path}: {exc}") from None


def load_registry(path: str | Path) -> Registry:
    """Read an experiment registry, refusing anything it cannot fully account for."""
    path = Path(path)
    raw = _decode(path)

    if "schema_version" not in raw:
        raise RegistryError(f"{path}: missing required key 'schema_version'")
    schema_version = raw.pop("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise RegistryError(
            f"{path}: schema_version must be the integer {SCHEMA_VERSION}, "
            f"got {schema_version!r}"
        )
    if schema_version != SCHEMA_VERSION:
        raise RegistryError(
            f"{path}: schema_version {schema_version!r} is not the supported "
            f"{SCHEMA_VERSION}"
        )

    sections = {}
    for section in ("datasets", "methods", "experiments"):
        value = raw.pop(section, {})
        if not isinstance(value, Mapping):
            raise RegistryError(f"{_loc(path, section)} must be a table, got {value!r}")
        sections[section] = value
    if raw:
        unknown = ", ".join(sorted(raw))
        raise RegistryError(f"{path}: unknown top-level key(s): {unknown}")

    datasets = {
        name: _dataset(path, name, entry)
        for name, entry in sections["datasets"].items()
    }
    methods = {
        _choice(_loc(path, f"methods.{mode}"), mode, "method mode", MODES): {
            name: _method(path, mode, name, entry) for name, entry in table.items()
        }
        for mode, table in sections["methods"].items()
    }
    experiments = {
        name: _experiment(path, name, entry, datasets, methods)
        for name, entry in sections["experiments"].items()
    }

    return Registry(
        schema_version=schema_version,
        datasets=MappingProxyType(datasets),
        methods=MappingProxyType({m: MappingProxyType(t) for m, t in methods.items()}),
        experiments=MappingProxyType(experiments),
    )


def _dataset(path: Path, name: str, entry: Mapping[str, Any]) -> Dataset:
    loc = _loc(path, f"datasets.{name}")
    entry = _table(loc, entry)
    _check_keys(loc, entry, _DATASET_KEYS)

    metric = _choice(loc, _require(loc, entry, "metric"), "metric", MODE_BY_METRIC)
    drop = _require(loc, entry, "drop")
    if not isinstance(drop, list) or not all(isinstance(c, str) for c in drop):
        _fail(loc, f"drop must be a list of column names, got {drop!r}")
    transform = entry.get("transform")
    if transform is not None:
        _choice(loc, transform, "transform", TRANSFORMS)

    return Dataset(
        name=name,
        file=_text(loc, entry, "file"),
        target=_text(loc, entry, "target"),
        drop=tuple(drop),
        metric=metric,
        transform=transform,
    )


def _method(path: Path, mode: str, name: str, entry: Mapping[str, Any]) -> Method:
    loc = _loc(path, f"methods.{mode}.{name}")
    entry = _table(loc, entry)
    _check_keys(loc, entry, _METHOD_KEYS)

    return Method(
        name=name,
        mode=mode,
        n_params=_choice(loc, _require(loc, entry, "n_params"), "n_params", N_PARAMS_RULES),
    )


def _experiment(
    path: Path,
    name: str,
    entry: Mapping[str, Any],
    datasets: Mapping[str, Dataset],
    methods: Mapping[str, Mapping[str, Method]],
) -> Experiment:
    loc = _loc(path, f"experiments.{name}")
    entry = _table(loc, entry)
    _check_keys(loc, entry, _EXPERIMENT_KEYS,
                hints={"metric": "the metric belongs to the dataset it names"})

    dataset_name = _text(loc, entry, "dataset")
    if dataset_name not in datasets:
        _fail(loc, f"references unknown dataset {dataset_name!r}")
    dataset = datasets[dataset_name]

    names = _require(loc, entry, "methods")
    if (not isinstance(names, list) or not names
            or not all(isinstance(m, str) for m in names)):
        _fail(loc, f"methods must be a non-empty list of method ids, got {names!r}")
    duplicates = sorted({m for m in names if names.count(m) > 1})
    if duplicates:
        _fail(loc, f"lists method {duplicates[0]!r} more than once")

    table = methods.get(dataset.mode, {})
    for method in names:
        if method not in table:
            _fail(loc, f"references unknown {dataset.mode} method {method!r}")

    row_sizes = entry.get("row_sizes", [])
    if not isinstance(row_sizes, list) or not all(
        isinstance(n, int) and not isinstance(n, bool) and n >= 1 for n in row_sizes
    ):
        _fail(loc, f"row_sizes must be a list of positive integers, got {row_sizes!r}")
    repeated = sorted({n for n in row_sizes if row_sizes.count(n) > 1})
    if repeated:
        _fail(loc, f"declares row size {repeated[0]} more than once")

    return Experiment(
        id=name,
        dataset=dataset_name,
        methods=tuple(names),
        metric=dataset.metric,
        n_folds=_integer(loc, entry, "n_folds", minimum=2),
        seed=_integer(loc, entry, "seed", minimum=0),
        model_version=_text(loc, entry, "model_version"),
        row_sizes=tuple(row_sizes),
    )


FOLD_KINDS = ("stratified", "kfold")


def make_folds(kind: str, n_folds: int, seed: int):
    """One configured splitter, so two scripts cannot build two different splits.

    `stratified` is for a class target, `kfold` for a continuous or count target. The
    caller passes the experiment's fold count and seed; a different caller that follows
    the same rule gets the same indices. An unknown kind is refused rather than guessed.
    """
    if kind == "stratified":
        from sklearn.model_selection import StratifiedKFold

        return StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    if kind == "kfold":
        from sklearn.model_selection import KFold

        return KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    raise RegistryError(
        f"unknown fold kind {kind!r}; expected one of: {', '.join(FOLD_KINDS)}"
    )


def datasets_by_mode(registry: Registry, mode: str) -> tuple[Dataset, ...]:
    """Every Dataset of one mode, in the registry's declared order.

    Scripts that loop over datasets use this instead of a private list. An unknown mode is
    refused rather than returning an empty tuple that would silently run nothing.
    """
    if mode not in MODES:
        raise RegistryError(f"unknown mode {mode!r}; expected one of: {', '.join(MODES)}")
    return tuple(dataset for dataset in registry.datasets.values() if dataset.mode == mode)


def dataset_entry(dataset: Dataset) -> dict[str, Any]:
    """The dataset entry the v1 runners' `load_Xy`/capture functions already take.

    `name` is the *dataset's*: output filenames, the sweep join and the capture stem are
    keyed to the data being measured, and discovery by `{dataset}__seed{s}__*` must keep
    resolving. The dict shape is the seam `load_Xy` takes; the registry owns the values.
    """
    entry: dict[str, Any] = {
        "name": dataset.name,
        "file": dataset.file,
        "target": dataset.target,
        "drop": list(dataset.drop),
        "metric": dataset.metric,
    }
    if dataset.transform:
        entry["transform"] = dataset.transform
    return entry


def load_dataset_entries(path: str | Path, mode: str) -> list[dict[str, Any]]:
    """Every Dataset entry of one mode, for a producer that only needs the entries."""
    return [dataset_entry(dataset) for dataset in datasets_by_mode(load_registry(path), mode)]


def mode_methods(registry: Registry, mode: str) -> tuple[Method, ...]:
    """The method list every experiment of one mode declares, refusing disagreement.

    Producers that are not themselves experiments (the reframe study, the rescore) lift
    the mode's method set from the registry instead of picking an arbitrary anchor
    experiment. If two experiments in a mode ever declare different methods, those
    scripts can no longer claim one canonical set, so the load fails loudly.
    """
    experiments = [e for e in registry.experiments.values() if e.mode == mode]
    if not experiments:
        raise RegistryError(f"no experiments for mode {mode!r}")
    lists = {experiment.methods for experiment in experiments}
    if len(lists) != 1:
        raise RegistryError(
            f"{mode} experiments disagree about which methods they compare: "
            f"{sorted(lists)}"
        )
    return registry.methods_of(experiments[0])

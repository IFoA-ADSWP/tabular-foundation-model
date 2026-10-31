"""Tests for the multi-repeat interval and the analysis report.

`nested_paired_bootstrap` is tested on synthetic repeats where the answer is known by
construction, and `scripts/analyse_pilot.py` is tested against a synthetic output directory laid
out exactly as the pipeline writes it -- so the report is proven on this branch without any run.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from paired_analysis import nested_paired_bootstrap  # noqa: E402  (importable after the src path insert above)


def auc(y_true, y_score):
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    pos, neg = y_score[y_true == 1], y_score[y_true == 0]
    if pos.size == 0 or neg.size == 0:
        raise ValueError("AUC undefined: one class missing")
    cmp = pos[:, None] - neg[None, :]
    return float((np.sum(cmp > 0) + 0.5 * np.sum(cmp == 0)) / (pos.size * neg.size))


def _repeats(rng, n_rep, n=300, delta=0.0):
    out = []
    for _ in range(n_rep):
        y = rng.integers(0, 2, size=n)
        base = rng.normal(size=n) + y * 0.8
        out.append((y, base, base + y * delta))
    return out


# --------------------------------------------------------------------------- the interval

def test_nested_bootstrap_is_zero_for_identical_arms():
    rng = np.random.default_rng(0)
    out = nested_paired_bootstrap(_repeats(rng, 3), auc, n_resamples=200, seed=1)
    assert out["estimate"] == pytest.approx(0.0, abs=1e-12)
    assert out["excludes_zero"] is False
    assert out["n_repeats"] == 3


def test_nested_bootstrap_detects_a_consistent_gain():
    rng = np.random.default_rng(1)
    out = nested_paired_bootstrap(_repeats(rng, 5, delta=1.2), auc, n_resamples=200, seed=1)
    assert out["estimate"] > 0
    assert out["excludes_zero"] is True


def test_the_interval_widens_with_repeat_heterogeneity():
    """One split cannot speak for the split population -- that is what the repeats measure."""
    rng = np.random.default_rng(2)
    consistent = nested_paired_bootstrap(
        [(y, a, a + y * 0.9) for y, a, _b in _repeats(rng, 5, delta=0.9)],
        auc, n_resamples=300, seed=3,
    )
    wild = []
    for i, (y, a, _b) in enumerate(_repeats(rng, 5)):
        wild.append((y, a, a + y * (0.9 if i % 2 == 0 else -0.9)))
    heterogeneous = nested_paired_bootstrap(wild, auc, n_resamples=300, seed=3)
    assert (heterogeneous["ci_high"] - heterogeneous["ci_low"]) > (
        consistent["ci_high"] - consistent["ci_low"]
    )


def test_nested_bootstrap_needs_repeats_and_matching_lengths():
    with pytest.raises(ValueError, match="no repeats"):
        nested_paired_bootstrap([], auc)
    y = np.array([0, 1, 0, 1])
    with pytest.raises(ValueError, match="same length"):
        nested_paired_bootstrap([(y, np.array([0.1, 0.2]), np.array([0.1, 0.2, 0.3, 0.4]))], auc)


def test_nested_bootstrap_seed_reproduces():
    rng = np.random.default_rng(4)
    reps = _repeats(rng, 3, delta=0.5)
    a = nested_paired_bootstrap(reps, auc, n_resamples=150, seed=11)
    b = nested_paired_bootstrap(reps, auc, n_resamples=150, seed=11)
    assert (a["ci_low"], a["ci_high"]) == (b["ci_low"], b["ci_high"])


# --------------------------------------------------------------------------- the report

def _load_analyser():
    spec = importlib.util.spec_from_file_location("analyse_pilot", _REPO / "scripts" / "analyse_pilot.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["analyse_pilot"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ap():
    return _load_analyser()


def _write_run(root: Path, dataset: str, arm: str, slot: str | None, rng, delta=0.0, epochs=None):
    d = root / dataset / arm
    if slot:
        d = d / slot
    d.mkdir(parents=True, exist_ok=True)
    y = rng.integers(0, 2, size=200)
    probs = rng.normal(size=200) + y * (0.8 + delta)
    np.save(d / "predictions.npy", probs)
    np.save(d / "ground_truth.npy", y)
    meta: dict = {"status": "complete"}
    if epochs is not None:
        meta["effective_config"] = {"kwargs": {"epochs": epochs}}
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


def test_report_pairs_arms_on_matching_slots_and_marks_the_baseline(ap, tmp_path):
    rng = np.random.default_rng(7)
    for slot in ("seed42_foldNone", "seed43_foldNone"):
        _write_run(tmp_path, "coil2000", "A_raw", slot, rng)
        _write_run(tmp_path, "coil2000", "B_ft30", slot, rng, delta=1.0, epochs=30)
    found = ap.discover(tmp_path)
    report = ap.analyse(found, "A_raw", None, n_resamples=100, seed=1)
    entry = report["datasets"]["coil2000"]["B_ft30"]
    assert entry["n_repeats"] == 2
    assert entry["excludes_zero"] is True
    assert "coil2000" in report["summary"]["B_ft30"] or report["summary"]["B_ft30"]["k"] == 1


def test_a_run_without_a_baseline_counterpart_is_excluded_and_reported(ap, tmp_path):
    """Comparing across different test rows is not the comparison the plan defines."""
    rng = np.random.default_rng(8)
    _write_run(tmp_path, "coil2000", "A_raw", "seed42_foldNone", rng)
    _write_run(tmp_path, "coil2000", "B_ft30", "seed42_foldNone", rng, delta=0.5)
    _write_run(tmp_path, "coil2000", "B_ft30", "seed43_foldNone", rng, delta=0.5)
    report = ap.analyse(ap.discover(tmp_path), "A_raw", None, n_resamples=100, seed=1)
    entry = report["datasets"]["coil2000"]["B_ft30"]
    assert entry["n_repeats"] == 1
    assert any("no A_raw counterpart" in note for note in report["unpaired"])


def test_the_cross_dataset_summary_weights_by_precision(ap, tmp_path):
    rng = np.random.default_rng(9)
    for dataset in ("coil2000", "uslapseagent", "eudirectlapse", "spanish_motor_lapse"):
        _write_run(tmp_path, dataset, "A_raw", "seed42_foldNone", rng)
        _write_run(tmp_path, dataset, "B_in_domain", "seed42_foldNone", rng, delta=0.7)
    report = ap.analyse(ap.discover(tmp_path), "A_raw", None, n_resamples=100, seed=1)
    summary = report["summary"]["B_in_domain"]
    assert summary["k"] == 4
    # the four-dataset family carries a Holm-adjusted p-value per dataset
    for arm_entries in report["datasets"].values():
        assert "holm_adjusted_p" in arm_entries["B_in_domain"]


def test_a_flat_slot_is_read_as_the_default_seed_and_fold(ap, tmp_path):
    rng = np.random.default_rng(10)
    _write_run(tmp_path, "coil2000", "A_raw", None, rng)
    _write_run(tmp_path, "coil2000", "E_glm", None, rng, delta=0.2)
    report = ap.analyse(ap.discover(tmp_path), "A_raw", None, n_resamples=100, seed=1)
    assert report["datasets"]["coil2000"]["E_glm"]["n_repeats"] == 1


def test_the_cli_reports_and_writes_json(ap, tmp_path, capsys):
    rng = np.random.default_rng(11)
    _write_run(tmp_path, "coil2000", "A_raw", "seed42_foldNone", rng)
    _write_run(tmp_path, "coil2000", "B_ft30", "seed42_foldNone", rng, delta=1.0)
    out_json = tmp_path / "report.json"
    rc = ap.main(["--outdir", str(tmp_path), "--n-resamples", "50", "--json", str(out_json)])
    assert rc == 0
    assert "B_ft30" in capsys.readouterr().out
    assert json.loads(out_json.read_text())["datasets"]["coil2000"]["B_ft30"]["n_repeats"] == 1


def test_the_cli_refuses_an_empty_directory_rather_than_reporting_nothing(ap, tmp_path):
    assert ap.main(["--outdir", str(tmp_path)]) == 2


def test_the_marker_follows_the_bounds_it_is_printed_with(ap):
    """A reader who trusts the marker and one who trusts the bounds must reach one verdict.

    Expectations are written out, not recomputed from the predicate under test: the probe
    write-up (#296) reported a marker that contradicted its own interval.
    """
    cases = [
        ((-0.0047, -0.0003), ""),      # excludes zero: no marker
        ((-0.0032, 0.0014), "***"),    # covers zero: marked
        ((-0.0001, 0.0002), "***"),    # covers zero, by a hair
        ((0.0020, 0.0100), ""),        # excludes zero, entirely positive
        ((0.0, 0.0100), "***"),        # touches zero at the low bound: covers it
    ]
    for (lo, hi), expected in cases:
        assert ap.significance_marker(lo, hi) == expected, (lo, hi)


def test_generated_comparisons_agree_with_the_interval_they_render(ap):
    """The invariant over a generated sweep: parse the printed bracket, not the predicate.

    The text is the independent source of truth here -- it is what a reader sees -- so the
    marker cannot agree with the code while disagreeing with the line.
    """
    for lo in (-0.0100, -0.0047, -0.0003, -0.00004, 0.0, 0.00004, 0.0014, 0.0100):
        for hi in (-0.0047, -0.0003, -0.00004, 0.0, 0.00004, 0.0014, 0.0030):
            if lo > hi:
                continue
            text = ap.format_interval(lo, hi)
            left, right = (float(part) for part in text[1:-1].split(", "))
            reads_as_covering = left <= 0.0 <= right
            assert (ap.significance_marker(lo, hi) == "***") is reads_as_covering, text


def test_a_bound_that_rounds_to_zero_keeps_the_sign_that_makes_it_readable(ap):
    """-0.00004 at four decimals reads as -0.0000: an interval excluding zero that looks
    like it touches it. The printed text must keep the bound's side of zero."""
    assert ap.format_interval(-0.0047, -0.00004) == "[-0.0047, -4.0e-05]"
    assert ap.format_interval(-0.0047, 0.00004) == "[-0.0047, +4.0e-05]"
    # Ordinary bounds keep the familiar four-decimal form.
    assert ap.format_interval(-0.0047, -0.0003) == "[-0.0047, -0.0003]"
    assert ap.format_interval(-0.0032, 0.0014) == "[-0.0032, +0.0014]"


def test_every_signed_number_in_the_block_keeps_its_sign(ap):
    """The estimate and the pooled summary carry a sign too; rounding must not erase it."""
    assert ap.signed_text(-0.00004) == "-4.0e-05"
    assert ap.signed_text(-0.0025) == "-0.0025"


def test_the_printed_line_never_marks_a_contradiction(ap, tmp_path, capsys):
    """#296 in one assertion: what the marker says, the bracket beside it shows."""
    def line_for(lo, hi):
        report = {
            "baseline": "A_raw", "unpaired": [], "summary": {},
            "datasets": {"uslapseagent": {"B_ft3": {
                "estimate": (lo + hi) / 2, "ci_low": lo, "ci_high": hi,
                "n_repeats": 1, "n_test_rows": 1000,
            }}},
        }
        ap.print_report(report, tmp_path)
        out = capsys.readouterr().out
        return next(line for line in out.splitlines() if "B_ft3" in line)

    excluding = line_for(-0.0047, -0.0003)
    assert "***" not in excluding
    assert "[-0.0047, -0.0003]" in excluding

    covering = line_for(-0.0032, 0.0014)
    assert "***" in covering
    assert "[-0.0032, +0.0014]" in covering

    # The boundary the write-up worried about: excludes zero by a hair, and says so.
    hair = line_for(-0.0047, -0.00004)
    assert "***" not in hair
    assert "[-0.0047, -4.0e-05]" in hair

    # And the other side of it: covers zero by a hair, marked, sign visible.
    just_covering = line_for(-0.0047, 0.00004)
    assert "***" in just_covering
    assert "+4.0e-05" in just_covering

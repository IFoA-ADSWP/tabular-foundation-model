"""The fair test's launch path (#564): primary mode exists, and a refused capture keeps the box.

The gate ran the primary comparison and shipped only a summary, so the 120 fits were lost with the
instance. Two things had to change for that not to repeat: `--fairtest primary` must exist at all
(`FAIRTEST=gate` was the only mode the bootstrap accepted), and a capture that did not arrive must
not be paid for twice -- destroying the instance discards the fits along with the fault.

These drive the real launcher against `mock_vastai.sh`, so nothing is provisioned and nothing is
spent.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_pilot2_seed_passthrough import _launch


def test_primary_below_the_poll_ceiling_is_refused_before_provisioning(tmp_path):
    """40 min cannot cover an hour of fits plus the paced transfer, so the default is refused."""
    state, result = _launch(tmp_path, "--fairtest", "primary", "--poll-minutes", "40")
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "is below the" in combined and "target(s)" in combined, combined
    assert not (state / "created.txt").exists(), "the refusal happened after provisioning"


def test_primary_is_refused_on_the_ssh_transport_it_cannot_use(tmp_path):
    """The ssh pull copies into the run tree; a capture has to land in results/."""
    state, result = _launch(
        tmp_path, "--fairtest", "primary", "--poll-minutes", "180", "--transport", "ssh"
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "wired for the log transport only" in combined, combined
    assert not (state / "created.txt").exists()


def test_a_payload_that_is_not_four_captures_is_refused_and_the_instance_is_kept(tmp_path):
    """The failure that cost the gate's evidence: a payload that arrives but is not a capture.

    The mock box emits one ordinary block, which is not four chunked captures carrying their run
    ids. The launch must refuse it AND leave the instance alone -- an hour of paid fits is on that
    box, and the transfer can be retried from it.
    """
    tree = tmp_path / "captures"
    tree.mkdir()
    (tree / "capture.json").write_text(json.dumps({"schema_version": 4, "captures": []}))

    state, result = _launch(
        tmp_path,
        "--fairtest", "primary",
        "--poll-minutes", "180",
        extra_env={"MOCK_OUTPUT_TREE": str(tree)},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 1, combined
    assert "capture payload is incomplete" in combined, combined
    assert "KEEPING the instance" in combined, combined
    assert not (state / "destroyed.txt").exists(), (
        "the capture never arrived and the instance holding the fits was destroyed anyway"
    )


def _target_tree(tmp_path, count=4):
    """Four sealed v4 captures, laid out as the box leaves them under results/."""
    import sys

    from tests.test_chunked_capture_transport import _slot

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from run_capture import build_capture, render_capture

    tree = tmp_path / "captures"
    ids = [f"20261112T09000{index}Z" for index in range(count)]
    for run_id in ids:
        run = tree / run_id
        run.mkdir(parents=True)
        _slot(run, 0)
        (run / "capture.json").write_text(render_capture(build_capture(run)))
    return tree, ids


def test_a_primary_launch_restores_four_captures_into_results(tmp_path):
    """The success path, end to end through the launcher: chunks in, results/<id>/ out.

    Without this the transport could pass in isolation and still be overwritten by the
    launcher's single-window copy -- which is exactly what happened on the first cut of #564.
    """
    tree, ids = _target_tree(tmp_path)

    state, result = _launch(
        tmp_path,
        "--fairtest", "primary",
        "--poll-minutes", "180",
        extra_env={
            "MOCK_OUTPUT_TREE": str(tree),
            "MOCK_PER_TARGET": "1",
            "TFM_CHUNK_LINES": "3",
            "TFM_CHUNK_PAUSE": "0",
        },
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "4 capture(s) restored and capturable" in combined, combined
    results = tmp_path / "repo" / "results"
    assert sorted(path.name for path in results.iterdir()) == sorted(ids), combined
    for run_id in ids:
        assert (results / run_id / "capture.json").is_file(), combined
    assert (state / "destroyed.txt").exists(), "a successful run must release the instance"


def test_a_canary_launch_restores_one_capture_for_one_target(tmp_path):
    """One target first is how ~20 minutes is risked instead of ~105 (#566).

    The registered matrix is four targets; a narrower list must also narrow what verification
    expects, or a correct canary is refused for restoring one capture instead of four.
    """
    tree, ids = _target_tree(tmp_path, count=1)

    state, result = _launch(
        tmp_path,
        "--fairtest", "primary",
        "--poll-minutes", "180",
        extra_env={
            "MOCK_OUTPUT_TREE": str(tree),
            "MOCK_PER_TARGET": "1",
            "TFM_CHUNK_LINES": "3",
            "TFM_CHUNK_PAUSE": "0",
            "TFM_FAIRTEST_TARGETS": "frequency_french",
        },
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 capture(s) restored and capturable" in combined, combined
    assert sorted(path.name for path in (tmp_path / "repo" / "results").iterdir()) == ids
    assert (state / "destroyed.txt").exists()

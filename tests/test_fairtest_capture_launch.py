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

from tests.test_pilot2_seed_passthrough import _launch


def test_primary_below_the_poll_ceiling_is_refused_before_provisioning(tmp_path):
    """40 min cannot cover an hour of fits plus the paced transfer, so the default is refused."""
    state, result = _launch(tmp_path, "--fairtest", "primary", "--poll-minutes", "40")
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "below the ~160 min a primary run needs" in combined, combined
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

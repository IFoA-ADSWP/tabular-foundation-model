"""`--yes` answers the leak preflight too (#423).

The preflight warns about billing `tabpfn-pilot*` instances and asks "Continue anyway?". With
`--yes` documented as "skip the confirmation prompt", a second launch in a batch still hit that
`read`, got EOF without a TTY, and aborted before provisioning -- so parallel batches were
impossible without piping `y` into a prompt whose purpose is to catch money leaking.

These drive the real launcher against the mock, which reports a sibling instance when asked.
"""

from __future__ import annotations

from tests.test_pilot2_seed_passthrough import _launch


def test_yes_continues_past_a_sibling_instance(tmp_path):
    """The concurrent case: the billing instance is this wave's own sibling, not a leak."""
    state, result = _launch(
        tmp_path,
        "--arms", "A_raw",
        extra_env={"MOCK_SIBLINGS": "1"},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "--yes: continuing" in combined, combined
    assert (state / "created.txt").exists(), "the launch aborted before provisioning anyway"


def test_without_yes_the_preflight_still_aborts(tmp_path):
    """A bare Enter must still refuse: the warning is real when nobody said --yes."""
    state, result = _launch(
        tmp_path,
        "--arms", "A_raw",
        assume_yes=False,
        extra_env={"MOCK_SIBLINGS": "1"},
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "aborted" in combined, combined
    assert not (state / "created.txt").exists(), "an unconfirmed launch provisioned a box"

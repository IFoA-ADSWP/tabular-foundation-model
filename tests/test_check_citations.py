"""The citation check (#364): a run cited in docs/ must have a capture.

Tests write a small repository tree and run the real checker over it, because the seam is the
tree a colleague would open — not the functions inside the script.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_citations.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load():
    spec = importlib.util.spec_from_file_location("check_citations", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load()

RUN = "20261102T101010Z"


def make_repo(
    tmp_path: Path,
    *,
    cite: str = RUN,
    manifest: dict | None = None,
    legacy: list[str] | None = None,
    arm: str = "A_raw",
    seed: int = 43,
) -> Path:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "analysis.md").write_text(
        f"The run `{cite}` produced these numbers.\n"
    )
    (root / "docs" / "analyses").mkdir()
    if legacy is not None:
        (root / "docs" / "analyses" / "legacy_citations.txt").write_text(
            "# header\n" + "\n".join(legacy) + "\n"
        )
    arm_dir = root / "results" / RUN / "uslapseagent" / arm / f"seed{seed}_foldNone"
    arm_dir.mkdir(parents=True)
    (arm_dir / "meta.json").write_text(
        json.dumps({"arm": arm, "seed": seed, "test_rows": 1000})
    )
    if manifest is not None:
        (root / "results" / RUN / "capture.json").write_text(json.dumps(manifest))
    return root


def entry(arm="A_raw", seed=43, **overrides):
    base = {
        "arm": arm,
        "seed": seed,
        "rows": 1000,
        "predictions_sha256": "a" * 64,
        "truth_sha256": "b" * 64,
        "record": f"{arm}/seed{seed}_foldNone/meta.json",
        "reason": None,
    }
    base.update(overrides)
    return base


def manifest(*entries):
    return {
        "schema_version": 1,
        "run_id": RUN,
        "dataset": "uslapseagent",
        "created_utc": "2026-11-02T10:10:00Z",
        "captures": list(entries),
    }


def run(root: Path) -> int:
    return cc.main(["--root", str(root)])


def test_a_complete_capture_passes(tmp_path):
    assert run(make_repo(tmp_path, manifest=manifest(entry()))) == 0


def test_a_cited_run_with_no_capture_fails(tmp_path):
    root = make_repo(tmp_path, manifest=None)
    assert run(root) == 1


def test_a_manifest_missing_an_arm_fails(tmp_path):
    root = make_repo(tmp_path, manifest=manifest())
    assert run(root) == 1


def test_an_entry_with_null_hashes_fails_and_quotes_the_reason(tmp_path):
    root = make_repo(
        tmp_path,
        manifest=manifest(
            entry(
                predictions_sha256=None,
                truth_sha256=None,
                reason="not retained in this run",
            )
        ),
    )
    assert run(root) == 1


def test_a_legacy_id_is_exempt(tmp_path):
    old = "20260912T144012Z"
    root = make_repo(tmp_path, cite=old, manifest=None, legacy=[old])
    assert run(root) == 0


def test_a_post_rule_id_cannot_be_grandfathered(tmp_path):
    root = make_repo(tmp_path, manifest=manifest(entry()), legacy=[RUN])
    assert run(root) == 1


def test_a_launch_id_alone_cites_nothing(tmp_path):
    root = make_repo(tmp_path, cite=f"{RUN}-6c2758", manifest=None)
    (root / "results" / RUN / "uslapseagent" / "A_raw" / "seed43_foldNone").mkdir(
        parents=True, exist_ok=True
    )
    assert run(root) == 0


def test_mentions_outside_docs_are_not_scanned(tmp_path):
    root = make_repo(tmp_path, manifest=manifest(entry()))
    (root / "README.md").write_text(f"A run {RUN} mentioned in the root readme.\n")
    assert run(root) == 0


def test_a_failure_names_the_file_and_line_that_cited_the_id(tmp_path):
    """The operator's next action is to open the document, so name the line.

    Before this, a refusal said only `20261102T101010Z: cited but no capture.json` and finding
    the offending sentence meant grepping `docs/` — twice per occurrence, because the id also
    appears under `results/`.
    """
    root = make_repo(tmp_path, manifest=None)
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        assert run(root) == 1

    message = stderr.getvalue()
    assert "docs/analysis.md:1" in message, message
    assert "cited at" in message, message

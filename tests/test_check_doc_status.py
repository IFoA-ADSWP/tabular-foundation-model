"""Tests for the documentation status check."""
from __future__ import annotations

import pathlib

from scripts.check_doc_status import (
    CLAIM_REGISTRY,
    DEFAULT_DIRS,
    campaign_readme_problems,
    experiment_count_problems,
    index_problems,
    main,
    registry_problems,
    unlabelled,
    citation_problems,
)


def _write(tmp_path: pathlib.Path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text)


def _registry(tmp_path: pathlib.Path, rows: str) -> pathlib.Path:
    path = tmp_path / "FINDINGS.md"
    path.write_text(
        "> **Status:** current\n\n| Claim | Status | Owner |\n| --- | --- | --- |\n" + rows
    )
    return path


def test_marked_report_passes(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "marked.md", "> **Historical document.** Superseded by X.\n\nbody\n")
    missing, total = unlabelled(tmp_path)
    assert missing == []
    assert total == 1


def test_unmarked_report_is_listed(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "bare.md", "# A report\n\nBody text mentioning the current design.\n")
    missing, total = unlabelled(tmp_path)
    assert missing == ["bare.md"]
    assert total == 1


def test_titles_do_not_pass_but_markers_below_the_window_do_not_either(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "late.md", "\n".join(["# A report"] + ["filler"] * 20 + ["> **Status:** current"]))
    missing, _ = unlabelled(tmp_path)
    assert missing == ["late.md"], "a marker past the window is not a status"


def test_default_scope_is_the_report_trees(tmp_path: pathlib.Path, monkeypatch) -> None:
    """The default must reach the experiment, shared and archive trees -- not the dissolved docs/reports/.

    Two moves have broken this default before: #200-#202 dissolved docs/reports/ and left the check
    pointing at it, so it exited 2 and enforced nothing; #595 replaced the three status directories
    with the campaign tree. A default that reaches no documents is worse than no check.
    """
    assert set(DEFAULT_DIRS) == {"docs/experiments", "docs/shared", "docs/archive"}
    for tier in DEFAULT_DIRS:
        (tmp_path / tier).mkdir(parents=True)
    (tmp_path / "docs/experiments/marked.md").write_text("> **Status:** current\n\nbody\n")
    (tmp_path / "docs/archive/bare.md").write_text("# A report\n\nbody\n")

    monkeypatch.chdir(tmp_path)
    assert main([]) == 1, "a bare report in archive/ must fail the run"


def test_each_tier_can_be_checked_on_its_own(tmp_path: pathlib.Path, monkeypatch) -> None:
    for tier in ("current", "reference"):
        (tmp_path / tier).mkdir()
    (tmp_path / "current/marked.md").write_text("> **Status:** current\n")
    (tmp_path / "reference/bare.md").write_text("# A report\n\nbody\n")

    monkeypatch.chdir(tmp_path)
    assert main(["--dir", "current"]) == 0
    assert main(["--dir", "current", "--dir", "reference"]) == 1


def test_a_missing_directory_fails_rather_than_passing_silently(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--dir", "docs/reports"]) == 2



def test_a_registry_row_that_restates_a_number_fails(tmp_path: pathlib.Path) -> None:
    """The failure this check exists to stop: a copied number that drifts from its owner."""
    problems = registry_problems(
        _registry(tmp_path, "| **F1** beats raw at 10,000 training rows | current | docs/owner.md |\n")
    )
    assert len(problems) == 1
    assert "F1" in problems[0] and "restates a number" in problems[0]


def test_row_ids_and_dates_are_identifiers_not_numbers(tmp_path: pathlib.Path) -> None:
    problems = registry_problems(
        _registry(
            tmp_path,
            "| **L3** superseded by F1 on 2026-11-08 | superseded | docs/owner.md |\n",
        )
    )
    assert problems == [], "an id or a date is not a measurement"


def test_a_registry_row_must_be_three_columns(tmp_path: pathlib.Path) -> None:
    problems = registry_problems(
        _registry(tmp_path, "| F1 | a claim | current | docs/owner.md |\n")
    )
    assert len(problems) == 1
    assert "Claim | Status | Owner" in problems[0]


def test_a_moved_registry_fails_rather_than_passing_silently(tmp_path: pathlib.Path) -> None:
    problems = registry_problems(tmp_path / "gone.md")
    assert problems and "missing claim registry" in problems[0]


def test_the_committed_registry_carries_no_numbers() -> None:
    """The shipped artefact, not a fixture: this is the check running on the real page."""
    root = pathlib.Path(__file__).resolve().parents[1]
    assert registry_problems(root / CLAIM_REGISTRY) == []


def test_an_index_that_misses_a_document_is_reported(tmp_path: pathlib.Path) -> None:
    """A hand-written index drifts on the next merge.

    docs/plans/README.md was one document short within a day of landing: #580 generated
    it, #576 added another plan, and nothing noticed. The check lives in this job rather
    than a ninth one, following #489.
    """
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "README.md").write_text("| [`a.md`](a.md) |\n")
    (plans / "a.md").write_text("x\n")
    (plans / "b.md").write_text("x\n")

    problems = index_problems(tmp_path)

    assert len(problems) == 1
    assert "b.md" in problems[0]


def test_a_complete_index_is_not_reported(tmp_path: pathlib.Path) -> None:
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "README.md").write_text("| [`a.md`](a.md) | [`b.md`](b.md) |\n")
    (plans / "a.md").write_text("x\n")
    (plans / "b.md").write_text("x\n")

    assert index_problems(tmp_path) == []


def _campaign(tmp_path: pathlib.Path, name: str, docs: int, archived: int, runs: int) -> None:
    live = tmp_path / "docs" / "experiments" / name
    live.mkdir(parents=True)
    (live / "README.md").write_text("# x\n\n```\n" + "\n".join(f"2026010{i}T000000Z" for i in range(runs)) + "\n```\n")
    for i in range(docs):
        (live / f"doc{i}.md").write_text("> **Status:** current\n")
    if archived:
        old = tmp_path / "docs" / "archive" / name
        old.mkdir(parents=True)
        for i in range(archived):
            (old / f"old{i}.md").write_text("> **Status:** archive\n")


def _table(tmp_path: pathlib.Path, rows: str) -> None:
    (tmp_path / "docs" / "EXPERIMENTS.md").write_text("| Campaign | Documents | Runs |\n| --- | --- | --- |\n" + rows)


def test_a_stale_campaign_count_is_reported(tmp_path: pathlib.Path) -> None:
    """Both halves of this drifted within a day of the table being written.

    #598 added two documents to the fair test after the row was written, and the frontier row kept
    saying 0 runs after its README started naming four. Both were counts nobody checked.
    """
    _campaign(tmp_path, "fair-test", docs=2, archived=0, runs=1)
    _table(tmp_path, "| [`fair-test`](experiments/fair-test/README.md) | 1 live, 0 archived | 1 |\n")

    problems = experiment_count_problems(tmp_path)

    assert len(problems) == 1
    assert "1 live / 0 archived / 1 runs" in problems[0]
    assert "2 / 0 / 1" in problems[0]


def test_correct_counts_are_not_reported(tmp_path: pathlib.Path) -> None:
    _campaign(tmp_path, "fair-test", docs=2, archived=1, runs=3)
    _table(tmp_path, "| [`fair-test`](experiments/fair-test/README.md) | 2 live, 1 archived | 3 |\n")

    assert experiment_count_problems(tmp_path) == []


def test_a_campaign_with_no_row_is_reported(tmp_path: pathlib.Path) -> None:
    _campaign(tmp_path, "orphan", docs=1, archived=0, runs=0)
    _table(tmp_path, "")

    problems = experiment_count_problems(tmp_path)

    assert any("orphan" in p and "no row" in p for p in problems)


def _campaign_readme(tmp_path: pathlib.Path, *, header: str | None, rows: tuple[str, ...], documents: tuple[str, ...]) -> None:
    """A campaign directory with the documents it holds and the README that should list them."""
    directory = tmp_path / "docs" / "experiments" / "demo"
    directory.mkdir(parents=True)
    for name in documents:
        (directory / name).write_text("> **Status:** current\n")
    table = "\n".join(f"| [`{name}`]({name}) | current | what it is |" for name in rows)
    (directory / "README.md").write_text(
        "# Demo\n\n> **Status:** index.\n\n"
        + (f"{header}\nRead them below.\n\n" if header else "")
        + "| Document | Status | What |\n|---|---|---|\n"
        + table
        + "\n"
    )


def test_a_campaign_readme_that_agrees_with_its_directory_is_not_reported(tmp_path: pathlib.Path) -> None:
    _campaign_readme(tmp_path, header="**2 documents.**", rows=("a.md", "b.md"), documents=("a.md", "b.md"))
    assert campaign_readme_problems(tmp_path) == []


def test_a_campaign_header_that_undercounts_is_reported(tmp_path: pathlib.Path) -> None:
    # The frontier-benchmark failure: ten rows, a header saying eight.
    _campaign_readme(tmp_path, header="**2 documents.**", rows=("a.md", "b.md", "c.md"),
              documents=("a.md", "b.md", "c.md"))
    problems = campaign_readme_problems(tmp_path)
    assert any("says 2 documents, the directory has 3" in problem for problem in problems)


def test_a_document_with_no_row_is_reported_even_when_the_count_matches(tmp_path: pathlib.Path) -> None:
    # The stronger half: a count decremented in step with a deleted row still hides a document.
    _campaign_readme(tmp_path, header="**2 documents.**", rows=("a.md", "b.md"), documents=("a.md", "b.md", "c.md"))
    assert any("c.md is in the directory but has no row" in problem for problem in campaign_readme_problems(tmp_path))


def test_a_row_naming_a_missing_file_is_reported(tmp_path: pathlib.Path) -> None:
    _campaign_readme(tmp_path, header="**2 documents.**", rows=("a.md", "ghost.md"), documents=("a.md", "b.md"))
    assert any("lists ghost.md, which is not in the directory" in problem for problem in campaign_readme_problems(tmp_path))


def test_a_campaign_without_documents_is_exempt(tmp_path: pathlib.Path) -> None:
    # lapse-students is a pointer to a plan: one row, no documents of its own, no count to check.
    _campaign_readme(tmp_path, header=None, rows=(), documents=())
    readme = tmp_path / "docs" / "experiments" / "demo" / "README.md"
    readme.write_text(
        "# Demo\n\n> **Status:** index.\n\n"
        "| Document | What it is |\n|---|---|\n"
        "| [`377-plan.md`](../../plans/377-plan.md) | the plan |\n"
    )
    assert campaign_readme_problems(tmp_path) == []


def test_a_campaign_with_documents_and_no_header_is_reported(tmp_path: pathlib.Path) -> None:
    _campaign_readme(tmp_path, header=None, rows=("a.md",), documents=("a.md",))
    assert any("no '**N documents.**' line" in problem for problem in campaign_readme_problems(tmp_path))


def _result_note(root: pathlib.Path, name: str, body: str) -> pathlib.Path:
    p = root / "docs" / "experiments"
    p.mkdir(parents=True, exist_ok=True)
    (p / name).write_text(body)
    return p / name


def _registry_with(root: pathlib.Path, rows: str) -> None:
    p = root / "docs" / "REPORT_REGISTRY.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("| report_path | topic_key |\n| --- | --- |\n" + rows)


CURRENT_CAPTURE_NOTE = (
    "> **Status:** current — analysis, 2026-11-22.\n\n"
    "Reads capture `20261112T164543Z` and `results/abc/`.\n"
)


def test_result_note_without_version_fails(tmp_path: pathlib.Path) -> None:
    _result_note(tmp_path, "r.md", CURRENT_CAPTURE_NOTE)
    _registry_with(tmp_path, "| docs/experiments/r.md | r |\n")
    problems = citation_problems(tmp_path)
    assert any("names no model version" in p for p in problems)


def test_result_note_with_version_passes(tmp_path: pathlib.Path) -> None:
    _result_note(tmp_path, "r.md", CURRENT_CAPTURE_NOTE + "\nMeasured on `v3_default`.\n")
    _registry_with(tmp_path, "| docs/experiments/r.md | r |\n")
    assert citation_problems(tmp_path) == []


def test_result_note_without_registry_row_fails(tmp_path: pathlib.Path) -> None:
    _result_note(tmp_path, "r.md", CURRENT_CAPTURE_NOTE + "\nMeasured on `v3_default`.\n")
    _registry_with(tmp_path, "| docs/experiments/other.md | other |\n")
    problems = citation_problems(tmp_path)
    assert any("no REPORT_REGISTRY.md row" in p for p in problems)


def test_baseline_only_note_needs_no_version(tmp_path: pathlib.Path) -> None:
    _result_note(tmp_path, "b.md", "> **Status:** current — baselines only; no TabPFN, no spend.\n"
                                   "\nReads `results/abc/`.\n")
    _registry_with(tmp_path, "| docs/experiments/b.md | b |\n")
    assert citation_problems(tmp_path) == []


def test_legacy_exempt_note_passes(tmp_path: pathlib.Path) -> None:
    _result_note(tmp_path, "old.md", CURRENT_CAPTURE_NOTE)
    _registry_with(tmp_path, "| docs/experiments/other.md | other |\n")
    legacy = tmp_path / "docs" / "experiments" / "legacy_version_exempt.txt"
    legacy.write_text("docs/experiments/old.md\n")
    assert citation_problems(tmp_path) == []

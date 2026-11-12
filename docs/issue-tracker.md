# Issue Tracker — GitHub

Repo: `IFoA-ADSWP/tabular-foundation-model`
Configured by `/setup-matt-pocock-skills`.

## Vocabulary (triage labels)

Canonical role -> label string used here:
- bug -> `bug`
- enhancement -> `enhancement`
- needs-triage -> `needs-triage`
- needs-info -> `needs-info`
- ready-to-build -> `ready-to-build`
- needs-decision -> `needs-decision`
- wontfix -> `wontfix`

Exactly one category label (`bug`/`enhancement`) and one state label on every triaged issue.

**The two state labels were renamed 2026-11-11.** They were `ready-for-agent` and
`ready-for-human`, which named the *executor* — a distinction only the workflow cares about
— on a tracker that contributors, reviewers and external stakeholders also read, where the
first read as an internal instruction leaked into a public place. The pair now describes the
issue's state: `ready-to-build` means fully specified and unblocked, so start now;
`needs-decision` means a maintainer must choose or sign off first.

These are now the skill defaults as well, so this repo and a fresh `/setup-matt-pocock-skills`
agree. The column is written out rather than left implicit because the skills route on the
**role**, and an explicit map is what stops a future re-run quietly changing the vocabulary.

## External PR rule

`external` = pull request whose author is NOT a collaborator on this repository. Resolve the
list with:

```
gh api repos/IFoA-ADSWP/tabular-foundation-model/collaborators --paginate --jq '.[].login'
```

The author-is-owner form (`author != IFoA-ADSWP`) is unusable here: the owner is an
organisation, so no PR author can ever satisfy it and every PR reads as external. The
collaborator test is the intended filter.

Internal PRs are out of scope for triage discovery. An explicitly named PR is always triaged
regardless of author.

## Operations

gh exposes these as first-class commands:
- View issue: `gh issue view N -R IFoA-ADSWP/tabular-foundation-model --json number,title,body,comments,labels,state`
- Create issue: `gh issue create -R IFoA-ADSWP/tabular-foundation-model --title ... --body ... --label ...`
- Comment: `gh issue comment N -R IFoA-ADSWP/tabular-foundation-model --body ...`
- Close: `gh issue close N -R IFoA-ADSWP/tabular-foundation-model` / reopen: `gh issue reopen N -R IFoA-ADSWP/tabular-foundation-model`
- List by label: `gh issue list -R IFoA-ADSWP/tabular-foundation-model --label <label> ...`

Pull requests take different verbs: view and edit them with `gh pr view N -R …` and
`gh pr edit N -R … --add-label …`. `gh issue view N` on a PR number fails with "Could not
resolve to an issue"; `gh issue comment N` does accept a PR number, so comments can go
through either command.

Before reporting a checks status or merging, read the run rather than the cached summary:
`gh pr checks N -R …` lags by minutes and can show `pending` for a job that already passed.
`gh run view <run-id> --json jobs` is the authority, and `mergeStateStatus` is a snapshot —
`CLEAN` can still fail to merge if the base moved.

Sub-issues and blocking relationships have **no** `gh` subcommand (`gh` 2.101); use `gh api`:
- List sub-issues of #N:
  `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N/sub_issues`
- Resolve the database id of any issue with the REST API:
  `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N --jq .id` — an integer, NOT the issue
  #N and NOT the `I_kw…` node id that `gh issue view N --json id` returns. The dependency
  endpoints reject the node id with HTTP 422 ("is not of type integer"). All write calls below
  take this integer.
- Add a sub-issue:
  `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N/sub_issues -X POST -F sub_issue_id=<child-db-id>`
- List what blocks #N: `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N/dependencies/blocked_by`
- List what #N blocks: `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N/dependencies/blocking`
- Add a blocker:
  `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N/dependencies/blocked_by -X POST -F issue_id=<blocker-db-id>`
- Remove a blocker:
  `gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N/dependencies/blocked_by/<blocker-db-id> -X DELETE`

If a call returns a 404, the endpoints may have moved; inspect with
`gh api repos/IFoA-ADSWP/tabular-foundation-model/issues/N --include` and retry against the path the response
nominates. Sub-issue/blocking ids are the child issue's numeric id, not its `#`-number's URL
form.

Issue reference resolution: bare `#N` resolves against `IFoA-ADSWP/tabular-foundation-model` by default.

## Wayfinding operations

- The map is one issue labelled `wayfinder:map`; its tickets are its sub-issues.
- Ticket labels: exactly one `wayfinder:research|prototype|grilling|task`, plus `wayfinder:map`
  on the parent. Wayfinder issues never carry triage labels.
- Child→parent link comes from the sub-issue relationship (not a body field).
- Frontier query (open, unblocked, unclaimed children): open sub-issues of the map whose
  `dependencies/blocked_by` is empty and which have no assignee. An unclaimed ticket is an
  open sub-issue with no assignee.
- Blocking uses the native GH dependency relationship only (see operations above).

## Tracker provenance

Run `gh --version` and record it here on setup:
- gh version: 2.101.0 (2026-09-15)

External-PR rule repeated for triage: external = author is not a repository collaborator
(org-owned repo, so the author-is-owner form cannot apply).

## Local vocabulary

The canonical roles above are the **only** state labels the skills route on:
`needs-triage`, `needs-info`, `ready-to-build`, `needs-decision`, `wontfix`.
This repo also uses the labels below. They annotate or park work; none of them
substitutes for a state label, and none of them routes anything.

**Rule.** An issue that could be picked up carries **exactly one** canonical
state label, plus any number of the labels below. An issue carrying only a label
from this table is invisible to the workflow: `implement` cannot pick it up,
`triage` treats it as untriaged, and the `doctor` counts it as queued but
unroutable (49 of 81 open issues were in that state on 2026-10-31). If an
issue's state is unknown, it is `needs-triage`.

### Priority and parking

| Label | Role | Effect on routing |
| --- | --- | --- |
| `priority: now` | priority | None. It still needs a state label; this only says "before the rest". |
| `priority: backlog` | **parking** | Parked on purpose. Remove `ready-to-build` / `needs-decision` when applying it. |
| `blocked` | **parking** | Waiting on something outside this repo (#22 GPU access, #57 a decision). Not actionable until the blocker clears; do not also carry a `ready-to-build` label. |

### Work type

| Label | Means |
| --- | --- |
| `tracking` | The spec or parent issue a set of tickets hangs off (#240, #252, #300, #324). Structural: it tracks children, so it is not itself implementable. |
| `deliverable` | Conference output work (#42–#45): abstract, writing, targeting, submission draft. |
| `documentation` | Docs-only change. |

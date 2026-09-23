# DEPRECATED — do not work here

Deprecated: 2026-09-13

**Use this checkout instead:**

    /Users/Scott/projects/tabular-foundation-model

That directory is the canonical working copy. It is on branch `finetune-v2` (the branch
holding the current work: the fine-tuning pipeline, the Pilot-2 prerequisites, the reports
and the GPU run records).

## Why this copy was deprecated

Redundant: it sits on `main` (`22a3bde`), which is an **ancestor** of the canonical checkout's `finetune-v2`. Zero unpushed commits. Its only tracked file differing from the canonical had **no unique lines** — the canonical version is a superset.

## What that means in practice

- Do not edit, commit, or run anything here. With more than one checkout of the same repo
  on this machine, an edit or a run can land in a tree that is not the one under discussion
  and nothing will complain — that has already cost time on this project.
- This is a **marker, not a deletion**. Nothing has been removed. If you believe something
  here is unique, check before deleting the directory: `git -C <dir> log --oneline
  --all --not --remotes` lists commits that exist nowhere else.
- It is safe to `rm -rf` this directory once you have confirmed there are no unpushed
  commits and nothing untracked that you need. Its history is on the remote either way.

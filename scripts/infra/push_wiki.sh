#!/usr/bin/env bash
# Push the maintenance backlog content to the GitHub Wiki.
#
# PREREQUISITE: The wiki must be initialized. To do this:
#   1. Go to https://github.com/IFoA-ADSWP/tabular-foundation-model/wiki
#   2. Click "Create the first page"
#   3. Title: "Home", body: anything (e.g., "init")
#   4. Save
# After that, run this script.
#
# The wiki repo is at: https://github.com/IFoA-ADSWP/tabular-foundation-model.wiki.git

set -euo pipefail

REPO="IFoA-ADSWP/tabular-foundation-model"
WIKI_DIR="${1:-/tmp/tabpfn-wiki}"
CONTENT_DIR="$(cd "$(dirname "$0")/.." && pwd)/.wiki-content"

# Stage release-facing pages for colleagues (browser-viewable, no repo clone needed)
mkdir -p "$CONTENT_DIR"
cp docs/archive/frontier-benchmark/TABPFN_BENCHMARK_SUMMARY.md "$CONTENT_DIR/Benchmark-Summary.md"
cp docs/experiments/frontier-benchmark/regime_characterization.md "$CONTENT_DIR/Adoption-Guidance.md"
cp docs/shared/metrics_explained.md "$CONTENT_DIR/Metrics-Explained.md"

echo "==> Cloning $REPO.wiki.git into $WIKI_DIR"
if [[ -d "$WIKI_DIR" ]]; then
  echo "    (directory exists, will pull instead)"
  (cd "$WIKI_DIR" && git pull)
else
  gh repo clone "$REPO.wiki" "$WIKI_DIR"
fi

echo "==> Syncing content from $CONTENT_DIR"
rsync -av \
  --exclude='.git' \
  --exclude='Home.md' \
  "$CONTENT_DIR/" "$WIKI_DIR/"

cd "$WIKI_DIR"

# Stage and commit
git add -A
if git diff --cached --quiet; then
  echo "==> No changes to commit"
else
  git -c user.name="scotthawes" -c user.email="scottlhawes@gmail.com" \
    commit -m "docs(wiki): sync release-facing pages + maintenance backlog

- Benchmark-Summary: TabPFN v8.2 one-pager for actuarial colleagues
- Adoption-Guidance: regime characterization / when to use TabPFN
- Metrics-Explained: log loss vs AUC vs Brier, insurance reading guide
- Maintenance-Backlog + tier pages: 36-issue backlog
- _Sidebar / _Footer: navigation"
  git push
  echo "==> Pushed to $REPO.wiki"
fi

echo "==> Done. View at: https://github.com/$REPO/wiki"

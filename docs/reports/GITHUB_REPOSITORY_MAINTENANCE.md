# GitHub Repository Maintenance: Capabilities & Processes

**Document purpose:** Overview of GitHub-related skills, processes, and tooling embedded in the TabPFN repository. For team understanding of AI-assisted GitHub proficiency.

**Date:** 2026-08-20

---

## Executive Summary

The TabPFN repository has **limited but functional** GitHub integration. The AI agents can perform basic GitHub operations via the `gh` CLI, but **no GitHub MCP server is currently configured**. Previously, the PSP-latro project had GitHub MCP connected, but this is not present in the TabPFN repo.

| Capability | Status | How It Works |
|------------|--------|--------------|
| Create branches | ✅ Available | `git` CLI via bash |
| Commit changes | ✅ Available | `git` CLI via bash |
| Push to remote | ✅ Available | `git` CLI via bash (with permission prompts) |
| Create PRs | ✅ Available | `gh` CLI via bash |
| Manage issues | ✅ Available | `gh` CLI via bash |
| GitHub MCP | ❌ Not configured | Would provide richer API access |
| Automated workflows | ⚠️ Limited | No CI/CD workflows in `.github/workflows/` |
| Issue templates | ✅ Configured | Bug reports, feature requests, doc improvements |
| PR template | ✅ Configured | Standard checklist |
| Dependabot | ✅ Configured | Weekly dependency updates |

---

## 1. What's Currently Embedded

### 1.1 GitHub CLI (`gh`) Access

**Status:** ✅ Active and authenticated

```
Logged in to github.com account scotthawes (keyring)
Token scopes: 'gist', 'project', 'read:org', 'repo', 'workflow'
```

**What the AI can do with `gh`:**
- Create/manage pull requests (`gh pr create`, `gh pr list`, `gh pr merge`)
- Create/manage issues (`gh issue create`, `gh issue list`, `gh issue close`)
- View repository information (`gh repo view`, `gh api`)
- Manage labels (`gh issue edit --add-label`)
- View checks and workflows (`gh run list`, `gh run view`)
- Clone and fork repos (`gh repo clone`, `gh repo fork`)

### 1.2 Git Operations

**Status:** ✅ Full access via bash

**What the AI can do with `git`:**
- Branch management (`git checkout -b`, `git branch -d`)
- Staging and committing (`git add`, `git commit`)
- Pushing (`git push -u origin <branch>`)
- Pulling and merging (`git pull`, `git merge`)
- Rebasing (`git rebase`)
- Viewing history (`git log`, `git diff`)
- Stashing (`git stash`)

**Permission safeguards configured:**
```json
"git push origin main": "ask",
"git push origin master": "ask",
"git push origin production": "ask",
"git push --force": "deny",
"git reset --hard": "ask",
"git branch -D *": "ask"
```

### 1.3 Repository Configuration

#### Issue Templates
Located in `.github/ISSUE_TEMPLATE/`:
- `bug_report.yml` — Structured bug report form
- `feature_request.yml` — Feature request form
- `doc_improvement.yml` — Documentation improvement form

#### Pull Request Template
Located in `.github/PULL_REQUEST_TEMPLATE.md`:
- Motivation and context
- Public API changes checklist
- Testing documentation
- Standard checklist (tested, docs updated, changelog, style, API impact)

#### Dependabot
Located in `.github/dependabot.yml`:
- Python dependencies: weekly, max 3 open PRs
- GitHub Actions: weekly, max 3 open PRs

### 1.4 Pre-commit Hooks

Located in `.pre-commit-config.yaml`:
- **ruff** — Python linting and formatting
- **commitizen** — Commit message convention enforcement
- **mypy** — Type checking (currently disabled in pre-commit)
- **pre-commit-hooks** — Large files, merge conflicts, YAML/TOML validation
- **check-jsonschema** — Validates GitHub workflow YAML

---

## 2. What's NOT Currently Configured

### 2.1 GitHub MCP Server

**Status:** ❌ Not present in TabPFN repo

**Previously in PSP-latro:** The PSP-latro project had GitHub MCP connected, which provided:
- Richer API access (GraphQL queries, rate limit awareness)
- Automated issue tracking and updates
- Workflow run monitoring
- Repository statistics
- Collaborator management

**Why it's missing here:** The TabPFN repo uses a different configuration approach (`.opencode/` directory with agent definitions) rather than the PSP-latro's more comprehensive setup.

### 2.2 CI/CD Workflows

**Status:** ❌ No `.github/workflows/` directory

**What's missing:**
- Automated testing on PR
- Linting checks
- Build verification
- Deployment automation
- Release automation

### 2.3 GitHub Actions

**Status:** ❌ No workflow files

**What could be added:**
- `pytest` on pull requests
- Pre-commit checks
- Documentation builds
- Dependency security scanning

---

## 3. How AI Agents Use GitHub

### 3.1 Agent Capabilities

**From `.opencode/agents/tabpfn-data-science.agent.md`:**
The data science agent focuses on experimentation and modeling, not GitHub operations. It:
- Runs TabPFN experiments
- Manages notebooks and outputs
- Reports results in structured format

**From `.opencode/agents/tabpfn-reporting.agent.md`:**
The reporting agent consolidates findings into reports. It:
- Checks `REPORT_REGISTRY.md` for duplicates
- Creates/updates documentation
- Links source workbooks and evidence files

### 3.2 What AI Can Do vs. What It Should Do

| Task | AI Capability | Recommended? |
|------|---------------|--------------|
| Create PR | ✅ Can do via `gh pr create` | ✅ Yes, with review |
| Push to main | ⚠️ Requires permission prompt | ⚠️ Only with approval |
| Merge PR | ✅ Can do via `gh pr merge` | ⚠️ Only with approval |
| Create issue | ✅ Can do via `gh issue create` | ✅ Yes |
| Close issue | ✅ Can do via `gh issue close` | ✅ Yes |
| Force push | ❌ Blocked by config | ❌ Never |
| Delete branch | ⚠️ Requires permission prompt | ⚠️ Only with approval |

---

## 4. Comparison: TabPFN vs PSP-latro GitHub Setup

| Feature | TabPFN | PSP-latro |
|---------|--------|-----------|
| GitHub CLI auth | ✅ Active | ✅ Active |
| GitHub MCP | ❌ Not configured | ✅ Previously connected |
| Issue templates | ✅ 3 templates | ✅ Full set |
| PR template | ✅ Standard | ✅ Comprehensive |
| CI/CD workflows | ❌ None | ✅ Full pipeline |
| Dependabot | ✅ Weekly | ✅ Weekly |
| Pre-commit hooks | ✅ Python-focused | ✅ Multi-language |
| Agent GitHub skills | ⚠️ Limited | ✅ Full GitHub workflow |
| Bus.js coordination | ❌ Not present | ✅ Multi-agent coordination |
| Memory MCP | ❌ Not present | ✅ Cross-session knowledge |

---

## 5. Recommendations for Your Colleague

### 5.1 If They Want AI GitHub Proficiency

**Minimum viable setup:**
1. **Ensure `gh` CLI is authenticated** — Already done ✅
2. **Add CI/CD workflows** — Create `.github/workflows/` with pytest, linting
3. **Configure GitHub MCP** — For richer API access and automation
4. **Add branch protection rules** — Prevent direct pushes to main

**Advanced setup:**
1. **Multi-agent coordination** — Like PSP-latro's bus.js system
2. **Memory MCP** — Cross-session knowledge persistence
3. **Issue tracking integration** — Automated claim/release workflow
4. **Automated testing** — Pre-commit + CI pipeline

### 5.2 What the AI Can Do Right Now

**For the TabPFN repo, the AI can:**
- ✅ Create branches and PRs
- ✅ Manage issues (create, close, label)
- ✅ View repository information
- ✅ Run git operations (commit, push, pull)
- ✅ Check CI/CD status (if workflows existed)
- ❌ Automatically update issues on PR merge (needs MCP or webhooks)
- ❌ Monitor workflow runs (no workflows configured)
- ❌ Perform GraphQL queries (needs GitHub MCP)

### 5.3 What's Missing for Full GitHub Proficiency

**To match PSP-latro's capabilities, TabPFN would need:**

1. **GitHub MCP Server**
   ```json
   // Add to .opencode/opencode.json
   "mcp": {
     "github": {
       "command": "npx",
       "args": ["-y", "@modelcontextprotocol/server-github"],
       "env": {
         "GITHUB_PERSONAL_ACCESS_TOKEN": "<token>"
       }
     }
   }
   ```

2. **CI/CD Workflows**
   ```yaml
   # .github/workflows/ci.yml
   name: CI
   on: [pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
         - run: pip install -r requirements.txt
         - run: pytest tests/
   ```

3. **Branch Protection Rules**
   - Require PR reviews before merge
   - Require status checks (CI) to pass
   - Require up-to-date branches
   - Restrict force pushes

---

## 6. Quick Reference: Available Commands

### GitHub CLI Commands

```bash
# Repository
gh repo view
gh repo clone IFoA-ADSWP/TabPFN

# Pull Requests
gh pr list
gh pr create --title "..." --body "..."
gh pr checkout <pr-number>
gh pr merge <pr-number>

# Issues
gh issue list
gh issue create --title "..." --body "..."
gh issue close <issue-number>
gh issue edit <issue-number> --add-label "bug"

# Checks
gh run list
gh run view <run-id>

# API
gh api repos/IFoA-ADSWP/TabPFN
gh api repos/IFoA-ADSWP/TabPFN/issues --paginate
```

### Git Commands

```bash
# Branches
git checkout -b feature/new-feature
git branch -d feature/old-feature
git push -u origin feature/new-feature

# Commits
git add .
git commit -m "feat: add new feature"
git push

# History
git log --oneline -10
git diff main..feature/new-feature
git stash
git stash pop
```

---

## 7. Summary

### Current State
- **GitHub CLI:** ✅ Active and authenticated
- **Git operations:** ✅ Full access with safeguards
- **Issue/PR management:** ✅ Basic capability via `gh`
- **CI/CD:** ❌ Not configured
- **GitHub MCP:** ❌ Not present
- **Agent GitHub skills:** ⚠️ Limited to basic operations

### What the AI Can Do
- Create branches, PRs, and issues
- Push code (with permission prompts for protected branches)
- View repository information
- Manage labels and assignments

### What's Missing
- GitHub MCP for richer API access
- CI/CD workflows for automated testing
- Branch protection rules
- Multi-agent coordination (like PSP-latro's bus.js)
- Memory MCP for cross-session knowledge

### Bottom Line
The AI has **basic GitHub proficiency** through the `gh` CLI, but lacks the **deep integration** that GitHub MCP would provide. For a colleague wanting to understand AI GitHub capabilities, the key takeaway is:

> **The AI can do basic Git/GitHub operations, but needs additional configuration (MCP, CI/CD, branch protection) for enterprise-grade repository maintenance.**

---

*Document compiled from TabPFN repository configuration. For PSP-latro's more comprehensive GitHub setup, see that project's `.opencode/` directory and `AGENTS.md`.*

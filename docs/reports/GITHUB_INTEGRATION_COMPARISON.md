# GitHub Integration: opencode-platform vs TabPFN vs PSP-latro

**Document purpose:** Comparison of GitHub capabilities across your three projects, showing what was previously configured in opencode-platform and what's available in each.

**Date:** 2026-08-20

---

## Executive Summary

Your **opencode-platform** project had **enterprise-grade GitHub integration** that is significantly more comprehensive than what's currently configured in TabPFN or PSP-latro. It included:

- **GitHub MCP server** (custom `gh` CLI wrapper)
- **CI/CD workflows** (3 automated pipelines)
- **Approval gates** (human-in-the-loop for dangerous actions)
- **Message bus** (multi-agent coordination)
- **Audit trail** (full traceability)

**Current status:** The opencode-platform repo exists at `/Users/Scott/opencode-platform` but is **not currently active** — the TabPFN and PSP-latro projects use simpler configurations.

---

## 1. Feature Comparison Matrix

| Feature | opencode-platform | TabPFN | PSP-latro |
|---------|-------------------|--------|-----------|
| **GitHub CLI (`gh`)** | ✅ Active | ✅ Active | ✅ Active |
| **GitHub MCP** | ✅ Custom wrapper | ❌ Not configured | ⚠️ Previously connected |
| **Git MCP** | ✅ @cyanheads/git-mcp-server | ❌ Not configured | ❌ Not configured |
| **CI/CD Workflows** | ✅ 3 workflows | ❌ None | ❌ None |
| **Approval Gates** | ✅ Human-in-the-loop | ❌ Not configured | ❌ Not configured |
| **Message Bus** | ✅ Multi-agent coordination | ❌ Not present | ✅ File-based |
| **Audit Trail** | ✅ Full traceability | ❌ Not configured | ❌ Not configured |
| **Issue Templates** | ✅ Configured | ✅ 3 templates | ✅ Configured |
| **PR Template** | ✅ Standard | ✅ Standard | ✅ Comprehensive |
| **Dependabot** | ❌ Not configured | ✅ Weekly | ✅ Weekly |
| **Pre-commit Hooks** | ❌ Not configured | ✅ Python-focused | ✅ Multi-language |
| **Snapshot Browser** | ✅ opencode-snapshots | ❌ Not configured | ❌ Not configured |
| **Eval Framework** | ✅ Golden tests | ❌ Not configured | ❌ Not configured |
| **Healthcheck** | ✅ Platform status | ❌ Not configured | ❌ Not configured |

---

## 2. opencode-platform: What Was Previously Configured

### 2.1 GitHub MCP Server (Custom Wrapper)

**Location:** `/Users/Scott/opencode-platform/scripts/github-gh-mcp.js`

**What it provides:**
- `github_create_issue` — Create issues with labels/assignees
- `github_get_issue` — Get issue details (JSON)
- `github_update_issue` — Update title, body, state
- `github_list_issues` — List/filter issues
- `github_add_issue_comment` — Add comments
- `github_create_pr` — Create pull requests
- `github_add_labels` — Manage labels

**How it works:**
```bash
# Wrapper script
exec node "$(dirname "$0")/github-gh-mcp.js" "$@"
```

**Configuration in opencode.json:**
```json
"github": {
  "type": "local",
  "command": ["/Users/Scott/.config/opencode/scripts/github-mcp-wrapper.sh"],
  "enabled": false
}
```

**Note:** Currently **disabled** (`"enabled": false`)

### 2.2 Git MCP Server

**Configuration:**
```json
"git": {
  "type": "local",
  "command": ["npx", "-y", "@cyanheads/git-mcp-server@latest"],
  "enabled": false
}
```

**Provides 28 Git tools:**
- `git_status`, `git_diff`, `git_log`
- `git_branch`, `git_checkout`, `git_commit`
- `git_stash`, `git_merge`, `git_rebase`
- And more...

**Note:** Currently **disabled** (`"enabled": false`)

### 2.3 CI/CD Workflows

**3 GitHub Actions workflows:**

#### 1. CI (`ci.yml`)
```yaml
name: CI
on: [push, pull_request]
jobs:
  ci:
    steps:
      - run: npm ci
      - run: node scripts/test-runner.js
      - run: node scripts/integration-test.js
      - run: node scripts/validate-workflows.js
      - run: node scripts/capability-report.js
```

#### 2. Approval Gates (`approval-gates.yml`)
```yaml
name: Approval Gates
on: [pull_request, push]
jobs:
  gate-check:
    steps:
      - name: Check for dangerous actions in PR
        run: node scripts/gate-checker.js check "$file"
      - name: Audit trail
        run: node scripts/gate-checker.js audit 1
```

#### 3. Validate Platform (`validate.yml`)
```yaml
name: Validate Platform
on: [push, pull_request]
jobs:
  validate:
    steps:
      - run: node scripts/validate.js
      - run: node scripts/eval-scorer.js --check-fail-threshold 0.80
```

### 2.4 Approval Gates System

**Purpose:** Human-in-the-loop for dangerous actions

**Commands:**
```bash
npm run gates -- gates              # show all gate rules
npm run gates -- check "git push origin main"  # check action
npm run gates -- approve "dangerous:git push origin main" "scott" 24
npm run gates -- list               # active approvals
npm run gates -- audit 7            # audit trail
```

**Configuration:** `gates/gates.yaml`
**Audit trail:** `gates/audit/`

### 2.5 Message Bus (Multi-Agent Coordination)

**Purpose:** Cross-session communication between agents

**Architecture:**
```
Any agent/session → bus.js send <target-agent> ... → inbox file
Orchestrator → bus.js read <agent-id> → pass to subagent as task context
```

**Commands:**
```bash
npm run bus -- send <from> <to> <type> [--payload "..."]
npm run bus -- check <agent-id>
npm run bus -- read <agent-id>
npm run bus -- list
npm run bus -- stats
npm run bus -- purge <agent-id|topic>
```

**Storage:** `bus/` directory (inboxes/, topics/, archive/)

### 2.6 Snapshot Browser

**Purpose:** Browse complete project state at any point in time

**Installation:**
```bash
npm install github:phishy/opencode-snapshots
```

**Usage:**
```bash
ocs          # Launch terminal UI
ocs serve    # Start web server at localhost:3000
```

**Features:**
- View file diffs from each coding session
- Timeline view through snapshots
- Download any snapshot as ZIP
- Search conversations for snapshots

### 2.7 Eval Framework

**Purpose:** Golden tests measure agent quality

**Commands:**
```bash
npm run eval           # score golden tests
npm run gate           # validate + eval (pre-push)
```

**Alerts:** Trigger on pass rate drop >10% or score drop >0.1

### 2.8 Healthcheck

**Purpose:** Single status surface for the platform

**Command:**
```bash
npm run healthcheck
```

**Validates:**
- Config JSON
- Agents
- Skills
- Registry sync
- Gates (incl. pending-approval count)
- Message bus (per-inbox health)

---

## 3. TabPFN: Current GitHub Capabilities

### 3.1 What's Available

| Capability | Status | How It Works |
|------------|--------|--------------|
| GitHub CLI (`gh`) | ✅ Active | Authenticated with `repo`, `workflow` scopes |
| Git operations | ✅ Full | Branch, commit, push (with permission prompts) |
| Issue management | ✅ Basic | Create, close, label via `gh` |
| PR management | ✅ Basic | Create, merge via `gh` |
| Issue templates | ✅ 3 templates | Bug, feature, doc improvement |
| PR template | ✅ Standard | Checklist format |
| Dependabot | ✅ Weekly | Python + GitHub Actions |
| Pre-commit | ✅ Ruff + commitizen | Linting and commit conventions |

### 3.2 What's Missing

| Feature | Status | Why It Matters |
|---------|--------|----------------|
| GitHub MCP | ❌ Not configured | Would provide richer API access, GraphQL queries |
| CI/CD workflows | ❌ None | No automated testing on PRs |
| Branch protection | ❌ Not configured | Could prevent direct pushes to main |
| Approval gates | ❌ Not configured | No human-in-the-loop for dangerous actions |
| Message bus | ❌ Not present | No multi-agent coordination |
| Eval framework | ❌ Not configured | No golden tests for agent quality |

---

## 4. PSP-latro: Current GitHub Capabilities

### 4.1 What's Available (from AGENTS.md)

| Capability | Status | How It Works |
|------------|--------|--------------|
| GitHub CLI (`gh`) | ✅ Active | Authenticated |
| Git operations | ✅ Full | With permission safeguards |
| Issue tracking | ✅ Pre-flight claim check | `scripts/pre-flight-claim-check.sh` |
| Claim/release workflow | ✅ Bus-based | `bus.js send` for issue claims |
| Cross-session coordination | ✅ Message bus | `bus.js` for multi-agent work |
| Memory MCP | ✅ Cross-session knowledge | `store_entity`, `query_nodes` |

### 4.2 What's Missing

| Feature | Status | Why It Matters |
|---------|--------|----------------|
| GitHub MCP | ❌ Not currently | Would provide richer API access |
| CI/CD workflows | ❌ None | No automated testing |
| Approval gates | ❌ Not configured | No human-in-the-loop |
| Eval framework | ❌ Not configured | No golden tests |

---

## 5. How to Reactivate opencode-platform GitHub Integration

### 5.1 Enable MCP Servers

Edit `/Users/Scott/opencode-platform/opencode.json`:

```json
"mcp": {
  "github": {
    "type": "local",
    "command": ["/Users/Scott/.config/opencode/scripts/github-mcp-wrapper.sh"],
    "enabled": true  // Change from false to true
  },
  "git": {
    "type": "local",
    "command": ["npx", "-y", "@cyanheads/git-mcp-server@latest"],
    "enabled": true  // Change from false to true
  }
}
```

### 5.2 Restart OpenCode

```bash
# Exit current session
exit

# Relaunch
opencode
```

### 5.3 Verify MCP Tools

```
show me the current git status
```

or

```
use git_status to check the repository state
```

---

## 6. Recommendations

### 6.1 For TabPFN Project

**Minimum viable GitHub integration:**
1. ✅ GitHub CLI — Already active
2. ❌ Add CI/CD workflows — Create `.github/workflows/` with pytest, linting
3. ❌ Configure GitHub MCP — For richer API access
4. ❌ Add branch protection — Prevent direct pushes to main

### 6.2 For Your Colleague

**If they want enterprise-grade GitHub integration:**
1. **Start with opencode-platform** — It has the most comprehensive setup
2. **Enable MCP servers** — Reactivate GitHub and Git MCP
3. **Use approval gates** — Human-in-the-loop for dangerous actions
4. **Leverage the message bus** — Multi-agent coordination

### 6.3 What's Different About opencode-platform

| Aspect | opencode-platform | TabPFN | PSP-latro |
|--------|-------------------|--------|-----------|
| **Primary use case** | Platform harness | Research repo | Game development |
| **GitHub integration** | Enterprise-grade | Basic | Intermediate |
| **Multi-agent** | ✅ Full coordination | ❌ Single agent | ✅ File-based |
| **Safety gates** | ✅ Approval system | ❌ Permission prompts | ⚠️ Permission prompts |
| **Auditability** | ✅ Full trail | ❌ Git history only | ⚠️ Git history only |
| **Quality gates** | ✅ Eval framework | ❌ Pre-commit only | ❌ Pre-commit only |

---

## 7. Quick Reference: Available Commands

### opencode-platform Commands

```bash
# Platform health
npm run healthcheck

# Message bus
npm run bus -- stats
npm run bus -- list
npm run bus -- send <from> <to> <type> [--payload "..."]
npm run bus -- check <agent-id>

# Approval gates
npm run gates -- gates
npm run gates -- check "git push origin main"
npm run gates -- approve "dangerous:git push origin main" "scott" 24

# Eval framework
npm run eval
npm run gate

# Traces
npm run traces
npm run traces -- errors
npm run traces -- agent-stats
```

### TabPFN Commands

```bash
# GitHub CLI
gh pr list
gh issue list
gh repo view

# Git
git status
git log --oneline -10
git diff main..feature/branch
```

### PSP-latro Commands

```bash
# Pre-flight claim check
bash scripts/pre-flight-claim-check.sh <issue-number>

# Bus operations
node ~/.config/opencode/scripts/bus.js stats
node ~/.config/opencode/scripts/bus.js read <agent-id>
```

---

## 8. Summary

### What You Previously Had (opencode-platform)

| Feature | Status | Value |
|---------|--------|-------|
| GitHub MCP | ✅ Custom wrapper | Rich API access, issue/PR management |
| Git MCP | ✅ 28 tools | Full Git operations via MCP |
| CI/CD | ✅ 3 workflows | Automated testing, validation |
| Approval gates | ✅ Human-in-the-loop | Safety for dangerous actions |
| Message bus | ✅ Multi-agent | Cross-session coordination |
| Audit trail | ✅ Full traceability | Complete action history |
| Eval framework | ✅ Golden tests | Agent quality measurement |
| Healthcheck | ✅ Platform status | Single status surface |

### What's Currently Active

| Project | GitHub MCP | CI/CD | Approval Gates | Message Bus |
|---------|------------|-------|----------------|-------------|
| opencode-platform | ❌ Disabled | ✅ Active | ✅ Active | ✅ Active |
| TabPFN | ❌ Not configured | ❌ None | ❌ None | ❌ None |
| PSP-latro | ❌ Not currently | ❌ None | ❌ None | ✅ File-based |

### Bottom Line

> **Your opencode-platform project had the most comprehensive GitHub integration** — it was a full platform harness with MCP servers, CI/CD, approval gates, and multi-agent coordination. The TabPFN and PSP-latro projects use simpler configurations focused on their specific use cases (research and game development, respectively).

---

*Document compiled from opencode-platform, TabPFN, and PSP-latro repository configurations.*

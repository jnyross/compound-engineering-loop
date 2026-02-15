---
title: "Comprehensive Plugin Refactoring: Fix 15 Critical and Quality Issues"
date: 2026-02-15
category: runtime-errors
tags:
  - plugin-architecture
  - workflow-automation
  - code-quality
  - security-hardening
  - runtime-stability
  - autonomous-execution
  - context-optimization
severity: high
component: compound-engineering-plugin
symptoms:
  - Workflow references to 5 non-existent phantom agents causing runtime errors
  - Review agent STATUS/DECISION mismatch blocking workflow progression
  - External plugin dependencies preventing standalone operation
  - Unsafe retry limit (50 cycles = 66+ hours unsupervised execution)
  - README component counts diverged from filesystem reality
  - Brainstorm phase blocking on user input during autonomous loops
  - Insecure curl|sudo bash installation pattern in rclone skill
  - Missing .gitignore exposing credential and artifact files
  - Binary review decisions forcing full 80-minute loops for minor fixes
  - Duplicate skill-creator implementations (192KB overlap)
  - Inconsistent naming conventions across commands and skills
  - Shell scripts missing strict mode and vulnerable to injection
  - Auto-loading skill descriptions exceeding context budget (339 chars avg)
root_cause: Plugin vendored from local cache into standalone repository without comprehensive validation pass
resolution_summary: Fixed all 15 issues across 3 priority-ordered phases plus 2 post-review findings, bumping v2.31.0 to v2.32.1
---

# Comprehensive Plugin Refactoring: Fix 15 Critical and Quality Issues

## Problem Summary

The compound-engineering plugin v2.31.0 suffered from 15 documented issues discovered during a comprehensive multi-agent code review. Issues ranged from P1 critical runtime failures blocking autonomous workflow execution to P3 quality improvements affecting maintainability. The root cause was vendoring the plugin from a local cache without validation, introducing phantom agent references, STATUS/DECISION mismatches, external dependency chains, unsafe retry limits, and security vulnerabilities.

## Root Cause

The plugin was extracted from a larger system and vendored into a standalone repository. No comprehensive validation pass was performed, so:

- **Architectural drift**: Plugin commands and root-level agent files diverged (~469 lines duplication)
- **Development settings in production**: `max_retries: 50` was for local testing, not autonomous execution
- **Security oversights**: Shell scripts lacked hardening, no `.gitignore`, `curl | bash` patterns
- **Context budget creep**: Skill descriptions averaged 339 chars (target: <200)

## Solution Overview

### Phase 1: Critical Runtime Fixes (P1)

5 issues blocking autonomous execution:

1. **Phantom agent references removed** — 5 non-existent agents (`dependency-detective`, `code-philosopher`, `devops-harmony-analyst`, `rails-turbo-expert`, `cora-test-reviewer`) removed from workflow commands
2. **Review agent STATUS fixed** — `STATUS: retry` changed to `STATUS: done` (DECISION field controls routing, not STATUS)
3. **External dependencies removed** — `/lfg` and `/slfg` rewritten to remove `ralph-wiggum:ralph-loop` and `compound-engineering:` prefix references
4. **Retry limit reduced** — `max_retries` from 50 to 3 in workflow.yml (caps autonomous execution at ~4 hours instead of 66+)
5. **README counts corrected** — Commands 25 to 24, Skills 16 to 17, missing table entries added

### Phase 2: Reliability & Security (P2)

5 issues degrading safety:

1. **Sync comments added** — All 5 `agents/*/AGENTS.md` files now point to `.claude/commands/workflows/` as authoritative source
2. **ANTFARM_MODE detection** — Brainstorm, plan, and work commands detect `ANTFARM_MODE` environment variable (interactive vs autonomous)
3. **Insecure install pattern replaced** — `curl | sudo bash` in rclone skill replaced with package manager instructions
4. **`.gitignore` added** — Python, credential, OS, IDE, and dependency patterns
5. **Three-state review decisions** — `needs_fixes` path added (approved to compound, needs_fixes to work, rejected to brainstorm)

### Phase 3: Quality & Consistency (P3)

5 issues reducing maintainability:

1. **Skill consolidation** — `skill-creator` merged into `create-agent-skills` (migrated 3 scaffolding scripts, deleted duplicate)
2. **Naming conventions fixed** — `resolve-pr-parallel` skill renamed from snake_case to kebab-case
3. **Shell scripts hardened** — `set -euo pipefail`, branch name validation, git-reserved pattern blocking
4. **Context window optimized** — All auto-loading skill descriptions trimmed to <200 chars
5. **Python scripts deduplicated** — Learnings-researcher model changed from `haiku` to `inherit`

### Post-Review Fixes

Multi-agent code review caught 2 additional issues:

1. **3 skill descriptions still over budget** — rclone (369 to 155), agent-browser (340 to 148), agent-native-architecture (248 to 145)
2. **`.gitignore` env pattern too narrow** — `.env` + `.env.local` + `.env.*.local` broadened to `.env` + `.env.*`

## Key Fixes with Code Examples

### Fix 1: STATUS/DECISION Separation

The review agent output `STATUS: retry` on rejection, but `workflow.yml` expected `STATUS: done` for all outcomes. The workflow engine hung.

```yaml
# BEFORE — workflow hangs
DECISION: rejected
STATUS: retry

# AFTER — workflow completes, DECISION drives routing
DECISION: rejected
STATUS: done
```

**Pattern**: STATUS = "did the agent finish" (always `done`). DECISION = "what happens next" (`approved`/`needs_fixes`/`rejected`).

### Fix 2: Bounded Retry Limits

Each review cycle takes ~80 minutes. 50 retries = 66+ hours unsupervised.

```yaml
# BEFORE
max_retries: 50  # 66+ hours autonomous

# AFTER
max_retries: 3   # ~4 hours maximum
on_exhausted:
  escalate_to: human
```

### Fix 3: Three-State Review Routing

Binary outcomes (approved/rejected) forced full 80-minute brainstorm-plan-work cycles for minor P2/P3 findings.

```yaml
# BEFORE — only two paths
on_decision:
  approved:
    next_step: compound
  rejected:
    retry_step: brainstorm

# AFTER — three paths, needs_fixes skips brainstorm/plan
on_decision:
  approved:
    next_step: compound
  needs_fixes:
    retry_step: work          # Skip brainstorm/plan
    pass_outputs: [issues]
  rejected:
    retry_step: brainstorm
    pass_outputs: [issues]
```

The work step input template was also updated to include `{{issues}}` so the agent receives review feedback.

### Fix 4: Shell Script Hardening

Branch name injection vulnerability in `worktree-manager.sh` — leading hyphens allowed git flag injection.

```bash
# BEFORE
#!/bin/bash
set -e
# No input validation

# AFTER
#!/bin/bash
set -euo pipefail
trap 'echo "Error on line $LINENO" >&2' ERR

validate_branch_name() {
  local branch="$1"
  # Must start with alphanumeric (prevents flag injection via leading -)
  if [[ ! "$branch" =~ ^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,99}$ ]]; then
    echo "Error: Invalid branch name: $branch" >&2
    return 1
  fi
  # Block git-reserved patterns
  if [[ "$branch" == *.lock ]] || [[ "$branch" == *..* ]]; then
    echo "Error: Branch name contains git-reserved pattern" >&2
    return 1
  fi
}
```

### Fix 5: Autonomous Mode Detection

When review rejected and looped to brainstorm, the agent called `AskUserQuestion` and waited indefinitely.

```markdown
## Mode Detection

Check `ANTFARM_MODE` environment variable (default: `interactive`).

| Mode | Behavior |
|------|----------|
| `interactive` | Pause for human input at decision gates |
| `autonomous` | Skip AskUserQuestion, auto-proceed with best judgment |
```

## Verification

The multi-agent code review (5 agents: architecture-strategist, security-sentinel, pattern-recognition-specialist, code-simplicity-reviewer, performance-oracle) validated all fixes and caught 2 additional issues missed in the original plan:

- 3 skill descriptions still exceeded 200-char budget (auto-loading skills not in the explicit audit list)
- `.gitignore` env pattern too narrow (`.env.local` only, missed `.env.test`, `.env.development`)

Both were fixed in v2.32.1.

## Prevention Strategies

### Automated Validation

```bash
# Check all skill descriptions are <= 200 chars
for skill in .claude/skills/*/SKILL.md; do
  desc=$(sed -n '/^description:/p' "$skill" | cut -d: -f2-)
  len=${#desc}
  [ "$len" -gt 200 ] && echo "FAIL: $(dirname $skill) = $len chars"
done

# Check for insecure installation patterns
grep -rE 'curl.*\|.*(sudo )?bash' .claude/skills/

# Verify .gitignore covers broad env pattern
grep '\.env\.\*' .gitignore || echo "FAIL: missing .env.* pattern"

# Verify agent references resolve
grep -rhoE 'Task [a-z-]+' .claude/commands/ | sort -u
```

### Pre-Commit Checklist Additions

- [ ] All agent references in commands resolve to actual agent files
- [ ] All skill descriptions <= 200 characters
- [ ] No `curl | bash` patterns in documentation
- [ ] `.gitignore` uses `.env.*` broad pattern
- [ ] Shell scripts include `set -euo pipefail` and validate inputs
- [ ] Review agents output `STATUS: done` with separate `DECISION` field
- [ ] `max_retries` <= 3 with `on_exhausted: escalate_to: human`
- [ ] Workflow input templates include all `pass_outputs` variables (e.g., `{{issues}}`)
- [ ] Environment variable detection documented for autonomous workflows

### Key Principles

1. **Validate at the edges** — Cross-reference agent/command references at commit time, not runtime
2. **Single source of truth** — `.claude/commands/workflows/` is authoritative; agent copies include sync comments
3. **Context budget is a first-class constraint** — Hard limit descriptions at 200 chars
4. **Security by default** — Broad `.gitignore`, no `curl | bash`, validate shell inputs
5. **Test all routing paths** — approved, needs_fixes, and rejected must all work end-to-end
6. **Bound autonomous execution** — Never allow unbounded retry loops

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total fixes | 17 (15 planned + 2 from review) |
| Version bump | 2.31.0 to 2.32.1 |
| Files changed | 46 |
| Commits | 8 |
| Time saved per cycle | ~80 min (via needs_fixes path) |
| Max autonomous time | 66 hours to 4 hours |
| Context budget | 339 avg to <200 chars |
| Skills removed | 1 duplicate (skill-creator) |

## Related Documentation

- [Multi-Agent Plugin Review Findings](../code-review/multi-agent-plugin-review-findings.md) — Original 7-agent review that identified the 15 issues
- [OpenCode Antfarm Workflow Phases](../integration-issues/opencode-antfarm-workflow-compound-engineering-plugin-phases.md) — Agent-to-plugin phase mapping
- [Implementation Plan](../../plans/2026-02-15-refactor-fix-all-15-documented-plugin-issues-plan.md) — Master plan with all 110 checkboxes
- [CHANGELOG v2.32.0](../../.claude/CHANGELOG.md) — Full change documentation

## Resources

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [tj-actions branch-names CVE](https://github.com/tj-actions/branch-names/security) — git flag injection via branch names

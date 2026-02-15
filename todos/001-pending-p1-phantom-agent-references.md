---
status: pending
priority: p1
issue_id: "001"
tags: [code-review, architecture, runtime-failure]
dependencies: []
---

# Remove Phantom Agent References From Review Command

## Problem Statement

The review command at `.claude/commands/workflows/review.md` references 5 agents that do not exist in the repository. When the review workflow runs and attempts to spawn these agents, it will fail silently or produce errors, degrading the review quality.

## Findings

- `dependency-detective` (line 72) — no file in `.claude/agents/`
- `code-philosopher` (line 75) — no file in `.claude/agents/`
- `devops-harmony-analyst` (line 78) — no file in `.claude/agents/`
- `rails-turbo-expert` (line 70) — no file in `.claude/agents/`
- `cora-test-reviewer` — referenced in compound command but does not exist
- The root-level `agents/review/AGENTS.md` does NOT reference these phantom agents, confirming they are stale references in the plugin command
- Found by: architecture-strategist, pattern-recognition-specialist

## Proposed Solutions

### Option 1: Remove phantom references (Recommended)

**Approach:** Delete the 5 non-existent agent references from `review.md` and the compound command.

**Pros:**
- Simple fix, no new files needed
- Eliminates runtime failures
- Aligns plugin command with root-level agent definitions

**Cons:**
- Reduces review coverage if those agents were intended

**Effort:** 30 minutes
**Risk:** Low

### Option 2: Create stub agent files

**Approach:** Create minimal agent definitions for the 5 missing agents.

**Pros:**
- Preserves intended review coverage
- No behavioral change in review workflow

**Cons:**
- Creates agents without clear specifications
- More work to define proper agent behavior

**Effort:** 2-3 hours
**Risk:** Medium

## Technical Details

**Affected files:**
- `.claude/commands/workflows/review.md` — lines 68-82, parallel agent list
- `.claude/commands/workflows/compound.md` — cora-test-reviewer reference

## Acceptance Criteria

- [ ] No agent references in commands that don't resolve to actual agent files
- [ ] Review workflow runs without agent-not-found errors
- [ ] Root-level and plugin-level agent lists are consistent

## Work Log

### 2026-02-15 - Initial Discovery

**By:** Claude Code Review (architecture-strategist, pattern-recognition-specialist)

**Actions:**
- Cross-referenced all agent invocations in commands against actual agent files
- Identified 5 phantom references
- Confirmed root-level agents do not have these references

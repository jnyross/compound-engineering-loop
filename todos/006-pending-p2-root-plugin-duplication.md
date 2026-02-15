---
status: pending
priority: p2
issue_id: "006"
tags: [code-review, architecture, duplication]
dependencies: []
---

# Eliminate Duplication Between Root Agents and Plugin Commands

## Problem Statement

The 5 root-level `agents/*/AGENTS.md` files duplicate the corresponding `.claude/commands/workflows/*.md` files. Both describe the same workflow phases with the same instructions. Changes must be made in two places, and they have already diverged (review agent lists differ, STATUS output differs).

## Findings

- `agents/brainstorm/AGENTS.md` (87 lines) duplicates `commands/workflows/brainstorm.md` (124 lines)
- `agents/plan/AGENTS.md` (78 lines) duplicates `commands/workflows/plan.md` (551 lines)
- `agents/work/AGENTS.md` (108 lines) duplicates `commands/workflows/work.md` (433 lines)
- `agents/review/AGENTS.md` (107 lines) duplicates `commands/workflows/review.md` (526 lines)
- `agents/compound/AGENTS.md` (89 lines) duplicates `commands/workflows/compound.md` (239 lines)
- Already diverged: review command has 5 phantom agents not in AGENTS.md
- Total: ~469 lines of duplicated content
- Found by: code-simplicity-reviewer, architecture-strategist, pattern-recognition-specialist

## Proposed Solutions

### Option 1: Make root agents reference plugin commands (Recommended)

**Approach:** Replace AGENTS.md content with thin stubs that say "Follow the process defined in `.claude/commands/workflows/<phase>.md`"

**Pros:**
- Single source of truth
- Root agents stay lightweight
- No drift between versions

**Cons:**
- Antfarm agents depend on .claude/ directory existing

**Effort:** 1 hour
**Risk:** Low

### Option 2: Remove root agents, reference commands from workflow.yml

**Approach:** Modify workflow.yml to point directly at .claude/commands/workflows/ files.

**Pros:**
- Eliminates root agents/ directory entirely
- Cleanest architecture

**Cons:**
- May not be supported by Antfarm's agent loading mechanism

**Effort:** 2 hours
**Risk:** Medium

## Technical Details

**Affected files:**
- `agents/brainstorm/AGENTS.md`
- `agents/plan/AGENTS.md`
- `agents/work/AGENTS.md`
- `agents/review/AGENTS.md`
- `agents/compound/AGENTS.md`

## Acceptance Criteria

- [ ] Single source of truth for each workflow phase
- [ ] No content duplication between root agents and plugin commands
- [ ] workflow.yml still functions correctly

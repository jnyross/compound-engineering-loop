---
status: pending
priority: p2
issue_id: "007"
tags: [code-review, agent-native, autonomy]
dependencies: []
---

# Brainstorm Phase Blocks Autonomous Execution

## Problem Statement

The brainstorm phase uses `AskUserQuestion` to ask questions "ONE AT A TIME" and waits for user responses. When the review step rejects and loops back to brainstorm, this creates a hard block — the agent cannot continue without human input, breaking the autonomous loop.

## Findings

- `agents/brainstorm/AGENTS.md` lines 22-28: mandatory AskUserQuestion usage
- `commands/workflows/brainstorm.md` lines 49-58, 82-89: interactive gates
- Plan and work phases also have interactive approval gates
- Phase 0 "Assess Requirements Clarity" has logic to skip when requirements are clear — this could be extended
- Found by: agent-native-reviewer

## Proposed Solutions

### Option 1: Add autonomous mode detection (Recommended)

**Approach:** When brainstorm receives structured input from workflow.yml (especially `{{issues}}` from a rejected review), skip interactive dialogue and produce output directly from the issues context.

**Effort:** 1-2 hours
**Risk:** Low

### Option 2: Make all interactive gates conditional

**Approach:** Detect "workflow mode" vs "standalone command mode" across all phases. Skip interactive menus in workflow mode.

**Effort:** 3-4 hours
**Risk:** Medium

## Technical Details

**Affected files:**
- `agents/brainstorm/AGENTS.md`
- `.claude/commands/workflows/brainstorm.md`
- `.claude/commands/workflows/plan.md` (post-generation menu)
- `.claude/commands/workflows/work.md` (approval gates)

## Acceptance Criteria

- [ ] Review rejection → brainstorm loop completes without human intervention
- [ ] Standalone `/workflows:brainstorm` retains interactive behavior

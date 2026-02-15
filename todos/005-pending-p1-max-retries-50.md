---
status: pending
priority: p1
issue_id: "005"
tags: [code-review, workflow, resource-safety]
dependencies: []
---

# Reduce Review Step max_retries From 50 to 3-5

## Problem Statement

The review step in workflow.yml has `max_retries: 50`. Each retry loops back through brainstorm-plan-work-review (~4800s per cycle). 50 retries = potentially 66+ hours of autonomous execution consuming significant compute resources without human oversight.

## Findings

- `workflow.yml` line 213: `max_retries: 50`
- Each full cycle: brainstorm (900s) + plan (900s) + work (1800s) + review (1200s) = 4800s
- 50 cycles = 240,000 seconds = ~66 hours of autonomous operation
- Found by: architecture-strategist, security-sentinel

## Proposed Solutions

### Option 1: Reduce to 3 retries (Recommended)

**Approach:** Change `max_retries: 50` to `max_retries: 3`.

**Effort:** 5 minutes
**Risk:** Low

## Technical Details

**Affected files:**
- `workflow.yml` — line 213

## Acceptance Criteria

- [ ] max_retries is 3-5, not 50
- [ ] on_exhausted still escalates to human

---
status: pending
priority: p2
issue_id: "010"
tags: [code-review, workflow, architecture]
dependencies: []
---

# Add "Approved With Fixes" Path to Review Step

## Problem Statement

The review step has only two outcomes: `approved` (proceed to compound) or `rejected` (loop all the way back to brainstorm). Minor P2/P3 review findings trigger a full re-brainstorm cycle, which is disproportionate. Most review feedback is incremental, not fundamental enough to require re-brainstorming.

## Findings

- `workflow.yml`: only `approved` and `rejected` decision paths
- No "needs minor fixes" path that re-enters only the work phase
- Full rejection loop: brainstorm→plan→work→review = ~80 minutes per cycle
- Found by: architecture-strategist

## Proposed Solutions

### Option 1: Add needs_fixes decision path (Recommended)

**Approach:** Add a third decision outcome in workflow.yml:
```yaml
on_decision:
  approved: { next_step: compound }
  needs_fixes: { retry_step: work, pass_outputs: [issues] }
  rejected: { retry_step: brainstorm, pass_outputs: [issues] }
```

**Effort:** 1-2 hours
**Risk:** Low

## Acceptance Criteria

- [ ] Review can route minor fixes directly to work phase
- [ ] Only fundamental issues loop back to brainstorm

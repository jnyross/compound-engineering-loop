---
status: done
priority: p1
issue_id: "002"
tags: [code-review, workflow, runtime-failure]
dependencies: []
---

# Fix Review Agent STATUS Output Mismatch

## Problem Statement

The Review `AGENTS.md` tells the agent to output `STATUS: retry` on rejection, but `workflow.yml` expects `STATUS: done` on all outcomes. This mismatch will cause the workflow engine to misinterpret the review step's completion, potentially triggering incorrect retry logic or timeout.

## Findings

- `agents/review/AGENTS.md` line 104: outputs `STATUS: retry` for rejections
- `workflow.yml` line 82: `expects: "STATUS: done"` — expects done regardless of verdict
- `workflow.yml` line 194 correctly notes: "IMPORTANT: Always output STATUS: done regardless of your verdict"
- The AGENTS.md contradicts the workflow.yml requirement
- Found by: agent-native-reviewer

## Proposed Solutions

### Option 1: Fix AGENTS.md to output STATUS: done (Recommended)

**Approach:** Change line 104 of `agents/review/AGENTS.md` from `STATUS: retry` to `STATUS: done`.

**Pros:**
- Aligns with workflow.yml expectations
- The DECISION field already controls routing (approved/rejected)

**Cons:**
- None

**Effort:** 5 minutes
**Risk:** Low

## Technical Details

**Affected files:**
- `agents/review/AGENTS.md` — line 104

## Acceptance Criteria

- [ ] Review agent always outputs `STATUS: done` regardless of DECISION value
- [ ] workflow.yml `expects` condition is satisfied by all review outcomes

## Work Log

### 2026-02-15 - Completed via CHANGELOG v2.32.0

**By:** Claude Code Review

**Actions:**
- Fixed in CHANGELOG v2.32.0 - "Fix review agent STATUS output — `STATUS: retry` → `STATUS: done`"

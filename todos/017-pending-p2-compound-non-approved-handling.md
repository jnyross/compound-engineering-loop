---
status: pending
priority: p2
issue_id: "017"
tags: [code-review, workflow, architecture, antfarm-compatibility]
dependencies: []
---

# Compound Agent Lacks Instructions for Non-Approved Review Decisions

## Problem Statement

On the current linear pipeline (Track A), the compound step always executes regardless of the review DECISION value. When DECISION is `needs_fixes` or `rejected`, the compound agent still receives the task and attempts to document learnings. However, the compound AGENTS.md has no instructions for handling these cases — it assumes a successful review and documents the solution as if it were complete.

This means after a rejected review, the compound agent would create a solution document for an incomplete or flawed implementation, polluting `docs/solutions/` with misleading documentation.

## Findings

- `agents/compound/AGENTS.md` — No mention of DECISION handling; process assumes successful implementation
- `workflow.yml:235-236` — Compound step receives `REVIEW DECISION: {{decision}}` but AGENTS.md doesn't reference it
- `workflow.yml:232-233` — Compound step receives `REVIEW ISSUES: {{review_issues}}` but AGENTS.md doesn't describe when to use it
- On linear pipeline, compound always runs after review (no routing)
- Found by: agent-native-reviewer, spec-flow-analyzer, architecture-strategist

## Proposed Solutions

### Option 1: Add decision-aware branching to compound AGENTS.md (Recommended)

**Approach:** Add a "Phase 0: Check Review Decision" step that reads the REVIEW DECISION input and adapts behavior:
- `approved` → Full documentation in `docs/solutions/`
- `needs_fixes` → Skip documentation, output minimal acknowledgment
- `rejected` → Skip documentation, document what was attempted and why it failed (optional learning)

**Pros:**
- Prevents misleading solution docs from incomplete implementations
- Graceful handling of all pipeline states
- Minimal changes to existing AGENTS.md

**Cons:**
- Adds complexity to compound agent
- On Track B, compound only runs on `approved`, making this check redundant

**Effort:** 20 minutes

**Risk:** Low

---

### Option 2: Add conditional skip instruction in workflow.yml compound input

**Approach:** Add to the compound step input: "If REVIEW DECISION is not 'approved', output a brief note and STATUS: done without creating any files."

**Pros:**
- Fix is in one place (workflow.yml), not AGENTS.md
- Clear, explicit instruction in the step input

**Cons:**
- Step input becomes longer
- Duplicates logic that should be in AGENTS.md

**Effort:** 10 minutes

**Risk:** Low

## Recommended Action

**To be filled during triage.**

## Technical Details

**Affected files:**
- `agents/compound/AGENTS.md` — Add Phase 0 decision check
- `workflow.yml:214-248` — Compound step input (if Option 2)

## Resources

- **Branch:** `claude/add-decision-routing-39rod`
- **Plan:** `docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md`

## Acceptance Criteria

- [ ] Compound agent handles `needs_fixes` decision gracefully (no solution doc created)
- [ ] Compound agent handles `rejected` decision gracefully (no solution doc created)
- [ ] `approved` path continues to work as before
- [ ] Output always includes STATUS: done regardless of decision

## Work Log

### 2026-02-15 - Initial Discovery

**By:** Code Review (agent-native-reviewer, spec-flow-analyzer, architecture-strategist)

**Actions:**
- Identified that compound AGENTS.md has no decision-awareness
- Traced data flow: review outputs DECISION → context → compound input
- Confirmed linear pipeline always advances to compound

**Learnings:**
- On Track B (decision routing), compound only runs on `approved`, making this a Track A-only concern
- The fix is cheap and prevents bad documentation from being committed

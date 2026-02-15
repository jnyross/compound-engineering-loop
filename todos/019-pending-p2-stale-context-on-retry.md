---
status: pending
priority: p2
issue_id: "019"
tags: [code-review, workflow, architecture, antfarm-compatibility]
dependencies: []
---

# Review Outputs Are Mutually Exclusive But Stale Values Persist in Context

## Problem Statement

The review agent outputs either `REVIEW_NOTES` (on approved) or `REVIEW_ISSUES` (on needs_fixes/rejected), never both. However, antfarm's global context merge is additive — once a key is set, it persists until explicitly overwritten. This creates two problems:

1. **First run approved → stale review_issues="":** Compound receives empty review_issues, which is fine.
2. **Retry scenario:** If review first outputs `REVIEW_ISSUES: fix X` (needs_fixes), then on retry outputs `REVIEW_NOTES: looks good` (approved), the context still contains the old `review_issues: fix X` from the first pass. The compound agent would see both review_notes AND review_issues populated, which is contradictory.

On the linear pipeline (Track A), this scenario cannot occur because there is no retry loop — review always advances to compound. But on Track B with decision routing, stale context from previous review passes would persist.

## Findings

- `agents/review/AGENTS.md:94-113` — Output format shows REVIEW_NOTES xor REVIEW_ISSUES based on DECISION
- `workflow.yml:13-27` — Context block initializes both `review_notes: ""` and `review_issues: ""` as empty
- Antfarm's `completeStep()` merges output into global context; it does not clear unset keys
- On retry cycles, previous output values remain unless explicitly overwritten
- Found by: spec-flow-analyzer

## Proposed Solutions

### Option 1: Instruct review agent to always output both keys (Recommended)

**Approach:** Change review AGENTS.md output format to always include both keys:
- Approved: `REVIEW_NOTES: assessment summary` + `REVIEW_ISSUES: none`
- Needs fixes: `REVIEW_NOTES: none` + `REVIEW_ISSUES: detailed list`
- Rejected: `REVIEW_NOTES: none` + `REVIEW_ISSUES: detailed list`

This ensures the previous value is always overwritten on each review pass.

**Pros:**
- Simple, no runtime changes
- Guarantees clean context on every review pass
- Backward compatible

**Cons:**
- Slightly more verbose output
- "none" values need to be handled by consumers

**Effort:** 15 minutes

**Risk:** Low

---

### Option 2: Clear context keys before retry in antfarm (Track B)

**Approach:** When routing a decision back to a previous step, reset relevant context keys to empty. Requires antfarm runtime changes.

**Pros:**
- Clean solution at the runtime level
- No agent instruction changes needed

**Cons:**
- Requires Track B antfarm changes
- Need to decide which keys to clear (risk of clearing too much)

**Effort:** 2-3 hours (Track B)

**Risk:** Medium

## Recommended Action

**To be filled during triage.**

## Technical Details

**Affected files:**
- `agents/review/AGENTS.md` — Output format section (lines 90-113)
- `workflow.yml` — Review step output expectations

## Resources

- **Branch:** `claude/add-decision-routing-39rod`
- **Plan:** `docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md`

## Acceptance Criteria

- [ ] Review agent always outputs both REVIEW_NOTES and REVIEW_ISSUES
- [ ] On approved: REVIEW_ISSUES is explicitly set to "none" or empty
- [ ] On needs_fixes/rejected: REVIEW_NOTES is explicitly set to "none" or empty
- [ ] No stale values persist across review retry cycles

## Work Log

### 2026-02-15 - Initial Discovery

**By:** Code Review (spec-flow-analyzer)

**Actions:**
- Identified mutually exclusive output pattern in review agent
- Traced context persistence behavior through antfarm's completeStep()
- Confirmed stale value risk on retry cycles

**Learnings:**
- This is a Track A concern only if the linear pipeline somehow retries (via max_retries)
- On Track B, decision routing would trigger retries where this becomes a real problem
- Option 1 (always output both keys) is the safest fix regardless of pipeline type

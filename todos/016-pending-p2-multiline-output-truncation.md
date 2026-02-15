---
status: pending
priority: p2
issue_id: "016"
tags: [code-review, workflow, architecture, antfarm-compatibility]
dependencies: []
---

# Agent Multi-Line Output Values Risk Truncation by completeStep()

## Problem Statement

Antfarm's `completeStep()` parses agent output line-by-line looking for `KEY: value` patterns. When agents produce multi-line values (e.g., a detailed REVIEW_ISSUES list or IMPLEMENTATION_SUMMARY), only the first line after the key is captured. Subsequent lines are either lost or misinterpreted as separate keys.

This affects every agent in the pipeline since several output keys naturally produce multi-line content: REVIEW_ISSUES (list of fixes), IMPLEMENTATION_SUMMARY (what was done), PLAN_SUMMARY (plan description), BRAINSTORM_OUTPUT (approaches explored), and LEARNINGS (documented patterns).

## Findings

- `agents/review/AGENTS.md:101-106` — Output format shows `REVIEW_ISSUES: detailed list of fixes needed with file:line references` — this naturally expands to multiple lines
- `agents/work/AGENTS.md:85-86` — `IMPLEMENTATION_SUMMARY: what was implemented and key decisions` and `FILES_CHANGED: list of files` both tend toward multi-line
- `agents/plan/AGENTS.md:57` — `PLAN_SUMMARY: [1-2 paragraph summary]` explicitly suggests multiple lines
- Antfarm `completeStep()` in `src/pipeline.ts` iterates `output.split('\n')` and matches `/^([A-Z_]+):\s*(.*)$/` per line
- Only the regex capture group on the same line as the key is stored
- Found by: agent-native-reviewer, spec-flow-analyzer

## Proposed Solutions

### Option 1: Add single-line constraint to all agent output instructions (Recommended)

**Approach:** Add explicit instruction to each AGENTS.md: "All output values MUST be single-line. Use semicolons to separate list items. Example: `FILES_CHANGED: app/models/user.rb; app/controllers/users_controller.rb; test/models/user_test.rb`"

**Pros:**
- Simple, no runtime changes needed
- Works with current antfarm parsing
- Agents (LLMs) can follow formatting constraints

**Cons:**
- Limits expressiveness of review issues and summaries
- Semicolon-delimited lists are less readable for humans inspecting context

**Effort:** 30 minutes

**Risk:** Low

---

### Option 2: Use a delimiter-based multi-line format

**Approach:** Define a convention like `KEY: <<<` to start and `>>>` to end multi-line values. Requires antfarm Track B changes to `completeStep()` parser.

**Pros:**
- Preserves rich, multi-line output
- Clean separation of values

**Cons:**
- Requires antfarm runtime changes (Track B scope)
- More complex parsing logic

**Effort:** 2-3 hours (Track B)

**Risk:** Medium

## Recommended Action

**To be filled during triage.**

## Technical Details

**Affected files:**
- `agents/brainstorm/AGENTS.md` — output format section
- `agents/plan/AGENTS.md` — output format section
- `agents/work/AGENTS.md` — output format section
- `agents/review/AGENTS.md` — output format section
- `agents/compound/AGENTS.md` — output format section

**Related components:**
- Antfarm `completeStep()` parser in `src/pipeline.ts`

## Resources

- **Branch:** `claude/add-decision-routing-39rod`
- **Plan:** `docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md`

## Acceptance Criteria

- [ ] All 5 AGENTS.md files include explicit single-line output constraint
- [ ] Output format examples show semicolon-delimited lists
- [ ] No agent output key naturally produces content that would span multiple lines

## Work Log

### 2026-02-15 - Initial Discovery

**By:** Code Review (architecture-strategist, agent-native-reviewer, spec-flow-analyzer)

**Actions:**
- Identified completeStep() line-by-line parsing behavior
- Mapped all agent output keys that naturally produce multi-line content
- Assessed truncation impact on downstream consumers

**Learnings:**
- The most critical key is REVIEW_ISSUES — truncation here means the work agent gets incomplete fix instructions on retry
- STATUS and DECISION are always single-line, so pipeline control flow is unaffected
- PLAN_FILE and PR_URL are paths/URLs, naturally single-line

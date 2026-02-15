---
title: "Antfarm Workflow P2/P3 Review Findings: Output Parsing, Stale Context, Decision Gates"
date: 2026-02-15
category: logic-errors
tags: [antfarm, workflow-pipeline, agent-prompts, context-management, output-parsing]
severity: medium
---

# Antfarm Workflow P2/P3 Review Findings

## Problem

After adapting the compound-engineering-loop workflow for antfarm v0.5.1 (Track A), an exhaustive 6-agent code review identified five categories of issues:

1. **Multi-line output truncation** (P2) -- agents could produce multi-line KEY: value pairs that antfarm's `completeStep()` silently truncated
2. **Compound runs on rejected reviews** (P2) -- no decision gate; compound agent documented "learnings" from failed implementations
3. **Inconsistent label naming** (P2) -- same variable referenced as "PREVIOUS REVIEW ISSUES", "REVIEW ISSUES", and "REVIEW_ISSUES"
4. **Stale context on retry** (P2) -- review output REVIEW_NOTES xor REVIEW_ISSUES conditionally; old values persisted across retry cycles
5. **Accumulated cruft** (P3) -- duplicated instructions, YAGNI todo step, inconsistent Phase/Step naming, redundant table

## Root Cause

**Output parsing (016):** Antfarm's `completeStep()` parses output line-by-line with `/^([A-Z_]+):\s*(.*)$/`. Any value spanning multiple lines loses everything after the first line. No warning is emitted.

**Missing decision gate (017):** The compound agent had no Phase 0 check. On Track A's linear pipeline, compound always runs after review regardless of DECISION value, creating misleading solution docs for rejected implementations.

**Naming drift (018):** Labels were added incrementally across workflow.yml and AGENTS.md files without a naming convention. Result: three variants of the same variable.

**Stale context (019):** Review agent output REVIEW_NOTES on approval and REVIEW_ISSUES on rejection -- never both. Antfarm's context merges new output into existing state. On retry, the key not emitted retains its previous value, causing downstream agents to see stale data.

**Cruft accumulation (020):** Incremental changes left behind duplicated output format specs in workflow.yml (14 lines duplicating what AGENTS.md already says), a todo file creation step removed from scope, and inconsistent "Step N" vs "Phase N" naming.

## Solution

### Fix 1: Single-Line Output Constraint (016)

Added output rules block to all five `agents/*/AGENTS.md` output format sections:

```markdown
**Output rules:** Each KEY: value pair must be on a single line. The runtime
parses line-by-line; continuation lines are silently dropped. Use semicolons
to separate list items. Do not include literal {{ }} in output values.

Example: REVIEW_ISSUES: Missing validation in users_controller.rb:42; N+1 in orders_service.rb:88
```

Also changed plan agent's `PLAN_SUMMARY: [1-2 paragraph summary]` to `[1-2 sentence summary]`.

### Fix 2: Compound Decision Gate (017)

Added Phase 0 to `agents/compound/AGENTS.md`:

```markdown
### Phase 0: Check Review Decision

Read the DECISION from your input.

- If DECISION is `approved`: proceed to Phase 1 (full documentation).
- If DECISION is `needs_fixes` or `rejected`: output brief acknowledgment and exit:
  LEARNINGS: Implementation did not pass review (decision: [value]); no solution documented
  FILE_CREATED: none
  STATUS: done
```

### Fix 3: Label Standardization (018)

Standardized all input labels to UPPER_SNAKE_CASE matching output keys:

| Before | After | Location |
|--------|-------|----------|
| `PREVIOUS REVIEW ISSUES` | `REVIEW_ISSUES` | workflow.yml brainstorm step |
| `REVIEW ISSUES` | `REVIEW_ISSUES` | workflow.yml work step |
| `IMPLEMENTATION:` | `IMPLEMENTATION_SUMMARY:` | workflow.yml compound step |
| `REVIEW NOTES:` | `REVIEW_NOTES:` | workflow.yml compound step |
| `REVIEW DECISION:` | `DECISION:` | workflow.yml compound step |

### Fix 4: Always Emit Both Keys (019)

Changed review agent to always output both REVIEW_NOTES and REVIEW_ISSUES, using `"none"` as sentinel:

```
If approved:    REVIEW_NOTES: [summary]     REVIEW_ISSUES: none
If needs_fixes: REVIEW_NOTES: none          REVIEW_ISSUES: [list]
If rejected:    REVIEW_NOTES: none          REVIEW_ISSUES: [list]
```

Updated downstream agents to handle the sentinel:
- `agents/brainstorm/AGENTS.md`: `If REVIEW_ISSUES is not empty and not "none"`
- `agents/work/AGENTS.md`: same pattern

### Fix 5: Simplifications (020)

- Condensed 14-line review step input in workflow.yml to 2 lines deferring to AGENTS.md
- Removed YAGNI "Create Todo Files" step and `todos/` shared file reference from review agent
- Merged "Deep Analysis" step into "Code Review" step in review agent
- Renamed all "Step N" to "Phase N" in review and plan agents for consistency
- Removed redundant "Common Mistakes" table from compound agent

## Prevention

### Agent Prompt Development Rules

1. **All output values must be single-line.** Antfarm's parser drops continuation lines. Use semicolons for lists. Add explicit constraint + example to every AGENTS.md output section.

2. **Every agent consuming DECISION must have a Phase 0 gate.** Check the decision value before doing any work. Non-applicable decisions should produce minimal output and exit.

3. **Use UPPER_SNAKE_CASE for all shared variable names.** Labels in workflow.yml step inputs must match the exact output key names (REVIEW_ISSUES, not "REVIEW ISSUES").

4. **Always emit all output keys on every run.** Conditional output creates stale context on retry. Use `"none"` sentinel for inapplicable keys. Update all downstream consumers to handle the sentinel.

5. **AGENTS.md is the single source of truth for output format.** Workflow.yml step inputs should reference AGENTS.md, not duplicate the full output spec.

6. **Use "Phase N" naming consistently** across all agent process sections.

### Code Review Checklist for Agent/Workflow Changes

- [ ] All KEY: value outputs fit on a single line
- [ ] Variable names use UPPER_SNAKE_CASE matching output keys
- [ ] Agent consuming DECISION has Phase 0 gate
- [ ] Review agent emits both REVIEW_NOTES and REVIEW_ISSUES on every path
- [ ] No duplicated output format specs between workflow.yml and AGENTS.md
- [ ] Phase numbering is contiguous (no gaps)

## Related

### Plans
- [Fix P2/P3 Code Review Findings](../../../docs/plans/2026-02-15-fix-p2-p3-workflow-review-findings-plan.md) -- implementation plan for these fixes
- [Antfarm Decision Routing Integration](../../../docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md) -- Track A/B plan that produced the code under review

### Solutions
- [Workflow Runtime Capability Mismatch](../integration-issues/2026-02-15-workflow-runtime-capability-mismatch.md) -- predecessor solution documenting the Track A antfarm adaptation
- [Multi-Agent Plugin Review Findings](../code-review/multi-agent-plugin-review-findings.md) -- full 6-agent review report that identified these issues

### Resolved Todos
- [016](../../../todos/016-pending-p2-multiline-output-truncation.md) -- multi-line output truncation
- [017](../../../todos/017-pending-p2-compound-non-approved-handling.md) -- compound non-approved handling
- [018](../../../todos/018-pending-p2-input-label-naming-inconsistency.md) -- input label naming
- [019](../../../todos/019-pending-p2-stale-context-on-retry.md) -- stale context on retry
- [020](../../../todos/020-pending-p3-code-simplification-opportunities.md) -- code simplifications

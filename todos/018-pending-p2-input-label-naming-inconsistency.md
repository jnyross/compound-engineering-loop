---
status: done
priority: p2
issue_id: "018"
tags: [code-review, workflow, quality, naming-convention]
dependencies: []
---

# Input Label Naming Inconsistency Across Pipeline Steps

## Problem Statement

The review issues variable is referenced with three different label names across the pipeline steps, creating confusion for agents that need to parse their input:

1. Brainstorm step input (workflow.yml:89): `PREVIOUS REVIEW ISSUES (empty on first run):`
2. Work step input (workflow.yml:141): `REVIEW ISSUES (if retrying from review):`
3. Review agent output key: `REVIEW_ISSUES:`
4. Brainstorm AGENTS.md line 32: references `REVIEW_ISSUES`
5. Work AGENTS.md line 18: references `REVIEW ISSUES`

Agents see the rendered input text with labels, then their AGENTS.md references a different naming convention. While LLMs handle this gracefully, the inconsistency makes the system harder to maintain and debug.

## Findings

- `workflow.yml:89` — Label: `PREVIOUS REVIEW ISSUES (empty on first run):`
- `workflow.yml:141` — Label: `REVIEW ISSUES (if retrying from review):`
- `workflow.yml:232` — Compound step label: `REVIEW ISSUES:`
- `agents/brainstorm/AGENTS.md:32` — References: `REVIEW_ISSUES`
- `agents/work/AGENTS.md:18` — References: `REVIEW ISSUES`
- Context key in workflow.yml:17 is `review_issues`
- Review agent output key is `REVIEW_ISSUES`
- Found by: agent-native-reviewer, pattern-recognition-specialist, architecture-strategist

## Proposed Solutions

### Option 1: Standardize all labels to match output key format (Recommended)

**Approach:** Use `REVIEW_ISSUES` consistently everywhere:
- Brainstorm input: `REVIEW_ISSUES (empty on first run):`
- Work input: `REVIEW_ISSUES (if retrying from review):`
- Compound input: `REVIEW_ISSUES:`
- All AGENTS.md files: reference `REVIEW_ISSUES`

**Pros:**
- Single naming convention throughout
- Labels match the output key exactly
- Easier to trace data flow

**Cons:**
- Underscore format is less human-readable than space-separated

**Effort:** 20 minutes

**Risk:** Low

---

### Option 2: Standardize to space-separated labels, document the mapping

**Approach:** Use `REVIEW ISSUES` as the human-readable label everywhere, and document that the context key is `review_issues` and the output key is `REVIEW_ISSUES`.

**Pros:**
- More readable labels
- Clear mapping documentation

**Cons:**
- Three different conventions still exist (label, context key, output key)
- More cognitive overhead

**Effort:** 30 minutes

**Risk:** Low

## Recommended Action

**To be filled during triage.**

## Technical Details

**Affected files:**
- `workflow.yml` — Lines 89, 141, 232 (step input labels)
- `agents/brainstorm/AGENTS.md` — Line 32 (reference)
- `agents/work/AGENTS.md` — Line 18 (reference)

## Resources

- **Branch:** `claude/add-decision-routing-39rod`

## Acceptance Criteria

- [ ] All step inputs use the same label format for review issues
- [ ] All AGENTS.md files reference the same name
- [ ] Data flow from review output → context → downstream input is traceable with consistent naming

## Work Log

### 2026-02-15 - Initial Discovery

**By:** Code Review (agent-native-reviewer, pattern-recognition-specialist)

**Actions:**
- Mapped all references to review issues across workflow.yml and AGENTS.md files
- Identified three naming variants: PREVIOUS REVIEW ISSUES, REVIEW ISSUES, REVIEW_ISSUES
- Confirmed LLMs handle this gracefully but it's a maintenance burden

### 2026-02-15 - Completed via CHANGELOG v2.33.2

**By:** Claude Code Review

**Actions:**
- Fixed in CHANGELOG v2.33.2 - "Standardized all input labels to UPPER_SNAKE_CASE matching output keys"

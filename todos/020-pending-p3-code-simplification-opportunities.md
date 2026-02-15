---
status: pending
priority: p3
issue_id: "020"
tags: [code-review, quality, simplification, code-cleanup]
dependencies: ["016", "017", "018", "019"]
---

# Code Simplification Opportunities Across Workflow and Agent Files

## Problem Statement

Multiple small simplification opportunities were identified across workflow.yml and the 5 AGENTS.md files. None are functional issues, but each adds unnecessary complexity, duplication, or cognitive load. Consolidated here as a single cleanup task.

## Findings

### 1. Terminal-only context keys (workflow.yml:26-27)
- `learnings: ""` and `file_created: ""` are outputs of the final step (compound). No downstream step consumes them. Initializing them to empty strings serves no purpose.

### 2. Self-referential context passthrough (workflow.yml:14-16)
- `task: "{{task}}"`, `repo: "{{repo}}"`, `branch: "{{branch}}"` may be no-ops if antfarm's `runWorkflow()` already merges caller-provided context. Verify behavior — if caller context is automatically available, these lines are identity transforms.

### 3. Duplicated review output format (workflow.yml:186-199)
- The review step input contains a 14-line output format specification that is a near-verbatim copy of `agents/review/AGENTS.md` lines 90-113. Could be replaced with a 3-line reminder: "Output STATUS: done always. Output DECISION as: approved, needs_fixes, or rejected."

### 4. Review agent Step 6: Todo file creation (review/AGENTS.md:82-88)
- YAGNI for antfarm pipeline. The work agent consumes `{{review_issues}}` from context, not todo files from disk. Step 6 creates artifacts no pipeline consumer reads. The `todos/` shared file reference (line 11) should also be removed.

### 5. Review agent Step 3: Deep Analysis (review/AGENTS.md:53-61)
- Stakeholder perspective analysis overlaps heavily with Step 2 (Code Review) which already covers security, performance, architecture, and quality. The scenario exploration line could be merged into Step 2. Saves 9 lines.

### 6. Phase vs Step naming inconsistency
- brainstorm, work, compound use "Phase 1", "Phase 2", etc.
- plan, review use "Step 1", "Step 2", etc.
- Not a functional issue but inconsistent.

### 7. Compound step label mismatches (workflow.yml:226, 235)
- Input label `IMPLEMENTATION:` but context key is `implementation_summary`
- Input label `REVIEW DECISION:` but context key is `decision`
- Labels should match the convention used by other steps.

### 8. Common Mistakes table (compound/AGENTS.md:92-98)
- Restates constraints already in the document: "Only ONE file" (line 14), "Include review issues" (Phase 1 step), "Specific prevention strategies" (Phase 1 step 4). Redundant.

### 9. Template double-expansion risk (security-sentinel finding)
- If agent output contains literal `{{key}}` patterns, resolveTemplate() would expand them in downstream steps. LOW risk since agents don't typically output template syntax, but worth a note in AGENTS.md: "Do not include literal {{ }} in output values."

## Proposed Solutions

### Option 1: Apply all simplifications in one pass (Recommended)

**Approach:** Address all 9 items in a single commit:
1. Remove `learnings` and `file_created` from context block
2. Verify and possibly remove self-referential context keys
3. Condense review step output format to 3 lines
4. Remove Step 6 and `todos/` reference from review AGENTS.md
5. Merge Step 3 scenario exploration into Step 2, remove Step 3
6. Standardize Phase/Step naming (prefer "Phase" for consistency with majority)
7. Fix compound input labels to match conventions
8. Remove Common Mistakes table
9. Add "no {{ }} in output" note to output format sections

**Effort:** 1-2 hours

**Risk:** Low

---

### Option 2: Cherry-pick highest-value simplifications only

**Approach:** Apply only items 1, 3, 4 (terminal keys, duplicated format, YAGNI todos) which have the clearest benefit. Defer cosmetic changes.

**Effort:** 30 minutes

**Risk:** Very low

## Recommended Action

**To be filled during triage.**

## Technical Details

**Affected files:**
- `workflow.yml` — Context block, review step input, compound step labels
- `agents/review/AGENTS.md` — Steps 3, 5, 6; shared files section
- `agents/compound/AGENTS.md` — Common Mistakes table
- `agents/brainstorm/AGENTS.md` — Phase/Step naming (if standardizing)
- `agents/plan/AGENTS.md` — Phase/Step naming (if standardizing)

## Resources

- **Branch:** `claude/add-decision-routing-39rod`
- **Found by:** code-simplicity-reviewer, pattern-recognition-specialist, security-sentinel

## Acceptance Criteria

- [ ] No unused context keys in workflow.yml
- [ ] Review step input does not duplicate AGENTS.md content
- [ ] No YAGNI artifacts (todo file creation removed from review agent)
- [ ] Consistent Phase/Step naming across all agents
- [ ] Input labels match conventions used by other steps

## Work Log

### 2026-02-15 - Initial Discovery

**By:** Code Review (code-simplicity-reviewer, pattern-recognition-specialist, security-sentinel)

**Actions:**
- Identified 9 simplification opportunities across 5 files
- Estimated ~43 lines of code removal (~5.5% of total)
- Categorized as P3 since none affect functionality

**Learnings:**
- The Track A changes are well-executed overall
- Most complexity comes from defensive duplication (same info in workflow.yml and AGENTS.md)
- Phase/Step naming split is a cosmetic issue, not structural

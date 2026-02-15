---
title: "Fix P2/P3 Code Review Findings from Track A Antfarm Compatibility"
type: fix
date: 2026-02-15
status: completed
todos: [016, 017, 018, 019, 020]
---

# Fix P2/P3 Code Review Findings

## Overview

Fix all four P2 todo items (016-019) and the consolidated P3 simplification item (020) identified during the exhaustive 6-agent code review of the Track A antfarm compatibility changes. These are quality and correctness improvements to `workflow.yml` and all five `agents/*/AGENTS.md` files.

## Problem Statement

The Track A changes made the workflow runnable on antfarm v0.5.1 but introduced five categories of issues:

1. **Multi-line output truncation** (016)--agents produce multi-line values that `completeStep()` silently truncates
2. **Compound runs on rejected reviews** (017)--creates misleading solution docs for failed implementations
3. **Inconsistent naming** (018)--"PREVIOUS REVIEW ISSUES" vs "REVIEW ISSUES" vs "REVIEW_ISSUES"
4. **Stale context on retry** (019)--review outputs one key, old values persist for the other
5. **Accumulated cruft** (020)--unused context keys, duplicated instructions, redundant sections

## Proposed Solution

Apply targeted fixes in dependency order across two phases, touching 7 files total.

### Phase 1: Correctness Fixes (016-019)

Applied in this order to avoid editing the same lines twice:

#### 1.1 Stale Context Fix (019)

**File:** `agents/review/AGENTS.md` (Output Format section, lines 90-120)

Change review agent to always output BOTH keys on every run:

```
If approved:
REVIEW_NOTES: summary of assessment
REVIEW_ISSUES: none
DECISION: approved
STATUS: done

If needs_fixes:
REVIEW_NOTES: none
REVIEW_ISSUES: [single-line semicolon-delimited list]
DECISION: needs_fixes
STATUS: done

If rejected:
REVIEW_NOTES: none
REVIEW_ISSUES: [single-line semicolon-delimited list]
DECISION: rejected
STATUS: done
```

**Critical: Update downstream "not empty" checks** to handle the `"none"` sentinel:

- `agents/brainstorm/AGENTS.md` line 32: change `If REVIEW_ISSUES is not empty` to `If REVIEW_ISSUES is not empty and not "none"`
- `agents/work/AGENTS.md` line 18: same change for `REVIEW ISSUES` check

Without this, brainstorm and work agents would incorrectly enter retry mode when they see `REVIEW_ISSUES: none` from an approved review (Track B scenario).

- [x] Update review AGENTS.md output format to always emit both keys
- [x] Update brainstorm AGENTS.md to handle "none" sentinel
- [x] Update work AGENTS.md to handle "none" sentinel

#### 1.2 Label Naming Standardization (018)

**Convention:** Labels match the output key format: `REVIEW_ISSUES` (UPPER_SNAKE_CASE).

**Files and changes:**

| File | Line | Before | After |
|------|------|--------|-------|
| `workflow.yml` | 89 | `PREVIOUS REVIEW ISSUES (empty on first run):` | `REVIEW_ISSUES (empty on first run):` |
| `workflow.yml` | 141 | `REVIEW ISSUES (if retrying from review):` | `REVIEW_ISSUES (if retrying from review):` |
| `workflow.yml` | 226 | `IMPLEMENTATION:` | `IMPLEMENTATION_SUMMARY:` |
| `workflow.yml` | 229 | `REVIEW NOTES:` | `REVIEW_NOTES:` |
| `workflow.yml` | 232 | `REVIEW ISSUES:` | `REVIEW_ISSUES:` |
| `workflow.yml` | 235 | `REVIEW DECISION:` | `DECISION:` |
| `agents/work/AGENTS.md` | ~18 | `REVIEW ISSUES` | `REVIEW_ISSUES` |

- [x] Standardize all workflow.yml input labels to UPPER_SNAKE_CASE
- [x] Update work AGENTS.md reference

#### 1.3 Single-Line Output Constraint (016)

**All five `agents/*/AGENTS.md` files:** Add this block to each Output Format section:

```markdown
**Output rules:** Each KEY: value pair must be on a single line. The runtime
parses line-by-line; continuation lines are silently dropped. Use semicolons
to separate list items. Do not include literal {{ }} in output values.

Example: FILES_CHANGED: app/models/user.rb; app/controllers/users_controller.rb
```

Also fix plan agent's `[1-2 paragraph summary]` to `[1-2 sentence summary]`.

- [x] Add single-line constraint to brainstorm AGENTS.md
- [x] Add single-line constraint to plan AGENTS.md (fix paragraph -> sentence)
- [x] Add single-line constraint to work AGENTS.md
- [x] Add single-line constraint to review AGENTS.md
- [x] Add single-line constraint to compound AGENTS.md

#### 1.4 Compound Non-Approved Handling (017)

**File:** `agents/compound/AGENTS.md`

Insert Phase 0 between "Critical Rule" (line 14) and "Phase 1: Research" (line 20):

```markdown
### Phase 0: Check Review Decision

Read the REVIEW DECISION from your input.

- If DECISION is `approved`: proceed to Phase 1 (full documentation).
- If DECISION is `needs_fixes` or `rejected`: the implementation did not pass review.
  Do NOT create a solution document. Output a brief acknowledgment and exit:
  ```
  LEARNINGS: Implementation did not pass review (decision: [value]); no solution documented
  FILE_CREATED: none
  STATUS: done
  ```
```

- [x] Add Phase 0 decision check to compound AGENTS.md

### Phase 2: Simplification (020)

Applied after Phase 1. Changes organized by file to minimize context switching.

#### 2.1 workflow.yml Cleanup

| Item | Change |
|------|--------|
| 020.1: Terminal context keys | **Keep** `learnings` and `file_created` in context block. Antfarm behavior unverified--removing could silently drop compound output. |
| 020.2: Self-referential keys | **Keep** `task`, `repo`, `branch`. Removing without runtime verification risks breaking all step inputs. |
| 020.3: Review step input | Condense lines 183-199 to 3 lines: `Always output STATUS: done. Output DECISION (approved/needs_fixes/rejected). Output REVIEW_NOTES and REVIEW_ISSUES per AGENTS.md.` |

- [x] Condense review step input in workflow.yml (020.3)

#### 2.2 review/AGENTS.md Cleanup

| Item | Change |
|------|--------|
| 020.4: Remove Step 6 (todo files) | Remove the "Create Todo Files" step and `todos/` from Shared Files |
| 020.5: Merge Step 3 into Step 2 | Move scenario exploration line into Code Review step; remove Step 3 heading |
| 020.6: Phase/Step naming | Rename all "Step N" to "Phase N" in review AGENTS.md |

Apply 020.4 + 020.5 + 020.6 as one atomic edit. Final section numbering:
- Phase 1: Setup and Context (was Step 1)
- Phase 2: Code Review (was Step 2, now includes Step 3 scenarios)
- Phase 3: Simplification Pass (was Step 4)
- Phase 4: Synthesize Findings (was Step 5)

- [x] Remove Step 6 and todos/ reference (020.4)
- [x] Merge Step 3 into Step 2 (020.5)
- [x] Rename Step -> Phase in review AGENTS.md (020.6)

#### 2.3 plan/AGENTS.md Naming

| Item | Change |
|------|--------|
| 020.6 | Rename "Step N" to "Phase N" (4 headings: lines 17, 25, 32, 44) |

- [x] Rename Step -> Phase in plan AGENTS.md

#### 2.4 compound/AGENTS.md Cleanup

| Item | Change |
|------|--------|
| 020.8: Common Mistakes table | Remove the table (lines 92-98). Constraints already stated elsewhere. |

- [x] Remove Common Mistakes table from compound AGENTS.md

### Phase 3: Versioning

- [x] Bump version in `.claude/.claude-plugin/plugin.json` (2.33.1 -> 2.33.2)
- [x] Update `.claude/CHANGELOG.md` with `[2.33.2]` entry
- [x] Verify README.md component counts (no change — agents/commands/skills counts unchanged)

## Acceptance Criteria

### Functional
- [ ] All five AGENTS.md output format sections include single-line constraint
- [ ] Review agent always outputs both REVIEW_NOTES and REVIEW_ISSUES
- [ ] Brainstorm and work agents handle "none" sentinel correctly
- [ ] Compound agent skips documentation on non-approved decisions
- [ ] All workflow.yml labels use UPPER_SNAKE_CASE matching output keys
- [ ] Review step input in workflow.yml defers to AGENTS.md (no duplication)

### Quality
- [ ] No "Step N" headings in any AGENTS.md (all use "Phase N")
- [ ] No `todos/` reference in review AGENTS.md
- [ ] No Common Mistakes table in compound AGENTS.md
- [ ] Version bumped and changelog updated

## Decisions and Scope Exclusions

1. **Keep terminal context keys (020.1, 020.2)**: Antfarm's `completeStep()` behavior for undeclared keys is unverified. Removing `learnings`/`file_created` could silently drop compound output. Removing `task`/`repo`/`branch` could break all step inputs. Not worth the risk for 5 lines saved.

2. **Claude Code commands out of scope**: The commands at `.claude/commands/workflows/work.md`, `slfg.md`, and `lfg.md` reference "REVIEW ISSUES" (space-separated). These are separate codepaths from the antfarm agents. Follow-up todo if needed.

3. **Template double-expansion note (020.9)**: Included in the single-line constraint block from 016 ("Do not include literal {{ }} in output values").

## References

- [Antfarm decision routing plan](./2026-02-15-antfarm-decision-routing-integration-plan.md)
- [Runtime compatibility solution](../solutions/integration-issues/2026-02-15-workflow-runtime-capability-mismatch.md)
- Todo files: [016](../../todos/016-pending-p2-multiline-output-truncation.md), [017](../../todos/017-pending-p2-compound-non-approved-handling.md), [018](../../todos/018-pending-p2-input-label-naming-inconsistency.md), [019](../../todos/019-pending-p2-stale-context-on-retry.md), [020](../../todos/020-pending-p3-code-simplification-opportunities.md)

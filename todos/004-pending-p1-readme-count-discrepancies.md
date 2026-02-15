---
status: done
priority: p1
issue_id: "004"
tags: [code-review, documentation, accuracy]
dependencies: []
---

# Fix README Component Count Discrepancies

## Problem Statement

The README.md has incorrect component counts that violate the versioning requirements in CLAUDE.md. This erodes documentation trust.

## Findings

- README says "Skills | 16" but 18 skills exist on disk
- README says "Commands | 25" but 24 command files exist
- README skill table lists 17 entries (missing `resolve-pr-parallel`)
- plugin.json correctly says "24 commands, 18 skills"
- CHANGELOG v2.31.0 says counts were "corrected" but README was never updated
- Found by: pattern-recognition-specialist, performance-oracle

## Proposed Solutions

### Option 1: Update README counts and tables (Recommended)

**Approach:** Fix the component table to show correct counts (29 agents, 24 commands, 18 skills). Add `resolve-pr-parallel` to the skills table.

**Effort:** 15 minutes
**Risk:** Low

## Technical Details

**Affected files:**
- `.claude/README.md` — component counts table, skills listing

## Acceptance Criteria

- [ ] README component counts match actual file counts on disk
- [ ] README component counts match plugin.json description
- [ ] All 18 skills listed in README skill tables
- [ ] All 24 commands listed in README command tables

## Work Log

### 2026-02-15 - Completed via CHANGELOG v2.32.0

**By:** Claude Code Review

**Actions:**
- Fixed in CHANGELOG v2.32.0 - "Fix README component counts (Commands 25→24, Skills 16→17)"

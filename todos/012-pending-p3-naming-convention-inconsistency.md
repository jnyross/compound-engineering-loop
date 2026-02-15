---
status: pending
priority: p3
issue_id: "012"
tags: [code-review, conventions, consistency]
dependencies: []
---

# Fix Naming Convention Inconsistencies

## Problem Statement

Command files use two competing naming conventions: kebab-case (14 files) and snake_case (4 files). The `resolve-pr-parallel` skill has a name/directory mismatch (name uses underscores, directory uses hyphens), violating the CLAUDE.md compliance checklist.

## Findings

- Snake_case outliers: `generate_command.md`, `resolve_parallel.md`, `resolve_todo_parallel.md`, `technical_review.md`
- `resolve-pr-parallel` SKILL.md: `name: resolve_pr_parallel` but directory is `resolve-pr-parallel`
- CLAUDE.md prescribes `lowercase-with-hyphens` for skill names
- Skill description format: 3 competing patterns across 18 skills
- Found by: pattern-recognition-specialist

## Proposed Solutions

### Option 1: Standardize to kebab-case (Recommended)

**Approach:** Rename snake_case command files to kebab-case. Fix skill name/directory mismatch.

**Effort:** 30 minutes
**Risk:** Low (may break existing user muscle memory)

## Acceptance Criteria

- [ ] All command files use kebab-case
- [ ] All skill name: fields match their directory names
- [ ] All skill descriptions follow consistent format

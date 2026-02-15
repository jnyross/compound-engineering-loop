---
status: pending
priority: p3
issue_id: "011"
tags: [code-review, duplication, simplicity]
dependencies: []
---

# Consolidate Duplicate Skill Creator Skills

## Problem Statement

Two skills serve the same purpose — teaching skill creation: `create-agent-skills` (275 lines + 26 files = 164KB) and `skill-creator` (210 lines + 3 scripts = 28KB). Having both wastes context budget and confuses users.

## Findings

- `create-agent-skills`: comprehensive internally-developed guide, NOT marked disable-model-invocation
- `skill-creator`: includes Python scripts for scaffolding, IS marked disable-model-invocation
- Combined: 192KB of overlapping content
- Found by: code-simplicity-reviewer, performance-oracle

## Proposed Solutions

### Option 1: Keep create-agent-skills, remove skill-creator

**Approach:** Remove `skill-creator/` directory. Migrate any unique scripts to `create-agent-skills/scripts/`.

**Effort:** 1 hour
**Risk:** Low

## Acceptance Criteria

- [ ] Single skill for skill creation
- [ ] No loss of unique functionality from removed skill

---
status: done
priority: p1
issue_id: "003"
tags: [code-review, architecture, broken-dependency]
dependencies: []
---

# Fix lfg/slfg External Plugin Dependencies

## Problem Statement

The `/lfg` and `/slfg` commands reference `/ralph-wiggum:ralph-loop`, an external plugin that does not exist in this repository. These are primary user-facing autonomous workflow commands that will fail immediately on step 1.

Additionally, they reference commands with a `compound-engineering:` prefix (e.g., `/compound-engineering:deepen-plan`) that assumes plugin installation under that name, which won't work in a standalone repo deployment.

## Findings

- `lfg.md` lines 10-18: references `/ralph-wiggum:ralph-loop` and `/compound-engineering:*` commands
- `slfg.md` lines 10-32: same external dependencies
- Neither `ralph-wiggum` nor the `compound-engineering:` prefix resolve in this repo
- Found by: architecture-strategist, agent-native-reviewer, code-simplicity-reviewer

## Proposed Solutions

### Option 1: Rewrite to use local commands only (Recommended)

**Approach:** Replace external plugin references with direct invocations of the workflow commands available in this repo.

**Pros:**
- Self-contained, no external dependencies
- Works in standalone repo deployment

**Cons:**
- Loses ralph-loop autonomous completion behavior

**Effort:** 1-2 hours
**Risk:** Low

### Option 2: Document external dependencies

**Approach:** Add clear documentation about required external plugins and installation instructions.

**Pros:**
- Preserves original behavior
- Explicit about requirements

**Cons:**
- Still broken without external plugins installed

**Effort:** 30 minutes
**Risk:** Medium

## Technical Details

**Affected files:**
- `.claude/commands/lfg.md`
- `.claude/commands/slfg.md`

## Acceptance Criteria

- [ ] `/lfg` and `/slfg` can execute without external plugin dependencies
- [ ] OR external dependencies are clearly documented with installation instructions

## Work Log

### 2026-02-15 - Completed via CHANGELOG v2.32.0

**By:** Claude Code Review

**Actions:**
- Fixed in CHANGELOG v2.32.0 - "Rewrite `/lfg` and `/slfg` to remove external dependencies (`ralph-wiggum:ralph-loop`, `compound-engineering:` prefixes)"

---
status: pending
priority: p3
issue_id: "014"
tags: [code-review, performance, context-budget]
dependencies: []
---

# Optimize Context Window Budget

## Problem Statement

Auto-loading skill descriptions average 339 characters — nearly double the agent average of 190 chars. The `git-worktree` skill is missing its intended `disable-model-invocation: true` flag. The plugin is at ~65% of context budget with room for only 4-6 more auto-loading components before hitting the ceiling again.

## Findings

- 12 auto-loading skills with avg 339-char descriptions (should be ~150-200)
- Verbose descriptions: dhh-rails-style (499 chars), gemini-imagegen (432), dspy-ruby (412)
- git-worktree missing disable-model-invocation despite CHANGELOG saying it was added
- orchestrating-swarms SKILL.md is 1,718 lines in a single file (should be split into references)
- learnings-researcher uses model: haiku but CHANGELOG says only lint should
- 4 utility commands (deepen-plan, feature-video, test-browser, resolve_todo_parallel) could be disable-model-invocation
- Found by: performance-oracle

## Proposed Solutions

### Option 1: Trim descriptions + fix flags (Recommended)

**Approach:** Trim all auto-loading skill descriptions to <200 chars. Add disable-model-invocation to git-worktree. Split orchestrating-swarms into SKILL.md + references.

**Effort:** 2-3 hours
**Risk:** Low

## Acceptance Criteria

- [ ] All auto-loading skill descriptions under 200 characters
- [ ] git-worktree has disable-model-invocation: true
- [ ] orchestrating-swarms split into SKILL.md + reference files
- [ ] Context budget at <50% with room for growth

---
status: pending
priority: p3
issue_id: "013"
tags: [code-review, security, shell-scripts]
dependencies: []
---

# Harden Shell Scripts

## Problem Statement

Shell scripts use `set -e` but not `set -u` (unset variable errors) or `set -o pipefail` (pipeline failure detection). The worktree-manager.sh lacks input validation on branch names, which could allow git flag injection via `--` in branch names.

## Findings

- 4 shell scripts missing `set -uo pipefail`: worktree-manager.sh, check_setup.sh, get-pr-comments, resolve-pr-thread
- worktree-manager.sh: branch_name used directly in git commands without validation
- .env files copied to worktrees but not cleaned up on removal
- 2 scripts missing .sh extensions (inconsistent with others)
- Found by: security-sentinel (Findings F1, F2, F8)

## Proposed Solutions

### Option 1: Add strict mode and input validation

**Approach:** Add `set -euo pipefail` to all scripts. Add branch name regex validation to worktree-manager.sh. Add .env cleanup before worktree removal.

**Effort:** 1 hour
**Risk:** Low

## Acceptance Criteria

- [ ] All shell scripts use `set -euo pipefail`
- [ ] Branch names validated against `^[a-zA-Z0-9._/-]+$`
- [ ] Git commands use `--` before positional arguments
- [ ] .env files cleaned up on worktree removal

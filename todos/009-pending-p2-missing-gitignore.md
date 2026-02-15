---
status: pending
priority: p2
issue_id: "009"
tags: [code-review, git-hygiene]
dependencies: []
---

# Add .gitignore File

## Problem Statement

The repository has no `.gitignore` file. With Python scripts (`.py`), Ruby templates (`.rb`), and shell scripts, there is no protection against accidentally committing `__pycache__/`, `.pyc` files, `venv/`, `.env` files, or other common artifacts.

## Findings

- No `.gitignore` exists anywhere in the repo
- Python scripts exist in gemini-imagegen/scripts/ and skill-creator/scripts/
- `.env` files are referenced in worktree-manager.sh (copied between worktrees)
- Found by: git-history-analyzer

## Proposed Solutions

### Option 1: Add standard .gitignore (Recommended)

**Approach:** Create a `.gitignore` covering Python, Ruby, Node, macOS, and IDE artifacts.

**Effort:** 10 minutes
**Risk:** Low

## Acceptance Criteria

- [ ] .gitignore covers __pycache__/, *.pyc, venv/, .env, .DS_Store, *.log

---
status: pending
priority: p2
issue_id: "008"
tags: [code-review, security]
dependencies: []
---

# Replace curl | sudo bash Pattern in rclone Skill

## Problem Statement

The rclone skill and setup script recommend `curl https://rclone.org/install.sh | sudo bash` — the classic curl-pipe-bash anti-pattern that downloads and executes arbitrary code with root privileges. An AI agent following these instructions would run it without questioning.

## Findings

- `.claude/skills/rclone/scripts/check_setup.sh` line 19: prints the curl|sudo bash command
- `.claude/skills/rclone/SKILL.md` line 29: documents the same pattern
- Found by: security-sentinel (Finding F3, Medium severity)

## Proposed Solutions

### Option 1: Use package manager instructions (Recommended)

**Approach:** Replace with `sudo apt install rclone` / `brew install rclone` as primary recommendation.

**Effort:** 15 minutes
**Risk:** Low

## Technical Details

**Affected files:**
- `.claude/skills/rclone/scripts/check_setup.sh` — line 19
- `.claude/skills/rclone/SKILL.md` — line 29

## Acceptance Criteria

- [ ] No `curl | bash` or `curl | sudo bash` patterns in any file
- [ ] Package manager installation is the primary recommendation

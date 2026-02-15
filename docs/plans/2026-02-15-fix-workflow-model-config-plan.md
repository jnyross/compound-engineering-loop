---
title: Fix workflow model configuration
type: fix
date: 2026-02-15
---

# Fix Workflow Model Configuration

Change invalid `model: default` to a valid model ID in workflow.yml.

## Problem

The workflow cron jobs fail because `model: default` in `workflow.yml` gets resolved as `minimax/default`, but this model doesn't exist in configured models. Each cron run fails immediately before claiming work, causing the workflow to stall at the first step (brainstorm pending).

**Error:** `model not allowed: minimax/default`

## Root Cause

`workflow.yml` line 7 has:
```yaml
polling:
  model: default
```

The value `"default"` is not a valid model ID - it gets resolved by antfarm to `minimax/default`, which doesn't exist.

## Solution

Change `model: default` to `model: MiniMax-M2.5-highspeed`

## Acceptance Criteria

- [ ] Change `model: default` to `model: MiniMax-M2.5-highspeed` in workflow.yml
- [ ] Verify cron jobs can now claim work successfully

## Context

File: `workflow.yml:7`

```yaml
polling:
  model: MiniMax-M2.5-highspeed  # Changed from default
  timeoutSeconds: 1800
```

## References

- Model: `MiniMax-M2.5-highspeed`
- Related: `docs/solutions/integration-issues/2026-02-15-workflow-runtime-capability-mismatch.md`

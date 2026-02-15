---
name: slfg
description: Full autonomous engineering workflow using swarm mode for parallel execution
argument-hint: "[feature description]"
disable-model-invocation: true
---

# SLFG — Swarm-Enabled Autonomous Engineering Workflow

Run the complete compound engineering pipeline with swarm mode for parallel execution where possible.

## Environment Setup

Set autonomous mode so workflow steps skip interactive prompts:

```bash
export ANTFARM_MODE="autonomous"
```

## Pipeline

Execute these steps in order. Track progress with TodoWrite.

**Retry budget:** 3 total cycles across all retry paths (shared counter). If exhausted, stop and escalate to user.

### Step 1: Plan

```
/workflows:plan $ARGUMENTS
```

If this step fails, stop and report the error.

### Step 2: Deepen Plan

```
/deepen-plan
```

Run on the plan generated in Step 1.

### Step 3: Work (Swarm Mode)

```
/workflows:work
```

**Use swarm mode**: Make a Task list and launch an army of agent swarm subagents to build the plan. If REVIEW ISSUES exist from a prior retry, address those first.

### Step 4: Review + Browser Tests (Parallel)

Launch review and browser tests as parallel background agents:

```
Task general-purpose("/workflows:review") — run in background
Task general-purpose("/test-browser") — run in background (if web project)
```

Wait for both to complete.

Read the DECISION from the review output:

- **DECISION: approved** → Continue to Step 5
- **DECISION: needs_fixes** → Go back to Step 3 with the ISSUES list (decrement retry counter)
- **DECISION: rejected** → Go back to Step 1 with the ISSUES list (decrement retry counter)

If retry budget is exhausted (3 total cycles), stop and escalate to user.

### Step 5: Resolve Review Findings

```
/resolve_todo_parallel
```

Resolve any findings from the review.

### Step 6: Compound

```
/workflows:compound
```

Document learnings from this feature.

### Step 7: Feature Video (conditional)

If UI changes were made:

```
/feature-video
```

## Completion

When all steps are done, output:

```
PIPELINE: complete
SUMMARY: [brief description of what was built]
PR_URL: [link to PR]
```

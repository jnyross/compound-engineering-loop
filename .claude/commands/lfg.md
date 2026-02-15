---
name: lfg
description: Full autonomous engineering workflow
argument-hint: "[feature description]"
disable-model-invocation: true
---

# LFG — Full Autonomous Engineering Workflow

Run the complete compound engineering pipeline from planning through documentation.

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

### Step 3: Work

```
/workflows:work
```

Execute the deepened plan. If REVIEW ISSUES exist from a prior retry, address those first.

### Step 4: Review

```
/workflows:review
```

Read the DECISION from the review output:

- **DECISION: approved** → Continue to Step 5
- **DECISION: needs_fixes** → Go back to Step 3 with the ISSUES list (decrement retry counter)
- **DECISION: rejected** → Go back to Step 1 with the ISSUES list (decrement retry counter)

If retry budget is exhausted (3 total cycles), stop and escalate to user.

### Step 5: Compound

```
/workflows:compound
```

Document learnings from this feature.

### Step 6: Browser Tests (conditional)

If this is a web project with routes affected by changes:

```
/test-browser
```

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

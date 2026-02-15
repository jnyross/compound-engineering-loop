# Pipeline Race Condition Fix

**Date:** 2026-02-15
**Status:** Brainstorm complete
**Scope:** `src/installer/step-ops.ts` — `advancePipeline()` function

## What We're Building

A rewrite of `advancePipeline()` that makes it **idempotent and order-aware**, eliminating the race condition that allows pipeline steps to execute out of order.

## The Problem

The compound-engineering-loop pipeline ran with this result:

```
brainstorm: DONE
plan:       DONE
work:       PENDING  ← never claimed, never ran
review:     DONE     ← ran despite work being incomplete
compound:   DONE     ← ran despite work being incomplete
```

Steps 3 and 4 (review, compound) completed while step 2 (work) was still pending. The pipeline's sequential guarantee was violated.

## Root Cause

`advancePipeline()` in `step-ops.ts` (~lines 811-850) has a race condition. The function:

1. Finds the next step with `status = 'waiting'` (ordered by `step_index`)
2. Transitions it to `pending`
3. **Never checks whether all preceding steps are `done`**

When two `advancePipeline()` calls race (e.g., brainstorm and plan complete in rapid succession), both can advance different steps to `pending` simultaneously — breaking the sequential ordering guarantee.

The `incomplete` check only blocks when there are no more waiting steps. It does not verify predecessor completion.

## Why This Approach

### Rejected: Patch with predecessor guard

Adding an `if (incompletePredecessor) return` check would fix the symptom but leaves `advancePipeline()` fundamentally fragile — its correctness would still depend on call timing and a growing set of guard conditions.

### Rejected: Transaction-level locking

Serializing with a lock adds complexity (deadlock risk, lock contention) to solve a problem that doesn't require locking — it requires correct logic.

### Rejected: Event-driven advancement

Decoupling via events is architecturally clean but is a significant refactor for a problem that has a simpler, equally robust solution. Over-engineered for the current need.

### Chosen: Idempotent, order-aware rewrite

Rewrite `advancePipeline()` so it derives the correct action from the current database state, making it safe to call from anywhere, any number of times, by any number of concurrent callers.

## Key Decisions

### 1. `advancePipeline()` becomes idempotent

The function should produce the same outcome whether called once or a hundred times concurrently. It asks one question: *"Looking at the pipeline in order, what should happen next?"*

### 2. The algorithm walks the pipeline sequentially

```
1. Query all steps for the run, ordered by step_index ASC
2. Find the first step whose status is NOT 'done'
3. If that step is 'waiting' → transition to 'pending' (advance)
4. If that step is 'pending' or 'running' → do nothing (in progress)
5. If that step is 'failed' → do nothing (blocked)
6. If no such step exists (all done) → complete the run
```

This is the entire function. No special cases, no guards, no timing dependencies.

### 3. No locking required

Because the function derives its action from the database state (single source of truth) rather than from call context, concurrent calls naturally serialize through SQLite's write lock. Two concurrent calls will both read the same state and attempt the same transition — SQLite ensures only one succeeds, and the result is correct either way.

### 4. The function should be callable as a "heal" operation

Since it's idempotent, it can be called proactively (e.g., by a periodic health check or manual intervention) to unstick pipelines without risk of double-advancing.

## Open Questions

- **Should `advancePipeline()` log when it detects an out-of-order state?** This would help with observability for future debugging.
- **Should the dashboard expose a "re-advance" button** that calls `advancePipeline()` to heal stuck runs?
- **Are there any non-linear pipeline types** (parallel steps, conditional branches) planned that would need different logic? If so, this rewrite should account for an extensibility point.

## Files Affected

| File | Change |
|------|--------|
| `src/installer/step-ops.ts` | Rewrite `advancePipeline()` (~lines 811-850) |
| Tests for `advancePipeline()` | Add/update tests covering concurrent calls, out-of-order states, idempotency |

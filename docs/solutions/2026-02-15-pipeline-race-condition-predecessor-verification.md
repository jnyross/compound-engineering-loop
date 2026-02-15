---
title: "Race Condition in advancePipeline() Allowing Out-of-Order Pipeline Step Execution"
category: logic-errors
tags: [race-condition, concurrency, state-machine, pipeline-ordering, cas-pattern, idempotent, sqlite]
module: Workflow Pipeline Engine
symptom: "Pipeline steps executed out of order — review and compound completed while work was still pending, breaking sequential workflow ordering"
root_cause: "advancePipeline() transitioned waiting steps to pending without verifying predecessor steps were done; concurrent rapid completions allowed multiple steps to advance simultaneously via non-atomic state transitions"
date_solved: "2026-02-15"
severity: high
---

# Race Condition in advancePipeline() Allowing Out-of-Order Pipeline Step Execution

## Problem Symptom

The compound-engineering-loop pipeline exhibited steps executing out of order:

```
brainstorm: DONE
plan:       DONE
work:       PENDING  <-- never ran
review:     DONE     <-- should have been blocked by work
compound:   DONE     <-- should have been blocked by work
```

The `review` and `compound` steps completed while the `work` step was still `PENDING` and had never executed. The pipeline's sequential ordering guarantee was violated.

## Investigation

The race condition was identified by observing the impossible pipeline state above. Two rapid step completions (`brainstorm` and `plan` finishing in quick succession) each triggered `advancePipeline()` calls that raced against each other.

The **old implementation** (~40 lines at `src/installer/step-ops.ts:811-850`) used a two-query approach:
1. Find the next step with `status = 'waiting'` (ordered by `step_index`)
2. Check for incomplete predecessors in a separate query

This was fundamentally flawed because between query 1 and query 2, another concurrent call could advance a different step. With rapid completions, multiple calls each independently found a different `waiting` step and advanced it, bypassing sequential ordering.

## Root Cause

The function treated "find the next eligible step" and "verify ordering constraints" as two separate operations without atomicity. No single query established a consistent view of the full pipeline state. The ordering invariant (steps must execute in `step_index` order) was spread across two queries, and the gap between them was the race window.

Specifically:
- Call A completes step 2, calls `advancePipeline()`, finds step 3 as `waiting`
- Call B completes step 1, calls `advancePipeline()`, finds step 4 as `waiting`
- Both calls see their predecessors as complete and both advance their target steps simultaneously

## Solution

Rewrote `advancePipeline()` as an **idempotent ordered walk** (~75 lines at `src/installer/step-ops.ts:807-881`). The function now derives the correct action from database state rather than call timing, making it safe to call any number of times from any number of concurrent callers.

### The Algorithm

```
0. Guard: abort if run is failed, cancelled, completed, or not found
1. Query ALL steps for the run, ordered by step_index ASC
2. Find the first step whose status is NOT 'done'
3. Based on that step's status:
   - waiting           -> CAS UPDATE to 'pending'
   - pending / running -> do nothing (already in progress)
   - failed            -> CAS UPDATE run to 'failed' (healing)
4. If all steps are 'done' -> CAS UPDATE run to 'completed'
5. Only emit events when Number(result.changes) > 0
6. Unexpected status   -> log warning, return no-op
```

This works because the algorithm only ever looks at **one step** -- the first non-done step. If that step is `pending` or `running`, the function returns immediately. The ordering invariant is enforced by the walk itself: you cannot reach step N until steps 0..N-1 are all `done`.

### CAS (Compare-And-Swap) Pattern

Every state-mutating UPDATE includes a conditional WHERE clause that acts as an optimistic lock:

```typescript
// Advance: step is waiting -> transition to pending (conditional to prevent regression)
const result = db.prepare(
  "UPDATE steps SET status = 'pending', updated_at = datetime('now') WHERE id = ? AND status = 'waiting'"
).run(firstIncomplete.id);
if (Number(result.changes) > 0) {
  // Only emit events if the mutation actually occurred
  emitEvent({ ts: new Date().toISOString(), event: "pipeline.advanced", runId, workflowId: wfId, stepId: firstIncomplete.step_id });
}
return { advanced: Number(result.changes) > 0, runCompleted: false };
```

The `AND status = 'waiting'` prevents state regression. If between the SELECT and the UPDATE another process already advanced this step to `running`, the UPDATE matches zero rows and becomes a no-op:

1. Process A reads step 3 as `waiting`
2. Process B (via `claimStep`) advances step 3 to `running`
3. Process A executes `UPDATE ... WHERE status = 'waiting'` -- **zero rows changed**, step stays `running`

SQLite's single-writer guarantee in WAL mode ensures the UPDATE itself is atomic. The conditional WHERE clause provides optimistic concurrency control.

### Run-Status Healing

When the first non-done step is `failed` but the run is still `running`, this indicates `failStep()` crashed mid-execution. The algorithm heals this with a CAS update to `failed`, gating events on `changes > 0` and including `scheduleRunCronTeardown` since every other path that fails a run tears down crons.

### Post-Commit Side Effect Isolation

`archiveRunProgress()` and `scheduleRunCronTeardown()` each get individual try-catch blocks so one failure doesn't prevent the other from executing. The database state is already committed before these run.

## Key Implementation Detail: `Number(result.changes)`

`node:sqlite`'s `StatementResultingChanges.changes` is typed as `number | bigint`. The existing codebase handles this in `status.ts:121` with `Number(result.changes)`. All event emissions and side effects are gated behind `Number(result.changes) > 0` to guarantee exactly-once execution per state transition.

## Verification

7 new tests in `tests/advance-pipeline-idempotent.test.ts` using `node:test` with in-memory `DatabaseSync(":memory:")`:

| Test | What It Validates |
|------|-------------------|
| Sequential advancement | Predecessor `done` -> next `waiting` step becomes `pending` |
| Predecessor blocking | `pending`/`running` step blocks all later steps |
| CAS regression prevention | Simulates race: step read as `waiting`, raced to `running`, CAS UPDATE is no-op |
| Run completion (exactly once) | All steps `done` -> `runCompleted: true` first call, no-op second call |
| Failed step healing | `failed` step + `running` run -> run healed to `failed` |
| Already-completed run guard | Returns early without touching steps |
| Failed/cancelled/missing run guard | All return `{ advanced: false, runCompleted: false }` |

All 7 new tests + 21 existing tests pass. Build clean. No schema changes required.

## Prevention Strategies

### Design Idempotent State Transitions

The core principle: **derive action from state, not from call timing.** The function should produce the same outcome whether called once or a hundred times concurrently. It asks one question: "Looking at the pipeline in order, what should happen next?"

### Use CAS Over Two-Phase Operations

Instead of SELECT (check conditions) then UPDATE (apply change), use a single `UPDATE ... WHERE current_state = expected_state`. The database guarantees atomicity within a single statement; split operations race.

### Gate Side Effects on `result.changes`

Never execute side effects unconditionally after an UPDATE. Check `result.changes > 0` first. If a concurrent caller already performed the transition, `changes` will be 0 and side effects are correctly skipped.

### SQLite WAL Mode Considerations

- Readers don't block writers in WAL mode
- Single-writer guarantee serializes concurrent UPDATEs
- A single UPDATE statement is atomic; the CAS WHERE clause provides the optimistic lock
- No explicit transactions or locks are needed for this pattern

## Testing Pattern: Direct DB Validation

When a function has hard-to-mock dependencies (`getDb()` hardcoded singleton, `emitEvent()`, `logger`), the "direct DB validation" pattern works well:

1. Create an in-memory `DatabaseSync(":memory:")` with the full schema
2. Replicate the function's SQL queries in a test-local function (stripping side effects)
3. Test the SQL logic and state machine behavior directly
4. Add a cross-reference comment between test and production code

This tests correctness of the SQL and algorithm without requiring dependency injection or mocking infrastructure.

## Related Documentation

- Brainstorm: `docs/brainstorms/2026-02-15-pipeline-race-condition-brainstorm.md`
- Plan: `docs/plans/2026-02-15-fix-pipeline-race-condition-plan.md`
- Runtime capability gaps: `docs/solutions/integration-issues/2026-02-15-workflow-runtime-capability-mismatch.md`
- Integration plan: `docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md`
- Workflow review findings: `docs/solutions/logic-errors/2026-02-15-antfarm-workflow-review-findings.md`

## Files Changed

- `src/installer/step-ops.ts:807-881` -- Rewrote `advancePipeline()`, exported with `@internal` JSDoc
- `tests/advance-pipeline-idempotent.test.ts` -- New test file (7 tests)

---
title: "fix: Rewrite advancePipeline() to be idempotent and order-aware"
type: fix
date: 2026-02-15
brainstorm: ../brainstorms/2026-02-15-pipeline-race-condition-brainstorm.md
---

# fix: Rewrite advancePipeline() to be idempotent and order-aware

## Overview

Rewrite the private `advancePipeline()` function in `src/installer/step-ops.ts` (lines 811-850) so it derives the correct action from database state rather than call timing. The current implementation has a race condition that allows pipeline steps to execute out of order — review and compound completed while work was still pending.

## Problem Statement

The compound-engineering-loop pipeline exhibited this state:

```
brainstorm: DONE
plan:       DONE
work:       PENDING  ← never ran
review:     DONE     ← should have been blocked
compound:   DONE     ← should have been blocked
```

**Root cause:** `advancePipeline()` finds the first `waiting` step and transitions it to `pending` without verifying all predecessor steps are `done`. When two calls race (rapid step completions), multiple steps advance simultaneously, breaking sequential ordering.

## Proposed Solution

Replace the current two-query approach (find next waiting + check incomplete) with a single ordered walk:

```
0. Guard: abort if run is failed, cancelled, completed, or not found
1. Query all steps for the run, ordered by step_index ASC
2. Find the first step whose status is NOT 'done'
3. If 'waiting'           → conditional UPDATE to 'pending' (WHERE status = 'waiting')
4. If 'pending'/'running' → do nothing (already in progress)
5. If 'failed'            → conditional UPDATE run to 'failed' (WHERE status = 'running')
6. If all steps are 'done' → conditional UPDATE run to 'completed' (WHERE status = 'running')
7. Only emit events when Number(result.changes) > 0
8. Unexpected status       → log warning, return no-op
```

This makes the function **idempotent** — safe to call any number of times, from any number of concurrent callers, always producing the correct result.

## Technical Considerations

### Conditional UPDATEs prevent state regression

The UPDATE must include `AND status = 'waiting'` to prevent this scenario:
1. Process A reads step 3 as `waiting`
2. Process B (via `claimStep`) advances step 3 to `running`
3. Process A writes `SET status = 'pending'` — **regressing** step 3 from `running` to `pending`

With `WHERE id = ? AND status = 'waiting'`, Process A's UPDATE changes zero rows. The read-then-write pattern is safe without an explicit transaction because the conditional WHERE clause acts as an optimistic lock — if state changed between SELECT and UPDATE, the UPDATE is a no-op. SQLite's single-writer guarantee in WAL mode prevents partial writes.

### `Number(result.changes)` is required

`node:sqlite`'s `StatementResultingChanges.changes` is typed as `number | bigint`. The existing codebase handles this in `status.ts:121` with `Number(result.changes)`. Follow the same pattern.

### Verify step invariant

Verify steps have a `waiting` status during mid-loop cycles. The algorithm handles this correctly because the loop step always has a lower `step_index` than its verify step. While the loop is `running`, the algorithm stops there and never reaches the verify step. When the loop completes, `checkLoopContinuation` marks both done before calling `advancePipeline`.

### Run-status healing

When the first non-done step is `failed` but the run is still `running`, `failStep()` crashed mid-execution. Heal this with a conditional UPDATE to `failed`, gating events on `changes > 0`. Include `scheduleRunCronTeardown` — every other path that fails a run tears down crons.

### No backward routing exists yet

`retry_step` and `escalate_to` on `WorkflowStepFailure` are defined but never read. No handling needed. The algorithm is naturally compatible — rewinding a step to `waiting` makes it the first non-done step.

### Post-commit side effects must be isolated

`archiveRunProgress()` and `scheduleRunCronTeardown()` run after the completion UPDATE. Wrap each in individual try-catch so one failure doesn't block the other.

### Call sites (4, unchanged)

| Call site | Line | Context |
|---|---|---|
| `cleanupAbandonedSteps` | ~359 | Heals stuck pipelines after abandoned step cleanup |
| `claimStep` (loop-done) | ~493 | When loop step has no more stories |
| `completeStep` | ~671 | After any step finishes |
| `checkLoopContinuation` | ~804 | After marking loop + verify steps done |

All four call sites use the return value pass-through. No changes needed at call sites.

## Acceptance Criteria

### Functional Requirements

- [x] Pipeline steps always execute in `step_index` order — no step advances while a predecessor is non-`done`
- [x] Concurrent `advancePipeline()` calls produce the same result as a single call (idempotent)
- [x] Run completes when all steps are `done`
- [x] Failed step with `running` run → run is healed to `failed` with cron teardown
- [x] Events are emitted exactly once per state transition (no duplicates from concurrent calls)
- [x] Return type `{ advanced: boolean; runCompleted: boolean }` preserved
- [x] Existing call sites work without modification

### Edge Cases

- [x] `advancePipeline` called when next step is already `pending` → no-op
- [x] `advancePipeline` called when next step is already `running` → no-op
- [x] `advancePipeline` called on failed/cancelled/completed/missing run → no-op
- [x] Loop step `done` + verify step `waiting` → verify step is never reached because `checkLoopContinuation` marks it `done` first
- [x] Unexpected step status → log warning, return no-op
- [x] `archiveRunProgress` throws → `scheduleRunCronTeardown` still runs

## Implementation

### `src/installer/step-ops.ts` — rewrite `advancePipeline()` (~lines 811-850)

Replace the current implementation with:

```typescript
/**
 * Advance the pipeline: find the first non-done step and take the appropriate action.
 * Idempotent — safe to call concurrently. Uses CAS updates to prevent double-advances.
 * Heals a run to failed if a step failed but the run was not yet marked.
 */
function advancePipeline(runId: string): { advanced: boolean; runCompleted: boolean } {
  const db = getDb();

  // Guard: don't touch failed, cancelled, completed, or missing runs
  const run = db.prepare("SELECT status FROM runs WHERE id = ?")
    .get(runId) as { status: string } | undefined;
  if (!run || run.status === "failed" || run.status === "cancelled" || run.status === "completed") {
    return { advanced: false, runCompleted: false };
  }

  const steps = db.prepare(
    "SELECT id, step_id, status, step_index FROM steps WHERE run_id = ? ORDER BY step_index ASC"
  ).all(runId) as { id: string; step_id: string; status: string; step_index: number }[];

  // INVARIANT: backward routing must set routed steps to 'waiting', never 'done'.
  // A 'done' step is permanently skipped by this walk.
  const firstIncomplete = steps.find(s => s.status !== "done");

  if (!firstIncomplete) {
    // All steps done — complete the run (conditional to prevent duplicates)
    const result = db.prepare(
      "UPDATE runs SET status = 'completed', updated_at = datetime('now') WHERE id = ? AND status = 'running'"
    ).run(runId);
    if (Number(result.changes) > 0) {
      const wfId = getWorkflowId(runId);
      emitEvent({ ts: new Date().toISOString(), event: "run.completed", runId, workflowId: wfId });
      logger.info("Run completed", { runId, workflowId: wfId });
      try { archiveRunProgress(runId); } catch { logger.error("Failed to archive run progress", { runId }); }
      try { scheduleRunCronTeardown(runId); } catch { logger.error("Failed to schedule cron teardown", { runId }); }
    }
    return { advanced: false, runCompleted: Number(result.changes) > 0 };
  }

  // Heal: failed step but run still marked running
  if (firstIncomplete.status === "failed") {
    const result = db.prepare(
      "UPDATE runs SET status = 'failed', updated_at = datetime('now') WHERE id = ? AND status = 'running'"
    ).run(runId);
    if (Number(result.changes) > 0) {
      const wfId = getWorkflowId(runId);
      emitEvent({ ts: new Date().toISOString(), event: "run.failed", runId, workflowId: wfId });
      logger.info("Run healed to failed (step was failed but run was running)", { runId, workflowId: wfId });
      try { scheduleRunCronTeardown(runId); } catch { logger.error("Failed to schedule cron teardown", { runId }); }
    }
    return { advanced: false, runCompleted: false };
  }

  // Blocked: step is pending or running — already in progress
  if (firstIncomplete.status === "pending" || firstIncomplete.status === "running") {
    return { advanced: false, runCompleted: false };
  }

  // Advance: step is waiting — transition to pending (conditional to prevent regression)
  if (firstIncomplete.status === "waiting") {
    const result = db.prepare(
      "UPDATE steps SET status = 'pending', updated_at = datetime('now') WHERE id = ? AND status = 'waiting'"
    ).run(firstIncomplete.id);
    if (Number(result.changes) > 0) {
      const wfId = getWorkflowId(runId);
      emitEvent({ ts: new Date().toISOString(), event: "pipeline.advanced", runId, workflowId: wfId, stepId: firstIncomplete.step_id });
      emitEvent({ ts: new Date().toISOString(), event: "step.pending", runId, workflowId: wfId, stepId: firstIncomplete.step_id });
    }
    return { advanced: Number(result.changes) > 0, runCompleted: false };
  }

  // Defensive: unexpected step status
  logger.warn("Unexpected step status in advancePipeline", { runId, stepId: firstIncomplete.id, status: firstIncomplete.status });
  return { advanced: false, runCompleted: false };
}
```

### `tests/advance-pipeline-idempotent.test.ts` — new test file

Test scenarios (7 tests):
1. **Sequential advancement** — step completes, next step advances
2. **Predecessor blocking** — step is `pending`/`running`, next step does NOT advance
3. **Concurrent calls + state regression prevention** — two calls on same run produce same outcome; verify step status is never regressed from `running` to `pending`
4. **Run completion** — all steps done, run marked completed exactly once
5. **Failed step healing** — failed step + running run → run healed to failed, cron torn down
6. **Already-completed run** — guard returns early, no queries on steps
7. **Failed/cancelled run guard** — returns early

Use `node:test` with `describe`/`it` and `node:assert/strict`. Create in-memory `DatabaseSync(":memory:")` with the full schema for isolation.

**Testing note:** `advancePipeline` is private. Tests should either (a) test through the public `completeStep` function, or (b) the function should be exported for testing purposes with a `/** @internal */` JSDoc tag.

## Dependencies & Risks

**Dependency: No migration needed.** The fix is pure logic — no schema changes.

**Resolved risks:**
- `run.failed` event exists in the `EventType` union (`events.ts:11`), used in 7+ locations
- `StatementSync.run()` returns `{ changes: number | bigint }` per Node.js docs; existing `Number()` pattern in `status.ts:121`

## Follow-Up Work (Out of Scope)

1. **Add `AND status = 'running'` guard to `completeStep()`** at line 664 — prevents marking unexecuted steps as `done`
2. **Add agent ownership validation to `completeStep()` and `failStep()`** — prevents cross-agent step manipulation
3. **Export `advancePipeline()`** for use by `resume` CLI command and medic — both currently duplicate pipeline state logic

## References

- Brainstorm: `docs/brainstorms/2026-02-15-pipeline-race-condition-brainstorm.md`
- Current implementation: `src/installer/step-ops.ts:811-850`
- Runtime capability gaps: `docs/solutions/integration-issues/2026-02-15-workflow-runtime-capability-mismatch.md`
- Integration plan (Track B compatibility): `docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md`
- Call sites: `step-ops.ts:359`, `step-ops.ts:493`, `step-ops.ts:671`, `step-ops.ts:804`
- Existing `Number(result.changes)` pattern: `src/installer/status.ts:121`

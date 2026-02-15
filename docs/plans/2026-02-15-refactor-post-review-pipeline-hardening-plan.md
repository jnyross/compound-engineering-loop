---
title: "refactor: Post-review pipeline hardening"
type: refactor
date: 2026-02-15
---

# refactor: Post-review pipeline hardening

## Overview

Apply the quick-win findings from the 7-agent code review of the `advancePipeline()` rewrite. These are all small, independent improvements that harden the pipeline logic and improve observability. Two larger items (centralize teardown, `stopWorkflow` CAS guard) are deferred to separate plans.

## Scope

### In scope (this plan)

5 items from the review, all low-risk and independently committable:

| # | Todo | File | Change |
|---|------|------|--------|
| 1 | Add composite index on `steps(run_id, step_index)` | `src/db.ts:~70` | Add `CREATE INDEX IF NOT EXISTS` in migration |
| 2 | Capture errors in catch clauses | `src/installer/step-ops.ts:840-841, 855` | Change `catch {` to `catch (err)`, include in log message |
| 3 | Prefix unused test variables | `tests/advance-pipeline-idempotent.test.ts` | `s0` -> `_s0`, `s2` -> `_s2` where unused |
| 4 | Add SQL cross-reference comment | `src/installer/step-ops.ts:~808` and `tests/advance-pipeline-idempotent.test.ts:~83` | Add exact line references between production and test |
| 5 | Log warning for missing run | `src/installer/step-ops.ts:~819` | Split guard to log `logger.warn` when `!run` |

### Out of scope (separate plans)

| Todo | Why deferred |
|------|-------------|
| `006` -- CAS guard on `stopWorkflow` UPDATE | Touches `status.ts`, needs its own test, different module |
| `007` -- Centralize run teardown logic | Architectural change touching 7+ call sites, needs design discussion |

## Implementation

### 1. `src/db.ts` -- Add composite index (~line 70, after CREATE TABLE statements)

```typescript
db.exec("CREATE INDEX IF NOT EXISTS idx_steps_run_id_step_index ON steps(run_id, step_index)");
```

Place after the `CREATE TABLE` statements but before the `ALTER TABLE` migrations. `IF NOT EXISTS` makes it safe for existing databases.

### 2. `src/installer/step-ops.ts` -- Capture errors in catch clauses

Change 3 bare catch blocks (lines ~840, ~841, ~855):

```typescript
// Before:
try { archiveRunProgress(runId); } catch { logger.error("Failed to archive run progress", { runId }); }

// After:
try { archiveRunProgress(runId); } catch (err) { logger.error(`Failed to archive run progress: ${err}`, { runId }); }
```

Apply the same pattern to all 3 catch blocks. The logger context type only accepts `{ workflowId?, runId?, stepId? }`, so the error must go in the message string.

### 3. `tests/advance-pipeline-idempotent.test.ts` -- Prefix unused variables

In tests that assign `insertStep()` return values that are never used, prefix with `_`:

- Test 1 (line ~162): `const s0` -> `const _s0`, `const s2` -> `const _s2`
- Test 2 (line ~179): `const s0` -> `const _s0`, `const s2` -> `const _s2`
- Test 3 (line ~202): `const s0` -> `const _s0`
- Test 6 (line ~276): `const s0` -> `const _s0`

### 4. Cross-reference comments

In `src/installer/step-ops.ts` above `advancePipeline()`:

```typescript
// NOTE: Algorithm SQL mirrored in tests/advance-pipeline-idempotent.test.ts advancePipeline() -- keep in sync.
```

In `tests/advance-pipeline-idempotent.test.ts` at line ~83, update existing comment:

```typescript
// Mirrors advancePipeline() in src/installer/step-ops.ts -- keep in sync.
```

Use function names, not line numbers — line numbers drift with every edit.

### 5. `src/installer/step-ops.ts` -- Log warning for missing run

Split the guard clause at line ~819:

```typescript
// Before:
if (!run || run.status === "failed" || run.status === "cancelled" || run.status === "completed") {
  return { advanced: false, runCompleted: false };
}

// After:
if (!run) {
  logger.warn("advancePipeline called with unknown runId", { runId });
  return { advanced: false, runCompleted: false };
}
if (run.status === "failed" || run.status === "cancelled" || run.status === "completed") {
  return { advanced: false, runCompleted: false };
}
```

Terminal states are expected (no log). Missing run is unexpected (warn).

## Acceptance Criteria

- [x] Composite index added; existing DBs get it on next startup
- [x] All 3 catch clauses capture and log error details
- [x] No unused variables in test file (all prefixed with `_`)
- [x] Cross-reference comments link production and test code
- [x] Missing-run case logs a warning; terminal states do not
- [x] All 28 tests pass (7 new + 21 existing)
- [x] Build passes clean

## References

- Review todos: `todos/001-005` in workspace
- Parent fix: commit `dda2ed2` -- `fix: rewrite advancePipeline() to be idempotent and order-aware`
- Solution doc: `docs/solutions/logic-errors/2026-02-15-pipeline-race-condition-predecessor-verification.md`

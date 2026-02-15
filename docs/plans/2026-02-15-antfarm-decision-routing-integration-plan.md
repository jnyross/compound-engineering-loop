---
title: "feat: Add Decision Routing to Antfarm Integration"
type: feature
date: 2026-02-15
---

# Add Decision Routing to Antfarm Integration

## Problem Statement

The `workflow.yml` declares four routing features that antfarm's runtime does not implement. Without them, the review step always advances linearly to compound — there is no review loop, which is the entire point of the compound engineering concept.

### Source code verification (antfarm v0.5.1)

All findings below are verified against the actual TypeScript source in `snarktank/antfarm`:

| Feature declared in workflow.yml | Antfarm source (`step-ops.ts`) | Status |
|----------------------------------|--------------------------------|--------|
| `decision_key: DECISION` | Not in `WorkflowStep` type, not checked by `advancePipeline()` or `completeStep()` | **Not implemented** |
| `on_decision: { approved: ..., needs_fixes: ..., rejected: ... }` | Not in type system or runtime | **Not implemented** |
| `retry_step: work` (in `on_decision`) | `failStep()` only retries the SAME step (`SET status = 'pending'`). Does not read `retry_step` or route to a different step. | **Not implemented** |
| `pass_outputs: [issues]` | Not a distinct feature. However, `completeStep()` merges ALL `KEY: value` outputs into global run context, so all outputs are available to all subsequent steps via `{{key}}` template resolution. | **Unnecessary** (global context merge) |
| `required_outputs: [brainstorm_output]` | `completeStep()` does no validation — just parses and merges | **Not implemented** |
| `on_fail: retry_step: implement` (feature-dev workflow) | Also not implemented in `failStep()`. The feature-dev workflow DECLARES this but the runtime ignores it. | **Declared but dead** |
| `on_fail: escalate_to: human` | `failStep()` just sets status to `failed`. No notification mechanism. | **Not implemented** |

### How antfarm actually works

**`advancePipeline(runId)`** — Finds the first step with `status = 'waiting'` ordered by `step_index ASC`, sets it to `pending`. If no waiting steps and no incomplete steps, completes the run. Purely linear.

**`completeStep(stepId, output)`** — Parses `KEY: value` lines from output, merges ALL into global run context (`context[key] = value`), marks step `done`, calls `advancePipeline()`.

**`failStep(stepId, error)`** — Increments `retry_count`. If `retry_count > max_retries`, sets step to `failed` (which stops the pipeline). Otherwise sets step back to `pending` (retries the SAME step).

**`resolveTemplate(template, context)`** — Replaces `{{key}}` with `context[key]`. Missing keys become the literal string `[missing: key]`.

**`workspace.files`** — Individual file copies only. `writeWorkflowFile()` copies one source file to one destination path. No directory tree support.

### Secondary integration gaps

5. **No shared filesystem between agents.** Each agent runs in an isolated OpenClaw session. `workspace.files` only copies `AGENTS.md` — and only supports individual file mappings, not directories. The shared directories (`docs/brainstorms/`, `docs/plans/`, `docs/solutions/`, `todos/`) are inaccessible to agents.

6. **No `repo` / `branch` context.** The work agent needs repo context. The workflow's initial context only sets `task`. `runWorkflow()` combines `taskTitle` with workflow-level `context` variables, so adding `repo` and `branch` to the workflow spec is sufficient.

7. **Agent prompts reference unavailable Claude Code features.** `TodoWrite`, `AskUserQuestion`, `/workflows:plan` slash commands, `skill:` loading, `compound-engineering.local.md`, and `Task` subagent spawning don't exist in OpenClaw.

8. **No `polling` config.** Antfarm defaults to `model: "default"` and `timeoutSeconds: 120`. The 120s timeout is far too short — the work agent needs 1800s. Antfarm's cron uses the polling timeout for step processing.

9. **Agent prompts output `STATUS: retry` which becomes `[missing: STATUS]`.** Actually, the review agent outputs `STATUS: done` for all outcomes (this was fixed in the 15-issue plan). But the feature-dev workflow's pattern of using `STATUS: retry` to trigger failure routing won't work either, since `failStep()` ignores `retry_step`.

10. **Template variables show `[missing: key]` on first run.** The work step input includes `{{issues}}` but on the first run (not a retry), this resolves to `[missing: issues]`, which the agent sees as literal text. The brainstorm step has the same issue.

## Proposed Solution

Two tracks with different timelines:

- **Track A (this repo):** Make workflow.yml run correctly on current antfarm by removing unsupported features and adapting agent prompts. Ships immediately.
- **Track B (antfarm repo):** Implement `retry_step` in `failStep()` and `decision_key`/`on_decision` in `advancePipeline()`. Enables the review loop. Requires PR to snarktank/antfarm.

## Technical Approach

### Track A: Make It Run (this repo, no antfarm changes)

#### A.1: Remove unsupported YAML fields from workflow.yml

Strip all fields that antfarm ignores. Keeping them is worse than removing them — they create the illusion of routing that doesn't exist.

**Remove from review step (lines 214-227):**
```yaml
# REMOVE — antfarm does not implement these
decision_key: DECISION
on_decision:
  approved:
    next_step: compound
  needs_fixes:
    retry_step: work
    pass_outputs: [issues]
  rejected:
    retry_step: brainstorm
    pass_outputs: [issues]
max_retries: 3
on_exhausted:
  escalate_to: human
```

**Remove from all steps:**
```yaml
# REMOVE — antfarm does not validate these
required_outputs: [brainstorm_output]
```

**Keep (these work):**
```yaml
expects: "STATUS: done"    # Used by polling to detect completion
max_retries: 2             # Used by failStep() for same-step retry
on_fail:
  escalate_to: human       # Not implemented, but documents intent
```

**Replace with comments documenting the intended routing:**
```yaml
# ROUTING INTENT (requires antfarm decision routing — Track B):
# approved → compound | needs_fixes → work | rejected → brainstorm
# Until Track B ships, pipeline is linear: review always advances to compound.
```

**Files:**
- [ ] `workflow.yml` — Remove `decision_key`, `on_decision`, `required_outputs` from all steps. Add routing intent comments.

**Acceptance criteria:**
- [ ] No fields in workflow.yml that antfarm ignores
- [ ] Routing intent is documented in comments
- [ ] Workflow loads and validates without errors

---

#### A.2: Add polling configuration

Without explicit polling config, all steps get 120s timeout — too short for every agent.

```yaml
# Add to workflow.yml top level
polling:
  model: default
  timeoutSeconds: 1800
```

The 1800s timeout matches the longest agent (work). Shorter agents (compound: 600s) will still complete within this window — the timeout is a maximum, not a duration.

**Files:**
- [ ] `workflow.yml` — Add `polling` block

**Acceptance criteria:**
- [ ] Polling timeout is 1800s (matches work agent)
- [ ] No agents timeout prematurely during normal execution

---

#### A.3: Add repo and branch to workflow context

`runWorkflow()` merges the workflow's `context` field into the initial run context. Adding `repo` and `branch` here makes them available to all steps via template resolution.

```yaml
# Add to workflow.yml top level
context:
  repo: "{{repo}}"
  branch: "{{branch}}"
```

These are provided by the caller when starting a run (e.g., `antfarm workflow run compound-engineering-loop "task" --context repo=myrepo,branch=main`). If not provided, they resolve to `[missing: repo]` and `[missing: branch]`.

Update the work step input to use them:

```yaml
- id: work
  input: |
    ...
    REPOSITORY: {{repo}}
    BRANCH: {{branch}}
    ...
```

**Files:**
- [ ] `workflow.yml` — Add `context` block, update work step input

**Acceptance criteria:**
- [ ] Work agent receives repo and branch information when provided
- [ ] Missing repo/branch shows `[missing: ...]` rather than crashing

---

#### A.4: Fix template variables for first-run case

On the first run (not a retry), `{{issues}}` resolves to `[missing: issues]`. The brainstorm step's `{{issues}}` and work step's `{{issues}}` inputs need to handle this.

**Option 1: Document the `[missing: key]` behavior in agent prompts**

Add to brainstorm and work AGENTS.md:
```
Note: If PREVIOUS ISSUES shows "[missing: issues]", this is the first run (not a retry). Ignore and proceed normally.
```

**Option 2: Initialize all template variables to empty in context**

```yaml
context:
  task: "{{task}}"
  issues: ""
  brainstorm_output: ""
  plan_file: ""
  plan_content: ""
  plan_summary: ""
  implementation_summary: ""
  files_changed: ""
  review_notes: ""
```

Option 2 is better — agents don't need to parse antfarm internals.

**Files:**
- [ ] `workflow.yml` — Initialize all pipeline variables to empty string in `context`

**Acceptance criteria:**
- [ ] First-run steps don't see `[missing: key]` literal strings
- [ ] Template variables resolve to empty string when not yet populated
- [ ] Populated variables override the empty defaults

---

#### A.5: Expand workspace.files for cross-agent file access

Agents need shared files for data flow. Since `workspace.files` only supports individual file mappings, there are two approaches:

**Approach 1: Rely on git (recommended)**

Each agent operates on the SAME git repo checkout. Brainstorm commits `docs/brainstorms/` to git, plan reads from git, etc. This is how the feature-dev workflow works — the setup agent creates a branch, the developer agent commits to it, the reviewer reads from it.

This requires NO changes to `workspace.files` — the git repo IS the shared filesystem. The only requirement is that all agents have access to the same repo checkout, which OpenClaw provides since they run in sessions attached to the same project.

**Approach 2: List individual shared files explicitly**

```yaml
workspace:
  files:
    AGENTS.md: agents/brainstorm/AGENTS.md
    docs/brainstorms/.gitkeep: docs/brainstorms/.gitkeep
    docs/plans/.gitkeep: docs/plans/.gitkeep
```

This is fragile — new files created by agents won't be provisioned since they don't exist at workflow definition time.

**Recommendation:** Approach 1 (git-based sharing). Add a note to each AGENTS.md that the agent should read shared files from the git working tree, not expect them in the workspace.

**Files:**
- [ ] `agents/*/AGENTS.md` — Add note about reading shared files from git

**Acceptance criteria:**
- [ ] Plan agent can read brainstorm output from `docs/brainstorms/`
- [ ] Work agent can read plan from `docs/plans/`
- [ ] Compound agent can write to `docs/solutions/`

---

#### A.6: Adapt AGENTS.md for OpenClaw compatibility

Each AGENTS.md references Claude Code features unavailable in OpenClaw. These need adaptation.

**Feature mapping:**

| Claude Code Feature | OpenClaw Reality | Adaptation |
|---------------------|------------------|------------|
| `TodoWrite` tool | Not available | Remove. Use agent's internal tracking. |
| `AskUserQuestion` tool | Not available (async) | Remove. Always operate autonomously (ANTFARM_MODE is always autonomous). |
| `skill: X` loading | Not available | Inline the critical behavioral instructions. Skills are only relevant for Claude Code interactive use. |
| `Task subagent_type` spawning | Not available | Replace with sequential analysis steps. Subagent parallelism is a Claude Code optimization. |
| `/workflows:plan` commands | Not available | Remove references. The agent IS the workflow step. |
| `compound-engineering.local.md` | Not available | Remove. Use defaults. |
| `git-worktree` skill | Not available | Replace with direct git commands if needed. |
| `agent-browser` | Not available | Remove. Screenshots not available in OpenClaw. |

**Per-agent changes:**

**brainstorm/AGENTS.md:**
- Remove `skill: brainstorming` reference → inline the brainstorming techniques
- Remove `AskUserQuestion` → always produce output directly
- Remove `repo-research-analyst` subagent → describe research steps inline
- Keep output format (`BRAINSTORM_OUTPUT`, `STATUS: done`)

**plan/AGENTS.md:**
- Remove `skill:` references → inline planning methodology
- Remove `repo-research-analyst`, `learnings-researcher`, `spec-flow-analyzer` subagent spawning → describe as sequential steps
- Remove `best-practices-researcher`, `framework-docs-researcher` → describe as research steps
- Keep output format (`PLAN_FILE`, `PLAN_CONTENT`, `PLAN_SUMMARY`, `STATUS: done`)

**work/AGENTS.md:**
- Remove `skill: git-worktree`, `agent-browser`, `rclone` → direct git commands
- Remove `TodoWrite` → use structured text output
- Remove screenshot capture → not available
- Keep output format (`IMPLEMENTATION_SUMMARY`, `FILES_CHANGED`, `PR_URL`, `STATUS: done`)

**review/AGENTS.md:**
- Remove ALL subagent spawning (9 review agents) → describe review criteria inline
- Remove `file-todos` skill → write todo files directly
- Remove `code-simplicity-reviewer` subagent → describe simplification criteria
- Keep 3-state output format (approved/needs_fixes/rejected) for future Track B compatibility
- Keep output format (`DECISION`, `ISSUES`, `REVIEW_NOTES`, `STATUS: done`)

**compound/AGENTS.md:**
- Remove 5 parallel subagents → describe as sequential analysis steps
- Remove `compound-docs` skill → inline the documentation schema
- Keep output format (`LEARNINGS`, `FILE_CREATED`, `STATUS: done`)

**Files:**
- [ ] `agents/brainstorm/AGENTS.md` — Adapt for OpenClaw
- [ ] `agents/plan/AGENTS.md` — Adapt for OpenClaw
- [ ] `agents/work/AGENTS.md` — Adapt for OpenClaw
- [ ] `agents/review/AGENTS.md` — Adapt for OpenClaw
- [ ] `agents/compound/AGENTS.md` — Adapt for OpenClaw

**Acceptance criteria:**
- [ ] No AGENTS.md references Claude Code-only features (TodoWrite, AskUserQuestion, skill:, Task subagent_type)
- [ ] Each AGENTS.md is self-contained with inline behavioral instructions
- [ ] Output format preserved for context merging compatibility
- [ ] Review agent still outputs 3-state DECISION for Track B compatibility

---

### Track B: Add Decision Routing to Antfarm (antfarm repo)

Two incremental changes to the antfarm runtime, each independently useful.

#### B.1: Implement `retry_step` in `failStep()` — 2-way routing

The `WorkflowStepFailure` type already declares `retry_step`. The feature-dev workflow already uses `on_fail: retry_step: implement`. But `failStep()` ignores this field and only retries the same step.

**Change:** When a step fails and `retry_step` is configured, reset the TARGET step to `pending` (and all steps between target and current to `waiting`) instead of retrying the current step.

**Implementation in `step-ops.ts`:**

```typescript
export function failStep(stepId: string, error: string):
  { retrying: boolean; runFailed: boolean } {
  const db = getDb();
  const step = db.prepare(
    "SELECT run_id, step_id, retry_count, max_retries, type, current_story_id FROM steps WHERE id = ?"
  ).get(stepId);

  if (!step) throw new Error(`Step not found: ${stepId}`);

  // Check max retries
  const newRetryCount = step.retry_count + 1;
  if (newRetryCount > step.max_retries) {
    // Mark step failed, fail run
    db.prepare(
      "UPDATE steps SET status = 'failed', output = ?, retry_count = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(error, newRetryCount, stepId);
    db.prepare(
      "UPDATE runs SET status = 'failed', updated_at = datetime('now') WHERE id = ?"
    ).run(step.run_id);
    return { retrying: false, runFailed: true };
  }

  // NEW: Check for retry_step routing
  const stepDef = getStepDefinition(step.run_id, step.step_id);
  if (stepDef?.on_fail?.retry_step) {
    const targetStepId = stepDef.on_fail.retry_step;

    // Reset target step to pending
    db.prepare(
      "UPDATE steps SET status = 'pending', updated_at = datetime('now') WHERE run_id = ? AND step_id = ?"
    ).run(step.run_id, targetStepId);

    // Reset all steps between target and current to waiting
    db.prepare(
      "UPDATE steps SET status = 'waiting', updated_at = datetime('now') WHERE run_id = ? AND step_index > (SELECT step_index FROM steps WHERE run_id = ? AND step_id = ?) AND step_index < (SELECT step_index FROM steps WHERE run_id = ? AND step_id = ?)"
    ).run(step.run_id, step.run_id, targetStepId, step.run_id, step.step_id);

    // Mark current step as done (it completed, just decided to retry earlier step)
    db.prepare(
      "UPDATE steps SET status = 'done', output = ?, retry_count = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(error, newRetryCount, stepId);

    return { retrying: true, runFailed: false };
  }

  // Existing behavior: retry same step
  db.prepare(
    "UPDATE steps SET status = 'pending', retry_count = ?, updated_at = datetime('now') WHERE id = ?"
  ).run(newRetryCount, stepId);
  return { retrying: true, runFailed: false };
}
```

**What this unlocks for compound-engineering-loop:**

Use the feature-dev pattern — review agent outputs `STATUS: retry` when issues found. This doesn't match `expects: "STATUS: done"`, so the step "fails". `failStep()` checks `on_fail: retry_step: work` and routes to the work step.

```yaml
# workflow.yml review step with B.1
- id: review
  agent: review
  expects: "STATUS: done"
  max_retries: 3
  on_fail:
    retry_step: work
```

**Limitation:** Only supports 2-way routing (approved vs. not-approved). Cannot distinguish between "needs minor fixes" and "fundamentally rejected".

**Files to modify in antfarm:**
- [ ] `src/installer/step-ops.ts` — Implement `retry_step` routing in `failStep()`
- [ ] `src/installer/step-ops.ts` — Add `getStepDefinition()` helper to look up workflow spec for a step
- [ ] `tests/step-ops.test.ts` — Add tests for retry_step routing

**Acceptance criteria:**
- [ ] `on_fail: retry_step: work` routes failed review to work step
- [ ] Steps between target and current are reset to `waiting`
- [ ] `retry_count` still increments and respects `max_retries`
- [ ] Existing workflows without `retry_step` continue to work (same-step retry)
- [ ] Feature-dev workflow's `on_fail: retry_step: implement` starts working

---

#### B.2: Implement `decision_key` / `on_decision` in `completeStep()` — 3-way routing

Full decision-based routing. When a step succeeds, read a specific output key and route based on its value.

**Implementation in `step-ops.ts`:**

Add decision routing to `completeStep()` AFTER output parsing but BEFORE calling `advancePipeline()`:

```typescript
// In completeStep(), after parsing and merging outputs:

const stepDef = getStepDefinition(step.run_id, step.step_id);
if (stepDef?.decision_key) {
  const decision = parsed[stepDef.decision_key.toLowerCase()];
  const route = stepDef.on_decision?.[decision];

  if (!route) {
    // Unknown decision — fail the step
    failStep(stepId, `Unknown decision value: '${decision}' for key '${stepDef.decision_key}'`);
    return { advanced: false, runCompleted: false };
  }

  if (route.next_step) {
    // Forward routing: skip to a specific step
    // Mark current step done
    db.prepare(
      "UPDATE steps SET status = 'done', output = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(output, stepId);

    // Skip intermediate steps
    db.prepare(
      "UPDATE steps SET status = 'skipped', updated_at = datetime('now') WHERE run_id = ? AND step_index > ? AND step_id != ? AND status = 'waiting'"
    ).run(step.run_id, step.step_index, route.next_step);

    // Set target step to pending
    db.prepare(
      "UPDATE steps SET status = 'pending', updated_at = datetime('now') WHERE run_id = ? AND step_id = ?"
    ).run(step.run_id, route.next_step);

    return { advanced: true, runCompleted: false };
  }

  if (route.retry_step) {
    // Backward routing: go back to a previous step
    const retryCount = (run.metadata?.decision_retry_count ?? 0) + 1;
    const maxRetries = stepDef.max_retries ?? 3;

    if (retryCount > maxRetries) {
      // Exhausted — fail the run
      db.prepare(
        "UPDATE steps SET status = 'failed', output = ?, updated_at = datetime('now') WHERE id = ?"
      ).run(`Decision retries exhausted (${maxRetries})`, stepId);
      db.prepare(
        "UPDATE runs SET status = 'failed', updated_at = datetime('now') WHERE id = ?"
      ).run(step.run_id);
      return { advanced: false, runCompleted: false };
    }

    // Update retry counter in run metadata
    const metadata = JSON.parse(run.metadata ?? '{}');
    metadata.decision_retry_count = retryCount;

    // Mark current step done
    db.prepare(
      "UPDATE steps SET status = 'done', output = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(output, stepId);

    // Reset target step and all subsequent steps to waiting
    db.prepare(
      "UPDATE steps SET status = 'waiting', updated_at = datetime('now') WHERE run_id = ? AND step_index >= (SELECT step_index FROM steps WHERE run_id = ? AND step_id = ?) AND status IN ('done', 'skipped')"
    ).run(step.run_id, step.run_id, route.retry_step);

    // Set target step to pending
    db.prepare(
      "UPDATE steps SET status = 'pending', updated_at = datetime('now') WHERE run_id = ? AND step_id = ?"
    ).run(step.run_id, route.retry_step);

    // Save metadata
    db.prepare(
      "UPDATE runs SET context = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(JSON.stringify({ ...context, __metadata: metadata }), step.run_id);

    return { advanced: true, runCompleted: false };
  }
}

// Existing linear behavior
```

**Type changes in `types.ts`:**

```typescript
interface WorkflowStep {
  // ... existing fields ...
  decision_key?: string;
  on_decision?: Record<string, {
    next_step?: string;
    retry_step?: string;
  }>;
}
```

Note: `pass_outputs` is unnecessary since `completeStep()` already merges ALL outputs into global context. All outputs from the review step (including `ISSUES`) are automatically available to subsequent steps.

**Schema validation in `workflow-spec.ts`:**

```typescript
// In validateSteps(), add:
if (step.decision_key) {
  if (!step.on_decision) {
    throw new Error(`Step '${step.id}' has decision_key but no on_decision`);
  }
  for (const [decision, route] of Object.entries(step.on_decision)) {
    if (route.next_step && !stepIds.includes(route.next_step)) {
      throw new Error(`Step '${step.id}' on_decision.${decision}.next_step '${route.next_step}' not found`);
    }
    if (route.retry_step && !stepIds.includes(route.retry_step)) {
      throw new Error(`Step '${step.id}' on_decision.${decision}.retry_step '${route.retry_step}' not found`);
    }
  }
}
```

**What this unlocks for compound-engineering-loop:**

Full 3-way routing. The review step stays in workflow.yml as originally designed:

```yaml
- id: review
  agent: review
  expects: "STATUS: done"
  decision_key: DECISION
  on_decision:
    approved:
      next_step: compound
    needs_fixes:
      retry_step: work
    rejected:
      retry_step: brainstorm
  max_retries: 3
```

Review agent always outputs `STATUS: done` (matching `expects`), and `completeStep()` reads the `DECISION` output to determine routing.

**Files to modify in antfarm:**
- [ ] `src/installer/types.ts` — Add `decision_key` and `on_decision` to `WorkflowStep`
- [ ] `src/installer/workflow-spec.ts` — Add validation for decision routing fields
- [ ] `src/installer/step-ops.ts` — Add decision routing to `completeStep()`
- [ ] `src/db.ts` — Add `metadata` column to `runs` table (or store in context)
- [ ] Tests for all decision routing paths

**Acceptance criteria:**
- [ ] `DECISION: approved` routes review → compound (forward, linear)
- [ ] `DECISION: needs_fixes` routes review → work (backward, with issues in context)
- [ ] `DECISION: rejected` routes review → brainstorm (backward, with issues in context)
- [ ] Retry counter increments on each backward route, shared across all decision paths
- [ ] After 3 retries, run transitions to `failed` status
- [ ] Unknown DECISION values fail the step
- [ ] Linear pipelines (no `decision_key`) continue to work unchanged
- [ ] Feature-dev and other existing workflows are unaffected

---

### Track B.3: Add `required_outputs` validation in `completeStep()` (nice-to-have)

Small addition to `completeStep()` — validate that required output keys are present before merging.

```typescript
// In completeStep(), after parsing output:
if (stepDef?.required_outputs) {
  const missing = stepDef.required_outputs.filter(
    key => !(key.toLowerCase() in parsed)
  );
  if (missing.length > 0) {
    return failStep(stepId, `Missing required outputs: ${missing.join(', ')}`);
  }
}
```

**Files to modify in antfarm:**
- [ ] `src/installer/types.ts` — Add `required_outputs?: string[]` to `WorkflowStep`
- [ ] `src/installer/step-ops.ts` — Add validation in `completeStep()`

---

## Implementation Order

```
IMMEDIATE (this repo, no antfarm changes):
  A.1 → A.2 → A.3 → A.4 → A.5 → A.6
  Result: Linear pipeline runs on current antfarm

PHASE 2 (antfarm PR — small, high-value):
  B.1: Implement retry_step in failStep()
  Result: 2-way routing (review → work retry loop)
  Update workflow.yml: add on_fail: retry_step: work to review step

PHASE 3 (antfarm PR — full routing):
  B.2: Implement decision_key / on_decision
  Result: 3-way routing (approved → compound, needs_fixes → work, rejected → brainstorm)
  Update workflow.yml: restore full decision routing declarations

OPTIONAL:
  B.3: required_outputs validation
```

### Phase 1: Track A — Make It Run (this repo)

| # | Task | Files | Deps |
|---|------|-------|------|
| A.1 | Remove unsupported YAML fields | workflow.yml | None |
| A.2 | Add polling config (1800s) | workflow.yml | None |
| A.3 | Add repo/branch context | workflow.yml | None |
| A.4 | Initialize template variables | workflow.yml | None |
| A.5 | Document git-based file sharing | agents/*/AGENTS.md | None |
| A.6 | Adapt AGENTS.md for OpenClaw | agents/*/AGENTS.md | A.5 |

### Phase 2: Track B.1 — 2-Way Routing (antfarm PR)

| # | Task | Files | Deps |
|---|------|-------|------|
| B.1a | Implement retry_step in failStep() | step-ops.ts | None |
| B.1b | Add getStepDefinition() helper | step-ops.ts | None |
| B.1c | Update workflow.yml for 2-way | workflow.yml (this repo) | B.1a |
| B.1d | Tests | step-ops.test.ts | B.1a |

### Phase 3: Track B.2 — 3-Way Routing (antfarm PR)

| # | Task | Files | Deps |
|---|------|-------|------|
| B.2a | Add types to WorkflowStep | types.ts | None |
| B.2b | Add schema validation | workflow-spec.ts | B.2a |
| B.2c | Implement decision routing in completeStep() | step-ops.ts | B.2a |
| B.2d | Add retry counter to run metadata | step-ops.ts, db.ts | B.2c |
| B.2e | Restore full routing in workflow.yml | workflow.yml (this repo) | B.2c |
| B.2f | Tests | step-ops.test.ts | B.2c |

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OpenClaw agents can't run git commands | Medium | High | Verify before A.5/A.6. Feature-dev workflow uses git, so likely supported. |
| Linear fallback produces unusable review output | Low | Medium | Review agent still outputs structured findings — just no automated re-work loop |
| B.1 retry_step breaks existing antfarm workflows | Low | High | All existing workflows don't use retry_step (it was already declared but dead). Implementing it is additive. |
| B.2 decision routing interacts badly with loop steps | Medium | Medium | Decision routing should only be allowed on non-loop steps. Add validation. |
| Global context merge causes key collisions | Low | Medium | Use prefixed keys (e.g., `review_issues` not just `issues`) |
| `[missing: key]` appears in agent prompts despite A.4 | Low | Low | A.4 initializes all variables to empty. Only custom variables would show `[missing: ...]`. |

## Versioning

After Track A changes:
- [ ] `workflow.yml` `version` field — Bump to `2`
- [ ] `CHANGELOG.md` — Document antfarm compatibility changes under new version
- [ ] `README.md` — Add antfarm integration section explaining current capabilities and limitations

## Open Questions

1. **Can OpenClaw agents run git commands?** The feature-dev workflow's developer agent creates branches, commits, and pushes. If this works, git-based file sharing (A.5) is valid.

2. **Does the antfarm team accept external PRs?** Track B requires changes to `snarktank/antfarm`. Check contribution guidelines.

3. **Should AGENTS.md files diverge from plugin commands?** Currently AGENTS.md files are "synchronized from" plugin commands. For OpenClaw compatibility, they need to diverge. Consider maintaining two versions (AGENTS.md for antfarm, commands/*.md for Claude Code) or making AGENTS.md the authoritative source.

4. **Should `retry_step` (B.1) or `decision_key` (B.2) be prioritized?** B.1 is simpler and gives 2-way routing. B.2 is the full solution. If the antfarm team is receptive, go straight to B.2. If uncertain, ship B.1 first as a smaller, more acceptable change.

5. **Does antfarm support per-step polling timeouts?** If yes, each agent could have an appropriate timeout instead of using the max (1800s) for all agents. Check `WorkflowStep` for a `timeoutSeconds` override.

## References

### Antfarm Source (verified v0.5.1)
- `src/installer/step-ops.ts` — `advancePipeline()`, `completeStep()`, `failStep()`, `resolveTemplate()`
- `src/installer/types.ts` — `WorkflowStep`, `WorkflowStepFailure`, `WorkflowSpec`
- `src/installer/workflow-spec.ts` — `loadWorkflowSpec()`, `validateSteps()`
- `src/installer/run.ts` — `runWorkflow()`
- `src/installer/workspace-files.ts` — `writeWorkflowFile()`
- `src/installer/agent-cron.ts` — `buildPollingPrompt()`, polling model resolution

### Internal
- `docs/plans/2026-02-15-refactor-fix-all-15-documented-plugin-issues-plan.md` — Previous plan (plugin quality)
- `docs/solutions/integration-issues/opencode-antfarm-workflow-compound-engineering-plugin-phases.md` — Integration notes

### Feature-Dev Workflow (reference implementation)
- `workflows/feature-dev/workflow.yml` — Uses `on_fail: retry_step: implement` (declared but not implemented in runtime)

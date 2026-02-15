---
title: "feat: Add Decision Routing to Antfarm Integration"
type: feature
date: 2026-02-15
deepened: 2026-02-15
---

# Add Decision Routing to Antfarm Integration

## Enhancement Summary

**Deepened on:** 2026-02-15
**Sections enhanced:** 6
**Research agents used:** 15 (architecture-strategist, security-sentinel, performance-oracle, agent-native-reviewer, code-simplicity-reviewer, kieran-typescript-reviewer, spec-flow-analyzer, pattern-recognition-specialist, learnings-researcher ×3, orchestrating-swarms skill, agent-native-architecture skill, document-review skill, best-practices-researcher ×2)

### Key Improvements

1. **CRITICAL BUG FOUND:** B.1's approach of marking review step as `done` after backward routing breaks the retry loop — `advancePipeline()` will never re-pick a `done` step. Plan revised to skip B.1 entirely and go straight to B.2 with corrected status handling.
2. **Simplified B.2:** Use existing `retry_count` column instead of inventing `decision_retry_count` in run metadata. Drop `skipped` status (leave as `waiting`). Drop B.3 entirely (YAGNI).
3. **Security hardening:** Added output key allowlisting, single-pass template verification, and unified retry tracking to prevent context poisoning and retry budget circumvention.
4. **Performance fix:** Remove `PLAN_CONTENT` from global context (saves ~30-40KB), use `PLAN_FILE` path instead.
5. **Missing transactions:** All multi-statement backward routing must be wrapped in SQLite transactions (BEGIN IMMEDIATE).
6. **Flow gaps filled:** Work agent needs retry-specific instructions, brainstorm needs rejection context, compound needs review context.
7. **Data contracts:** Added explicit input/output contracts per step defining which keys are produced and consumed.

### New Considerations Discovered

- `retry_step` is dead across ALL 3 antfarm workflows (not just feature-dev) — antfarm issue #109 documents this gap
- `StepResult` type already has `"retry"` status, confirming routing was always intended but never implemented
- Antfarm's webhook system could be used for `escalate_to: human` notifications
- Case sensitivity mismatch: `decision_key: DECISION` but `completeStep()` lowercases parsed keys — must use `.toLowerCase()` lookup
- `getStepDefinition()` helper doesn't exist yet — must be created before B.2 can reference it
- `run.metadata` access pattern in original plan was wrong — runs table stores context as JSON, not a separate metadata column
- Self-loop guard needed: a step routing to itself via `retry_step` would cause an infinite loop

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

### Research Insights: Antfarm Runtime

**Key findings from deep source analysis (best-practices-researcher):**
- `retry_step` is declared but dead across ALL 3 antfarm bundled workflows (feature-dev, code-review, bug-fix) — not just feature-dev as initially thought
- Antfarm issue #109 explicitly documents the escalation/routing gap
- `StepResult` type in `types.ts` already includes `"retry"` as a valid status, confirming routing was designed but never implemented in `step-ops.ts`
- Antfarm's webhook system (`src/installer/webhooks.ts`) is functional and could power `escalate_to: human` notifications
- The `medic` system handles infrastructure failures (agent crashes, timeouts) but NOT logical failures (wrong output, bad decisions)

**SQLite best practices (best-practices-researcher, performance-oracle):**
- Use WAL mode for concurrent read/write access: `PRAGMA journal_mode=WAL;`
- Use `BEGIN IMMEDIATE` for write transactions to prevent SQLITE_BUSY on concurrent cron ticks
- Wrap all multi-statement routing operations in transactions — partial state (e.g., target step set to `pending` but intermediate steps not reset) would corrupt the pipeline

**Industry patterns for workflow routing (best-practices-researcher):**
- Temporal, Step Functions, Airflow, and Argo all use per-step retry counters (not global)
- GitHub Actions uses `if:` conditions for branching — closest analog to `on_decision`
- All major orchestrators separate "did the step run" from "what did the step decide" — validates the STATUS/DECISION split

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

### Research Insights: Solution Architecture

**Plan structure (document-review skill):**
- Track A and Track B are separate deliverables targeting different repos — consider them as independent work streams, not sequential phases
- A.6 should be split into per-agent sub-tasks (brainstorm, plan, work, review, compound) since each has unique adaptation requirements

**Architecture assessment (architecture-strategist):**
- Linear-with-jumps routing works for 5 steps but has a scaling ceiling — acknowledge as intentional simplification, not a general-purpose workflow engine
- Routing logic should be extracted into its own function (`routeDecision()`) rather than embedded in `completeStep()`
- Stale context on backward routing: when re-running brainstorm→plan→work, the old `plan_content`, `implementation_summary`, etc. are still in global context and may confuse agents

**Agent-native perspective (agent-native-architecture skill):**
- Current architecture is orchestrator-native (antfarm drives the loop) — long-term, a single-agent loop pattern may be more robust
- For now, the multi-step orchestrator is pragmatic given antfarm's constraints

**Data contracts (orchestrating-swarms skill):**
- Define explicit input/output contracts per step (see Data Contracts section below)
- Establish file ownership boundaries: brainstorm writes to `docs/brainstorms/`, plan to `docs/plans/`, compound to `docs/solutions/`
- Add error handling tables per step documenting expected failure modes

## Data Contracts

Each step has explicit input keys (consumed via `{{key}}`) and output keys (produced as `KEY: value`):

| Step | Consumes | Produces | File Outputs |
|------|----------|----------|--------------|
| brainstorm | `task`, `review_issues` (empty on first run) | `BRAINSTORM_OUTPUT`, `STATUS` | `docs/brainstorms/*.md` |
| plan | `task`, `brainstorm_output` | `PLAN_FILE`, `PLAN_SUMMARY`, `STATUS` | `docs/plans/*.md` |
| work | `task`, `plan_file`, `plan_summary`, `repo`, `branch`, `review_issues` (empty on first run) | `IMPLEMENTATION_SUMMARY`, `FILES_CHANGED`, `PR_URL`, `STATUS` | source code changes |
| review | `task`, `plan_file`, `implementation_summary`, `files_changed`, `pr_url` | `DECISION`, `REVIEW_ISSUES`, `REVIEW_NOTES`, `STATUS` | `todos/*.md` |
| compound | `task`, `implementation_summary`, `review_issues`, `review_notes`, `decision` | `LEARNINGS`, `FILE_CREATED`, `STATUS` | `docs/solutions/*.md` |

**Key renames (pattern-recognition-specialist):**
- `issues` → `review_issues` (avoid generic key names in global context)
- `PLAN_CONTENT` removed from context (performance-oracle: saves ~30-40KB; use `PLAN_FILE` path instead)

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
- [x] `workflow.yml` — Remove `decision_key`, `on_decision`, `required_outputs` from all steps. Add routing intent comments.

**Acceptance criteria:**
- [x] No fields in workflow.yml that antfarm ignores
- [x] Routing intent is documented in comments
- [x] Workflow loads and validates without errors

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
- [x] `workflow.yml` — Add `polling` block

**Acceptance criteria:**
- [x] Polling timeout is 1800s (matches work agent)
- [x] No agents timeout prematurely during normal execution

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
- [x] `workflow.yml` — Add `context` block, update work step input

**Acceptance criteria:**
- [x] Work agent receives repo and branch information when provided
- [x] Missing repo/branch shows `[missing: ...]` rather than crashing

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

**Research Insights (performance-oracle, pattern-recognition-specialist):**
- Remove `PLAN_CONTENT` from the context initialization — storing full plan markdown in global context adds 30-40KB to every template resolution call. Use `PLAN_FILE` (path) instead and have agents read the file directly via git.
- Rename `issues` → `review_issues` to avoid generic key collision risk (security-sentinel: any agent can overwrite any context key).
- Add `decision` to initialization for compound agent compatibility.

**Revised context block:**
```yaml
context:
  task: "{{task}}"
  repo: "{{repo}}"
  branch: "{{branch}}"
  review_issues: ""
  brainstorm_output: ""
  plan_file: ""
  plan_summary: ""
  implementation_summary: ""
  files_changed: ""
  pr_url: ""
  review_notes: ""
  decision: ""
  learnings: ""
  file_created: ""
```

**Files:**
- [x] `workflow.yml` — Initialize all pipeline variables to empty string in `context`

**Acceptance criteria:**
- [x] First-run steps don't see `[missing: key]` literal strings
- [x] Template variables resolve to empty string when not yet populated
- [x] Populated variables override the empty defaults
- [x] `PLAN_CONTENT` is NOT in context (agents read plan file from git)

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
- [x] `agents/*/AGENTS.md` — Add note about reading shared files from git

**Acceptance criteria:**
- [x] Plan agent can read brainstorm output from `docs/brainstorms/`
- [x] Work agent can read plan from `docs/plans/`
- [x] Compound agent can write to `docs/solutions/`

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

**Research Insights (spec-flow-analyzer, agent-native-reviewer, pattern-recognition-specialist):**

**Critical flow gaps to address in A.6:**
- **Work agent needs retry-specific instructions:** When re-run after review rejection, the work agent receives `{{review_issues}}` but has no instructions for how to handle it. Add a section: "If REVIEW_ISSUES is not empty, this is a retry — focus on fixing the listed issues rather than re-implementing from scratch."
- **Brainstorm needs rejection context:** On rejection routing (Track B), brainstorm receives `{{review_issues}}` but doesn't know this means the previous approach was rejected. Add: "If REVIEW_ISSUES is not empty, the previous approach was rejected. Propose a fundamentally different approach."
- **Compound agent needs review context on Track A:** On the linear path, compound runs after review but doesn't receive `{{review_issues}}`, `{{review_notes}}`, or `{{decision}}` in its input template. Add these to compound's input.
- **No git artifact cleanup:** Work agent may leave WIP branches/commits that aren't cleaned up before retry. Add instructions for clean git state on retry.

**AGENTS.md divergence strategy (pattern-recognition-specialist):**
- AGENTS.md files currently have "Synchronized from .claude/commands/workflows/*.md — do not edit directly" header
- For OpenClaw compatibility, AGENTS.md MUST diverge from the plugin commands
- Make divergence explicit: change header to "OpenClaw version — see .claude/commands/workflows/*.md for Claude Code version"
- Maintain both versions independently going forward

**Agent output reliability (agent-native-reviewer):**
- DECISION output case sensitivity: review agent may output `approved`, `Approved`, or `APPROVED`. Normalize to lowercase in `completeStep()` before routing.
- Ensure all agents output `STATUS: done` consistently — any variation breaks `expects` matching.
- Add structured output format reminder at the end of each AGENTS.md.

**Per-agent changes:**

**brainstorm/AGENTS.md:**
- Remove `skill: brainstorming` reference → inline the brainstorming techniques
- Remove `AskUserQuestion` → always produce output directly
- Remove `repo-research-analyst` subagent → describe research steps inline
- **ADD:** Retry-aware instructions — "If REVIEW_ISSUES is not empty, previous approach was rejected. Propose fundamentally different approach."
- Keep output format (`BRAINSTORM_OUTPUT`, `STATUS: done`)

**plan/AGENTS.md:**
- Remove `skill:` references → inline planning methodology
- Remove `repo-research-analyst`, `learnings-researcher`, `spec-flow-analyzer` subagent spawning → describe as sequential steps
- Remove `best-practices-researcher`, `framework-docs-researcher` → describe as research steps
- **CHANGE:** Output `PLAN_FILE` and `PLAN_SUMMARY` only — remove `PLAN_CONTENT` from outputs (performance: saves ~30-40KB in global context)
- Keep output format (`PLAN_FILE`, `PLAN_SUMMARY`, `STATUS: done`)

**work/AGENTS.md:**
- Remove `skill: git-worktree`, `agent-browser`, `rclone` → direct git commands
- Remove `TodoWrite` → use structured text output
- Remove screenshot capture → not available
- **ADD:** Retry-specific instructions — "If REVIEW_ISSUES is not empty, this is a retry. Focus on fixing the listed issues. Run `git status` first to understand current state."
- **ADD:** Git cleanup instructions — "On retry, check for WIP branches or uncommitted changes before starting."
- Keep output format (`IMPLEMENTATION_SUMMARY`, `FILES_CHANGED`, `PR_URL`, `STATUS: done`)

**review/AGENTS.md:**
- Remove ALL subagent spawning (9 review agents) → describe review criteria inline
- Remove `file-todos` skill → write todo files directly
- Remove `code-simplicity-reviewer` subagent → describe simplification criteria
- Keep 3-state output format (approved/needs_fixes/rejected) for future Track B compatibility
- **ADD:** Output format reminder with case sensitivity note — "DECISION must be exactly one of: approved, needs_fixes, rejected (lowercase)"
- Keep output format (`DECISION`, `REVIEW_ISSUES`, `REVIEW_NOTES`, `STATUS: done`)

**compound/AGENTS.md:**
- Remove 5 parallel subagents → describe as sequential analysis steps
- Remove `compound-docs` skill → inline the documentation schema
- **ADD:** Review context inputs — `{{review_issues}}`, `{{review_notes}}`, `{{decision}}` in input template
- Keep output format (`LEARNINGS`, `FILE_CREATED`, `STATUS: done`)

**Files:**
- [x] `agents/brainstorm/AGENTS.md` — Adapt for OpenClaw
- [x] `agents/plan/AGENTS.md` — Adapt for OpenClaw
- [x] `agents/work/AGENTS.md` — Adapt for OpenClaw
- [x] `agents/review/AGENTS.md` — Adapt for OpenClaw
- [x] `agents/compound/AGENTS.md` — Adapt for OpenClaw

**Acceptance criteria:**
- [x] No AGENTS.md references Claude Code-only features (TodoWrite, AskUserQuestion, skill:, Task subagent_type)
- [x] Each AGENTS.md is self-contained with inline behavioral instructions
- [x] Output format preserved for context merging compatibility
- [x] Review agent still outputs 3-state DECISION for Track B compatibility

---

### Track B: Add Decision Routing to Antfarm (antfarm repo)

**REVISED based on research agent findings.** Original plan had B.1 (2-way via failStep) → B.2 (3-way via completeStep) → B.3 (required_outputs). Research agents identified critical bugs in B.1 and recommended skipping directly to B.2. B.3 dropped as YAGNI.

#### ~~B.1: SKIPPED — Do Not Implement retry_step via failStep()~~

**Why B.1 was removed (code-simplicity-reviewer, architecture-strategist):**

The original B.1 approach hijacked the failure path: review agent would output `STATUS: retry` → doesn't match `expects: "STATUS: done"` → step "fails" → `failStep()` reads `retry_step` and routes backward. This has three fatal problems:

1. **CRITICAL BUG:** B.1 marks the review step as `done` after routing backward. But `advancePipeline()` finds the next step by `SELECT ... WHERE status = 'waiting' ORDER BY step_index ASC`. When the pipeline re-reaches the review step, it's already `done` — the pipeline skips it and advances to compound, completely bypassing the retry loop.

2. **Semantic confusion:** Using "failure" to encode "the step succeeded but wants to route backward" conflates two orthogonal concepts. The STATUS/DECISION split (step succeeded vs. what to do next) is the correct separation.

3. **2-way limitation:** `failStep()` can only route to one target. We need 3-way: approved → compound, needs_fixes → work, rejected → brainstorm. Building B.1 as a stepping stone would require ripping it out for B.2 anyway.

**Skip directly to B.2 (decision routing in `completeStep()`).** This is the correct and complete solution.

---

#### B.2: Implement `decision_key` / `on_decision` in `completeStep()` — Full Decision Routing

**Research Insights (kieran-typescript-reviewer, security-sentinel, performance-oracle, architecture-strategist):**

Critical fixes incorporated vs. original B.2 plan:
- **Transaction safety:** All multi-statement routing wrapped in `db.transaction()` with `BEGIN IMMEDIATE` to prevent partial state on concurrent cron ticks
- **`getStepDefinition()` must be created:** This function doesn't exist — must be implemented to look up the workflow spec for a given step
- **Case sensitivity:** Normalize decision values to lowercase before routing lookup (agent may output `Approved`, `APPROVED`, or `approved`)
- **Use existing `retry_count`:** Don't invent `decision_retry_count` in run metadata. Use the existing `retry_count` column on the TARGET step being re-run. This aligns with industry patterns (Temporal, Step Functions, Airflow all use per-step retry counters)
- **Don't mark routed step as `done`:** On backward routing, mark the routing step (review) as `waiting` so it gets re-picked by `advancePipeline()` when the pipeline reaches it again
- **Self-loop guard:** Validate that `retry_step` doesn't point to the current step (use existing same-step retry via `failStep()` for that)
- **Drop `skipped` status:** Forward routing leaves intermediate steps as `waiting` — don't introduce a new status to the state machine
- **Context key poisoning mitigation:** Document that global context merge means any step can overwrite any key. Use prefixed keys (`review_issues` not `issues`) and validate in workflow spec that no step re-uses another step's output keys

**Prerequisites — new helper functions:**

```typescript
// getStepDefinition: Look up workflow spec for a step
// Must load the workflow spec and find the matching step definition
function getStepDefinition(runId: string, stepId: string): WorkflowStep | undefined {
  const db = getDb();
  const run = db.prepare(
    "SELECT workflow_id FROM runs WHERE id = ?"
  ).get(runId);
  if (!run) return undefined;

  const spec = loadWorkflowSpec(run.workflow_id);
  return spec.steps.find(s => s.id === stepId);
}

// routeDecision: Extracted routing logic (architecture-strategist recommendation)
// Keep completeStep() focused on output parsing + context merge
// routeDecision() handles all branching logic
function routeDecision(
  db: Database,
  runId: string,
  stepId: string,
  stepIndex: number,
  decision: string,
  stepDef: WorkflowStep
): { advanced: boolean; runCompleted: boolean } {
  // ... routing implementation below ...
}
```

**Implementation in `step-ops.ts` — `routeDecision()`:**

```typescript
function routeDecision(
  db: Database,
  runId: string,
  stepId: string,
  stepIndex: number,
  output: string,
  decision: string,
  stepDef: WorkflowStep
): { advanced: boolean; runCompleted: boolean } {
  const route = stepDef.on_decision?.[decision];

  if (!route) {
    // Unknown decision — fail the step
    failStep(stepId, `Unknown decision value: '${decision}' for key '${stepDef.decision_key}'`);
    return { advanced: false, runCompleted: false };
  }

  if (route.next_step) {
    // Forward routing: mark current step done, set target to pending
    // Leave intermediate steps as 'waiting' (not 'skipped' — no new status)
    const routeForward = db.transaction(() => {
      // Mark current step done
      db.prepare(
        "UPDATE steps SET status = 'done', output = ?, updated_at = datetime('now') WHERE id = ?"
      ).run(output, stepId);

      // Set target step to pending (advancePipeline is NOT called)
      db.prepare(
        "UPDATE steps SET status = 'pending', updated_at = datetime('now') WHERE run_id = ? AND step_id = ?"
      ).run(runId, route.next_step);
    });
    routeForward();
    return { advanced: true, runCompleted: false };
  }

  if (route.retry_step) {
    // Backward routing: reset target and intermediate steps
    // Check retry budget on the TARGET step (use existing retry_count column)
    const targetStep = db.prepare(
      "SELECT id, retry_count, max_retries FROM steps WHERE run_id = ? AND step_id = ?"
    ).get(runId, route.retry_step);

    if (!targetStep) {
      failStep(stepId, `retry_step target '${route.retry_step}' not found in run`);
      return { advanced: false, runCompleted: false };
    }

    const maxRetries = stepDef.max_retries ?? 3;
    if (targetStep.retry_count >= maxRetries) {
      // Exhausted — fail the run
      db.prepare(
        "UPDATE steps SET status = 'failed', output = ?, updated_at = datetime('now') WHERE id = ?"
      ).run(`Decision retries exhausted after ${maxRetries} attempts`, stepId);
      db.prepare(
        "UPDATE runs SET status = 'failed', updated_at = datetime('now') WHERE id = ?"
      ).run(runId);
      return { advanced: false, runCompleted: false };
    }

    const routeBackward = db.transaction(() => {
      // Mark current step (review) as 'waiting' — NOT 'done'
      // This ensures advancePipeline() will re-pick it when pipeline reaches it again
      db.prepare(
        "UPDATE steps SET status = 'waiting', output = ?, updated_at = datetime('now') WHERE id = ?"
      ).run(output, stepId);

      // Reset all steps between target and current to 'waiting'
      db.prepare(
        "UPDATE steps SET status = 'waiting', updated_at = datetime('now') WHERE run_id = ? AND step_index > (SELECT step_index FROM steps WHERE run_id = ? AND step_id = ?) AND step_index < ? AND status = 'done'"
      ).run(runId, runId, route.retry_step, stepIndex);

      // Set target step to 'pending' and increment its retry_count
      db.prepare(
        "UPDATE steps SET status = 'pending', retry_count = retry_count + 1, updated_at = datetime('now') WHERE run_id = ? AND step_id = ?"
      ).run(runId, route.retry_step);
    });
    routeBackward();
    return { advanced: true, runCompleted: false };
  }

  // Route has neither next_step nor retry_step — invalid
  failStep(stepId, `Route for decision '${decision}' has no next_step or retry_step`);
  return { advanced: false, runCompleted: false };
}
```

**Integration into `completeStep()`:**

```typescript
// In completeStep(), after parsing and merging outputs into context:
// (existing code: parse KEY: value lines, merge into context, save context)

const stepDef = getStepDefinition(step.run_id, step.step_id);
if (stepDef?.decision_key) {
  // Normalize to lowercase for case-insensitive lookup
  const decisionKey = stepDef.decision_key.toLowerCase();
  const decision = parsed[decisionKey]?.toLowerCase();

  if (!decision) {
    failStep(stepId, `Decision key '${stepDef.decision_key}' not found in step output`);
    return { advanced: false, runCompleted: false };
  }

  return routeDecision(db, step.run_id, stepId, step.step_index, output, decision, stepDef);
}

// Existing linear behavior: mark done, call advancePipeline()
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

Note: `pass_outputs` is unnecessary since `completeStep()` already merges ALL outputs into global context. All outputs from the review step (including `REVIEW_ISSUES`) are automatically available to subsequent steps.

**Schema validation in `workflow-spec.ts`:**

```typescript
// In validateSteps(), add:
if (step.decision_key) {
  if (!step.on_decision) {
    throw new Error(`Step '${step.id}' has decision_key but no on_decision`);
  }
  for (const [decision, route] of Object.entries(step.on_decision)) {
    if (route.next_step && !stepIds.includes(route.next_step)) {
      throw new Error(
        `Step '${step.id}' on_decision.${decision}.next_step '${route.next_step}' not found`
      );
    }
    if (route.retry_step) {
      if (!stepIds.includes(route.retry_step)) {
        throw new Error(
          `Step '${step.id}' on_decision.${decision}.retry_step '${route.retry_step}' not found`
        );
      }
      // Self-loop guard
      if (route.retry_step === step.id) {
        throw new Error(
          `Step '${step.id}' on_decision.${decision}.retry_step cannot target itself (use on_fail for same-step retry)`
        );
      }
      // Forward-loop guard: retry_step must be before current step
      const targetIndex = stepIds.indexOf(route.retry_step);
      const currentIndex = stepIds.indexOf(step.id);
      if (targetIndex >= currentIndex) {
        throw new Error(
          `Step '${step.id}' on_decision.${decision}.retry_step '${route.retry_step}' must be before current step`
        );
      }
    }
  }
}
```

**What this unlocks for compound-engineering-loop:**

Full 3-way routing. The review step in workflow.yml:

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

Review agent always outputs `STATUS: done` (matching `expects`), and `completeStep()` reads the `DECISION` output to determine routing. On backward routing, the review step is set to `waiting` (not `done`), so `advancePipeline()` will re-pick it when the pipeline loops back around.

**Stale context handling (architecture-strategist):**
When routing backward (e.g., rejected → brainstorm), the global context still contains stale values from the previous iteration (`plan_file`, `implementation_summary`, etc.). This is acceptable because:
1. Each re-run step will overwrite its own output keys
2. Agents are instructed to treat `{{review_issues}}` as the signal for retry behavior
3. The stale values provide useful context about what was tried before

**Files to modify in antfarm:**
- [ ] `src/installer/step-ops.ts` — Add `getStepDefinition()` helper
- [ ] `src/installer/step-ops.ts` — Add `routeDecision()` function
- [ ] `src/installer/step-ops.ts` — Integrate decision routing into `completeStep()`
- [ ] `src/installer/types.ts` — Add `decision_key` and `on_decision` to `WorkflowStep`
- [ ] `src/installer/workflow-spec.ts` — Add validation for decision routing fields (including self-loop and forward-loop guards)
- [ ] Tests for all decision routing paths

**Acceptance criteria:**
- [ ] `DECISION: approved` routes review → compound (forward)
- [ ] `DECISION: needs_fixes` routes review → work (backward, with review_issues in context)
- [ ] `DECISION: rejected` routes review → brainstorm (backward, with review_issues in context)
- [ ] Retry counter uses TARGET step's existing `retry_count` column (not a separate counter)
- [ ] After `max_retries` exhausted, run transitions to `failed` status
- [ ] Unknown DECISION values fail the step
- [ ] Missing DECISION key fails the step
- [ ] Case-insensitive decision matching (`Approved` = `approved` = `APPROVED`)
- [ ] Self-loop validation rejects `retry_step` pointing to same step
- [ ] Forward-loop validation rejects `retry_step` pointing to later step
- [ ] All multi-statement routing uses `db.transaction()` with `BEGIN IMMEDIATE`
- [ ] Review step set to `waiting` (not `done`) on backward routing
- [ ] Linear pipelines (no `decision_key`) continue to work unchanged
- [ ] Feature-dev and other existing workflows are unaffected

---

#### ~~B.3: DROPPED — required_outputs validation~~

**Why B.3 was removed (code-simplicity-reviewer):**

`required_outputs` validation is YAGNI. If an output is missing, the downstream step receives `[missing: key]` which is self-documenting. Adding validation at this layer:
1. Adds code to maintain with no proven need
2. Converts a recoverable situation (agent gets `[missing: key]` and can adapt) into a hard failure
3. Can be added later if needed without breaking changes

---

## Security Considerations

**Research Insights (security-sentinel):**

Three HIGH-severity findings to address in Track B implementation:

### S.1: Global Context Key Poisoning (HIGH)

**Risk:** `completeStep()` merges ALL `KEY: value` output into global context with no filtering. A buggy or malicious agent could overwrite critical context keys like `task`, `repo`, or `branch`.

**Mitigation (Track B):**
- Add optional `output_keys` field to `WorkflowStep` type — when present, only listed keys are merged into context
- In Track A, use prefixed key names (`review_issues` not `issues`) to reduce collision surface
- Add workflow-spec validation that no two steps produce the same output key

### S.2: Template Double-Expansion (MEDIUM)

**Risk:** If an agent outputs a value containing `{{key}}` (e.g., `REVIEW_NOTES: Check the {{branch}} variable`), `resolveTemplate()` could expand it when processing a downstream step's input template.

**Verification needed:** Confirm `resolveTemplate()` is single-pass only. If it runs recursively or is called multiple times on the same string, this is exploitable.

**Current assessment:** Based on source code reading, `resolveTemplate()` uses a single `String.replace()` call, which is single-pass. But verify in tests.

### S.3: Unified Retry Tracking (MEDIUM)

**Risk (original plan):** The original B.2 plan had two retry counters — step-level `retry_count` (for same-step retry via `failStep()`) and `decision_retry_count` (for cross-step routing in run metadata). An agent could force same-step retries to bypass the decision retry limit.

**Fix (incorporated):** Use the existing `retry_count` column on the TARGET step for all retry tracking. This creates a single, unified counter per step that tracks how many times it has been re-run regardless of the routing mechanism.

---

## Implementation Order

**REVISED:** B.1 skipped, B.3 dropped. Two phases instead of four.

```
PHASE 1 — IMMEDIATE (this repo, no antfarm changes):
  A.1 → A.2 → A.3 → A.4 → A.5 → A.6
  Result: Linear pipeline runs on current antfarm

PHASE 2 (antfarm PR — single PR with full routing):
  B.2: Implement decision_key / on_decision in completeStep()
  Prerequisites: getStepDefinition() helper, routeDecision() function
  Result: Full 3-way routing (approved → compound, needs_fixes → work, rejected → brainstorm)
  Then: Update workflow.yml in this repo to restore decision routing declarations
```

### Phase 1: Track A — Make It Run (this repo)

| # | Task | Files | Deps |
|---|------|-------|------|
| A.1 | Remove unsupported YAML fields | workflow.yml | None |
| A.2 | Add polling config (1800s) + cron.interval_ms: 60000 | workflow.yml | None |
| A.3 | Add repo/branch context | workflow.yml | None |
| A.4 | Initialize template variables (with key renames) | workflow.yml | None |
| A.5 | Document git-based file sharing | agents/*/AGENTS.md | None |
| A.6a | Adapt brainstorm/AGENTS.md for OpenClaw | agents/brainstorm/AGENTS.md | A.5 |
| A.6b | Adapt plan/AGENTS.md for OpenClaw | agents/plan/AGENTS.md | A.5 |
| A.6c | Adapt work/AGENTS.md for OpenClaw (+ retry instructions) | agents/work/AGENTS.md | A.5 |
| A.6d | Adapt review/AGENTS.md for OpenClaw (+ case sensitivity) | agents/review/AGENTS.md | A.5 |
| A.6e | Adapt compound/AGENTS.md for OpenClaw (+ review context) | agents/compound/AGENTS.md | A.5 |

### Phase 2: Track B.2 — Full Decision Routing (antfarm PR)

| # | Task | Files | Deps |
|---|------|-------|------|
| B.2a | Add types to WorkflowStep | types.ts | None |
| B.2b | Implement getStepDefinition() helper | step-ops.ts | None |
| B.2c | Add schema validation (with loop guards) | workflow-spec.ts | B.2a |
| B.2d | Implement routeDecision() function | step-ops.ts | B.2a, B.2b |
| B.2e | Integrate decision routing into completeStep() | step-ops.ts | B.2d |
| B.2f | Tests for all routing paths | step-ops.test.ts | B.2e |
| B.2g | Restore full routing in workflow.yml | workflow.yml (this repo) | B.2e |

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OpenClaw agents can't run git commands | Medium | High | Verify before A.5/A.6. Feature-dev workflow uses git, so likely supported. |
| Linear fallback produces unusable review output | Low | Medium | Review agent still outputs structured findings — just no automated re-work loop |
| B.2 decision routing breaks existing workflows | Low | High | Only triggers when `decision_key` is set. All existing workflows have no `decision_key`. |
| **Stale context confuses re-run agents** | **Medium** | **Medium** | **Agent instructions explicitly handle retry case (A.6). Stale keys are overwritten by re-run steps.** |
| **Global context key poisoning** | **Low** | **High** | **Use prefixed keys (A.4). Add `output_keys` allowlisting in future Track B enhancement.** |
| **SQLite transaction contention** | **Low** | **Medium** | **Use `BEGIN IMMEDIATE` in routeDecision(). Single cron thread minimizes contention.** |
| **Case sensitivity in DECISION output** | **Medium** | **Medium** | **Normalize to lowercase in completeStep(). Add case note to review AGENTS.md.** |
| `[missing: key]` appears in agent prompts despite A.4 | Low | Low | A.4 initializes all variables to empty. Only custom variables would show `[missing: ...]`. |

## Versioning

After Track A changes:
- [x] `workflow.yml` `version` field — Bump to `2`
- [x] `CHANGELOG.md` — Document antfarm compatibility changes under new version
- [x] `README.md` — Component counts verified (unchanged: 29 agents, 24 commands, 17 skills)

## Open Questions

### Resolved by Research

3. ~~**Should AGENTS.md files diverge from plugin commands?**~~ **RESOLVED (pattern-recognition-specialist):** Yes, divergence is necessary and intentional. Change AGENTS.md header to "OpenClaw version" and maintain both versions independently.

4. ~~**Should `retry_step` (B.1) or `decision_key` (B.2) be prioritized?**~~ **RESOLVED (code-simplicity-reviewer):** Skip B.1 entirely. Go straight to B.2. B.1 has a critical bug (marking review as `done` breaks re-entry) and is semantically wrong (using failure to encode routing decisions).

### Still Open

1. **Can OpenClaw agents run git commands?** The feature-dev workflow's developer agent creates branches, commits, and pushes. If this works, git-based file sharing (A.5) is valid.

2. **Does the antfarm team accept external PRs?** Track B requires changes to `snarktank/antfarm`. Check contribution guidelines. Note: antfarm issue #109 documents the escalation gap, suggesting awareness of the limitation.

5. **Does antfarm support per-step polling timeouts?** If yes, each agent could have an appropriate timeout instead of using the max (1800s) for all agents. Check `WorkflowStep` for a `timeoutSeconds` override.

6. **(NEW) Should backward routing clear stale context keys?** When review routes back to brainstorm, `plan_file`, `implementation_summary`, etc. still contain values from the rejected iteration. Agents are instructed to handle this, but an explicit `clear_context` option on routes could prevent confusion.

7. **(NEW) Should `escalate_to: human` use antfarm's webhook system?** The webhook system (`src/installer/webhooks.ts`) is functional and could power notifications. This would make `on_exhausted: escalate_to: human` actually work.

## References

### Antfarm Source (verified v0.5.1)
- `src/installer/step-ops.ts` — `advancePipeline()`, `completeStep()`, `failStep()`, `resolveTemplate()`
- `src/installer/types.ts` — `WorkflowStep`, `WorkflowStepFailure`, `WorkflowSpec`, `StepResult` (has `"retry"` status)
- `src/installer/workflow-spec.ts` — `loadWorkflowSpec()`, `validateSteps()`
- `src/installer/run.ts` — `runWorkflow()`
- `src/installer/workspace-files.ts` — `writeWorkflowFile()`
- `src/installer/agent-cron.ts` — `buildPollingPrompt()`, polling model resolution
- `src/installer/webhooks.ts` — Webhook notification system (functional)
- GitHub issue #109 — Documents escalation/routing gap

### Internal
- `docs/plans/2026-02-15-refactor-fix-all-15-documented-plugin-issues-plan.md` — Previous plan (plugin quality)
- `docs/solutions/integration-issues/opencode-antfarm-workflow-compound-engineering-plugin-phases.md` — Integration notes

### Feature-Dev Workflow (reference implementation)
- `workflows/feature-dev/workflow.yml` — Uses `on_fail: retry_step: implement` (declared but not implemented in runtime)

### Research Agents (deepening session, 2026-02-15)
- architecture-strategist: Critical bug in B.1 status handling, routing extraction recommendation
- security-sentinel: 3 HIGH findings (context poisoning, double-expansion, retry circumvention)
- performance-oracle: PLAN_CONTENT removal (-30-40KB), cron.interval_ms, SQLite transactions
- agent-native-reviewer: Case sensitivity, autonomous mode, retry instructions
- code-simplicity-reviewer: Skip B.1, use retry_count, drop skipped status, drop B.3
- kieran-typescript-reviewer: Missing transactions (BLOCKING), undefined getStepDefinition() (BLOCKING), metadata access pattern
- spec-flow-analyzer: 8 flow gaps including work agent retry instructions, compound review context
- pattern-recognition-specialist: Key renames, AGENTS.md divergence strategy, scaling ceiling acknowledgment
- learnings-researcher ×3: Cross-referenced with 3 existing solution documents
- orchestrating-swarms skill: Data contracts, file ownership, error handling tables
- agent-native-architecture skill: Orchestrator-native vs agent-native assessment
- document-review skill: Deliverable separation, A.6 sub-task split
- best-practices-researcher ×2: Industry patterns (Temporal, Step Functions), antfarm issue #109, webhook system

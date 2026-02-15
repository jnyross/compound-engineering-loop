---
title: "Antfarm Runtime Compatibility for Compound Engineering Loop Workflow"
date: 2026-02-15
category: integration-issues
tags: [workflow-compatibility, antfarm-runtime, yaml-schema, agent-refactoring, openclaw]
severity: medium
component: workflow-engine
runtime: antfarm
version_bumped: 2.33.0
---

# Antfarm Runtime Compatibility for Compound Engineering Loop Workflow

## Problem

The compound-engineering-loop workflow (`workflow.yml`) and its five agent prompt files (`agents/*/AGENTS.md`) could not run on the antfarm v0.5.1 runtime (OpenClaw agent execution environment). Two categories of incompatibility blocked execution:

**1. Unsupported YAML features in workflow.yml:**
- `decision_key` and `on_decision`—conditional routing after review (not implemented in `advancePipeline()`)
- `required_outputs` and `pass_outputs`—output filtering (not implemented in `completeStep()`)
- `on_exhausted`—retry exhaustion handling (not implemented in `failStep()`)
- Missing `polling` and `cron` configuration (required by runtime)
- Missing `context` block initialization (causes `[missing: key]` in templates)

**2. Claude Code-only features in agent prompts:**
- Skill loading (`/workflows:plan`, `/workflows:review`)
- Subagent spawning via `Task` tool (five or more subagents in the review agent alone)
- Interactive tools (`AskUserQuestion`, `TodoWrite`)
- Tool references (`git-worktree`, `agent-browser`, `rclone`)

**Observable symptoms:** The workflow failed to parse or execute. The runtime silently ignored steps referencing `decision_key`. Agent prompts referenced capabilities absent from the OpenClaw sandbox, causing unpredictable behavior.

## Root Cause

The workflow was designed against a *hypothetical runtime* that supported decision routing, conditional branching, and output filtering. The actual antfarm v0.5.1 runtime implements:

- **`advancePipeline()`**—strictly linear: finds first `waiting` step by `step_index ASC`
- **`completeStep()`**—parses `KEY: value` output line-by-line, merges all into global context, marks step `done`
- **`failStep()`**—only retries the *same* step; `retry_step` field is dead code
- **`resolveTemplate()`**—single-pass `{{key}}` to value replacement; missing keys become `[missing: key]`

The agent prompts targeted Claude Code interactive mode, where skills, subagents, and interactive tools are available. OpenClaw provides an isolated sandbox with no access to these features.

**Root cause pattern:** Gap between documented or assumed capabilities and actual runtime implementation. No schema validation existed to catch unsupported fields.

## Solution

### Track A: Make workflow compatible with current antfarm (this repo)

The fix required six tasks:

**A.1-A.4: Workflow YAML changes (`workflow.yml`)**

Removed all unsupported fields and added required runtime configuration:

```yaml
# BEFORE (broken)
steps:
  - id: review
    decision_key: DECISION          # Not implemented
    on_decision:                     # Not implemented
      approved: compound
      needs_fixes: work
      rejected: brainstorm
    required_outputs: [DECISION]     # Not implemented
    pass_outputs: [review_notes]     # Not implemented
```

```yaml
# AFTER (compatible)
steps:
  - id: review
    expects: "STATUS: done"
    # ROUTING INTENT (Track B): decision_key: DECISION
    # approved -> compound, needs_fixes -> work, rejected -> brainstorm
    # Until Track B ships, pipeline is linear.
    max_retries: 3
```

Added `polling` (1800s timeout), `cron` (60s interval), and a `context` block initializing all 13 output keys to empty strings to prevent `[missing: key]` errors.

**A.5-A.6: Agent prompt adaptation (all five `AGENTS.md` files)**

Adapted all agents for OpenClaw by: removing Claude Code-only features (skills, subagents, interactive tools), adding structured `KEY: value` output format for `completeStep()` parsing, adding shared filesystem documentation, and adding retry-aware instructions (agents detect non-empty `REVIEW_ISSUES` and change behavior on retry). Each file includes a header comment linking to its Claude Code counterpart: `<!-- OpenClaw version -- see .claude/commands/workflows/*.md for Claude Code version -->`.

See [plan](../../plans/2026-02-15-antfarm-decision-routing-integration-plan.md) sections A.5-A.6 for per-agent details.

### Key Design Decisions

1. **Routing intent comments**—Decision routing logic remains as YAML comments rather than deleted code. The comments document Track B goals and make degraded behavior explicit.

2. **PLAN_CONTENT removal**—Agents write plans to `docs/plans/` and output `PLAN_FILE` (path) only. Downstream agents read the file directly from the shared git checkout. This avoids 30-40 KB of context bloat.

3. **STATUS/DECISION separation**—STATUS always equals `done` (signals step completion). DECISION is a separate key for routing (`approved`, `needs_fixes`, `rejected`).

## Prevention

1. **Validate workflow YAML against runtime capabilities before committing.** The root cause was using YAML fields the runtime does not implement. Check the actual `WorkflowStep` TypeScript interface (or a capability registry derived from it) before adding workflow fields. A pre-commit hook that blocks unsupported fields would catch this class of error in seconds rather than hours.

2. **Maintain explicit mode boundaries.** Claude Code agent prompts and OpenClaw agent prompts are separate artifacts with different capability constraints. The header comment pattern (`<!-- OpenClaw version -->`) makes the boundary visible. The two versions live at `agents/*/AGENTS.md` (OpenClaw) and `.claude/commands/workflows/*.md` (Claude Code).

3. **Treat output format as a contract.** `completeStep()` parses line-by-line; multi-line values truncate silently. Document the exact parsing rules in each agent's output format section. The runtime's TypeScript interfaces are more accurate than documentation.

## Related

- **Plan:** [docs/plans/2026-02-15-antfarm-decision-routing-integration-plan.md](../../plans/2026-02-15-antfarm-decision-routing-integration-plan.md)—full technical plan with Track A and Track B specifications
- **Prior solution:** [opencode-antfarm-workflow-compound-engineering-plugin-phases.md](./opencode-antfarm-workflow-compound-engineering-plugin-phases.md)—agent name remapping (strategist to brainstorm, architect to plan, etc.)
- **Prior solution:** [compound-engineering-plugin-comprehensive-refactor.md](../runtime-errors/compound-engineering-plugin-comprehensive-refactor.md)—15 critical and quality issue fixes including STATUS/DECISION separation
- **Open todos:** [016](../../todos/016-pending-p2-multiline-output-truncation.md) (multi-line truncation), [017](../../todos/017-pending-p2-compound-non-approved-handling.md) (compound non-approved handling), [018](../../todos/018-pending-p2-input-label-naming-inconsistency.md) (label naming), [019](../../todos/019-pending-p2-stale-context-on-retry.md) (stale context), [020](../../todos/020-pending-p3-code-simplification-opportunities.md) (simplification)
- **Track B:** Pending PR to `snarktank/antfarm` to implement `routeDecision()` for conditional routing

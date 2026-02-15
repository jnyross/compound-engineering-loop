---
title: Remap antfarm workflow agents to match compound-engineering-plugin phases
date: 2026-02-15
category: integration-issues
tags: [opencode, antfarm, workflow, compound-engineering, agent-configuration, skill-invocation]
severity: medium
modules: [workflow.yml, agents/]
root_cause: Custom agent names (strategist, architect, developer, reviewer, documenter) did not align with compound-engineering-plugin phase names (brainstorm, plan, work, review, compound), preventing automatic skill invocation
---

# Remap Antfarm Workflow Agents to Match Compound Engineering Plugin Phases

## Problem Symptom

An OpenCode antfarm workflow (`compound-engineering-loop`) had 5 agents with generic phase names (strategist, architect, developer, reviewer, documenter) that didn't align with the EveryInc compound-engineering-plugin's workflow structure. Skills were not being invoked automatically because agent prompts were hand-written without referencing them.

## Root Cause

The plugin defines 5 workflow commands — `brainstorm`, `plan`, `work`, `review`, `compound` — each expecting specific skills to be loaded and specific data flows between phases. The custom agents used different names and freehand prompts that didn't trigger any of this behavior.

The critical insight: the plugin's workflow commands aren't just naming conventions — they're **contracts** that expect specific skills to be loaded and specific data flows (like `PLAN_CONTENT`) between phases.

## Working Solution

### 1. Remap agents to plugin phases

| Old Agent | New Agent | Plugin Command | Key Skills |
|-----------|-----------|----------------|------------|
| strategist | brainstorm | brainstorm.md | `brainstorming` |
| architect | plan | plan.md | `repo-research-analyst`, `learnings-researcher`, `spec-flow-analyzer` |
| developer | work | work.md | `git-worktree`, `agent-browser` |
| reviewer | review | review.md | `security-sentinel`, `performance-oracle`, `code-simplicity-reviewer` |
| documenter | compound | compound.md | `compound-docs` |

### 2. Fix data flow: add PLAN_CONTENT output

The plan step must output full plan content (not just a file path) so review can verify implementation against it:

```yaml
# plan step
required_outputs: [plan_file, plan_content, plan_summary]

# review step input
PLAN (what should have been implemented):
{{plan_content}}
```

### 3. Add missing review features

- **Protected artifacts**: Never flag `docs/plans/*.md` or `docs/solutions/*.md` for deletion
- **Conditional migration agents**: `schema-drift-detector`, `data-migration-expert` only when migrations present
- **Ultra-thinking**: Stakeholder perspective analysis, edge case exploration
- **Severity synthesis**: P1/P2/P3 todo files in `todos/`

### 4. Add missing work features

- Post-Deploy Monitoring section in PR descriptions
- Screenshot capture/upload for UI changes
- Incremental commits per logical unit

### 5. Review failure loops back to brainstorm

On rejection, the loop returns to brainstorm (not just re-implement) to re-analyze root cause.

## Prevention Strategies

1. **Start from the plugin, not from scratch.** Never write agent prompts freehand when a plugin already defines the workflow. Run the plugin's workflow once on a trivial task first.

2. **Audit data flow between steps.** For every step transition, verify: "What does step N output? What does step N+1 expect as input? Are these the same artifact?"

3. **Respect mode boundaries.** Brainstorm mode = no code changes. Encode this as a hard gate, not a soft suggestion.

4. **Test each step in isolation.** Verify each step independently with known inputs before connecting them in a chain.

5. **Customization should be subtractive.** Start with the full plugin workflow and remove what you don't need, rather than building from nothing.

## Cross-References

- Plugin source: [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin)
- Workflow commands: `plugins/compound-engineering/commands/workflows/`
- Skills referenced: `brainstorming`, `compound-docs`, `git-worktree`, `file-todos`

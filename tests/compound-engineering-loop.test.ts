/**
 * Test: compound-engineering-loop workflow contract
 *
 * Validates:
 * - Section A: workflow.yml loads and has correct structure
 * - Section B: every template variable resolves (no [missing: ...] markers)
 *
 * This test is standalone and can run in the compound-engineering-loop repo.
 */

import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";

// Simple resolveTemplate implementation (matches antfarm's)
function resolveTemplate(template: string, context: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_match, key: string) => {
    if (key in context) return context[key];
    const lower = key.toLowerCase();
    if (lower in context) return context[lower];
    return `[missing: ${key}]`;
  });
}

// Load workflow spec from local YAML
function loadWorkflowSpec(workflowDir: string) {
  const workflowPath = path.join(workflowDir, "workflow.yml");
  const content = fs.readFileSync(workflowPath, "utf-8");
  return YAML.parse(content);
}

// Test runner
const testResults: { name: string; passed: boolean; error?: string }[] = [];

function it(name: string, fn: () => void) {
  try {
    fn();
    testResults.push({ name, passed: true });
  } catch (e) {
    testResults.push({ name, passed: false, error: String(e) });
  }
}

function describe(name: string, fn: () => void) {
  console.log(`\n▶ ${name}`);
  fn();
}

const WORKFLOW_DIR = path.resolve(import.meta.dirname, "..");

// Section A: workflow.yml loads and validates
describe("compound-engineering-loop workflow loads", () => {
  it("loads workflow with correct id", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    if (spec.id !== "compound-engineering-loop") {
      throw new Error(`Expected id "compound-engineering-loop", got "${spec.id}"`);
    }
  });

  it("has 5 steps", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    if (spec.steps?.length !== 5) {
      throw new Error(`Expected 5 steps, got ${spec.steps?.length}`);
    }
  });

  it("has correct step ids in order", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    const stepIds = spec.steps.map((s: { id: string }) => s.id);
    const expected = ["brainstorm", "plan", "work", "review", "compound"];
    if (JSON.stringify(stepIds) !== JSON.stringify(expected)) {
      throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(stepIds)}`);
    }
  });

  it("all steps expect STATUS: done", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    for (const step of spec.steps) {
      if (!step.expects?.includes("STATUS: done")) {
        throw new Error(`Step ${step.id} should expect STATUS: done`);
      }
    }
  });

  it("max_retries is between 1-3", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    for (const step of spec.steps) {
      if (step.max_retries < 1 || step.max_retries > 3) {
        throw new Error(`Step ${step.id} max_retries should be 1-3, got ${step.max_retries}`);
      }
    }
  });
});

// Section B: template variable completeness
describe("template variables resolve without [missing:]", () => {
  // Context keys defined in workflow.yml
  const initialContext = new Set([
    "task", "repo", "branch", "review_issues", "brainstorm_output",
    "plan_file", "plan_summary", "implementation_summary", "files_changed",
    "pr_url", "review_notes", "decision", "learnings", "file_created"
  ]);

  // Known output keys from each step
  const stepOutputs: Record<string, string[]> = {
    brainstorm: ["brainstorm_output", "status"],
    plan: ["plan_file", "plan_summary", "status"],
    work: ["implementation_summary", "files_changed", "pr_url", "status"],
    review: ["review_notes", "review_issues", "decision", "status"],
    compound: ["learnings", "file_created", "status"],
  };

  it("every {{variable}} in step inputs resolves from context or earlier step outputs", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    const availableKeys = new Set(initialContext);

    for (const step of spec.steps) {
      const templateVars = step.input?.match(/\{\{(\w+)\}\}/g) || [];

      for (const match of templateVars) {
        const varName = match.slice(2, -2);
        if (!availableKeys.has(varName)) {
          throw new Error(
            `Step '${step.id}' references {{${varName}}} which is not available. ` +
            `Available: ${[...availableKeys].join(", ")}`
          );
        }
      }

      const outputs = stepOutputs[step.id] || [];
      for (const key of outputs) {
        availableKeys.add(key);
      }
    }
  });

  it("resolveTemplate produces no [missing:] with full context", () => {
    const spec = loadWorkflowSpec(WORKFLOW_DIR);
    const fullContext: Record<string, string> = {};

    for (const key of initialContext) {
      fullContext[key] = `test-value-${key}`;
    }
    for (const outputs of Object.values(stepOutputs)) {
      for (const key of outputs) {
        fullContext[key] = `test-value-${key}`;
      }
    }

    for (const step of spec.steps) {
      const resolved = resolveTemplate(step.input || "", fullContext);
      if (resolved.includes("[missing:")) {
        throw new Error(`Step '${step.id}' resolved contains [missing:]: ${resolved.slice(0, 200)}`);
      }
    }
  });

  it("resolveTemplate produces [missing:] for undefined variables", () => {
    const result = resolveTemplate("task: {{task}} and {{missing}}", { task: "my task" });
    if (result !== "task: my task and [missing: missing]") {
      throw new Error(`Expected "[missing: missing]", got "${result}"`);
    }
  });
});

// Run and report
console.log("\n" + "=".repeat(60));
const passed = testResults.filter(r => r.passed).length;
const failed = testResults.filter(r => !r.passed).length;

for (const result of testResults) {
  if (result.passed) {
    console.log(`  ✔ ${result.name}`);
  } else {
    console.log(`  ✘ ${result.name}`);
    console.log(`    ${result.error}`);
  }
}

console.log("=".repeat(60));
console.log(`ℹ tests ${testResults.length}`);
console.log(`ℹ pass ${passed}`);
console.log(`ℹ fail ${failed}`);

if (failed > 0) {
  process.exit(1);
}

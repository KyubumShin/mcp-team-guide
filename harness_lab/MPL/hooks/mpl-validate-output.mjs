#!/usr/bin/env node
/**
 * MPL Output Validation Hook (PostToolUse)
 * Inserts validation reminder when a validate_prompt-enabled agent completes.
 *
 * Based on: design doc section 9.2 hook 2 + hoyeon validate_prompt pattern
 *
 * Agents with validate_prompt: gap-analyzer, tradeoff-analyzer, verification-planner, worker
 * When these agents complete via Task tool, this hook inserts a [MPL VALIDATION] reminder
 * so the orchestrator checks the output against the agent's Output_Schema.
 */

import { dirname, join } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { existsSync, readFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Import shared MPL state utility
const { isMplActive, readState, writeState } = await import(
  pathToFileURL(join(__dirname, 'lib', 'mpl-state.mjs')).href
);

// Import shared stdin reader
const { readStdin } = await import(
  pathToFileURL(join(__dirname, 'lib', 'stdin.mjs')).href
);

// Agents that require output validation
const VALIDATE_AGENTS = new Set([
  'mpl-gap-analyzer',
  'mpl-tradeoff-analyzer',
  'mpl-verification-planner',
  'mpl-worker',
  'mpl-research-synthesizer',
]);

// Expected output sections per agent
const EXPECTED_SECTIONS = {
  'mpl-gap-analyzer': [
    '1. Missing Requirements',
    '2. AI Pitfalls',
    '3. Must NOT Do',
    '4. Recommended Questions',
  ],
  'mpl-tradeoff-analyzer': [
    'Overall Risk Assessment',
    'Change-Level Analysis',
    'Recommended Execution Order',
  ],
  'mpl-verification-planner': [
    '1. Test Infrastructure',
    '2. A-items',
    '3. S-items',
    '4. H-items',
    '5. Verification Gaps',
    '6. External Dependencies',
  ],
  'mpl-worker': [
    'todo_id',
    'status',
    'outputs',
    'acceptance_criteria',
  ],
  'mpl-research-synthesizer': [
    'Executive Summary',
    'Option Comparison',
    'Anti-Patterns & Risks',
    'Recommendations',
    'Implementation Guidance',
    'Open Questions',
    'Sources',
  ],
};

async function main() {
  const input = await readStdin();

  let data;
  try {
    data = JSON.parse(input);
  } catch {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
    return;
  }

  const toolName = data.tool_name || data.toolName || '';

  // Only intercept Task tool completions
  if (!['Task', 'task'].includes(toolName)) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
    return;
  }

  // Check if MPL is active
  const cwd = data.cwd || data.directory || process.cwd();
  if (!isMplActive(cwd)) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
    return;
  }

  // Extract agent type from tool input
  const toolInput = data.tool_input || data.toolInput || {};
  const agentType = toolInput.subagent_type || toolInput.subagentType || '';

  // Check if this agent requires validation
  if (!VALIDATE_AGENTS.has(agentType)) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
    return;
  }

  // Get expected sections for this agent
  const sections = EXPECTED_SECTIONS[agentType] || [];

  // Actually validate tool_response content against expected sections
  const toolResponse = data.tool_response || data.toolResponse || '';
  const responseText = typeof toolResponse === 'string'
    ? toolResponse
    : JSON.stringify(toolResponse);

  const missingSections = [];
  const foundSections = [];
  for (const section of sections) {
    // Case-insensitive search for section name in response
    if (responseText.toLowerCase().includes(section.toLowerCase())) {
      foundSections.push(section);
    } else {
      missingSections.push(section);
    }
  }

  const validationPassed = missingSections.length === 0;
  const sectionList = sections.map(s => {
    const found = foundSections.includes(s);
    return `  - ${found ? '[PASS]' : '[MISSING]'} ${s}`;
  }).join('\n');

  // H2: Estimate token usage from response length and update state
  try {
    const estimatedTokens = Math.ceil(responseText.length / 4);
    if (estimatedTokens > 0) {
      const currentState = readState(cwd);
      if (currentState) {
        const currentTokens = currentState.cost?.total_tokens || 0;
        writeState(cwd, { cost: { total_tokens: currentTokens + estimatedTokens } });
      }
    }
  } catch {
    // Token tracking is best-effort; do not block on failure
  }

  let message;
  if (validationPassed) {
    message = `[MPL VALIDATION PASSED] Agent "${agentType}" output contains all ${sections.length} required sections.`;
  } else {
    // C3: Prefix with [VALIDATION FAILED] for unmistakable signal
    message = `[VALIDATION FAILED] [MPL VALIDATION FAILED] Agent "${agentType}" output is missing ${missingSections.length}/${sections.length} required sections.

Validation results:
${sectionList}

Missing sections: ${missingSections.join(', ')}

ACTION REQUIRED: Re-run the agent with clarified instructions targeting the missing sections.
Do NOT proceed to the next phase until all sections are present.`;
  }

  // C3: Block (continue: false) when validation fails
  console.log(JSON.stringify({
    continue: validationPassed,
    hookSpecificOutput: {
      hookEventName: 'PostToolUse',
      additionalContext: message
    }
  }));
}

main().catch(() => {
  console.log(JSON.stringify({ continue: true, suppressOutput: true }));
});

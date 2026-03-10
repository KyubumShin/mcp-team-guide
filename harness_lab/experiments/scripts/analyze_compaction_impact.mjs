#!/usr/bin/env node
/**
 * Compaction Impact Analyzer
 *
 * Reads phases.jsonl and compactions.jsonl from MPL profile data,
 * then analyzes the correlation between compaction count and pass rate degradation.
 *
 * Usage: node analyze_compaction_impact.mjs <project-root>
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const PROFILE_DIR = '.mpl/mpl/profile';

function parseJsonl(filePath) {
  if (!existsSync(filePath)) return [];
  return readFileSync(filePath, 'utf-8')
    .split('\n')
    .filter(l => l.trim())
    .map(l => { try { return JSON.parse(l); } catch { return null; } })
    .filter(Boolean);
}

function analyze(projectRoot) {
  const phasesPath = join(projectRoot, PROFILE_DIR, 'phases.jsonl');
  const compactionsPath = join(projectRoot, PROFILE_DIR, 'compactions.jsonl');

  const phases = parseJsonl(phasesPath);
  const compactions = parseJsonl(compactionsPath);

  console.log('=== Compaction Impact Analysis ===\n');

  // --- Compaction Events ---
  console.log(`Compaction events: ${compactions.length}`);
  if (compactions.length > 0) {
    console.log('\nCompaction Log:');
    console.log(`${'#'.padStart(3)} ${'Trigger'.padEnd(8)} ${'Phase'.padEnd(20)} ${'Tokens'.padStart(10)} ${'Fix Loops'.padStart(10)}`);
    console.log('-'.repeat(55));
    for (const c of compactions) {
      console.log(
        `${String(c.compaction_count).padStart(3)} ` +
        `${(c.trigger || '?').padEnd(8)} ` +
        `${(c.current_phase || '?').padEnd(20)} ` +
        `${String(c.total_tokens_at_compaction || 0).padStart(10)} ` +
        `${String(c.fix_loop_count || 0).padStart(10)}`
      );
    }
  }

  // --- Phase Pass Rates by Compaction Count ---
  const phasesWithCompaction = phases.filter(p => p.compaction_count !== undefined);

  if (phasesWithCompaction.length === 0) {
    console.log('\nNo phases with compaction_count data found.');
    console.log('Run MPL pipelines with the compaction tracker enabled to collect data.');
    return;
  }

  // Group by compaction_count
  const groups = {};
  for (const p of phasesWithCompaction) {
    const cc = p.compaction_count || 0;
    if (!groups[cc]) groups[cc] = [];
    groups[cc].push(p);
  }

  console.log('\n--- Pass Rate by Compaction Count ---');
  console.log(`${'Compactions'.padStart(12)} ${'Phases'.padStart(8)} ${'Avg Pass%'.padStart(10)} ${'Avg Fixes'.padStart(10)} ${'Stagnation%'.padStart(12)}`);
  console.log('-'.repeat(56));

  const sortedKeys = Object.keys(groups).map(Number).sort((a, b) => a - b);

  for (const cc of sortedKeys) {
    const group = groups[cc];
    const withPassRate = group.filter(p => p.pass_rate !== null && p.pass_rate !== undefined);
    const avgPassRate = withPassRate.length > 0
      ? (withPassRate.reduce((s, p) => s + p.pass_rate, 0) / withPassRate.length).toFixed(1)
      : 'N/A';
    const avgFixes = (group.reduce((s, p) => s + (p.micro_fixes || 0), 0) / group.length).toFixed(1);

    // Stagnation: phases where pass_rate didn't improve from previous
    let stagnationCount = 0;
    for (let i = 1; i < withPassRate.length; i++) {
      if (withPassRate[i].pass_rate <= withPassRate[i-1].pass_rate) stagnationCount++;
    }
    const stagnationRate = withPassRate.length > 1
      ? ((stagnationCount / (withPassRate.length - 1)) * 100).toFixed(0)
      : 'N/A';

    console.log(
      `${String(cc).padStart(12)} ` +
      `${String(group.length).padStart(8)} ` +
      `${String(avgPassRate).padStart(10)} ` +
      `${String(avgFixes).padStart(10)} ` +
      `${String(stagnationRate + '%').padStart(12)}`
    );
  }

  // --- Statistical Summary ---
  if (sortedKeys.length >= 2) {
    console.log('\n--- Trend Analysis ---');
    const firstGroup = groups[sortedKeys[0]];
    const lastGroup = groups[sortedKeys[sortedKeys.length - 1]];

    const firstAvg = firstGroup.filter(p => p.pass_rate != null)
      .reduce((s, p) => s + p.pass_rate, 0) / firstGroup.filter(p => p.pass_rate != null).length;
    const lastAvg = lastGroup.filter(p => p.pass_rate != null)
      .reduce((s, p) => s + p.pass_rate, 0) / lastGroup.filter(p => p.pass_rate != null).length;

    const delta = lastAvg - firstAvg;
    console.log(`Pass rate change (compaction ${sortedKeys[0]} → ${sortedKeys[sortedKeys.length - 1]}): ${delta > 0 ? '+' : ''}${delta.toFixed(1)}%`);

    if (delta < -10) {
      console.log('⚠ Significant degradation detected. Session reset recommended after this compaction count.');
    } else if (delta < -5) {
      console.log('⚠ Moderate degradation. Monitor closely.');
    } else {
      console.log('✓ No significant degradation observed.');
    }
  }

  console.log('\n--- Raw Data ---');
  console.log(`Total phases recorded: ${phases.length}`);
  console.log(`Phases with compaction data: ${phasesWithCompaction.length}`);
  console.log(`Compaction events logged: ${compactions.length}`);
}

// Main
const projectRoot = process.argv[2] || process.cwd();
if (!existsSync(join(projectRoot, '.mpl'))) {
  console.error('Error: No .mpl directory found at', projectRoot);
  console.error('Usage: node analyze_compaction_impact.mjs <project-root>');
  process.exit(1);
}

analyze(projectRoot);

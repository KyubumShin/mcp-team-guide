/**
 * UAM Configuration Loader
 * Loads user-defined overrides from .uam/config.json with sensible defaults.
 */

import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

const DEFAULTS = {
  max_fix_loops: 10,
  max_total_tokens: 500000,
  gate1_strategy: 'auto',  // 'docker', 'native', 'skip'
  hitl_timeout_seconds: 30,
  convergence: {
    stagnation_window: 3,
    min_improvement: 0.05,
    regression_threshold: -0.1
  }
};

/**
 * Load UAM config from .uam/config.json, falling back to defaults.
 * @param {string} cwd - Working directory
 * @returns {object} Merged config
 */
export function loadConfig(cwd) {
  const configPath = join(cwd, '.uam', 'config.json');
  if (!existsSync(configPath)) return { ...DEFAULTS };
  try {
    const userConfig = JSON.parse(readFileSync(configPath, 'utf-8'));
    return { ...DEFAULTS, ...userConfig };
  } catch {
    return { ...DEFAULTS };
  }
}

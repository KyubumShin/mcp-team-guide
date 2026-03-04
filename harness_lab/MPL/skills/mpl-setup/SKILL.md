---
description: Setup and configure MPL plugin - install, verify, and repair the Unified Agent Methodology pipeline
---

# MPL Setup

Interactive setup wizard for the MPL plugin. Handles first-time installation, configuration, and repair.

## Protocol

### Step 1: Detect Current State

Check the current MPL installation state:

1. **Plugin exists?** Check for `MPL/.claude-plugin/plugin.json`
2. **Hooks registered?** Check for `MPL/hooks/hooks.json` with all 4 events
3. **State directory?** Check for `.mpl/` directory
4. **Config exists?** Check for `.mpl/config.json`
5. **Settings configured?** Check for `MPL/.claude/settings.local.json`

Classify installation state:
- **NOT_INSTALLED**: No plugin.json found
- **PARTIAL**: Plugin exists but missing hooks, config, or settings
- **INSTALLED**: All components present
- **CORRUPTED**: Files exist but are invalid (bad JSON, missing fields)

### Step 2: Route by State

| State | Action |
|-------|--------|
| NOT_INSTALLED | Report error: "MPL plugin files not found. This project needs the MPL directory with plugin structure. Clone or copy the MPL plugin first." |
| PARTIAL | Go to Step 3 (Repair) |
| INSTALLED | Go to Step 4 (Verify) |
| CORRUPTED | Go to Step 3 (Repair) |

### Step 3: Repair / First-time Configuration

#### 3a: Create `.mpl/` Runtime Directory

```bash
mkdir -p .mpl
mkdir -p .mpl/research
mkdir -p .mpl/checkpoints
```

#### 3b: Create Default Config

If `.mpl/config.json` does not exist, create it:

```json
{
  "max_fix_loops": 10,
  "max_total_tokens": 500000,
  "gate1_strategy": "auto",
  "hitl_timeout_seconds": 30,
  "convergence": {
    "stagnation_window": 3,
    "min_improvement": 0.05,
    "regression_threshold": -0.1
  }
}
```

#### 3c: Verify Hook File Integrity

For each hook file referenced in `hooks/hooks.json`:
1. Check the .mjs file exists
2. Run `node --check {file}` to validate syntax
3. If syntax error found, report the exact error and file

#### 3d: Verify Agent Definitions

For each .md file in `agents/`:
1. Check YAML frontmatter has `name`, `description`, `model`
2. Validate `model` is one of: haiku, sonnet, opus
3. Report any malformed agents

#### 3e: Verify Skill Definitions

For each directory in `skills/`:
1. Check `SKILL.md` exists
2. Check YAML frontmatter has `description`
3. Report any incomplete skills

#### 3f: Ensure Settings

If `MPL/.claude/settings.local.json` doesn't have minimum permissions, create/update:

```json
{
  "permissions": {
    "allow": [
      "Bash(git commit*)",
      "Bash(gh pr*)",
      "Bash(git checkout*)",
      "Bash(node*)",
      "Bash(cat*)"
    ]
  }
}
```

### Step 4: Verify Installation

Run the doctor diagnostic:

```
Task(
  subagent_type="mpl-doctor",
  model="haiku",
  prompt="Run full MPL diagnostics on {MPL_ROOT}. Report all 8 categories."
)
```

### Step 5: Present Results

Display a setup summary:

```
MPL Setup Complete
══════════════════

Plugin:    MPL v{version}
Location:  {MPL_ROOT}
Status:    {HEALTHY|REPAIRED|ISSUES_REMAIN}

Components:
  Plugin Config  : OK
  Hooks (4/4)    : OK
  Agents ({N})   : OK
  Skills ({N})   : OK
  Commands ({N}) : OK
  Runtime (.mpl) : OK
  Config         : OK
  Settings       : OK

{if REPAIRED}
Repairs Made:
  - Created .mpl/ runtime directory
  - Created default config.json
  - {other repairs}
{/if}

{if ISSUES_REMAIN}
Remaining Issues:
  - {issue 1}
  - {issue 2}
{/if}

Quick Start:
  Say "mpl {task description}" to start a full pipeline
  Say "mpl small {task}" for a lightweight pipeline
  Run "/mpl:mpl-doctor" to re-check health
  Run "/mpl:mpl-status" to view pipeline status
```

### Step 6: Optional Configuration Interview

After basic setup, ask the user if they want to customize:

Use AskUserQuestion:
- "Would you like to customize MPL settings?"
  - "Use defaults (Recommended)" - Skip customization
  - "Customize" - Proceed to customization questions

If "Customize" selected, ask about:
1. **Max fix loops** (default 10): How many fix attempts before circuit breaker?
2. **Token budget** (default 500K): Maximum token spend per pipeline run?
3. **HITL timeout** (default 30s): How long to wait for human approval before auto-proceeding?
4. **Gate 1 strategy** (auto/docker/native/skip): How to run automated tests?

Write answers to `.mpl/config.json`.

## Error Handling

| Error | Recovery |
|-------|----------|
| MPL directory not found | "MPL plugin directory not found. Ensure the MPL/ directory exists in your project with the plugin structure." |
| Node.js not available | "Node.js is required for MPL hooks. Install Node.js >= 18." |
| Hook syntax error | "Hook file has syntax error: {detail}. Check the file manually." |
| Permission denied | "Cannot create .mpl/ directory. Check file system permissions." |
| Invalid plugin.json | "Plugin config is corrupted. Recreating from template..." |

## Idempotency

This skill is safe to run multiple times:
- Existing valid files are never overwritten
- Only missing or invalid components are created/repaired
- Config customizations are preserved across re-runs
- State files (.mpl/state.json) are never touched by setup

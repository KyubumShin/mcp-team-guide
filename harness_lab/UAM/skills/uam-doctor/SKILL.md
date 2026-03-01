---
description: Diagnose UAM installation - validate plugin structure, hooks, agents, skills, state, and configuration
---

# UAM Doctor

Run comprehensive diagnostics on the UAM installation and report health status.

## Protocol

### Step 1: Locate UAM Root

Find the UAM plugin root directory:
1. Check if `UAM/.claude-plugin/plugin.json` exists relative to the project root
2. If not found, search for `.claude-plugin/plugin.json` in parent directories
3. If not found, report: "UAM plugin not found. Run `/uam:uam-setup` to install."

Record the UAM root path for all subsequent checks.

### Step 2: Run Diagnostics

Delegate to the `uam-doctor` agent with the UAM root path:

```
Task(
  subagent_type="uam-doctor",
  model="haiku",
  prompt="Run full UAM diagnostics on the plugin at {UAM_ROOT}. Check all 8 categories: plugin structure, hooks, agents, skills, commands, state/runtime, configuration, documentation. The project working directory is {CWD}."
)
```

### Step 3: Present Results

Display the doctor's report to the user. Add a summary header:

```
UAM Doctor - Installation Diagnostics
══════════════════════════════════════
{agent report}
```

### Step 4: Offer Next Steps

Based on the results:

| Result | Action |
|--------|--------|
| All PASS | "UAM is healthy and ready to use. Say `uam` to start a pipeline." |
| WARN only | "UAM is functional with minor issues. Recommendations listed above." |
| Any FAIL | "UAM has issues that need fixing. Run `/uam:uam-setup` to auto-repair, or fix manually using the recommendations above." |
| Plugin not found | "UAM is not installed. Run `/uam:uam-setup` to set up." |

# MPL (Micro-Phase Loop)

Independent autonomous coding pipeline plugin for Claude Code.

MPL decomposes user requests into ordered micro-phases, each with independent plan-execute-verify mini-loops. Each phase gets a fresh session with structured context only (Pivot Points + Phase Decisions + impact files), preventing context pollution.

## Quick Start

```
Say "mpl {task description}" to start a pipeline
```

Or use the skill directly:
```
/mpl:mpl
```

## Architecture

### Core Principle: Orchestrator-Worker Separation

The orchestrator NEVER writes source code directly. All code changes are delegated to `mpl-worker` agents via the Task tool. PreToolUse hook enforces this as a hard block.

### Pipeline Flow

```
Step 0: Maturity Mode Detection
Step 1: Pivot Points Interview (immutable constraints)
Step 2: Codebase Analysis (structure, dependencies, interfaces)
Step 3: Phase Decomposition (mpl-decomposer -> ordered micro-phases)
Step 4: Phase Execution Loop (mpl-phase-runner -> mpl-worker per phase)
Step 5: Finalize (verification, learnings, atomic commits)
```

### State Machine

```
mpl-init -> mpl-decompose -> mpl-phase-running <-> mpl-phase-complete
                 ^                    |                      |
                 +-- mpl-circuit-break               mpl-finalize -> completed
                           |
                       mpl-failed
```

## Components

### Agents (5)

| Agent | Role | Model |
|-------|------|-------|
| `mpl-worker` | TODO implementation specialist | sonnet |
| `mpl-phase-runner` | Phase executor with mini-plan, delegation, verification | sonnet |
| `mpl-decomposer` | Phase decomposition from user request | opus |
| `mpl-git-master` | Atomic commit specialist | sonnet |
| `mpl-compound` | Learning extraction and knowledge distillation | sonnet |

### Skills (7)

| Skill | Purpose |
|-------|---------|
| `/mpl:mpl` | Main MPL pipeline |
| `/mpl:mpl-pivot` | Pivot Points interview |
| `/mpl:mpl-status` | Pipeline status dashboard |
| `/mpl:mpl-cancel` | Clean cancellation with state preservation |
| `/mpl:mpl-resume` | Resume from last checkpoint |
| `/mpl:mpl-doctor` | Installation diagnostics |
| `/mpl:mpl-setup` | Setup wizard |

### Hooks (4)

| Hook | Event | Purpose |
|------|-------|---------|
| `mpl-write-guard` | PreToolUse | Blocks orchestrator from editing source files |
| `mpl-validate-output` | PostToolUse | Validates agent output against expected schema |
| `mpl-phase-controller` | Stop | Manages phase transitions and loop continuation |
| `mpl-keyword-detector` | UserPromptSubmit | Detects "mpl" keyword and initializes pipeline |

### State Directory: `.mpl/`

| Path | Purpose |
|------|---------|
| `.mpl/state.json` | Pipeline state |
| `.mpl/mpl/state.json` | MPL execution state |
| `.mpl/mpl/decomposition.yaml` | Phase decomposition output |
| `.mpl/mpl/phase-decisions.md` | Accumulated Phase Decisions |
| `.mpl/mpl/phases/phase-N/` | Per-phase artifacts |
| `.mpl/pivot-points.md` | Immutable constraints |
| `.mpl/config.json` | User configuration overrides |

## Maturity Modes

| Mode | Phase Size | PP Required | Discovery Handling |
|------|-----------|-------------|-------------------|
| `explore` | S (1-3 TODOs) | Optional | Auto-approved |
| `standard` | M (3-5 TODOs) | Required | HITL on PP conflict |
| `strict` | L (5-7 TODOs) | Required + enforced | All changes HITL |

## Installation

```
/mpl:mpl-setup
```

Or say "setup mpl" to run the setup wizard.

## Diagnostics

```
/mpl:mpl-doctor
```

## Design Reference

Full specification: `MPL/docs/design.md`

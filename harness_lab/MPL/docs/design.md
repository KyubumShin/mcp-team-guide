# MPL (Micro-Phase Loop) Design Document

## Overview

MPL is an independent autonomous coding pipeline that decomposes user requests into ordered micro-phases. Each phase operates with a fresh session and structured context only, preventing context pollution that degrades agent performance in long-running tasks.

## Design Principles

### Principle 1: Orchestrator-Worker Separation
The orchestrator NEVER writes code directly. All code changes go through `mpl-worker` agents via the Task tool. This is enforced by the `mpl-write-guard` PreToolUse hook.

### Principle 2: Plan First
Execution starts only after phase decomposition. The decomposition output (ordered phases with interface contracts) is the source of truth.

### Principle 3: Test-Based Verification
Each phase has machine-verifiable success criteria. No subjective "done" claims -- only evidence-backed verification (command exit codes, test results, file existence, grep patterns).

### Principle 4: Bounded Retries
Phase Runners have max 3 retries internally. The orchestrator has max 2 redecompositions. Exceeding limits triggers circuit break, not infinite loops.

### Principle 5: Knowledge Accumulation
State Summaries are the ONLY knowledge transfer between phases. Phase Decisions accumulate across phases with a 3-Tier classification system (Active/Summary/Archived) to manage token budget.

## Pipeline Architecture

### State Machine

```
mpl-init -> mpl-decompose -> mpl-phase-running <-> mpl-phase-complete
                 ^                    |                      |
                 +-- mpl-circuit-break               mpl-finalize -> completed
                           |
                       mpl-failed
```

### Step-by-Step Flow

#### Step 0: Maturity Mode Detection
Read `.mpl/config.json` for `maturity_mode` (default: `"standard"`).

| Mode | Phase Size | Discovery Handling |
|------|-----------|-------------------|
| `explore` | S (1-3 TODOs, 1-3 files) | Auto-approved |
| `standard` | M (3-5 TODOs, 2-5 files) | HITL on PP conflict |
| `strict` | L (5-7 TODOs, 4-8 files) | All changes HITL |

#### Step 1: Pivot Points Interview
Discover immutable project constraints through structured interview. PP states: CONFIRMED (hard constraint) / PROVISIONAL (soft, HITL on conflict).

#### Step 2: Codebase Analysis
Orchestrator analyzes codebase structure using built-in tools:
- Structure analysis (Glob)
- Dependency graph (ast_grep_search / Grep)
- Interface extraction (lsp_document_symbols)
- Centrality analysis (derived from dependencies)
- Test infrastructure (Glob + Read)
- Configuration (Read)

Output saved to `.mpl/mpl/codebase-analysis.json`.

#### Step 3: Phase Decomposition
`mpl-decomposer` (opus) breaks user request into ordered micro-phases. Each phase declares:
- Scope and rationale
- Impact (files to create/modify/test)
- Interface contract (requires/produces)
- Success criteria (typed: command/test/file_exists/grep/description)
- Estimated complexity (S/M/L)

Output saved to `.mpl/mpl/decomposition.yaml`.

#### Step 4: Phase Execution Loop
For each phase in order:

1. **Context Assembly**: Load Pivot Points, tiered Phase Decisions, phase definition, impact files, previous state summary
2. **Phase Runner Execution**: Fresh Task agent session with assembled context
3. **Result Processing**: Validate state summary, save artifacts, process discoveries, update state
4. **On circuit break**: Redecompose remaining work (max 2 redecompositions)

##### Phase Decision 3-Tier Classification
- **Tier 1 (Active)**: Full detail -- PDs whose affected files intersect current phase impact
- **Tier 2 (Summary)**: 1-line summary -- architectural/schema/API PDs not directly touching current files
- **Tier 3 (Archived)**: IDs only -- not sent in context

Token budget: Tier 1 ~400-800, Tier 2 ~90-240 tokens (stable regardless of phase count).

#### Step 5: Finalize
- Final verification (all criteria from all phases)
- Learning extraction via `mpl-compound`
- Atomic commits via `mpl-git-master`
- Metrics saved to `.mpl/mpl/metrics.json`
- Completion report

## Agent Catalog

| Agent | Role | Model | Disallowed Tools |
|-------|------|-------|-----------------|
| `mpl-worker` | Implement single TODO item | sonnet | Task |
| `mpl-phase-runner` | Execute one phase (plan, delegate, verify, summarize) | sonnet | None |
| `mpl-decomposer` | Break request into ordered phases | opus | Read, Write, Edit, Bash, Glob, Grep, Task |
| `mpl-git-master` | Atomic commit creation | sonnet | Write, Edit, Task |
| `mpl-compound` | Learning extraction post-pipeline | sonnet | None |

## Hook System

| Hook | Event | Purpose |
|------|-------|---------|
| `mpl-write-guard` | PreToolUse (Edit/Write) | Blocks orchestrator source file edits when MPL active |
| `mpl-validate-output` | PostToolUse (Task) | Validates agent output sections, tracks token usage |
| `mpl-phase-controller` | Stop | Manages phase transitions based on state |
| `mpl-keyword-detector` | UserPromptSubmit | Detects "mpl" keyword, initializes pipeline state |

## State Management

### Pipeline State: `.mpl/state.json`
Top-level pipeline tracking: run_mode, current_phase, gate_results, fix_loop_count, cost, convergence, research status.

### MPL State: `.mpl/mpl/state.json`
MPL-specific tracking: phases total/completed/current/failed, phase_details array, redecompose_count, totals.

### Per-Phase Artifacts: `.mpl/mpl/phases/phase-N/`
- `mini-plan.md`: Phase-specific TODO list
- `state-summary.md`: Completion summary (knowledge transfer)
- `verification.md`: Verification results with evidence

## Discovery Processing

When Phase Runner reports discoveries:
1. **PP Conflict Check**: CONFIRMED PP conflict -> auto-reject. PROVISIONAL -> maturity determines HITL.
2. **PD Override Check**: Explicit override request required for changing past decisions.
3. **General Discovery**: Handling varies by maturity mode (auto-approve / batch review / backlog).

## Resume Protocol

MPL supports resume via per-phase state persistence. On session start, detect `.mpl/state.json` with `run_mode == "mpl"`, find next incomplete phase, load accumulated Phase Decisions and last state summary, continue execution.

## Configuration

`.mpl/config.json` supports:
- `max_fix_loops` (default: 10)
- `max_total_tokens` (default: 500000)
- `gate1_strategy` (auto/docker/native/skip)
- `hitl_timeout_seconds` (default: 30)
- `convergence` settings (stagnation_window, min_improvement, regression_threshold)
- `maturity_mode` (explore/standard/strict)

---
description: UAM 5-Phase Pipeline - Unified Agent Methodology. Standalone orchestration for automated planning, execution, and verification.
---

# UAM (Unified Agent Methodology)

You are now the UAM orchestrator. This skill activates the full 5-Phase pipeline.
UAM works **standalone** — no external orchestration framework required.

## Activation Protocol

1. Initialize `.uam/state.json` if not exists (keyword hook may have already done this)
2. Read state to determine current phase
3. **Load the detailed orchestration protocol**: read `/uam:uam-run` command for Phase-by-Phase execution instructions
4. Execute phases sequentially until completion

## Core Rules (HARD ENFORCEMENT)

```
RULE 1: You NEVER write source code directly. All code changes → uam-worker/uam-frontend via Task tool.
RULE 2: PLAN.md checkboxes are SSOT. Only update when Worker + Verify both pass.
RULE 3: Validate agent output. Check Output_Schema after every validate_prompt agent.
RULE 4: Respect phase gates. Never skip phases or bypass quality gates.
```

## State Machine

```
phase1a-research → phase1b-plan → phase2-sprint → phase3-gate → phase5-finalize
      ↓ (skip)          ↑                              ↓
      └─────────────────┘                         phase4-fix ←→ phase3-gate (re-run)
                                                       ↓
                                                  phase5-finalize (partial)
```

## Key Files

| File | Purpose |
|------|---------|
| `.uam/state.json` | Pipeline state (current_phase, gate_results, fix_loop_count) |
| `.uam/PLAN.md` | Plan with TODO checkboxes (SSOT) |
| `.uam/pivot-points.md` | Immutable constraints (Phase 0) |
| `.uam/research/report.md` | Deep research output (Phase 1-A) |
| `docs/learnings/{feature}/` | Extracted learnings (Phase 5) |

## Phase Overview

| Phase | Name | Key Action | Agents |
|-------|------|------------|--------|
| 0 | Pivot Points | Immutable constraints interview | (orchestrator) |
| 1-A | Deep Research | 3-stage research (skippable) | explore, researcher, synthesizer |
| 1-B | Plan Generation | Parallel analysis → PLAN.md → HITL | gap-analyzer, pm, verification-planner, tradeoff-analyzer, designer |
| 2 | MVP Sprint | Non-blocking TODO parallel dispatch | worker, frontend, git-master |
| 3 | Quality Gate | Gate 1 (tests) → Gate 2 (review) → Gate 3 (agent-as-user) | code-reviewer, Judge logic |
| 4 | Fix Loop | Adaptive 3-tier: simple fix → session reset → circuit breaker | worker, debugger |
| 5 | Finalize | Learnings extraction + atomic commits | git-master |

## IMPORTANT: Load Detailed Protocol

This SKILL.md is the activation summary. For **Phase-by-Phase execution instructions** (agent calls, PLAN.md template, model routing, Discovery processing, ConvergenceDetector logic, error handling), you MUST read the full orchestration protocol:

```
Read the command file: UAM/commands/uam-run.md
```

Do NOT proceed with Phase execution without loading the detailed protocol first.

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/uam:uam-small` | 3-Phase lightweight pipeline (1-5 files, clear scope) |
| `/uam:uam-pivot` | Pivot Points interview (immutable constraints) |
| `/uam:uam-research` | Standalone deep research (independent of pipeline) |
| `/uam:uam-status` | Pipeline status dashboard |
| `/uam:uam-cancel` | Clean cancellation with state preservation |
| `/uam:uam-resume` | Resume from last phase |
| `/uam:uam-bugfix` | Standalone adaptive bug fixing (single bug, 3 attempts) |
| `/uam:uam-compound` | Learning extraction and knowledge distillation |
| `/uam:uam-doctor` | Installation diagnostics and health check |
| `/uam:uam-setup` | Setup wizard - install, configure, repair |

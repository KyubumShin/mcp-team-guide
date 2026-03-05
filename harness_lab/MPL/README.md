# MPL (Micro-Phase Loop) v3.0

Coherence-first autonomous coding pipeline plugin for Claude Code.

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

### Design Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | Orchestrator-Worker Separation | Orchestrator delegates all code changes to workers |
| 2 | Plan First | Execution starts only after phase decomposition |
| 3 | Test-Based Verification | Machine-verifiable success criteria only -- no subjective "done" |
| 4 | Bounded Retries | Max 3 retries/phase, max 2 redecompositions, then circuit break |
| 5 | Knowledge Accumulation | State Summaries are the ONLY knowledge transfer between phases |

### Pipeline Flow

```
Step 0: Maturity Mode Detection + Triage
Step 1: Pivot Points Interview (immutable constraints)
Step 2: Phase 0 Enhanced (API contracts, examples, types, error specs)
Step 3: Codebase Analysis (structure, dependencies, interfaces)
Step 4: Pre-Execution Analysis (gap analysis, tradeoffs, verification plan, pre-mortem)
Step 5: Phase Decomposition (mpl-decomposer -> ordered micro-phases)
Step 6: Phase Execution Loop (mpl-phase-runner -> mpl-worker per phase)
Step 7: Finalize (verification, learnings, atomic commits)
```

### State Machine

```
mpl-init -> mpl-decompose -> mpl-phase-running <-> mpl-phase-complete
                 ^                    |                      |
                 +-- mpl-circuit-break               mpl-finalize -> completed
                           |
                       mpl-failed
```

## Phase 0 Enhanced

실험 7건의 실증 데이터로 검증된 사전 명세 프로세스. Phase 0에 투자하여 Phase 5(디버깅/수정)를 불필요하게 만든다.

### 4-Step Process

| Step | Source | Output |
|------|--------|--------|
| 1. API Contract Extraction | 함수 시그니처, 파라미터 순서 | `api-contracts` |
| 2. Example Pattern Analysis | 사용 패턴, 기본값, 엣지 케이스 | `examples` |
| 3. Type Policy Definition | 타입 힌트, 컬렉션 타입 규칙 | `type-policy` |
| 4. Error Specification | 표준 예외, 메시지 패턴 | `error-spec` |

### Token Budget Rebalance

```
v1.0 (~81K total)              v3.0 (50~55K target)
Phase 0:  ~5K  ( 6%)           Phase 0: 8~25K (16~45%)  ← 강화
Phase 1-3: ~45K (57%)          Phase 1-3: ~36K (66~72%)
Phase 4:  ~15K (19%)           Phase 4:  ~6K  (11~12%)
Phase 5:  ~16K (20%)           Phase 5:  ~0K  ( 0%)     ← 제거
```

## Build-Test-Fix Micro-Cycles

Phase Runner는 TODO별 즉시 검증을 수행한다:

```
For each TODO:
  Build  → Worker가 구현
  Test   → 즉시 테스트 실행
  Fix    → 실패 시 즉시 수정 (max 2회)

After all TODOs:
  Test Agent → 독립 테스트 작성/실행 (코드 작성자 ≠ 테스트 작성자)
  Cumulative Verification → 전체 테스트 스위트 회귀 검증
```

## Components

### Agents (12)

| Agent | Role | Model | Tool Restrictions |
|-------|------|-------|-------------------|
| `mpl-worker` | TODO 구현 specialist | sonnet | Task 차단 |
| `mpl-phase-runner` | Phase 실행 (mini-plan, delegation, verification) | sonnet | None |
| `mpl-decomposer` | Phase 분해 (pure reasoning) | opus | Read/Write/Edit/Bash/Glob/Grep/Task 차단 |
| `mpl-git-master` | 원자적 커밋 | sonnet | Write/Edit/Task 차단 |
| `mpl-compound` | 학습 추출 및 지식 증류 | sonnet | None |
| `mpl-interviewer` | Pivot Point 인터뷰 specialist | opus | Write/Edit/Bash/Task 차단 |
| `mpl-gap-analyzer` | 누락 요구사항 및 AI 함정 식별 | haiku | Write/Edit/Bash/Task 차단 |
| `mpl-tradeoff-analyzer` | 리스크 평가 (LOW/MED/HIGH) 및 가역성 분석 | sonnet | Write/Edit/Bash/Task 차단 |
| `mpl-verification-planner` | A/S/H-items 분류 및 검증 전략 설계 | sonnet | Write/Edit/Task 차단 |
| `mpl-critic` | Pre-mortem 시뮬레이션 및 리스크 레지스터 | opus | Write/Edit/Bash/Task 차단 |
| `mpl-test-agent` | 독립 테스트 작성/실행 (코드 작성자와 분리) | sonnet | None |
| `mpl-code-reviewer` | 8-category 코드 리뷰 및 Quality Gate | sonnet | Write/Edit/Task 차단 |

### Agent Pipeline Flow

```
mpl-interviewer ──→ mpl-gap-analyzer ──→ mpl-tradeoff-analyzer
       │                   │                      │
       ▼                   ▼                      ▼
  Pivot Points         Gap Report            Risk Assessment
                                                  │
mpl-verification-planner ◀────────────────────────┘
       │
       ▼
  A/S/H Verification Plan
       │
mpl-critic ◀──────────────────────────────────────┘
       │
       ▼
  Go/No-Go Assessment
       │
mpl-decomposer ◀─────────────────────────────────┘
       │
       ▼
  Phase Decomposition (YAML)
       │
mpl-phase-runner (per phase) ──→ mpl-worker (per TODO)
       │                              │
       │                    mpl-test-agent (after all TODOs)
       │
mpl-code-reviewer ◀──────────────────┘ (Quality Gate)
       │
mpl-compound ◀────────────────────────┘ (Finalize)
       │
mpl-git-master ◀──────────────────────┘ (Atomic Commits)
```

### Skills (7)

| Skill | Purpose |
|-------|---------|
| `/mpl:mpl` | Main MPL pipeline |
| `/mpl:mpl-pivot` | Pivot Points interview (standalone or pipeline) |
| `/mpl:mpl-status` | Pipeline status dashboard |
| `/mpl:mpl-cancel` | Clean cancellation with state preservation |
| `/mpl:mpl-resume` | Resume from last checkpoint |
| `/mpl:mpl-doctor` | Installation diagnostics |
| `/mpl:mpl-setup` | Setup wizard |

### Hooks (4)

| Hook | Event | Purpose |
|------|-------|---------|
| `mpl-write-guard` | PreToolUse (Edit/Write) | Blocks orchestrator from editing source files |
| `mpl-validate-output` | PostToolUse (Task) | Validates agent output against expected schema |
| `mpl-phase-controller` | Stop | Manages phase transitions and loop continuation |
| `mpl-keyword-detector` | UserPromptSubmit | Detects "mpl" keyword and initializes pipeline |

### State Directory: `.mpl/`

| Path | Purpose |
|------|---------|
| `.mpl/state.json` | Pipeline state |
| `.mpl/pivot-points.md` | Immutable constraints (Pivot Points) |
| `.mpl/config.json` | User configuration overrides |
| `.mpl/mpl/state.json` | MPL execution state |
| `.mpl/mpl/decomposition.yaml` | Phase decomposition output |
| `.mpl/mpl/phase-decisions.md` | Accumulated Phase Decisions (3-Tier) |
| `.mpl/mpl/phase0/` | Phase 0 Enhanced artifacts (api-contracts, examples, type-policy, error-spec) |
| `.mpl/mpl/phases/phase-N/` | Per-phase artifacts (mini-plan, state-summary, verification) |
| `.mpl/mpl/metrics.json` | Pipeline metrics |

## Verification System

### A/S/H-items Classification

| Type | Name | Verified By | Example |
|------|------|-------------|---------|
| A-item | Agent-Verifiable | Exit code check | `npm test` exits 0 |
| S-item | Sandbox Agent Testing | BDD scenario | Given/When/Then |
| H-item | Human-Required | Side Interview | UX judgment, visual review |

### 3-Gate Quality System

| Gate | Method | Agent |
|------|--------|-------|
| Gate 1 | Automated tests | mpl-phase-runner (cumulative) |
| Gate 2 | Code review (8 categories) | mpl-code-reviewer |
| Gate 3 | PP compliance + H-items | Orchestrator + Human |

### Convergence Detection

Fix loop에서 pass rate 이력을 추적하여 자동 판단:

| Status | Condition | Action |
|--------|-----------|--------|
| `improving` | delta > min_improvement | Continue |
| `stagnating` | variance < 5% AND delta < threshold | Strategy change suggestion |
| `regressing` | delta < -10% | Revert or review Phase 0 artifacts |

## Phase Decision 3-Tier System

Phase 간 의사결정 전달 시 토큰 예산 관리:

| Tier | Content | Token Budget | When |
|------|---------|-------------|------|
| Tier 1 (Active) | Full detail | ~400-800 | Files intersect current phase impact |
| Tier 2 (Summary) | 1-line summary | ~90-240 | Architectural/API PDs not touching current files |
| Tier 3 (Archived) | IDs only | Minimal | Not relevant to current phase |

## Maturity Modes

| Mode | Phase Size | PP Required | Discovery Handling |
|------|-----------|-------------|-------------------|
| `explore` | S (1-3 TODOs) | Optional | Auto-approved |
| `standard` | M (3-5 TODOs) | Required | HITL on PP conflict |
| `strict` | L (5-7 TODOs) | Required + enforced | All changes HITL |

## Triage Integration

Pivot Points interview 깊이를 자동 결정:

| Triage Result | Interview Behavior |
|---------------|-------------------|
| `full` | 4 Rounds: What → What NOT → Either/Or → How to Judge |
| `light` | 2 Rounds: What → What NOT only |
| `skip` | No interview, extract PPs from prompt directly |

## Installation

```
/mpl:mpl-setup
```

Or say "setup mpl" to run the setup wizard.

## Diagnostics

```
/mpl:mpl-doctor
```

## Testing

```
node --test hooks/__tests__/*.test.mjs
```

## Design Reference

- Full specification: `MPL/docs/design.md`
- Roadmap overview: `MPL/docs/roadmap/overview.md`
- Phase 1 Foundation: `MPL/docs/roadmap/phase1-foundation.md`
- Phase 2 Incremental: `MPL/docs/roadmap/phase2-incremental.md`
- Phase 3 Automation: `MPL/docs/roadmap/phase3-automation.md`
- Experiments summary: `MPL/docs/roadmap/experiments-summary.md`

---
description: UAM 3-Phase Lightweight pipeline orchestration protocol
---

# UAM Small Orchestration Protocol

You are now operating as the UAM orchestrator in **small mode**. Follow this protocol exactly.

## Core Rules (HARD ENFORCEMENT)

1. **You NEVER write source code directly.** All code changes go through `uam-worker` agents via Task tool.
2. **PLAN.md checkboxes are SSOT.** Only update checkboxes when Worker + Verify both pass.
3. **Validate agent output.** Check Output_Schema sections after every validate_prompt agent completes.
4. **Respect phase gates.** Do not skip phases or bypass verification.

## State Management

State file: `.uam/state.json` (`run_mode: "small"`)
- Read state to determine current phase
- Update state at phase transitions
- Track `fix_loop_count` (max 3), `gate_results.gate2_passed`

Key state differences from full pipeline:
- `run_mode: "small"`
- `current_phase`: `small-plan` | `small-sprint` | `small-verify` | `completed`
- `max_fix_loops: 3` (vs 10 in full)
- `max_total_tokens: 150000` (vs 500000 in full)

## Model Routing (Fixed — No Escalation)

Small pipeline uses fixed model assignments. Do NOT escalate to opus.

| Agent | Model | Phase | Notes |
|-------|-------|-------|-------|
| `uam-explore` | haiku | 1 | Codebase exploration |
| `uam-pm` | **sonnet** | 1 | Downgraded from opus — small scope doesn't need opus |
| `uam-worker` | sonnet | 2 | Backend/general implementation |
| `uam-frontend` | sonnet | 2 | Frontend/UI implementation |
| `uam-git-master` | sonnet | 2, 3 | Atomic commits |
| `uam-code-reviewer` | sonnet | 3 | Single code review |

---

## Phase 1: Small Plan

### Step 1: Parallel Exploration + Light Research (3 agents)

Launch in a SINGLE message (parallel). 경량 연구를 기존 에이전트 호출에 통합한다.

```
Task(subagent_type="uam-explore", model="haiku",
     prompt="Explore the codebase for: {user request}. Map relevant files, existing patterns, test infrastructure. Keep report concise.")

Task(subagent_type="uam-pm", model="sonnet",
     prompt="Refine requirements for: {user request}. Write concise user stories and acceptance criteria. A-items only (agent-verifiable commands). MoSCoW priority. Keep scope minimal — this is a small feature.")

Task(subagent_type="uam-researcher", model="haiku",
     prompt="Stage 1 Broad Scan (light mode) for: {user request}. Quick survey only — max 2 WebSearch queries + codebase Grep. Identify key prior art and one recommendation. Output Stage 1 schema. Keep brief.")
```

Light research 완료 후 `.uam/research/brief.md` 작성:
```markdown
# Research Brief: {topic}
## Key Finding
{1-2 sentences}
## Prior Art
{top 2-3 relevant references}
## Recommendation
{1 sentence}
## Sources
{URLs}
```

상태 업데이트: `writeState(cwd, { research: { status: 'completed', mode: 'light', report_path: '.uam/research/brief.md' } })`

**Small → Full 에스컬레이션**:

경량 연구 결과에서 복잡도 신호 감지 시:
- 외부 라이브러리 3개 이상 비교 필요
- 기존 코드베이스에 관련 패턴 없음
- Relevance HIGH 항목이 3개 이상

```
AskUserQuestion: "연구 결과 복잡도가 높습니다. 어떻게 하시겠습니까?"
Options:
  1. "Full pipeline으로 전환" → 아래 에스컬레이션 절차 실행
  2. "경량으로 계속" → brief.md 생성 후 진행
  3. "독립 연구 먼저" → /uam:uam-research 안내
```

**Full pipeline 에스컬레이션 절차** (Option 1 선택 시):
```
1. 기존 light research 결과 보존: .uam/research/brief.md 유지
2. run_mode만 변경 (initState 재호출 금지 — 상태 리셋 방지):
   writeState(cwd, {
     run_mode: 'full',
     current_phase: 'phase1a-research',
     max_fix_loops: 10,
     cost: { max_total_tokens: 500000 },
     research: { status: 'stage1', mode: 'full' }
   })
3. Phase 1-A Stage 1에서 brief.md를 기존 연구로 참조 (중복 조사 방지)
4. /uam:uam-run 프로토콜로 전환
```

**Agents NOT used in small mode** (vs full pipeline):
- `uam-gap-analyzer`: scope is small enough to not need gap analysis
- `uam-tradeoff-analyzer`: risk is low for small features
- `uam-verification-planner`: A-items only, no need for A/S/H classification
- `uam-designer`: delegate to uam-frontend if UI work needed

### Step 2: Generate Simplified PLAN.md

Using agent outputs, create `.uam/PLAN.md`:

```markdown
# PLAN: {feature-name}

## Summary
{1-2 sentence summary}

## Research Note (optional — included when light research produced findings)
- Brief: `.uam/research/brief.md`
- Key finding: {1-2 sentence core discovery}
- Recommendation: {1 sentence}

## Risk Assessment
- Overall: {LOW|MED|HIGH}

## TODOs

### [ ] TODO 1: {title}
- Description: {detailed description}
- Dependencies: none
- Acceptance Criteria:
  - [A] `{command}` passes
  - [A] `{command}` passes

### [ ] TODO 2: {title}
- Dependencies: TODO-1
- Acceptance Criteria:
  - [A] `{command}` passes
```

**Simplified PLAN.md rules:**
- NO Pivot Points section (PP interview skipped)
- NO S-items or H-items (A-items only — agent-verifiable)
- NO separate Test Strategy section (criteria are inline)
- NO Dependency Graph section
- NO per-TODO risk rating (only overall)
- Research Note section is optional — only when light research produced relevant findings

### Step 3: HITL (Human-in-the-Loop)

```
AskUserQuestion: "이 계획으로 진행할까요?"
Options:
  1. "진행" → Update state: small-sprint, plan_approved: true
  2. "수정 필요" → Incorporate feedback, regenerate PLAN.md
Timeout: 30 seconds → Auto-select option 1
```

---

## Phase 2: Small Sprint

### Step 1: Parse PLAN.md

- Parse `### [ ] TODO N:` entries
- Extract Dependencies fields
- Identify non-blocking TODOs

### Step 2: Parallel Dispatch

For each non-blocking TODO, launch the appropriate worker in a SINGLE message:

```
# Backend / general TODO → uam-worker
Task(subagent_type="uam-worker", model="sonnet",
     prompt="Implement TODO-N: {title}\n\nDescription: {description}\n\nAcceptance Criteria:\n{criteria}\n\nIMPORTANT: Return structured JSON output matching the Output_Schema.")

# Frontend / UI TODO → uam-frontend
Task(subagent_type="uam-frontend", model="sonnet",
     prompt="Implement TODO-N: {title}\n\nDescription: {description}\n\nAcceptance Criteria:\n{criteria}\n\nIMPORTANT: Return structured JSON output matching the Output_Schema.")
```

Worker selection:
- UI/component/CSS/layout keywords → `uam-frontend`
- API/logic/DB/infra → `uam-worker`

### Step 3: Verify Each Worker Output

After each worker completes:
1. **Validate JSON schema** (todo_id, status, outputs, acceptance_criteria)
2. **Re-run acceptance criteria commands** independently via Bash
3. ALL pass → commit via `uam-git-master`, update PLAN.md `[x]`
4. Any fail → retry (max 3 attempts)

**No Discovery processing** in small mode (no Pivot Points → no conflict checks).

### Step 4: Completion Check

All TODOs resolved → State transitions to `small-verify` (Stop hook handles this)

---

## Phase 3: Small Verify

### Single Code Review

Run one code-reviewer pass (no multi-model, no Gate 1 docker tests, no Gate 3 agent-as-user):

```
Task(subagent_type="uam-code-reviewer", model="sonnet",
     prompt="Review all changes since sprint start. Focus on: correctness, side effects, hidden bugs, and production readiness. Keep review concise.")
```

### Verdict

- **SHIP** (critical=0) → Gate 2 PASS
  - Update state: `gate_results.gate2_passed = true`
  - Proceed to finalization
- **NEEDS_FIXES** (critical>0) → Gate 2 FAIL
  - Update state: `gate_results.gate2_passed = false`
  - Stop hook handles retry logic (back to `small-sprint`, max 3 retries)

### Finalization (on pass)

1. **Extract learnings** → `docs/learnings/{feature}/learnings.md` only
   - No decisions.md, issues.md, metrics.md (simplified)
2. **Atomic commit** via `uam-git-master`
3. **Completion report**:
   - TODOs completed/failed
   - Code review verdict
   - Fix loop iterations used (if any)
   - Key learnings

Update state → `completed`

---

## Differences from Full Pipeline

| Aspect | Full (`uam`) | Small (`uam-small`) |
|--------|-------------|---------------------|
| Phases | 5 (plan → sprint → gate → fix → finalize) | 3 (plan → sprint → verify) |
| Planning agents | 4-6 parallel | 2 parallel (explore + pm) |
| PM model | opus | sonnet |
| Quality gates | 3 (docker + review + agent-as-user) | 1 (code review only) |
| Fix strategy | Adaptive 3-tier + ConvergenceDetector | Simple retry max 3 |
| Max fix loops | 10 | 3 |
| Token budget | 500K | 150K |
| Pivot Points | Full interview | Skipped |
| Learnings | 4 files | 1 file (learnings.md only) |
| Model escalation | Dynamic (sonnet → opus) | Fixed (no escalation) |
| A/S/H items | All three | A-items only |

---
description: UAM 5-Phase Pipeline full orchestration protocol
---

# UAM Orchestration Protocol

You are now operating as the UAM orchestrator. Follow this protocol exactly.

## Core Rules (HARD ENFORCEMENT)

1. **You NEVER write source code directly.** All code changes go through `uam-worker` agents via Task tool.
2. **PLAN.md checkboxes are SSOT.** Only update checkboxes when Worker + Verify both pass.
3. **Validate agent output.** Check Output_Schema sections after every validate_prompt agent completes.
4. **Respect phase gates.** Do not skip phases or bypass quality gates.

## State Management

State file: `.uam/state.json`
- Read state to determine current phase
- Update state at phase transitions
- Track fix_loop_count, gate_results, convergence data

## Model Routing Guide (Dynamic Escalation)

에이전트 파일의 `model:`은 기본값이다. 오케스트레이터는 Task 호출 시 `model` 파라미터로 상향 가능하다.

| 조건 | 기본 모델 | 상향 모델 | 기준 |
|------|----------|----------|------|
| 단순한 요구사항, 파일 5개 미만 | sonnet | — | 그대로 사용 |
| 모호한 요구사항, 다중 이해관계자 | sonnet | **opus** | pm, tradeoff-analyzer |
| 아키텍처 변경, 모듈 경계 재설계 | sonnet | **opus** | tradeoff-analyzer, designer |
| 복잡한 디버깅, 3회 이상 반복 실패 | sonnet | **opus** | debugger |
| 대규모 리팩토링 (20+ 파일) | sonnet | **opus** | worker, code-reviewer |

**Phase별 권장 상향 시점**:
- Phase 1: 요구사항이 모호하거나 시스템 전체에 영향 → pm, tradeoff-analyzer를 opus로
- Phase 2: TODO 복잡도가 L(Large)이고 아키텍처 변경 포함 → worker를 opus로
- Phase 3: 보안/API 호환성이 중요한 리뷰 → code-reviewer를 opus로
- Phase 4: 3회 반복 실패 (stagnation) → debugger를 opus로 상향

---

## Phase 0: Pivot Points (Pre-Planning)

Before Phase 1, establish Pivot Points — immutable constraints that discoveries must never violate.

### Step 1: Check for Existing PPs

```
if `.uam/pivot-points.md` exists → load PPs and proceed to Phase 1
if not exists → run PP interview (Step 2)
if maturity_mode = "explore" → PP is optional, skip if user declines
```

### Step 2: PP Interview (if needed)

```
AskUserQuestion: "프로젝트의 핵심 제약사항(Pivot Points)을 정의할까요?"
Options:
  1. "인터뷰 시작" → Run `/uam:uam-pivot` interview
  2. "건너뛰기" → Proceed without PPs (explore mode only)
  3. "기존 PP 로드" → Read from `.uam/pivot-points.md`
```

### PP States

- **CONFIRMED**: Hard constraint. Discovery 충돌 시 자동 반려.
- **PROVISIONAL**: Soft constraint. Discovery 충돌 시 HITL로 판단 요청.

### Maturity Modes

| 모드 | PP 필수 | Discovery 처리 | 적합한 시점 |
|------|---------|---------------|------------|
| `explore` | 선택 | 즉시 PLAN.md 수정 | 초기 탐색/프로토타입 |
| `standard` | 필수 | Phase 전환 시 일괄 검토 | 일반 개발 |
| `strict` | 필수 + 강제 | 다음 사이클 백로그로 이관 | 안정화/릴리스 |

State에 `maturity_mode` 기록: `.uam/state.json`

---

## Phase 1-A: Deep Research

### Skip Conditions

Research can be skipped when ALL of these are true:
- 기존 코드베이스 패턴만 사용 (새 라이브러리/기술 불필요)
- 구현 방법이 명확하고 검증됨
- 외부 라이브러리 도입 불필요

스킵 시: `writeState(cwd, { research: { status: 'skipped' }, current_phase: 'phase1b-plan' })`

### Token Budget Guard (Heuristic)

연구 토큰 상한 목표: 전체 예산의 20% (full: ~100K tokens)

> **주의**: `cost.total_tokens`는 자동 추적되지 않는다. 오케스트레이터가 각 Stage 완료 후
> 에이전트 응답 길이를 근사 토큰으로 환산(1 token ≈ 4 chars)하여 수동 업데이트해야 한다.
> `writeState(cwd, { cost: { total_tokens: estimated } })`

```
Stage 완료 시마다 오케스트레이터가 cost.total_tokens를 갱신한 후 확인:
- Stage 1 완료 후 > 15% 사용: Stage 2를 TOP 2로 축소 (3→2)
- Stage 2 완료 후 > 18% 사용: Stage 3를 간략 모드로 전환 (full schema → brief schema)
- 언제든 > 20% 도달: 즉시 현재 Stage 결과로 종합 → Phase 1-B 전환

토큰 추적이 불가능한 환경에서는 Stage 수로 제한:
- 3 Stage 모두 실행하되, Stage 2 deep-dive 대상을 TOP 2로 제한 (3→2)
```

### Step 1: Broad Scan (병렬)

```
writeState(cwd, { research: { status: 'stage1', started_at: new Date().toISOString() } })

# 병렬 실행
Task(subagent_type="uam-explore", model="haiku",
     prompt="Explore the codebase for: {user request}. Map structure, patterns, test infrastructure.")

Task(subagent_type="uam-researcher", model="sonnet",
     prompt="Stage 1 Broad Scan for: {user request}. Follow Stage 1 protocol. Run 3-5 WebSearch queries + codebase Grep/Glob. Select TOP 3 findings for deep-dive. Output Stage 1 schema.")
```

기존 `.uam/research/` 보고서가 있으면 researcher에게 컨텍스트로 전달:
```
"기존 연구 보고서가 있습니다: {file list}. 이미 조사된 내용은 건너뛰고 새로운 발견에 집중하세요."
```

Stage 1 완료 시 중간 결과 캐싱:
```
# .uam/research/stage1-cache.md에 Stage 1 결과 저장
writeState(cwd, { research: { stages_completed: ['stage1'] } })
```

### Step 2: Deep-Dive (순차)

Stage 1의 TOP 3 findings에 대해 심층 조사:

```
writeState(cwd, { research: { status: 'stage2' } })

Task(subagent_type="uam-researcher", model="sonnet",
     prompt="Stage 2 Deep-Dive for: {user request}.
     TOP findings from Stage 1:
     1. {finding 1} -- Rationale: {why}
     2. {finding 2} -- Rationale: {why}
     3. {finding 3} -- Rationale: {why}

     Follow Stage 2 protocol. WebFetch official docs for each finding. Assess compatibility, maintenance, extract code examples. Output Stage 2 schema.")
```

Stage 2 실패 처리:
- 특정 URL WebFetch 실패 → 해당 Finding만 `[FETCH_FAILED]` 마킹, 나머지 진행
- 3개 전부 실패 → Stage 2를 `degraded`로 기록: `writeState(cwd, { research: { degraded_stages: ['stage2'] } })`
- Researcher 에이전트 자체 오류 → 1회 재시도. 재실패 시 `research.status = 'skipped'`, Phase 1-B로 즉시 전환

Stage 2 완료 시 캐싱:
```
# .uam/research/stage2-cache.md에 Stage 2 결과 저장
writeState(cwd, { research: { stages_completed: ['stage1', 'stage2'] } })
```

### Step 3: Synthesis

Stage 1 + Stage 2 출력을 종합하여 보고서 생성:

```
writeState(cwd, { research: { status: 'stage3' } })

Task(subagent_type="uam-research-synthesizer", model="sonnet",
     prompt="Synthesize research for: {user request}.

     Stage 1 Results:
     {stage1 output}

     Stage 2 Results:
     {stage2 output}

     Pivot Points (if defined):
     {pivot points from .uam/pivot-points.md}

     Existing research (if any):
     {list of .uam/research/ files}

     Follow the full report Output_Schema. Generate comprehensive synthesis.")
```

Stage 3 완료 후 오케스트레이터가 `.uam/research/report.md`에 결과 작성.

**품질 체크** (Stage 3 완료 후):
```
필수 섹션 존재 확인:
- Executive Summary 비어 있음 → 재시도 1회
- Recommendations 0개 → 재시도 1회
- 모든 Recommendation confidence가 LOW → HITL:
  AskUserQuestion: "연구 결과 확신도가 낮습니다. 어떻게 하시겠습니까?"
  Options: "진행" | "재조사" | "연구 스킵"
- Sources 0개 → degraded 마킹 (근거 없는 연구)

재시도 후에도 품질 미달 → research.degraded_stages에 'stage3' 추가
→ Phase 1-B에서 PM이 연구 결과를 참고용으로만 사용
```

상태 업데이트:
```
writeState(cwd, {
  research: {
    status: 'completed',
    completed_at: new Date().toISOString(),
    stages_completed: ['stage1', 'stage2', 'stage3'],
    report_path: '.uam/research/report.md',
    findings_count: {count from report},
    sources_count: {count from report}
  },
  current_phase: 'phase1b-plan'
})
```

Stage 캐시 파일 정리 (report.md만 유지):
```
Bash: rm -f .uam/research/stage1-cache.md .uam/research/stage2-cache.md
```

---

## Phase 1-B: Plan Generation

### Step 1: Parallel Exploration (5+ agents simultaneously)

Launch agents in a SINGLE message (parallel). 모든 에이전트가 연구 보고서를 **명시적 입력**으로 수신한다.

```
# 필수 (항상 호출) — 연구 결과를 명시적으로 전달
Task(subagent_type="uam-gap-analyzer", model="haiku",
     prompt="Analyze gaps for: {user request}. Identify missing requirements, AI pitfalls, Must NOT Do.

     Research context (executive summary + recommendations):
     {research executive summary}
     {research recommendations}")

Task(subagent_type="uam-pm", model="opus",
     prompt="Refine requirements for: {user request}. Write user stories, acceptance criteria, MoSCoW priority, scope boundaries.

     Research report (full):
     {contents of .uam/research/report.md}")

Task(subagent_type="uam-verification-planner", model="sonnet",
     prompt="Plan verification for: {user request}. Classify acceptance criteria as A/S/H items.

     Research context (anti-patterns & risks):
     {research anti-patterns and risks section}")

# 선택적 (해당 시 호출)
Task(subagent_type="uam-designer", model="sonnet",
     prompt="Design UI/UX for: {user request}. Component hierarchy, interaction flows, accessibility requirements, responsive behavior.

     Research context (implementation guidance):
     {research implementation guidance section}")
```

호출 기준:
- `uam-designer`: UI/프론트엔드 작업이 포함된 경우
- `uam-pm`: 기본 opus. 단순한 요구사항이면 `model="sonnet"`으로 하향 가능
- 연구가 skipped인 경우: `uam-explore`를 추가 호출 (Phase 1-A에서 이미 실행했으면 생략)

### Step 2: Tradeoff Analysis

After Step 1 completes:

```
Task(subagent_type="uam-tradeoff-analyzer", model="sonnet",
     prompt="Assess risks for: {user request}. Rate each change LOW/MED/HIGH with reversibility.

     Research context (risks + anti-patterns):
     {research risks and anti-patterns section}")
```

Note: 아키텍처 변경이 포함되면 `model="opus"`로 상향한다.

### Step 3: Generate PLAN.md

Using all agent outputs + research report, create `.uam/PLAN.md` with this structure:

```markdown
# PLAN: {feature-name}

## Pivot Points (from .uam/pivot-points.md)
### PP-1: {title} [{CONFIRMED|PROVISIONAL}]
- Principle: {immutable constraint}
- Judgment: {violation condition}
### PP-2: ...
Priority: PP-1 > PP-2

## Research Findings
- Report: `.uam/research/report.md`
- Key recommendation: {top recommendation from synthesis}
- Chosen approach: {selected option + rationale for selection}
- Risks to monitor: {top 2-3 risks from research}
- References: {key URLs for Workers to consult}

## Summary
{1-2 sentence summary}

## Risk Assessment
- Overall: {LOW|MED|HIGH}
- Irreversible changes: {details}

## TODOs

### [ ] TODO 1: {title}
- Description: {detailed description}
- Dependencies: none
- Risk: {LOW|MED|HIGH}
- Estimated complexity: {S|M|L}
- **Research context**: {relevant findings/recommendations for this TODO}
- Acceptance Criteria:
  - [A] `{command}` passes
  - [S] {scenario description}
  - [H] {human verification item}

### [ ] TODO 2: {title}
- Dependencies: TODO-1
- **Research context**: {relevant research for this TODO}
- ...

## Test Strategy
### A-items (Agent-Verifiable)
{list from verification-planner}

### S-items (Sandbox Agent Testing)
{list from verification-planner}

### H-items (Human-Required)
{list from verification-planner}

## Dependency Graph
{TODO dependency DAG}
```

### Step 4: Plan-Research Consistency Check

PLAN.md 생성 후 오케스트레이터 검증:

1. Research Findings의 "Chosen approach"와 TODO 구현 방향 비교
2. 불일치 감지 시 → PLAN.md의 Research Findings 섹션에 "⚠ Deviation" 마킹
3. HITL에서 사용자에게 불일치 사유 표시:
   "연구는 Option A를 권장했으나, PM은 Option B를 선택했습니다. 사유: {PM의 rationale}"
4. 사용자 판단에 위임 (연구는 권고일 뿐, 최종 결정은 사용자)

### Step 5: HITL (Human-in-the-Loop)

```
AskUserQuestion: "이 계획으로 진행할까요?"
Options:
  1. "진행" → Update state: phase2-sprint, plan_approved: true
  2. "수정 필요" → Incorporate feedback, regenerate PLAN.md
  3. "재계획" → Restart Phase 1-B (연구 유지, Plan만 재생성)
  4. "연구부터 재시작" → Restart Phase 1-A (report.md → report-prev.md 백업)
Timeout: 30 seconds → Auto-select option 1
```

### HITL (Human-in-the-Loop) Timeout Protocol

Pivot Points 평가 등 사용자 입력이 필요한 단계에서:

1. `AskUserQuestion` 도구로 질문 제시
2. **30초 내 응답 없으면** 기본값으로 자동 진행:
   - Pivot Point 충돌 판정 → PROVISIONAL PP는 "허용" (진행 우선)
   - Discovery 승인 → "보류" (안전한 기본값)
   - 스코프 질문 → 최소 스코프 (MVP 원칙)
3. 타임아웃 발생 시 로그에 `[HITL-TIMEOUT]` 기록
4. 사용자가 나중에 재검토할 수 있도록 결정 사항을 `decisions.md`에 기록

> 실제 timeout 구현은 오케스트레이터 레벨의 prompt instruction이다.
> Hook이나 시스템 타이머가 아닌, 오케스트레이터가 "30초 대기 후 기본값 진행" 프로토콜을 따른다.

---

## Phase 2: MVP Sprint

### Step 1: Parse PLAN.md and Build Dependency Graph

- Parse `### [ ] TODO N:` entries
- Extract Dependencies fields
- Identify non-blocking TODOs (dependencies: none or all predecessors completed)

### Step 2: Parallel Dispatch

For each non-blocking TODO, launch the appropriate worker:

```
# Backend / general TODO → uam-worker
Task(subagent_type="uam-worker", model="sonnet",
     prompt="Implement TODO-N: {title}\n\nDescription: {description}\n\nAcceptance Criteria:\n{criteria}\n\nIMPORTANT: Return structured JSON output matching the Output_Schema.")

# Frontend / UI / component TODO → uam-frontend
Task(subagent_type="uam-frontend", model="sonnet",
     prompt="Implement TODO-N: {title}\n\nDescription: {description}\n\nDesign Spec: {designer output if available}\n\nAcceptance Criteria:\n{criteria}\n\nIMPORTANT: Return structured JSON output matching the Output_Schema. Follow the Frontend Checklist.")
```

Worker 선택 기준:
- TODO에 UI/컴포넌트/CSS/레이아웃/접근성 키워드 → `uam-frontend`
- 그 외 (API, 로직, DB, 인프라) → `uam-worker`
- TODO 복잡도가 L(Large) + 아키텍처 변경 → `model="opus"` 상향

Launch multiple workers in a SINGLE message for parallel execution.

### Step 3: Verify Each Worker Output + Process Discoveries

After each worker completes:
1. **Validate JSON schema** (todo_id, status, outputs, acceptance_criteria, discoveries fields)
2. **Re-run acceptance criteria commands independently** (Verify Worker pattern)
   - Run each `acceptance_criteria[].command` via Bash
   - Compare actual exit code with expected
3. If ALL pass: commit via `uam-git-master`, update PLAN.md checkbox to `[x]`
4. If any fail: retry (max 3 attempts with DAG append-only)

**Discovery Processing** (if worker output contains `discoveries`):

Worker/Frontend가 구현 중 더 나은 접근법을 발견하면 `discoveries` 필드로 제안한다.

1. Append to `.uam/discoveries.md` (기록 보존)
2. Check each discovery against Pivot Points:
   - **CONFIRMED PP 충돌** → 자동 반려 (사유를 discoveries.md에 기록)
   - **PROVISIONAL PP 충돌** → HITL로 판단 요청:
     ```
     AskUserQuestion: "Discovery D-{N}이 PP-{M}과 충돌합니다. 어떻게 처리할까요?"
     Options:
       1. "반려" → Discovery 무시
       2. "수용" → PP를 PROVISIONAL→해제, Discovery 반영
       3. "보류" → 백로그로 이관
     ```
   - **PP 충돌 없음** → maturity_mode에 따라 처리:

| maturity_mode | 처리 방식 |
|---------------|----------|
| `explore` | 즉시 PLAN.md TODO 수정 (빠른 반영) |
| `standard` | Phase 2→3 전환 시 일괄 검토 |
| `strict` | 다음 사이클 백로그로 이관 |

### Step 4: Completion Check

When all TODOs are resolved → State transitions to phase3-gate (Stop hook handles this)

---

## Phase 3: Quality Gate

### Gate 1: Automated Tests (A-items)

Run ALL A-items from PLAN.md Test Strategy section:
```bash
# Fast-Fail order: Unit → Integration → E2E
# Stop at first tier failure
```

### Gate 1 Test Execution Strategy

테스트 실행은 다음 우선순위로 시도한다:

1. **Docker 사용 가능** → Docker 컨테이너 내 pytest/test runner 실행 (격리 보장)
2. **Docker 미설치/미실행** → Native test runner 자동 감지:
   - `package.json` 존재 → `npm test`
   - `pytest.ini` / `pyproject.toml` [tool.pytest] → `pytest`
   - `Cargo.toml` → `cargo test`
   - `go.mod` → `go test ./...`
3. **Test runner 미발견** → Gate 1 = **SKIPPED** (PASS가 아님)
   - SKIPPED 상태는 Gate 2 (code review)에서 테스트 커버리지 부족을 별도 플래그

> ⚠️ SKIPPED ≠ PASS. Gate 1이 SKIPPED이면 Gate 2 리뷰어에게 "테스트 미실행" 컨텍스트를 전달한다.

**Judge Logic** (orchestrator-internal, not an agent):
- Parse test output: extract pass/fail counts
- 100% A-items pass → Gate 1 PASS
- Any failure → Gate 1 FAIL + generate structured failure summary (500 chars max):
  ```
  Gate 1 Results: {passed}/{total} passed ({pct}%)
  Failed tests:
    - {test_name}: {error_type} — {brief description}
  Error categories: {type}({count}), ...
  ```

Update state: `gate_results.gate1_passed = true|false`

### Gate 2: Multi-Model Code Review

```
Task(subagent_type="uam-code-reviewer", model="sonnet",
     prompt="Review all changes since sprint start. Cover all 8 categories. Attempt multi-model review with Codex and Gemini CLIs.")
```

**Verdict mapping**:
- SHIP (critical=0, warning<=2) → Gate 2 PASS
- NEEDS_FIXES → Gate 2 FAIL

Update state: `gate_results.gate2_passed = true|false`

### Gate 3: Agent-as-User (optional, only if S-items exist)

If PLAN.md has S-items:
- Run BDD scenarios using agent personas
- Each scenario 3-5 times, 80%+ pass required

If no S-items: auto-PASS Gate 3.

### Gate 3: Agent-as-User Evaluation Protocol

Gate 3는 S-items (Subjective/UX 항목)이 verification plan에 존재할 때만 실행한다.

**실행 조건:** `verification_plan.items`에 `category: "S"` 항목이 1개 이상

**평가자:** `uam-designer` agent를 "사용자 관점 평가자"로 활용

**체크리스트:**
- [ ] **접근성 (Accessibility)**: 키보드 내비게이션, 스크린리더 호환, 색상 대비
- [ ] **에러 핸들링 UX**: 에러 메시지 명확성, 복구 경로 제공
- [ ] **반응형 (Responsive)**: 모바일/태블릿/데스크톱 뷰포트
- [ ] **로딩 상태**: 비동기 작업 시 피드백 (스피너, 스켈레톤, progress)
- [ ] **사용자 플로우 일관성**: 기대 동작과 실제 동작 일치

**판정 기준:**
- PASS: 모든 해당 체크리스트 통과
- FAIL: 1개 이상 critical issue 발견
- SKIPPED: S-items 없음 (자동 PASS 아님, Gate 3 N/A로 기록)

Update state: `gate_results.gate3_passed = true|false`

---

## Phase 4: Fix Loop

### Failure Classification

| Pattern | Strategy | Action |
|---------|----------|--------|
| 1-2 test failures, new errors | Simple fix | Worker targeted fix, re-verify |
| Same error 3x consecutive | Session reset | New approach, structured failure summary |
| >50% failures OR 10%+ pass rate drop | Circuit breaker | Phase 1 re-plan |

### ConvergenceDetector Logic

After each fix iteration:
```
pass_rate_history.push(current_pass_rate)
recent_3 = pass_rate_history.slice(-3)

if (recent_3 variance < 5%) → Stagnation → Session reset strategy
if (current - previous < -10%) → Regression → Circuit breaker
if (improving) → Continue
```

### HITL Direction Check (every loop)

```
AskUserQuestion: "{N}번째 수정 루프. 테스트 통과율 {X}%. 계속 진행할까요?"
Options:
  1. "계속" → Continue fix loop
  2. "방향 변경" → Phase 1 re-plan
  3. "현재 상태로 종료" → Phase 5 (partial)
Timeout: 30 seconds → Auto-select option 1
```

Increment state: `fix_loop_count += 1`

After fix: re-run Phase 3 gates (state → phase3-gate)

---

## Phase 5: Finalize

### Step 1: Extract Learnings

Create `docs/learnings/{feature-name}/`:
- `learnings.md` — Patterns and conventions discovered
- `decisions.md` — Design decisions with rationale
- `issues.md` — Unresolved problems
- `metrics.md` — Pass rates, iteration counts, token usage

### Step 2: Update Project Memory

If project-memory tools available:
```
project_memory_add_note(category="architecture", content="...")
project_memory_add_note(category="patterns", content="...")
```

### Step 3: Atomic Commits

```
Task(subagent_type="uam-git-master", model="sonnet",
     prompt="Create atomic commits for all changes. Detect project commit style. 3+ files → 2+ commits.")
```

### Step 4: Completion Report

Summarize:
- TODOs completed vs failed
- Gate pass rates
- Fix loop iterations used
- Key learnings
- Remaining issues (if any)

Update state: `current_phase = "completed"`

# MPL 설계 보완: Compaction Resilience & Error Context 보존

> **기반**: Planning Phase Compaction 실험 (2026-03-12)
> **대상**: MPL v3.2 → v3.3 설계 반영
> **상태**: 제안

---

## 실험 결과 요약

### 발견된 3가지 구조적 취약점

| # | 취약점 | 발견 경위 | 영향 |
|---|--------|----------|------|
| 1 | **Error 전문이 compaction으로 왜곡됨** | fix loop에서 에러 메시지가 compaction summary에 의해 축약/변형 → 잘못된 수정 방향 유도 | pass_rate 수렴 실패 |
| 2 | **Phase 전환 시 compaction이 이전 분석 결과를 손실** | Planning 10라운드에서 compaction 4회 발생, 5회째 실패 | 세션 교착 |
| 3 | **불필요한 docs 재로드** | subagent context가 살아있는데도 매번 memory docs를 로드 | 토큰 낭비 + 컨텍스트 오염 |

### 실험 데이터

```
Worker 구현 (subagent 위임):  compaction 0회, ctx 21%
Planning 대화 (직접 수행):    compaction 4회 + 실패 1회
파일 외부화 후 정보 보존:     높음 (probe 2/2 정확)
터미널 출력만 후 정보 보존:   측정 전 세션 교착
Compaction 실패 시점:         4회 누적 후, ctx 77%에서 auto compact 실패
```

---

## 보완 설계: 3개 Feature

### F-30: Error Context File Preservation

#### 문제

현재 MPL의 에러 처리 흐름:
```
Worker 실패 → error message를 orchestrator에 텍스트로 반환
→ orchestrator 컨텍스트에 에러 메시지 누적
→ compaction 발생 시 에러 메시지가 요약/변형됨
→ 다음 fix loop에서 왜곡된 에러 정보로 수정 시도
→ 엉뚱한 방향으로 fix → pass_rate 미수렴
```

#### 해결

```
Worker 실패 → error 전문을 파일로 저장
→ orchestrator는 파일 경로만 수신
→ compaction이 발생해도 파일은 그대로
→ 다음 fix loop에서 파일을 Read하여 정확한 에러 확인
→ QMD가 에러 파일을 읽어 정밀 진단
```

#### 구현

**파일 구조**:
```
.mpl/mpl/phases/phase-N/
├── state-summary.md        # (기존) 성공 시 요약
├── errors/                  # (신규) 실패 시 에러 보존
│   ├── todo-1-error.md      # TODO별 에러 전문
│   ├── todo-2-error.md
│   └── gate-1-error.md      # Gate 실패 시 에러 전문
```

**에러 파일 포맷** (`todo-N-error.md`):
```markdown
# Error: {todo_name}
- **Phase**: {phase_name}
- **Attempt**: {attempt_number}/3
- **Timestamp**: {ISO timestamp}
- **Pass Rate**: {pass_rate}%

## Error Output (전문)
\`\`\`
{test_runner_output_verbatim}
\`\`\`

## Failed Tests
| Test | Error Type | Message |
|------|-----------|---------|
| {test_name} | {error_type} | {error_message} |

## Context
- **Modified Files**: {files_changed}
- **Last Edit Summary**: {what_was_changed}
```

**Phase Runner 변경** (`mpl-phase-runner.md`):
```
기존 (Step 5: Report):
  circuit_break 시 failure_info를 텍스트로 반환

변경:
  Step 5-A: 실패 시 에러 전문을 .mpl/mpl/phases/phase-N/errors/todo-{n}-error.md에 Write
  Step 5-B: orchestrator에는 파일 경로 + 1줄 요약만 반환
  Step 5-C: QMD 연동 시 에러 파일 경로를 QMD context로 전달
```

**QMD 연동**:
```
Fix Loop 진입 시:
  1. .mpl/mpl/phases/phase-N/errors/ 디렉토리 확인
  2. 에러 파일이 있으면 QMD에 경로 전달
  3. QMD가 에러 전문을 읽고 근본 원인 분석
  4. QMD 진단 결과를 fix 전략으로 활용
```

**Subagent context 분기**:
```
Worker 실패 후:
  IF worker가 subagent로 실행되어 context가 살아있음:
    → 에러 파일 Write 생략 (context에 에러 전문이 그대로 있음)
    → 즉시 retry 가능
  IF compaction 발생했거나 새 session:
    → 에러 파일 Read하여 정확한 에러 복원
    → QMD 연동으로 진단 후 retry
```

---

### F-31: Compaction-Aware Context Recovery

#### 문제

현재 MPL의 compaction 처리:
```
PreCompact 훅 → compaction_count 증가 → 끝
→ compaction 후 orchestrator는 이전 분석 결과를 잃을 수 있음
→ 특히 planning phase에서 spec 분석, 의존관계 파악 등이 손실
→ 동일한 파일을 다시 읽는 비효율 또는 불완전한 정보로 판단
```

#### 해결

```
PreCompact 훅 → compaction_count 증가
  + memory checkpoint 생성 (현재 작업 상태 스냅샷)
SessionStart(source="compact") 훅
  → checkpoint에서 작업 상태 복원
  → 필요한 memory docs만 선택적 로드
```

#### 구현

**Memory Checkpoint** (PreCompact 시점):
```
.mpl/mpl/checkpoints/
├── compaction-1.md     # 1차 compaction 시점의 작업 상태
├── compaction-2.md     # 2차
└── compaction-N.md
```

**Checkpoint 포맷**:
```markdown
# Compaction Checkpoint #{N}
- **Timestamp**: {ISO}
- **Current Phase**: {phase_name}
- **Active TODO**: {todo_name or "planning"}
- **Context Usage**: {ctx_pct}%

## Working State
- **What was being done**: {current_task_description}
- **Files being analyzed**: {file_list}
- **Key findings so far**: {bullet_list}

## Recovery Instructions
- Read: {files_to_reload}
- Resume: {next_action}
```

**PreCompact 훅 변경** (`mpl-compaction-tracker.mjs`):
```javascript
// 기존: compaction_count만 증가
// 변경: checkpoint 파일도 생성

const checkpoint = {
  compaction_number: newCount,
  timestamp: new Date().toISOString(),
  current_phase: state.current_phase,
  // context에서 추출 가능한 상태 정보
};

// checkpoint 파일 Write
const checkpointPath = `.mpl/mpl/checkpoints/compaction-${newCount}.md`;
fs.writeFileSync(checkpointPath, formatCheckpoint(checkpoint));
```

**Compaction 횟수 기반 세션 전략**:
```
compaction_count 0-2:  정상 진행
compaction_count 3:    경고 — "세션 분할 권장"
compaction_count 4+:   자동 세션 리셋 + checkpoint에서 복원
```

---

### F-32: Adaptive Context Loading (Smart Docs Reload)

#### 문제

현재 phase 전환 시 항상 동일한 context assembly:
```
prev_summary + dependency_summaries + phase0_artifacts + learnings
→ subagent context가 살아있어도 전부 다시 로드
→ 토큰 낭비 + 컨텍스트 오염 가능
```

#### 해결

Context 상태를 판단하여 로드량을 조절:

```
IF 동일 세션 내 phase 전환 (compaction 없음):
  → prev_summary만 로드 (이전 분석이 context에 남아있음)
  → dependency_summaries, phase0_artifacts 스킵

IF compaction 발생 후 phase 전환:
  → 전체 context assembly 수행
  → checkpoint에서 추가 컨텍스트 복원

IF 새 세션에서 resume:
  → 전체 context assembly + RUNBOOK.md + learnings.md
```

#### 구현

**Context Assembly 분기** (`mpl-run-execute.md` Step 4.1 수정):
```python
def assemble_phase_context(phase, state):
    context = {}

    # 항상 로드 (경량)
    context["phase_def"] = read_decomposition(phase)
    context["phase_decisions"] = read_phase_decisions(tiered=True)

    # Compaction 감지
    compaction_since_last_phase = (
        state.compaction_count > state.last_phase_compaction_count
    )
    is_new_session = state.session_id != previous_session_id

    if is_new_session:
        # 새 세션: 전체 로드
        context["prev_summary"] = read_state_summary(phase - 1)
        context["dep_summaries"] = load_dependency_summaries(phase)
        context["phase0_artifacts"] = load_phase0_artifacts(grade)
        context["learnings"] = read_learnings()
        context["runbook_tail"] = read_runbook(last_n=20)
        context["errors"] = load_error_files(phase)  # F-30

    elif compaction_since_last_phase:
        # Compaction 발생: 선택적 로드
        context["prev_summary"] = read_state_summary(phase - 1)
        context["dep_summaries"] = load_dependency_summaries(phase)
        context["checkpoint"] = read_latest_checkpoint()  # F-31
        context["errors"] = load_error_files(phase)  # F-30
        # phase0_artifacts는 필요 시에만 (Complex grade만)
        if grade == "Complex":
            context["phase0_artifacts"] = load_phase0_artifacts(grade)

    else:
        # 동일 세션, compaction 없음: 최소 로드
        context["prev_summary"] = read_state_summary(phase - 1)
        # 나머지는 context에 이미 있으므로 스킵

    # state 갱신
    state.last_phase_compaction_count = state.compaction_count

    return context
```

**state.json 확장**:
```json
{
  "compaction_count": 4,
  "last_phase_compaction_count": 2,
  "session_id": "abc123",
  "context_load_mode": "minimal"
}
```

---

## 통합: 전체 흐름

```
Phase N 실행 시작
│
├─ Context Assembly (F-32)
│   ├─ 동일 세션, compaction 없음 → 최소 로드
│   ├─ Compaction 발생 후 → 선택적 로드 + checkpoint
│   └─ 새 세션 → 전체 로드
│
├─ Phase Runner (Worker) 실행
│   ├─ 성공 → state-summary.md 생성
│   └─ 실패 → error 전문 파일 저장 (F-30)
│       ├─ subagent context 살아있음 → 즉시 retry
│       └─ compaction 발생 → error 파일 Read + QMD 진단
│
├─ Compaction 감지 (F-31)
│   ├─ PreCompact → checkpoint 생성
│   ├─ count 3 → 세션 분할 경고
│   └─ count 4+ → 자동 세션 리셋 + 복원
│
└─ Phase 전환
    ├─ state-summary.md 저장 (기존)
    ├─ <remember priority> 태그 (기존)
    ├─ error 파일 보존 (F-30, 신규)
    └─ compaction_count 기록 (F-31, 신규)
```

---

## 기존 MPL 구조와의 호환성

| 기존 메커니즘 | 변경 사항 | 호환성 |
|-------------|----------|--------|
| state-summary.md | 변경 없음 | 완전 호환 |
| Phase Decisions 3-Tier | 변경 없음 | 완전 호환 |
| learnings.md | 변경 없음 | 완전 호환 |
| RUNBOOK.md | 변경 없음 | 완전 호환 |
| `<remember priority>` 태그 | 변경 없음 | 완전 호환 |
| PreCompact 훅 | **확장** — checkpoint 생성 추가 | 하위 호환 |
| Phase Runner 에러 보고 | **확장** — 파일 Write 추가 | 하위 호환 |
| Context Assembly (Step 4.1) | **확장** — 3-way 분기 추가 | 하위 호환 |
| state.json | **확장** — 2개 필드 추가 | 하위 호환 |

모든 변경이 기존 동작을 유지하면서 확장하는 형태이므로 **breaking change 없음**.

---

## 우선순위

| 순위 | Feature | 구현 난이도 | 영향도 | 이유 |
|------|---------|-----------|--------|------|
| **P0** | F-30: Error File Preservation | 낮음 | 높음 | fix loop 수렴율 직접 개선. 구현이 간단 (Write 1줄 추가) |
| **P1** | F-32: Adaptive Context Loading | 중간 | 중간 | 토큰 절약 + 컨텍스트 품질. Step 4.1에 분기 추가 |
| **P2** | F-31: Compaction Checkpoint | 중간 | 낮음 | Planning 전용 시나리오에서만 해당. 일반 MPL 실행에서는 compaction 자체가 드묾 |

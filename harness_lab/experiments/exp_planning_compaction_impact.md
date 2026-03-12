# 실험: Planning Phase 컨텍스트 누적과 Compaction 영향

> **목표**: MPL 오케스트레이터의 계획 수립 과정에서 컴팩션이 발생하는 조건과, 컴팩션 후 계획/실행 품질 저하를 측정한다.

## 배경

### 이전 실험 발견 (exp_compaction_pass_rate_degradation)

| 발견 | 내용 |
|------|------|
| Subagent 면역 | Worker 위임 시 오케스트레이터 컨텍스트 ~21%, 컴팩션 미발생 |
| Yggdrasil 77테스트 | 14모듈 전부 구현에도 컴팩션 0회 |
| 핵심 인사이트 | **코드 작성이 아닌 "사고 과정"에서 컴팩션 발생** |

### 피봇 근거

컴팩션은 Worker의 코드 편집이 아니라 Orchestrator의 **계획 수립 과정**에서 발생:

```
실제 컨텍스트 소비 패턴:
  1. Spec 문서 읽기 (3,297줄) → 대량 적재
  2. 아키텍처 분석 및 의존성 파악 → 추론 누적
  3. Phase 분해 및 우선순위 결정 → 판단 과정
  4. 사용자와 계획 논의 (질문-응답 반복) → 대화 누적
  5. 계획 수정 및 재검토 → 이전 계획 + 수정본 공존
  = 컨텍스트 선형 증가 → 임계점 도달 → 컴팩션
```

## 실험 설계

### 변수

```
독립 변수: 오케스트레이터의 계획 수립 라운드 수 (1, 2, 3, ... N)
종속 변수:
  - 컴팩션 발생 시점 (라운드 #)
  - 컴팩션 후 계획 품질 (scoring rubric)
  - 컴팩션 후 실행 pass_rate vs 컴팩션 전 실행 pass_rate
통제 변수: 동일 프로젝트 (Yggdrasil), 동일 spec, 동일 모델
```

### 프로토콜

```
Phase A: Planning 컨텍스트 누적 유도

  Round 1: "Yggdrasil 전체 spec을 읽고 모듈별 구현 계획을 세워줘"
    → 5개 spec 문서 전부 읽기 (~3,300줄 컨텍스트 적재)
    → 초기 계획 생성

  Round 2: "type 정의와 test 파일도 분석해서 계획을 보완해"
    → 6개 type 파일 + 8개 test 파일 읽기 (추가 ~2,000줄)
    → 기존 계획 + 보완된 계획 공존

  Round 3: "모듈 간 의존관계를 분석하고 구현 순서를 재배치해"
    → 기존 컨텍스트 위에 의존성 분석 추가
    → 계획 재구성

  Round 4: "각 모듈별 예상 난이도와 리스크를 평가해"
    → 누적된 컨텍스트에서 추론 수행

  Round N: 컴팩션 발생까지 계속 추가 분석 요청
    → "테스트 커버리지 분석", "에지케이스 식별", "성능 고려사항" 등

Phase B: 컴팩션 전후 실행 비교

  B-1 (Before compaction): 컴팩션 직전 시점의 계획으로 구현 실행
    → Worker에게 위임, pass_rate 기록

  B-2 (After compaction): 컴팩션 발생 후 동일 구현 지시
    → Worker에게 위임, pass_rate 기록

  B-3 (Fresh session): 세션 리셋 후 spec만 다시 읽고 구현
    → 대조군, pass_rate 기록
```

### 측정 항목

| 항목 | 측정 방법 |
|------|----------|
| 컴팩션 발생 라운드 | PreCompact 훅 → compactions.jsonl |
| 컨텍스트 사용률 변화 | HUD context_window 비율 (각 라운드별) |
| 계획 품질 (정량) | 생성된 계획의 모듈 수, phase 세분화 수준, spec 커버리지 |
| 계획 품질 (정성) | Scoring rubric: completeness, consistency, spec-alignment (1-5) |
| 실행 pass_rate | vitest run 결과 |
| 정보 보존도 | 컴팩션 후 "이전에 분석한 X에 대해 설명해줘" 질문 → 정확도 |

### 실험 환경

```
프로젝트: /private/tmp/yggdrasil-compaction-experiment
Spec 규모: 5파일, 3,297줄
Type 정의: 6파일
테스트: 8파일, 77테스트
소스 스텁: 14파일
모델: Sonnet (기본 MPL 모델)
컴팩션 임계점: ~83.5% (기본값)
```

### 예상 시나리오

```
Round 1: spec 읽기 → ~40% 컨텍스트
Round 2: type + test 읽기 → ~55%
Round 3: 의존성 분석 → ~65%
Round 4: 리스크 평가 → ~75%
Round 5: 추가 분석 → ~83% → 컴팩션 발생
Round 6: 컴팩션 후 계획 재확인 → 품질 측정
```

## 데이터 수집 포맷

**planning_rounds.jsonl** (신규):
```json
{
  "round": 1,
  "timestamp": "2026-03-11T15:00:00Z",
  "prompt_summary": "전체 spec 읽기 + 초기 계획",
  "context_pct": 40,
  "compaction_count": 0,
  "plan_modules_count": 14,
  "plan_phases_count": 5,
  "spec_refs_count": 23
}
```

**plan_quality_scoring.json** (라운드별):
```json
{
  "round": 5,
  "compaction_count": 1,
  "scores": {
    "completeness": 4,
    "consistency": 3,
    "spec_alignment": 2,
    "dependency_accuracy": 3,
    "risk_identification": 2
  },
  "information_loss_probes": [
    { "question": "backend spec의 auth 모듈 설계는?", "accuracy": "partial" },
    { "question": "DB schema의 relation 구조는?", "accuracy": "lost" }
  ]
}
```

## 한계 및 보완

| 한계 | 보완 방법 |
|------|----------|
| 계획 품질 scoring이 주관적 | Rubric 사전 정의 + 2명 이상 독립 평가 |
| 라운드별 프롬프트가 다름 | 프롬프트 세트를 사전 고정 |
| 컴팩션 시점이 불확실 | HUD 모니터링 + PreCompact 훅 자동 기록 |
| 단일 프로젝트만 사용 | 추후 다른 규모의 프로젝트로 재현 |

## 실험 결과 반영 계획

```
IF 컴팩션 후 계획 품질이 유의미하게 저하:
  → MPL phase1 (research + planning) 단계에서 컨텍스트 예산 관리 필요
  → 긴 계획 수립 시 중간 결과를 파일로 외부화하는 패턴 도입
  → "plan checkpoint" 메커니즘 설계

IF 컴팩션이 계획 품질에 큰 영향 없음:
  → 오케스트레이터의 planning 컨텍스트는 compaction에 내성이 있음
  → 구조화된 계획(PLAN.md)이 컴팩션 후에도 참조 가능하기 때문

IF 컴팩션 자체가 발생하지 않음:
  → Yggdrasil 규모(3,300줄 spec)도 planning context 임계점에 불충분
  → 더 큰 규모의 프로젝트 필요 또는 CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 조절
```

## 상태

- [x] 실험 환경 (Yggdrasil) 셋업 완료
- [x] PreCompact 훅 핸들러 구현
- [x] 이전 실험 결론 정리
- [x] Planning round 프롬프트 세트 확정 (`experiments/prompts/planning_rounds.md`)
- [x] Phase A 실행: 10라운드, compaction 4회 발생 + 5회째 실패
- [x] 컴팩션 발생 확인 및 데이터 수집
- [ ] Phase B 실행: 전후 비교 (세션 교착으로 미실행)
- [x] 데이터 분석 및 결론 도출

## 실험 결과

> 상세: `experiments/data/yggdrasil-planning-run1/conclusion.md`

### 핵심 발견

1. **Planning 대화가 compaction의 주요 유발원** — Worker 구현은 0회, Planning 10라운드는 4회+
2. **파일 외부화 = compaction resilience** — .md로 Write한 분석 결과는 compaction 후에도 Read로 복원 가능
3. **Compaction 실패 한계점 존재** — 4회 compaction 후 5회째에서 auto compact 메커니즘 자체가 실패
4. **컨텍스트 증가 속도**: 파일 Write 라운드는 느림(+8%), 터미널 직접 출력은 빠름(+12-20%)

### 예상 결과 vs 실제 결과

| 예상 | 실제 |
|------|------|
| Round 5 근처에서 첫 compaction | **정확** — Round 5에서 발생 |
| Compaction 후 정보 손실 | **파일 외부화로 손실 최소** |
| 2차 이후 품질 저하 | **측정 전 세션 교착** |
| Compaction 실패 가능성 | **예상 못함 — 새로운 발견** |

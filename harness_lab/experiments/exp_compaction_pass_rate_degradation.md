# 실험: 컴팩션 횟수와 Pass Rate 저하 상관관계

> **목표**: 컨텍스트 컴팩션 N회 이후 fix loop pass_rate이 유의미하게 하락하는 교차점을 찾고, MPL 토큰 제한 체계의 근거 데이터를 확보한다.

## 배경

### 문제 인식

MPL의 토큰 총 사용량 제한(`max_total_tokens`)은 임의의 값(500K)으로 설정되어 있다.
토큰 제한의 본래 목적은 비용 절감이 아니라 **컨텍스트 품질 유지**:

```
세션이 길어짐 → 컨텍스트 누적 → compaction 발생
→ 정보 손실 → 지시 따르기 정확도 하락 → fix loop 수렴 실패
```

### 설계 변경 방향 (확정)

| 항목 | 기존 | 변경 |
|------|------|------|
| 기본 제한 | 전체 토큰 예산 (tier별 고정) | **Fix Loop 1회당 토큰 상한** |
| 전체 예산 | 필수 (80K/150K/500K) | **optional, default OFF** |
| 세션 리셋 기준 | 없음 | **컴팩션 횟수 기반 (본 실험으로 결정)** |

## 감지 인프라

### 사용 가능한 메커니즘

| 방법 | 시점 | 감지 방식 |
|------|------|----------|
| PreCompact 훅 | 컴팩션 직전 | `hooks.json`에 등록, `trigger: "auto"/"manual"` |
| SessionStart (source="compact") | 컴팩션 직후 | source 필드 체크 |
| HUD context_window | 실시간 | `mpl-hud.mjs`에서 `context_window.used/total` 비율 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 설정 | 기본 ~83.5%에서 컴팩션 트리거 |

### 추가 구현 필요

1. **PreCompact 훅 핸들러**: `.mpl/profile/compactions.jsonl`에 컴팩션 이벤트 기록
2. **phases.jsonl 확장**: `compaction_count` 필드 추가
3. **분석 스크립트**: compaction_count별 pass_rate 그룹핑 및 시각화

## 실험 설계

### 변수

```
독립 변수: 컴팩션 발생 횟수 (0, 1, 2, 3, ...)
종속 변수: fix loop 1회당 pass_rate 변화량 (Δpass_rate)
통제 변수: 동일 태스크, 동일 tier, 동일 모델
```

### 프로토콜

```
Step 1: 중간 복잡도 태스크 5개 선정 (Standard tier)
        - 각 태스크는 fix loop 3회 이상을 유발할 정도의 난이도
        - 동일 프로젝트, 동일 테스트 스위트

Step 2: 각 태스크를 두 조건으로 실행 (paired design)
        A) Long session: 세션 리셋 없이 끝까지 실행
        B) Fresh session: 컴팩션 발생 시점마다 세션 리셋 후 재개

Step 3: PreCompact 훅으로 컴팩션 횟수 자동 기록
        - timestamp, compaction_count, trigger, context_pct

Step 4: phase별 pass_rate × compaction_count 매트릭스 수집

Step 5: 교차점 분석
        - "컴팩션 N회부터 세션 리셋이 유리" 판단
        - paired t-test 또는 Wilcoxon signed-rank test
```

### 데이터 수집 포맷

**compactions.jsonl** (신규):
```json
{
  "timestamp": "2026-03-10T14:30:00Z",
  "pipeline_id": "abc123",
  "compaction_count": 2,
  "trigger": "auto",
  "context_pct": 83.5
}
```

**phases.jsonl** (확장):
```json
{
  "step": "phase-3",
  "name": "add_validation",
  "pass_rate": 82,
  "micro_fixes": 3,
  "estimated_tokens": { "context": 5000, "output": 3000, "total": 8000 },
  "compaction_count": 2,
  "session_condition": "long"
}
```

### 예상 결과 형태

```
compaction_count | avg_pass_rate | avg_fix_loops | stagnation_rate
0                | 94%           | 1.2           | 5%
1                | 91%           | 1.8           | 12%
2                | 82%           | 3.1           | 35%    ← 임계점?
3                | 71%           | 4.5           | 58%
```

## 한계 및 보완

| 한계 | 보완 방법 |
|------|----------|
| 태스크 5개로는 통계적 유의성 부족 | 각 태스크를 3회 반복 실행 (총 30 runs) |
| 태스크 난이도 편차 | paired design (동일 태스크의 long vs fresh 비교) |
| 컴팩션 ≠ 유일한 성능 저하 원인 | fresh session 대조군으로 분리 |
| 컴팩션 내용/품질 측정 불가 | pass_rate을 proxy로 사용 |
| Claude 모델 업데이트 시 재현성 | 실험 시점의 모델 버전 기록 |

## 실험 결과 반영 계획

실험 결과에 따라 MPL 설계에 반영:

```
IF 컴팩션 N회부터 pass_rate 급락 확인:
  → MPL에 "compaction_count >= N이면 세션 리셋 권고" 로직 추가
  → per-loop 토큰 상한의 근거 데이터로 활용

IF 컴팩션 횟수와 pass_rate 간 유의미한 상관 없음:
  → 컴팩션 기반 제한 폐기
  → convergence 감지(stagnation)만으로 충분한지 재검토

IF 컴팩션 1회부터 즉시 급락:
  → 컴팩션 자체를 방지하는 방향 검토
  → 세션당 토큰 사용량을 컴팩션 임계점 이하로 유지
```

## 상태

- [x] PreCompact 훅 핸들러 구현 (`MPL/hooks/mpl-compaction-tracker.mjs`)
- [x] phases.jsonl compaction_count 필드 추가 (`MPL/hooks/mpl-validate-output.mjs`)
- [x] hooks.json에 PreCompact 훅 등록
- [x] mpl-state.mjs DEFAULT_STATE에 compaction_count 추가
- [x] 분석 스크립트 작성 (`experiments/scripts/analyze_compaction_impact.mjs`)
- [ ] 실험용 태스크 5개 선정
- [ ] 실험 실행 (A: long session)
- [ ] 실험 실행 (B: fresh session)
- [ ] 데이터 분석 및 교차점 도출
- [ ] MPL 설계 문서 반영

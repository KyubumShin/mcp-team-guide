# 실험 결론: Planning Phase 컴팩션 영향

> **실험**: exp_planning_compaction_impact
> **날짜**: 2026-03-12
> **상태**: 완료 (세션 교착으로 종료)

## 핵심 발견

### 1. Planning 대화가 컴팩션의 주요 유발원

| 시나리오 | Compaction 발생 |
|---------|----------------|
| Worker가 77개 테스트 구현 (이전 실험) | **0회** |
| Orchestrator가 10라운드 계획 수립 | **4회 + 실패 1회** |

코드 작성이 아니라 **"사고 과정"** — spec 읽기, 분석, 의존관계 파악, 계획 수립, 비판적 검토 — 이 컨텍스트를 누적시킨다.

### 2. 파일 외부화 = Compaction Resilience 전략

| 출력 방식 | Compaction 후 정보 보존 |
|----------|----------------------|
| `.md` 파일로 Write | **높음** — 파일을 다시 읽어 복원 가능 |
| 터미널 직접 출력 | **낮음** — compaction summary에 의존 |

에이전트가 분석 결과를 파일로 외부화하면:
- Compaction이 발생해도 파일을 다시 Read하여 정보 복원 가능
- 사실상 "외부 메모리"로 작동
- 이는 의도적 설계가 아닌 우연한 방어 메커니즘

### 3. Compaction 실패 한계점 존재

4번의 compaction 후 5번째 시도에서 auto compact 자체가 실패했다.
- 77% 컨텍스트 사용 중인 상태에서 실패
- 대화 이력이 compaction summary 생성 능력을 초과
- 세션이 교착 상태에 빠짐 (진행도 불가, 컴팩션도 불가)

### 4. 컨텍스트 사용 패턴

```
Round 1-4: 0% → 77% (spec 읽기 + 분석 = 선형 증가)
Round 5:   77% → 83%+ → COMPACTION #1 → 낮은 %
Round 6:   → COMPACTION #2 → 21%
Round 7:   21% → 51% (파일 외부화로 느린 증가)
Round 8:   51% → 59% → 71%
Round 9:   71% → COMPACTION #3 → ?%
Round 10:  → COMPACTION #4 (실패) → 77% 교착
```

파일 외부화 라운드(Round 7)는 컨텍스트 증가가 느리고,
터미널 직접 출력 라운드(Round 8)는 빠르게 증가한다.

## 이전 실험과 통합

| 발견 | 실험 |
|------|------|
| Subagent 위임이 compaction을 구조적으로 방지 | taskq + yggdrasil 구현 실험 |
| Planning 대화가 compaction의 주요 유발원 | **본 실험** |
| 파일 외부화가 compaction resilience로 작동 | **본 실험** |
| Compaction 실패 한계점 존재 (~4회) | **본 실험** |

## MPL 설계 시사점

### 즉시 적용 가능

1. **Phase 1 (Research/Planning)에서 중간 결과를 파일로 외부화**
   - 분석 결과를 `.mpl/research/` 또는 `PLAN.md`에 기록
   - Compaction 후에도 파일을 다시 읽어 컨텍스트 복원
   - 이미 MPL이 하고 있는 패턴 (PLAN.md 생성)을 강화

2. **Planning 세션에 라운드 상한 설정**
   - ~4-5라운드 후 compaction 위험 증가
   - 5라운드 이상의 planning은 세션 분할 권장
   - 또는 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`를 낮춰 조기 compaction 유도

3. **Compaction 실패 감지 및 대응**
   - Compaction 실패 시 자동으로 세션 리셋 + 파일 기반 컨텍스트 복원
   - `.mpl/state.json`에 `compaction_failure_count` 추가

### 추가 연구 필요

1. Compaction 실패의 정확한 메커니즘 (왜 77%에서 실패하는가?)
2. 최적의 compaction 임계점 (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 값)
3. 파일 외부화 vs remember 태그 vs 훅 재주입의 정보 보존도 비교
4. Compaction 횟수와 계획 품질의 정량적 상관관계

## 실험 한계

| 한계 | 영향 |
|------|------|
| 단일 세션, 단일 프로젝트 | 재현성 미확인 |
| Compaction 후 정보 보존 측정이 주관적 | probe 질문 2개로는 부족 |
| 파일 외부화를 통제하지 못함 (에이전트 자율 결정) | 혼합 변수 |
| 정확한 ctx % 측정이 수동 | 자동화 필요 |
| Compaction 실패 원인 불명 | 추가 조사 필요 |

# MPL 로드맵: v1.0→v3.0 진화와 잔여 계획

## 비전: "Phase 0 Enhanced + Phase 5 Minimized"

MPL의 핵심 철학은 **사전 명세(Phase 0)를 강화하여 사후 수정(Phase 5)을 불필요하게 만드는 것**이다. 7개의 실험(Exp 1~8, Exp 2 제외)을 통해 Phase 0에 투자하는 토큰이 Phase 5의 디버깅/수정 비용을 완전히 제거할 수 있음을 실증적으로 검증했다.

v3.0에서 이 비전은 **구현 완료**되었으며, 추가로 로드맵에 없던 기능들(Pre-Execution Analysis, 3-Gate 품질, Convergence Detection 등)도 도입되었다.

---

## 3단계 구현 로드맵 — 달성 현황

| 단계 | 이름 | 핵심 목표 | 상태 | 상세 문서 |
|------|------|----------|------|----------|
| Phase 1 | Foundation | Phase 0 Enhanced: 복잡도 적응형 4단계 분석 | **v3.0 완전 구현** | [phase1-foundation.md](./phase1-foundation.md) |
| Phase 2 | Incremental | Build-Test-Fix 마이크로 사이클, Phase 5 진입 조건 엄격화 | **v3.0 완전 구현** | [phase2-incremental.md](./phase2-incremental.md) |
| Phase 3 | Automation | 토큰 프로파일링, Phase 0 캐싱, API 자동 추출, 패턴 자동 분석 | **부분 구현** (2/4) | [phase3-automation.md](./phase3-automation.md) |

---

## 핵심 수치 목표 — 달성 여부

| 지표 | v1.0 기준 | v2.0 목표 | v3.0 달성 | 상태 |
|------|----------|----------|----------|------|
| 총 토큰 사용량 | ~81K | 50~55K | 적응형 (복잡도별 가변) | ✓ 복잡도 기반 최적화 |
| Phase 4 통과율 | 66~83% | 95%+ | 3-Gate 시스템으로 대체 | ✓ 95% 이상 요구 |
| Phase 5 의존도 | 높음 (필수) | 최소 (조건부) | Fix Loop + Convergence Detection으로 대체 | ✓ 사실상 제거 |
| Phase 0 토큰 | ~5K | 8~25K (복잡도별) | 8~25K (4등급 적응형) | ✓ 목표 달성 |
| 디버깅 사이클 수 | 3~5회 | 0~1회 | Build-Test-Fix (TODO당 최대 2회) | ✓ 즉시 수정으로 전환 |

---

## 구현 상태 매트릭스

### Phase 1: Foundation — 완전 구현

| 기능 | 설계 | 구현 | 비고 |
|------|------|------|------|
| 복잡도 감지기 (4등급) | ✓ | ✓ | Simple/Medium/Complex/Enterprise |
| Phase 0 4단계 프로세스 | ✓ | ✓ | Step 1~4, 복잡도별 선택적 적용 |
| API Contract Extraction | ✓ | ✓ | ast_grep_search + lsp 기반 |
| Example Pattern Analysis | ✓ | ✓ | 7개 패턴 카테고리 |
| Type Policy Definition | ✓ | ✓ | 타입 힌트 규칙 |
| Error Specification | ✓ | ✓ | 모든 복잡도에서 필수 |
| 산출물 검증 체크리스트 | - | ✓ | v3.0 추가 |
| Phase 0 요약 생성 | - | ✓ | v3.0 추가 |

### Phase 2: Incremental — 완전 구현

| 기능 | 설계 | 구현 | 비고 |
|------|------|------|------|
| Build-Test-Fix 마이크로 사이클 | ✓ | ✓ | TODO당 최대 2회 재시도 |
| 누적 테스트 (회귀 방지) | ✓ | ✓ | 페이즈 종료 시 전체 실행 |
| Phase 5 진입 조건 엄격화 | ✓ | ✓ | 3-Gate 시스템으로 발전 |
| 복잡도 자동 감지기 | ✓ | ✓ | Step 2.5에 통합 |
| Test Agent (독립 검증) | - | ✓ | v3.0 추가: 코드 작성자와 분리 |
| Convergence Detection | - | ✓ | v3.0 추가: improving/stagnating/regressing |

### Phase 3: Automation — 부분 구현

| 기능 | 설계 | 구현 | 비고 |
|------|------|------|------|
| 토큰 프로파일링 | ✓ | ✓ | phases.jsonl + run-summary.json |
| Phase 0 캐싱 | ✓ | ✓ | .mpl/cache/phase0/ |
| API 자동 추출 (AST 파서) | ✓ | ✗ | 미구현: 오케스트레이터가 수동 분석 |
| 패턴 자동 분석 (패턴 감지기) | ✓ | ✗ | 미구현: 에이전트 기반 분석으로 대체 중 |

---

## v3.0에서 로드맵 외 추가된 기능

로드맵에 계획되지 않았으나 v3.0에서 새로 도입된 기능들:

| 기능 | 설명 | 관련 에이전트 |
|------|------|-------------|
| **Triage** | information_density 기반 인터뷰 깊이 자동 결정 (skip/light/full) | (오케스트레이터) |
| **Pre-Execution Analysis** | Gap/Tradeoff/Verification/Critic 4단계 사전 분석 | mpl-gap-analyzer, mpl-tradeoff-analyzer, mpl-verification-planner, mpl-critic |
| **3-Gate 품질 시스템** | Gate 1(자동 테스트) + Gate 2(코드 리뷰) + Gate 3(Agent-as-User) | mpl-code-reviewer |
| **A/S/H 검증 분류** | Agent/Sandbox/Human 검증 항목 분류 | mpl-verification-planner |
| **Test Agent** | 코드 작성자와 독립된 테스트 에이전트 | mpl-test-agent |
| **Convergence Detection** | Fix Loop에서 improving/stagnating/regressing 감지 | (오케스트레이터) |
| **Side Interview** | CRITICAL discovery / H-items / AD 마커 시 사용자 확인 | (오케스트레이터) |
| **Resume 프로토콜** | 페이즈별 상태 영속성 기반 이어하기 | (오케스트레이터) |
| **컨텍스트 정리** | 페이즈 완료 후 오케스트레이터 메모리 정리 | (오케스트레이터) |

---

## 실험 성과 매트릭스

7개 실험 모두 77/77 = 100% 달성 (최종 테스트 스위트 기준). 이 실험 결과는 v3.0의 Phase 0 Enhanced 설계의 근거가 되었다.

| 실험 | Phase 0 기법 | 누적 점수 진행 | v3.0 반영 |
|------|-------------|---------------|----------|
| Exp 1 | API 계약 추출 | 34/89 (38%) → 77/77 (100%) | Step 1: API Contract Extraction |
| Exp 3 | 예제 패턴 분석 | 52/89 (58%) → 77/77 (100%) | Step 2: Example Pattern Analysis |
| Exp 4 | 타입 정책 정의 | 58/89 (65%) → 77/77 (100%) | Step 3: Type Policy Definition |
| Exp 5 | 테스트 스텁 생성 | 69/89 (77%) → 77/77 (100%) | Build-Test-Fix 마이크로 사이클 |
| Exp 6 | 점진적 테스팅 | 74/89 (83%) → 77/77 (100%) | Incremental Verification |
| Exp 7 | 에러 명세 | 77/77 (100%) | Step 4: Error Specification |
| Exp 8 | 하이브리드 검증 | 77/77 (100%) | 3-Gate 품질 시스템 |

> **핵심 발견**: 누적 점수 진행(38% → 58% → 65% → 77% → 83% → 100%)은 Phase 0 기법이 추가될수록 점수가 단조 증가함을 보여준다. 이 발견이 복잡도 적응형 Phase 0 설계의 근거가 되었다.

## Phase 0 Enhanced: 4단계 프로세스

실험 결과를 종합하면, 완전한 Phase 0는 4단계로 구성된다. v3.0에서 **구현 완료**되었다:

```
Step 1: API Contract Extraction (Exp 1) ─── 함수 시그니처, 파라미터 순서
Step 2: Example Pattern Analysis (Exp 3) ── 사용 패턴, 기본값, 엣지 케이스
Step 3: Type Policy Definition (Exp 4) ──── 타입 힌트, 컬렉션 타입 규칙
Step 4: Error Specification (Exp 7) ──────── 표준 예외, 메시지 패턴
```

각 단계가 독립적으로도 점수를 개선하지만, 조합했을 때 시너지 효과가 극대화된다. 복잡도에 따라 적용 Step이 자동 선택된다.

## 토큰 예산 재배분

v1.0에서 v3.0으로의 토큰 예산 변화. v3.0은 Phase 5를 Fix Loop + 3-Gate로 대체하여 구조가 변경되었다:

```
v1.0 (기존)                          v3.0 (달성)
┌──────────────────────────┐        ┌──────────────────────────┐
│ Phase 0:  ~5K  ( 6%)     │        │ Phase 0: 8~25K (적응형)   │
│ Phase 1: ~15K (19%)      │        │ Phase 실행: 페이즈당 적응형  │
│ Phase 2: ~15K (19%)      │        │ 3-Gate: ~2K              │
│ Phase 3: ~15K (19%)      │        │ Fix Loop: 0~10K (조건부)  │
│ Phase 4: ~15K (19%)      │        │ Finalize: ~2K            │
│ Phase 5: ~16K (20%)      │        │                          │
│ ─────────────────────    │        │ Phase 0 캐시 히트 시: ~0K  │
│ 합계:    ~81K            │        │ 합계: 복잡도 기반 가변     │
└──────────────────────────┘        └──────────────────────────┘
```

## 잔여 계획 및 알려진 이슈

> 최종 감사일: 2026-03-05. 전체 목록은 [design.md §9](../design.md#9-알려진-이슈-및-잔여-작업)를 참조한다.

### CRITICAL (2건) — 정합성 영향

| ID | 항목 | 상세 |
|----|------|------|
| I-01 | 유령 에이전트 `mpl-research-synthesizer` | `mpl-validate-output.mjs`의 VALIDATE_AGENTS에 등록되었으나 에이전트 파일 없음. 제거 또는 생성 필요. |
| I-02 | mpl-run.md Related Skills 중복 | `/mpl:mpl`이 2회 등록되어 실행 프로토콜이 모호함. |

### HIGH (5건) — 기능 누락

| ID | 항목 | 상세 |
|----|------|------|
| I-03 | 스킬 `/mpl:mpl-bugfix` 미구현 | mpl-run.md에 등록되었으나 SKILL.md 없음 |
| I-04 | 스킬 `/mpl:mpl-small` 미구현 | mpl-run.md에 등록되었으나 SKILL.md 없음 |
| I-05 | 스킬 `/mpl:mpl-compound` 래퍼 없음 | 에이전트는 존재, 독립 스킬 없음 |
| I-06 | 스킬 `/mpl:mpl-gap-analysis` 래퍼 없음 | 에이전트는 존재, 독립 스킬 없음 |
| I-07 | `mpl-validate-output` 에이전트 목록 불완전 | `mpl-decomposer`, `mpl-git-master` 출력이 검증 우회 |

### MEDIUM (2건) — 미구현 로드맵

| ID | 항목 | 현재 대안 |
|----|------|----------|
| I-08 | API 자동 추출 (AST 파서) — `TestAnalyzer` 클래스 | 오케스트레이터가 ast_grep_search/lsp로 수동 분석 |
| I-09 | 패턴 자동 분석 (패턴 감지기) — 7개 카테고리 자동 분류 | 오케스트레이터가 Grep/ast_grep으로 수동 추출 |

### LOW (4건) — 개선 사항

| ID | 항목 |
|----|------|
| I-10 | Convergence 상태 명명 불일치 (훅 `stagnant` vs 프로토콜 `stagnating`) |
| I-11 | Phase 0 캐시 검증 유틸리티 코드 없음 (프로토콜 의존) |
| I-12 | 토큰 프로파일링 집계·시각화 도구 없음 |
| I-13 | Triage 로직이 훅으로 강제되지 않음 (프로토콜 수준만) |

---

## 결론

MPL은 v1.0→v3.0 진화를 통해 "예방이 치료보다 낫다"는 원칙을 실증 데이터로 뒷받침하는 파이프라인으로 성장했다. 7개 실험의 일관된 결과에 기반한 Phase 0 Enhanced와, 로드맵 외에서 추가된 Pre-Execution Analysis, 3-Gate 품질 시스템, Convergence Detection이 결합되어 견고한 자율 코딩 파이프라인을 구성한다.

상세 설계는 각 문서를 참고한다:

- [Phase 1: Foundation - Phase 0 Enhanced](./phase1-foundation.md) — **구현 완료**
- [Phase 2: Incremental - 점진적 구현/테스트](./phase2-incremental.md) — **구현 완료**
- [Phase 3: Automation - 자동화 및 최적화](./phase3-automation.md) — **부분 구현**
- [실험 결과 요약](./experiments-summary.md)
- [v3.0 설계 문서](../design.md)

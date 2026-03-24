# MPL 1M 컨텍스트 윈도우 영향 분석

> 작성일: 2026-03-24
> 대상: MPL v0.6.6 (design.md 기준)
> 변경 요인: Claude Opus 4.6 1M 컨텍스트 윈도우 (기존 ~200K 대비 5배 증가)

---

## 1. 핵심 요약

MPL의 아키텍처는 ~200K 컨텍스트 제약 하에서 설계되었다. 1M(5배 증가)은 **설계 전제를 흔드는 질적 변화**이나, Phase 구조 자체는 컨텍스트 절약이 아닌 **기능 단위 격리·일관성·병렬화·실패 격리** 목적이므로 유지한다.

**변경 방향**: Phase 구조 유지 + Phase 내부 컨텍스트 풍부함 극대화

---

## 2. 현재 설계에서 컨텍스트 제약이 만든 메커니즘

| # | 메커니즘 | 설계 의도 | 현재 파라미터 | 위치 |
|---|---------|----------|-------------|------|
| M1 | Phase Decision 3-Tier 분류 | Phase 간 결정 토큰 일정 유지 | Tier 1(~800t), Tier 2(~240t), Tier 3(~0t) | design.md §6.2 |
| M2 | State Summary 유일 다리 | Phase 간 지식 전달 최소화 | Summary만 전달, 상세 파기 | design.md §2 Principle 5 |
| M3 | Context Cleanup | Phase 완료 후 즉시 상세 해제 | 매 phase 후 즉시 | design.md §4.3.6 |
| M4 | Impact file 캡 | Worker context 폭발 방지 | 파일당 최대 500줄 | design.md §4.1 |
| M5 | Phase 0 Caching | 8-25K 토큰 절약 | 7일 TTL, hash 기반 | design.md §3.3 Step 2.5 |
| M6 | max_total_tokens | 전체 예산 상한 | 500,000 | design.md §8, state-manager.ts:50 |
| M7 | Episodic Memory 압축 | 오래된 phase 정보 폐기 | 최근 2 phases만 상세 | mpl-memory.mjs |
| M8 | Adaptive Router 기준 | 파이프라인 크기 결정 | Frugal(<0.3)/Standard(0.3~0.65)/Frontier(≥0.65) | roadmap F-20 |
| M9 | Budget Safety Margin | 토큰 부족 방지 | 1.15× | mpl-profile.mjs |

---

## 3. 유지하는 것 (컨텍스트와 무관한 구조적 이점)

| 원칙 | 유지 이유 |
|------|----------|
| **Micro-Phase 분해 구조** | 기능 단위 worker 구현의 일관성, 병렬화, 실패 시 롤백 범위 제한 |
| **Orchestrator-Worker 분리** | 검증 객관성 확보 (자기 코드 방어 방지) |
| **5-Gate Quality System** | 품질 보장은 컨텍스트 크기와 독립 |
| **A/S/H Verification 분류** | 검증 방법론 자체는 유지 |
| **Convergence Detection** | Fix Loop 수렴 판단은 컨텍스트 무관 |
| **Build-Test-Fix Micro-Cycle** | TODO별 즉시 테스트는 구조적 이점 |
| **Write Guard 훅** | 역할 분리 원칙 |
| **Bounded Retries** | 무한 루프 방지는 항상 필요 |

---

## 4. 변경 항목

### 4.1 P0 — 즉시 반영 (하드코딩 값 수정)

#### 4.1.1 `max_total_tokens` 상향
- **현재**: 500,000
- **변경**: 900,000
- **근거**: 1M 중 ~100K는 시스템 프롬프트/도구 정의에 소모. 유효 900K가 실질적 상한.
- **위치**: `state-manager.ts:50`, `design.md §8`

#### 4.1.2 Impact file 캡 상향
- **현재**: 파일당 최대 500줄
- **변경**: 파일당 최대 2,000줄
- **근거**: 500줄은 200K 기준. 1M에서는 관련 파일 전체를 로드해도 여유. 중간 크기 파일의 잘린 컨텍스트로 인한 worker 오류 감소.
- **위치**: `design.md §4.1`, `mpl-phase-runner.md`

#### 4.1.3 Episodic Memory 유지 기간 확대
- **현재**: 최근 2 phases 상세
- **변경**: 최근 5 phases 상세 (이전은 1줄 요약)
- **근거**: Phase 4에서 Phase 1의 구현 세부사항을 참조할 수 있으면 cross-phase 일관성 향상.
- **위치**: `mpl-memory.mjs`

#### 4.1.4 Budget Safety Margin 완화
- **현재**: 1.15×
- **변경**: 1.10×
- **근거**: 절대적 여유분이 200K→900K로 증가했으므로 비율 완화 가능.
- **위치**: `mpl-profile.mjs`

### 4.2 P1 — 구조 개선

#### 4.2.1 Phase Decision 3-Tier → 2-Tier 단순화
- **현재**: Tier 1(Active) / Tier 2(Summary) / Tier 3(Archived, ID만)
- **변경**: Tier 1(Full) / Tier 2(Summary). Tier 3(Archived) 제거.
- **근거**: 10-phase 프로젝트에서 모든 PD를 Tier 1~2로 유지해도 ~10K 토큰 — 1M의 ~1%. 정보 손실 없이 phase 간 의사결정 추적 품질 향상. Tier 3는 "토큰을 0으로 만들기 위한 극단적 절약"이었으나 1M에서 불필요.
- **영향**: design.md §6.2, phase-runner context assembly 로직

#### 4.2.2 Adaptive Router 기준점 재조정
- **현재**: Frugal(5-15K) / Standard(20-40K) / Frontier(50-100K+)
- **변경 제안**:
  - Frugal: 5-30K (Phase 0에 더 투자 가능)
  - Standard: 30-150K (multi-phase도 넉넉한 context)
  - Frontier: 150-500K (복잡한 프로젝트의 full context 유지)
- **근거**: 기존 Frontier 상한(100K+)이 200K 한도에서 설정됨. 1M에서는 Standard로도 이전 Frontier 수준의 작업 가능.
- **영향**: Triage 로직, F-20 pipeline score → tier 매핑

#### 4.2.3 State Summary + 선택적 상세 컨텍스트 전달
- **현재**: Phase 간 전달은 State Summary만
- **변경**: State Summary + **직전 phase의 코드 변경 diff** + **실패한 테스트 로그** (선택적)
- **근거**: 다음 phase가 직전 phase의 변경과 직접 연관될 때 diff를 보면 구현 일관성 향상. 단, 무제한 전달은 금지 — 구조화된 추가 컨텍스트만.
- **제약**: 추가 컨텍스트는 직전 1 phase만. 2+ phases 전은 여전히 Summary만.
- **영향**: design.md §2 Principle 5 수정, §4.1 Context Assembly 확장

### 4.3 P2 — 최적화

#### 4.3.1 Context Cleanup 정책 → Sliding Window
- **현재**: Phase 완료 즉시 상세 해제
- **변경**: 최근 N phases(기본 3)는 상세 유지, 그 이전은 Summary로 압축
- **근거**: 1M에서 3 phases의 상세 데이터(각 ~20-30K) 유지해도 ~90K — 전체의 10%. Cross-phase 디버깅 시 이전 phase 컨텍스트 접근 가능.
- **영향**: design.md §4.3.6 수정

#### 4.3.2 Phase 0 Cache 전략 완화
- **현재**: Cache miss = 8-25K 토큰 손실
- **변경**: Cache 메커니즘 유지하되, cache miss 시 더 상세한 Phase 0 실행 허용 (토큰 예산 ~30K까지 확대)
- **근거**: 8-25K 절약이 200K의 4-12%였으나, 1M의 0.8-2.5%로 상대적 중요도 감소. Cache 유지보수 복잡성 대비 이득이 줄었으나, 시간 절약(LLM 호출 절약)은 여전히 유효하므로 제거하지 않음.
- **영향**: design.md §3.3 Step 2.5 토큰 예산 테이블

---

## 5. 새로운 가능성 (향후 검토)

### 5.1 Interview + Execution 연속 세션
1M이면 Interview의 전체 대화를 유지한 채 Execution으로 진입 가능. 인터뷰에서 나온 뉘앙스·맥락이 보존되어 PP 해석 품질 향상. 현재는 Interview → (context 정리) → Execution이 별도 단계.

### 5.2 Full Codebase Context Loading
중소규모 프로젝트(총 코드 <200K 토큰)는 관련 파일 전체를 context에 로드 가능. Phase Runner의 "필요한 파일만 선별" 로직 단순화 가능.

### 5.3 Cross-Phase Decision 완전 보존
모든 Phase Decision을 Tier 1(Full)로 유지해도 부담이 미미. "Phase 4에서 Phase 1의 결정을 잊는다"는 핵심 문제 해소.

### 5.4 Worker에게 더 풍부한 컨텍스트 전달
현재 worker는 최소한의 TODO + impact files만 받지만, 1M에서는 **관련 테스트 코드, 인접 모듈, Phase 0 전체 아티팩트**를 함께 전달 가능. Worker의 "맥락 부족으로 인한 잘못된 구현" 감소 기대.

---

## 6. 변경하지 말아야 할 것들 — 상세 근거

| 항목 | 변경 유혹 | 변경하면 안 되는 이유 |
|------|---------|---------------------|
| Phase 분해 자체 제거 | "1M이면 한 세션에 다 되지 않나?" | 기능 단위 격리가 주는 **구현 일관성, 테스트 격리, 실패 범위 제한**은 컨텍스트와 무관. Worker별 TODO 단위 실행이 코드 품질에 직접 기여. |
| Orchestrator-Worker 분리 제거 | "context 넉넉하니 orchestrator가 직접 짜도 되지 않나?" | 검증 객관성(자기 코드를 방어하지 않음)은 인간 심리와 동일한 LLM 편향 문제. 컨텍스트와 무관. |
| 5-Gate 단순화 | "여유 있으니 Gate 줄여도 되지 않나?" | Gate는 품질 보장. 컨텍스트가 늘어도 LLM의 실수 확률이 0이 되지 않음. |
| Bounded Retries 완화 | "더 많이 시도하면 성공하지 않을까?" | 무한 루프 방지는 안전 장치. 토큰이 많아도 수렴하지 않는 문제는 전략 변경이 답. |

---

## 7. 버전 분리 계획

### v0.6.7 — 파라미터 튜닝 (즉시 적용 가능)

상수 변경 + 프롬프트 텍스트 수정만으로 적용 가능. 프로토콜 로직 변경 없음.

| 항목 | 변경 | 수정 대상 | 난이도 |
|------|------|----------|--------|
| max_total_tokens | 500K→900K | `state-manager.ts`, `mpl-config.mjs`, `mpl-state.mjs`, `mpl-setup/SKILL.md` | 상수 4곳 |
| Impact file 캡 | 500→2000줄 | `mpl-run-execute-context.md` | 텍스트 1줄 |
| Phase 0 토큰 예산 | 8K/12K/20K→10K/18K/30K | `design.md` (가이드라인) | 이미 반영 |
| Episodic Memory | 2→5 phases | `mpl-memory.mjs` (default param + slice) | 상수 2곳 |

### v0.7.0 — 프로토콜 구조 변경 (6+ 파일 재작성 필요)

분류 로직, context assembly 프로토콜, cleanup 정책 등 **프로토콜 수준** 변경.

| 항목 | 변경 | 수정 대상 | 난이도 |
|------|------|----------|--------|
| PD 3-Tier→2-Tier | Tier 3(Archived) 제거 | `mpl-run-execute-context.md` (분류 로직), `mpl-run-execute.md`, `mpl-run-decompose.md`, `SKILL.md`, `README.md`, `README_ko.md` | 6+ 파일 프로토콜 재작성 |
| Context Cleanup→Sliding Window | 즉시 해제→N=3 유지 | `mpl-run-execute-parallel.md` §4.3.7 | 프로토콜 재작성 |
| State Summary + N-1 diff | Summary만→diff/실패 로그 추가 | `mpl-run-execute-context.md` context assembly | 프로토콜 재작성 |
| Router 기준점 재조정 | Frugal/Standard/Frontier 예산 | Triage 로직, F-20 관련 | 설계 검토 필요 |

---

## 8. Design Doc 반영 현황

| 섹션 | v0.6.7 반영 | v0.7.0 (planned 표기) |
|------|-----------|---------------------|
| §2 Principle 5 | - | "planned" 노트 추가 |
| §3.3 Step 2.5 | Phase 0 토큰 예산 갱신 완료 | - |
| §4.1 Context Assembly | Impact file 캡 2000줄 반영 | N-1 diff planned 노트 |
| §4.3.6 Context Cleanup | - | Sliding Window planned 노트 |
| §6.2 Phase Decision | - | 2-Tier planned 노트 |
| §8 Configuration | max_total_tokens 900K 반영 | - |
| §9 Version History | v0.6.7 + v0.7.0(planned) 분리 | 상세 변경 목록 |

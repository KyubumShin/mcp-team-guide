# 4-System A/B Comparison Experiment

## 1. 목적

- 동일 과제에서 4개 시스템(OMC, hoyeon, UAM-Standard, UAM-MPL)의 성능을 5개 차원으로 비교
- MPL의 break-even 가설 검증

## 2. 독립변수

- 시스템: {OMC, hoyeon, UAM-Standard, UAM-MPL}
- 태스크 복잡도: {Tier 1 (TaskFlow), Tier 2 (Bookshelf API)}

## 3. 종속변수 (5차원 20개 메트릭)

### 3.1 Task Success Rate

- **criteria_pass_rate**: passed / total criteria — 요구사항 충족도
- **regression_rate**: broken_inherited / total_inherited — 기존 기능 보존율
- **completion_rate**: completed_tasks / total_tasks — 완주율

### 3.2 Token Efficiency

- **total_tokens**: 전체 입출력 토큰 합 — 절대 비용
- **tokens_per_todo**: total_tokens / completed_todos — TODO당 효율
- **context_growth_rate**: phase_N_context / phase_1_context — Context 증가율
- **overhead_ratio**: (planning + verify) / execution — 비실행 overhead

### 3.3 Error Isolation

- **error_detection_point**: error_phase / total_phases — 조기 발견 정도
- **error_blast_radius**: affected_files / total_files — 영향 범위
- **error_fix_cost**: fix_tokens / total_tokens — 수정 비용 비율

### 3.4 Adaptability

- **discovery_count**: 실행 중 발견된 새로운 정보 수
- **plan_drift**: (final_todos - initial_todos) / initial_todos — 계획 변동률

### 3.5 User Experience

- **hitl_count**: 사용자 개입 필요 횟수
- **time_to_first_result**: 첫 번째 의미 있는 산출물까지 시간(초)

## 4. 통제변수

- **모델**: Claude Sonnet 4.6 (모든 시스템 동일)
- **프롬프트**: v3 (PM 기획서 수준, 구현 세부사항 숨김)
- **HITL**: 스크립팅된 동일 응답 (hitl_responses.yaml)
- **시작 코드**: 동일한 빈 프로젝트 (pyproject.toml + 기본 구조만)
- **반복**: 각 조건 3회 (통계적 유의성)

## 5. 핵심 가설

1. **Tier 1** (3-4 TODO): OMC ≥ hoyeon ≥ UAM ≥ MPL (오버헤드 순)
2. **Tier 2** (15-20 TODO): MPL의 O(1) 컨텍스트가 다른 시스템을 역전
3. **Break-even**: ~15 TODO / 5+ Phase에서 MPL이 순이익

## 6. 실험 매트릭스

Full table: 4 systems × 2 tiers × 3 runs = 24 total runs

| # | 시스템 | Tier | 반복 | 총 실행 |
|---|--------|------|------|---------|
| 1 | OMC | T1 | ×3 | 3 |
| 2 | hoyeon | T1 | ×3 | 3 |
| 3 | UAM-Std | T1 | ×3 | 3 |
| 4 | UAM-MPL | T1 | ×3 | 3 |
| 5 | OMC | T2 | ×3 | 3 |
| 6 | hoyeon | T2 | ×3 | 3 |
| 7 | UAM-Std | T2 | ×3 | 3 |
| 8 | UAM-MPL | T2 | ×3 | 3 |
| 합계 | | | | 24회 |

## 7. 태스크 명세

### Tier 1: TaskFlow (기존)

- **출처**: `/Users/kbshin/project/uam_v3_test/prompt.md`
- **복잡도**: 3-4 TODO, 단일 Phase
- **기본 테스트**: 59개 (v3_eval_store)
- **히든 테스트**: 30개

### Tier 2: Bookshelf API (신규)

- **설계**: `tasks/tier2-bookshelf-api/`
- **복잡도**: 15-20 TODO, 5+ Phase (Auth → CRUD → Bookshelf → Search → Validation)
- **기본 테스트**: ~60개
- **히든 테스트**: ~30개

## 8. 시스템별 활성화 프로토콜

- **OMC**: `autopilot: {prompt}` (ralph+ultrawork 자동 활성화)
- **hoyeon**: `/specify` → `/execute` (SDD 파이프라인)
- **UAM-Std**: `uam {prompt}` (5-Phase 파이프라인)
- **UAM-MPL**: `uam mpl {prompt}` (Micro-Phase Loop)

## 9. 채점 방법

- 기본 점수 = (기본 통과 / 기본 전체) × 70
- 히든 점수 = (히든 통과 / 히든 전체) × 30
- 총점 = 기본 + 히든 (100점 만점)

### 등급 기준

| 등급 | 점수 범위 |
|------|----------|
| S | 95-100 |
| A | 85-94 |
| B | 70-84 |
| C | 50-69 |
| F | 0-49 |

## 10. 데이터 수집 방법

- **pytest 결과**: `pytest --tb=short -q` 파싱
- **토큰**: `.uam/metrics.json` 또는 `.omc/state/` 파일
- **시간**: `git log` 타임스탬프 (첫 커밋 ~ 마지막 커밋)
- **컨텍스트 크기**: session transcript `.jsonl` 파싱 (가용 시)
- **PLAN 분석**: `PLAN.md` 파싱 (TODO 수, 완료 수, 실패 수)

## 11. 위협 요인 및 완화

- **모델 비결정성**: 3회 반복으로 완화
- **HITL 차이**: 스크립팅된 응답으로 통제
- **네트워크/API 변동**: 같은 시간대에 연속 실행
- **플러그인 버전**: 실험 전 버전 고정 (git sha 기록)

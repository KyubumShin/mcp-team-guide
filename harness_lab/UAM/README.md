# UAM (Unified Agent Methodology)

Claude Code 전용 **독립형** 에이전트 오케스트레이션 플러그인.
OMC, hoyeon, SG-Loop 세 시스템의 강점을 하나의 5-Phase 파이프라인으로 통합했다.
외부 의존성 없음 — Claude Code + Node.js 16+만 있으면 동작한다.

---

## 빠른 시작

| 방법 | 명령 |
|------|------|
| 키워드 자동활성화 (권장) | 입력에 `uam` 포함 |
| 스킬 직접 호출 | `/uam:uam` |
| 상세 프로토콜 참조 | `/uam:uam-run` |

**Auto-Routing**: 키워드 감지 훅이 파이프라인을 자동 선택한다.

| 키워드 패턴 | 파이프라인 | 적합한 작업 |
|------------|----------|-----------|
| `uam bugfix` | Bugfix | 단일 버그 수정 |
| `uam small` / `uam quick` | Small (3-Phase) | 일상적 기능 추가 |
| `uam` | Full (5-Phase) | 복잡한 기능, 리팩토링 |

---

## 5-Phase 파이프라인

| Phase | 이름 | 에이전트 | 핵심 산출물 |
|-------|------|---------|-----------|
| 0 | Pivot Points | (인터뷰) | `.uam/pivot-points.md` |
| 1-A | Deep Research | explore, researcher, research-synthesizer | `.uam/research/report.md` |
| 1-B | Plan Generation | gap-analyzer, tradeoff-analyzer, verification-planner, pm, designer | `.uam/PLAN.md` |
| 2 | MVP Sprint | worker, frontend (병렬), git-master | 구현된 코드 + 원자적 커밋 |
| 3 | Quality Gate | code-reviewer + Judge 로직 | Gate 1-3 통과/실패 판정 |
| 4 | Fix Loop | worker, debugger | 적응적 3단계 수정 |
| 5 | Finalize | git-master | 학습 추출 + project-memory |

---

## 에이전트 카탈로그

| 에이전트 | 모델 | Phase | 역할 |
|---------|------|-------|------|
| `uam-explore` | Haiku | 1-A, 1-B | 코드베이스 탐색 |
| `uam-gap-analyzer` | Haiku | 1-B | 누락 요구사항 식별 |
| `uam-tradeoff-analyzer` | Sonnet | 1-B | 위험도 평가 |
| `uam-verification-planner` | Sonnet | 1-B | A/S/H 테스트 분류 |
| `uam-pm` | **Opus** | 1-B | 요구사항 정제, MoSCoW 우선순위 |
| `uam-designer` | Sonnet | 1-B, 3 | UX/UI 설계, 접근성 |
| `uam-researcher` | Sonnet | 1-A | Stage 1+2 기술 조사 |
| `uam-research-synthesizer` | Sonnet | 1-A | Stage 3 연구 종합 |
| `uam-worker` | Sonnet | 2, 4 | TODO 구현 (범용) |
| `uam-frontend` | Sonnet | 2, 4 | 프론트엔드 구현 |
| `uam-git-master` | Sonnet | 2, 5 | 원자적 커밋 |
| `uam-code-reviewer` | Sonnet | 3 | 멀티모델 교차 리뷰 |
| `uam-debugger` | Sonnet | 4 | 근본 원인 분석 |

Judge는 에이전트가 아닌 오케스트레이터 내부 로직.

---

## 스킬 레퍼런스

| 스킬 | 호출 | 목적 |
|------|------|------|
| `uam` | `/uam:uam` | 전체 5-Phase 파이프라인 |
| `uam-small` | `/uam:uam-small` | 경량 3-Phase 파이프라인 |
| `uam-pivot` | `/uam:uam-pivot` | Pivot Points 인터뷰 |
| `uam-status` | `/uam:uam-status` | 파이프라인 대시보드 |
| `uam-cancel` | `/uam:uam-cancel` | 안전한 중단 + 상태 보존 |
| `uam-resume` | `/uam:uam-resume` | 이전 Phase에서 재개 |
| `uam-bugfix` | `/uam:uam-bugfix` | 독립형 적응적 버그 수정 |
| `uam-compound` | `/uam:uam-compound` | 학습 추출 + 지식 증류 |

커맨드: `/uam:uam-run` (5-Phase 상세 프로토콜), `/uam:uam-small-run` (3-Phase 경량 프로토콜)

---

## 설정

`.uam/config.json` 으로 모델 라우팅, 비용 제한, maturity_mode를 설정한다.

```json
{
  "maturity_mode": "standard",
  "cost": {
    "max_total_tokens": 500000,
    "max_fix_loops": 10
  }
}
```

| maturity_mode | Discovery 처리 | 적합한 시점 |
|---------------|---------------|------------|
| `explore` | 즉시 PLAN.md 수정 | 초기 탐색/프로토타입 |
| `standard` | Phase 전환 시 일괄 검토 | 일반 개발 |
| `strict` | 다음 사이클 백로그 이관 | 안정화/릴리스 |

---

## 핵심 원칙

- **오케스트레이터-워커 분리**: 오케스트레이터는 소스 코드를 직접 작성하지 않는다. PreToolUse 훅으로 하드 강제.
- **PLAN.md SSOT**: 체크박스가 진행 상태의 유일한 원천. `[ ]` → `[x]` → `[FAILED]`
- **A/S/H-items**: A(자동 검증), S(Agent-as-User), H(인간 판단 필요)
- **HITL 최소화**: Phase 1 계획 확인 시 1회 필수 (30초 타임아웃 → 자동 진행)

---

## 상세 설계 문서

전체 사양: [`docs/design_unified_agent_methodology.md`](docs/design_unified_agent_methodology.md)

- §1: 설계 목표와 원칙
- §2-7: Phase별 상세 프로토콜
- §8: 에이전트 카탈로그
- §9: 훅 시스템 (4개)
- §10: HITL 정책
- §12: 상태 관리 및 state.json 스키마
- §13: 비용 모델

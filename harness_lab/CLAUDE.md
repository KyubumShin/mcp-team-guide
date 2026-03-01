# Harness Lab

Research repository for **agent context engineering** and **evaluation harness** design.

## Purpose

- Study and document techniques for shaping AI agent behavior through context (system prompts, CLAUDE.md, AGENTS.md, memory files, hooks)
- Design and iterate on evaluation harnesses that measure agent performance on real-world tasks
- Collect patterns, anti-patterns, and lessons learned from multi-agent orchestration

## Conventions

- All notes and research artifacts are written in **English**
- Use Markdown for documentation; keep files focused on a single topic
- Prefix experimental files with `exp_` and finalized references with `ref_`
- Store raw experiment logs under `logs/` and analysis summaries under `analysis/`

## Key Topics

- **Context Engineering**: prompt structure, instruction hierarchy, memory persistence, context window management
- **Harness Design**: task definitions, scoring rubrics, reproducibility, baseline comparisons
- **Agent Behavior**: delegation patterns, tool usage, verification protocols, failure modes

## Language Rules

- **Thinking/reasoning**: Always in English (internal chain-of-thought)
- **Output/docs/responses**: Always in Korean (한글) for user-facing content
- Documentation files, analysis reports, and user responses should be written in Korean
- Code comments and variable names remain in English

## Working Rules

- This is a research space — favor clarity and traceability over polish
- Link sources and timestamps when recording observations
- When an experiment contradicts a previous finding, update the earlier note rather than creating duplicates

## UAM Plugin

UAM (Unified Agent Methodology)은 OMC, hoyeon, SG-Loop 세 시스템의 강점을 하나의 5-Phase 파이프라인으로 통합한 에이전트 오케스트레이션 플러그인이다.

### Activation

- **Keyword**: 사용자 입력에 `uam` 포함 시 자동 활성화 (UserPromptSubmit 훅)
- **Skill**: `/project:uam` 으로 전체 파이프라인 활성화 (독립형, OMC 불필요)
- **Command**: `/project:uam-run` 으로 상세 오케스트레이션 프로토콜 로드

### Core Principle: Orchestrator-Worker Separation (HARD ENFORCEMENT)

> **오케스트레이터는 절대 소스 코드를 직접 작성하지 않는다.**

- PreToolUse 훅이 Edit/Write를 차단 (`.uam/`, `.omc/`, `.claude/`, `PLAN.md`, `docs/learnings/` 제외)
- 모든 코드 변경은 `uam-worker` 에이전트에게 Task 도구로 위임
- 위반 시 hard block (operation 자체가 진행되지 않음)

### 5-Phase Pipeline

| Phase | 이름 | 에이전트 | 핵심 산출물 |
|-------|------|---------|-----------|
| 1 | Quick Plan | explore, gap-analyzer, tradeoff-analyzer, verification-planner, **pm**, **designer**, **researcher** | PLAN.md (체크박스 SSOT) |
| 2 | MVP Sprint | worker, **frontend** (병렬), git-master | 구현된 코드 + 원자적 커밋 |
| 3 | Quality Gate | code-reviewer + Judge 로직 | Gate 1-3 통과/실패 판정 |
| 4 | Fix Loop | worker, debugger | 적응적 3단계 수정 |
| 5 | Finalize | git-master | 학습 추출 + project-memory |

### Agent Catalog (12 agents + Judge logic)

| Agent | Model | disallowedTools | Phase | 역할 |
|-------|-------|-----------------|-------|------|
| `uam-explore` | haiku | Write, Edit, Task | 1 | 코드베이스 탐색 |
| `uam-gap-analyzer` | haiku | Write, Edit, Bash, Task | 1 | 누락 요구사항 식별 |
| `uam-tradeoff-analyzer` | sonnet | Write, Edit, Bash, Task | 1 | 위험도 평가 |
| `uam-verification-planner` | sonnet | Write, Edit, Bash, Task | 1 | A/S/H 테스트 분류 |
| `uam-pm` | **opus** | Write, Edit, Bash, Task | 1 | 요구사항 정제, 사용자 스토리, 우선순위 |
| `uam-designer` | sonnet | Write, Edit, Bash, Task | 1, 3 | UX/UI 설계, 컴포넌트 구조, 접근성 |
| `uam-researcher` | sonnet | Write, Edit, Task | 1 | 기술 조사, 선행 사례, 라이브러리 평가 |
| `uam-worker` | sonnet | Task | 2, 4 | TODO 구현 (범용) |
| `uam-frontend` | sonnet | Task | 2, 4 | 프론트엔드 구현 (UI/CSS/컴포넌트) |
| `uam-git-master` | sonnet | Write, Edit, Task | 2, 5 | 원자적 커밋 |
| `uam-code-reviewer` | sonnet | Write, Edit | 3 | 멀티모델 교차 리뷰 |
| `uam-debugger` | sonnet | Write, Edit, Task | 4 | 근본 원인 분석 |

Judge는 에이전트가 아닌 오케스트레이터 내부 로직 (Docker pytest 결과 판정).

### Hook System (4 hooks)

| Hook | Event | Role |
|------|-------|------|
| `uam-write-guard.mjs` | PreToolUse (Edit/Write) | 소스 파일 쓰기 차단 |
| `uam-validate-output.mjs` | PostToolUse (Task) | 에이전트 출력 스키마 검증 리마인더 |
| `uam-phase-controller.mjs` | Stop | Phase 전환 + 루프 지속 |
| `uam-keyword-detector.mjs` | UserPromptSubmit | "uam" 키워드 감지 + 상태 초기화 |

### State Management

- 상태 파일: `.uam/state.json` (design doc §12.2 스키마)
- 계획 파일: `.uam/PLAN.md` (체크박스가 SSOT)
- 학습 파일: `docs/learnings/{feature}/` (learnings, decisions, issues, metrics)
- UAM 비활성 시 모든 훅이 조용히 패스 (기존 워크플로 간섭 없음)

### Skill Set (7 skills + 1 command)

| Skill | 호출 | 목적 | 출처 패턴 |
|-------|------|------|----------|
| `uam` | `/project:uam` | 전체 5-Phase 파이프라인 (독립형) | hoyeon Fat Skill + UAM 상태 머신 |
| `uam-pivot` | `/project:uam-pivot` | Pivot Points 인터뷰 (불변 제약 정의) | UAM 고유 |
| `uam-status` | `/project:uam-status` | 파이프라인 대시보드 (진행률, 게이트, 수렴) | OMC status-check |
| `uam-cancel` | `/project:uam-cancel` | 안전한 중단 + 상태 보존 | OMC cancel + hoyeon 상태 보존 |
| `uam-resume` | `/project:uam-resume` | 이전 Phase에서 재개 | UAM 고유 |
| `uam-bugfix` | `/project:uam-bugfix` | 독립형 적응적 버그 수정 (3회 시도 + 서킷 브레이커) | hoyeon /bugfix |
| `uam-compound` | `/project:uam-compound` | 학습 추출 + 지식 증류 + 프로젝트 메모리 | hoyeon /compound |
| `uam-run` | `/project:uam-run` (command) | 상세 오케스트레이션 프로토콜 참조 | UAM 설계 문서 |

UAM은 OMC 없이 완전히 독립적으로 동작한다. 키워드 감지, 상태 관리, Phase 전환 모두 자체 훅으로 처리.

### Discovery-Driven Plan Evolution

Worker가 실행 중 발견한 개선점(Discovery)은 Pivot Points와 충돌 검사 후 Plan에 반영된다:
- **CONFIRMED PP 충돌** → 자동 반려
- **PROVISIONAL PP 충돌** → HITL로 판단
- **PP 충돌 없음** → maturity_mode에 따라 즉시/검토/보류

### Design Reference

전체 사양: `docs/design_unified_agent_methodology.md` (1,057줄, 43.6KB)

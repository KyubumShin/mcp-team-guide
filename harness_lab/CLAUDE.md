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

UAM (Unified Agent Methodology)은 OMC, hoyeon, SG-Loop 세 시스템의 강점을 하나의 5-Phase 파이프라인으로 통합한 에이전트 오케스트레이션 플러그인이다. OMC 없이 완전히 독립적으로 동작한다.

### Activation

- **Keyword**: 사용자 입력에 `uam` 포함 시 자동 활성화
- **Skill**: `/project:uam` 으로 전체 파이프라인 활성화
- **Command**: `/project:uam-run` 으로 상세 오케스트레이션 프로토콜 로드
- **Setup**: `/uam:uam-setup` 으로 설치 및 설정
- **Doctor**: `/uam:uam-doctor` 으로 설치 상태 진단

### Core Principle: Orchestrator-Worker Separation

> **오케스트레이터는 절대 소스 코드를 직접 작성하지 않는다.**

PreToolUse 훅이 Edit/Write를 차단하며, 모든 코드 변경은 `uam-worker` 에이전트에게 Task 도구로 위임한다.

### 5-Phase Pipeline

| Phase | 이름 | 핵심 산출물 |
|-------|------|-----------|
| 1-A | Deep Research | `.uam/research/report.md` |
| 1-B | Plan Generation | `.uam/PLAN.md` (체크박스 SSOT) |
| 2 | MVP Sprint | 구현된 코드 + 원자적 커밋 |
| 3 | Quality Gate | Gate 1-3 통과/실패 판정 |
| 4 | Fix Loop | 적응적 3단계 수정 |
| 5 | Finalize | 학습 추출 + project-memory |

### Design Reference

전체 사양: `UAM/docs/design_unified_agent_methodology.md`
빠른 참조: `UAM/README.md`

## MPL Plugin

MPL(Micro-Phase Loop)은 독립 플러그인으로, 태스크를 마이크로 페이즈로 분해하여
각각 독립적으로 계획-실행-검증하는 구조화된 파이프라인이다.

### Activation

- **Keyword**: 사용자 입력에 `mpl` 포함 시 자동 활성화
- **Skill**: `/mpl:mpl` 으로 파이프라인 활성화
- **Setup**: `/mpl:mpl-setup` 으로 설치
- **Doctor**: `/mpl:mpl-doctor` 으로 진단

### Core Principle: Orchestrator-Worker Separation

> **오케스트레이터는 절대 소스 코드를 직접 작성하지 않는다.**

PreToolUse 훅이 Edit/Write를 차단하며, 모든 코드 변경은 `mpl-worker` 에이전트에게 Task 도구로 위임한다.

### Design Reference

전체 사양: `MPL/docs/design.md`
로드맵: `MPL/docs/roadmap/overview.md`
빠른 참조: `MPL/README.md`
